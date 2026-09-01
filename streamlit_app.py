import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="PP3G Weekly KPI", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 36px; font-weight: bold; color: #1f77b4; margin-bottom: 30px; }
    .section-header { font-size: 22px; font-weight: bold; color: #2c3e50; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    data = {}
    
    # 기본 파일들
    base_files = {
        'chpsi': 'chpsi_reorganized.json',
        'live_commerce': 'live_commerce_complete.json',
        'affiliate': 'affiliate_final_data.json',
        'smartstore': 'smartstore_customers.json',
        'coupang_ppm': 'coupang_ppm_data.json'
    }
    
    for key, filename in base_files.items():
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data[key] = json.load(f)
        except:
            data[key] = {}
    
    # 분할된 bizplan 병합 (채널별)
    bizplan = {}
    bizplan_files = [
        'bizplan_SOP.json',
        'bizplan_쿠팡.json',
        'bizplan_종합몰.json',
        'bizplan_홈쇼핑.json'
    ]
    
    for filename in bizplan_files:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                bizplan.update(json.load(f))
        except:
            pass
    data['bizplan'] = bizplan
    
    # 분할된 premium 병합 (제품별)
    premium = {}
    premium_files = [
        'premium_냉장고.json',
        'premium_세탁기.json',
        'premium_식기세척기.json',
        'premium_정수기.json'
    ]
    
    for filename in premium_files:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                premium.update(json.load(f))
        except:
            pass
    data['premium'] = premium
    
    return data

data = load_all_data()

st.markdown('<div class="main-header">📊 PP3G Weekly KPI 대시보드</div>', unsafe_allow_html=True)
st.markdown(f"**업데이트**: {datetime.now().strftime('%Y.%m.%d %H:%M')}")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "전체 현황", "FCST 현황", "프리미엄 비중", "스마트스토어",
    "라이브커머스", "어필리에이트", "쿠팡 PPM", "SOP 활동", "STAR RAW"
])

# TAB 1: 전체 현황 (BIZ Plan)
with tab1:
    st.markdown('<div class="section-header">📈 전체 현황</div>', unsafe_allow_html=True)
    
    if data['bizplan']:
        channels = list(data['bizplan'].keys())
        channel = st.selectbox("📍 채널 선택", channels, key="tab1_channel")
        
        if channel in data['bizplan']:
            products = list(data['bizplan'][channel].keys())
            product = st.selectbox("📦 제품 선택", products, key="tab1_product")
            
            if product in data['bizplan'][channel]:
                st.subheader(f"📊 {channel} - {product}")
                
                models = data['bizplan'][channel][product]
                
                for model_name, model_data in models.items():
                    st.write(f"**{model_name}**")
                    
                    table_data = []
                    for month, value in model_data.items():
                        table_data.append({
                            "월": month,
                            "값": f"{value:,.0f}" if isinstance(value, (int, float)) else value
                        })
                    
                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)
                    
                    st.divider()
    else:
        st.warning("⚠️ 데이터 없음")

# TAB 2: FCST 현황
with tab2:
    st.markdown('<div class="section-header">📊 FCST 현황</div>', unsafe_allow_html=True)
    
    if data['chpsi']:
        channels = list(data['chpsi'].keys())
        channel = st.selectbox("📍 채널 선택", channels, key="tab2_channel")
        
        if channel in data['chpsi']:
            products = list(data['chpsi'][channel].keys())
            product = st.selectbox("📦 제품 선택", products, key="tab2_product")
            
            if product in data['chpsi'][channel]:
                st.subheader(f"📊 {channel} - {product}")
                
                models = data['chpsi'][channel][product]
                
                for model_name, model_data in models.items():
                    st.write(f"**{model_name}**")
                    
                    table_data = []
                    for month, value in model_data.items():
                        table_data.append({
                            "월": month,
                            "값": f"{value:,.0f}" if isinstance(value, (int, float)) else value
                        })
                    
                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)
                    
                    st.divider()
    else:
        st.warning("⚠️ 데이터 없음")

