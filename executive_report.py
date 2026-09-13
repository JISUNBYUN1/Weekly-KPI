"""PP3G 월간·주간 분석 및 품목별 실적 보고 모듈."""
import json
import math
import re
from pathlib import Path

import pandas as pd
import openpyxl

AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]
CHANNELS = ("네이버스마트스토어", "쇼핑커넥트", "공동구매", "AI라이브")
STYLE = """
<style>
:root {--ink:#152a45;--muted:#65758b;--line:#e1e7ee;--accent:#164c96;}
.stApp {background:#f4f6f9;color:var(--ink);}
html,body,[class*="css"],button,input,textarea {font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;}
.block-container {max-width:1480px;padding-top:2.4rem;padding-bottom:4rem;}
h1 {font-size:2rem!important;letter-spacing:-.055em;font-weight:700!important;} h2 {font-size:1.35rem!important;letter-spacing:-.035em;} h3 {font-size:1.05rem!important;}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid var(--line);}
[data-testid="stSidebar"] .stButton>button {text-align:left;justify-content:flex-start;border:0;border-radius:7px;min-height:2.65rem;}
.stButton>button {border-radius:7px;border-color:#d3dce8;} .stButton>button[kind="primary"] {background:#164c96;color:white;}
[data-testid="stMetric"] {background:white;border:1px solid var(--line);border-top:3px solid var(--accent);padding:20px 22px;border-radius:8px;}
[data-testid="stMetricLabel"] {color:var(--muted);font-size:.85rem;} [data-testid="stMetricValue"] {color:var(--ink);font-size:2rem;}
[data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:8px;overflow:hidden;} [data-testid="stExpander"] {background:white;border-radius:8px;}
.stTabs [data-baseweb="tab-list"] {gap:24px;border-bottom:1px solid var(--line);}
.report-eyebrow {font-size:11px;letter-spacing:.16em;color:#64758a;font-weight:700;margin-bottom:8px;}
@media print {[data-testid="stSidebar"],header,footer,.stButton {display:none!important;}.stApp {background:#fff;}.block-container {padding:0;max-width:none;}}
</style>
"""


def load_star_xlsx(root):
    """STAR.xlsx 파일 로드 및 분석"""
    try:
        star_path = Path(root) / "STAR.xlsx"
        if not star_path.exists():
            return {}, []
        
        df = pd.read_excel(star_path, sheet_name=0)
        
        # 필요한 컬럼 확인
        required_cols = ['영업그룹', '기준품목', '주', '월', '메져_구분']
        if not all(col in df.columns for col in required_cols):
            return {}, [f"STAR.xlsx 필수 컬럼 부족: {required_cols}"]
        
        # 품목별, 주차별 S/I, S/O, FCST, RTF 데이터 구성
        result = {}
        for _, row in df.iterrows():
            product = row.get('기준품목', '미분류')
            week = row.get('주', 'W00')
            month = row.get('월', '')
            measure = row.get('메져_구분', '')
            
            key = f"{month}_{week}_{product}_{measure}"
            result[key] = {
                'S/I_FCST': row.get('◆_AP1_S/I FCST_예상', 0),
                'S/I_실적': row.get('◆_매출', 0),
                'S/O_FCST': row.get('◆_AP1_S/O FCST_예상', 0),
                'S/O_실적': row.get('◆_실판매_모바일/유통직판 포함', 0),
                'RTF_FCST': row.get('◆_AP1_RTF_예상', 0),
            }
        
        return result, []
    except Exception as e:
        return {}, [f"STAR.xlsx 로드 오류: {str(e)}"]


def read_json(root, filename, errors, default=None):
    path = Path(root) / filename
    if not path.exists():
        return {} if default is None else default
    try:
        with path.open(encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, ValueError) as error:
        errors.append(f"{filename}: {error}")
        return {} if default is None else default


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def strict_sum(values):
    values = list(values)
    return sum(values) if values and all(number(value) for value in values) else None


def shown(value, decimals=0):
    return f"{value:,.{decimals}f}" if number(value) else "미제공"


def week_key(value):
    match = re.fullmatch(r"W(\d{1,2})([AB]?)", value or "")
    return (int(match.group(1)), match.group(2)) if match else (-1, "")


