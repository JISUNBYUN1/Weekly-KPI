import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="PP3G Weekly KPI Dashboard", page_icon="📊", layout="wide")

st.markdown('<div style="font-size: 36px; font-weight: bold; color: #1f77b4; margin-bottom: 30px;">📊 PP3G Weekly KPI 종합 대시보드</div>', unsafe_allow_html=True)
st.markdown(f"**업데이트**: {datetime.now().strftime('%Y.%m.%d %H:%M')}")

@st.cache_data
def load_all_data():
    data = {}
    json_files = {'chpsi': 'chpsi_reorganized.json', 'bizplan': 'bizplan_final.json', 'live_commerce': 'live_commerce_complete.json', 'affiliate': 'affiliate_final_data.json', 'smartstore': 'smartstore_customers.json', 'premium': 'premium_data.json', 'coupang_ppm': 'coupang_ppm_data.json'}
    for key, filename in json_files.items():
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data[key] = json.load(f)
        except:
            data[key] = {}
    return data

data = load_all_data()

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["전체 현황", "FCST 현황", "프리미엄 비중", "스마트스토어", "라이브커머스", "어필리에이트", "쿠팡 PPM", "활동 내역"])

with tab1:
    st.markdown('**전체 현황**')
    if data['chpsi']:
        for channel in ['SOP', '쿠팡', '종합몰', '홈쇼핑']:
            if channel in data['chpsi']:
                st.markdown(f'**{channel} 채널**')
                col1, col2, col3, col4 = st.columns(4)
                total_fcst = sum(sum(p.get('Sell-out_FCST', {}).values() for p in pg.values() if isinstance(p, dict)) for pg in data['chpsi'][channel].values())
                total_sellin = sum(sum(p.get('Sell-in', {}).values() for p in pg.values() if isinstance(p, dict)) for pg in data['chpsi'][channel].values())
                with col1:
                    st.metric("🎯 FCST", f"{total_fcst:,}대")
                with col2:
                    st.metric("✅ 실적", f"{total_sellin:,}대")
                with col3:
                    if total_fcst > 0:
                        st.metric("📈 달성률", f"{(total_sellin / total_fcst * 100):.1f}%")
                with col4:
                    st.metric("차이", f"{total_sellin - total_fcst:+,}대")
                st.divider()

with tab2:
    st.markdown('**FCST 현황**')
    st.info("📊 월별/주차별 FCST 데이터")

with tab3:
    st.markdown('**프리미엄 비중**')
    st.info("📈 프리미엄 비중 분석")

with tab4:
    st.markdown('**스마트스토어**')
    st.info("👥 고객수 분석")

with tab5:
    st.markdown('**라이브커머스**')
    st.info("🎬 라이브커머스 효율")

with tab6:
    st.markdown('**어필리에이트**')
    st.info("🌟 어필리에이트 현황")

with tab7:
    st.markdown('**쿠팡 PPM**')
    st.info("🔖 쿠팡 PPM")

with tab8:
    st.markdown('**활동 내역**')
    st.info("📝 SOP 활동 내역")

st.markdown("---")
st.markdown("*Data Source: Samsung Electronics PP3G*")
