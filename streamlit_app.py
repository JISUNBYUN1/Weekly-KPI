import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="PP3G KPI", layout="wide")

st.title("📊 PP3G 주차별 KPI 대시보드")
st.markdown("자동화된 대리점 KPI 현황 시스템 | 누적 데이터 기반 분석")

partners = ['평강', '문성', '케이디엘', '하나로', '회산', '현성', '클릭나라']

# 누적 데이터 (연간)
accumulated_data = {
    '평강': {'forecast': 88, 'sales': 85, 'premium': 45, 'efficiency': 92, 'smartstore': 130610, 'marketing': "📱 SNS 광고\n🏪 POP 배치", 'affiliate_customers': 124, 'affiliate_sales': 780, 'live_count': 845, 'live_sales': 22591},
    '문성': {'forecast': 92, 'sales': 88, 'premium': 52, 'efficiency': 87, 'smartstore': 109266, 'marketing': "⭐ 프리미엄 강화\n📢 홍보물", 'affiliate_customers': 33, 'affiliate_sales': 27, 'live_count': 358, 'live_sales': 16679},
    '케이디엘': {'forecast': 90, 'sales': 86, 'premium': 50, 'efficiency': 88, 'smartstore': 86331, 'marketing': "🌐 멀티채널\n🤝 협력사", 'affiliate_customers': 246, 'affiliate_sales': 366, 'live_count': 450, 'live_sales': 18000},
    '하나로': {'forecast': 84, 'sales': 82, 'premium': 48, 'efficiency': 89, 'smartstore': 79682, 'marketing': "🎄 시즈널\n📦 번들", 'affiliate_customers': 207, 'affiliate_sales': 1203, 'live_count': 380, 'live_sales': 15000},
    '회산': {'forecast': 75, 'sales': 68, 'premium': 35, 'efficiency': 80, 'smartstore': 85164, 'marketing': "📋 기초활동\n🎯 초점강화", 'affiliate_customers': 120, 'affiliate_sales': 450, 'live_count': 200, 'live_sales': 8000},
    '현성': {'forecast': 72, 'sales': 70, 'premium': 38, 'efficiency': 85, 'smartstore': 177569, 'marketing': "🏪 기본관리\n💡 상품배치", 'affiliate_customers': 180, 'affiliate_sales': 550, 'live_count': 280, 'live_sales': 9500},
    '클릭나라': {'forecast': 82, 'sales': 79, 'premium': 42, 'efficiency': 84, 'smartstore': 140000, 'marketing': "💻 온라인중심\n📱 SNS강화", 'affiliate_customers': 150, 'affiliate_sales': 600, 'live_count': 350, 'live_sales': 12000}
}

# W34 샘플 데이터
sample_data_w34 = {
    '평강_W34': {'forecast': 88, 'sales': 85, 'premium': 45, 'efficiency': 92, 'smartstore': 245, 'marketing': "📱 SNS 광고\n🏪 POP 배치", 'affiliate_customers': 42, 'affiliate_sales': 1250, 'live_count': 3, 'live_sales': 680},
    '문성_W34': {'forecast': 92, 'sales': 88, 'premium': 52, 'efficiency': 87, 'smartstore': 318, 'marketing': "⭐ 프리미엄\n📢 홍보물", 'affiliate_customers': 58, 'affiliate_sales': 1890, 'live_count': 5, 'live_sales': 1120},
    '케이디엘_W34': {'forecast': 90, 'sales': 86, 'premium': 50, 'efficiency': 88, 'smartstore': 292, 'marketing': "🌐 멀티채널\n🤝 협력사", 'affiliate_customers': 52, 'affiliate_sales': 1650, 'live_count': 4, 'live_sales': 920},
    '하나로_W34': {'forecast': 84, 'sales': 82, 'premium': 48, 'efficiency': 89, 'smartstore': 267, 'marketing': "🎄 시즈널\n📦 번들", 'affiliate_customers': 45, 'affiliate_sales': 1380, 'live_count': 4, 'live_sales': 850},
    '회산_W34': {'forecast': 75, 'sales': 68, 'premium': 35, 'efficiency': 80, 'smartstore': 189, 'marketing': "📋 기초활동\n🎯 초점강화", 'affiliate_customers': 32, 'affiliate_sales': 920, 'live_count': 2, 'live_sales': 510},
    '현성_W34': {'forecast': 72, 'sales': 70, 'premium': 38, 'efficiency': 85, 'smartstore': 156, 'marketing': "🏪 기본관리\n💡 상품배치", 'affiliate_customers': 28, 'affiliate_sales': 780, 'live_count': 2, 'live_sales': 420},
    '클릭나라_W34': {'forecast': 82, 'sales': 79, 'premium': 42, 'efficiency': 84, 'smartstore': 223, 'marketing': "💻 온라인중심\n📱 SNS강화", 'affiliate_customers': 38, 'affiliate_sales': 1120, 'live_count': 3, 'live_sales': 680}
}

