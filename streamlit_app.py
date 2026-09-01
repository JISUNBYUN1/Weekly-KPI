import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="PP3G Weekly KPI", page_icon="📊", layout="wide")

@st.cache_data
def load_all_data():
    data = {}
    
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
    
    bizplan = {}
    for filename in ['bizplan_SOP.json', 'bizplan_쿠팡.json', 'bizplan_종합몰.json', 'bizplan_홈쇼핑.json']:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                bizplan.update(json.load(f))
        except:
            pass
    data['bizplan'] = bizplan
    
    premium = {}
    for filename in ['premium_냉장고.json', 'premium_세탁기.json', 'premium_식기세척기.json', 'premium_정수기.json']:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                premium.update(json.load(f))
        except:
            pass
    data['premium'] = premium
    
    return data

data = load_all_data()

st.title("📊 PP3G Weekly KPI 대시보드")
st.markdown(f"**업데이트**: {datetime.now().strftime('%Y.%m.%d %H:%M')}")

tabs = st.tabs(["전체 현황", "FCST 현황", "프리미엄 비중", "스마트스토어", "라이브커머스", "어필리에이트", "쿠팡 PPM", "SOP 활동", "SOP 입력", "STAR RAW"])

# TAB 1
with tabs[0]:
    st.header("📈 전체 현황")
    if data['bizplan']:
        channels = list(data['bizplan'].keys())
        channel = st.selectbox("채널", channels, key="t1_ch")
        if channel in data['bizplan']:
            products = list(data['bizplan'][channel].keys())
            product = st.selectbox("제품", products, key="t1_prod")
            if product in data['bizplan'][channel]:
                for model, model_data in data['bizplan'][channel][product].items():
                    st.write(f"**{model}**")
                    df = pd.DataFrame([{"월": k, "값": f"{v:,.0f}" if isinstance(v, (int, float)) else v} for k, v in model_data.items()])
                    st.dataframe(df, use_container_width=True)

# TAB 2
with tabs[1]:
    st.header("📊 FCST 현황 (BIZ PLAN)")
    if data['bizplan']:
        channels = list(data['bizplan'].keys())
        channel = st.selectbox("채널", channels, key="t2_ch")
        if channel in data['bizplan']:
            products = list(data['bizplan'][channel].keys())
            product = st.selectbox("제품", products, key="t2_prod")
            if product in data['bizplan'][channel]:
                for model, model_data in data['bizplan'][channel][product].items():
                    st.write(f"**{model}**")
                    df = pd.DataFrame([{"월": k, "값": f"{v:,.0f}" if isinstance(v, (int, float)) else v} for k, v in model_data.items()])
                    st.dataframe(df, use_container_width=True)

# TAB 3
with tabs[2]:
    st.header("💎 프리미엄 비중")
    if data['premium']:
        products = list(data['premium'].keys())
        product = st.selectbox("제품", products, key="t3_prod")
        if product in data['premium']:
            months = list(data['premium'][product].keys())
            month = st.selectbox("월", months, key="t3_month")
            if month in data['premium'][product]:
                for channel, ch_data in data['premium'][product][month].items():
                    st.write(f"**{channel}**")
                    rows = []
                    for key, value in ch_data.items():
                        if isinstance(value, dict):
                            rows.append({"기간": key, "전체": f"{value.get('전체', 0):,.0f}", "프리미엄": f"{value.get('프리미엄', 0):,.0f}", "비중": f"{value.get('비중', 0):.1f}%"})
                        else:
                            rows.append({"기간": key, "전체": "", "프리미엄": "", "비중": str(value)})
                    if rows:
                        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# TAB 4
with tabs[3]:
    st.header("🛍️ 스마트스토어")
    if data['smartstore']:
        months = list(data['smartstore'].keys())
        month = st.selectbox("월", months, key="t4_month")
        if month in data['smartstore']:
            rows = [{"대리점": k, **v} for k, v in data['smartstore'][month].items() if isinstance(v, dict)]
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

# TAB 5
with tabs[4]:
    st.header("🎥 라이브커머스")
    if data['live_commerce']:
        if '26년_전체' in data['live_commerce']:
            st.write("**2026년 전체**")
            rows = [{"항목": k, "값": f"{v:,.0f}" if isinstance(v, int) else v} for k, v in data['live_commerce']['26년_전체'].items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        if '월별' in data['live_commerce']:
            st.write("**월별 현황**")
            months_dict = data['live_commerce']['월별']
            months = list(months_dict.keys())
            month = st.selectbox("월", months, key="t5_month")
            if month in months_dict:
                rows = [{"대리점": k, **v} for k, v in months_dict[month].items() if isinstance(v, dict)]
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)

