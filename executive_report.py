"""PP3G 임원 보고 화면. 원본 데이터와 비교 조건을 명확히 표시한다."""
import json
import math
from pathlib import Path

import pandas as pd


AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]
STYLE = """
<style>
:root {--ink:#152a45;--muted:#65758b;--line:#e1e7ee;--accent:#164c96;}
.stApp {background:#f4f6f9;color:var(--ink);}
html,body,[class*="css"],button,input,textarea {font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;}
.block-container {max-width:1480px;padding-top:2.4rem;padding-bottom:4rem;}
h1 {font-size:2rem!important;letter-spacing:-.055em;font-weight:700!important;}
h2 {font-size:1.35rem!important;letter-spacing:-.035em;}
h3 {font-size:1.05rem!important;letter-spacing:-.025em;}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid var(--line);}
[data-testid="stSidebar"] .stButton>button {text-align:left;justify-content:flex-start;border:0;border-radius:7px;min-height:2.65rem;}
.stButton>button {border-radius:7px;border-color:#d3dce8;}
.stButton>button[kind="primary"] {background:#164c96;color:white;}
[data-testid="stMetric"] {background:white;border:1px solid var(--line);border-top:3px solid var(--accent);padding:20px 22px;border-radius:8px;}
[data-testid="stMetricLabel"] {color:var(--muted);font-size:.85rem;}
[data-testid="stMetricValue"] {color:var(--ink);font-size:2rem;letter-spacing:-.045em;}
[data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:8px;overflow:hidden;}
[data-testid="stExpander"] {background:white;border-radius:8px;}
.stTabs [data-baseweb="tab-list"] {gap:24px;border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"] {font-size:14px;}
.report-eyebrow {font-size:11px;letter-spacing:.16em;color:#64758a;font-weight:700;margin-bottom:8px;}
.report-rule {height:1px;background:#dce3eb;margin:20px 0 24px;}
.report-note {font-size:13px;color:#64758a;line-height:1.7;}
@media print {
 [data-testid="stSidebar"],header,footer,.stButton {display:none!important;}
 .stApp {background:#fff;} .block-container {padding:0;max-width:none;}
 [data-testid="stMetric"] {break-inside:avoid;}
}
</style>
"""


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
    return sum(values) if values and all(number(v) for v in values) else None


def report_rows(live, affiliate, smart):
    rows = []
    for agency in AGENCIES:
        live_row = live.get(agency, {})
        channels = affiliate.get(agency, {})
        # 상세 두 채널만 합산. 원본 '계'를 다시 더하지 않는다.
        affiliate_sale = strict_sum(channels.get(channel, {}).get("주문금액")
                                    for channel in ("쇼핑커넥트", "공동구매"))
        rows.append({"거래선": agency,
                     "라이브 매출(백만)": live_row.get("방송매출") / 1e6 if number(live_row.get("방송매출")) else None,
                     "방송횟수": live_row.get("방송횟수"),
                     "어필리에이트 주문금액(백만)": affiliate_sale / 1e6 if affiliate_sale is not None else None,
                     "신규 관심고객": smart.get(agency, {}).get("신규관심고객수")})
    return rows


def formatted(value, money=False):
    if not number(value):
        return "미제공"
    return f"{value:,.2f}" if money else f"{value:,.0f}"


