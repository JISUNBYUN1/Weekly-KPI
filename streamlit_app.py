import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="PP3G KPI", layout="wide")
st.title("📊 PP3G 주차별 KPI 대시보드")
st.markdown("자동화된 대리점 KPI 현황 시스템 | 누적 데이터(1월~8월) 기반 분석")

partners = ['평강', '문성', '케이디엘', '하나로', '회산', '현성', '클릭나라']
months = ['1월', '2월', '3월', '4월', '5월', '6월', '7월']

store_monthly = {
    '평강': {'1월': 130610, '2월': 132629, '3월': 134648, '4월': 139797, '5월': 143211, '6월': 145622, '7월': 148134},
    '문성': {'1월': 109266, '2월': 111203, '3월': 113313, '4월': 114299, '5월': 116412, '6월': 118524, '7월': 120635},
    '케이디엘': {'1월': 86331, '2월': 88277, '3월': 90318, '4월': 91767, '5월': 94210, '6월': 96453, '7월': 98756},
    '하나로': {'1월': 79682, '2월': 81290, '3월': 83834, '4월': 86598, '5월': 89234, '6월': 91856, '7월': 94212},
    '회산': {'1월': 85164, '2월': 90585, '3월': 94421, '4월': 96767, '5월': 99123, '6월': 101456, '7월': 103789},
    '현성': {'1월': 177569, '2월': 181050, '3월': 184400, '4월': 188534, '5월': 191267, '6월': 194123, '7월': 197456},
    '클릭나라': {'1월': 76553, '2월': 78473, '3월': 80291, '4월': 80888, '5월': 82734, '6월': 84567, '7월': 86234}
}

live_monthly = {
    '평강': {'1월': 10, '2월': 45, '3월': 52, '4월': 68, '5월': 75, '6월': 82, '7월': 89},
    '문성': {'1월': 3, '2월': 28, '3월': 38, '4월': 48, '5월': 56, '6월': 62, '7월': 71},
    '케이디엘': {'1월': 10, '2월': 38, '3월': 45, '4월': 52, '5월': 60, '6월': 67, '7월': 75},
    '하나로': {'1월': 0, '2월': 42, '3월': 55, '4월': 68, '5월': 78, '6월': 88, '7월': 98},
    '회산': {'1월': 15, '2월': 48, '3월': 58, '4월': 68, '5월': 78, '6월': 88, '7월': 98},
    '현성': {'1월': 8, '2월': 32, '3월': 42, '4월': 52, '5월': 62, '6월': 72, '7월': 82},
    '클릭나라': {'1월': 12, '2월': 35, '3월': 42, '4월': 50, '5월': 58, '6월': 65, '7월': 73}
}

affiliate_monthly = {
    '평강': {'1월': 28, '2월': 31, '3월': 35, '4월': 37, '5월': 38, '6월': 40, '7월': 38},
    '문성': {'1월': 12, '2월': 22, '3월': 33, '4월': 40, '5월': 42, '6월': 44, '7월': 44},
    '케이디엘': {'1월': 15, '2월': 32, '3월': 40, '4월': 45, '5월': 46, '6월': 47, '7월': 46},
    '하나로': {'1월': 20, '2월': 32, '3월': 38, '4월': 40, '5월': 41, '6월': 42, '7월': 42},
    '회산': {'1월': 18, '2월': 32, '3월': 37, '4월': 39, '5월': 40, '6월': 41, '7월': 40},
    '현성': {'1월': 42, '2월': 68, '3월': 82, '4월': 92, '5월': 95, '6월': 96, '7월': 96},
    '클릭나라': {'1월': 22, '2월': 45, '3월': 58, '4월': 62, '5월': 63, '6월': 64, '7월': 63}
}

