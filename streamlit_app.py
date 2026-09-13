"""Samsung PP3G 통합 실적 대시보드.

RAW 파일 분석 (주간/월간 FCST & 실적) + 9개 탭 (거래선 관리, 피드백, 채널별 분석)

Run:
    streamlit run streamlit_app_integrated.py
"""

from __future__ import annotations

import re
import json
import os
from io import BytesIO
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================================
# 페이지 설정
# ============================================================================

st.set_page_config(page_title="삼성 PP3G 실적", page_icon="📊", layout="wide")

DEFAULT_FILE = Path("upload/STAR(2).xlsx")
AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]
DIMENSIONS = ["영업그룹", "기준품목", "SMSS_ATTR01", "SMSS_ATTR02", "SMSS_ATTR03"]


# ============================================================================
# RAW 파일 분석 함수 (GPT 코드 통합)
# ============================================================================

def find_header_row(file) -> int:
    """RAW 파일에서 헤더 행 찾기."""
    preview = pd.read_excel(file, header=None, nrows=30)
    for idx, row in preview.iterrows():
        if "영업그룹" in row.astype(str).tolist() and "주" in row.astype(str).tolist():
            return idx
    raise ValueError("RAW 파일에서 '영업그룹'과 '주' 헤더를 찾지 못했습니다.")


@st.cache_data(show_spinner=False)
def load_raw(file_bytes: bytes | None, file_name: str) -> pd.DataFrame:
    """RAW 파일 로드 및 정제."""
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
    """주차 정렬용 (W31 → 31)."""
    match = re.search(r"(\d{2})W$", str(value))
    return int(match.group(1)) if match else 999


def aggregate(frame: pd.DataFrame, period: str) -> pd.DataFrame:
    """주/월별 집계 및 FCST vs 실적 비교."""
    group_keys = [period, "영업그룹", "기준품목", "메져_구분"]
    columns = {
        "◆_AP1_S/I FCST_예상": "S/I FCST",
        "◆_AP1_RTF_예상": "RTF FCST",
        "◆_AP1_S/O FCST_예상": "S/O FCST",
        "◆_실판매_모바일/유통직판 포함": "S/O 실적",
        "◆_매출": "S/I 실적",
    }
    
    actual_periods = frame.groupby(period)[["◆_실판매_모바일/유통직판 포함", "◆_매출"]].apply(
        lambda x: x.notna().any().any()
    )
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
    """금액 포맷팅 (억 단위)."""
    if pd.isna(value):
        return "-"
    if unit == "금액":
        return f"{value / 100_000_000:,.1f}억"
    return f"{value:,.0f}"


def apply_filters(frame: pd.DataFrame, channels: list[str], products: list[str], measure: str) -> pd.DataFrame:
    """RAW 데이터 필터링."""
    return frame[
        frame["영업그룹"].isin(channels)
        & frame["기준품목"].isin(products)
        & frame["메져_구분"].eq(measure)
    ].copy()


# ============================================================================
# JSON 데이터 함수 (기존 코드)
# ============================================================================