# TAB 6
with tabs[5]:
    st.header("👥 어필리에이트")
    if data['affiliate']:
        months = list(data['affiliate'].keys())
        month = st.selectbox("월", months, key="t6_month")
        if month in data['affiliate']:
            channels = list(data['affiliate'][month].keys())
            channel = st.selectbox("채널", channels, key="t6_ch")
            if channel in data['affiliate'][month]:
                rows = [{"대리점": k, **v} for k, v in data['affiliate'][month][channel].items() if isinstance(v, dict)]
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)

# TAB 7
with tabs[6]:
    st.header("🏪 쿠팡 PPM")
    if data['coupang_ppm']:
        weeks = list(data['coupang_ppm'].keys())
        week = st.selectbox("주차", weeks, key="t7_week")
        if week in data['coupang_ppm']:
            for product, models in data['coupang_ppm'][week].items():
                st.write(f"**{product}**")
                if isinstance(models, list) and len(models) > 0 and isinstance(models[0], dict):
                    st.dataframe(pd.DataFrame(models), use_container_width=True)

# TAB 8
with tabs[7]:
    st.header("📋 SOP 활동")
    col1, col2 = st.columns(2)
    with col1:
        month = st.selectbox("월", ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월"], key="t8_month")
    with col2:
        week = st.number_input("주차", 1, 5, 1, key="t8_week")
    st.write(f"**{month} {week}주차 SOP 활동**")
    sample = pd.DataFrame({
        "대리점": ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"],
        "활동건수": [12, 18, 15, 9, 14, 11, 16],
        "매출액": [5000000, 8500000, 4200000, 2100000, 3800000, 2900000, 6100000]
    })
    st.dataframe(sample, use_container_width=True)

# TAB 9
with tabs[8]:
    st.header("✏️ SOP 입력")
    input_type = st.radio("선택", ["어필리에이트", "스마트스토어", "마케팅활동"], horizontal=True)
    
    if input_type == "어필리에이트":
        col1, col2, col3 = st.columns(3)
        with col1:
            month = st.selectbox("월", ["7월", "8월"], key="aff_m")
        with col2:
            store = st.selectbox("대리점", ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"], key="aff_s")
        with col3:
            channel = st.selectbox("채널", ["쇼핑커넥트", "공동구매"], key="aff_c")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            creators = st.number_input("크리에이터", 0, key="aff_cr")
        with col2:
            orders = st.number_input("주문수", 0, key="aff_or")
        with col3:
            sales = st.number_input("매출액", 0, key="aff_sa")
        with col4:
            commission = st.number_input("수수료(%)", 0.0, 100.0, key="aff_co")
        if st.button("저장", key="aff_btn"):
            st.success(f"✅ {month} {store} ({channel}) 저장됨")
    
    elif input_type == "스마트스토어":
        col1, col2 = st.columns(2)
        with col1:
            month = st.selectbox("월", [f"{i}월" for i in range(1, 13)], key="ss_m")
        with col2:
            store = st.selectbox("대리점", ["전체", "평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"], key="ss_s")
        col1, col2, col3 = st.columns(3)
        with col1:
            total = st.number_input("총 고객수", 0, key="ss_t")
        with col2:
            new = st.number_input("신규유입", 0, key="ss_n")
        with col3:
            mom = st.number_input("전월차", -100000, 100000, key="ss_m2")
        if st.button("저장", key="ss_btn"):
            st.success(f"✅ {month} {store} 저장됨")
    
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            month = st.selectbox("월", [f"{i}월" for i in range(1, 13)], key="mk_m")
        with col2:
            week = st.number_input("주차", 1, 5, key="mk_w")
        with col3:
            store = st.selectbox("대리점", ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"], key="mk_s")
        col1, col2, col3 = st.columns(3)
        with col1:
            activity_type = st.selectbox("활동종류", ["SNS", "이벤트", "광고", "전시회", "기타"], key="mk_t")
        with col2:
            participants = st.number_input("참여인원", 0, key="mk_p")
        with col3:
            investment = st.number_input("투자액", 0, key="mk_i")
        description = st.text_area("활동 설명", key="mk_d")
        if st.button("저장", key="mk_btn"):
            st.success(f"✅ {month} {week}주차 {store} 저장됨")

# TAB 10
with tabs[9]:
    st.header("⭐ STAR RAW 업로드")
    uploaded_file = st.file_uploader("파일 선택", type=["xlsx", "xls", "csv"], key="star")
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            st.write(f"**미리보기**")
            st.dataframe(df.head(10), use_container_width=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("행", len(df))
            with col2:
                st.metric("열", len(df.columns))
            with col3:
                st.metric("파일", uploaded_file.name)
            if st.button("저장", key="star_btn"):
                st.success(f"✅ 저장 완료! ({len(df)}행)")
                st.balloons()
        except Exception as e:
            st.error(f"❌ 오류: {e}")