def weeks_for_month(calendar, month):
    target = int(month.replace("월", ""))
    weeks = []
    for week, info in calendar.items():
        months = info.get("month", [])
        months = months if isinstance(months, list) else [months]
        if target in months:
            weeks.append(week if len(months) == 1 else week + ("A" if months.index(target) == 0 else "B"))
    return sorted(weeks, key=week_key, reverse=True)


def report_rows(live, affiliate, smart):
    rows = []
    for agency in AGENCIES:
        source = live.get(agency, {})
        channels = affiliate.get(agency, {})
        affiliate_sale = strict_sum(channels.get(channel, {}).get("주문금액") for channel in ("쇼핑커넥트", "공동구매"))
        rows.append({"거래선": agency,
                     "라이브 매출(백만)": source.get("방송매출") / 1e6 if number(source.get("방송매출")) else None,
                     "방송횟수": source.get("방송횟수"),
                     "어필리에이트 주문금액(백만)": affiliate_sale / 1e6 if affiliate_sale is not None else None,
                     "신규 관심고객": smart.get(agency, {}).get("신규관심고객수")})
    return rows


def activities(records, agency, week=None):
    result = []
    for record in records:
        record_week = record.get("주차_표시", record.get("주차", ""))
        if record.get("거래선") != agency or (week and record_week != week):
            continue
        for channel in CHANNELS:
            value = record.get(channel, {}).get("마케팅활동", "")
            if isinstance(value, str) and value.strip():
                result.append((record_week, channel, value.strip()))
        for subject, value in record.get("당주주요활동", {}).items():
            if isinstance(value, str) and value.strip():
                result.append((record_week, subject, value.strip()))
    return result


def infer(agency, row, weekly_smart, activity_rows, scope):
    observations, proposals = [], []
    if number(row["라이브 매출(백만)"]) and row["라이브 매출(백만)"] > 0:
        observations.append(f"라이브 매출 {row['라이브 매출(백만)']:,.2f}백만원이 {scope}에 기록됐습니다.")
        proposals.append("방송 횟수·시간대·상품 구성을 다음 기간에도 기록해 회차당 매출을 비교하세요.")
    if number(row["어필리에이트 주문금액(백만)"]) and row["어필리에이트 주문금액(백만)"] > 0:
        observations.append(f"어필리에이트 주문금액 {row['어필리에이트 주문금액(백만)']:,.2f}백만원이 기록됐습니다.")
        proposals.append("채널별 유입·주문·금액을 함께 입력해 전환 개선 활동을 판단하세요.")
    if number(row["신규 관심고객"]):
        direction = "순증" if row["신규 관심고객"] > 0 else "순감" if row["신규 관심고객"] < 0 else "변동 없음"
        observations.append(f"신규 관심고객은 {abs(row['신규 관심고객']):,.0f}명 {direction}입니다.")
        if row["신규 관심고객"] <= 0:
            proposals.append("관심고객 감소 원인과 유입 경로를 확인하고 회복 목표를 설정하세요.")
    change = weekly_smart.get("전주비") if isinstance(weekly_smart, dict) else None
    if number(change):
        observations.append(f"선택 주차 신규 관심고객은 전주 대비 {change:,.1f}% 변동했습니다.")
    if activity_rows:
        labels = ", ".join(dict.fromkeys(channel for _, channel, _ in activity_rows))
        observations.append(f"기록 활동: {labels}. 해당 기간 실적과의 동행은 관찰되나 인과관계는 검증 전입니다.")
        proposals.append("차주에도 활동별 목표 지표와 결과를 함께 기록하세요.")
    else:
        proposals.append("차주 활동·목표 지표·결과를 입력해 성과 분석 근거를 확보하세요.")
    return observations, list(dict.fromkeys(proposals))


