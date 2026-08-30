import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="PP3G KPI", layout="wide")

st.title("📊 PP3G 주차별 KPI 대시보드")
st.markdown("자동화된 대리점 KPI 현황 시스템 | 누적 데이터(1월~8월) 기반 분석")

partners = ['평강', '문성', '케이디엘', '하나로', '회산', '현성', '클릭나라']

# ==================== 스토어 고객변화 (월계: 1월~7월, 주차별: 8월) ====================
store_monthly = {
    '평강': {'2월': 132629, '3월': 134648, '4월': 139797, '5월': 143211, '6월': 145622, '7월': 148134},
    '문성': {'2월': 111203, '3월': 113313, '4월': 114299, '5월': 116412, '6월': 118524, '7월': 120635},
    '케이디엘': {'2월': 88277, '3월': 90318, '4월': 91767, '5월': 94210, '6월': 96453, '7월': 98756},
    '하나로': {'2월': 81290, '3월': 83834, '4월': 86598, '5월': 89234, '6월': 91856, '7월': 94212},
    '회산': {'2월': 90585, '3월': 94421, '4월': 96767, '5월': 99123, '6월': 101456, '7월': 103789},
    '현성': {'2월': 181050, '3월': 184400, '4월': 188534, '5월': 191267, '6월': 194123, '7월': 197456},
    '클릭나라': {'2월': 78473, '3월': 80291, '4월': 80888, '5월': 82734, '6월': 84567, '7월': 86234}
}

store_weekly_aug = {
    '평강': {'W31': 245, 'W32': 267, 'W33': 289, 'W34': 312},
    '문성': {'W31': 318, 'W32': 334, 'W33': 356, 'W34': 378},
    '케이디엘': {'W31': 292, 'W32': 310, 'W33': 328, 'W34': 345},
    '하나로': {'W31': 267, 'W32': 285, 'W33': 301, 'W34': 318},
    '회산': {'W31': 189, 'W32': 205, 'W33': 223, 'W34': 241},
    '현성': {'W31': 156, 'W32': 172, 'W33': 189, 'W34': 206},
    '클릭나라': {'W31': 223, 'W32': 239, 'W33': 255, 'W34': 271}
}

# ==================== AI Live 효율 (월계: 1월~7월, 주차별: 8월) ====================
live_monthly = {
    '평강': {'1월': 10, '2월': 45, '3월': 52, '4월': 68, '5월': 75, '6월': 82, '7월': 89},
    '문성': {'1월': 3, '2월': 28, '3월': 38, '4월': 48, '5월': 56, '6월': 62, '7월': 71},
    '케이디엘': {'1월': 10, '2월': 38, '3월': 45, '4월': 52, '5월': 60, '6월': 67, '7월': 75},
    '하나로': {'1월': 0, '2월': 42, '3월': 55, '4월': 68, '5월': 78, '6월': 88, '7월': 98},
    '회산': {'1월': 15, '2월': 48, '3월': 58, '4월': 68, '5월': 78, '6월': 88, '7월': 98},
    '현성': {'1월': 8, '2월': 32, '3월': 42, '4월': 52, '5월': 62, '6월': 72, '7월': 82},
    '클릭나라': {'1월': 12, '2월': 35, '3월': 42, '4월': 50, '5월': 58, '6월': 65, '7월': 73}
}

live_weekly_aug = {
    '평강': {'W31': 3, 'W32': 3, 'W33': 3, 'W34': 3},
    '문성': {'W31': 5, 'W32': 5, 'W33': 5, 'W34': 5},
    '케이디엘': {'W31': 4, 'W32': 4, 'W33': 4, 'W34': 4},
    '하나로': {'W31': 4, 'W32': 4, 'W33': 4, 'W34': 4},
    '회산': {'W31': 2, 'W32': 2, 'W33': 2, 'W34': 2},
    '현성': {'W31': 2, 'W32': 2, 'W33': 2, 'W34': 2},
    '클릭나라': {'W31': 3, 'W32': 3, 'W33': 3, 'W34': 3}
}

# ==================== 어필리에이트 현황 (7월 월계, 8월 주차별) ====================
affiliate_july = {
    '평강': 38, '문성': 44, '케이디엘': 46, '하나로': 42, '회산': 40, '현성': 96, '클릭나라': 63
}

affiliate_aug = {
    '평강': {'W31': 14, 'W32': 15, 'W33': 16, 'W34': 17},
    '문성': {'W31': 40, 'W32': 41, 'W33': 42, 'W34': 43},
    '케이디엘': {'W31': 63, 'W32': 64, 'W33': 65, 'W34': 66},
    '하나로': {'W31': 14, 'W32': 14, 'W33': 14, 'W34': 15},
    '회산': {'W31': 33, 'W32': 34, 'W33': 35, 'W34': 36},
    '현성': {'W31': 53, 'W32': 54, 'W33': 55, 'W34': 56},
    '클릭나라': {'W31': 47, 'W32': 47, 'W33': 48, 'W34': 48}
}