def render_executive(st, root):
    errors = []
    live = read_json(root, "live_commerce_data.json", errors)
    affiliate = read_json(root, "affiliate_data.json", errors)
    smart = read_json(root, "smartstore_data.json", errors)
    weekly = read_json(root, "weekly_data.json", errors, [])
    if not isinstance(weekly, list):
        errors.append("주차별 입력 데이터 형식을 확인해주세요.")
        weekly = []
    if any(not isinstance(data, dict) for data in (live, affiliate, smart)):
        st.error("실적 파일은 월별 데이터를 포함한 JSON 객체여야 합니다.")
        return
    if live.get("금액단위", "원") != "원" or live.get("기준연도", 2026) != 2026:
        errors.append("라이브 데이터의 금액 단위 또는 기준연도가 보고 기준과 다릅니다.")
        live = {}

    months = [f"{m}월" for m in range(12, 0, -1)]
    latest = next((m for m in months if live.get("월별", {}).get(m)), "8월")
    left, right = st.columns([1, 3])
    with left:
        month = st.selectbox("보고 월", months, index=months.index(latest), key="executive_month")
    with right:
        st.caption("2026년 월별 제공 실적 · 채널별 자료 범위와 마감 여부를 확인한 후 보고해주세요.")
        st.caption("주차별 상세는 각 채널 메뉴에서 확인할 수 있습니다.")
    live_month = live.get("월별", {}).get(month, {})
    affiliate_month = affiliate.get("월별", {}).get(month, {})
    smart_month = smart.get("신규관심고객", {}).get("월별", {}).get(month, {})
    rows = report_rows(live_month, affiliate_month, smart_month)
    live_total = strict_sum(row["라이브 매출(백만)"] for row in rows)
    affiliate_total = strict_sum(row["어필리에이트 주문금액(백만)"] for row in rows)
    interest_total = strict_sum(row["신규 관심고객"] for row in rows)

    st.subheader(f"{month} 핵심 실적")
    for col, title, value, unit, money in zip(st.columns(3),
            ["라이브커머스 매출", "어필리에이트 주문금액", "스마트스토어 신규 관심고객"],
            [live_total, affiliate_total, interest_total], ["백만원", "백만원", "명"], [True, True, False]):
        with col:
            st.metric(title, formatted(value, money) + (f" {unit}" if value is not None else ""))
    st.caption("서로 다른 채널의 금액을 합산하지 않습니다. 미제공은 실적 0과 구분합니다.")

    st.markdown('<div class="report-rule"></div>', unsafe_allow_html=True)
    left, right = st.columns([1.7, 1])
    with left:
        st.subheader("거래선별 성과")
        display = [{key: value if key == "거래선" else formatted(value, "백만" in key)
                    for key, value in row.items()} for row in rows]
        st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)
    with right:
        st.subheader("라이브 매출 비교")
        chart_rows = [r for r in rows if number(r["라이브 매출(백만)"])]
        if chart_rows:
            chart = pd.DataFrame(chart_rows).set_index("거래선")[["라이브 매출(백만)"]]
            st.bar_chart(chart, color="#164c96", height=285)
            st.caption("단위: 백만원 · 선택 월의 제공 자료 기준")
        else:
            st.info("선택 월의 라이브 매출 자료가 없습니다.")

    st.subheader("보고 시 확인할 사항")
    notes = []
    if live_total is not None and live_total > 0:
        leader = max(rows, key=lambda r: r["라이브 매출(백만)"])
        notes.append(f"라이브 매출 최대 거래선은 {leader['거래선']}이며, 제공된 7개 거래선 합계의 "
                     f"{leader['라이브 매출(백만)'] / live_total * 100:.1f}%입니다. 수익성·활동의 우수성을 의미하지는 않습니다.")
    if not affiliate_month:
        notes.append(f"{month} 어필리에이트 월별 자료가 없어 합계를 표시하지 않았습니다.")
    if live_month and any(live_month.get(a, {}).get("소요비용") is None for a in AGENCIES):
        notes.append("라이브 비용 자료가 완비되지 않아 비용 대비 매출과 수익성 평가를 보류했습니다.")
    negative = [r["거래선"] for r in rows if number(r["신규 관심고객"]) and r["신규 관심고객"] < 0]
    if negative:
        notes.append("신규 관심고객이 음수인 거래선: " + ", ".join(negative) + ". 순증감·취소 반영 여부를 확인해야 합니다.")
    if smart_month and all(smart_month.get(a, {}).get("누적관심고객수") == 0 for a in AGENCIES):
        notes.append("관심고객 원본이 전 거래선 0으로 기재되어 있습니다. 실제 0인지 미입력 자리표시인지 확인해주세요.")
    if live.get("확인필요"):
        notes.append("라이브 주차 배정 확인 대상이 남아 있습니다. 월별 실적과 주차별 분석의 기준을 확인해주세요.")
    for note in notes:
        st.write("• " + note)
    if not notes:
        st.caption("추가 자동 확인 사항이 없습니다. 자료 완결성을 보증하는 의미는 아닙니다.")

    st.markdown('<div class="report-rule"></div>', unsafe_allow_html=True)
    st.subheader("거래선 활동 브리핑")
    records = [r for r in weekly if isinstance(r, dict) and r.get("월") == month
               and r.get("거래선") in AGENCIES and str(r.get("연도", 2026)) == "2026"]
    st.caption("선택 월의 주차별 입력 원문 · 활동에 따른 성과 인과관계는 아직 검증되지 않았습니다.")
    activity_count = 0
    for agency in AGENCIES:
        agency_records = [r for r in records if r.get("거래선") == agency]
        lines = []
        for record in agency_records:
            week = record.get("주차_표시", record.get("주차", "주차 미지정"))
            for channel in ("네이버스마트스토어", "쇼핑커넥트", "공동구매", "AI라이브"):
                activity = record.get(channel, {}).get("마케팅활동", "")
                if activity and str(activity).strip():
                    lines.append(f"{week} / {channel}\n{activity}")
            for subject, activity in record.get("당주주요활동", {}).items():
                if activity and str(activity).strip():
                    lines.append(f"{week} / {subject}\n{activity}")
        if lines:
            activity_count += 1
            with st.expander(f"{agency} · 활동 {len(lines)}건"):
                for line in lines:
                    st.text(line)
    if not activity_count:
        st.info("선택 월의 활동 원문이 없습니다. 거래선입력에 작성된 활동이 이 영역에 표시됩니다.")

    with st.expander("차주 보고 준비 과제 · 제안"):
        st.write("1. 각 거래선의 이번 주 활동과 결과 지표를 함께 확인하고 담당자 피드백을 확정합니다.")
        if live_month and any(live_month.get(a, {}).get("소요비용") is None for a in AGENCIES):
            st.write("2. 라이브 비용을 동일 월·주차 기준으로 수집해 효율 분석 조건을 갖춥니다.")
        if negative:
            st.write("3. 관심고객 음수 값의 집계 정의를 확인하고 수정 필요 여부를 결정합니다.")
        st.caption("업무 제안이며 확정 지시·자동 AI 평가가 아닙니다. 담당자와 기한은 별도 확정이 필요합니다.")
    with st.expander("데이터 범위 및 확인"):
        st.dataframe(pd.DataFrame([
            {"영역": label, "선택 월 제공 거래선": f"{sum(a in data for a in AGENCIES)} / 7", "기준": month}
            for label, data in [("라이브커머스", live_month), ("어필리에이트", affiliate_month), ("스마트스토어", smart_month)]
        ]), hide_index=True, use_container_width=True)
        for error in errors:
            st.error(error)
        st.caption("채널별 마감 여부와 주차 기준이 확정되지 않아 전월·전주 증감률을 이 요약에서 제시하지 않습니다.")