def render_month_week_analysis(st, root):
    errors = []
    live = read_json(root, "live_commerce_data.json", errors)
    affiliate = read_json(root, "affiliate_data.json", errors)
    smart = read_json(root, "smartstore_data.json", errors)
    weekly = read_json(root, "weekly_data.json", errors, [])
    calendar = read_json(root, "weeks_2026.json", errors)
    if not isinstance(weekly, list):
        weekly = []; errors.append("weekly_data.json 형식을 확인해주세요.")
    months = [f"{m}월" for m in range(12, 0, -1)]
    latest = next((month for month in months if live.get("월별", {}).get(month)), "8월")
    col1, col2 = st.columns(2)
    with col1:
        month = st.selectbox("대상 월", months, index=months.index(latest), key="analysis_month")
    with col2:
        selected_week = st.selectbox("대상 주차", ["월간"] + weeks_for_month(calendar, month), key=f"analysis_week_{month}")
    monthly = selected_week == "월간"
    live_data = live.get("월별" if monthly else "주차별", {}).get(month if monthly else selected_week, {})
    affiliate_data = affiliate.get("월별" if monthly else "주차별", {}).get(month if monthly else selected_week, {})
    smart_data = smart.get("신규관심고객", {}).get("월별" if monthly else "주차별", {}).get(month if monthly else selected_week, {})
    rows = report_rows(live_data, affiliate_data, smart_data)
    scope = month if monthly else f"{month} {selected_week}"

    st.subheader(f"{scope} 핵심 실적")
    totals = [strict_sum(row[field] for row in rows) for field in ("라이브 매출(백만)", "어필리에이트 주문금액(백만)", "신규 관심고객")]
    for col, label, value, unit, precision in zip(st.columns(3), ["라이브커머스 매출", "어필리에이트 주문금액", "스마트스토어 신규 관심고객"], totals, ["백만원", "백만원", "명"], [2, 2, 0]):
        with col:
            st.metric(label, f"{shown(value, precision)} {unit}" if number(value) else "미제공")
    st.caption("실제 실적 RAW 형식이 확정되면 동일 기준으로 KPI에 연결합니다. 채널 간 금액은 합산하지 않습니다.")

    st.subheader("채널별 비교 분석")
    display = []
    for row in rows:
        item = {key: value if key == "거래선" else shown(value, 2 if "백만" in key else 0) for key, value in row.items()}
        activity_rows = activities(weekly, row["거래선"], None if monthly else selected_week)
        observations, _ = infer(row["거래선"], row, smart_data.get(row["거래선"], {}), activity_rows, scope)
        item["요약"] = " ".join(observations[:2]) if observations else "제공된 지표가 없습니다."
        display.append(item)
    st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)

    st.subheader("월간·주간 활동 분석")
    st.caption("활동과 실적이 같은 기간에 기록됐다는 관찰을 보여줍니다. 활동이 실적을 만들었다고 단정하지 않습니다.")
    for agency in AGENCIES:
        row = next(row for row in rows if row["거래선"] == agency)
        activity_rows = activities(weekly, agency, None if monthly else selected_week)
        observations, proposals = infer(agency, row, smart_data.get(agency, {}), activity_rows, scope)
        with st.expander(f"{agency} 분석"):
            st.write("**분석 요약**")
            for value in observations:
                st.write("• " + value)
            if activity_rows:
                st.write("**기록 활동**")
                for week, channel, value in activity_rows:
                    st.text(f"{week} / {channel}\n{value}")
            st.write("**다음 기간 제안**")
            for value in proposals:
                st.write("• " + value)

    st.subheader("거래선별 Action Item")
    target = st.selectbox("거래선 선택", AGENCIES, key=f"action_agency_{month}_{selected_week}")
    row = next(row for row in rows if row["거래선"] == target)
    _, proposals = infer(target, row, smart_data.get(target, {}), activities(weekly, target, None if monthly else selected_week), scope)
    st.dataframe(pd.DataFrame([{"우선순위": index + 1, "Action Item": value, "대상 기간": "차월" if monthly else "차주"} for index, value in enumerate(proposals)]), use_container_width=True, hide_index=True)
    if errors:
        with st.expander("데이터 읽기 안내"):
            for error in errors: st.error(error)


def collect_product_data(root):
    result, errors = {}, []
    for filename in ("bizplan_SOP.json", "bizplan_쿠팡.json", "bizplan_종합몰.json", "bizplan_홈쇼핑.json"):
        for channel, products in read_json(root, filename, errors).items():
            for product, models in products.items():
                for model in models.values():
                    for month, value in model.get("SALES", {}).items():
                        result.setdefault(product, {}).setdefault(month, {}).setdefault(channel, 0)
                        result[product][month][channel] += value if number(value) else 0
    return result, errors