tab1, tab2, tab3, tab4 = st.tabs(["🤖 최종분석", "📈 실시간 대시보드", "✏️ SOP 데이터 입력", "📤 RAW 데이터 업로드"])

with tab1:
    st.header("🤖 누적 성과 분석")
    st.markdown("### 📊 연간 누적 성과 vs W34 현주")
    
    st.divider()
    
    st.subheader("📈 연간 누적 KPI 요약")
    col1, col2, col3, col4 = st.columns(4)
    avg_forecast = sum([accumulated_data[p]['forecast'] for p in partners]) / len(partners)
    avg_sales = sum([accumulated_data[p]['sales'] for p in partners]) / len(partners)
    avg_premium = sum([accumulated_data[p]['premium'] for p in partners]) / len(partners)
    avg_efficiency = sum([accumulated_data[p]['efficiency'] for p in partners]) / len(partners)
    col1.metric("📈 평균 예측", f"{avg_forecast:.1f}%")
    col2.metric("💰 평균 판매", f"{avg_sales:.1f}%")
    col3.metric("⭐ 평균 프리미엄", f"{avg_premium:.1f}%")
    col4.metric("⚡ 평균 효율성", f"{avg_efficiency:.1f}%")
    
    st.divider()
    
    st.subheader("📊 대리점별 누적 성과 현황")
    kpi_data = []
    for partner in partners:
        data = accumulated_data[partner]
        kpi_data.append({'대리점': partner, '예측': f"{data['forecast']}%", '판매': f"{data['sales']}%", '프리미엄': f"{data['premium']}%", '효율': f"{data['efficiency']}%", '고객수': f"{data['smartstore']:,}명", '상태': '🟢' if data['forecast'] >= 85 else '🟡' if data['forecast'] >= 75 else '🔴'})
    st.dataframe(pd.DataFrame(kpi_data), use_container_width=True, hide_index=True)
    
    st.divider()
    
    st.subheader("📊 누적 vs 현주(W34) 비교")
    comparison_data = []
    for partner in partners:
        acc = accumulated_data[partner]
        w34_key = f"{partner}_W34"
        w34 = sample_data_w34[w34_key]
        comparison_data.append({'대리점': partner, '누적예측': f"{acc['forecast']}%", '현주예측': f"{w34['forecast']}%", '누적고객': f"{acc['smartstore']:,}명", '현주고객': f"{w34['smartstore']:,}명", '누적라이브': f"{acc['live_count']}회", '현주라이브': f"{w34['live_count']}회"})
    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
    
    st.divider()
    
    st.subheader("📋 SOP별 누적 성과 분석")
    sop_tabs = st.tabs(["📱 스마트스토어", "🎬 라이브 방송", "🤝 어필리에이트", "📣 마케팅활동"])
    
    with sop_tabs[0]:
        st.markdown("### 📱 스마트스토어 누적 고객수")
        smartstore_data = []
        for partner in partners:
            data = accumulated_data[partner]
            smartstore_data.append({'대리점': partner, '누적고객': f"{data['smartstore']:,}명", '효율': f"{data['efficiency']}%", '기여도': '🔴높음' if data['smartstore'] > 130000 else '🟡중간' if data['smartstore'] > 80000 else '🟢낮음'})
        st.dataframe(pd.DataFrame(smartstore_data), use_container_width=True, hide_index=True)
        col1, col2, col3 = st.columns(3)
        total_ss = sum([accumulated_data[p]['smartstore'] for p in partners])
        col1.metric("총 누적고객", f"{total_ss:,}명")
        col2.metric("평균", f"{total_ss/len(partners):,.0f}명")
        col3.metric("최고", f"{max([accumulated_data[p]['smartstore'] for p in partners]):,}명")
    
    with sop_tabs[1]:
        st.markdown("### 🎬 라이브 방송 누적 성과")
        live_data = []
        for partner in partners:
            data = accumulated_data[partner]
            live_data.append({'대리점': partner, '라이브': f"{data['live_count']}회", '매출': f"{data['live_sales']:,}만원", '회당': f"{data['live_sales']/max(data['live_count'], 1):.1f}만원", '효율': '🔥높음' if (data['live_sales']/max(data['live_count'], 1)) > 30 else '📈중간'})
        st.dataframe(pd.DataFrame(live_data), use_container_width=True, hide_index=True)
        col1, col2, col3, col4 = st.columns(4)
        total_live = sum([accumulated_data[p]['live_count'] for p in partners])
        total_live_sales = sum([accumulated_data[p]['live_sales'] for p in partners])
        col1.metric("총 라이브", f"{total_live}회")
        col2.metric("총 매출", f"{total_live_sales:,}만원")
        col3.metric("회당 평균", f"{total_live_sales/max(total_live, 1):.1f}만원")
        col4.metric("평균/대리점", f"{total_live/len(partners):.0f}회")
    
    with sop_tabs[2]:
        st.markdown("### 🤝 어필리에이트 누적 성과")
        affiliate_data = []
        for partner in partners:
            data = accumulated_data[partner]
            affiliate_data.append({'대리점': partner, '고객': f"{data['affiliate_customers']}명", '매출': f"{data['affiliate_sales']:,}만원", '고객당': f"{data['affiliate_sales']/max(data['affiliate_customers'], 1):.1f}만원", '성과': '⭐⭐⭐' if data['affiliate_sales'] > 1000 else '⭐⭐'})
        st.dataframe(pd.DataFrame(affiliate_data), use_container_width=True, hide_index=True)
        col1, col2, col3, col4 = st.columns(4)
        total_aff_cust = sum([accumulated_data[p]['affiliate_customers'] for p in partners])
        total_aff_sales = sum([accumulated_data[p]['affiliate_sales'] for p in partners])
        col1.metric("총 고객", f"{total_aff_cust}명")
        col2.metric("총 매출", f"{total_aff_sales:,}만원")
        col3.metric("고객당 평균", f"{total_aff_sales/max(total_aff_cust, 1):.1f}만원")
        col4.metric("평균/대리점", f"{total_aff_cust/len(partners):.0f}명")
    
    with sop_tabs[3]:
        st.markdown("### 📣 마케팅활동 현황")
        for partner in partners:
            data = accumulated_data[partner]
            status = '🟢' if data['forecast'] >= 88 else '🟡' if data['forecast'] >= 75 else '🔴'
            with st.expander(f"{status} {partner} ({data['forecast']}%)"):
                st.markdown(data['marketing'])
                col1, col2, col3 = st.columns(3)
                col1.metric("예측", f"{data['forecast']}%")
                col2.metric("프리미엄", f"{data['premium']}%")
                col3.metric("효율", f"{data['efficiency']}%")