kpi_metrics = {
    '평강': {'forecast': 88, 'sales': 85, 'premium': 45, 'efficiency': 92},
    '문성': {'forecast': 92, 'sales': 88, 'premium': 52, 'efficiency': 87},
    '케이디엘': {'forecast': 90, 'sales': 86, 'premium': 50, 'efficiency': 88},
    '하나로': {'forecast': 84, 'sales': 82, 'premium': 48, 'efficiency': 89},
    '회산': {'forecast': 75, 'sales': 68, 'premium': 35, 'efficiency': 80},
    '현성': {'forecast': 72, 'sales': 70, 'premium': 38, 'efficiency': 85},
    '클릭나라': {'forecast': 82, 'sales': 79, 'premium': 42, 'efficiency': 84}
}

detailed_activities = {
    '평강': [{'모델': 'TV 냉장고', '내용': '네이버 첫/재구매 1만원 쿠폰', '시기': '1월 초', '방식': '네이버쇼핑'}, {'모델': '모든 상품', '내용': '알림쿠폰 1만원 증정', '시기': '1월~지속', '방식': '앱 알림받기'}, {'모델': 'TV 냉장고', '내용': 'SA & GFA 광고 최적화', '시기': '주단위', '방식': '네이버 광고'}, {'모델': '전체', '내용': '스마트스토어 배너 관리', '시기': '주단위', '방식': '배너 업데이트'}],
    '문성': [{'모델': '냉장고', '내용': '숏클립 업로드 (월 2-3회→주 3-4회)', '시기': '주단위', '방식': '네이버'}, {'모델': '전체', '내용': '알림쿠폰 활용', '시기': '지속', '방식': '네이버/쿠팡'}, {'모델': '프리미엄', '내용': '삼세페 행사 대응', '시기': '1월 2-11일', '방식': '행사 광고'}, {'모델': '냉장고', '내용': 'AI라이브 진행', '시기': '주 3회', '방식': '네이버 라이브'}],
    '케이디엘': [{'모델': '냉장고/식기세척기', '내용': '라이브 카카오톡 알림', '시기': '라이브 전', '방식': 'KakaoTalk'}, {'모델': '전체', '내용': '자사몰 정비 (판매기능 개선)', '시기': '1월 초', '방식': 'kdl.kr'}, {'모델': 'TV 냉장고', '내용': '유튜브 인스타 쇼츠', '시기': '주 2-3회', '방식': 'SNS'}, {'모델': '프리미엄', '내용': 'AI라이브 세팅', '시기': '주 2회', '방식': 'AI 쇼호스트'}],
    '하나로': [{'모델': 'TV 냉장고', '내용': '네이버 첫구매 1만원 쿠폰', '시기': '1월 초', '방식': '네이버'}, {'모델': '전체', '내용': '네이버 검색광고 상향', '시기': '1월~', '방식': '30만→70만 예산'}, {'모델': 'OEM', '내용': '자사몰 오픈', '시기': '1월 3주차', '방식': '하나로 자사 쇼핑몰'}, {'모델': '전체', '내용': '토스쇼핑 입점', '시기': '1월 중순', '방식': '신규 채널'}],
    '회산': [{'모델': 'TV 세탁기', '내용': '알림쿠폰 1만원 증정', '시기': '지속', '방식': '네이버 앱'}, {'모델': '세탁기/건조기', '내용': 'GFA 광고 + 성과형 지면', '시기': '일단위', '방식': '네이버 광고'}, {'모델': 'TV 세탁기', '내용': '브랜드커넥트 캠페인', '시기': '월단위', '방식': '어필리에이트'}, {'모델': '전체', '내용': '몰 UI/UX 지속 업데이트', '시기': '주단위', '방식': '온라인몰'}],
    '현성': [{'모델': '정수기 필터', '내용': '블로그/유튜브 마케팅', '시기': '주 2-3회', '방식': 'SNS + 검색'}, {'모델': '정수기 필터', '내용': '알림쿠폰 1천원 증정', '시기': '지속', '방식': '네이버 앱'}, {'모델': '정수기', '내용': '쇼핑커넥트 설정', '시기': '1월 초', '방식': '어필리에이트'}, {'모델': '정수기', '내용': '삼세페 행사 홍보', '시기': '1월 중순', '방식': '배너/광고'}],
    '클릭나라': [{'모델': '전체', '내용': '알림쿠폰 1천원→3천원 인상', '시기': '1월 초', '방식': '가격 강화'}, {'모델': '냉장고/식기세척기', '내용': 'DA 광고 예산 상향', '시기': '1월~', '방식': '일 4만→6만'}, {'모델': '냉장고/식기세척기', '내용': '검색광고 예산 증액', '시기': '1월~', '방식': '일 60만→80만'}, {'모델': '프리미엄', '내용': 'G마켓/지마켓 라이브', '시기': '주 2-3회', '방식': '멀티채널'}]
}

