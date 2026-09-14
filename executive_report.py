"""PP3G 월간·주간 분석 및 품목별 실적 보고 모듈."""
import json
import math
import re
from pathlib import Path

import pandas as pd

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
[data-testid="stDataFrame"] * {text-align:center!important;}
.stTabs [data-baseweb="tab-list"] {gap:24px;border-bottom:1px solid var(--line);}
.report-eyebrow {font-size:11px;letter-spacing:.16em;color:#64758a;font-weight:700;margin-bottom:8px;}
@media print {[data-testid="stSidebar"],header,footer,.stButton {display:none!important;}.stApp {background:#fff;}.block-container {padding:0;max-width:none;}}
</style>
"""




STAR_METRIC_COLUMNS = {
    'S/I': '◆_AP1_S/I FCST_예상',
    'S/O': '◆_AP1_S/O FCST_예상',
    'RTF': '◆_AP1_RTF_예상',
}
_STAR_MONTH_RE = re.compile(r"(\d{2})Y(\d{2})M")
_STAR_WEEK_RE = re.compile(r"(\d{2})Y(\d{2})W([AB]?)")

# STAR 원본은 'FCST_LATEST_VER'(최신 계획치) 단일 값이며, 마감된 과거 주차는 실적과
# 동일해지고 아직 지나지 않은 주차는 예측치 그대로입니다. 확인 결과 STAR 36주는
# A(8/30-31)/B(9/1-5)로 분할되고 그 다음 37주가 9/6-9/12로 정확히 떨어져,
# 사용자가 알려준 '9/12 마감' 기준과 정확히 일치합니다. 따라서 37주까지는 실적,
# 38주부터는 FCST(예측)로 구분합니다. 이 컷오프는 데이터 갱신 시 조정이 필요합니다.
STAR_ACTUAL_CUTOFF_WEEK = 37


def _star_status(week_num, force_status=None):
    if force_status:
        return force_status
    return "실적" if week_num <= STAR_ACTUAL_CUTOFF_WEEK else "FCST"


def _read_star_dataframe(csv_path, xlsx_path):
    if csv_path.exists():
        return pd.read_csv(csv_path, encoding="utf-8-sig")
    if xlsx_path.exists():
        # 2025 STAR는 상단에 안내 행이 있고 8번째 행이 헤더다. 향후 양식이
        # 바뀌어도 '기준품목' 헤더를 기준으로 찾아 전년 비교가 끊기지 않게 한다.
        preview = pd.read_excel(xlsx_path, sheet_name=0, header=None, nrows=20, engine='openpyxl')
        header_row = next((idx for idx in preview.index if "기준품목" in preview.iloc[idx].astype(str).tolist()), 0)
        return pd.read_excel(xlsx_path, sheet_name=0, header=header_row, engine='openpyxl')
    return None


def _parse_star_dataframe(df, force_status=None):
    """STAR 원본 DataFrame -> {"수량": {...}, "금액": {...}} 구조.
    force_status를 주면(예: 전년도 참조 데이터) 실적/FCST 컷오프 없이 모두 해당 상태로 집계합니다."""
    result = {"수량": {"월별": {}, "주차별": {}}, "금액": {"월별": {}, "주차별": {}}}
    for _, row in df.iterrows():
        product = row.get('기준품목')
        if not isinstance(product, str) or not product.strip():
            continue
        measure_type = row.get('메져_구분')
        if measure_type not in ("수량", "금액"):
            continue
        channel = row.get('영업그룹')
        channel = channel if isinstance(channel, str) and channel.strip() else "미분류"

        m_match = _STAR_MONTH_RE.fullmatch(str(row.get('월(AB)', '')).strip())
        w_match = _STAR_WEEK_RE.fullmatch(str(row.get('주(AB)', '')).strip())
        if not m_match or not w_match:
            continue
        month_label = f"{int(m_match.group(2))}월"
        week_num = int(w_match.group(2))
        week_label = f"{week_num}주{w_match.group(3)}"
        status = _star_status(week_num, force_status)

        metrics = {}
        for key, col in STAR_METRIC_COLUMNS.items():
            value = row.get(col)
            metrics[key] = value if number(value) else 0

        attrs = {
            'SMSS_ATTR01': row.get('SMSS_ATTR01'),
            'SMSS_ATTR02': row.get('SMSS_ATTR02'),
            'SMSS_ATTR03': row.get('SMSS_ATTR03'),
        }

        bucket = result[measure_type]

        month_store = bucket["월별"].setdefault(
            month_label, {"실적": {"total": {}, "channel": {}, "rows": []}, "FCST": {"total": {}, "channel": {}, "rows": []}})[status]
        entry = month_store["total"].setdefault(product, {k: 0 for k in STAR_METRIC_COLUMNS})
        for key, value in metrics.items():
            entry[key] += value
        ch_entry = month_store["channel"].setdefault(product, {}).setdefault(channel, {k: 0 for k in STAR_METRIC_COLUMNS})
        for key, value in metrics.items():
            ch_entry[key] += value
        month_store["rows"].append((product, attrs, metrics))

        week_store = bucket["주차별"].setdefault(
            week_label, {"status": status, "month": month_label, "total": {}, "channel": {}, "rows": []})
        entry = week_store["total"].setdefault(product, {k: 0 for k in STAR_METRIC_COLUMNS})
        for key, value in metrics.items():
            entry[key] += value
        ch_entry = week_store["channel"].setdefault(product, {}).setdefault(channel, {k: 0 for k in STAR_METRIC_COLUMNS})
        for key, value in metrics.items():
            ch_entry[key] += value
        week_store["rows"].append((product, attrs, metrics))

    return result


def load_star_xlsx(root):
    """당해년도 STAR.csv(우선)/STAR.xlsx 및 전년도 STAR_2025.csv(우선)/STAR_2025.xlsx를 로드.
    반환 구조:
    {"수량": {
        "월별": {"8월": {"실적": {"total":{품목:{S/I,S/O,RTF}}, "channel":{...}, "rows":[(품목,attrs,metrics),...]},
                        "FCST": {...동일 구조...}}},
        "주차별": {"37주": {"status":"실적", "month":"9월", "total":{...}, "channel":{...}, "rows":[...]}},
        "prev_year_월별": {"8월": {품목:{S/I,S/O,RTF}}},   # 전년 동월 합산(실적 기준, 있는 경우만)
        "prev_year_주차별": {"37주": {품목:{...}}},          # 전년 동주차 합산(주차 번호 기준 매칭)
     }, "금액": {...동일 구조...}}
    채널은 STAR 원본의 '영업그룹'(SOP/종합몰/홈쇼핑/쿠팡)이며, 거래선(평강 등) 정보는
    STAR 원본에 없어 채널 단위로만 분해합니다. rows에는 SMSS_ATTR01/02/03 원본 속성을
    함께 보관해 프리미엄 세그먼트 등 추가 분류에 사용합니다. 전년비는 전년도 STAR
    데이터가 없으면 계산하지 않습니다(N/A). 주차 라벨은 STAR 원본 고유 번호이며 PP3G
    업무주차표(weeks_2026.json)의 W번호와 체계가 다를 수 있고, 전년 주차 매칭도
    같은 번호 기준의 근사치입니다."""
    try:
        df = _read_star_dataframe(Path(root) / "STAR.csv", Path(root) / "STAR.xlsx")
        if df is None:
            return {}, []
        required_cols = ['기준품목', '월(AB)', '주(AB)', '메져_구분']
        if not all(col in df.columns for col in required_cols):
            return {}, ["STAR 파일 필수 칼럼 부족"]

        result = _parse_star_dataframe(df)

        prev_df = _read_star_dataframe(Path(root) / "STAR_2025.csv", Path(root) / "STAR_2025.xlsx")
        if prev_df is not None and all(col in prev_df.columns for col in required_cols):
            prev_result = _parse_star_dataframe(prev_df, force_status="실적")
            for unit in ("수량", "금액"):
                result[unit]["prev_year_월별"] = {
                    month: bucket["실적"]["total"] for month, bucket in prev_result[unit]["월별"].items()
                }
                result[unit]["prev_year_주차별"] = {
                    week: bucket["total"] for week, bucket in prev_result[unit]["주차별"].items()
                }
        else:
            for unit in ("수량", "금액"):
                result[unit]["prev_year_월별"] = {}
                result[unit]["prev_year_주차별"] = {}

        return result, []
    except Exception as e:
        return {}, [f"STAR 파일 로드 오류: {str(e)}"]


def star_week_sort_key(label):
    match = re.fullmatch(r"(\d{1,2})주([AB]?)", label or "")
    return (int(match.group(1)), match.group(2)) if match else (-1, "")


def business_week_to_star_label(week_label):
    """업무주차 W36B → STAR 표기 36주B.

    월간ㆍ주간 분석의 선택값은 업무주차표 기준이고 STAR는 자체 표기를 사용하므로,
    주간 셀인/셀아웃이 0으로 보이지 않도록 화면 경계에서만 변환한다.
    """
    match = re.fullmatch(r"W(\d{1,2})([AB]?)", str(week_label or ""))
    return f"{int(match.group(1))}주{match.group(2)}" if match else week_label


def star_month_sort_key(label):
    match = re.fullmatch(r"(\d{1,2})월", label or "")
    return int(match.group(1)) if match else -1


# 프리미엄 세그먼트 정의: 품목 -> (SMSS_ATTR 칼럼, 판정 키워드)
# '키친핏'처럼 여러 변형(4Door/1Door 등)이 있는 경우 포함(contains) 매칭,
# '25kg'/'14인용'/'냉온정'처럼 단일 값인 경우도 동일한 포함 매칭 방식으로 처리합니다.
PREMIUM_SEGMENT_DEF = {
    "냉장고": ("SMSS_ATTR01", "키친핏"),
    "김치냉장고": ("SMSS_ATTR01", "키친핏"),
    "세탁기": ("SMSS_ATTR01", "25kg"),
    "조리기기": ("SMSS_ATTR02", "14인용"),
    "정수기": ("SMSS_ATTR01", "냉온정"),
}


def build_premium_segment_table(star_data, scope_type, scope_value):
    """PREMIUM_SEGMENT_DEF 기준 품목별 전체 실적 / 프리미엄 세그먼트 실적 / 판매비중(%).
    금액은 억원 단위. 정의되지 않은 품목은 표에서 제외합니다."""
    rows = []
    for product, (attr_col, keyword) in PREMIUM_SEGMENT_DEF.items():
        total = {"S/I": 0, "S/O": 0}
        premium = {"S/I": 0, "S/O": 0}
        total_amt = {"S/I": 0, "S/O": 0}
        premium_amt = {"S/I": 0, "S/O": 0}
        for unit, total_bucket, premium_bucket in (("수량", total, premium), ("금액", total_amt, premium_amt)):
            if scope_type == "월별":
                statuses = star_data.get(unit, {}).get("월별", {}).get(scope_value, {})
                row_sources = statuses.get("실적", {}).get("rows", []) + statuses.get("FCST", {}).get("rows", [])
            else:
                row_sources = star_data.get(unit, {}).get("주차별", {}).get(scope_value, {}).get("rows", [])
            for row_product, attrs, metrics in row_sources:
                if row_product != product:
                    continue
                total_bucket["S/I"] += metrics.get("S/I", 0)
                total_bucket["S/O"] += metrics.get("S/O", 0)
                value = attrs.get(attr_col)
                if isinstance(value, str) and keyword in value:
                    premium_bucket["S/I"] += metrics.get("S/I", 0)
                    premium_bucket["S/O"] += metrics.get("S/O", 0)

        for basis, all_values, premium_values, divisor in (
                ("수량", total, premium, 1), ("금액(억원)", total_amt, premium_amt, 1e8)):
            si_ratio = premium_values["S/I"] / all_values["S/I"] * 100 if all_values["S/I"] else None
            so_ratio = premium_values["S/O"] / all_values["S/O"] * 100 if all_values["S/O"] else None
            decimals = 0
            rows.append({
                ("품목", "품목"): product,
                ("구분", "구분"): basis,
                ("S/I", "전체"): f"{all_values['S/I'] / divisor:,.{decimals}f}",
                ("S/I", "프리미엄"): f"{premium_values['S/I'] / divisor:,.{decimals}f}",
                ("S/I", "비중(%)"): f"{si_ratio:.1f}" if number(si_ratio) else "N/A",
                ("S/O", "전체"): f"{all_values['S/O'] / divisor:,.{decimals}f}",
                ("S/O", "프리미엄"): f"{premium_values['S/O'] / divisor:,.{decimals}f}",
                ("S/O", "비중(%)"): f"{so_ratio:.1f}" if number(so_ratio) else "N/A",
            })
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame.columns = pd.MultiIndex.from_tuples(frame.columns)
    return frame


def _combined_month_total(star_data, unit, month_label):
    """해당 월의 실적+FCST 합산 품목별 total (월 비교용)."""
    bucket = star_data.get(unit, {}).get("월별", {}).get(month_label, {})
    combined = {}
    for status in ("실적", "FCST"):
        for product, metrics in bucket.get(status, {}).get("total", {}).items():
            entry = combined.setdefault(product, {k: 0 for k in STAR_METRIC_COLUMNS})
            for k, v in metrics.items():
                entry[k] += v
    return combined


def _pct_change(current, previous):
    if not number(current) or not number(previous) or previous == 0:
        return None
    return (current - previous) / previous * 100


def _fmt_pct(value):
    if not number(value):
        return "N/A"
    return f"+{value:.1f}" if value > 0 else f"△{abs(value):.1f}" if value < 0 else "0.0"


def _fmt_amount_100m(value):
    """원 단위 금액 값을 억원 단위로 변환해 표시."""
    return f"{value / 1e8:,.0f}" if number(value) else "0"


def build_star_combined_table(star_data, scope_type, scope_value, prev_scope_value):
    """S/I·S/O를 그룹 헤더로 묶은 표: 수량|금액(억원)|전기간비|전년비 (S/I),
    수량|금액(억원)|전기간비|전년비 (S/O). 전년비는 2025년 STAR 데이터(STAR_2025.csv)가
    있으면 동월/동주차 기준으로 계산하고, 없으면 'N/A'로 표시합니다."""
    if scope_type == "월별":
        qty = _combined_month_total(star_data, "수량", scope_value)
        amt = _combined_month_total(star_data, "금액", scope_value)
        qty_prev = _combined_month_total(star_data, "수량", prev_scope_value) if prev_scope_value else {}
        amt_prev = _combined_month_total(star_data, "금액", prev_scope_value) if prev_scope_value else {}
        qty_yoy = star_data.get("수량", {}).get("prev_year_월별", {}).get(scope_value, {})
        amt_yoy = star_data.get("금액", {}).get("prev_year_월별", {}).get(scope_value, {})
        change_label = "전월비(%)"
    else:
        qty = star_data.get("수량", {}).get("주차별", {}).get(scope_value, {}).get("total", {})
        amt = star_data.get("금액", {}).get("주차별", {}).get(scope_value, {}).get("total", {})
        qty_prev = star_data.get("수량", {}).get("주차별", {}).get(prev_scope_value, {}).get("total", {}) if prev_scope_value else {}
        amt_prev = star_data.get("금액", {}).get("주차별", {}).get(prev_scope_value, {}).get("total", {}) if prev_scope_value else {}
        qty_yoy = star_data.get("수량", {}).get("prev_year_주차별", {}).get(scope_value, {})
        amt_yoy = star_data.get("금액", {}).get("prev_year_주차별", {}).get(scope_value, {})
        change_label = "전주비(%)"

    products = sorted(set(qty) | set(amt))
    if not products:
        return None

    rows = []
    for product in products:
        q = qty.get(product, {k: 0 for k in STAR_METRIC_COLUMNS})
        a = amt.get(product, {k: 0 for k in STAR_METRIC_COLUMNS})
        qp = qty_prev.get(product, {})
        ap = amt_prev.get(product, {})
        qy = qty_yoy.get(product, {})
        ay = amt_yoy.get(product, {})
        si_qty_chg = _pct_change(q['S/I'], qp.get('S/I'))
        si_amt_chg = _pct_change(a['S/I'], ap.get('S/I'))
        so_qty_chg = _pct_change(q['S/O'], qp.get('S/O'))
        so_amt_chg = _pct_change(a['S/O'], ap.get('S/O'))
        si_yoy_chg = _pct_change(q['S/I'], qy.get('S/I'))
        si_yoy_chg = si_yoy_chg if si_yoy_chg is not None else _pct_change(a['S/I'], ay.get('S/I'))
        so_yoy_chg = _pct_change(q['S/O'], qy.get('S/O'))
        so_yoy_chg = so_yoy_chg if so_yoy_chg is not None else _pct_change(a['S/O'], ay.get('S/O'))
        rows.append({
            ("품목", "품목"): product,
            ("S/I", "수량"): f"{q['S/I']:,.0f}",
            ("S/I", "금액(억원)"): _fmt_amount_100m(a['S/I']),
            ("S/I", change_label): _fmt_pct(si_qty_chg) if si_qty_chg is not None else _fmt_pct(si_amt_chg),
            ("S/I", "전년비(%)"): _fmt_pct(si_yoy_chg),
            ("S/O", "수량"): f"{q['S/O']:,.0f}",
            ("S/O", "금액(억원)"): _fmt_amount_100m(a['S/O']),
            ("S/O", change_label): _fmt_pct(so_qty_chg) if so_qty_chg is not None else _fmt_pct(so_amt_chg),
            ("S/O", "전년비(%)"): _fmt_pct(so_yoy_chg),
        })
    df = pd.DataFrame(rows)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def build_star_channel_table(star_data, scope_type, scope_value, product):
    """선택한 품목의 채널(SOP/종합몰/홈쇼핑/쿠팡)별 S/I·S/O 수량/금액."""
    if scope_type == "월별":
        qty_channel = {}
        amt_channel = {}
        for status in ("실적", "FCST"):
            qty_bucket = star_data.get("수량", {}).get("월별", {}).get(scope_value, {}).get(status, {}).get("channel", {}).get(product, {})
            amt_bucket = star_data.get("금액", {}).get("월별", {}).get(scope_value, {}).get(status, {}).get("channel", {}).get(product, {})
            for ch, metrics in qty_bucket.items():
                entry = qty_channel.setdefault(ch, {k: 0 for k in STAR_METRIC_COLUMNS})
                for k, v in metrics.items():
                    entry[k] += v
            for ch, metrics in amt_bucket.items():
                entry = amt_channel.setdefault(ch, {k: 0 for k in STAR_METRIC_COLUMNS})
                for k, v in metrics.items():
                    entry[k] += v
    else:
        qty_channel = star_data.get("수량", {}).get("주차별", {}).get(scope_value, {}).get("channel", {}).get(product, {})
        amt_channel = star_data.get("금액", {}).get("주차별", {}).get(scope_value, {}).get("channel", {}).get(product, {})

    # SOP·종합몰·홈쇼핑·쿠팡 4개 채널을 항상 표시(데이터 없으면 0) — 채널 누락 오해 방지
    channels = ["SOP", "종합몰", "홈쇼핑", "쿠팡"]
    rows = []
    for ch in channels:
        q = qty_channel.get(ch, {k: 0 for k in STAR_METRIC_COLUMNS})
        a = amt_channel.get(ch, {k: 0 for k in STAR_METRIC_COLUMNS})
        rows.append({
            "채널": ch,
            "S/I 수량": q['S/I'], "S/I 금액(억원)": a['S/I'] / 1e8,
            "S/O 수량": q['S/O'], "S/O 금액(억원)": a['S/O'] / 1e8,
        })
    return pd.DataFrame(rows)


def render_star_section(st, star_data, scope_type, scope_value, prev_scope_value):
    """S/I·S/O 그룹 헤더 표 + 품목별 그래프 + 채널별(품목 선택) 표/그래프를 한 화면에 표시.
    반환값: 사용자가 채널 구성에서 선택한 품목명(다른 섹션과 동기화용), 없으면 None."""
    st.caption(f"⚠️ STAR 원본은 {STAR_ACTUAL_CUTOFF_WEEK}주(9/12)까지는 실적으로 확정되고 이후는 FCST(예측)입니다. "
               "금액은 억원 단위이며, 전년비는 2025년 STAR 데이터 기준 동월/동주차 비교입니다(전년 데이터 없는 항목은 N/A).")
    table = build_star_combined_table(star_data, scope_type, scope_value, prev_scope_value)
    if table is None:
        st.info(f"{scope_value}에 품목별 STAR 실적 데이터가 없습니다.")
        return None

    st.dataframe(table, use_container_width=True, hide_index=True)

    # 품목별 S/I vs S/O 그래프 (수량 기준)
    if scope_type == "월별":
        qty = _combined_month_total(star_data, "수량", scope_value)
    else:
        qty = star_data.get("수량", {}).get("주차별", {}).get(scope_value, {}).get("total", {})
    chart_df = pd.DataFrame([{"품목": p, "S/I": m["S/I"], "S/O": m["S/O"]} for p, m in sorted(qty.items())]).set_index("품목")
    if not chart_df.empty:
        st.markdown("**품목별 S/I·S/O 수량 비교**")
        st.bar_chart(chart_df, color=["#164c96", "#8fb4e3"], height=300)

    # 채널(SOP/종합몰/홈쇼핑/쿠팡)별 실적 - 거래선(평강 등) 정보는 STAR 원본에 없어 채널 기준으로 표시
    products = sorted(qty.keys())
    selected_product = None
    if products:
        st.markdown("**품목별 채널 구성 (SOP·종합몰·홈쇼핑·쿠팡)**")
        st.caption("STAR 원본에는 거래선(평강 등) 구분이 없어, 원본이 제공하는 채널(영업그룹) 기준으로 보여줍니다. "
                   "품목에 따라 실제로 판매 실적이 없는 채널은 0으로 표시됩니다.")
        selected_product = st.selectbox("품목 선택", products, key=f"star_channel_product_{scope_type}_{scope_value}")
        channel_df = build_star_channel_table(star_data, scope_type, scope_value, selected_product)
        if channel_df is not None:
            display_df = channel_df.copy()
            for col in ("S/I 수량", "S/O 수량"):
                display_df[col] = display_df[col].map(lambda v: f"{v:,.0f}")
            for col in ("S/I 금액(억원)", "S/O 금액(억원)"):
                display_df[col] = display_df[col].map(lambda v: f"{v:,.0f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            st.bar_chart(channel_df.set_index("채널")[["S/I 수량", "S/O 수량"]], color=["#164c96", "#8fb4e3"], height=280)
        else:
            st.caption("채널별 데이터가 없습니다.")
    return selected_product


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


def shown_kpi(value, decimals=0):
    """KPI 실적값의 음수는 대시보드 공통 기호 △로 표시한다."""
    if not number(value):
        return "미제공"
    return f"△{abs(value):,.{decimals}f}" if value < 0 else f"{value:,.{decimals}f}"


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


def fmt_amount(value, unit="", decimals=0):
    """절대값 표시(매출·수량 등): 1,242백만원"""
    return f"{value:,.{decimals}f}{unit}" if number(value) else "데이터없음"


def fmt_delta(value, unit="", decimals=0):
    """증감값 표시(신규관심고객, 격차, 전월비 등): +821명 / △591명 / 0"""
    if not number(value):
        return "데이터없음"
    if value == 0:
        return f"0{unit}"
    sign = "+" if value > 0 else "△"
    return f"{sign}{abs(value):,.{decimals}f}{unit}"


def star_overall_totals(star_data, scope_type, scope_value):
    """선택 구간의 전 품목 합산 S/I·S/O 수량/금액."""
    if scope_type == "월별":
        qty = _combined_month_total(star_data, "수량", scope_value)
        amt = _combined_month_total(star_data, "금액", scope_value)
    else:
        qty = star_data.get("수량", {}).get("주차별", {}).get(scope_value, {}).get("total", {})
        amt = star_data.get("금액", {}).get("주차별", {}).get(scope_value, {}).get("total", {})
    total = {"S/I_수량": 0, "S/O_수량": 0, "S/I_금액": 0, "S/O_금액": 0}
    for metrics in qty.values():
        total["S/I_수량"] += metrics.get("S/I", 0)
        total["S/O_수량"] += metrics.get("S/O", 0)
    for metrics in amt.values():
        total["S/I_금액"] += metrics.get("S/I", 0)
        total["S/O_금액"] += metrics.get("S/O", 0)
    return total


def benchmark_insights(rows, weekly=None, week_scope=None, monthly=False):
    """거래선 간 특이값(1위/최하위)을 찾아 (관찰 리스트, 상세 제언 리스트)로 반환.
    상세 제언은 1위 거래선의 실제 기록 활동(weekly_data.json)이 있으면 그 내용을 인용해
    구체적으로 제안하고, 없으면 일반 제안으로 대체합니다."""
    weekly = weekly or []
    observations, proposals = [], []

    def activity_summary(text, limit=72):
        text = re.sub(r"\s+", " ", str(text)).strip()
        parts = [p.strip(" -·") for p in re.split(r"[\n。]|(?<=다)\.", text) if p.strip()]
        value = parts[0] if parts else text
        return value if len(value) <= limit else value[:limit - 1] + "…"

    def detailed_proposal(top_name, bottom_name, topic, gap_text, generic_action, kpi):
        acts = activities(weekly, top_name, week_scope)
        if acts:
            _, _, activity_text = acts[-1]
            return (f"**대상 {bottom_name} | 근거** {topic} 격차 {gap_text} · "
                    f"**벤치마킹** {top_name} ‘{activity_summary(activity_text)}’ · "
                    f"**제안** 동일 활동을 1회 시험 적용하고 **확인 KPI** {kpi}로 전후 효과 비교")
        return (f"**대상 {bottom_name} | 근거** {top_name} 대비 {topic} 격차 {gap_text} · "
                f"**제안** {generic_action} · **확인 KPI** {kpi}")

    amount_unit, amount_scale = ("억원", 100) if monthly else ("백만원", 1)

    valid = [(r["거래선"], r["라이브 매출(백만)"], r.get("방송횟수")) for r in rows if number(r["라이브 매출(백만)"])]
    if len(valid) >= 2:
        valid.sort(key=lambda x: x[1], reverse=True)
        top_name, top_val, top_cnt = valid[0]
        bottom_name, bottom_val, bottom_cnt = valid[-1]
        top_eff = top_val / top_cnt if number(top_cnt) and top_cnt else None
        bottom_eff = bottom_val / bottom_cnt if number(bottom_cnt) and bottom_cnt else None
        observations.append(f"라이브 선도 거래선 **{top_name}** {fmt_amount(top_val / amount_scale, amount_unit, 0)} · 회당 {fmt_amount(top_eff, '백만원', 0) if number(top_eff) else 'N/A'}")
        observations.append(f"라이브 개선 거래선 **{bottom_name}** {fmt_amount(bottom_val / amount_scale, amount_unit, 0)} · 회당 {fmt_amount(bottom_eff, '백만원', 0) if number(bottom_eff) else 'N/A'}")
        proposals.append(detailed_proposal(top_name, bottom_name, "라이브 매출",
                                            fmt_delta(top_val - bottom_val, "백만원", 0),
                                            "상위 거래선의 고효율 편성 시간대·상품 구성을 한 회차에 복제",
                                            "회당 매출·방송 유입·주문 전환율"))

    valid_aff = [(r["거래선"], r["어필리에이트 주문금액(백만)"]) for r in rows if number(r["어필리에이트 주문금액(백만)"])]
    if len(valid_aff) >= 2:
        valid_aff.sort(key=lambda x: x[1], reverse=True)
        top_name, top_val = valid_aff[0]
        bottom_name, bottom_val = valid_aff[-1]
        observations.append(f"어필리에이트 선도 거래선 **{top_name}** {fmt_amount(top_val / amount_scale, amount_unit, 0)}")
        observations.append(f"어필리에이트 개선 거래선 **{bottom_name}** {fmt_amount(bottom_val / amount_scale, amount_unit, 0)}")
        proposals.append(detailed_proposal(top_name, bottom_name, "어필리에이트 주문금액",
                                            fmt_delta(top_val - bottom_val, "백만원", 0),
                                            "주문 발생 크리에이터·상품 조합을 선별해 콘텐츠 발행을 집중",
                                            "크리에이터당 주문·유입 대비 전환율·취소율"))

    valid2 = [(r["거래선"], r["신규 관심고객"]) for r in rows if number(r["신규 관심고객"])]
    if len(valid2) >= 2:
        valid2.sort(key=lambda x: x[1], reverse=True)
        top_name, top_val = valid2[0]
        bottom_name, bottom_val = valid2[-1]
        observations.append(f"관심고객 유입 선도 거래선 **{top_name}** {fmt_delta(top_val, '명')}")
        observations.append(f"관심고객 유입 개선 거래선 **{bottom_name}** {fmt_delta(bottom_val, '명')}")
        proposals.append(detailed_proposal(top_name, bottom_name, "신규 관심고객",
                                            fmt_delta(top_val - bottom_val, "명"),
                                            "상위 거래선의 유입 소재·혜택·노출 채널을 한 건씩 시험",
                                            "신규 관심고객·신규 구매 전환율"))
    return observations, proposals


def star_benchmark_insights(star_data, scope_type, scope_value, prev_scope_value):
    """품목 간 S/O 성장률 특이값(1위/최하위)을 찾아 (관찰 리스트, 상세 제언 리스트)로 반환."""
    if not prev_scope_value:
        return [], []
    if scope_type == "월별":
        qty = _combined_month_total(star_data, "수량", scope_value)
        qty_prev = _combined_month_total(star_data, "수량", prev_scope_value)
    else:
        qty = star_data.get("수량", {}).get("주차별", {}).get(scope_value, {}).get("total", {})
        qty_prev = star_data.get("수량", {}).get("주차별", {}).get(prev_scope_value, {}).get("total", {})

    changes = []
    for product, metrics in qty.items():
        prev = qty_prev.get(product, {}).get("S/O")
        change = _pct_change(metrics.get("S/O"), prev)
        if change is not None:
            changes.append((product, change, metrics.get("S/O")))
    if len(changes) < 2:
        return [], []
    changes.sort(key=lambda x: x[1], reverse=True)
    top, bottom = changes[0], changes[-1]
    observations = [
        f"🏆 S/O 성장률 1위 품목: **{top[0]}** {fmt_delta(top[1], '%', 1)} (수량 {fmt_amount(top[2], '', 0)})",
        f"⚠️ S/O 성장률 최하위 품목: **{bottom[0]}** {fmt_delta(bottom[1], '%', 1)} (수량 {fmt_amount(bottom[2], '', 0)})",
    ]
    proposals = [
        f"**{bottom[0]}**: {top[0]}({fmt_delta(top[1], '%', 1)})의 판매 채널 구성·프로모션 방식을 "
        f"벤치마킹해 적용하는 것을 검토·제안합니다. (S/O 성장률 격차 {fmt_delta(top[1]-bottom[1], '%p', 1)})"
    ]
    return observations, proposals


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
    """줄글 대신 '지표 +값' 형태의 리포트형 관찰/제안을 생성."""
    observations, proposals = [], []
    if number(row["라이브 매출(백만)"]) and row["라이브 매출(백만)"] > 0:
        observations.append(f"라이브 매출 {fmt_amount(row['라이브 매출(백만)'], '백만원', 1)}")
        proposals.append("방송 횟수·시간대·상품 구성 기록으로 회차당 매출 비교")
    if number(row["어필리에이트 주문금액(백만)"]) and row["어필리에이트 주문금액(백만)"] > 0:
        observations.append(f"어필리에이트 주문금액 {fmt_amount(row['어필리에이트 주문금액(백만)'], '백만원', 1)}")
        proposals.append("채널별 유입·주문·금액 기록으로 전환 개선 판단")
    if number(row["신규 관심고객"]):
        observations.append(f"신규 관심고객 {fmt_delta(row['신규 관심고객'], '명')}")
        if row["신규 관심고객"] <= 0:
            proposals.append("관심고객 감소 원인·유입 경로 점검 및 회복 목표 설정")
    change = weekly_smart.get("전주비") if isinstance(weekly_smart, dict) else None
    if number(change):
        observations.append(f"신규 관심고객 전주비 {fmt_delta(change, '%', 1)}")
    if activity_rows:
        labels = ", ".join(dict.fromkeys(channel for _, channel, _ in activity_rows))
        observations.append(f"기록 활동: {labels}")
        proposals.append("차주에도 활동별 목표 지표·결과 함께 기록")
    else:
        proposals.append("차주 활동·목표 지표·결과 입력으로 성과 분석 근거 확보")
    return observations, list(dict.fromkeys(proposals))


def _period_totals(live, affiliate, smart, month, calendar, monthly, selected_week):
    """지정 기간의 라이브/어필리에이트/신규관심고객 합계."""
    scope_key = "월별" if monthly else "주차별"
    period = month if monthly else selected_week
    live_data = live.get(scope_key, {}).get(period, {})
    affiliate_data = affiliate_period_data(affiliate, calendar, month, "월간" if monthly else selected_week)
    smart_data = smart.get("신규관심고객", {}).get(scope_key, {}).get(period, {})
    period_rows = report_rows(live_data, affiliate_data, smart_data)
    return [strict_sum(row[field] for row in period_rows) for field in ("라이브 매출(백만)", "어필리에이트 주문금액(백만)", "신규 관심고객")]


def _smart_interest_kpi(smart, month, week, monthly):
    """월간은 월말 누적 관심고객, 주간은 해당 주 신규 유입을 사용한다."""
    scope = "월별" if monthly else "주차별"
    key = month if monthly else week
    rows = smart.get("신규관심고객", {}).get(scope, {}).get(key, {})
    field = "누적관심고객수" if monthly else "신규관심고객수"
    values = [row.get(field) for row in rows.values() if number(row.get(field))]
    return sum(values) if values else None


def affiliate_period_data(affiliate, calendar, month, selected_week):
    """월별 원천이 없을 때도 그 달에 속한 주차 합계로 월 KPI를 제공한다."""
    weekly = affiliate.get("주차별", {})
    if selected_week != "월간":
        return weekly.get(selected_week, weekly.get(str(selected_week).rstrip("AB"), {}))
    direct = affiliate.get("월별", {}).get(month)
    if direct:
        return direct
    merged = {}
    for label in weeks_for_month(calendar, month):
        source = weekly.get(label, weekly.get(label.rstrip("AB"), {}))
        for agency, channels in source.items():
            for channel, values in channels.items():
                target = merged.setdefault(agency, {}).setdefault(channel, {})
                for field, value in values.items():
                    if field != "전환율" and number(value):
                        target[field] = target.get(field, 0) + value
    return merged


def render_month_week_analysis(st, root):
    errors = []
    live = read_json(root, "live_commerce_data.json", errors)
    affiliate = read_json(root, "affiliate_data.json", errors)
    smart = read_json(root, "smartstore_data.json", errors)
    weekly = read_json(root, "weekly_data.json", errors, [])
    calendar = read_json(root, "weeks_2026.json", errors)
    star_data, star_errors = load_star_xlsx(root)
    errors.extend(star_errors)
    
    if not isinstance(weekly, list):
        weekly = []; errors.append("weekly_data.json 형식을 확인해주세요.")
    months = [f"{m}월" for m in range(12, 0, -1)]
    latest = next((month for month in months if live.get("월별", {}).get(month)), "8월")
    col1, col2 = st.columns(2)
    with col1:
        month = st.selectbox("대상 월", months, index=months.index(latest), key="analysis_month")
    with col2:
        week_options = ["월간"] + weeks_for_month(calendar, month)
        selected_week = st.selectbox("대상 주차", week_options, key=f"analysis_week_{month}")
    monthly = selected_week == "월간"
    live_data = live.get("월별" if monthly else "주차별", {}).get(month if monthly else selected_week, {})
    affiliate_data = affiliate_period_data(affiliate, calendar, month, "월간" if monthly else selected_week)
    smart_data = smart.get("신규관심고객", {}).get("월별" if monthly else "주차별", {}).get(month if monthly else selected_week, {})
    rows = report_rows(live_data, affiliate_data, smart_data)
    scope = month if monthly else f"{month} {selected_week}"

    # 이전 기간(전월/전주) 계산
    if monthly:
        month_num = star_month_sort_key(month)
        prev_month, prev_week = (f"{month_num - 1}월" if month_num > 1 else None), None
        change_label = "전월비"
    else:
        prev_month = None
        week_list_only = week_options[1:]
        idx = week_list_only.index(selected_week) if selected_week in week_list_only else -1
        prev_week = week_list_only[idx + 1] if 0 <= idx < len(week_list_only) - 1 else None  # 목록이 최신순이라 다음 인덱스가 이전 기간
        change_label = "전주비"
    if monthly:
        prev_totals = _period_totals(live, affiliate, smart, prev_month, calendar, True, None) if prev_month else [None, None, None]
    else:
        prev_totals = _period_totals(live, affiliate, smart, month, calendar, False, prev_week) if prev_week else [None, None, None]

    st.subheader(f"{scope} 핵심 실적 요약")
    totals = [strict_sum(row[field] for row in rows) for field in ("라이브 매출(백만)", "어필리에이트 주문금액(백만)", "신규 관심고객")]
    totals[2] = _smart_interest_kpi(smart, month, selected_week, monthly)
    prev_totals[2] = _smart_interest_kpi(smart, prev_month if monthly else month, prev_week, monthly) if (prev_month if monthly else prev_week) else None
    metric_cols = list(st.columns(5))
    money_unit, money_scale = ("억원", 100) if monthly else ("백만원", 1)
    metric_specs = [
        ("라이브커머스 매출", totals[0], prev_totals[0], money_unit, money_scale),
        ("어필리에이트 주문금액", totals[1], prev_totals[1], money_unit, money_scale),
        (("스마트스토어 누적 관심고객" if monthly else "스마트스토어 신규 관심고객"), totals[2], prev_totals[2], "명", 1),
    ]
    for col, (label, value, prev_value, unit, scale) in zip(metric_cols[:3], metric_specs):
        with col:
            displayed = value / scale if number(value) else None
            if unit == "명":
                delta = fmt_delta(value - prev_value, "명") if number(value) and number(prev_value) else None
            else:
                delta_pct = _pct_change(value, prev_value)
                delta = f"{_fmt_pct(delta_pct)}%" if number(delta_pct) else None
            st.metric(f"{label}({unit})", shown_kpi(displayed, 0), delta=f"{delta} ({change_label})" if delta else None)

    # 셀인(S/I)·셀아웃(S/O) 실적 카드 (STAR 기반, 금액=억원, 전월비/전주비 delta 표시)
    if star_data:
        if monthly:
            cur_totals = star_overall_totals(star_data, "월별", month)
            star_prev_totals = star_overall_totals(star_data, "월별", prev_month) if prev_month else None
        else:
            star_week = business_week_to_star_label(selected_week)
            star_prev_week = business_week_to_star_label(prev_week) if prev_week else None
            cur_totals = star_overall_totals(star_data, "주차별", star_week)
            star_prev_totals = star_overall_totals(star_data, "주차별", star_prev_week) if star_prev_week else None
        si_amt = cur_totals["S/I_금액"] / 1e8
        so_amt = cur_totals["S/O_금액"] / 1e8
        si_delta = _pct_change(cur_totals["S/I_금액"], star_prev_totals["S/I_금액"]) if star_prev_totals else None
        so_delta = _pct_change(cur_totals["S/O_금액"], star_prev_totals["S/O_금액"]) if star_prev_totals else None
        with metric_cols[3]:
            st.metric("셀인 실적(억원)", f"{si_amt:,.0f}", delta=f"{_fmt_pct(si_delta)}% ({change_label})" if number(si_delta) else None)
        with metric_cols[4]:
            st.metric("셀아웃 실적(억원)", f"{so_amt:,.0f}", delta=f"{_fmt_pct(so_delta)}% ({change_label})" if number(so_delta) else None)
    st.caption(f"모든 증감은 {change_label} 기준입니다. 월 누계 금액은 억원, 주간 금액은 백만원으로 표시합니다.")

    # 요약(써머리) — 거래선/품목 벤치마킹 인사이트: 특이 거래선·품목을 짚고 실행 가능한 제언을 제시
    st.subheader("📊 요약 및 벤치마킹 인사이트")
    week_scope_for_activity = None if monthly else selected_week
    observations, proposals = benchmark_insights(rows, weekly, week_scope_for_activity, monthly)
    if star_data and (prev_month if monthly else prev_week):
        star_scope = month if monthly else business_week_to_star_label(selected_week)
        star_previous_scope = prev_month if monthly else business_week_to_star_label(prev_week)
        star_obs, star_props = star_benchmark_insights(star_data, "월별" if monthly else "주차별", star_scope, star_previous_scope)
        observations += star_obs
        proposals += star_props
    # 줄글이 아닌 경영 보고용 신호 목록: 값과 방향을 한 줄에 명확하게 표시한다.
    period_signals = []
    for label, value, prev_value, unit, precision in zip(
            ["라이브커머스 매출", "어필리에이트 주문금액", ("누적 관심고객" if monthly else "신규 관심고객")],
            totals, prev_totals, [money_unit, money_unit, "명"], [0, 0, 0]):
        if number(value):
            scale = 100 if monthly and unit == "억원" else 1
            value = value / scale
            prev_value = prev_value / scale if number(prev_value) else None
            delta_value = value - prev_value if number(prev_value) else None
            delta_text = fmt_delta(delta_value, unit, precision) if number(delta_value) else "비교 기준 없음"
            current_text = fmt_delta(value, unit, precision) if unit == "명" else (
                f"△{abs(value):,.{precision}f}{unit}" if value < 0 else fmt_amount(value, unit, precision))
            period_signals.append({"핵심 지표": label, "당기": current_text, change_label: delta_text})
    if star_data:
        for label, key in (("셀인 금액", "S/I_금액"), ("셀아웃 금액", "S/O_금액")):
            value = cur_totals[key] / 1e8
            prev_value = star_prev_totals[key] / 1e8 if star_prev_totals else None
            delta_value = value - prev_value if number(prev_value) else None
            period_signals.append({"핵심 지표": label, "당기": fmt_amount(value, "억원", 0), change_label: fmt_delta(delta_value, "억원", 0) if number(delta_value) else "비교 기준 없음"})
    if period_signals:
        st.dataframe(pd.DataFrame(period_signals), use_container_width=True, hide_index=True)
    if observations:
        st.markdown("**핵심 변동 및 확인 포인트**")
        for line in observations:
            st.markdown("- " + line)
    else:
        st.info("비교 가능한 데이터가 부족합니다.")

    if proposals:
        with st.expander(f"🔍 실행 제안 · 벤치마킹 ({len(proposals)}건)", expanded=False):
            for index, text in enumerate(proposals, 1):
                st.markdown(f"**제안 {index} · 검토 및 실행**  \n{text}")

    # 이 탭은 전체 요약 대시보드다. 모든 원천 테이블을 반복하지 않고,
    # 특이 거래선만 비교 차트와 신호로 보여주며 상세는 거래선별 분석 탭에서 확인한다.
    signal_df = pd.DataFrame(rows)
    if not signal_df.empty:
        st.subheader("거래선별 성과 편차")
        chart_left, chart_right = st.columns(2)
        with chart_left:
            st.caption("라이브·어필리에이트 주문금액 비교")
            st.bar_chart(signal_df.set_index("거래선")[["라이브 매출(백만)", "어필리에이트 주문금액(백만)"]], height=270)
        with chart_right:
            st.caption("스마트스토어 신규 관심고객 비교")
            st.bar_chart(signal_df.set_index("거래선")[["신규 관심고객"]], height=270)
        exception_rows = []
        for field, label in [("라이브 매출(백만)", "라이브"), ("어필리에이트 주문금액(백만)", "어필리에이트"), ("신규 관심고객", "신규 관심고객")]:
            valid = signal_df[["거래선", field]].dropna()
            if not valid.empty and valid[field].sum() > 0:
                top = valid.loc[valid[field].idxmax()]
                low = valid.loc[valid[field].idxmin()]
                exception_rows.append({"지표": label, "상위 거래선": top["거래선"], "상위 값": f"{top[field]:,.1f}",
                                       "확인 거래선": low["거래선"], "확인 값": f"{low[field]:,.1f}"})
        if exception_rows:
            st.dataframe(pd.DataFrame(exception_rows), use_container_width=True, hide_index=True)
    if errors:
        with st.expander("데이터 읽기 안내"):
            for error in errors:
                st.warning(error)
    return

    st.subheader("채널별 비교 분석")
    display = []
    for row in rows:
        item = {key: value if key == "거래선" else shown(value, 2 if "백만" in key else 0) for key, value in row.items()}
        activity_rows = activities(weekly, row["거래선"], None if monthly else selected_week)
        row_observations, _ = infer(row["거래선"], row, smart_data.get(row["거래선"], {}), activity_rows, scope)
        item["요약"] = " · ".join(row_observations[:3]) if row_observations else "제공된 지표가 없습니다."
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

    # 벤치마킹 인사이트 중 이 거래선(최하위)에 해당하는 항목을 최우선 Action Item으로 추가
    bench_proposals = []
    valid = [(r["거래선"], r["라이브 매출(백만)"]) for r in rows if number(r["라이브 매출(백만)"])]
    if len(valid) >= 2:
        valid.sort(key=lambda x: x[1], reverse=True)
        if valid[-1][0] == target:
            bench_proposals.append(f"{valid[0][0]} 대비 라이브 매출 최하위 — 방송 횟수·편성 전략 벤치마킹")
    valid2 = [(r["거래선"], r["신규 관심고객"]) for r in rows if number(r["신규 관심고객"])]
    if len(valid2) >= 2:
        valid2.sort(key=lambda x: x[1], reverse=True)
        if valid2[-1][0] == target:
            bench_proposals.append(f"{valid2[0][0]} 대비 신규 관심고객 최하위 — 유입 활동 벤치마킹")
    proposals = bench_proposals + [p for p in proposals if p not in bench_proposals]

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


def render_product_performance(st, root):
    data, errors = collect_product_data(root)
    star_data, star_errors = load_star_xlsx(root)

    st.subheader("품목별 실적")

    sync_month = None    # 채널별 실적(bizplan)과 동기화할 월
    sync_product = None  # 채널별 실적(bizplan)과 동기화할 품목

    # STAR 데이터 있으면 먼저 표시 (S/I·S/O 그룹표 + 그래프 + 채널구성, 실적/FCST 자동 구분)
    if star_data:
        st.markdown("### STAR 기반 실적 (셀인·셀아웃, 마감분은 실적/잔여기간은 FCST)")
        scope_type = st.radio("데이터 종류", ["월별", "주차별"], key="product_star_scope", horizontal=True)
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
            selected_scope = st.selectbox("대상 월" if scope_type == "월별" else "대상 주차", keys, key="product_star_scope_value")
            if scope_type == "월별":
                month_num = star_month_sort_key(selected_scope)
                prev_scope = f"{month_num - 1}월" if month_num > 1 else None
                sync_month = selected_scope
            else:
                weeks_sorted_asc = sorted(
                    set(star_data.get("수량", {}).get("주차별", {}).keys()) | set(star_data.get("금액", {}).get("주차별", {}).keys()),
                    key=star_week_sort_key)
                idx = weeks_sorted_asc.index(selected_scope) if selected_scope in weeks_sorted_asc else -1
                prev_scope = weeks_sorted_asc[idx - 1] if idx > 0 else None
                sync_month = star_data.get("수량", {}).get("주차별", {}).get(selected_scope, {}).get("month")
            sync_product = render_star_section(st, star_data, scope_type, selected_scope, prev_scope)
        else:
            st.info("STAR 품목별 실적 데이터가 없습니다.")

        if star_errors:
            with st.expander("STAR 데이터 읽기 안내"):
                for error in star_errors:
                    st.error(error)

        # STAR 안에서 품목별 총 실적과 SOP·종합몰·홈쇼핑·쿠팡 채널 구성을
        # 함께 보여주므로 별도 bizplan 표를 중복 노출하지 않는다.
        return
    elif star_errors:
        with st.expander("STAR 데이터 읽기 안내"):
            for error in star_errors:
                st.error(error)

    # 채널별 실적 (bizplan 기반) - 위 STAR 섹션에서 고른 월·품목을 그대로 사용(중복 선택 제거)
    st.markdown("### 채널별 실적")
    if not data:
        st.info("채널별 실적 데이터가 없습니다.")
        return

    all_months = [f"{m}월" for m in range(12, 0, -1)]
    month = sync_month if sync_month in all_months else all_months[0]
    product = sync_product if sync_product in data else "전체"
    st.caption(f"위 STAR 섹션에서 선택한 기간·품목과 동일하게 표시합니다 → **{month} / {product}**")
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
