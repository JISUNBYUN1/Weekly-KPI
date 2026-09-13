"""Samsung PP3G weekly and monthly performance dashboard.

Run:
    streamlit run streamlit_app.py

The default file is STAR.xlsx.  The sidebar also accepts the recurring
RAW Excel upload from the manager-feedback workflow.
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="삼성 PP3G 실적", page_icon="📊", layout="wide")

DEFAULT_FILE = Path("upload/STAR.xlsx")
DIMENSIONS = ["영업그룹", "기준품목", "SMSS_ATTR01", "SMSS_ATTR02", "SMSS_ATTR03"]


def find_header_row(file) -> int:
    """Find the report header even when the RAW export has title rows."""
    preview = pd.read_excel(file, header=None, nrows=30)
    for idx, row in preview.iterrows():
        if "영업그룹" in row.astype(str).tolist() and "주" in row.astype(str).tolist():
            return idx
    raise ValueError("RAW 파일에서 '영업그룹'과 '주' 헤더를 찾지 못했습니다.")


@st.cache_data(show_spinner=False)
def load_raw(file_bytes: bytes | None, file_name: str) -> pd.DataFrame:
    source = DEFAULT_FILE if file_bytes is None else BytesIO(file_bytes)
    header_row = find_header_row(source)
    raw = pd.read_excel(source, header=header_row)
    raw = raw.loc[:, ~raw.columns.astype(str).str.startswith("Unnamed")].copy()
    raw.columns = raw.columns.astype(str).str.strip()

    required = {"영업그룹", "기준품목", "월", "주", "메져_구분"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {', '.join(sorted(missing))}")

    column_map = {
        "si_fcst": "◆_AP1_S/I FCST_예상",
        "rtf_fcst": "◆_AP1_RTF_예상",
        "so_fcst": "◆_AP1_S/O FCST_예상",
        "so_actual": "◆_실판매_모바일/유통직판 포함",
        "si_actual": "◆_매출",
    }
    absent = [label for label, col in column_map.items() if col not in raw.columns]
    if absent:
        raise ValueError("RAW 파일에 필요한 지표 컬럼이 없습니다: " + ", ".join(absent))

    for col in column_map.values():
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    for col in DIMENSIONS:
        if col in raw.columns:
            raw[col] = raw[col].fillna("미분류").astype(str)
    raw["월"] = raw["월"].astype(str)
    raw["주"] = raw["주"].astype(str)
    raw["메져_구분"] = raw["메져_구분"].astype(str)
    return raw


def week_number(value: str) -> int:
    match = re.search(r"(\d{2})W$", str(value))
    return int(match.group(1)) if match else 999


def aggregate(frame: pd.DataFrame, period: str) -> pd.DataFrame:
    """Create a report-ready total, selecting actuals whenever supplied."""
    group_keys = [period, "영업그룹", "기준품목", "메져_구분"]
    columns = {
        "◆_AP1_S/I FCST_예상": "S/I FCST",
        "◆_AP1_RTF_예상": "RTF FCST",
        "◆_AP1_S/O FCST_예상": "S/O FCST",
        "◆_실판매_모바일/유통직판 포함": "S/O 실적",
        "◆_매출": "S/I 실적",
    }
    # RAW exports leave zero actuals blank.  A period is treated as actual once
    # it contains any S/I or S/O actual value; blanks inside that closed period
    # are therefore zero, while a wholly unreported future period stays FCST.
    actual_periods = frame.groupby(period)[["◆_실판매_모바일/유통직판 포함", "◆_매출"]].apply(lambda x: x.notna().any().any())
    work = frame.copy()
    is_actual = work[period].map(actual_periods).fillna(False)
    for col in ["◆_실판매_모바일/유통직판 포함", "◆_매출"]:
        work.loc[is_actual, col] = work.loc[is_actual, col].fillna(0)

    report = work.groupby(group_keys, dropna=False)[list(columns)].sum(min_count=1).reset_index()
    report = report.rename(columns=columns)
    report["실적여부"] = report[period].map(actual_periods).fillna(False)
    report["S/I 표시값"] = report["S/I 실적"].where(report["실적여부"], report["S/I FCST"])
    report["S/O 표시값"] = report["S/O 실적"].where(report["실적여부"], report["S/O FCST"])
    report["S/I 구분"] = report["실적여부"].map({True: "실적", False: "FCST"})
    report["S/O 구분"] = report["실적여부"].map({True: "실적", False: "FCST"})
    report = report.drop(columns="실적여부")
    return report


def money(value: float, unit: str) -> str:
    if pd.isna(value):
        return "-"
    if unit == "금액":
        return f"{value / 100_000_000:,.1f}억"
    return f"{value:,.0f}"


def apply_filters(frame: pd.DataFrame, channels: list[str], products: list[str], measure: str) -> pd.DataFrame:
    return frame[
        frame["영업그룹"].isin(channels)
        & frame["기준품목"].isin(products)
        & frame["메져_구분"].eq(measure)
    ].copy()


st.title("삼성 PP3G 주간·월간 실적")
st.caption("실적이 입력된 기간은 실적값을, 미입력 기간은 FCST를 표시합니다. RTF는 주차별 FCST입니다.")

with st.sidebar:
    st.header("데이터")
    uploaded = st.file_uploader("RAW 실적 파일 업로드", type=["xlsx"])
    if uploaded:
        file_bytes, file_name = uploaded.getvalue(), uploaded.name
    else:
        file_bytes, file_name = None, DEFAULT_FILE.name

try:
    raw = load_raw(file_bytes, file_name)
except Exception as exc:
    st.error(f"파일을 읽을 수 없습니다: {exc}")
    st.stop()

with st.sidebar:
    st.divider()
    measure = st.radio("기준", ["금액", "수량"], horizontal=True)
    channels = st.multiselect("영업그룹", sorted(raw["영업그룹"].unique()), default=sorted(raw["영업그룹"].unique()))
    products = st.multiselect("기준품목", sorted(raw["기준품목"].unique()), default=sorted(raw["기준품목"].unique()))

filtered = apply_filters(raw, channels, products, measure)
weekly = aggregate(filtered, "주")
monthly = aggregate(filtered, "월")
week_order = sorted(weekly["주"].unique(), key=week_number)
month_order = sorted(monthly["월"].unique())

actual_weeks = weekly.loc[weekly["S/I 구분"].eq("실적") | weekly["S/O 구분"].eq("실적"), "주"].unique()
latest_actual_week = max(actual_weeks, key=week_number) if len(actual_weeks) else None

if not channels or not products:
    st.warning("표시할 영업그룹과 품목을 하나 이상 선택하세요.")
    st.stop()

tab_week, tab_month, tab_detail = st.tabs(["주간 실적", "월간 실적", "상세 데이터"])

with tab_week:
    selected_week = st.selectbox("주차", week_order, index=len(week_order) - 1)
    current = weekly[weekly["주"].eq(selected_week)]
    si_value, so_value, rtf_value = current[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
    si_actual = current["S/I 실적"].sum(min_count=1)
    so_actual = current["S/O 실적"].sum(min_count=1)
    status = "실적" if selected_week == latest_actual_week else ("실적 포함" if (pd.notna(si_actual) or pd.notna(so_actual)) else "FCST")
    a, b, c, d = st.columns(4)
    a.metric(f"S/I ({status})", money(si_value, measure))
    b.metric(f"S/O ({status})", money(so_value, measure))
    c.metric("RTF FCST", money(rtf_value, measure))
    d.metric("S/O 달성률", f"{(so_actual / current['S/O FCST'].sum() * 100):.1f}%" if pd.notna(so_actual) and current["S/O FCST"].sum() else "-", help="실적 S/O ÷ S/O FCST")

    trend = weekly.groupby("주", as_index=False)[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
    trend["주"] = pd.Categorical(trend["주"], categories=week_order, ordered=True)
    trend = trend.sort_values("주").melt(id_vars="주", var_name="지표", value_name="값")
    st.plotly_chart(px.line(trend, x="주", y="값", color="지표", markers=True, title="주차별 S/I · S/O · RTF"), use_container_width=True)

    breakdown = current.groupby("영업그룹", as_index=False)[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
    st.subheader("영업그룹별 주간 실적")
    st.dataframe(breakdown, use_container_width=True, hide_index=True, column_config={col: st.column_config.NumberColumn(format="%,.0f") for col in breakdown.columns if col != "영업그룹"})

with tab_month:
    selected_month = st.selectbox("월", month_order, index=len(month_order) - 1)
    current = monthly[monthly["월"].eq(selected_month)]
    si_value, so_value, rtf_value = current[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
    a, b, c = st.columns(3)
    a.metric("S/I (실적/FCST)", money(si_value, measure))
    b.metric("S/O (실적/FCST)", money(so_value, measure))
    c.metric("RTF FCST", money(rtf_value, measure))

    trend = monthly.groupby("월", as_index=False)[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1).melt(id_vars="월", var_name="지표", value_name="값")
    st.plotly_chart(px.bar(trend, x="월", y="값", color="지표", barmode="group", title="월별 S/I · S/O · RTF"), use_container_width=True)

    product = current.groupby("기준품목", as_index=False)[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
    st.subheader("품목별 월간 실적")
    st.dataframe(product.sort_values("S/O 표시값", ascending=False), use_container_width=True, hide_index=True, column_config={col: st.column_config.NumberColumn(format="%,.0f") for col in product.columns if col != "기준품목"})

with tab_detail:
    view = st.radio("조회 단위", ["주", "월"], horizontal=True)
    data = weekly if view == "주" else monthly
    data = data.sort_values(view, key=lambda s: s.map(week_number) if view == "주" else s)
    display_columns = [view, "영업그룹", "기준품목", "메져_구분", "S/I 실적", "S/I FCST", "RTF FCST", "S/O 실적", "S/O FCST", "S/I 구분", "S/O 구분"]
    st.dataframe(data[display_columns], use_container_width=True, hide_index=True, column_config={col: st.column_config.NumberColumn(format="%,.0f") for col in display_columns if col not in {view, "영업그룹", "기준품목", "메져_구분", "S/I 구분", "S/O 구분"}})
    st.download_button("집계 데이터 다운로드", data[display_columns].to_csv(index=False).encode("utf-8-sig"), f"PP3G_{view}_summary.csv", "text/csv")