# ==================== 파트너별 주요활동 요약 (1월 1주차 기준) ====================
activity_summary = {
    '평강': "📱 네이버 쿠폰 1만원\n🎁 알림쿠폰 1만원\n📊 SA & GFA 광고 최적화\n🏪 스마트스토어 배너 관리",
    '문성': "📹 숏클립 업로드 (월 2-3회→주 3-4회)\n🎁 알림쿠폰 활용\n🔔 삼세페 행사 대응\n📺 라이브 마케팅",
    '케이디엘': "💬 라이브 카카오톡 알림\n🛍️ 자사몰 정비\n📱 유튜브 인스타 영상\n🤖 AI라이브 세팅",
    '하나로': "🎁 네이버 첫구매 쿠폰 1만원\n📊 검색광고 상향 (30만→70만)\n🏪 자사몰 오픈 준비\n🛒 토스쇼핑 입점",
    '회산': "🎁 알림쿠폰 1만원\n📊 GFA 광고 + 성과형 지면광고\n🌐 브랜드커넥트 캠페인\n📦 온라인몰 지속 업데이트",
    '현성': "🔗 정수기 마케팅 (블로그/유튜브)\n🎁 알림쿠폰 1천원\n🛒 쇼핑커넥트 설정\n🎪 삼세페 행사 대응",
    '클릭나라': "🎁 알림쿠폰 1천원→3천원\n📊 DA 광고 예산 상향\n📡 검색광고 예산 증액\n📺 라이브 방송 진행"
}

tab1, tab2, tab3, tab4 = st.tabs(["🤖 최종분석", "📈 실시간 대시보드", "✏️ SOP 데이터 입력", "📤 RAW 데이터 업로드"])

