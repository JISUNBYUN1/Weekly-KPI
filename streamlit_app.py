import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
import math
import re
import tempfile
from pathlib import Path

st.set_page_config(page_title="PP3G | Marketing Performance", page_icon="▥", layout="wide")

from executive_report import STYLE, render_month_week_analysis, render_product_performance, load_star_xlsx, render_star_section, star_week_sort_key, star_month_sort_key

st.markdown(STYLE, unsafe_allow_html=True)

# 거래선 목록
AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]
PRODUCT_ORDER = ["냉장고", "김치냉장고", "의류케어", "조리기기", "정수기"]

# 세션 상태
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "page" not in st.session_state:
    st.session_state.page = "전체"

# 데이터 로드
@st.cache_data(ttl=3600)
def load_sales_data():
    """KPI 데이터 로드"""
    import os
    data = {}
    
    # 현재 디렉토리 확인
    current_dir = os.getcwd()
    
    bizplan = {}
    bizplan_files = ['bizplan_SOP.json', 'bizplan_쿠팡.json', 'bizplan_종합몰.json', 'bizplan_홈쇼핑.json']
    for f in bizplan_files:
        try:
            with open(f, encoding='utf-8') as file:
                bizplan.update(json.load(file))
        except FileNotFoundError:
            pass
        except Exception as e:
            pass
    data['bizplan'] = bizplan
    
    premium = {}
    premium_files = ['premium_냉장고.json', 'premium_세탁기.json', 'premium_식기세척기.json', 'premium_정수기.json']
    for f in premium_files:
        try:
            with open(f, encoding='utf-8') as file:
                premium.update(json.load(file))
        except FileNotFoundError:
            pass
        except Exception as e:
            pass
    data['premium'] = premium
    
    base_files = {
        'smartstore': 'smartstore_customers.json',
        'affiliate': 'affiliate_final_data.json',
        'coupang_ppm': 'coupang_ppm_data.json'
    }
    
    for key, filename in base_files.items():
        try:
            with open(filename, encoding='utf-8') as f:
                loaded_data = json.load(f)
                data[key] = loaded_data
        except FileNotFoundError:
            # 파일을 찾을 수 없으면 빈 데이터로 설정
            data[key] = {}
        except json.JSONDecodeError:
            data[key] = {}
        except Exception as e:
            data[key] = {}
    
    return data

