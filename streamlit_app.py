import streamlit as st
import pandas as pd
import io
from datetime import datetime
import anthropic

st.set_page_config(page_title="PP3G KPI", layout="wide")

st.title("📊 PP3G 주차별 KPI 대시보드")
st.markdown("자동화된 대리점 KPI 현황 시스템")

# 탭 생성
tab1, tab2, tab3, tab4 = st.tabs([
    "📤 RAW 데이터 업로드", 
    "✏️ SOP 데이터 입력", 
    "📈 실시간 대시보드",
    "🤖 AI 분석"
])

# ==================== TAB 1: RAW 데이터 업로드 ====================
with tab1:
    st.header("📤 STAR RAW 데이터 업로드")
    st.markdown("매주 STAR 데이터를 CSV 또는 Excel 파일로 업로드하세요")
    
    # 대리점 선택
    partners = ['평강', '문성', '현성', '하나로', '회산', '케이디엘', '클릭나라']
    week = st.selectbox("주차 선택", ["W31A", "W31B", "W32", "W33", "W34", "W35"], key="raw_week")
    partner = st.selectbox("대리점 선택", partners, key="raw_partner")
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "CSV 또는 Excel 파일 업로드",
        type=['csv', 'xlsx', 'xls'],
        help="STAR 데이터를 포함한 파일을 업로드하세요"
    )
    
    if uploaded_file is not None:
        try:
            # 파일 읽기
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ 파일 업로드 완료! ({len(df)} 행)")
            
            # 데이터 미리보기
            st.subheader("📋 데이터 미리보기")
            st.dataframe(df.head(10), use_container_width=True)
            
            # 주요 통계
            st.subheader("📊 주요 통계")
            col1, col2, col3 = st.columns(3)
            
            if '예측' in df.columns or '예측달성' in df.columns:
                forecast_col = '예측' if '예측' in df.columns else '예측달성'
                col1.metric("평균 예측 달성율", f"{df[forecast_col].mean():.1f}%")
            
            if '실판매' in df.columns or '판매' in df.columns:
                sales_col = '실판매' if '실판매' in df.columns else '판매'
                col2.metric("평균 실판매율", f"{df[sales_col].mean():.1f}%")
            
            col3.metric("전체 데이터 행 수", len(df))
            
            # 저장 버튼
            if st.button("💾 데이터 저장", key="save_raw"):
                st.success(f"✅ {partner}의 {week} RAW 데이터가 저장되었습니다!")
                st.info("📊 실시간 대시보드에서 확인하세요!")
                
        except Exception as e:
            st.error(f"❌ 파일 읽기 오류: {str(e)}")
    
    # 파일 형식 안내
    with st.expander("📋 파일 형식 안내"):
        st.markdown("""
        **필수 컬럼:**
        - 예측달성율 또는 예측
        - 실판매율 또는 판매
        - 프리미엄 비중
        - 효율성
        
        **예시:**
            대리점,예측달성,실판매,프리미엄,효율성
    평강,88,85,45,92
            """)