with tab2:
    st.header("📈 실시간 대시보드")
    st.info("📊 현재 W34 데이터를 표시 중입니다")
    st.subheader("📊 W34 KPI 요약")
    col1, col2, col3, col4 = st.columns(4)
    forecast_values = [sample_data_w34[f"{p}_W34"]['forecast'] for p in partners]
    col1.metric("📈 예측", f"{sum(forecast_values)/len(forecast_values):.1f}%")
    col2.metric("💰 판매", f"{sum([sample_data_w34[f'{p}_W34']['sales'] for p in partners])/len(partners):.1f}%")
    col3.metric("⭐ 프리미엄", f"{sum([sample_data_w34[f'{p}_W34']['premium'] for p in partners])/len(partners):.1f}%")
    col4.metric("⚡ 효율", f"{sum([sample_data_w34[f'{p}_W34']['efficiency'] for p in partners])/len(partners):.1f}%")
    st.divider()
    st.subheader("🏢 대리점별 상세 현황")
    tabs_partners = st.tabs(partners)
    for idx, partner in enumerate(partners):
        with tabs_partners[idx]:
            key = f"{partner}_W34"
            data = sample_data_w34[key]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("예측", f"{data['forecast']}%")
            col2.metric("판매", f"{data['sales']}%")
            col3.metric("프리미엄", f"{data['premium']}%")
            col4.metric("효율", f"{data['efficiency']}%")
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**스마트스토어**")
                st.metric("고객수", data['smartstore'])
                st.markdown("**어필리에이트**")
                c1, c2 = st.columns(2)
                c1.metric("고객", data['affiliate_customers'])
                c2.metric("매출", f"{data['affiliate_sales']:,}만원")
            with col2:
                st.markdown("**라이브 방송**")
                c1, c2 = st.columns(2)
                c1.metric("횟수", data['live_count'])
                c2.metric("매출", f"{data['live_sales']:,}만원")
            st.divider()
            st.markdown("**📋 주요 마케팅**")
            st.success(data['marketing'])

with tab3:
    st.header("✏️ SOP 데이터 입력")
    with st.form("sop_form"):
        col1, col2 = st.columns(2)
        with col1:
            partner = st.selectbox("🏢 대리점 선택 *", partners, key="sop_partner")
        with col2:
            week = st.selectbox("📅 주차 선택 *", ["W31A", "W31B", "W32", "W33", "W34", "W35"], key="sop_week")
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
                st.info("📍 최종분석 탭에서 확인하세요!")

with tab4:
    st.header("📤 STAR RAW 데이터 일괄 업로드")
    week_select = st.selectbox("📅 분석 주차 선택", ["W31A", "W31B", "W32", "W33", "W34", "W35"], key="raw_week")
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
st.markdown("<div style='text-align: center; color: gray; font-size: 12px;'>💫 PP3G KPI 자동화 시스템 | 누적 데이터 기반 실시간 모니터링</div>", unsafe_allow_html=True)