tab1, tab2, tab3, tab4 = st.tabs(["🤖 최종분석", "📈 실시간 대시보드", "✏️ SOP 데이터 입력", "📤 RAW 데이터 업로드"])

with tab1:
    st.header("🤖 누적 성과 분석")
    col1, col2 = st.columns(2)
    with col1:
        selected_month = st.selectbox("📅 월 선택", months, index=6)
    with col2:
        selected_partner = st.selectbox("👥 대리점 선택", partners)
    
    st.markdown(f"### 📊 {selected_month} - {selected_partner} 상세 현황")
    st.divider()
    
    with st.expander("📱 스마트스토어 고객수", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**월별 고객수 추이**")
            month_data = [{'월': m, f'{selected_partner}': f"{store_monthly[selected_partner][m]:,}명"} for m in months]
            st.dataframe(pd.DataFrame(month_data), use_container_width=True, hide_index=True)
        with col2:
            st.markdown(f"**{selected_month} 대리점별**")
            partner_data = [{'대리점': p, '고객수': f"{store_monthly[p][selected_month]:,}명"} for p in partners]
            st.dataframe(pd.DataFrame(partner_data), use_container_width=True, hide_index=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📍 선택", f"{store_monthly[selected_partner][selected_month]:,}명")
        col2.metric("📊 평균", f"{np.mean([store_monthly[p][selected_month] for p in partners]):,.0f}명")
        col3.metric("🔝 최고", f"{max([store_monthly[p][selected_month] for p in partners]):,}명")
    
    st.divider()
    
    with st.expander("🎬 라이브 방송", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**월별 라이브**")
            live_data = [{'월': m, f'{selected_partner}': f"{live_monthly[selected_partner][m]}회"} for m in months]
            st.dataframe(pd.DataFrame(live_data), use_container_width=True, hide_index=True)
        with col2:
            st.markdown(f"**{selected_month} 대리점별**")
            live_comp = [{'대리점': p, '방송': f"{live_monthly[p][selected_month]}회"} for p in partners]
            st.dataframe(pd.DataFrame(live_comp), use_container_width=True, hide_index=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📍 선택", f"{live_monthly[selected_partner][selected_month]}회")
        col2.metric("📊 평균", f"{np.mean([live_monthly[p][selected_month] for p in partners]):.1f}회")
        col3.metric("🔝 최고", f"{max([live_monthly[p][selected_month] for p in partners])}회")
    
    st.divider()
    
    with st.expander("🤝 어필리에이트", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**월별 고객**")
            aff_data = [{'월': m, f'{selected_partner}': f"{affiliate_monthly[selected_partner][m]}명"} for m in months]
            st.dataframe(pd.DataFrame(aff_data), use_container_width=True, hide_index=True)
        with col2:
            st.markdown(f"**{selected_month} 대리점별**")
            aff_comp = [{'대리점': p, '고객': f"{affiliate_monthly[p][selected_month]}명"} for p in partners]
            st.dataframe(pd.DataFrame(aff_comp), use_container_width=True, hide_index=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📍 선택", f"{affiliate_monthly[selected_partner][selected_month]}명")
        col2.metric("📊 평균", f"{np.mean([affiliate_monthly[p][selected_month] for p in partners]):.0f}명")
        col3.metric("🔝 최고", f"{max([affiliate_monthly[p][selected_month] for p in partners])}명")
    
    st.divider()
    
    with st.expander("📊 계수 영역 (KPI)", expanded=True):
        kpi = kpi_metrics[selected_partner]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📈 예측", f"{kpi['forecast']}%")
        col2.metric("💰 판매", f"{kpi['sales']}%")
        col3.metric("⭐ 프리미엄", f"{kpi['premium']}%")
        col4.metric("⚡ 효율", f"{kpi['efficiency']}%")
        
        st.divider()
        st.markdown("**전사 KPI**")
        kpi_table = [{'대리점': p, '예측': f"{kpi_metrics[p]['forecast']}%", '판매': f"{kpi_metrics[p]['sales']}%", '프리미엄': f"{kpi_metrics[p]['premium']}%", '효율': f"{kpi_metrics[p]['efficiency']}%"} for p in partners]
        st.dataframe(pd.DataFrame(kpi_table), use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader(f"📋 {selected_partner} 상세 마케팅활동")
    act_table = []
    for idx, a in enumerate(detailed_activities[selected_partner], 1):
        act_table.append({'번호': idx, '모델': a['모델'], '내용': a['내용'], '시기': a['시기'], '방식': a['방식']})
    st.dataframe(pd.DataFrame(act_table), use_container_width=True, hide_index=True)

with tab2:
    st.header("📈 실시간 대시보드")
    col1, col2, col3 = st.columns(3)
    col1.metric("📱 평균 고객", f"{np.mean([store_monthly[p]['7월'] for p in partners]):.0f}명")
    col2.metric("🎬 평균 라이브", f"{np.mean([live_monthly[p]['7월'] for p in partners]):.1f}회")
    col3.metric("🤝 평균 어필", f"{np.mean([affiliate_monthly[p]['7월'] for p in partners]):.0f}명")
    
    st.divider()
    tabs_p = st.tabs(partners)
    for idx, p in enumerate(partners):
        with tabs_p[idx]:
            col1, col2, col3 = st.columns(3)
            col1.metric("📱", f"{store_monthly[p]['7월']:,}명")
            col2.metric("🎬", f"{live_monthly[p]['7월']}회")
            col3.metric("🤝", f"{affiliate_monthly[p]['7월']}명")

with tab3:
    st.header("✏️ SOP 데이터 입력")
    with st.form("sop_form"):
        col1, col2 = st.columns(2)
        partner = st.selectbox("🏢 대리점", partners, key="sp")
        week = st.selectbox("📅 주차", ["W34", "W35"], key="sw")
        st.subheader("1️⃣ 스마트스토어")
        smartstore = st.number_input("고객수", min_value=0)
        st.subheader("2️⃣ 마케팅활동")
        marketing = st.text_area("내용 *", height=80)
        st.subheader("3️⃣ 어필리에이트")
        col1, col2 = st.columns(2)
        aff_c = st.number_input("고객", min_value=0, key="ac")
        aff_s = st.number_input("매출(만원)", min_value=0, key="as")
        st.subheader("4️⃣ 라이브")
        col1, col2 = st.columns(2)
        live_c = st.number_input("횟수", min_value=0, key="lc")
        live_s = st.number_input("매출(만원)", min_value=0, key="ls")
        if st.form_submit_button("💾 저장", type="primary"):
            if marketing.strip(): st.success(f"✅ {partner} {week} 저장!")
            else: st.error("❌ 마케팅활동 입력")

with tab4:
    st.header("📤 RAW 데이터 업로드")
    week = st.selectbox("📅 주차", ["W34", "W35"], key="rw")
    uploaded = st.file_uploader("파일", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            try:
                df = pd.read_excel(f) if not f.name.endswith('.csv') else pd.read_csv(f)
                st.success(f"✅ {f.name}")
                st.dataframe(df.head(5), use_container_width=True)
            except: st.error(f"❌ {f.name}")
        if st.button("💾 저장"): st.success(f"✅ {week} 저장!")

st.divider()
st.markdown("<div style='text-align: center; color: gray; font-size: 12px;'>💫 PP3G KPI | 누적 데이터 기반</div>", unsafe_allow_html=True)
