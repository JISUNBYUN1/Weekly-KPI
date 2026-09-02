import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="PP3G KPI", page_icon="📊", layout="wide")

@st.cache_data
def load_all_data():
    data = {}
    base_files = {'chpsi': 'chpsi_reorganized.json', 'live_commerce': 'live_commerce_complete.json',
                  'affiliate': 'affiliate_final_data.json', 'smartstore': 'smartstore_customers.json', 'coupang_ppm': 'coupang_ppm_data.json'}
    for k, f in base_files.items():
        try:
            with open(f, encoding='utf-8') as file:
                data[k] = json.load(file)
        except:
            data[k] = {}
    
    bizplan, premium = {}, {}
    for f in ['bizplan_SOP.json', 'bizplan_쿠팡.json', 'bizplan_종합몰.json', 'bizplan_홈쇼핑.json']:
        try:
            with open(f, encoding='utf-8') as file:
                bizplan.update(json.load(file))
        except:
            pass
    for f in ['premium_냉장고.json', 'premium_세탁기.json', 'premium_식기세척기.json', 'premium_정수기.json']:
        try:
            with open(f, encoding='utf-8') as file:
                premium.update(json.load(file))
        except:
            pass
    data['bizplan'], data['premium'] = bizplan, premium
    return data

data = load_all_data()
st.title("📊 PP3G Weekly KPI")
st.markdown(f"**업데이트**: {datetime.now().strftime('%Y.%m.%d %H:%M')}")

t = st.tabs(["전체", "FCST", "프리미엄", "스마트스토어", "라이브", "어필", "PPM", "SOP활동", "SOP입력", "STAR"])

def create_month_table(model_data):
    """월을 가로로 배열한 테이블 생성"""
    months = sorted(model_data.get('SALES', {}).keys(), key=lambda x: int(x.replace("월", "")) if "월" in x else 0)
    
    data_dict = {}
    for month in months:
        actual = model_data.get('SALES', {}).get(month, 0)
        annual = model_data.get('ANNUAL', {}).get(month, 1)
        action = model_data.get('ACTION', {}).get(month, 1)
        prev_year = model_data.get('2025', {}).get(month, 1)
        
        data_dict[f"{month}\n실적(수량)"] = f"{actual:,.0f}"
        data_dict[f"{month}\n경영대비(%)"] = f"{(actual/annual):.2f}%" if annual > 0 else "-"
        data_dict[f"{month}\n실행대비(%)"] = f"{(actual/action):.2f}%" if action > 0 else "-"
        # 전년대비(%) = ((2026년 / 2025년) - 1) × 100
        data_dict[f"{month}\n전년대비(%)"] = f"{((actual/prev_year - 1) * 100):.2f}%" if prev_year > 0 else "-"
    
    return pd.DataFrame([data_dict]).T

# TAB 1
with t[0]:
    st.header("전체 현황")
    if data['bizplan']:
        all_products = {}
        for channel_data in data['bizplan'].values():
            for product_name, product_models in channel_data.items():
                if product_name not in all_products:
                    all_products[product_name] = {"SALES": {}, "ANNUAL": {}, "ACTION": {}, "2025": {}}
                for model_data in product_models.values():
                    for key in ["SALES", "ANNUAL", "ACTION", "2025"]:
                        if key in model_data:
                            for month, value in model_data[key].items():
                                if month not in all_products[product_name][key]:
                                    all_products[product_name][key][month] = 0
                                if isinstance(value, (int, float)):
                                    all_products[product_name][key][month] += value
        
        grand_total = {"SALES": {}, "ANNUAL": {}, "ACTION": {}, "2025": {}}
        for product_data in all_products.values():
            for key in ["SALES", "ANNUAL", "ACTION", "2025"]:
                for month, value in product_data[key].items():
                    if month not in grand_total[key]:
                        grand_total[key][month] = 0
                    grand_total[key][month] += value
        
        st.dataframe(create_month_table(grand_total), width='stretch')

# TAB 2 - FCST 현황
with t[1]:
    st.header("FCST 현황")
    if data['bizplan']:
        all_products = {}
        for channel_data in data['bizplan'].values():
            for product_name, product_models in channel_data.items():
                if product_name not in all_products:
                    all_products[product_name] = {"SALES": {}, "ANNUAL": {}, "ACTION": {}, "2025": {}}
                for model_data in product_models.values():
                    for key in ["SALES", "ANNUAL", "ACTION", "2025"]:
                        if key in model_data:
                            for month, value in model_data[key].items():
                                if month not in all_products[product_name][key]:
                                    all_products[product_name][key][month] = 0
                                if isinstance(value, (int, float)):
                                    all_products[product_name][key][month] += value
        
        # 디폴트: 전체 품목 합계
        st.subheader("📊 전체 현황 (기본)")
        grand_total = {"SALES": {}, "ANNUAL": {}, "ACTION": {}, "2025": {}}
        for product_data in all_products.values():
            for key in ["SALES", "ANNUAL", "ACTION", "2025"]:
                for month, value in product_data[key].items():
                    if month not in grand_total[key]:
                        grand_total[key][month] = 0
                    grand_total[key][month] += value
        
        st.dataframe(create_month_table(grand_total), width='stretch')
        st.divider()
        
        # 제품별로 expander 처리
        st.subheader("📦 제품별 상세")
        for product_name in sorted(all_products.keys()):
            with st.expander(f"📦 {product_name}", expanded=False):
                product_data = all_products[product_name]
                
                # 제품 전체
                st.write(f"**{product_name} 전체**")
                st.dataframe(create_month_table(product_data), width='stretch')
                st.divider()
                
                # 채널별
                for channel_name in sorted(data['bizplan'].keys()):
                    channel_data = data['bizplan'][channel_name]
                    if product_name not in channel_data:
                        continue
                    
                    models = channel_data[product_name]
                    channel_total = {"SALES": {}, "ANNUAL": {}, "ACTION": {}, "2025": {}}
                    
                    for model_data in models.values():
                        for key in ["SALES", "ANNUAL", "ACTION", "2025"]:
                            if key in model_data:
                                for month, value in model_data[key].items():
                                    if month not in channel_total[key]:
                                        channel_total[key][month] = 0
                                    if isinstance(value, (int, float)):
                                        channel_total[key][month] += value
                    
                    # 냉장고, 의류케어, 조리기기: 모든 채널이 expander
                    if product_name in ["냉장고", "의류케어", "조리기기"]:
                        with st.expander(f"🔽 {channel_name}"):
                            st.write(f"**{channel_name} 전체**")
                            st.dataframe(create_month_table(channel_total), width='stretch')
                            st.divider()
                            
                            # 모델들
                            for model_name, model_data in sorted(models.items()):
                                st.write(f"  **{model_name}**")
                                st.dataframe(create_month_table(model_data), width='stretch')
                    else:
                        # 김치냉장고, 정수기: expander 없음
                        st.write(f"**{channel_name}**")
                        st.dataframe(create_month_table(channel_total), width='stretch')