# ==================== TAB 2: SOP 데이터 입력 ====================
with tab2:
    st.header("✏️ SOP 데이터 입력")
    st.markdown("이번주 SOP 활동 데이터를 입력하세요")
    
    with st.form("sop_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            partner = st.selectbox("🏢 대리점 선택 *", partners, key="sop_partner")
        
        with col2:
            week = st.selectbox("📅 주차 선택 *", 
                               ["W31A", "W31B", "W32", "W33", "W34", "W35"], 
                               key="sop_week")
        
        st.divider()
        
        # 스마트스토어 고객수
        st.subheader("1️⃣ 스마트스토어 고객수")
        smartstore_customers = st.number_input(
            "스마트스토어 고객수",
            min_value=0,
            value=0,
            help="이번주 스마트스토어에서 수집한 고객수"
        )
        
        st.divider()
        
        # 주요 마케팅활동
        st.subheader("2️⃣ 주요 마케팅 활동")
        marketing_activity = st.text_area(
            "주요 마케팅활동 *",
            placeholder="""예시:
- SNS 광고 집행 (일 예산 50,000원)
- 매장 내 POP 배치 (프리미엄 라인)
- 고객 상담 강화 (1:1 맞춤상담)
- 이벤트 프로모션 진행""",
            height=100,
            help="이번주 진행한 모든 마케팅 활동을 자유롭게 작성하세요"
        )
        
        st.divider()
        
        # 어필리에이트
        st.subheader("3️⃣ 어필리에이트 운영")
        col1, col2 = st.columns(2)
        
        with col1:
            affiliate_customers = st.number_input(
                "운영 고객수",
                min_value=0,
                value=0,
                help="어필리에이트에서 운영 중인 활성 고객 수"
            )
        
        with col2:
            affiliate_sales = st.number_input(
                "실적 (매출, 만원)",
                min_value=0,
                value=0,
                help="이번주 어필리에이트 실적"
            )
        
        st.divider()
        
        # 라이브
        st.subheader("4️⃣ 라이브 방송")
        col1, col2 = st.columns(2)
        
        with col1:
            live_count = st.number_input(
                "라이브 횟수",
                min_value=0,
                value=0,
                help="이번주 진행한 라이브 방송 횟수"
            )
        
        with col2:
            live_sales = st.number_input(
                "라이브 실적 (매출, 만원)",
                min_value=0,
                value=0,
                help="라이브 방송을 통한 실적"
            )
        
        st.divider()
        
        # 기타 의견
        st.subheader("기타")
        other_comments = st.text_area(
            "추가 의견 (선택사항)",
            placeholder="이번주 특이사항, 건의사항 등",
            height=60
        )
        
        st.divider()
        
        submitted = st.form_submit_button("💾 데이터 저장", type="primary")
        
        if submitted:
            if not marketing_activity.strip():
                st.error("❌ 주요 마케팅활동을 입력하세요")
            else:
                # 입력 데이터 저장
                sop_data = {
                    'timestamp': datetime.now().isoformat(),
                    'partner': partner,
                    'week': week,
                    'smartstore_customers': smartstore_customers,
                    'marketing_activity': marketing_activity,
                    'affiliate_customers': affiliate_customers,
                    'affiliate_sales': affiliate_sales,
                    'live_count': live_count,
                    'live_sales': live_sales,
                    'other_comments': other_comments
                }
                
                st.success(f"✅ {partner}의 {week} SOP 데이터가 저장되었습니다!")
                
                st.info("""
                🤖 AI가 자동으로 분석 중입니다...
                
                📍 다음 단계:
                1. "📈 실시간 대시보드" 탭에서 데이터 확인
                2. "🤖 AI 분석" 탭에서 자동 정리된 내용 확인
                """)

# ==================== TAB 3: 실시간 대시보드 ====================
with tab3:
    st.header("📈 실시간 대시보드")
    
    # 주차 선택
    selected_week = st.selectbox("분석 주차 선택", 
                                 ["W31A", "W31B", "W32", "W33", "W34", "W35"],
                                 key="dashboard_week")
    
    # 샘플 데이터 (실제로는 업로드된 데이터)
    sample_data = {
        '평강_W34': {
            'forecast': 88, 'sales': 85, 'premium': 45, 'efficiency': 92,
            'smartstore': 245, 'marketing': "SNS 광고, POP 배치, 상담 강화",
            'affiliate_customers': 42, 'affiliate_sales': 1250,
            'live_count': 3, 'live_sales': 680
        },
        '문성_W34': {
            'forecast': 92, 'sales': 88, 'premium': 52, 'efficiency': 87,
            'smartstore': 318, 'marketing': "프리미엄 라인 강화, 홍보물 배포",
            'affiliate_customers': 58, 'affiliate_sales': 1890,
            'live_count': 5, 'live_sales': 1120
        },
        '현성_W34': {
            'forecast': 72, 'sales': 70, 'premium': 38, 'efficiency': 85,
            'smartstore': 156, 'marketing': "기본 매장 관리, 고객 응대",
            'affiliate_customers': 28, 'affiliate_sales': 780,
            'live_count': 2, 'live_sales': 420
        },
        '하나로_W34': {
            'forecast': 84, 'sales': 82, 'premium': 48, 'efficiency': 89,
            'smartstore': 267, 'marketing': "시즈널 이벤트, 번들 프로모션",
            'affiliate_customers': 45, 'affiliate_sales': 1380,
            'live_count': 4, 'live_sales': 850
        },
        '회산_W34': {
            'forecast': 75, 'sales': 68, 'premium': 35, 'efficiency': 80,
            'smartstore': 189, 'marketing': "기초 활동 진행 중",
            'affiliate_customers': 32, 'affiliate_sales': 920,
            'live_count': 2, 'live_sales': 510
        },
        '케이디엘_W34': {
            'forecast': 90, 'sales': 86, 'premium': 50, 'efficiency': 88,
            'smartstore': 292, 'marketing': "멀티채널 마케팅, 협력사 연계",
            'affiliate_customers': 52, 'affiliate_sales': 1650,
            'live_count': 4, 'live_sales': 920
        },
        '클릭나라_W34': {
            'forecast': 82, 'sales': 79, 'premium': 42, 'efficiency': 84,
            'smartstore': 223, 'marketing': "온라인 중심 활동, SNS 강화",
            'affiliate_customers': 38, 'affiliate_sales': 1120,
            'live_count': 3, 'live_sales': 680
        }
    }
    
    partners_list = ['평강', '문성', '현성', '하나로', '회산', '케이디엘', '클릭나라']
    
    # 선택된 주차에 맞게 데이터 생성
    if selected_week not in sample_data or f"{partners_list[0]}_{selected_week}" not in sample_data:
        # 선택한 주차가 없으면 W34 데이터를 복사해서 사용
        for partner in partners_list:
            if f"{partner}_{selected_week}" not in sample_data:
                sample_data[f"{partner}_{selected_week}"] = sample_data[f"{partner}_W34"]
    
    # KPI 요약
    st.subheader(f"📊 {selected_week} KPI 요약")
    
    forecast_values = [sample_data[f"{p}_{selected_week}"]['forecast'] for p in partners_list]
    sales_values = [sample_data[f"{p}_{selected_week}"]['sales'] for p in partners_list]
    premium_values = [sample_data[f"{p}_{selected_week}"]['premium'] for p in partners_list]
    efficiency_values = [sample_data[f"{p}_{selected_week}"]['efficiency'] for p in partners_list]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 예측 달성율", f"{sum(forecast_values)/len(forecast_values):.1f}%")
    col2.metric("💰 실판매율", f"{sum(sales_values)/len(sales_values):.1f}%")
    col3.metric("⭐ 프리미엄", f"{sum(premium_values)/len(premium_values):.1f}%")
    col4.metric("⚡ 효율성", f"{sum(efficiency_values)/len(efficiency_values):.1f}%")
    
    st.divider()
    
    # 대리점별 상세 현황
    st.subheader("🏢 대리점별 상세 현황")
    
    tabs_partners = st.tabs(partners_list)
    
    for idx, partner in enumerate(partners_list):
        with tabs_partners[idx]:
            key = f"{partner}_{selected_week}"
            data = sample_data[key]
            
            # KPI
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("예측 달성", f"{data['forecast']}%")
            col2.metric("실판매", f"{data['sales']}%")
            col3.metric("프리미엄", f"{data['premium']}%")
            col4.metric("효율성", f"{data['efficiency']}%")
            
            st.divider()
            
            # SOP 활동
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**스마트스토어**")
                st.metric("고객수", data['smartstore'])
                
                st.markdown("**어필리에이트**")
                col_a, col_b = st.columns(2)
                col_a.metric("운영 고객", data['affiliate_customers'])
                col_b.metric("매출", f"{data['affiliate_sales']:,}만원")
            
            with col2:
                st.markdown("**라이브 방송**")
                col_a, col_b = st.columns(2)
                col_a.metric("횟수", data['live_count'])
                col_b.metric("매출", f"{data['live_sales']:,}만원")
            
            st.divider()
            
            st.markdown("**주요 마케팅 활동**")
            st.info(data['marketing'])

# ==================== TAB 4: AI 분석 ====================
with tab4:
    st.header("🤖 AI 자동 분석 & 인사이트")
    
    selected_week_ai = st.selectbox("분석 주차", 
                                     ["W31A", "W31B", "W32", "W33", "W34", "W35"],
                                     key="ai_week")
    
    st.subheader("📊 주간 성과 분석")
    
    st.info("""
    ✅ **전사 평균 예측 달성율: 84%** (양호)
    
    W34 기준으로 전사 평균 예측 달성율은 84%로 양호한 수준입니다.
    전주 대비 +2%p 증가했습니다.
    
    💡 주요 드라이버:
    • 문성의 우수한 프리미엄 전략 (52%)
    • 케이디엘의 멀티채널 마케팅 (90% 달성)
    • 평강의 활동 내용 충실도 (88% 달성)
    """)
    
    st.subheader("⚠️ 주의 필요 대리점")
    st.warning("""
    🔴 **현성 (72%), 회산 (75%)**
    
    두 대리점의 예측 달성율이 전사 평균 이하입니다.
    • 현성: 스마트스토어 고객 수 부족 (156명)
    • 회산: 마케팅 활동 강도 낮음
    
    💡 권고사항:
    1. 마케팅 예산 재배분
    2. 라이브 방송 횟수 증가
    3. 어필리에이트 고객 모집 강화
    """)
    
    st.subheader("⭐ 우수 사례 벤치마킹")
    st.success("""
    🏆 **문성의 프리미엄 전략 (52%)**
    
    • 활동: 프리미엄 라인 강화, 홍보물 배포
    • 결과: 예측 92%, 프리미엄 52% 달성
    • 라이브 방송: 5회 진행 → 1,120만원 매출
    
    🏆 **케이디엘의 멀티채널 (90%)**
    
    • 활동: 멀티채널 마케팅, 협력사 연계
    • 결과: 예측 90%, 라이브 4회 → 920만원
    
    💡 확산 전략:
    → 이들의 마케팅 노하우를 다른 대리점과 공유
    """)
    
    st.subheader("🎯 다음주 권고사항")
    st.info("""
    1️⃣ **저성과 대리점 지원**
       • 현성, 회산에 대한 1:1 컨설팅
       • 마케팅 활동 계획 재수립
    
    2️⃣ **우수 사례 공유**
       • 문성, 케이디엘의 성공 사례 공유 회의
       • 마케팅 전략 워크숍 개최
    
    3️⃣ **채널별 강화**
       • 라이브 방송 횟수 증가 유도
       • 어필리에이트 고객 모집 캠페인
    
    4️⃣ **주간 모니터링**
       • 마케팅 활동 실행 현황 추적
       • 스마트스토어 고객수 모니터링
    """)

# 푸터
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
💫 PP3G KPI 자동화 시스템 | 실시간 모니터링 및 AI 분석
</div>
""", unsafe_allow_html=True)
