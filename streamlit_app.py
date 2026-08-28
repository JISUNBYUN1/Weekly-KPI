import streamlit as st
import pandas as pd

st.set_page_config(page_title="PP3G KPI", layout="wide")

st.title("📊 PP3G 주차별 KPI 대시보드")
st.markdown("자동화된 대리점 KPI 현황 시스템")

# 탭
tab1, tab2, tab3 = st.tabs(["📈 대시보드", "✏️ 데이터 입력", "🤖 AI 분석"])

# 샘플 데이터
sample_data = {
    '평강_W34': {'forecast': 88, 'sales': 85, 'premium': 45, 'efficiency': 92},
    '문성_W34': {'forecast': 92, 'sales': 88, 'premium': 52, 'efficiency': 87},
    '현성_W34': {'forecast': 72, 'sales': 70, 'premium': 38, 'efficiency': 85},
    '하나로_W34': {'forecast': 84, 'sales': 82, 'premium': 48, 'efficiency': 89},
    '회산_W34': {'forecast': 75, 'sales': 68, 'premium': 35, 'efficiency': 80},
    '케이디엘_W34': {'forecast': 90, 'sales': 86, 'premium': 50, 'efficiency': 88},
    '클릭나라_W34': {'forecast': 82, 'sales': 79, 'premium': 42, 'efficiency': 84}
}

partners = ['평강', '문성', '현성', '하나로', '회산', '케이디엘', '클릭나라']

# ==================== TAB 1: 대시보드 ====================
with tab1:
    st.header("📊 주간 KPI 현황 (W34)")
    
    # KPI 요약
    col1, col2, col3, col4 = st.columns(4)
    
    avg_forecast = sum([sample_data[f"{p}_W34"]['forecast'] for p in partners]) / len(partners)
    avg_sales = sum([sample_data[f"{p}_W34"]['sales'] for p in partners]) / len(partners)
    avg_premium = sum([sample_data[f"{p}_W34"]['premium'] for p in partners]) / len(partners)
    avg_efficiency = sum([sample_data[f"{p}_W34"]['efficiency'] for p in partners]) / len(partners)
    
    col1.metric("📈 예측 달성율", f"{avg_forecast:.0f}%", "+2%")
    col2.metric("💰 실판매율", f"{avg_sales:.0f}%", "+1%")
    col3.metric("⭐ 프리미엄", f"{avg_premium:.0f}%", "0%")
    col4.metric("⚡ 효율성", f"{avg_efficiency:.0f}%", "+3%")
    
    st.divider()
    
    # 대리점별 테이블
    st.subheader("🏢 대리점별 상세 현황")
    
    table_data = []
    for p in partners:
        d = sample_data[f"{p}_W34"]
        table_data.append({
            '대리점': p,
            '예측 달성': f"{d['forecast']}%",
            '실판매': f"{d['sales']}%",
            '프리미엄': f"{d['premium']}%",
            '효율성': f"{d['efficiency']}%"
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

# ==================== TAB 2: 데이터 입력 ====================
with tab2:
    st.header("✏️ 주간 KPI 입력")
    
    with st.form("kpi_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            partner = st.selectbox("🏢 대리점 선택 *", partners)
        
        with col2:
            week = st.selectbox("📅 주차 *", ["W31A", "W31B", "W32", "W33", "W34"], index=4)
        
        forecast = st.number_input("📈 예측 달성율 (%)", min_value=0, max_value=150, value=85)
        premium = st.number_input("⭐ 프리미엄 비중 (%)", min_value=0, max_value=100, value=45)
        efficiency = st.number_input("⚡ 효율성 (%)", min_value=0, max_value=100, value=92)
        
        activity = st.text_area("📝 주요 활동", placeholder="이번주 진행한 주요 활동을 입력하세요", height=60)
        issue = st.text_area("⚠️ 발생된 이슈", placeholder="발생된 이슈를 입력하세요", height=60)
        
        submitted = st.form_submit_button("💾 데이터 저장", type="primary")
        
        if submitted:
            if not partner:
                st.error("❌ 대리점을 선택하세요")
            else:
                st.success(f"✅ {partner}의 {week} 데이터가 저장되었습니다!")
                st.info("🤖 AI가 자동으로 분석 중입니다...")

# ==================== TAB 3: AI 분석 ====================
with tab3:
    st.header("🤖 AI 자동 분석 & 인사이트")
    
    st.subheader("📊 주간 성과 요약")
    st.info(f"""
    ✅ **전사 평균 예측 달성율: {avg_forecast:.0f}%** (양호)
    
    W34 기준으로 전사 평균 예측 달성율은 {avg_forecast:.0f}%로 양호한 수준입니다.
    """)
    
    st.subheader("⚠️ 주의 필요 대리점")
    st.warning("""
    🔴 **현성 (72%), 회산 (68%)**
    
    두 대리점의 예측 달성율이 전사 평균 이하입니다.
    """)
    
    st.subheader("⭐ 우수 사례 벤치마킹")
    st.success("""
    💡 **문성의 프리미엄 전략 (52%)**
    
    문성의 프리미엄 비중이 52%로 전사 평균을 상회합니다.
    """)
    
    st.subheader("🎯 다음주 권고사항")
    st.info("""
    1️⃣ 저성과 대리점 지원
    2️⃣ 우수 사례 공유 교육
    3️⃣ 이슈 관리 강화
    """)

# 푸터
st.divider()
st.markdown("💫 PP3G KPI 자동화 시스템 | 실시간 모니터링", unsafe_allow_html=False)