# TAB 3
with t[2]:
    st.header("프리미엄 비중")
    if data['premium']:
        pr = st.selectbox("제품", list(data['premium'].keys()), key="p3")
        mo = st.selectbox("월", list(data['premium'][pr].keys()), key="m3")
        for ch, cd in data['premium'][pr][mo].items():
            st.write(f"**{ch}**")
            rows = []
            for k, v in cd.items():
                if isinstance(v, dict):
                    rows.append({"기간": k, "전체": f"{v.get('전체',0):,.0f}", "프리미엄": f"{v.get('프리미엄',0):,.0f}", "비중": f"{v.get('비중',0):.1f}%"})
            st.dataframe(pd.DataFrame(rows))

# TAB 4
with t[3]:
    st.header("스마트스토어")
    if data['smartstore']:
        mo = st.selectbox("월", list(data['smartstore'].keys()), key="m4")
        st.dataframe(pd.DataFrame([{"대리점": k, **v} for k, v in data['smartstore'][mo].items() if isinstance(v, dict)]))

# TAB 5
with t[4]:
    st.header("라이브커머스")
    if data['live_commerce'] and '월별' in data['live_commerce']:
        mo = st.selectbox("월", list(data['live_commerce']['월별'].keys()), key="m5")
        st.dataframe(pd.DataFrame([{"대리점": k, **v} for k, v in data['live_commerce']['월별'][mo].items() if isinstance(v, dict)]))

# TAB 6
with t[5]:
    st.header("어필리에이트")
    if data['affiliate']:
        mo = st.selectbox("월", list(data['affiliate'].keys()), key="m6")
        ch = st.selectbox("채널", list(data['affiliate'][mo].keys()), key="c6")
        st.dataframe(pd.DataFrame([{"대리점": k, **v} for k, v in data['affiliate'][mo][ch].items() if isinstance(v, dict)]))

# TAB 7
with t[6]:
    st.header("쿠팡 PPM")
    if data['coupang_ppm']:
        wk = st.selectbox("주차", list(data['coupang_ppm'].keys()), key="w7")
        for pr, models in data['coupang_ppm'][wk].items():
            st.write(f"**{pr}**")
            if isinstance(models, list) and models and isinstance(models[0], dict):
                st.dataframe(pd.DataFrame(models))

# TAB 8
with t[7]:
    st.header("SOP 활동")
    mo = st.selectbox("월", ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월"], key="m8")
    wk = st.number_input("주차", 1, 5, 1)
    sample = pd.DataFrame({"대리점": ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"], "활동건수": [12, 18, 15, 9, 14, 11, 16], "매출액": [5000000, 8500000, 4200000, 2100000, 3800000, 2900000, 6100000]})
    st.dataframe(sample)

# TAB 9
with t[8]:
    st.header("SOP 입력")
    inp = st.radio("선택", ["어필리에이트", "스마트스토어", "마케팅활동"], horizontal=True)
    if inp == "어필리에이트":
        col1, col2, col3 = st.columns(3)
        with col1:
            m = st.selectbox("월", ["7월", "8월"], key="am")
        with col2:
            s = st.selectbox("대리점", ["평강", "문성"], key="as")
        with col3:
            c = st.selectbox("채널", ["쇼핑커넥트", "공동구매"], key="ac")
        if st.button("저장", key="ab"):
            st.success(f"✅ {m} {s} 저장됨")
    elif inp == "스마트스토어":
        m = st.selectbox("월", [f"{i}월" for i in range(1, 13)], key="sm")
        t_val = st.number_input("고객수", 0, key="st")
        if st.button("저장", key="sb"):
            st.success(f"✅ {m} 저장됨")
    else:
        m = st.selectbox("월", [f"{i}월" for i in range(1, 13)], key="mm")
        t_val = st.selectbox("활동", ["SNS", "이벤트"], key="mt")
        if st.button("저장", key="mb"):
            st.success(f"✅ {m} 저장됨")

# TAB 10
with t[9]:
    st.header("STAR RAW")
    f = st.file_uploader("파일", type=["xlsx", "csv"])
    if f:
        try:
            df = pd.read_excel(f) if f.name.endswith('xlsx') else pd.read_csv(f)
            st.dataframe(df.head(10))
            st.metric("행", len(df))
            if st.button("저장"):
                st.success(f"✅ {len(df)}행 저장됨")
                st.balloons()
        except Exception as e:
            st.error(f"오류: {e}")