def load_weekly_data() -> list:
    """거래선입력 데이터 로드."""
    if os.path.exists("weekly_data.json"):
        try:
            with open("weekly_data.json", "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_weekly_data(data: list) -> None:
    """거래선입력 데이터 저장."""
    with open("weekly_data.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_feedback_data() -> dict:
    """담당자피드백 데이터 로드."""
    if os.path.exists("feedback.json"):
        try:
            with open("feedback.json", "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_feedback_data(data: dict) -> None:
    """담당자피드백 데이터 저장."""
    with open("feedback.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_smartstore_data() -> dict:
    """스마트스토어 데이터 로드."""
    if os.path.exists("smartstore_data.json"):
        try:
            with open("smartstore_data.json", "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def load_affiliate_data() -> dict:
    """어필리에이트 데이터 로드."""
    if os.path.exists("affiliate_data.json"):
        try:
            with open("affiliate_data.json", "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def load_live_commerce_data() -> dict:
    """라이브커머스 데이터 로드."""
    if os.path.exists("live_commerce_data.json"):
        try:
            with open("live_commerce_data.json", "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def load_premium_data() -> dict:
    """프리미엄 데이터 로드."""
    if os.path.exists("premium_data.json"):
        try:
            with open("premium_data.json", "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def load_weeks_2026() -> dict:
    """주차 정보 로드."""
    if os.path.exists("weeks_2026.json"):
        try:
            with open("weeks_2026.json", "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


# ============================================================================
# 페이지 제목
# ============================================================================

st.title("삼성 PP3G 주간·월간 실적 & 거래선 관리")
st.caption("RAW 파일: 실적 입력된 기간은 실적값, 미입력 기간은 FCST 표시 | JSON 탭: 거래선별 주차 데이터 관리")


# ============================================================================
# 사이드바 (RAW + JSON)
# ============================================================================

with st.sidebar:
    # ===== RAW 데이터 =====
    st.header("📊 RAW 데이터 (FCST & 실적)")
    
    uploaded = st.file_uploader("RAW 실적 파일 업로드 (STAR.xlsx)", type=["xlsx"])
    if uploaded:
        file_bytes, file_name = uploaded.getvalue(), uploaded.name
    else:
        file_bytes, file_name = None, DEFAULT_FILE.name

    st.divider()
    
    measure = st.radio("기준", ["금액", "수량"], horizontal=True)
    
    # RAW 데이터 로드 시도
    try:
        raw = load_raw(file_bytes, file_name)
        channels = st.multiselect("영업그룹", sorted(raw["영업그룹"].unique()), 
                                 default=sorted(raw["영업그룹"].unique()))
        products = st.multiselect("기준품목", sorted(raw["기준품목"].unique()), 
                                 default=sorted(raw["기준품목"].unique()))
        raw_available = True
    except Exception as exc:
        st.error(f"RAW 파일 읽음 실패: {exc}")
        raw = pd.DataFrame()
        channels = []
        products = []
        raw_available = False
    
    # ===== JSON 데이터 =====
    st.divider()
    st.header("📋 거래선 데이터 (주차별)")
    
    selected_agency = st.selectbox("거래선", AGENCIES)
    
    all_months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
    all_months_reversed = list(reversed(all_months))
    selected_month = st.selectbox("월", all_months_reversed)
    
    # 주차 동적 생성
    weeks_2026 = load_weeks_2026()
    month_num = int(selected_month.replace('월', ''))
    weeks_list = ["계"]
    
    for week, info in weeks_2026.items():
        month_info = info.get('month', [])
        if isinstance(month_info, int):
            if month_info == month_num:
                weeks_list.append(week)
        elif isinstance(month_info, list):
            if month_num in month_info:
                if month_num == month_info[0]:
                    weeks_list.append(f"{week}A")
                else:
                    weeks_list.append(f"{week}B")
    
    def sort_key(w):
        if w == "계":
            return -1
        num = int(''.join(filter(str.isdigit, w)))
        return num
    
    weeks_list = sorted(weeks_list, key=sort_key, reverse=True)
    selected_week = st.selectbox("주차", weeks_list if weeks_list else ["계"])


# ============================================================================
# 탭 정의 (10개)
# ============================================================================

tabs = st.tabs([
    "📊 전체", 
    "✏️ 거래선입력", 
    "📋 거래선현황", 
    "💬 담당자피드백",
    "📈 FCST",
    "🎯 예측",
    "💎 프리미엄",
    "🛒 스마트스토어",
    "🤝 어필리에이트",
    "🎥 라이브커머스"
])

tab_overview, tab_input, tab_status, tab_feedback, tab_fcst, tab_forecast, tab_premium, tab_smartstore, tab_affiliate, tab_live = tabs


# ============================================================================
# 탭 1: 📊 전체 (전사 현황)
# ============================================================================

with tab_overview:
    st.subheader("📊 전사 현황 대시보드")
    
    if raw_available and not raw.empty and channels and products:
        filtered = apply_filters(raw, channels, products, measure)
        weekly = aggregate(filtered, "주")
        monthly = aggregate(filtered, "월")
        
        week_order = sorted(weekly["주"].unique(), key=week_number)
        month_order = sorted(monthly["월"].unique())
        
        actual_weeks = weekly.loc[weekly["S/I 구분"].eq("실적") | weekly["S/O 구분"].eq("실적"), "주"].unique()
        latest_actual_week = max(actual_weeks, key=week_number) if len(actual_weeks) else None
        
        if week_order:
            latest_week = week_order[-1]
            current = weekly[weekly["주"].eq(latest_week)]
            si_value, so_value, rtf_value = current[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
            si_actual = current["S/I 실적"].sum(min_count=1)
            so_actual = current["S/O 실적"].sum(min_count=1)
            status = "실적" if latest_week == latest_actual_week else ("실적 포함" if (pd.notna(si_actual) or pd.notna(so_actual)) else "FCST")
            
            a, b, c, d = st.columns(4)
            a.metric(f"S/I ({status}) - {latest_week}", money(si_value, measure))
            b.metric(f"S/O ({status}) - {latest_week}", money(so_value, measure))
            c.metric(f"RTF FCST - {latest_week}", money(rtf_value, measure))
            d.metric("S/O 달성률", 
                    f"{(so_actual / current['S/O FCST'].sum() * 100):.1f}%" if pd.notna(so_actual) and current["S/O FCST"].sum() else "-",
                    help="실적 S/O ÷ S/O FCST")
            
            st.divider()
            
            # 트렌드
            trend = weekly.groupby("주", as_index=False)[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
            trend["주"] = pd.Categorical(trend["주"], categories=week_order, ordered=True)
            trend = trend.sort_values("주").melt(id_vars="주", var_name="지표", value_name="값")
            st.plotly_chart(px.line(trend, x="주", y="값", color="지표", markers=True, title="주차별 S/I · S/O · RTF"), 
                          use_container_width=True)
    else:
        st.info("RAW 파일을 업로드하고 영업그룹과 기준품목을 선택해주세요.")


# ============================================================================
# 탭 2: ✏️ 거래선입력
# ============================================================================

with tab_input:
    st.subheader("✏️ 거래선 주차별 데이터 입력")
    st.info("거래선, 월, 주차를 선택하고 데이터를 입력합니다.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        input_agency = st.selectbox("거래선", AGENCIES, key="input_agency")
    with col2:
        input_month = st.selectbox("월", all_months_reversed, key="input_month")
    with col3:
        # 주차 동적 생성
        month_num = int(input_month.replace('월', ''))
        weeks_list = []
        for week, info in weeks_2026.items():
            month_info = info.get('month', [])
            if isinstance(month_info, int):
                if month_info == month_num:
                    weeks_list.append(week)
            elif isinstance(month_info, list):
                if month_num in month_info:
                    if month_num == month_info[0]:
                        weeks_list.append(f"{week}A")
                    else:
                        weeks_list.append(f"{week}B")
        
        weeks_list = sorted(weeks_list, key=lambda x: int(''.join(filter(str.isdigit, x))), reverse=True)
        input_week = st.selectbox("주차", weeks_list if weeks_list else ["W00"], key="input_week")
    
    st.divider()
    
    # 데이터 입력 폼
    st.subheader("📊 입력 데이터")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ss_interest = st.number_input("신규 관심고객수", min_value=0, step=1, key="ss_interest")
    with col2:
        ss_new = st.number_input("신규구매 구매자수", min_value=0, step=1, key="ss_new")
    with col3:
        ss_repurchase = st.number_input("재구매 구매자수", min_value=0, step=1, key="ss_repurchase")
    
    st.subheader("🛒 어필리에이트")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("🔹 **쇼핑커넥트**")
        sc_creator = st.number_input("크리에이터수", min_value=0, step=1, key="sc_creator")
        sc_model = st.number_input("운영모델수", min_value=0, step=1, key="sc_model")
        sc_visits = st.number_input("유입수", min_value=0, step=1, key="sc_visits")
        sc_orders = st.number_input("주문건수", min_value=0, step=1, key="sc_orders")
        sc_amount = st.number_input("주문금액 (원 단위)", min_value=0, step=1, key="sc_amount")
    
    with col2:
        st.write("🔹 **공동구매**")
        cj_creator = st.number_input("크리에이터수", min_value=0, step=1, key="cj_creator")
        cj_model = st.number_input("운영모델수", min_value=0, step=1, key="cj_model")
        cj_orders = st.number_input("주문건수", min_value=0, step=1, key="cj_orders")
        cj_amount = st.number_input("주문금액 (원 단위)", min_value=0, step=1, key="cj_amount")
    
    st.subheader("🎥 AI라이브")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        live_count = st.number_input("방송횟수", min_value=0, step=1, key="live_count")
    with col2:
        live_sale = st.number_input("방송매출 (원 단위)", min_value=0, step=1, key="live_sale")
    with col3:
        live_cost = st.number_input("소요비용 (원 단위)", min_value=0, step=1, key="live_cost")
    
    # 저장 버튼
    if st.button("💾 데이터 저장", use_container_width=True):
        weekly_data = load_weekly_data()
        
        new_data = {
            "거래선": input_agency,
            "월": input_month,
            "주차": input_week,
            "네이버스마트스토어": {
                "신규관심고객수": ss_interest,
                "신규구매구매자수": ss_new,
                "재구매구매자수": ss_repurchase,
                "마케팅활동": ""
            },
            "쇼핑커넥트": {
                "크리에이터운영수": sc_creator,
                "운영모델수": sc_model,
                "유입수": sc_visits,
                "상품주문건수": sc_orders,
                "주문금액": round(sc_amount / 1000000, 2),
                "마케팅활동": ""
            },
            "공동구매": {
                "크리에이터운영수": cj_creator,
                "운영모델수": cj_model,
                "상품주문건수": cj_orders,
                "주문금액": round(cj_amount / 1000000, 2),
                "마케팅활동": ""
            },
            "AI라이브": {
                "방송횟수": live_count,
                "방송매출": round(live_sale / 1000000, 2),
                "소요비용": round(live_cost / 1000000, 4),
                "마케팅활동": ""
            },
            "당주주요활동": {
                "AI라이브효율증대": "",
                "어필리에이트내재화": "",
                "구독활성화": "",
                "기타신규프로젝트": ""
            }
        }
        
        weekly_data.append(new_data)
        save_weekly_data(weekly_data)
        st.success(f"✅ {input_agency} - {input_week} ({input_month}) 데이터 저장됨!")


# ============================================================================
# 탭 3: 📋 거래선현황
# ============================================================================

with tab_status:
    st.subheader("📋 거래선 현황 (조회/수정/삭제)")
    
    weekly_data = load_weekly_data()
    agency_data = [item for item in weekly_data if item.get("거래선") == selected_agency]
    
    if agency_data:
        def get_week_num(week_str):
            num_str = ''.join(c for c in week_str if c.isdigit())
            return int(num_str) if num_str else 0
        
        agency_data_sorted = sorted(agency_data, key=lambda x: (get_week_num(x.get("주차", "W00")), x.get("월", "")), reverse=True)
        
        st.write(f"**총 {len(agency_data_sorted)}개 주차 데이터**")
        
        for idx, data in enumerate(agency_data_sorted):
            week = data.get("주차", "")
            month = data.get("월", "")
            week_display = f"**{week}** ({month})"
            
            with st.expander(week_display):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**네이버 스마트스토어**")
                    ss = data.get("네이버스마트스토어", {})
                    st.metric("신규 관심고객", f"{ss.get('신규관심고객수', 0):,}")
                    st.metric("신규구매", f"{ss.get('신규구매구매자수', 0):,}")
                    st.metric("재구매", f"{ss.get('재구매구매자수', 0):,}")
                
                with col2:
                    st.write("**어필리에이트**")
                    sc = data.get("쇼핑커넥트", {})
                    cj = data.get("공동구매", {})
                    st.metric("쇼핑커넥트 금액", f"{sc.get('주문금액', 0):.2f}백만")
                    st.metric("공동구매 금액", f"{cj.get('주문금액', 0):.2f}백만")
                
                st.write("**AI라이브**")
                live = data.get("AI라이브", {})
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("방송횟수", live.get('방송횟수', 0))
                with col2:
                    st.metric("방송매출", f"{live.get('방송매출', 0):.2f}백만")
                
                st.divider()
                
                # 삭제 버튼
                if st.button(f"🗑️ 삭제", key=f"delete_{idx}"):
                    weekly_data.pop(weekly_data.index(data))
                    save_weekly_data(weekly_data)
                    st.success("✅ 데이터 삭제됨!")
                    st.rerun()
    else:
        st.info(f"{selected_agency}의 등록된 데이터가 없습니다.")


# ============================================================================
# 탭 4: 💬 담당자피드백
# ============================================================================

with tab_feedback:
    st.subheader("💬 담당자 피드백")
    
    weekly_data = load_weekly_data()
    agency_data = [item for item in weekly_data if item.get("거래선") == selected_agency]
    
    if agency_data:
        feedback_data = load_feedback_data()
        
        def get_week_num(week_str):
            num_str = ''.join(c for c in week_str if c.isdigit())
            return int(num_str) if num_str else 0
        
        agency_data_sorted = sorted(agency_data, key=lambda x: (get_week_num(x.get("주차", "W00")), x.get("월", "")), reverse=True)
        
        for idx, data in enumerate(agency_data_sorted):
            week = data.get("주차", "")
            month = data.get("월", "")
            unique_key = f"{selected_agency}_{week}_{month}_{idx}"
            week_display = f"**{week}** ({month})"
            
            with st.expander(week_display):
                feedback_key = f"{selected_agency}_{week}_{month}_{idx}"
                existing_feedback = feedback_data.get(feedback_key, {})
                
                st.write("**스마트스토어 피드백**")
                ss_feedback = st.text_area("", value=existing_feedback.get("네이버스마트스토어", ""), height=60, key=f"ss_fb_{unique_key}")
                
                st.write("**어필리에이트 피드백**")
                af_feedback = st.text_area("", value=existing_feedback.get("어필리에이트", ""), height=60, key=f"af_fb_{unique_key}")
                
                st.write("**AI라이브 피드백**")
                live_feedback = st.text_area("", value=existing_feedback.get("AI라이브", ""), height=60, key=f"live_fb_{unique_key}")
                
                st.write("**당주주요활동 피드백**")
                activity_feedback = st.text_area("", value=existing_feedback.get("당주주요활동", ""), height=60, key=f"act_fb_{unique_key}")
                
                if st.button("💾 피드백 저장", key=f"save_fb_{unique_key}"):
                    feedback_data[feedback_key] = {
                        "거래선": selected_agency,
                        "주차": week,
                        "월": month,
                        "네이버스마트스토어": ss_feedback,
                        "어필리에이트": af_feedback,
                        "AI라이브": live_feedback,
                        "당주주요활동": activity_feedback,
                        "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    save_feedback_data(feedback_data)
                    st.success("✅ 피드백 저장됨!")
    else:
        st.info(f"{selected_agency}의 등록된 데이터가 없습니다.")


# ============================================================================
# 탭 5: 📈 FCST (주간 실적 - RAW 기반)
# ============================================================================

with tab_fcst:
    st.subheader("📈 FCST (주간 실적)")
    st.caption("RAW 파일 기반 주간 실적 분석")
    
    if raw_available and not raw.empty and channels and products:
        filtered = apply_filters(raw, channels, products, measure)
        weekly = aggregate(filtered, "주")
        week_order = sorted(weekly["주"].unique(), key=week_number)
        
        if week_order:
            selected_week = st.selectbox("주차 선택", week_order, index=len(week_order)-1, key="fcst_week")
            current = weekly[weekly["주"].eq(selected_week)]
            si_value, so_value, rtf_value = current[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
            si_actual = current["S/I 실적"].sum(min_count=1)
            so_actual = current["S/O 실적"].sum(min_count=1)
            
            actual_weeks = weekly.loc[weekly["S/I 구분"].eq("실적") | weekly["S/O 구분"].eq("실적"), "주"].unique()
            latest_actual_week = max(actual_weeks, key=week_number) if len(actual_weeks) else None
            status = "실적" if selected_week == latest_actual_week else ("실적 포함" if (pd.notna(si_actual) or pd.notna(so_actual)) else "FCST")
            
            a, b, c, d = st.columns(4)
            a.metric(f"S/I ({status})", money(si_value, measure))
            b.metric(f"S/O ({status})", money(so_value, measure))
            c.metric("RTF FCST", money(rtf_value, measure))
            d.metric("S/O 달성률", 
                    f"{(so_actual / current['S/O FCST'].sum() * 100):.1f}%" if pd.notna(so_actual) and current["S/O FCST"].sum() else "-")
            
            st.divider()
            
            # 트렌드
            trend = weekly.groupby("주", as_index=False)[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
            trend["주"] = pd.Categorical(trend["주"], categories=week_order, ordered=True)
            trend = trend.sort_values("주").melt(id_vars="주", var_name="지표", value_name="값")
            st.plotly_chart(px.line(trend, x="주", y="값", color="지표", markers=True, title="주차별 S/I · S/O · RTF"),
                          use_container_width=True)
            
            # 영업그룹별
            st.subheader("영업그룹별 주간 실적")
            breakdown = current.groupby("영업그룹", as_index=False)[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
            st.dataframe(breakdown, use_container_width=True, hide_index=True)
    else:
        st.info("RAW 파일을 업로드해주세요.")


# ============================================================================
# 탭 6: 🎯 예측 (월간 실적 - RAW 기반)
# ============================================================================

with tab_forecast:
    st.subheader("🎯 예측 (월간 실적)")
    st.caption("RAW 파일 기반 월간 실적 분석")
    
    if raw_available and not raw.empty and channels and products:
        filtered = apply_filters(raw, channels, products, measure)
        monthly = aggregate(filtered, "월")
        month_order = sorted(monthly["월"].unique())
        
        if month_order:
            selected_month = st.selectbox("월 선택", month_order, index=len(month_order)-1, key="forecast_month")
            current = monthly[monthly["월"].eq(selected_month)]
            si_value, so_value, rtf_value = current[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
            
            a, b, c = st.columns(3)
            a.metric("S/I (실적/FCST)", money(si_value, measure))
            b.metric("S/O (실적/FCST)", money(so_value, measure))
            c.metric("RTF FCST", money(rtf_value, measure))
            
            st.divider()
            
            # 트렌드
            trend = monthly.groupby("월", as_index=False)[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
            trend = trend.melt(id_vars="월", var_name="지표", value_name="값")
            st.plotly_chart(px.bar(trend, x="월", y="값", color="지표", barmode="group", title="월별 S/I · S/O · RTF"),
                          use_container_width=True)
            
            # 품목별
            st.subheader("품목별 월간 실적")
            product = current.groupby("기준품목", as_index=False)[["S/I 표시값", "S/O 표시값", "RTF FCST"]].sum(min_count=1)
            st.dataframe(product.sort_values("S/O 표시값", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("RAW 파일을 업로드해주세요.")


# ============================================================================
# 탭 7: 💎 프리미엄
# ============================================================================

with tab_premium:
    st.subheader("💎 프리미엄 제품 KPI")
    
    premium_data = load_premium_data()
    
    if premium_data:
        st.info("프리미엄 데이터 표시 준비 중...")
    else:
        st.info("프리미엄 데이터가 없습니다.")


# ============================================================================
# 탭 8: 🛒 스마트스토어
# ============================================================================

with tab_smartstore:
    st.subheader("🛒 스마트스토어 실적")
    
    smartstore_data = load_smartstore_data()
    
    if smartstore_data:
        tab_interest, tab_purchase = st.tabs(["📌 신규 관심고객", "📊 구매비중"])
        
        with tab_interest:
            st.write("신규 관심고객 유입 현황")
            if "신규관심고객" in smartstore_data:
                data_type = st.radio("데이터 종류", ["월별", "주차별"], key="ss_interest_type")
                
                if data_type == "월별":
                    months = list(smartstore_data["신규관심고객"]["월별"].keys())
                    selected = st.selectbox("월 선택", months, key="ss_interest_month")
                    display_data = smartstore_data["신규관심고객"]["월별"].get(selected, {})
                else:
                    weeks = list(smartstore_data["신규관심고객"]["주차별"].keys())
                    selected = st.selectbox("주차 선택", weeks, key="ss_interest_week")
                    display_data = smartstore_data["신규관심고객"]["주차별"].get(selected, {})
                
                if display_data:
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
        
        with tab_purchase:
            st.write("구매비중 변화 (신규 vs 재구매)")
            if "구매비중" in smartstore_data:
                data_type = st.radio("데이터 종류", ["월별", "주차별"], key="ss_purchase_type")
                
                if data_type == "월별":
                    months = list(smartstore_data["구매비중"]["월별"].keys())
                    selected = st.selectbox("월 선택", months, key="ss_purchase_month")
                    display_data = smartstore_data["구매비중"]["월별"].get(selected, {})
                else:
                    weeks = list(smartstore_data["구매비중"]["주차별"].keys())
                    selected = st.selectbox("주차 선택", weeks, key="ss_purchase_week")
                    display_data = smartstore_data["구매비중"]["주차별"].get(selected, {})
                
                if display_data:
                    rows = []
                    for agency, data in display_data.items():
                        row = {
                            "거래선": agency,
                            "신규구매고객": f"{data.get('신규구매고객수', 0):,}",
                            "신규구매비중(%)": f"{data.get('신규구매비중', 0):.2f}%",
                            "재구매고객": f"{data.get('재구매고객수', 0):,}",
                            "재구매비중(%)": f"{data.get('재구매비중', 0):.2f}%",
                        }
                        if data_type == "월별":
                            row["신규전월비(%)"] = f"{data.get('신규구매전월비', 0):.2f}%"
                            row["재전월비(%)"] = f"{data.get('재구매전월비', 0):.2f}%"
                        else:
                            row["신규전주비(%)"] = f"{data.get('신규구매전주비', 0):.2f}%"
                            row["재전주비(%)"] = f"{data.get('재구매전주비', 0):.2f}%"
                        rows.append(row)
                    
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("스마트스토어 데이터가 없습니다.")


# ============================================================================
# 탭 9: 🤝 어필리에이트
# ============================================================================

with tab_affiliate:
    st.subheader("🤝 어필리에이트 실적")
    
    affiliate_data = load_affiliate_data()
    
    if affiliate_data and ("월별" in affiliate_data or "주차별" in affiliate_data):
        available_weeks = list(affiliate_data.get("주차별", {}).keys())
        
        if "계" in available_weeks:
            available_weeks.remove("계")
            available_weeks = ["계"] + sorted(available_weeks, reverse=True)
        else:
            available_weeks = sorted(available_weeks, reverse=True)
        
        if available_weeks:
            selected_week = st.selectbox("주차 선택", available_weeks, key="affiliate_week")
            
            if selected_week in affiliate_data.get("주차별", {}):
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
                
                if rows:
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("어필리에이트 데이터가 없습니다.")


# ============================================================================
# 탭 10: 🎥 라이브커머스
# ============================================================================

with tab_live:
    st.subheader("🎥 라이브커머스 실적")
    
    live_data = load_live_commerce_data()
    
    if live_data and ("월별" in live_data or "주차별" in live_data):
        available_weeks = list(live_data.get("주차별", {}).keys())
        
        if "계" in available_weeks:
            available_weeks.remove("계")
            available_weeks = ["계"] + sorted(available_weeks, reverse=True)
        else:
            available_weeks = sorted(available_weeks, reverse=True)
        
        if available_weeks:
            selected_week = st.selectbox("주차 선택", available_weeks, key="live_week")
            
            if selected_week in live_data.get("주차별", {}):
                week_data = live_data["주차별"][selected_week]
                
                rows = []
                for agency, data in week_data.items():
                    rows.append({
                        "거래선": agency,
                        "방송횟수": data.get('방송횟수', 0),
                        "방송매출(백만)": f"{data.get('방송매출', 0) / 1000000:.2f}",
                        "소요비용(백만)": f"{data.get('소요비용', 0) / 1000000:.2f}",
                        "마케팅활동": data.get('마케팅활동', '')
                    })
                
                if rows:
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("라이브커머스 데이터가 없습니다.")


# ============================================================================
# 푸터
# ============================================================================

st.divider()
st.caption("삼성 PP3G 통합 실적 대시보드 | RAW 파일 + 거래선 데이터 | 마지막 업데이트: 2026-09-13")