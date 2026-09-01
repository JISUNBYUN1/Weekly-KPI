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

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "전체 현황", "FCST 현황", "프리미엄 비중", "스마트스토어",
    "라이브커머스", "어필리에이트", "쿠팡 PPM", "SOP 활동"
])

# TAB 1
with tab1:
    st.markdown('<div class="section-header">📈 전체 현황</div>', unsafe_allow_html=True)
    if data['bizplan']:
        st.success("✅ BIZ Plan 데이터 로드됨")
        st.json(list(data['bizplan'].keys())[:3])
    else:
        st.warning("⚠️ 데이터 로드 실패")

# TAB 2
with tab2:
    st.markdown('<div class="section-header">📊 FCST 현황</div>', unsafe_allow_html=True)
    if data['chpsi']:
        st.success("✅ CH_PSI 데이터 로드됨")
        st.json(list(data['chpsi'].keys())[:3])

# TAB 3
with tab3:
    st.markdown('<div class="section-header">💎 프리미엄 비중</div>', unsafe_allow_html=True)
    
    if data['premium']:
        st.success("✅ Premium 데이터 로드됨")
        
        # 제품별 선택
        products = list(data['premium'].keys())
        if products:
            product = st.selectbox("📦 제품 선택", products)
            
            if product in data['premium']:
                st.subheader(f"📊 {product}")
                
                product_data = data['premium'][product]
                
                # 채널별 테이블 생성
                channels = list(product_data.keys())
                
                for channel in channels:
                    st.write(f"**📍 {channel} 채널**")
                    
                    channel_data = product_data[channel]
                    
                    # 데이터 정리
                    table_data = []
                    for period, values in channel_data.items():
                        if isinstance(values, dict):
                            table_data.append({
                                "기간": period,
                                "전체": f"{values.get('전체', 0):,.0f}",
                                "프리미엄": f"{values.get('프리미엄', 0):,.0f}",
                                "비중": f"{values.get('비중', 0):.1f}%"
                            })
                    
                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)
                    
                    st.divider()
    else:
        st.warning("⚠️ Premium 데이터를 로드할 수 없습니다.")

# TAB 4
with tab4:
    st.markdown('<div class="section-header">🛍️ 스마트스토어</div>', unsafe_allow_html=True)
    if data['smartstore']:
        st.success("✅ Smartstore 데이터 로드됨")
        st.json(data['smartstore'])

# TAB 5
with tab5:
    st.markdown('<div class="section-header">🎥 라이브커머스</div>', unsafe_allow_html=True)
    if data['live_commerce']:
        st.success("✅ Live Commerce 데이터 로드됨")
        st.json(list(data['live_commerce'].keys())[:3])

# TAB 6
with tab6:
    st.markdown('<div class="section-header">👥 어필리에이트</div>', unsafe_allow_html=True)
    if data['affiliate']:
        st.success("✅ Affiliate 데이터 로드됨")
        st.json(list(data['affiliate'].keys())[:3])

# TAB 7
with tab7:
    st.markdown('<div class="section-header">🏪 쿠팡 PPM</div>', unsafe_allow_html=True)
    if data['coupang_ppm']:
        st.success("✅ Coupang PPM 데이터 로드됨")
        st.json(list(data['coupang_ppm'].keys())[:3])

# TAB 8
with tab8:
    st.markdown('<div class="section-header">📋 SOP 활동</div>', unsafe_allow_html=True)
    st.info("🔄 SOP 활동 데이터 구성 중...")