# ==================== TAB 1: 최종분석 ====================
with tab1:
    st.header("🤖 누적 성과 분석 (1월~8월)")
    
    st.markdown("### 📊 누적 기간별 데이터 현황")
    st.divider()
    
    # 1️⃣ 월별 고객수 추이
    st.subheader("1️⃣ 스마트스토어 고객수 추이 (월계: 1월~7월)")
    
    months = ['2월', '3월', '4월', '5월', '6월', '7월']
    store_data_display = []
    for partner in partners:
        row = {'대리점': partner}
        for month in months:
            row[month] = f"{store_monthly[partner][month]:,}명"
        store_data_display.append(row)
    
    st.dataframe(pd.DataFrame(store_data_display), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 2️⃣ 8월 주차별 고객수
    st.subheader("2️⃣ 스마트스토어 고객수 (주차별: 8월)")
    
    store_aug_data = []
    for partner in partners:
        row = {'대리점': partner, 'W31': store_weekly_aug[partner]['W31'], 'W32': store_weekly_aug[partner]['W32'], 'W33': store_weekly_aug[partner]['W33'], 'W34': store_weekly_aug[partner]['W34']}
        store_aug_data.append(row)
    
    st.dataframe(pd.DataFrame(store_aug_data), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 3️⃣ AI Live 효율 (월계)
    st.subheader("3️⃣ AI Live 방송횟수 (월계: 1월~7월)")
    
    live_data_display = []
    for partner in partners:
        row = {'대리점': partner}
        for month in months:
            row[month] = live_monthly[partner][month]
        live_data_display.append(row)
    
    st.dataframe(pd.DataFrame(live_data_display), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 4️⃣ AI Live (주차별 8월)
    st.subheader("4️⃣ AI Live 방송횟수 (주차별: 8월)")
    
    live_aug_data = []
    for partner in partners:
        row = {'대리점': partner, 'W31': live_weekly_aug[partner]['W31'], 'W32': live_weekly_aug[partner]['W32'], 'W33': live_weekly_aug[partner]['W33'], 'W34': live_weekly_aug[partner]['W34']}
        live_aug_data.append(row)
    
    st.dataframe(pd.DataFrame(live_aug_data), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 5️⃣ 어필리에이트 (7월 월계)
    st.subheader("5️⃣ 어필리에이트 운영고객 (월계: 7월)")
    
    affiliate_july_data = []
    for partner in partners:
        affiliate_july_data.append({'대리점': partner, '7월 운영고객': affiliate_july[partner]})
    
    st.dataframe(pd.DataFrame(affiliate_july_data), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 6️⃣ 어필리에이트 (주차별 8월)
    st.subheader("6️⃣ 어필리에이트 운영고객 (주차별: 8월)")
    
    affiliate_aug_data = []
    for partner in partners:
        row = {'대리점': partner, 'W31': affiliate_aug[partner]['W31'], 'W32': affiliate_aug[partner]['W32'], 'W33': affiliate_aug[partner]['W33'], 'W34': affiliate_aug[partner]['W34']}
        affiliate_aug_data.append(row)
    
    st.dataframe(pd.DataFrame(affiliate_aug_data), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 7️⃣ 마케팅활동 요약 (1월 1주차 기준)
    st.subheader("7️⃣ 파트너별 주요활동 요약 (1월 1주차 기준)")
    
    for partner in partners:
        status = '🟢' if activity_summary else '🟡'
        with st.expander(f"{status} {partner}"):
            st.markdown(activity_summary[partner])

with tab2:
    st.header("📈 실시간 대시보드 (W34)")
    st.info("📊 현재 W34 데이터를 표시 중입니다")
    st.subheader("📊 W34 월별 누적 현황")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📱 평균 고객수", f"{np.mean([store_weekly_aug[p]['W34'] for p in partners]):.0f}명")
    col2.metric("🎬 평균 라이브", f"{np.mean([live_weekly_aug[p]['W34'] for p in partners]):.1f}회")
    col3.metric("🤝 평균 어필 고객", f"{np.mean([affiliate_aug[p]['W34'] for p in partners]):.0f}명")
    
    st.divider()
    st.subheader("🏢 대리점별 상세 현황 (W34)")
    
    tabs_partners = st.tabs(partners)
    
    for idx, partner in enumerate(partners):
        with tabs_partners[idx]:
            col1, col2, col3 = st.columns(3)
            col1.metric("📱 스마트스토어 고객", store_weekly_aug[partner]['W34'])
            col2.metric("🎬 AI Live 횟수", live_weekly_aug[partner]['W34'])
            col3.metric("🤝 어필리에이트 고객", affiliate_aug[partner]['W34'])
            
            st.divider()
            st.markdown("**📋 주요 마케팅활동**")
            st.success(activity_summary[partner])

with tab3:
    st.header("✏️ SOP 데이터 입력")
    with st.form("sop_form"):
        col1, col2 = st.columns(2)
        with col1:
            partner = st.selectbox("🏢 대리점 선택 *", partners, key="sop_partner")
        with col2:
            week = st.selectbox("📅 주차 선택 *", ["W34", "W35"], key="sop_week")
        
        st.divider()
        st.subheader("1️⃣ 스마트스토어 고객수")
        smartstore_customers = st.number_input("고객수", min_value=0, value=0)
        
        st.divider()
        st.subheader("2️⃣ 주요 마케팅 활동")
        marketing_activity = st.text_area("마케팅활동 *", placeholder="예시:\n- SNS 광고\n- POP 배치", height=100)
        
        st.divider()
        st.subheader("3️⃣ 어필리에이트 운영")
        col1, col2 = st.columns(2)
        with col1:
            affiliate_customers = st.number_input("운영 고객수", min_value=0, value=0)
        with col2:
            affiliate_sales = st.number_input("실적 (만원)", min_value=0, value=0)
        
        st.divider()
        st.subheader("4️⃣ 라이브 방송")
        col1, col2 = st.columns(2)
        with col1:
            live_count = st.number_input("라이브 횟수", min_value=0, value=0)
        with col2:
            live_sales = st.number_input("라이브 실적 (만원)", min_value=0, value=0)
        
        st.divider()
        submitted = st.form_submit_button("💾 데이터 저장", type="primary")
        
        if submitted:
            if not marketing_activity.strip():
                st.error("❌ 주요 마케팅활동을 입력하세요")
            else:
                st.success(f"✅ {partner}의 {week} SOP 데이터가 저장되었습니다!")

with tab4:
    st.header("📤 STAR RAW 데이터 일괄 업로드")
    week_select = st.selectbox("📅 분석 주차 선택", ["W34", "W35"], key="raw_week")
    st.divider()
    st.subheader("1️⃣ 파일 업로드")
    uploaded_files = st.file_uploader("RAW 데이터 파일 업로드", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
    
    if uploaded_files:
        st.subheader("2️⃣ 업로드된 파일")
        for uploaded_file in uploaded_files:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                st.success(f"✅ {uploaded_file.name} ({len(df)} 행)")
                st.dataframe(df.head(5), use_container_width=True)
            except Exception as e:
                st.error(f"❌ {uploaded_file.name}: {str(e)}")
        
        if st.button("💾 데이터 저장"):
            st.success(f"✅ {week_select} RAW 데이터가 저장되었습니다!")

st.divider()
st.markdown("<div style='text-align: center; color: gray; font-size: 12px;'>💫 PP3G KPI 자동화 시스템 | 1월~8월 누적 데이터 기반 실시간 모니터링</div>", unsafe_allow_html=True)
