import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

st.set_page_config(page_title="PP3G 통합 대시보드", page_icon="📊", layout="wide")

# 보고서용 Google Fonts 적용
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap');

* {
    font-family: 'IBM Plex Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
    font-weight: 600 !important;
    font-family: 'IBM Plex Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# 거래선 목록
AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]
PRODUCT_ORDER = ["냉장고", "김치냉장고", "의류케어", "조리기기", "정수기"]

# 세션 상태
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "page" not in st.session_state:
    st.session_state.page = "전체"

# 데이터 로드
@st.cache_data(ttl=3600)
def load_sales_data():
    """KPI 데이터 로드"""
    data = {}
    
    bizplan = {}
    for f in ['bizplan_SOP.json', 'bizplan_쿠팡.json', 'bizplan_종합몰.json', 'bizplan_홈쇼핑.json']:
        try:
            with open(f, encoding='utf-8') as file:
                bizplan.update(json.load(file))
        except:
            pass
    data['bizplan'] = bizplan
    
    premium = {}
    for f in ['premium_냉장고.json', 'premium_세탁기.json', 'premium_식기세척기.json', 'premium_정수기.json']:
        try:
            with open(f, encoding='utf-8') as file:
                premium.update(json.load(file))
        except:
            pass
    data['premium'] = premium
    
    base_files = {
        'smartstore': 'smartstore_customers.json',
        'live_commerce': 'live_commerce_complete.json',
        'affiliate': 'affiliate_final_data.json',
        'coupang_ppm': 'coupang_ppm_data.json'
    }
    
    for key, filename in base_files.items():
        try:
            with open(filename, encoding='utf-8') as f:
                data[key] = json.load(f)
        except:
            data[key] = {}
    
    return data