def render_product_performance_with_star(st, root):
    """STAR.xlsx 기반 품목별 S/I, S/O, FCST, RTF 분석"""
    star_data, star_errors = load_star_xlsx(root)
    
    st.subheader("품목별 실적 분석 (RAW 데이터)")
    
    if not star_data:
        st.info("STAR.xlsx 품목별 실적 데이터가 없습니다.")
        for error in star_errors:
            st.error(error)
        return
    
    # 월 선택
    months = sorted(set(key.split('_')[0] for key in star_data.keys() if key.split('_')[0]))
    if not months:
        st.warning("사용 가능한 월 데이터가 없습니다.")
        return
    
    selected_month = st.selectbox("대상 월", months, key="product_star_month")
    
    # 선택한 월의 데이터 필터링
    month_data = {k: v for k, v in star_data.items() if k.startswith(f"{selected_month}_")}
    
    if not month_data:
        st.warning(f"{selected_month} 데이터가 없습니다.")
        return
    
    # 품목별 집계
    product_summary = {}
    for key, data in month_data.items():
        parts = key.split('_')
        if len(parts) >= 4:
            product = parts[2]
            if product not in product_summary:
                product_summary[product] = {
                    'S/I_FCST': 0, 'S/I_실적': 0,
                    'S/O_FCST': 0, 'S/O_실적': 0,
                    'RTF_FCST': 0
                }
            for k, v in data.items():
                if k in product_summary[product]:
                    product_summary[product][k] += v if number(v) else 0
    
    # 테이블 구성
    display_rows = []
    for product, metrics in sorted(product_summary.items()):
        si_rate = (metrics['S/I_실적'] / metrics['S/I_FCST'] * 100) if metrics['S/I_FCST'] > 0 else 0
        so_rate = (metrics['S/O_실적'] / metrics['S/O_FCST'] * 100) if metrics['S/O_FCST'] > 0 else 0
        
        display_rows.append({
            "품목": product,
            "S/I FCST": f"{metrics['S/I_FCST']:,.0f}",
            "S/I 실적": f"{metrics['S/I_실적']:,.0f}",
            "S/I 달성율(%)": f"{si_rate:.1f}",
            "S/O FCST": f"{metrics['S/O_FCST']:,.0f}",
            "S/O 실적": f"{metrics['S/O_실적']:,.0f}",
            "S/O 달성율(%)": f"{so_rate:.1f}",
            "RTF FCST": f"{metrics['RTF_FCST']:,.0f}"
        })
    
    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
    
    if star_errors:
        with st.expander("데이터 읽기 안내"):
            for error in star_errors:
                st.error(error)


def render_product_performance(st, root):
    data, errors = collect_product_data(root)
    st.subheader("품목별 실적")
    if not data:
        st.info("품목별 실적 데이터가 없습니다."); return
    product = st.selectbox("품목", ["전체"] + sorted(data), key="product_select")
    month = st.selectbox("대상 월", [f"{m}월" for m in range(12, 0, -1)], key="product_month")
    items = sorted(data) if product == "전체" else [product]
    channel_rows = [{"거래선": channel, "실적(수량)": sum(data[item].get(month, {}).get(channel, 0) for item in items)}
                    for channel in sorted({channel for item in items for values in data[item].values() for channel in values})]
    trend = [{"월": f"{m}월", "실적(수량)": sum(sum(data[item].get(f"{m}월", {}).values()) for item in items)} for m in range(1, 13)]
    left, right = st.columns(2)
    with left:
        st.metric(f"{month} {product} 실적", f"{sum(row['실적(수량)'] for row in channel_rows):,.0f}")
        st.dataframe(pd.DataFrame(channel_rows), use_container_width=True, hide_index=True)
    with right:
        st.bar_chart(pd.DataFrame(channel_rows).set_index("거래선"), color="#164c96", height=300)
    st.subheader("연간 월간 추이")
    st.line_chart(pd.DataFrame(trend).set_index("월"), color="#164c96", height=300)
    st.caption("현재 원본은 채널별·월별 품목 실적입니다. 주차별 품목 실적 파일이 추가되면 같은 화면에 주간 추이를 연결합니다.")
    for error in errors: st.error(error)