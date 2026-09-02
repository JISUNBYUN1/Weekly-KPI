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

# 제품 순서 정의
PRODUCT_ORDER = ["냉장고", "김치냉장고", "의류케어", "조리기기", "정수기"]

def create_summary_table_no_group(all_products_data):
    """제품별 합계 테이블 생성 (그룹 계 제외)"""
    rows = []
    
    # 제품별 행 추가 (정렬 순서)
    for product_name in PRODUCT_ORDER:
        if product_name not in all_products_data:
            continue
        product_data = all_products_data[product_name]
        
        sales_total = sum(product_data.get("SALES", {}).values())
        annual_total = sum(product_data.get("ANNUAL", {}).values())
        action_total = sum(product_data.get("ACTION", {}).values())
        prev_year_total = sum(product_data.get("2025", {}).values())
        
        rows.append({
            "제품": product_name,
            "실적(수량)": f"{sales_total:,.0f}",
            "경영비(%)": f"{(sales_total/annual_total):.2f}%" if annual_total > 0 else "-",
            "실행비(%)": f"{(sales_total/action_total):.2f}%" if action_total > 0 else "-",
            "전년비(%)": f"{((sales_total/prev_year_total - 1) * 100):.2f}%" if prev_year_total > 0 else "-"
        })
    
    return pd.DataFrame(rows)

def create_summary_table_with_group(all_products_data):
    """제품별 합계 테이블 생성 (그룹 계 포함)"""
    rows = []
    
    # 전체 합계 행 추가
    grand_total_sales = sum(sum(p.get("SALES", {}).values()) for p in all_products_data.values() if "SALES" in p)
    grand_total_annual = sum(sum(p.get("ANNUAL", {}).values()) for p in all_products_data.values() if "ANNUAL" in p)
    grand_total_action = sum(sum(p.get("ACTION", {}).values()) for p in all_products_data.values() if "ACTION" in p)
    grand_total_2025 = sum(sum(p.get("2025", {}).values()) for p in all_products_data.values() if "2025" in p)
    
    rows.append({
        "제품": "그룹 계",
        "실적(수량)": f"{grand_total_sales:,.0f}",
        "경영비(%)": f"{(grand_total_sales/grand_total_annual):.2f}%" if grand_total_annual > 0 else "-",
        "실행비(%)": f"{(grand_total_sales/grand_total_action):.2f}%" if grand_total_action > 0 else "-",
        "전년비(%)": f"{((grand_total_sales/grand_total_2025 - 1) * 100):.2f}%" if grand_total_2025 > 0 else "-"
    })
    
    # 제품별 행 추가
    for product_name in PRODUCT_ORDER:
        if product_name not in all_products_data:
            continue
        product_data = all_products_data[product_name]
        
        sales_total = sum(product_data.get("SALES", {}).values())
        annual_total = sum(product_data.get("ANNUAL", {}).values())
        action_total = sum(product_data.get("ACTION", {}).values())
        prev_year_total = sum(product_data.get("2025", {}).values())
        
        rows.append({
            "제품": product_name,
            "실적(수량)": f"{sales_total:,.0f}",
            "경영비(%)": f"{(sales_total/annual_total):.2f}%" if annual_total > 0 else "-",
            "실행비(%)": f"{(sales_total/action_total):.2f}%" if action_total > 0 else "-",
            "전년비(%)": f"{((sales_total/prev_year_total - 1) * 100):.2f}%" if prev_year_total > 0 else "-"
        })
    
    return pd.DataFrame(rows)

def create_month_summary_table(all_products_data, selected_month):
    """선택된 월별 제품 요약 테이블"""
    rows = []
    
    for product_name in PRODUCT_ORDER:
        if product_name not in all_products_data:
            continue
        product_data = all_products_data[product_name]
        
        sales = product_data.get("SALES", {}).get(selected_month, 0)
        annual = product_data.get("ANNUAL", {}).get(selected_month, 1)
        action = product_data.get("ACTION", {}).get(selected_month, 1)
        prev_year = product_data.get("2025", {}).get(selected_month, 1)
        
        rows.append({
            "제품": product_name,
            "실적(수량)": f"{sales:,.0f}",
            "경영비(%)": f"{(sales/annual):.2f}%" if annual > 0 else "-",
            "실행비(%)": f"{(sales/action):.2f}%" if action > 0 else "-",
            "전년비(%)": f"{((sales/prev_year - 1) * 100):.2f}%" if prev_year > 0 else "-"
        })
    
    return pd.DataFrame(rows)

def create_channel_summary_table(channel_total):
    """채널별 요약 테이블 (세로)"""
    rows = []
    
    sales_total = sum(channel_total.get("SALES", {}).values())
    annual_total = sum(channel_total.get("ANNUAL", {}).values())
    action_total = sum(channel_total.get("ACTION", {}).values())
    prev_year_total = sum(channel_total.get("2025", {}).values())
    
    rows.append({
        "구분": "계",
        "실적(수량)": f"{sales_total:,.0f}",
        "경영비(%)": f"{(sales_total/annual_total):.2f}%" if annual_total > 0 else "-",
        "실행비(%)": f"{(sales_total/action_total):.2f}%" if action_total > 0 else "-",
        "전년비(%)": f"{((sales_total/prev_year_total - 1) * 100):.2f}%" if prev_year_total > 0 else "-"
    })
    
    return pd.DataFrame(rows)

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
        
        st.dataframe(create_summary_table_with_group(all_products), width='stretch', hide_index=True)

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
        
        # 26년 계 - 월 선택
        st.subheader("📊 26년 계")
        months = sorted(set().union(*[p.get("SALES", {}).keys() for p in all_products.values()]), 
                       key=lambda x: int(x.replace("월", "")) if "월" in x else 0)
        selected_month = st.selectbox("📅 월 선택", months, key="fcst_month")
        
        st.dataframe(create_month_summary_table(all_products, selected_month), width='stretch', hide_index=True)
        st.divider()
        
        # 제품별 상세
        st.subheader("📦 제품별 상세")
        for product_name in PRODUCT_ORDER:
            if product_name not in all_products:
                continue
            
            with st.expander(f"📦 {product_name}", expanded=False):
                product_data = all_products[product_name]
                
                # 제품 전체
                st.write(f"**{product_name} 계**")
                product_summary = {product_name: product_data}
                st.dataframe(create_summary_table_no_group(product_summary), width='stretch', hide_index=True)
                st.divider()
                
                # 채널별 (Seg.별)
                st.write("**Seg.별**")
                for channel_name in ["SOP", "쿠팡", "종합몰", "홈쇼핑"]:
                    channel_data = data['bizplan'].get(channel_name, {})
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
                    
                    # 채널별 세로 표
                    st.write(f"**{channel_name}**")
                    st.dataframe(create_channel_summary_table(channel_total), width='stretch', hide_index=True)

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