def load_weekly_data():
    if os.path.exists("weekly_data.json"):
        with open("weekly_data.json", encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_weekly_data(data):
    with open("weekly_data.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_feedback():
    if os.path.exists("feedback.json"):
        with open("feedback.json", encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_feedback(data):
    with open("feedback.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_raw_upload(uploaded_file):
    """담당자가 올린 원본을 파일명 충돌 없이 보관하고 목록에 남긴다."""
    safe_name = Path(uploaded_file.name).name
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("파일명을 확인해주세요")
    upload_dir = Path(__file__).resolve().with_name("raw_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    destination = upload_dir / f"{timestamp}_{safe_name}"
    with destination.open("wb") as handle:
        handle.write(uploaded_file.getbuffer())
    manifest_path = upload_dir / "upload_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    except ValueError:
        manifest = []
    manifest.append({"파일명": safe_name, "저장파일": destination.name,
                     "용량(byte)": destination.stat().st_size,
                     "업로드시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination, manifest

# 라이브커머스: 원 단위 원본과 표시용 값을 분리한다.
def live_week_sort_key(week):
    match = re.fullmatch(r"W(\d{1,2})([AB]?)", week)
    if not match or not 1 <= int(match.group(1)) <= 53:
        raise ValueError(f"올바르지 않은 주차: {week}")
    return int(match.group(1)), match.group(2)


def live_weeks_for_month(calendar, month):
    """제공된 업무 주차표를 사용하며 월경계만 A/B로 분할한다."""
    month_num = int(month.replace("월", ""))
    result = set()
    for week, info in calendar.items():
        live_week_sort_key(week)
        months = info["month"]
        months = months if isinstance(months, list) else [months]
        if not months or len(months) > 2 or any(
            isinstance(m, bool) or not isinstance(m, int) or not 1 <= m <= 12
            for m in months
        ):
            raise ValueError(f"{week}: 월 정보가 올바르지 않습니다")
        if month_num not in months:
            continue
        if week.endswith(("A", "B")):
            if len(months) == 1 or months[0 if week.endswith("A") else 1] == month_num:
                result.add(week)
        elif len(months) == 1:
            result.add(week)
        else:
            result.add(week + ("A" if months.index(month_num) == 0 else "B"))
    return ["계"] + sorted(result, key=live_week_sort_key, reverse=True)


def live_sum_records(records):
    """비어 있는 비용/실적은 0이 아니다. 하나라도 미제공이면 합계도 미제공."""
    records = list(records)
    result = {}
    for field in ("방송횟수", "방송매출", "소요비용"):
        values = [record.get(field) for record in records]
        result[field] = sum(values) if values and all(v is not None for v in values) else None
    result["마케팅활동"] = "\n".join(dict.fromkeys(
        record["마케팅활동"].strip() for record in records
        if record.get("마케팅활동") and record["마케팅활동"].strip()
    ))
    return result


def live_aggregate_periods(periods):
    periods = list(periods)
    return {
        agency: live_sum_records(period.get(agency, {}) for period in periods)
        for agency in AGENCIES
    }


def live_validate_data(data):
    """검증 후 새 객체 반환. 주차별 '계'는 상세 주차만으로 재계산한다."""
    if not isinstance(data, dict):
        raise ValueError("최상위 데이터는 JSON 객체여야 합니다")
    if data.get("금액단위", "원") != "원":
        raise ValueError("금액단위는 '원'이어야 합니다. 백만 단위 자료는 먼저 원으로 변환해주세요")
    if data.get("기준연도", 2026) != 2026:
        raise ValueError("이 화면은 weeks_2026.json 기준입니다. 다른 연도 자료를 혼합할 수 없습니다")
    if data.get("schema_version", 1) != 1:
        raise ValueError("지원하지 않는 라이브커머스 데이터 형식 버전입니다")
    result = {**data}
    for section in ("월별", "주차별"):
        source = data.get(section, {})
        if not isinstance(source, dict):
            raise ValueError(f"{section}은 JSON 객체여야 합니다")
        result[section] = {}
        for period, agencies in source.items():
            if section == "월별":
                if not re.fullmatch(r"([1-9]|1[0-2])월", period):
                    raise ValueError(f"올바르지 않은 월: {period}")
            elif period == "계":
                continue  # 수동 합계는 이중 집계하지 않는다.
            else:
                live_week_sort_key(period)
            if not isinstance(agencies, dict):
                raise ValueError(f"{section}/{period}: 거래선별 객체가 필요합니다")
            result[section][period] = {}
            for agency, record in agencies.items():
                if agency not in AGENCIES or not isinstance(record, dict):
                    raise ValueError(f"{section}/{period}/{agency}: 거래선 또는 데이터 형식 확인")
                clean = dict(record)
                for field in ("방송횟수", "방송매출", "소요비용"):
                    value = record.get(field)
                    if value is not None:
                        if isinstance(value, bool) or not isinstance(value, (int, float)):
                            raise ValueError(f"{period}/{agency}/{field}: 숫자 또는 null이 필요합니다")
                        if not math.isfinite(value) or value < 0:
                            raise ValueError(f"{period}/{agency}/{field}: 유한한 0 이상 숫자가 필요합니다")
                        if field == "방송횟수" and int(value) != value:
                            raise ValueError(f"{period}/{agency}/방송횟수: 정수가 필요합니다")
                    clean[field] = value
                activity = record.get("마케팅활동", "")
                if activity is not None and not isinstance(activity, str):
                    raise ValueError(f"{period}/{agency}/마케팅활동: 문자열이 필요합니다")
                clean["마케팅활동"] = activity or ""
                result[section][period][agency] = clean
    details = list(result["주차별"].values())
    result["주차별"] = {
        "계": live_aggregate_periods(details) if details else {},
        **result["주차별"],
    }
    return result


def live_load_data(path=None):
    """매 화면 실행 시 읽어 수정 직후 데이터가 한 시간 캐시에 묶이지 않게 한다."""
    path = Path(path) if path is not None else Path(__file__).resolve().with_name("live_commerce_data.json")
    with path.open(encoding="utf-8-sig") as file:
        return live_validate_data(json.load(file))


def live_save_data(data, path=None):
    """원 단위 데이터를 검증 후 원자적으로 저장. 조회 시에는 호출하지 않는다.

    파일 손상 방지용이며 동시 편집 충돌 방지나 클라우드 영구 저장을 보장하지 않는다.
    """
    validated = live_validate_data(data)
    path = Path(path) if path is not None else Path(__file__).resolve().with_name("live_commerce_data.json")
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as file:
            temp_name = file.name
            json.dump(validated, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name is not None and os.path.exists(temp_name):
            os.unlink(temp_name)


def live_select_period(data, calendar, month, week):
    """UI의 '계'는 선택 월이다. 전체 주차 합계와 혼용하지 않는다."""
    if week == "계":
        monthly = data.get("월별", {}).get(month, {})
        if monthly:
            return monthly, "월별 제공 실적"
        available = live_weeks_for_month(calendar, month)[1:]
        periods = [data["주차별"][w] for w in available if data.get("주차별", {}).get(w)]
        if periods:
            return live_aggregate_periods(periods), "입력된 주차만의 합계 · 월 마감 실적 아님"
        return {}, "해당 월에 제공된 데이터가 없습니다"
    if week not in live_weeks_for_month(calendar, month):
        return {}, "선택 월에 속하지 않는 주차입니다"
    return data.get("주차별", {}).get(week, {}), "주차별 제공 실적"


def live_table_rows(agencies):
    if not agencies:
        return []
    records = {agency: agencies.get(agency, {}) for agency in AGENCIES}
    total = live_sum_records(records.values())
    total["마케팅활동"] = "거래선별 내용 참조"
    rows = []
    for agency, record in [("전체", total)] + list(records.items()):
        count = record.get("방송횟수")
        sale = record.get("방송매출")
        cost = record.get("소요비용")
        rows.append({
            "거래선": agency,
            "방송횟수": f"{count:,.0f}" if count is not None else "미제공",
            "방송매출(백만)": f"{sale / 1000000:,.2f}" if sale is not None else "미제공",
            "소요비용(백만)": f"{cost / 1000000:,.2f}" if cost is not None else "미제공",
            "마케팅활동": record.get("마케팅활동") or "미제공",
        })
    return rows


def live_render_table(agencies):
    st.dataframe(pd.DataFrame(live_table_rows(agencies)), use_container_width=True, hide_index=True)
    st.caption("금액 단위: 백만원 · 소수점 둘째 자리 표시 · 미제공과 0은 구분합니다.")
    if any(record.get("마케팅활동") for record in agencies.values()):
        with st.expander("📝 마케팅활동 전문 보기"):
            for agency in AGENCIES:
                activity = agencies.get(agency, {}).get("마케팅활동")
                if activity:
                    st.write(f"**{agency}**")
                    st.text(activity)


def live_render_page():
    st.subheader("라이브커머스 실적")
    st.caption("2026년 · 업무 주차 기준")
    try:
        data = live_load_data()
    except FileNotFoundError:
        st.warning("live_commerce_data.json이 없습니다. 앱과 같은 폴더에 파일을 추가해주세요.")
        data = {"월별": {}, "주차별": {}}
    except (OSError, ValueError, TypeError) as error:
        st.error(f"라이브커머스 데이터를 읽을 수 없습니다: {error}")
        return
    try:
        with Path(__file__).resolve().with_name("weeks_2026.json").open(encoding="utf-8-sig") as file:
            calendar = json.load(file)
        # 전체 캘린더를 먼저 확인해 잘못된 월/주차를 조용히 누락하지 않는다.
        calendar_weeks = set()
        for number in range(1, 13):
            calendar_weeks.update(live_weeks_for_month(calendar, f"{number}월")[1:])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        st.warning(f"주차 파일 확인 필요: {error}. 월별 데이터만 조회합니다.")
        calendar, calendar_weeks = {}, set()

    months = [f"{number}월" for number in range(12, 0, -1)]
    default_index = next((i for i, month in enumerate(months) if data["월별"].get(month)), 0)
    month = st.selectbox("월 선택", months, index=default_index, key="live_month_select")
    weeks = live_weeks_for_month(calendar, month)
    week = st.selectbox("주차 선택", weeks, key=f"live_week_select_{month}")
    st.write("---")
    period_label = "월 전체" if week == "계" else week
    st.write(f"**📊 {month} 라이브커머스 실적 ({period_label})**")

    unassigned = set(data["주차별"]) - {"계"} - calendar_weeks
    pending = data.get("확인필요", [])
    if unassigned or pending:
        st.warning("주차표와 일치하지 않는 원본 데이터가 있습니다. 해당 자료는 월·주차 상세에 자동 배정하지 않았습니다.")
        with st.expander("주차 확인 사항"):
            for week_name in sorted(unassigned):
                st.text(f"{week_name}: weeks_2026.json에 해당 표시 주차가 없습니다.")
            for item in pending:
                if isinstance(item, dict):
                    st.text(f"{item.get('원본월', '')} {item.get('원본주차', '')}: {item.get('사유', '주차 확인 필요')}")

    agencies, note = live_select_period(data, calendar, month, week)
    if agencies:
        st.caption(note)
        live_render_table(agencies)
    else:
        st.info(f"{month} {week}: 제공된 데이터가 없습니다.")

# 로그인
def login_page():
    st.title("PP3G 마케팅 성과 관리")
    st.caption("주간 실적 · 거래선 활동 · 담당자 피드백")
    st.markdown("---")
    
    user_name = st.text_input("이름을 입력하세요")
    
    if st.button("입장", use_container_width=True):
        if user_name.strip():
            st.session_state.user_name = user_name
            st.rerun()
        else:
            st.error("이름을 입력해주세요")

# 값 포매팅 함수
def format_display_value(val):
    """표시용 값 포매팅 (0->-, 음수->△)"""
    if val is None or val == "":
        return "-"
    if isinstance(val, str):
        return val
    if isinstance(val, (int, float)):
        if val == 0:
            return "-"
        elif val < 0:
            if isinstance(val, float) and val > -1:
                return f"△{abs(val):.1f}%"
            return f"△{int(abs(val))}" if val == int(val) else f"△{abs(val):.2f}"
        else:
            return f"{int(val):,}"
    return str(val)

# 라이브커머스 테이블 생성
def create_live_commerce_table(data_dict, title=""):
    """라이브커머스 계층형 테이블 생성 (소수점 1자리 ROUND)
    
    필요한 데이터 구조:
    {
        "전체": {
            "방송횟수": int,
            "방송매출": float (원 단위 또는 백만원),
            "소요비용": float (원 단위 또는 백만원)
        },
        "거래선명": {
            "방송횟수": int,
            "방송매출": float,
            "소요비용": float
        }
    }
    """
    st.markdown(f"### {title}")
    
    html = """
    <style>
        .live-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .live-table th, .live-table td { border: 1px solid #d0d0d0; padding: 8px 6px; text-align: center; height: 26px; }
        .header-tier1 { background: #e2efda; font-weight: 600; font-size: 13px; }
        .total-row { background: #fff2cc; font-weight: 600; border-top: 2px solid #333; }
        .data-row { background: #f9f9f9; }
        .data-row:nth-child(even) { background: #ffffff; }
        .agency-col { text-align: left; font-weight: 500; padding-left: 8px; }
        .number { text-align: right; padding-right: 4px; font-family: 'Courier New', monospace; }
        .negative { color: #d92d20; }
    </style>
    <table class="live-table">
        <thead>
            <tr>
                <th class="header-tier1">거래선</th>
                <th class="header-tier1">방송횟수</th>
                <th class="header-tier1">방송매출(백만)</th>
                <th class="header-tier1">소요비용(백만)</th>
                <th class="header-tier1">방송효율</th>
                <th class="header-tier1">회당매출(백만)</th>
            </tr>
        </thead>
        <tbody>
    """
    
    def add_row(agency_name, is_total=False, broadcast_count=0, broadcast_sale=0, cost=0):
        """행 생성 (6개 칼럼: 거래선, 방송횟수, 방송매출, 소요비용, 방송효율, 회당매출)
        broadcast_count: 방송횟수 (정수)
        broadcast_sale: 방송매출 (원 단위 또는 백만원, float) → 소수점 1자리
        cost: 소요비용 (원 단위 또는 백만원, float) → 소수점 2자리
        """
        row_class = "total-row" if is_total else "data-row"
        html_row = f'<tr class="{row_class}"><td class="agency-col">{agency_name}</td>'
        
        # 방송횟수 (정수)
        html_row += f'<td class="number">{format_display_value(int(broadcast_count))}</td>'
        
        # 방송매출 (원 단위를 백만 단위로 변환, 소수점 1자리, 천단위 쉼표)
        if isinstance(broadcast_sale, (int, float)):
            # 원 단위인지 백만 단위인지 판단 (1000000 이상이면 원 단위)
            if broadcast_sale >= 1000000:
                sale_million = broadcast_sale / 1000000
            else:
                sale_million = broadcast_sale
            html_row += f'<td class="number">{round(sale_million, 1):,.1f}</td>'
        else:
            html_row += f'<td class="number">-</td>'
        
        # 소요비용 (원 단위를 백만 단위로 변환, 소수점 2자리, 천단위 쉼표)
        if isinstance(cost, (int, float)) and cost > 0:
            if cost >= 1000000:
                cost_million = cost / 1000000
            else:
                cost_million = cost
            html_row += f'<td class="number">{round(cost_million, 2):,.2f}</td>'
        else:
            html_row += f'<td class="number">-</td>'
        
        # 방송효율 = 방송매출 / 소요비용 (소수점 2자리)
        if isinstance(cost, (int, float)) and cost > 0 and isinstance(broadcast_sale, (int, float)):
            efficiency = round(broadcast_sale / cost, 2)
            html_row += f'<td class="number">{efficiency:.2f}</td>'
        else:
            html_row += f'<td class="number">-</td>'
        
        # 회당매출 = 방송매출 / 방송횟수 (백만원, 소수점 1자리, 천단위 쉼표)
        if isinstance(broadcast_count, (int, float)) and broadcast_count > 0 and isinstance(broadcast_sale, (int, float)):
            if broadcast_sale >= 1000000:
                per_broadcast = broadcast_sale / broadcast_count / 1000000
            else:
                per_broadcast = broadcast_sale / broadcast_count
            per_broadcast_rounded = round(per_broadcast, 1)
            html_row += f'<td class="number">{per_broadcast_rounded:,.1f}</td>'
        else:
            html_row += f'<td class="number">-</td>'
        
        html_row += '</tr>'
        return html_row
    
    # 계 (전체) 행
    if "전체" in data_dict:
        total = data_dict["전체"]
        html += add_row(
            "계",
            is_total=True,
            broadcast_count=total.get('방송횟수', 0),
            broadcast_sale=total.get('방송매출', 0),
            cost=total.get('소요비용', 0)
        )
    
    # 거래선별 행
    for agency in AGENCIES:
        if agency in data_dict:
            agency_data = data_dict[agency]
            html += add_row(
                agency,
                is_total=False,
                broadcast_count=agency_data.get('방송횟수', 0),
                broadcast_sale=agency_data.get('방송매출', 0),
                cost=agency_data.get('소요비용', 0)
            )
    
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)




def create_affiliate_table(data_dict, title=""):
    """어필리에이트 4단계 계층형 테이블 생성"""
    st.markdown(f"### {title}")
    
    html = """
    <style>
        .affiliate-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .affiliate-table th, .affiliate-table td { border: 1px solid #d0d0d0; padding: 8px 6px; text-align: center; height: 26px; }
        .header-tier1 { background: #d9e1f2; font-weight: 600; font-size: 14px; }
        .header-tier2 { background: #e7eef7; font-weight: 500; font-size: 13px; }
        .total-row { background: #fff2cc; font-weight: 600; border-top: 2px solid #333; }
        .data-row { background: #f9f9f9; }
        .data-row:nth-child(even) { background: #ffffff; }
        .agency-col { text-align: left; font-weight: 500; padding-left: 8px; }
        .number { text-align: right; padding-right: 4px; font-family: 'Courier New', monospace; }
    </style>
    <table class="affiliate-table">
        <thead>
            <tr>
                <th rowspan="2" class="header-tier1">거래선</th>
                <th colspan="4" class="header-tier1">어필리에이트</th>
                <th colspan="6" class="header-tier1">쇼핑커넥트</th>
                <th colspan="4" class="header-tier1">공동구매</th>
            </tr>
            <tr>
                <th class="header-tier2">크리에이터 운영수</th>
                <th class="header-tier2">운영모델</th>
                <th class="header-tier2">주문건수</th>
                <th class="header-tier2">주문금액(백만)</th>
                <th class="header-tier2">크리에이터 운영수</th>
                <th class="header-tier2">운영모델</th>
                <th class="header-tier2">유입수</th>
                <th class="header-tier2">상품주문</th>
                <th class="header-tier2">전환율(%)</th>
                <th class="header-tier2">주문금액(백만)</th>
                <th class="header-tier2">크리에이터 운영수</th>
                <th class="header-tier2">운영모델</th>
                <th class="header-tier2">상품주문</th>
                <th class="header-tier2">주문금액(백만)</th>
            </tr>
        </thead>
        <tbody>
    """
    
    def add_row(agency_name, is_total=False, data_item=None):
        row_class = "total-row" if is_total else "data-row"
        html_row = f'<tr class="{row_class}"><td class="agency-col">{agency_name}</td>'
        if data_item:
            aff = data_item.get("어필리에이트", {})
            html_row += f'<td class="number">{format_display_value(aff.get("크리에이터"))}</td>'
            html_row += f'<td class="number">{format_display_value(aff.get("운영모델"))}</td>'
            html_row += f'<td class="number">{format_display_value(aff.get("주문건수"))}</td>'
            html_row += f'<td class="number">{format_display_value(aff.get("주문금액"))}</td>'
            shop = data_item.get("쇼핑커넥트", {})
            html_row += f'<td class="number">{format_display_value(shop.get("크리에이터"))}</td>'
            html_row += f'<td class="number">{format_display_value(shop.get("운영모델"))}</td>'
            html_row += f'<td class="number">{format_display_value(shop.get("유입수"))}</td>'
            html_row += f'<td class="number">{format_display_value(shop.get("상품주문"))}</td>'
            conversion = shop.get("전환율")
            if conversion is None or conversion == 0:
                conv_str = "-"
            elif conversion < 0:
                conv_str = f"△{abs(conversion):.2f}%"
            else:
                conv_str = f"{conversion:.2f}%"
            html_row += f'<td class="number">{conv_str}</td>'
            html_row += f'<td class="number">{format_display_value(shop.get("주문금액"))}</td>'
            joint = data_item.get("공동구매", {})
            html_row += f'<td class="number">{format_display_value(joint.get("크리에이터"))}</td>'
            html_row += f'<td class="number">{format_display_value(joint.get("운영모델"))}</td>'
            html_row += f'<td class="number">{format_display_value(joint.get("상품주문"))}</td>'
            html_row += f'<td class="number">{format_display_value(joint.get("주문금액"))}</td>'
        html_row += '</tr>'
        return html_row
    
    if "계" in data_dict:
        html += add_row("계", is_total=True, data_item=data_dict["계"])
    for agency in AGENCIES:
        if agency in data_dict:
            html += add_row(agency, is_total=False, data_item=data_dict[agency])
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

# 메인 대시보드
def dashboard():
    user_name = st.session_state.user_name
    
    # 사이드바 메뉴
    with st.sidebar:
        st.markdown("### PP3G")
        st.caption("MARKETING PERFORMANCE")
        st.divider()
        
        pages = [
            ("월간ㆍ주간 분석", "전체"),
            ("품목별 실적", "FCST"),
            ("프리미엄", "프리미엄"),
            ("스마트스토어", "스마트"),
            ("라이브커머스", "라이브"),
            ("어필리에이트", "어필"),
            ("주간 실적 입력", "거래선입력"),
            ("거래선 기록", "거래선현황"),
            ("담당자 피드백", "담당자피드백"),
        ]
        
        for emoji_name, page_key in pages:
            if st.button(emoji_name, use_container_width=True, key=f"btn_{page_key}", type="primary" if st.session_state.page == page_key else "secondary"):
                st.session_state.page = page_key
                st.rerun()
        
        st.divider()
        st.caption(f"사용자: {user_name}")
        
        if st.button("로그아웃", use_container_width=True):
            st.session_state.user_name = None
            st.rerun()
    
    # 메인 콘텐츠
    st.markdown('<div class="report-eyebrow">SAMSUNG PP3G / MARKETING PERFORMANCE</div>', unsafe_allow_html=True)
    st.title("마케팅 성과 및 활동 분석")
    st.caption("월간 성과와 주간 실행 활동을 연결해 확인합니다.")
    st.divider()
    
    sales_data = load_sales_data()
    weekly_data = load_weekly_data()
    feedback_data = load_feedback()
    
    current_page = st.session_state.page
    
    # 월간ㆍ주간 분석
    if current_page == "전체":
        render_month_week_analysis(st, Path(__file__).resolve().parent)

    # 품목별 실적
    elif current_page == "FCST":
        render_product_performance(st, Path(__file__).resolve().parent)
    
    # 프리미엄
    # 라이브커머스
    elif current_page == "라이브":
        live_render_page()
    
    # 어필리에이트
    elif current_page == "어필":
        st.subheader("🤝 어필리에이트 실적")
        
        # affiliate_data.json 로드
        affiliate_data = {"월별": {}, "주차별": {}}
        if os.path.exists("affiliate_data.json"):
            try:
                with open("affiliate_data.json", "r", encoding='utf-8') as f:
                    affiliate_data = json.load(f)
            except:
                affiliate_data = {"월별": {}, "주차별": {}}
        
        if affiliate_data["월별"] or affiliate_data["주차별"]:
            # 드롭다운: 월 선택 (역순)
            all_months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
            all_months_reversed = list(reversed(all_months))
            selected_month = st.selectbox("월 선택", all_months_reversed, key="affiliate_month_select")
            
            # 주차 드롭다운: "계"를 항상 맨 위에
            available_weeks = list(affiliate_data["주차별"].keys())
            
            # "계"를 맨 앞으로
            if "계" in available_weeks:
                available_weeks.remove("계")
                available_weeks = ["계"] + sorted(available_weeks, reverse=True)
            else:
                available_weeks = sorted(available_weeks, reverse=True)
            
            if available_weeks:
                selected_week = st.selectbox("주차 선택", available_weeks, key="affiliate_week_select")
            else:
                st.warning("주차 데이터가 없습니다")
                selected_week = None
            
            st.write("---")
            
            if selected_week:
                # 데이터 표시
                if selected_week == "계":
                    st.write(f"**📊 어필리에이트 실적 (전체 계)**")
                    
                    # 계 데이터 표시
                    if selected_week in affiliate_data["주차별"]:
                        week_data = affiliate_data["주차별"][selected_week]
                        
                        rows = []
                        for agency, channels in week_data.items():
                            for channel, data in channels.items():
                                rows.append({
                                    "거래선": agency,
                                    "채널": channel,
                                    "크리에이터": data.get('크리에이터운영수', 0),
                                    "모델": data.get('운영모델', 0),
                                    "유입수": f"{data.get('유입수', 0):,}",
                                    "주문건수": f"{data.get('상품주문건수', 0):,}",
                                    "전환율(%)": f"{data.get('전환율', 0):.4f}%",
                                    "주문금액(백만)": f"{data.get('주문금액', 0) / 1000000:.2f}"
                                })
                        
                        df = pd.DataFrame(rows)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("계 데이터가 없습니다")
                else:
                    st.write(f"**📊 {selected_week} 어필리에이트 실적**")
                    
                    # 주차별 데이터 표시
                    if selected_week in affiliate_data["주차별"]:
                        week_data = affiliate_data["주차별"][selected_week]
                        
                        rows = []
                        for agency, channels in week_data.items():
                            for channel, data in channels.items():
                                rows.append({
                                    "거래선": agency,
                                    "채널": channel,
                                    "크리에이터": data.get('크리에이터운영수', 0),
                                    "모델": data.get('운영모델', 0),
                                    "유입수": f"{data.get('유입수', 0):,}",
                                    "주문건수": f"{data.get('상품주문건수', 0):,}",
                                    "전환율(%)": f"{data.get('전환율', 0):.4f}%",
                                    "주문금액(백만)": f"{data.get('주문금액', 0) / 1000000:.2f}"
                                })
                        
                        df = pd.DataFrame(rows)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("해당 주차의 데이터가 없습니다")
        else:
            st.warning("어필리에이트 데이터가 없습니다")
    
    # 거래선 입력
    elif current_page == "거래선입력":
        st.subheader("✏️ 거래선 주차별 입력")
        
        # 2026년 주차 정보 로드
        try:
            with open('weeks_2026.json', 'r', encoding='utf-8') as f:
                weeks_2026 = json.load(f)
        except:
            st.error("weeks_2026.json 파일을 찾을 수 없습니다")
            weeks_2026 = {}
        
        # 월별 주차 매핑
        def get_weeks_by_month(month):
            """해당 월의 주차 리스트 반환 (A/B 표시 포함, 역순)"""
            month_num = int(month.replace('월', ''))
            weeks_with_suffix = []
            
            for week, info in weeks_2026.items():
                month_info = info['month']
                
                # 단일 월인 경우 (A/B 없음)
                if isinstance(month_info, int):
                    if month_info == month_num:
                        weeks_with_suffix.append(week)
                
                # 리스트인 경우 (월 경계, A/B 있음)
                elif isinstance(month_info, list):
                    if month_num in month_info:
                        # A/B 결정
                        if month_num == month_info[0]:  # 첫 번째 월 (A)
                            weeks_with_suffix.append(f"{week}A")
                        else:  # 두 번째 월 (B)
                            weeks_with_suffix.append(f"{week}B")
            
            # 주차 숫자로 정렬 후 역순
            def sort_key(w):
                # "W35" → 35, "W35A" → 35, "W35B" → 35
                num = int(''.join(filter(str.isdigit, w)))
                return num
            
            return sorted(weeks_with_suffix, key=sort_key, reverse=True)
        
        # Form 외부에서 월/주차 선택 (form 내에서 업데이트 안 되는 문제 해결)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            input_agency = st.selectbox("거래선 선택", AGENCIES, key="input_agency")
        
        with col2:
            # 월 선택 (1-12월 동적, 역순)
            all_months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
            all_months_reversed = list(reversed(all_months))
            input_month = st.selectbox("월 선택", all_months_reversed, key="input_month")
        
        with col3:
            # 선택된 월의 주차 리스트
            available_weeks = get_weeks_by_month(input_month)
            if available_weeks:
                input_week = st.selectbox("주차 선택", available_weeks, key="input_week")
            else:
                st.warning(f"{input_month}에 데이터가 없습니다")
                input_week = None
        
        st.write("---")
        
        with st.form("weekly_form"):
            st.subheader("📝 1️⃣ 네이버 스마트 스토어")
            col1, col2, col3 = st.columns(3)
            with col1:
                ss_new_interest = st.number_input("신규 관심고객수", min_value=0, step=1, key="ss_new_interest_input")
            with col2:
                ss_new_buyer = st.number_input("신규구매 구매자수", min_value=0, step=1, key="ss_new_buyer_input")
            with col3:
                ss_repurchase = st.number_input("재구매 구매자수", min_value=0, step=1, key="ss_repurchase_input")
            
            ss_activity = st.text_area("📌 마케팅활동", placeholder="이번 주 스마트스토어 마케팅 활동을 작성해주세요", height=60, key="ss_activity_input")
            
            st.write("---")
            st.subheader("📱 2️⃣ 어필리에이트")
            
            # 쇼핑커넥트
            st.write("🔹 **쇼핑커넥트**")
            col1, col2, col3 = st.columns(3)
            with col1:
                sc_creator = st.number_input("크리에이터 운영 수", min_value=0, step=1, key="sc_creator_input")
            with col2:
                sc_model = st.number_input("운영 모델 수", min_value=0, step=1, key="sc_model_input")
            with col3:
                sc_visits = st.number_input("유입수", min_value=0, step=1, key="sc_visits_input")
            
            col1, col2 = st.columns(2)
            with col1:
                sc_orders = st.number_input("상품주문건수", min_value=0, step=1, key="sc_orders_input")
            with col2:
                sc_amount = st.number_input("주문금액", min_value=0, step=1, key="sc_amount_input")
            
            sc_activity = st.text_area("📌 마케팅활동", placeholder="쇼핑커넥트 마케팅 활동을 작성해주세요", height=60, key="sc_activity_input")
            
            st.write("")
            
            # 공동구매
            st.write("🔹 **공동구매**")
            col1, col2, col3 = st.columns(3)
            with col1:
                cj_creator = st.number_input("크리에이터 운영 수", min_value=0, step=1, key="cj_creator_input")
            with col2:
                cj_model = st.number_input("운영 모델 수", min_value=0, step=1, key="cj_model_input")
            with col3:
                st.write("")
            
            col1, col2 = st.columns(2)
            with col1:
                cj_orders = st.number_input("상품주문건수", min_value=0, step=1, key="cj_orders_input")
            with col2:
                cj_amount = st.number_input("주문금액", min_value=0, step=1, key="cj_amount_input")
            
            cj_activity = st.text_area("📌 마케팅활동", placeholder="공동구매 마케팅 활동을 작성해주세요", height=60, key="cj_activity_input")
            
            st.write("---")
            st.subheader("🎥 3️⃣ AI 라이브")
            col1, col2, col3 = st.columns(3)
            with col1:
                live_count = st.number_input("방송횟수", min_value=0, step=1, key="live_count_input")
            with col2:
                live_sale = st.number_input("방송매출", min_value=0, step=1, key="live_sale_input")
            with col3:
                live_cost = st.number_input("소요비용", min_value=0, step=1, key="live_cost_input")
            
            live_activity = st.text_area("📌 마케팅활동", placeholder="AI 라이브 마케팅 활동을 작성해주세요", height=60, key="live_activity_input")
            
            st.write("---")
            st.subheader("🎯 당주 주요활동")
            
            activity_AI라이브효율증대 = st.text_area("📌 AI 라이브 효율 증대", placeholder="AI 라이브 효율 증대 관련 활동을 작성해주세요", height=50, key="activity_AI라이브효율증대_input")
            activity_어필리에이트내재화 = st.text_area("📌 어필리에이트 내재화", placeholder="어필리에이트 내재화 관련 활동을 작성해주세요", height=50, key="activity_어필리에이트내재화_input")
            activity_구독활성화 = st.text_area("📌 구독활성화", placeholder="구독활성화 관련 활동을 작성해주세요", height=50, key="activity_구독활성화_input")
            activity_기타신규프로젝트 = st.text_area("📌 기타 신규 프로젝트", placeholder="기타 신규 프로젝트를 작성해주세요", height=50, key="activity_기타신규프로젝트_input")
            
            st.write("---")
            
            submit_button = st.form_submit_button("💾 저장", use_container_width=True)
            
            if submit_button:
                if input_week is None:
                    st.error("주차를 선택해주세요")
                else:
                    # 주차에서 A/B 제거 (저장용 기본 주차명)
                    # 예: "W35B" → "W35"
                    base_week = input_week.replace('A', '').replace('B', '')
                    
                    # 데이터 조합 (새로운 구조)
                    new_data = {
                        "거래선": input_agency,
                        "월": input_month,
                        "주차": base_week,  # A/B 제거한 주차명 저장
                        "주차_표시": input_week,  # 화면에 보여줬던 형식 저장 (A/B 포함)
                        "네이버스마트스토어": {
                            "신규관심고객수": ss_new_interest,
                            "신규구매구매자수": ss_new_buyer,
                            "재구매구매자수": ss_repurchase,
                            "마케팅활동": ss_activity
                        },
                        "쇼핑커넥트": {
                            "크리에이터운영수": sc_creator,
                            "운영모델수": sc_model,
                            "유입수": sc_visits,
                            "상품주문건수": sc_orders,
                            "주문금액": sc_amount,
                            "마케팅활동": sc_activity
                        },
                        "공동구매": {
                            "크리에이터운영수": cj_creator,
                            "운영모델수": cj_model,
                            "상품주문건수": cj_orders,
                            "주문금액": cj_amount,
                            "마케팅활동": cj_activity
                        },
                        "AI라이브": {
                            "방송횟수": live_count,
                            "방송매출": live_sale,
                            "소요비용": live_cost,
                            "마케팅활동": live_activity
                        },
                        "당주주요활동": {
                            "AI라이브효율증대": activity_AI라이브효율증대,
                            "어필리에이트내재화": activity_어필리에이트내재화,
                            "구독활성화": activity_구독활성화,
                            "기타신규프로젝트": activity_기타신규프로젝트
                        }
                    }
                    
                    # weekly_data.json에 저장
                    if os.path.exists("weekly_data.json"):
                        try:
                            with open("weekly_data.json", "r", encoding='utf-8') as f:
                                loaded_data = json.load(f)
                                # 리스트인지 확인, 아니면 빈 리스트로
                                weekly_data_list = loaded_data if isinstance(loaded_data, list) else []
                        except:
                            weekly_data_list = []
                    else:
                        weekly_data_list = []
                    
                    # 중복 확인 및 업데이트
                    found = False
                    for idx, item in enumerate(weekly_data_list):
                        # item이 딕셔너리인지 확인
                        if isinstance(item, dict) and (item.get("거래선") == input_agency and 
                            item.get("월") == input_month and 
                            item.get("주차") == base_week):
                            weekly_data_list[idx] = new_data
                            found = True
                            break
                    
                    if not found:
                        weekly_data_list.append(new_data)
                    
                    with open("weekly_data.json", "w", encoding='utf-8') as f:
                        json.dump(weekly_data_list, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"✅ {input_agency} - {input_month} {input_week} 데이터가 저장되었습니다!")
                    st.balloons()
    
    # 스마트스토어
    elif current_page == "스마트":
        st.subheader("🛒 스마트스토어 실적")
        
        # smartstore_data.json 로드
        smartstore_data = {}
        if os.path.exists("smartstore_data.json"):
            try:
                with open("smartstore_data.json", "r", encoding='utf-8') as f:
                    smartstore_data = json.load(f)
            except:
                smartstore_data = {}
        
        if smartstore_data:
            # 신규관심고객과 구매비중을 같은 화면에 표시
            st.subheader("신규 관심고객 유입 현황")
            
            # 월/주차 선택
            col1, col2 = st.columns(2)
            with col1:
                data_type = st.radio("데이터 종류", ["월별", "주차별"], key="ss_interest_type")
            with col2:
                if data_type == "월별":
                    all_months = list(reversed(list(smartstore_data["신규관심고객"]["월별"].keys())))
                    selected = st.selectbox("월 선택", all_months, key="ss_interest_month")
                    display_data = smartstore_data["신규관심고객"]["월별"].get(selected, {})
                else:
                    all_weeks = sorted(smartstore_data["신규관심고객"]["주차별"].keys(), reverse=True)
                    selected = st.selectbox("주차 선택", all_weeks, key="ss_interest_week")
                    display_data = smartstore_data["신규관심고객"]["주차별"].get(selected, {})
            
            if display_data:
                # 테이블 생성
                rows = []
                for agency, data in display_data.items():
                    row = {
                        "거래선": agency,
                        "누적관심고객수": f"{data.get('누적관심고객수', 0):,}",
                        "신규관심고객수": f"{data.get('신규관심고객수', 0):,}",
                    }
                    if data_type == "월별":
                        row["전월비(%)"] = f"{data.get('전월비', 0):.2f}%"
                    else:
                        row["전주비(%)"] = f"{data.get('전주비', 0):.2f}%"
                    rows.append(row)
                
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("구매비중 변화 (신규 vs 재구매)")
            
            # 월/주차 선택
            col1, col2 = st.columns(2)
            with col1:
                data_type2 = st.radio("데이터 종류", ["월별", "주차별"], key="ss_purchase_type")
            with col2:
                if data_type2 == "월별":
                    all_months = list(reversed(list(smartstore_data["구매비중"]["월별"].keys())))
                    selected2 = st.selectbox("월 선택", all_months, key="ss_purchase_month")
                    display_data2 = smartstore_data["구매비중"]["월별"].get(selected2, {})
                else:
                    all_weeks = sorted(smartstore_data["구매비중"]["주차별"].keys(), reverse=True)
                    selected2 = st.selectbox("주차 선택", all_weeks, key="ss_purchase_week")
                    display_data2 = smartstore_data["구매비중"]["주차별"].get(selected2, {})
            
            if display_data2:
                # 테이블 생성
                rows = []
                for agency, data in display_data2.items():
                    row = {
                        "거래선": agency,
                        "신규구매고객": f"{data.get('신규구매고객수', 0):,}",
                        "신규구매비중(%)": f"{data.get('신규구매비중', 0):.2f}%",
                        "재구매고객": f"{data.get('재구매고객수', 0):,}",
                        "재구매비중(%)": f"{data.get('재구매비중', 0):.2f}%",
                    }
                    if data_type2 == "월별":
                        row["신규전월비(%)"] = f"{data.get('신규구매전월비', 0):.2f}%"
                        row["재전월비(%)"] = f"{data.get('재구매전월비', 0):.2f}%"
                    else:
                        row["신규전주비(%)"] = f"{data.get('신규구매전주비', 0):.2f}%"
                        row["재전주비(%)"] = f"{data.get('재구매전주비', 0):.2f}%"
                    rows.append(row)
                
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("스마트스토어 데이터가 없습니다")
    elif current_page == "프리미엄":
        st.subheader("💎 프리미엄 제품별 실적")
        
        # STAR 데이터 로드
        star_data, star_errors = load_star_xlsx(Path(__file__).resolve().parent)
        
        if star_data:
            st.markdown("### 🎯 STAR 기반 프리미엄 제품 S/I, S/O 실적 (마감분은 실적/잔여기간은 FCST)")
            
            scope_type = st.radio("데이터 종류", ["월별", "주차별"], key="premium_star_scope", horizontal=True)
            if scope_type == "월별":
                keys = sorted(
                    set(star_data.get("수량", {}).get("월별", {}).keys()) | set(star_data.get("금액", {}).get("월별", {}).keys()),
                    key=star_month_sort_key, reverse=True)
            else:
                keys = sorted(
                    set(star_data.get("수량", {}).get("주차별", {}).keys()) | set(star_data.get("금액", {}).get("주차별", {}).keys()),
                    key=star_week_sort_key, reverse=True)
                st.caption("STAR 원본 자체 주차 번호이며, PP3G 업무주차표(W번호)와 월경계 주차에서 다를 수 있습니다.")
            
            if keys:
                selected_scope = st.selectbox("대상 월" if scope_type == "월별" else "대상 주차", keys, key="premium_star_scope_value")
                if scope_type == "월별":
                    month_num = star_month_sort_key(selected_scope)
                    prev_scope = f"{month_num - 1}월" if month_num > 1 else None
                else:
                    weeks_sorted_asc = sorted(
                        set(star_data.get("수량", {}).get("주차별", {}).keys()) | set(star_data.get("금액", {}).get("주차별", {}).keys()),
                        key=star_week_sort_key)
                    idx = weeks_sorted_asc.index(selected_scope) if selected_scope in weeks_sorted_asc else -1
                    prev_scope = weeks_sorted_asc[idx - 1] if idx > 0 else None
                render_star_section(st, star_data, scope_type, selected_scope, prev_scope)
            else:
                st.info("STAR 품목별 실적 데이터가 없습니다.")
            
            st.markdown("---")
        
        if star_errors:
            with st.expander("STAR 데이터 읽기 안내"):
                for error in star_errors:
                    st.warning(error)
        
        # 기존 프리미엄 데이터
        premium_data = {}
        premium_products = ['냉장고', '세탁기', '식기세척기', '정수기']
        
        for product in premium_products:
            try:
                with open(f'premium_{product}.json', 'r', encoding='utf-8') as f:
                    premium_data[product] = json.load(f)
            except:
                premium_data[product] = {}
        
        if premium_data:
            # 제품별 Expander
            for product in premium_products:
                if premium_data[product]:
                    with st.expander(f"💎 {product}", expanded=False):
                        # 월별 선택
                        months = sorted([m for m in premium_data[product].keys() if isinstance(premium_data[product].get(m), dict)], reverse=True)
                        
                        if months:
                            selected_month = st.selectbox(f"{product} 월 선택", months, key=f"prem_{product}_month")
                            
                            if selected_month in premium_data[product]:
                                month_data = premium_data[product][selected_month]
                                
                                # 테이블 생성
                                st.markdown(f"### {selected_month} {product} 실적")
                                
                                html = f"""
                                <style>
                                    .prem-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
                                    .prem-table th, .prem-table td {{ border: 1px solid #d0d0d0; padding: 8px 6px; text-align: center; height: 26px; }}
                                    .prem-header {{ background: #9966cc; color: white; font-weight: 600; }}
                                    .prem-total {{ background: #fff2cc; font-weight: 600; border-top: 2px solid #333; }}
                                    .prem-data {{ background: #f9f9f9; }}
                                    .prem-data:nth-child(even) {{ background: #ffffff; }}
                                    .prem-agency {{ text-align: left; font-weight: 500; padding-left: 8px; }}
                                    .prem-number {{ text-align: right; padding-right: 4px; font-family: 'Courier New', monospace; }}
                                </style>
                                <table class="prem-table">
                                    <thead>
                                        <tr>
                                            <th class="prem-header">거래선</th>
                                            <th class="prem-header">매출(백만)</th>
                                            <th class="prem-header">판매량</th>
                                            <th class="prem-header">전월비</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                """
                                
                                # 합계 행
                                if '합계' in month_data:
                                    total = month_data['합계']
                                    html += f"""
                                        <tr class="prem-total">
                                            <td class="prem-agency">합계</td>
                                            <td class="prem-number">{total.get('매출', 0):,.1f}</td>
                                            <td class="prem-number">{total.get('판매량', 0):,}</td>
                                            <td class="prem-number">{total.get('전월비', '0'):}</td>
                                        </tr>
                                    """
                                
                                # 거래선별 행
                                for agency in AGENCIES:
                                    if agency in month_data and agency != '합계':
                                        data = month_data[agency]
                                        html += f"""
                                            <tr class="prem-data">
                                                <td class="prem-agency">{agency}</td>
                                                <td class="prem-number">{data.get('매출', 0):,.1f}</td>
                                                <td class="prem-number">{data.get('판매량', 0):,}</td>
                                                <td class="prem-number">{data.get('전월비', '0'):}</td>
                                            </tr>
                                        """
                                
                                html += """
                                    </tbody>
                                </table>
                                """
                                st.markdown(html, unsafe_allow_html=True)
        else:
            st.warning("프리미엄 데이터가 없습니다")
    
    # 거래선 현황
    elif current_page == "거래선현황":
        st.subheader("📋 거래선 현황")
        
        # weekly_data.json 로드
        weekly_data_list = []
        if os.path.exists("weekly_data.json"):
            try:
                with open("weekly_data.json", "r", encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    weekly_data_list = loaded_data if isinstance(loaded_data, list) else []
            except:
                weekly_data_list = []
        
        # 거래선별 데이터 필터링
        selected_agency = st.selectbox("거래선 선택", AGENCIES, key="view_agency")
        
        # 선택한 거래선의 데이터만 필터링
        agency_data = [item for item in weekly_data_list if item.get("거래선") == selected_agency]
        
        if agency_data:
            # 주차명 정렬 함수 (숫자만 추출해서 정렬)
            def get_week_num(week_str):
                num_str = ''.join(c for c in week_str if c.isdigit())
                return int(num_str) if num_str else 0
            
            # 최신 주차순으로 정렬
            agency_data_sorted = sorted(agency_data, key=lambda x: (get_week_num(x.get("주차", "W00")), x.get("월", "")), reverse=True)
            
            st.write(f"**총 {len(agency_data_sorted)}개 주차 데이터**")
            st.write("")
            
            # 순회용 인덱스
            for idx, data in enumerate(agency_data_sorted):
                week_raw = data.get("주차", "")
                month = data.get("월", "")
                
                # 주차명 정리: 숫자만 추출 후 W + 숫자로 표시
                week_num = ''.join(c for c in week_raw if c.isdigit())
                week_clean = f"W{week_num}" if week_num else week_raw
                
                week_display = f"**{week_clean}** ({month})"
                unique_key = f"{selected_agency}_{week_clean}_{month}_{idx}"
                
                # 수정 모드 확인
                is_edit_mode = st.session_state.get("edit_mode", False) and st.session_state.get("edit_key", "") == unique_key
                
                with st.expander(week_display, expanded=is_edit_mode):
                    if is_edit_mode:
                        # ===== 수정 FORM =====
                        st.subheader("✏️ 데이터 수정")
                        
                        with st.form(f"edit_form_{unique_key}"):
                            # 1. 네이버 스마트 스토어
                            st.write("**1️⃣ 네이버 스마트 스토어**")
                            ss = data.get("네이버스마트스토어", {})
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                ss_interest = st.number_input("신규 관심고객수", min_value=0, step=1, value=max(0, ss.get('신규관심고객수', 0)), key=f"edit_ss_interest_{unique_key}")
                            with col2:
                                ss_new = st.number_input("신규구매 구매자수", min_value=0, step=1, value=max(0, ss.get('신규구매구매자수', 0)), key=f"edit_ss_new_{unique_key}")
                            with col3:
                                ss_repurchase = st.number_input("재구매 구매자수", min_value=0, step=1, value=max(0, ss.get('재구매구매자수', 0)), key=f"edit_ss_repurchase_{unique_key}")
                            ss_activity = st.text_area("마케팅활동", value=ss.get('마케팅활동', ''), height=50, key=f"edit_ss_activity_{unique_key}")
                            
                            st.write("---")
                            
                            # 2. 어필리에이트
                            st.write("**2️⃣ 어필리에이트**")
                            
                            sc = data.get("쇼핑커넥트", {})
                            st.write("🔹 **쇼핑커넥트**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                sc_creator = st.number_input("크리에이터 운영 수", min_value=0, step=1, value=max(0, sc.get('크리에이터운영수', 0)), key=f"edit_sc_creator_{unique_key}")
                            with col2:
                                sc_model = st.number_input("운영 모델 수", min_value=0, step=1, value=max(0, sc.get('운영모델수', 0)), key=f"edit_sc_model_{unique_key}")
                            with col3:
                                sc_visits = st.number_input("유입수", min_value=0, step=1, value=max(0, sc.get('유입수', 0)), key=f"edit_sc_visits_{unique_key}")
                            col1, col2 = st.columns(2)
                            with col1:
                                sc_orders = st.number_input("상품주문건수", min_value=0, step=1, value=max(0, sc.get('상품주문건수', 0)), key=f"edit_sc_orders_{unique_key}")
                            with col2:
                                sc_amount = st.number_input("주문금액 (전체 금액)", min_value=0, step=1, value=max(0, int(sc.get('주문금액', 0) * 1000000)), key=f"edit_sc_amount_{unique_key}")
                            sc_activity = st.text_area("마케팅활동", value=sc.get('마케팅활동', ''), height=40, key=f"edit_sc_activity_{unique_key}")
                            
                            st.write("")
                            
                            cj = data.get("공동구매", {})
                            st.write("🔹 **공동구매**")
                            col1, col2 = st.columns(2)
                            with col1:
                                cj_creator = st.number_input("크리에이터 운영 수", min_value=0, step=1, value=max(0, cj.get('크리에이터운영수', 0)), key=f"edit_cj_creator_{unique_key}")
                            with col2:
                                cj_model = st.number_input("운영 모델 수", min_value=0, step=1, value=max(0, cj.get('운영모델수', 0)), key=f"edit_cj_model_{unique_key}")
                            col1, col2 = st.columns(2)
                            with col1:
                                cj_orders = st.number_input("상품주문건수", min_value=0, step=1, value=max(0, cj.get('상품주문건수', 0)), key=f"edit_cj_orders_{unique_key}")
                            with col2:
                                cj_amount = st.number_input("주문금액 (전체 금액)", min_value=0, step=1, value=max(0, int(cj.get('주문금액', 0) * 1000000)), key=f"edit_cj_amount_{unique_key}")
                            cj_activity = st.text_area("마케팅활동", value=cj.get('마케팅활동', ''), height=40, key=f"edit_cj_activity_{unique_key}")
                            
                            st.write("---")
                            
                            # 3. AI 라이브
                            st.write("**🎥 3️⃣ AI 라이브**")
                            live = data.get("AI라이브", {})
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                live_count = st.number_input("방송횟수", min_value=0, step=1, value=max(0, live.get('방송횟수', 0)), key=f"edit_live_count_{unique_key}")
                            with col2:
                                live_sale = st.number_input("방송매출 (전체 금액)", min_value=0, step=1, value=max(0, int(live.get('방송매출', 0) * 1000000)), key=f"edit_live_sale_{unique_key}")
                            with col3:
                                live_cost = st.number_input("소요비용 (전체 금액)", min_value=0, step=1, value=max(0, int(live.get('소요비용', 0) * 1000000)), key=f"edit_live_cost_{unique_key}")
                            live_activity = st.text_area("마케팅활동", value=live.get('마케팅활동', ''), height=40, key=f"edit_live_activity_{unique_key}")
                            
                            st.write("---")
                            
                            if st.form_submit_button("💾 저장", use_container_width=True):
                                # 데이터 업데이트
                                data["네이버스마트스토어"] = {
                                    "신규관심고객수": ss_interest,
                                    "신규구매구매자수": ss_new,
                                    "재구매구매자수": ss_repurchase,
                                    "마케팅활동": ss_activity
                                }
                                data["쇼핑커넥트"] = {
                                    "크리에이터운영수": sc_creator,
                                    "운영모델수": sc_model,
                                    "유입수": sc_visits,
                                    "상품주문건수": sc_orders,
                                    "주문금액": round(sc_amount / 1000000, 2),
                                    "마케팅활동": sc_activity
                                }
                                data["공동구매"] = {
                                    "크리에이터운영수": cj_creator,
                                    "운영모델수": cj_model,
                                    "상품주문건수": cj_orders,
                                    "주문금액": round(cj_amount / 1000000, 2),
                                    "마케팅활동": cj_activity
                                }
                                data["AI라이브"] = {
                                    "방송횟수": live_count,
                                    "방송매출": round(live_sale / 1000000, 2),
                                    "소요비용": round(live_cost / 1000000, 4),
                                    "마케팅활동": live_activity
                                }
                                
                                # weekly_data.json 업데이트
                                with open("weekly_data.json", "w", encoding='utf-8') as f:
                                    json.dump(weekly_data_list, f, ensure_ascii=False, indent=2)
                                
                                st.session_state.edit_mode = False
                                st.success(f"✅ {selected_agency} - {week_clean} ({month}) 데이터 저장됨!")
                                st.rerun()
                    
                    else:
                        # ===== 조회 모드 =====
                        # 1. 네이버 스마트 스토어
                        st.subheader("1️⃣ 네이버 스마트 스토어")
                        ss = data.get("네이버스마트스토어", {})
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("신규 관심고객", f"{ss.get('신규관심고객수', 0):,}")
                        with col2:
                            st.metric("신규구매 구매자", f"{ss.get('신규구매구매자수', 0):,}")
                        with col3:
                            st.metric("재구매 구매자", f"{ss.get('재구매구매자수', 0):,}")
                        
                        if ss.get("마케팅활동"):
                            st.info(f"📌 **마케팅활동**: {ss.get('마케팅활동')}")
                        
                        st.write("")
                        
                        # 2. 어필리에이트
                        st.subheader("2️⃣ 어필리에이트")
                        
                        sc = data.get("쇼핑커넥트", {})
                        col_sc1, col_sc2 = st.columns(2)
                        with col_sc1:
                            st.write("🔹 **쇼핑커넥트**")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("크리에이터", f"{sc.get('크리에이터운영수', 0)}")
                                st.metric("모델", f"{sc.get('운영모델수', 0)}")
                            with col2:
                                st.metric("유입수", f"{sc.get('유입수', 0):,}")
                                st.metric("주문", f"{sc.get('상품주문건수', 0)}")
                            st.metric("금액", f"{sc.get('주문금액', 0):.2f}백만")
                            if sc.get("마케팅활동"):
                                st.caption(f"📌 {sc.get('마케팅활동')}")
                        
                        cj = data.get("공동구매", {})
                        with col_sc2:
                            st.write("🔹 **공동구매**")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("크리에이터", f"{cj.get('크리에이터운영수', 0)}")
                                st.metric("모델", f"{cj.get('운영모델수', 0)}")
                            with col2:
                                st.metric("주문", f"{cj.get('상품주문건수', 0)}")
                            st.metric("금액", f"{cj.get('주문금액', 0):.2f}백만")
                            if cj.get("마케팅활동"):
                                st.caption(f"📌 {cj.get('마케팅활동')}")
                        
                        st.write("")
                        
                        # 3. AI 라이브
                        st.subheader("🎥 3️⃣ AI 라이브")
                        live = data.get("AI라이브", {})
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("방송횟수", f"{live.get('방송횟수', 0)}")
                        with col2:
                            st.metric("방송매출", f"{live.get('방송매출', 0):.2f}백만")
                        with col3:
                            st.metric("소요비용", f"{live.get('소요비용', 0):.4f}백만")
                        
                        if live.get("마케팅활동"):
                            st.info(f"📌 **마케팅활동**: {live.get('마케팅활동')}")
                        
                        st.write("")
                        
                        # 4. 당주 주요활동
                        st.subheader("🎯 당주 주요활동")
                        activity = data.get("당주주요활동", {})
                        
                        activity_items = [
                            ("📌 AI 라이브 효율 증대", "AI라이브효율증대"),
                            ("📌 어필리에이트 내재화", "어필리에이트내재화"),
                            ("📌 구독활성화", "구독활성화"),
                            ("📌 기타 신규 프로젝트", "기타신규프로젝트")
                        ]
                        
                        for label, key in activity_items:
                            if activity.get(key):
                                with st.expander(label, key=f"act_{key}_{unique_key}"):
                                    st.write(activity.get(key))
                        
                        st.write("")
                        st.subheader("⚙️ 데이터 관리")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✏️ 수정", key=f"edit_{unique_key}", use_container_width=True):
                                st.session_state.edit_mode = True
                                st.session_state.edit_key = unique_key
                                st.rerun()
                        
                        with col2:
                            if st.button("🗑️ 삭제", key=f"delete_{unique_key}", use_container_width=True):
                                weekly_data_list.remove(data)
                                with open("weekly_data.json", "w", encoding='utf-8') as f:
                                    json.dump(weekly_data_list, f, ensure_ascii=False, indent=2)
                                st.success(f"✅ {selected_agency} - {week_clean} ({month}) 데이터 삭제됨!")
                                st.rerun()
        else:
            st.info(f"등록된 데이터가 없습니다")
    
    # 담당자 피드백
    elif current_page == "담당자피드백":
        st.subheader("담당자 피드백")
        
        # weekly_data.json 로드
        weekly_data_list = []
        if os.path.exists("weekly_data.json"):
            try:
                with open("weekly_data.json", "r", encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    weekly_data_list = loaded_data if isinstance(loaded_data, list) else []
            except:
                weekly_data_list = []
        
        # feedback.json 로드
        feedback_data = {}
        if os.path.exists("feedback.json"):
            try:
                with open("feedback.json", "r", encoding='utf-8') as f:
                    feedback_data = json.load(f)
            except:
                feedback_data = {}
        
        # 거래선별 필터링
        selected_agency = st.selectbox("거래선 선택", AGENCIES, key="feedback_agency")
        
        # 선택한 거래선의 데이터만 필터링
        agency_data = [item for item in weekly_data_list if item.get("거래선") == selected_agency]
        
        if agency_data:
            # 주차명 정렬 함수
            def get_week_num(week_str):
                num_str = ''.join(c for c in week_str if c.isdigit())
                return int(num_str) if num_str else 0
            
            # 최신 주차순으로 정렬
            agency_data_sorted = sorted(agency_data, key=lambda x: (get_week_num(x.get("주차", "W00")), x.get("월", "")), reverse=True)
            
            for idx, data in enumerate(agency_data_sorted):
                week_raw = data.get("주차", "")
                month = data.get("월", "")
                
                # 주차명 정리
                week_num = ''.join(c for c in week_raw if c.isdigit())
                week_clean = f"W{week_num}" if week_num else week_raw
                week_key = f"{selected_agency}_{week_clean}_{month}_{idx}"
                
                with st.expander(f"**{week_clean}** ({month})", expanded=False):
                    # ===== 데이터 대시보드 =====
                    st.subheader("📊 입력 데이터 & 분석")
                    st.divider()
                    
                    # 1. 스마트스토어
                    st.write("**🛒 네이버 스마트 스토어**")
                    ss = data.get("네이버스마트스토어", {})
                    
                    col_ss1, col_ss2 = st.columns([2, 1])
                    with col_ss1:
                        # 테이블
                        ss_data = {
                            "항목": ["신규 관심고객", "신규구매 구매자", "재구매 구매자", "합계"],
                            "수량": [
                                ss.get('신규관심고객수', 0),
                                ss.get('신규구매구매자수', 0),
                                ss.get('재구매구매자수', 0),
                                ss.get('신규관심고객수', 0) + ss.get('신규구매구매자수', 0) + ss.get('재구매구매자수', 0)
                            ]
                        }
                        ss_df = pd.DataFrame(ss_data)
                        st.dataframe(ss_df, use_container_width=True, hide_index=True)
                    
                    with col_ss2:
                        # 파이 차트 (구매 비율)
                        if ss.get('신규구매구매자수', 0) > 0 or ss.get('재구매구매자수', 0) > 0:
                            pie_data = {
                                "유형": ["신규구매", "재구매"],
                                "수량": [ss.get('신규구매구매자수', 0), ss.get('재구매구매자수', 0)]
                            }
                            pie_df = pd.DataFrame(pie_data)
                            pie_chart = px.pie(pie_df, names="유형", values="수량", title="구매자 구성")
                            st.plotly_chart(pie_chart, use_container_width=True)
                    
                    if ss.get("마케팅활동"):
                        st.info(f"📌 활동: {ss.get('마케팅활동')}")
                    
                    st.divider()
                    
                    # 2. 어필리에이트
                    st.write("**📱 어필리에이트**")
                    sc = data.get("쇼핑커넥트", {})
                    cj = data.get("공동구매", {})
                    
                    col_af1, col_af2 = st.columns([1, 2])
                    
                    with col_af1:
                        # 테이블
                        af_data = {
                            "채널": ["쇼핑커넥트", "공동구매"],
                            "크리에이터": [sc.get('크리에이터운영수', 0), cj.get('크리에이터운영수', 0)],
                            "주문건수": [sc.get('상품주문건수', 0), cj.get('상품주문건수', 0)],
                            "금액(백만)": [f"{sc.get('주문금액', 0):.1f}", f"{cj.get('주문금액', 0):.1f}"]
                        }
                        af_df = pd.DataFrame(af_data)
                        st.dataframe(af_df, use_container_width=True, hide_index=True)
                    
                    with col_af2:
                        # 막대 차트
                        chart_data = {
                            "채널": ["쇼핑커넥트", "공동구매"],
                            "주문건수": [sc.get('상품주문건수', 0), cj.get('상품주문건수', 0)],
                            "금액(백만)": [sc.get('주문금액', 0), cj.get('주문금액', 0)]
                        }
                        chart_df = pd.DataFrame(chart_data)
                        bar_chart = px.bar(chart_df, x="채널", y=["주문건수", "금액(백만)"], barmode="group", title="쇼핑커넥트 vs 공동구매")
                        st.plotly_chart(bar_chart, use_container_width=True)
                    
                    if sc.get("마케팅활동") or cj.get("마케팅활동"):
                        st.info(f"📌 쇼핑커넥트: {sc.get('마케팅활동', '-')} | 공동구매: {cj.get('마케팅활동', '-')}")
                    
                    st.divider()
                    
                    # 3. AI 라이브
                    st.write("**🎥 AI 라이브**")
                    live = data.get("AI라이브", {})
                    
                    col_live1, col_live2 = st.columns([2, 1])
                    
                    with col_live1:
                        # 테이블
                        live_cost = live.get('소요비용', 0.1)
                        live_efficiency = live.get('방송매출', 0) / live_cost if live_cost > 0 else 0
                        
                        live_data = {
                            "항목": ["방송횟수", "방송매출(백만)", "소요비용(백만)", "효율(매출/비용)"],
                            "값": [
                                live.get('방송횟수', 0),
                                f"{live.get('방송매출', 0):.1f}",
                                f"{live_cost:.2f}",
                                f"{live_efficiency:.2f}"
                            ]
                        }
                        live_df = pd.DataFrame(live_data)
                        st.dataframe(live_df, use_container_width=True, hide_index=True)
                    
                    with col_live2:
                        if live.get('방송횟수', 0) > 0:
                            # 효율 게이지
                            efficiency_color = "🟢" if live_efficiency > 1 else "🟡" if live_efficiency > 0.5 else "🔴"
                            st.metric("효율도", f"{live_efficiency:.2f}배", delta=f"{efficiency_color} {'우수' if live_efficiency > 1 else '보통' if live_efficiency > 0.5 else '개선필요'}")
                    
                    if live.get("마케팅활동"):
                        st.info(f"📌 활동: {live.get('마케팅활동')}")
                    
                    st.divider()
                    
                    # ===== 담당자 피드백 입력 =====
                    st.subheader("📝 담당자 피드백")
                    
                    # 기존 피드백 로드
                    existing_feedback = feedback_data.get(week_key, {})
                    
                    with st.form(f"feedback_form_{week_key}"):
                        # 각 영역별 피드백
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**🛒 네이버 스마트 스토어**")
                            ss_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("네이버스마트스토어", ""),
                                height=70,
                                key=f"ss_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        with col2:
                            st.write("**📱 어필리에이트**")
                            af_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("어필리에이트", ""),
                                height=70,
                                key=f"af_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**🎥 AI 라이브**")
                            live_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("AI라이브", ""),
                                height=70,
                                key=f"live_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        with col2:
                            st.write("**🎯 당주 주요활동**")
                            activity_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("당주주요활동", ""),
                                height=70,
                                key=f"activity_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        st.write("---")
                        
                        if st.form_submit_button("💾 피드백 저장", use_container_width=True):
                            # 피드백 데이터 저장
                            feedback_data[week_key] = {
                                "거래선": selected_agency,
                                "주차": week_clean,
                                "월": month,
                                "네이버스마트스토어": ss_feedback,
                                "어필리에이트": af_feedback,
                                "AI라이브": live_feedback,
                                "당주주요활동": activity_feedback,
                                "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # feedback.json에 저장
                            with open("feedback.json", "w", encoding='utf-8') as f:
                                json.dump(feedback_data, f, ensure_ascii=False, indent=2)
                            
                            st.success("✅ 피드백이 저장되었습니다!")
                            st.rerun()
                    
                    st.write("")
        else:
            st.info(f"등록된 데이터가 없습니다")

# 메인
if st.session_state.user_name is None:
    login_page()
else:
    dashboard()