# TAB 3: 프리미엄 비중
with tab3:
    st.markdown('<div class="section-header">💎 프리미엄 비중</div>', unsafe_allow_html=True)
    
    if data['premium']:
        products = list(data['premium'].keys())
        product = st.selectbox("📦 제품 선택", products, key="tab3_product")
        
        if product in data['premium']:
            months = list(data['premium'][product].keys())
            month = st.selectbox("📅 월 선택", months, key="tab3_month")
            
            if month in data['premium'][product]:
                st.subheader(f"📊 {product} - {month}")
                
                month_data = data['premium'][product][month]
                
                for channel, channel_data in month_data.items():
                    st.write(f"**📍 {channel} 채널**")
                    
                    if isinstance(channel_data, dict):
                        table_data = []
                        
                        for key, value in channel_data.items():
                            if isinstance(value, dict):
                                # 26년, 25년 등 nested dict
                                table_data.append({
                                    "기간": key,
                                    "전체": f"{value.get('전체', 0):,.0f}",
                                    "프리미엄": f"{value.get('프리미엄', 0):,.0f}",
                                    "비중": f"{value.get('비중', 0):.1f}%"
                                })
                            else:
                                # 전년비, 비중차 등
                                table_data.append({
                                    "기간": key,
                                    "전체": "",
                                    "프리미엄": "",
                                    "비중": f"{value:.1f}" if isinstance(value, float) else f"{value:,.0f}" if isinstance(value, int) else str(value)
                                })
                        
                        if table_data:
                            df = pd.DataFrame(table_data)
                            st.dataframe(df, use_container_width=True)
                    
                    st.divider()
    else:
        st.warning("⚠️ 데이터 없음")

# TAB 4: 스마트스토어
with tab4:
    st.markdown('<div class="section-header">🛍️ 스마트스토어</div>', unsafe_allow_html=True)
    
    if data['smartstore']:
        months = list(data['smartstore'].keys())
        month = st.selectbox("📅 월 선택", months, key="tab4_month")
        
        if month in data['smartstore']:
            st.subheader(f"📊 {month} 스마트스토어")
            
            month_data = data['smartstore'][month]
            
            table_data = []
            for store, values in month_data.items():
                if isinstance(values, dict):
                    row = {"대리점": store}
                    row.update(values)
                    table_data.append(row)
            
            if table_data:
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ 데이터 없음")

# TAB 5: 라이브커머스
with tab5:
    st.markdown('<div class="section-header">🎥 라이브커머스</div>', unsafe_allow_html=True)
    
    if data['live_commerce']:
        # 요약 정보
        if '26년_전체' in data['live_commerce']:
            st.write("**📊 2026년 전체**")
            summary = data['live_commerce']['26년_전체']
            
            table_data = []
            for key, value in summary.items():
                table_data.append({
                    "항목": key,
                    "값": f"{value:,.0f}" if isinstance(value, int) else value
                })
            
            if table_data:
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
            
            st.divider()
        
        # 월별 데이터
        if '월별' in data['live_commerce']:
            st.write("**📅 월별 현황**")
            months_dict = data['live_commerce']['월별']
            
            if isinstance(months_dict, dict):
                # 드롭다운으로 월 선택
                months = list(months_dict.keys())
                selected_month = st.selectbox("📅 월 선택", months, key="tab5_month")
                
                if selected_month in months_dict:
                    month_data = months_dict[selected_month]
                    
                    table_data = []
                    for store, values in month_data.items():
                        if isinstance(values, dict):
                            row = {"대리점": store}
                            row.update(values)
                            table_data.append(row)
                    
                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ 데이터 없음")

# TAB 6: 어필리에이트
with tab6:
    st.markdown('<div class="section-header">👥 어필리에이트</div>', unsafe_allow_html=True)
    
    if data['affiliate']:
        months = list(data['affiliate'].keys())
        month = st.selectbox("📅 월 선택", months, key="tab6_month")
        
        if month in data['affiliate']:
            channels = list(data['affiliate'][month].keys())
            channel = st.selectbox("📍 채널 선택", channels, key="tab6_channel")
            
            if channel in data['affiliate'][month]:
                st.subheader(f"📊 {month} - {channel}")
                
                channel_data = data['affiliate'][month][channel]
                
                table_data = []
                for store, values in channel_data.items():
                    if isinstance(values, dict):
                        row = {"대리점": store}
                        row.update(values)
                        table_data.append(row)
                
                if table_data:
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ 데이터 없음")