def load_weekly_data():
    if os.path.exists("weekly_data.json"):
        with open("weekly_data.json", encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_weekly_data(data):
    with open("weekly_data.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_feedback():
    if os.path.exists("feedback.json"):
        with open("feedback.json", encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_feedback(data):
    with open("feedback.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 로그인
def login_page():
    st.title("📊 PP3G 통합 대시보드")
    st.markdown("---")
    
    user_name = st.text_input("이름을 입력하세요")
    
    if st.button("입장", use_container_width=True):
        if user_name.strip():
            st.session_state.user_name = user_name
            st.rerun()
        else:
            st.error("이름을 입력해주세요")

# 값 포매팅 함수
def format_display_value(val):
    """표시용 값 포매팅 (0->-, 음수->△)"""
    if val is None or val == "":
        return "-"
    if isinstance(val, str):
        return val
    if isinstance(val, (int, float)):
        if val == 0:
            return "-"
        elif val < 0:
            if isinstance(val, float) and val > -1:
                return f"△{abs(val):.1f}%"
            return f"△{int(abs(val))}" if val == int(val) else f"△{abs(val):.2f}"
        else:
            return f"{int(val):,}"
    return str(val)

# 어필리에이트 테이블 생성
def create_affiliate_table(data_dict, title=""):
    """어필리에이트 4단계 계층형 테이블 생성"""
    st.markdown(f"### {title}")
    
    html = """
    <style>
        .affiliate-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .affiliate-table th, .affiliate-table td { border: 1px solid #d0d0d0; padding: 8px 6px; text-align: center; height: 26px; }
        .header-tier1 { background: #d9e1f2; font-weight: 600; font-size: 14px; }
        .header-tier2 { background: #e7eef7; font-weight: 500; font-size: 13px; }
        .total-row { background: #fff2cc; font-weight: 600; border-top: 2px solid #333; }
        .data-row { background: #f9f9f9; }
        .data-row:nth-child(even) { background: #ffffff; }
        .agency-col { text-align: left; font-weight: 500; padding-left: 8px; }
        .number { text-align: right; padding-right: 4px; font-family: 'Courier New', monospace; }
    </style>
    <table class="affiliate-table">
        <thead>
            <tr>
                <th rowspan="2" class="header-tier1">거래선</th>
                <th colspan="4" class="header-tier1">어필리에이트</th>
                <th colspan="6" class="header-tier1">쇼핑커넥트</th>
                <th colspan="4" class="header-tier1">공동구매</th>
            </tr>
            <tr>
                <th class="header-tier2">크리<br/>운영수</th>
                <th class="header-tier2">운영<br/>모델</th>
                <th class="header-tier2">주문<br/>건수</th>
                <th class="header-tier2">주문금액<br/>(백만)</th>
                <th class="header-tier2">크리</th>
                <th class="header-tier2">운영</th>
                <th class="header-tier2">유입수</th>
                <th class="header-tier2">상품주문</th>
                <th class="header-tier2">전환율<br/>(%)</th>
                <th class="header-tier2">주문금액<br/>(백만)</th>
                <th class="header-tier2">크리</th>
                <th class="header-tier2">운영</th>
                <th class="header-tier2">상품주문</th>
                <th class="header-tier2">주문금액<br/>(백만)</th>
            </tr>
        </thead>
        <tbody>
    """
    
    def add_row(agency_name, is_total=False, data_item=None):
        row_class = "total-row" if is_total else "data-row"
        html_row = f'<tr class="{row_class}"><td class="agency-col">{agency_name}</td>'
        if data_item:
            aff = data_item.get("어필리에이트", {})
            html_row += f'<td class="number">{format_display_value(aff.get("크리에이터"))}</td>'
            html_row += f'<td class="number">{format_display_value(aff.get("운영모델"))}</td>'
            html_row += f'<td class="number">{format_display_value(aff.get("주문건수"))}</td>'
            html_row += f'<td class="number">{format_display_value(aff.get("주문금액"))}</td>'
            shop = data_item.get("쇼핑커넥트", {})
            html_row += f'<td class="number">{format_display_value(shop.get("크리에이터"))}</td>'
            html_row += f'<td class="number">{format_display_value(shop.get("운영모델"))}</td>'
            html_row += f'<td class="number">{format_display_value(shop.get("유입수"))}</td>'
            html_row += f'<td class="number">{format_display_value(shop.get("상품주문"))}</td>'
            conversion = shop.get("전환율")
            if conversion is None or conversion == 0:
                conv_str = "-"
            elif conversion < 0:
                conv_str = f"△{abs(conversion):.2f}%"
            else:
                conv_str = f"{conversion:.2f}%"
            html_row += f'<td class="number">{conv_str}</td>'
            html_row += f'<td class="number">{format_display_value(shop.get("주문금액"))}</td>'
            joint = data_item.get("공동구매", {})
            html_row += f'<td class="number">{format_display_value(joint.get("크리에이터"))}</td>'
            html_row += f'<td class="number">{format_display_value(joint.get("운영모델"))}</td>'
            html_row += f'<td class="number">{format_display_value(joint.get("상품주문"))}</td>'
            html_row += f'<td class="number">{format_display_value(joint.get("주문금액"))}</td>'
        html_row += '</tr>'
        return html_row
    
    if "계" in data_dict:
        html += add_row("계", is_total=True, data_item=data_dict["계"])
    for agency in AGENCIES:
        if agency in data_dict:
            html += add_row(agency, is_total=False, data_item=data_dict[agency])
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

# 메인 대시보드
def dashboard():
    user_name = st.session_state.user_name
    
    # 사이드바 메뉴
    with st.sidebar:
        st.title("📑 메뉴")
        st.divider()
        
        pages = [
            ("📊 전체", "전체"),
            ("📈 FCST", "FCST"),
            ("💎 프리미엄", "프리미엄"),
            ("🛒 스마트스토어", "스마트스토어"),
            ("📹 라이브커머스", "라이브"),
            ("🤝 어필리에이트", "어필"),
            ("✏️ 거래선입력", "거래선입력"),
            ("📋 거래선현황", "거래선현황"),
            ("💬 담당자피드백", "담당자피드백"),
        ]
        
        for emoji_name, page_key in pages:
            if st.button(emoji_name, use_container_width=True, key=f"btn_{page_key}"):
                st.session_state.page = page_key
        
        st.divider()
        st.caption(f"사용자: {user_name}")
        
        if st.button("←로그아웃", use_container_width=True):
            st.session_state.user_name = None
            st.rerun()
    
    # 메인 콘텐츠
    st.title("📊 PP3G 통합 대시보드")
    st.divider()
    
    sales_data = load_sales_data()
    weekly_data = load_weekly_data()
    feedback_data = load_feedback()
    
    current_page = st.session_state.page
    
    # 전체
    if current_page == "전체":
        st.subheader("📊 대시보드 SUMMARY")
        
        # 탭 생성
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 FCST", "🛒 스마트스토어", "📹 라이브커머스", "🤝 어필리에이트", "💎 프리미엄"])
        
        # Tab 1: FCST
        with tab1:
            st.write("#### FCST 현황")
            if sales_data['bizplan']:
                all_products = {}
                for channel_data in sales_data['bizplan'].values():
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
                
                # 최신월만 표시
                months = sorted(set().union(*[p.get("SALES", {}).keys() for p in all_products.values()]),
                               key=lambda x: int(x.replace("월", "")) if "월" in x else 0, reverse=True)
                if months:
                    latest_month = months[0]
                    st.write(f"**{latest_month} 현황**")
                    
                    rows = []
                    grand_total_sales = sum(all_products[pn].get("SALES", {}).get(latest_month, 0) for pn in all_products)
                    grand_total_annual = sum(all_products[pn].get("ANNUAL", {}).get(latest_month, 0) for pn in all_products)
                    
                    rows.append({
                        "제품": "그룹 계",
                        "실적(수량)": f"{grand_total_sales:,.0f}",
                        "경영비(%)": f"{(grand_total_sales/grand_total_annual):.2f}%" if grand_total_annual > 0 else "-"
                    })
                    
                    for product_name in PRODUCT_ORDER:
                        if product_name in all_products:
                            sales = all_products[product_name].get("SALES", {}).get(latest_month, 0)
                            annual = all_products[product_name].get("ANNUAL", {}).get(latest_month, 1)
                            rows.append({
                                "제품": product_name,
                                "실적(수량)": f"{sales:,.0f}",
                                "경영비(%)": f"{(sales/annual):.2f}%" if annual > 0 else "-"
                            })
                    
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        
        # Tab 2: 스마트스토어
        with tab2:
            st.write("#### 스마트스토어 현황")
            if sales_data['smartstore'] and '월별' in sales_data['smartstore']:
                months = sorted(list(sales_data['smartstore']['월별'].keys()), reverse=True)
                if months:
                    latest_month = months[0]
                    st.write(f"**{latest_month} 현황**")
                    
                    st.dataframe(pd.DataFrame([
                        {"거래선": k, **v} 
                        for k, v in sales_data['smartstore']['월별'][latest_month].items() 
                        if isinstance(v, dict)
                    ]), use_container_width=True, hide_index=True)
        
        # Tab 3: 라이브커머스
        with tab3:
            st.write("#### 라이브커머스 현황")
            if sales_data['live_commerce'] and '월별' in sales_data['live_commerce']:
                months = sorted(list(sales_data['live_commerce']['월별'].keys()), reverse=True)
                if months:
                    latest_month = months[0]
                    st.write(f"**{latest_month} 현황**")
                    
                    st.dataframe(pd.DataFrame([
                        {"거래선": k, **v} 
                        for k, v in sales_data['live_commerce']['월별'][latest_month].items() 
                        if isinstance(v, dict)
                    ]), use_container_width=True, hide_index=True)
        
        # Tab 4: 어필리에이트
        with tab4:
            st.write("#### 어필리에이트 현황")
            affiliate_data = sales_data.get('affiliate', {})
            if affiliate_data:
                months = affiliate_data.get('월별', {})
                if months:
                    months_list = sorted(list(months.keys()), reverse=True)
                    if months_list:
                        latest_month = months_list[0]
                        st.write(f"**{latest_month} 현황**")
                        create_affiliate_table(months[latest_month], "")
        
        # Tab 5: 프리미엄
        with tab5:
            st.write("#### 프리미엄 현황")
            if sales_data['premium']:
                premium_data = sales_data['premium']
                products = list(premium_data.keys())[:3]  # 최대 3개 제품만 표시
                
                for product in products:
                    st.write(f"**{product}**")
                    product_info = premium_data[product]
                    
                    if isinstance(product_info, dict):
                        if '월별' in product_info:
                            months = sorted(list(product_info['월별'].keys()), reverse=True)
                            if months:
                                latest_month = months[0]
                                month_data = product_info['월별'][latest_month]
                                st.dataframe(pd.DataFrame([
                                    {"거래선": k, **v} 
                                    for k, v in month_data.items() 
                                    if isinstance(v, dict)
                                ]), use_container_width=True, hide_index=True)
                        else:
                            st.write(product_info)
                    elif isinstance(product_info, list):
                        if product_info and isinstance(product_info[0], dict):
                            st.dataframe(pd.DataFrame(product_info), use_container_width=True, hide_index=True)
            else:
                st.info("프리미엄 데이터가 없습니다")
    
    # FCST
    elif current_page == "FCST":
        st.subheader("📈 FCST 현황")
        
        if sales_data['bizplan']:
            all_products = {}
            for channel_data in sales_data['bizplan'].values():
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
            
            months = sorted(set().union(*[p.get("SALES", {}).keys() for p in all_products.values()]),
                           key=lambda x: int(x.replace("월", "")) if "월" in x else 0, reverse=True)
            
            selected_month = st.selectbox("월 선택", months)
            
            rows = []
            for product_name in PRODUCT_ORDER:
                if product_name in all_products:
                    product_data = all_products[product_name]
                    sales = product_data.get("SALES", {}).get(selected_month, 0)
                    annual = product_data.get("ANNUAL", {}).get(selected_month, 1)
                    
                    rows.append({
                        "제품": product_name,
                        "실적(수량)": f"{sales:,.0f}",
                        "경영비(%)": f"{(sales/annual):.2f}%" if annual > 0 else "-"
                    })
            
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    
    # 프리미엄
    elif current_page == "프리미엄":
        st.subheader("💎 프리미엄 비중")
        
        if sales_data['premium']:
            # 제품별로 데이터 표시
            premium_data = sales_data['premium']
            
            # 제품 목록 추출
            products = list(premium_data.keys())
            
            if products:
                st.write(f"**총 {len(products)}개 제품 데이터**")
                
                for product in products:
                    product_info = premium_data[product]
                    
                    with st.expander(f"📊 {product}"):
                        # 데이터가 dict 형식인 경우
                        if isinstance(product_info, dict):
                            # 월별 데이터가 있는 경우
                            if '월별' in product_info:
                                months = sorted(list(product_info['월별'].keys()), reverse=True)
                                selected_month = st.selectbox("월", months, key=f"premium_{product}_month")
                                
                                month_data = product_info['월별'][selected_month]
                                st.dataframe(pd.DataFrame([
                                    {"거래선": k, **v} 
                                    for k, v in month_data.items() 
                                    if isinstance(v, dict)
                                ]), use_container_width=True, hide_index=True)
                            else:
                                # 직접적인 데이터 표시
                                st.write(product_info)
                        # 리스트 형식인 경우
                        elif isinstance(product_info, list):
                            if product_info and isinstance(product_info[0], dict):
                                st.dataframe(pd.DataFrame(product_info), use_container_width=True, hide_index=True)
                            else:
                                st.write(product_info)
                        else:
                            st.write(product_info)
            else:
                st.info("프리미엄 제품 데이터가 없습니다")
        else:
            st.info("프리미엄 데이터를 불러올 수 없습니다")
    
    # 스마트스토어
    elif current_page == "스마트스토어":
        st.subheader("🛒 스마트스토어")
        
        if sales_data['smartstore'] and '월별' in sales_data['smartstore']:
            months = sorted(list(sales_data['smartstore']['월별'].keys()), reverse=True)
            selected_month = st.selectbox("월", months, key="ss_month")
            
            st.dataframe(pd.DataFrame([
                {"대리점": k, **v} 
                for k, v in sales_data['smartstore']['월별'][selected_month].items() 
                if isinstance(v, dict)
            ]), use_container_width=True, hide_index=True)
    
    # 라이브커머스
    elif current_page == "라이브":
        st.subheader("📹 라이브커머스")
        
        if sales_data['live_commerce'] and '월별' in sales_data['live_commerce']:
            months = sorted(list(sales_data['live_commerce']['월별'].keys()), reverse=True)
            selected_month = st.selectbox("월", months, key="live_month")
            
            st.dataframe(pd.DataFrame([
                {"대리점": k, **v} 
                for k, v in sales_data['live_commerce']['월별'][selected_month].items() 
                if isinstance(v, dict)
            ]), use_container_width=True, hide_index=True)
    
    # 어필리에이트
    elif current_page == "어필":
        st.subheader("🤝 어필리에이트 실적")
        
        affiliate_data = sales_data.get('affiliate', {})
        
        if affiliate_data:
            tab1, tab2 = st.tabs(["📅 월별", "📆 주차별"])
            
            with tab1:
                st.write("#### 월별 실적")
                months = affiliate_data.get('월별', {})
                if months:
                    months_list = sorted(list(months.keys()), reverse=True)
                    selected_month = st.selectbox("월 선택", months_list, key="month_select")
                    
                    if selected_month in months:
                        display_data = months[selected_month].copy()
                        
                        # 8월인 경우 주차별 합계로 표시
                        if selected_month == "8월":
                            weeks_data = affiliate_data.get('주차별', {})
                            if weeks_data:
                                # 거래선별 합계 계산
                                sum_data = {}
                                for agency in AGENCIES:
                                    agency_sum = {
                                        "어필리에이트": {"크리에이터": 0, "운영모델": 0, "주문건수": 0, "주문금액": 0},
                                        "쇼핑커넥트": {"크리에이터": 0, "운영모델": 0, "유입수": 0, "상품주문": 0, "주문금액": 0},
                                        "공동구매": {"크리에이터": 0, "운영모델": 0, "상품주문": 0, "주문금액": 0}
                                    }
                                    
                                    for week in weeks_data.values():
                                        if agency in week:
                                            for channel in ["어필리에이트", "쇼핑커넥트", "공동구매"]:
                                                for key, val in week[agency][channel].items():
                                                    if key != "전환율" and isinstance(val, (int, float)):
                                                        agency_sum[channel][key] += val
                                    
                                    # 쇼핑커넥트 전환율 계산
                                    if agency_sum["쇼핑커넥트"]["유입수"] > 0:
                                        agency_sum["쇼핑커넥트"]["전환율"] = (agency_sum["쇼핑커넥트"]["상품주문"] / agency_sum["쇼핑커넥트"]["유입수"]) * 100
                                    else:
                                        agency_sum["쇼핑커넥트"]["전환율"] = 0
                                    
                                    sum_data[agency] = agency_sum
                                
                                # 전체 합계
                                total_sum = {
                                    "어필리에이트": {"크리에이터": 0, "운영모델": 0, "주문건수": 0, "주문금액": 0},
                                    "쇼핑커넥트": {"크리에이터": 0, "운영모델": 0, "유입수": 0, "상품주문": 0, "주문금액": 0},
                                    "공동구매": {"크리에이터": 0, "운영모델": 0, "상품주문": 0, "주문금액": 0}
                                }
                                
                                for agency_data in sum_data.values():
                                    for channel in ["어필리에이트", "쇼핑커넥트", "공동구매"]:
                                        for key, val in agency_data[channel].items():
                                            if key != "전환율" and isinstance(val, (int, float)):
                                                total_sum[channel][key] += val
                                
                                if total_sum["쇼핑커넥트"]["유입수"] > 0:
                                    total_sum["쇼핑커넥트"]["전환율"] = (total_sum["쇼핑커넥트"]["상품주문"] / total_sum["쇼핑커넥트"]["유입수"]) * 100
                                else:
                                    total_sum["쇼핑커넥트"]["전환율"] = 0
                                
                                sum_data["계"] = total_sum
                                display_data = sum_data
                        
                        create_affiliate_table(display_data, f"📊 {selected_month} 어필리에이트 실적")
                else:
                    st.warning("월별 데이터가 없습니다")
            
            with tab2:
                st.write("#### 주차별 실적")
                weeks = affiliate_data.get('주차별', {})
                if weeks:
                    weeks_list = sorted(list(weeks.keys()), reverse=True)
                    selected_week = st.selectbox("주차 선택", weeks_list, key="week_select")
                    if selected_week in weeks:
                        create_affiliate_table(weeks[selected_week], f"📊 {selected_week} 어필리에이트 실적")
                else:
                    st.warning("주차별 데이터가 없습니다")
        else:
            st.warning("어필리에이트 데이터가 없습니다")
    
    # 거래선 입력
    elif current_page == "거래선입력":
        st.subheader("✏️ 거래선 주차별 입력")
        
        with st.form("weekly_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                input_month = st.selectbox("월", ["7월", "8월"], key="input_month")
            with col2:
                agency = st.selectbox("거래선", AGENCIES, key="input_agency")
            with col3:
                week = st.number_input("주차", min_value=1, max_value=52, step=1, key="input_week")
            
            st.write("---")
            st.subheader("1️⃣ 스마트스토어")
            col1, col2, col3 = st.columns(3)
            with col1:
                ss_total = st.number_input("총 고객수", min_value=0, step=1, key="ss_total_input")
            with col2:
                ss_new = st.number_input("신규 고객수", min_value=0, step=1, key="ss_new_input")
            with col3:
                ss_repeat = st.number_input("재구매 고객수", min_value=0, step=1, key="ss_repeat_input")
            
            st.write("---")
            st.subheader("2️⃣ 어필리에이트")
            col1, col2 = st.columns(2)
            with col1:
                af_sales = st.number_input("판매액 (원)", min_value=0, step=100000, key="af_sales_input")
            with col2:
                af_visits = st.number_input("방문수", min_value=0, step=1, key="af_visits_input")
            af_notes = st.text_area("특이사항", height=60, key="af_notes_input")
            
            st.write("---")
            st.subheader("3️⃣ 라이브커머스")
            col1, col2 = st.columns(2)
            with col1:
                live_count = st.number_input("방송 횟수", min_value=0, step=1, key="live_count_input")
            with col2:
                live_sales = st.number_input("판매액 (원)", min_value=0, step=100000, key="live_sales_input")
            live_notes = st.text_area("특이사항", height=60, key="live_notes_input")
            
            st.write("---")
            st.subheader("4️⃣ 마케팅활동")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write("**□ 어필리에이트**")
                aff_activity = st.text_area("활동", height=80, key="aff_activity")
            with col2:
                st.write("**□ 네이버**")
                nav_activity = st.text_area("활동", height=80, key="nav_activity")
            with col3:
                st.write("**□ 광고운영**")
                ad_activity = st.text_area("활동", height=80, key="ad_activity")
            
            st.write("---")
            
            if st.form_submit_button("💾 저장", use_container_width=True):
                weekly_data[agency] = weekly_data.get(agency, {})
                weekly_data[agency][str(week)] = {
                    "월": input_month,
                    "등록일": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "스마트스토어": {"총고객수": ss_total, "신규고객": ss_new, "재구매": ss_repeat},
                    "어필리에이트": {"판매액": af_sales, "방문수": af_visits, "특이사항": af_notes},
                    "라이브커머스": {"방송횟수": live_count, "판매액": live_sales, "특이사항": live_notes},
                    "마케팅활동": {"어필리에이트": aff_activity, "네이버": nav_activity, "광고운영": ad_activity}
                }
                save_weekly_data(weekly_data)
                st.success(f"✅ {input_month} {agency} {week}주차 저장됨!")
    
    # 거래선 현황
    elif current_page == "거래선현황":
        st.subheader("📋 거래선 현황")
        
        selected_agency = st.selectbox("거래선 선택", AGENCIES, key="view_agency")
        
        if selected_agency in weekly_data:
            for week in sorted(weekly_data[selected_agency].keys(), key=lambda x: int(x), reverse=True):
                data = weekly_data[selected_agency][week]
                month_info = data.get('월', '')
                month_display = f" ({month_info})" if month_info else ""
                
                with st.expander(f"**{week}주차{month_display}** ({data.get('등록일', '-')})"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.subheader("🛒 스마트스토어")
                        ss = data.get('스마트스토어', {})
                        st.metric("총 고객수", f"{ss.get('총고객수', 0):,}")
                        st.metric("신규 고객", f"{ss.get('신규고객', 0):,}")
                        st.metric("재구매", f"{ss.get('재구매', 0):,}")
                    
                    with col2:
                        st.subheader("📱 어필리에이트")
                        af = data.get('어필리에이트', {})
                        st.metric("판매액", f"{af.get('판매액', 0):,}")
                        st.metric("방문수", f"{af.get('방문수', 0):,}")
                    
                    with col3:
                        st.subheader("📹 라이브커머스")
                        lc = data.get('라이브커머스', {})
                        st.metric("방송 횟수", f"{lc.get('방송횟수', 0)}")
                        st.metric("판매액", f"{lc.get('판매액', 0):,}")
                    
                    st.write("---")
                    st.subheader("📢 마케팅활동")
                    ma = data.get('마케팅활동', {})
                    
                    if ma.get('어필리에이트'):
                        with st.expander("□ 어필리에이트"):
                            st.write(ma.get('어필리에이트'))
                    if ma.get('네이버'):
                        with st.expander("□ 네이버"):
                            st.write(ma.get('네이버'))
                    if ma.get('광고운영'):
                        with st.expander("□ 광고운영"):
                            st.write(ma.get('광고운영'))
                    
                    st.write("---")
                    st.subheader("⚙️ 데이터 관리")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✏️ 수정", key=f"edit_{selected_agency}_{week}", use_container_width=True):
                            st.session_state.edit_mode = True
                            st.session_state.edit_week = week
                            st.session_state.edit_agency = selected_agency
                    with col2:
                        if st.button("🗑️ 삭제", key=f"delete_{selected_agency}_{week}", use_container_width=True):
                            del weekly_data[selected_agency][week]
                            save_weekly_data(weekly_data)
                            st.success(f"✅ {selected_agency} {week}주차 삭제됨!")
                            st.rerun()
                    
                    # 수정 모드
                    if st.session_state.get('edit_mode') and st.session_state.get('edit_week') == week and st.session_state.get('edit_agency') == selected_agency:
                        st.write("---")
                        st.subheader("📝 데이터 수정")
                        
                        with st.form("edit_weekly_form"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                months_list = ["7월", "8월"]
                                current_month = data.get('월', '7월')
                                month_index = months_list.index(current_month) if current_month in months_list else 0
                                edit_month = st.selectbox("월", months_list, index=month_index, key="edit_month")
                            
                            st.write("---")
                            st.subheader("1️⃣ 스마트스토어")
                            col1, col2, col3 = st.columns(3)
                            ss = data.get('스마트스토어', {})
                            with col1:
                                edit_ss_total = st.number_input("총 고객수", min_value=0, step=1, value=ss.get('총고객수', 0), key="edit_ss_total")
                            with col2:
                                edit_ss_new = st.number_input("신규 고객수", min_value=0, step=1, value=ss.get('신규고객', 0), key="edit_ss_new")
                            with col3:
                                edit_ss_repeat = st.number_input("재구매 고객수", min_value=0, step=1, value=ss.get('재구매', 0), key="edit_ss_repeat")
                            
                            st.write("---")
                            st.subheader("2️⃣ 어필리에이트")
                            col1, col2 = st.columns(2)
                            af = data.get('어필리에이트', {})
                            with col1:
                                edit_af_sales = st.number_input("판매액 (원)", min_value=0, step=100000, value=af.get('판매액', 0), key="edit_af_sales")
                            with col2:
                                edit_af_visits = st.number_input("방문수", min_value=0, step=1, value=af.get('방문수', 0), key="edit_af_visits")
                            edit_af_notes = st.text_area("특이사항", height=60, value=af.get('특이사항', ''), key="edit_af_notes")
                            
                            st.write("---")
                            st.subheader("3️⃣ 라이브커머스")
                            col1, col2 = st.columns(2)
                            lc = data.get('라이브커머스', {})
                            with col1:
                                edit_live_count = st.number_input("방송 횟수", min_value=0, step=1, value=lc.get('방송횟수', 0), key="edit_live_count")
                            with col2:
                                edit_live_sales = st.number_input("판매액 (원)", min_value=0, step=100000, value=lc.get('판매액', 0), key="edit_live_sales")
                            edit_live_notes = st.text_area("특이사항", height=60, value=lc.get('특이사항', ''), key="edit_live_notes")
                            
                            st.write("---")
                            st.subheader("4️⃣ 마케팅활동")
                            col1, col2, col3 = st.columns(3)
                            ma = data.get('마케팅활동', {})
                            with col1:
                                st.write("**□ 어필리에이트**")
                                edit_aff_activity = st.text_area("활동", height=80, value=ma.get('어필리에이트', ''), key="edit_aff_activity")
                            with col2:
                                st.write("**□ 네이버**")
                                edit_nav_activity = st.text_area("활동", height=80, value=ma.get('네이버', ''), key="edit_nav_activity")
                            with col3:
                                st.write("**□ 광고운영**")
                                edit_ad_activity = st.text_area("활동", height=80, value=ma.get('광고운영', ''), key="edit_ad_activity")
                            
                            st.write("---")
                            
                            if st.form_submit_button("💾 저장", use_container_width=True):
                                weekly_data[selected_agency][week] = {
                                    "월": edit_month,
                                    "등록일": data.get('등록일'),
                                    "스마트스토어": {"총고객수": edit_ss_total, "신규고객": edit_ss_new, "재구매": edit_ss_repeat},
                                    "어필리에이트": {"판매액": edit_af_sales, "방문수": edit_af_visits, "특이사항": edit_af_notes},
                                    "라이브커머스": {"방송횟수": edit_live_count, "판매액": edit_live_sales, "특이사항": edit_live_notes},
                                    "마케팅활동": {"어필리에이트": edit_aff_activity, "네이버": edit_nav_activity, "광고운영": edit_ad_activity}
                                }
                                save_weekly_data(weekly_data)
                                st.session_state.edit_mode = False
                                st.success(f"✅ {selected_agency} {week}주차 수정됨!")
                                st.rerun()
        else:
            st.info("등록된 데이터가 없습니다")
    
    # 담당자 피드백
    elif current_page == "담당자피드백":
        st.subheader("💬 담당자 피드백")
        
        feedback_agency = st.selectbox("거래선 선택", AGENCIES, key="feedback_agency")
        
        if feedback_agency in weekly_data:
            recent_weeks = sorted(weekly_data[feedback_agency].items(), key=lambda x: int(x[0]), reverse=True)[:5]
            
            for week, data in recent_weeks:
                month_info = data.get('월', '')
                month_display = f" ({month_info})" if month_info else ""
                
                st.write(f"### {week}주차{month_display}")
                
                # 데이터 표시
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("스마트스토어", f"{data.get('스마트스토어', {}).get('총고객수', 0):,}")
                with col2:
                    st.metric("어필리에이트", f"{data.get('어필리에이트', {}).get('판매액', 0):,}")
                with col3:
                    st.metric("라이브", f"{data.get('라이브커머스', {}).get('방송횟수', 0)}")
                
                st.write("---")
                
                # 각 항목별 피드백
                st.subheader("📝 세부 피드백")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**🛒 스마트스토어**")
                    ss_comment = st.text_area("의견", height=60, key=f"fb_ss_{feedback_agency}_{week}")
                
                with col2:
                    st.write("**📱 어필리에이트**")
                    af_comment = st.text_area("의견", height=60, key=f"fb_af_{feedback_agency}_{week}")
                
                with col3:
                    st.write("**📹 라이브커머스**")
                    lc_comment = st.text_area("의견", height=60, key=f"fb_lc_{feedback_agency}_{week}")
                
                st.write("---")
                
                st.write("**📢 마케팅활동**")
                marketing_comment = st.text_area("의견", height=60, key=f"fb_marketing_{feedback_agency}_{week}")
                
                st.write("---")
                
                if st.button("💾 저장", key=f"fb_save_{feedback_agency}_{week}", use_container_width=True):
                    if feedback_agency not in feedback_data:
                        feedback_data[feedback_agency] = {}
                    
                    feedback_data[feedback_agency][week] = {
                        "스마트스토어": ss_comment,
                        "어필리에이트": af_comment,
                        "라이브커머스": lc_comment,
                        "마케팅활동": marketing_comment,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    
                    save_feedback(feedback_data)
                    st.success("✅ 피드백 저장됨!")
                
                st.divider()

# 메인
if st.session_state.user_name is None:
    login_page()
else:
    dashboard()