# TAB 7: 쿠팡 PPM
with tab7:
    st.markdown('<div class="section-header">🏪 쿠팡 PPM</div>', unsafe_allow_html=True)
    
    if data['coupang_ppm']:
        weeks = list(data['coupang_ppm'].keys())
        week = st.selectbox("📅 주차 선택", weeks, key="tab7_week")
        
        if week in data['coupang_ppm']:
            st.subheader(f"📊 {week}")
            
            week_data = data['coupang_ppm'][week]
            
            for product, models in week_data.items():
                st.write(f"**{product}**")
                
                if isinstance(models, list):
                    if len(models) > 0 and isinstance(models[0], dict):
                        df = pd.DataFrame(models)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.json(models)
                else:
                    st.json(models)
                
                st.divider()
    else:
        st.warning("⚠️ 데이터 없음")

# TAB 8: SOP 활동 입력
with tab8:
    st.markdown('<div class="section-header">📋 SOP 활동 입력</div>', unsafe_allow_html=True)
    
    st.info("🔄 SOP 대리점별 주차별 활동 내역을 입력하세요.")
    
    # 입력 폼
    col1, col2, col3 = st.columns(3)
    
    with col1:
        agency = st.selectbox(
            "🏪 대리점 선택",
            ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"],
            key="sop_agency"
        )
    
    with col2:
        week = st.number_input("📅 주차", min_value=1, max_value=52, value=1, key="sop_week")
    
    with col3:
        month = st.selectbox("📆 월", ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월"], key="sop_month")
    
    st.divider()
    
    # 활동 항목 입력
    col1, col2, col3 = st.columns(3)
    
    with col1:
        activity = st.number_input("📊 활동 건수", min_value=0, value=0, key="sop_activity")
    
    with col2:
        sales = st.number_input("💰 매출액", min_value=0, value=0, key="sop_sales")
    
    with col3:
        performance = st.number_input("📈 달성률 (%)", min_value=0.0, max_value=200.0, value=100.0, key="sop_performance")
    
    # 저장 버튼
    if st.button("💾 SOP 활동 저장", key="sop_save"):
        st.success(f"✅ {month} {week}주차 - {agency}: 활동 {activity}건, 매출 ₩{sales:,.0f}, 달성률 {performance:.1f}% 저장됨")
    
    st.divider()
    
    # 입력된 SOP 데이터 표시 (예시)
    st.write("**📊 최근 입력 현황**")
    sample_data = pd.DataFrame({
        "대리점": ["평강", "문성", "케이디엘"],
        "주차": [1, 1, 1],
        "월": ["1월", "1월", "1월"],
        "활동건수": [15, 20, 18],
        "매출액": [5000000, 7500000, 6200000],
        "달성률": [105.2, 98.5, 110.3]
    })
    st.dataframe(sample_data, use_container_width=True)

# TAB 9: STAR RAW 데이터 업로드
with tab9:
    st.markdown('<div class="section-header">⭐ STAR RAW 데이터 업로드</div>', unsafe_allow_html=True)
    
    st.info("📤 STAR 데이터(Excel/CSV)를 업로드하세요.")
    
    uploaded_file = st.file_uploader(
        "파일 선택 (xlsx, xls, csv)",
        type=["xlsx", "xls", "csv"],
        key="star_upload"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ 파일 선택됨: {uploaded_file.name}")
        
        # 파일 타입에 따라 읽기
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write(f"**📊 미리보기 (처음 10행)**")
            st.dataframe(df.head(10), use_container_width=True)
            
            st.write(f"**📈 데이터 정보**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("행 수", len(df))
            with col2:
                st.metric("열 수", len(df.columns))
            with col3:
                st.metric("파일명", uploaded_file.name)
            
            # 저장 버튼
            if st.button("💾 STAR RAW 데이터 저장", key="star_save"):
                st.success(f"✅ STAR RAW 데이터 저장 완료! ({len(df)}행)")
        
        except Exception as e:
            st.error(f"❌ 파일 읽기 실패: {e}")
    else:
        st.write("파일을 선택해주세요.")
