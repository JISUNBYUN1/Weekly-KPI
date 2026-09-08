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
    import os
    data = {}
    
    # 현재 디렉토리 확인
    current_dir = os.getcwd()
    
    bizplan = {}
    bizplan_files = ['bizplan_SOP.json', 'bizplan_쿠팡.json', 'bizplan_종합몰.json', 'bizplan_홈쇼핑.json']
    for f in bizplan_files:
        try:
            with open(f, encoding='utf-8') as file:
                bizplan.update(json.load(file))
        except FileNotFoundError:
            pass
        except Exception as e:
            pass
    data['bizplan'] = bizplan
    
    premium = {}
    premium_files = ['premium_냉장고.json', 'premium_세탁기.json', 'premium_식기세척기.json', 'premium_정수기.json']
    for f in premium_files:
        try:
            with open(f, encoding='utf-8') as file:
                premium.update(json.load(file))
        except FileNotFoundError:
            pass
        except Exception as e:
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
                loaded_data = json.load(f)
                data[key] = loaded_data
        except FileNotFoundError:
            # 파일을 찾을 수 없으면 빈 데이터로 설정
            data[key] = {}
        except json.JSONDecodeError:
            data[key] = {}
        except Exception as e:
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

# 라이브커머스 테이블 생성
def create_live_commerce_table(data_dict, title=""):
    """라이브커머스 계층형 테이블 생성 (소수점 1자리 ROUND)
    
    필요한 데이터 구조:
    {
        "전체": {
            "방송횟수": int,
            "방송매출": float (원 단위 또는 백만원),
            "소요비용": float (원 단위 또는 백만원)
        },
        "거래선명": {
            "방송횟수": int,
            "방송매출": float,
            "소요비용": float
        }
    }
    """
    st.markdown(f"### {title}")
    
    html = """
    <style>
        .live-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .live-table th, .live-table td { border: 1px solid #d0d0d0; padding: 8px 6px; text-align: center; height: 26px; }
        .header-tier1 { background: #e2efda; font-weight: 600; font-size: 13px; }
        .total-row { background: #fff2cc; font-weight: 600; border-top: 2px solid #333; }
        .data-row { background: #f9f9f9; }
        .data-row:nth-child(even) { background: #ffffff; }
        .agency-col { text-align: left; font-weight: 500; padding-left: 8px; }
        .number { text-align: right; padding-right: 4px; font-family: 'Courier New', monospace; }
        .negative { color: #d92d20; }
    </style>
    <table class="live-table">
        <thead>
            <tr>
                <th class="header-tier1">거래선</th>
                <th class="header-tier1">방송횟수</th>
                <th class="header-tier1">방송매출(백만)</th>
                <th class="header-tier1">소요비용(백만)</th>
                <th class="header-tier1">방송효율</th>
                <th class="header-tier1">회당매출(백만)</th>
            </tr>
        </thead>
        <tbody>
    """
    
    def add_row(agency_name, is_total=False, broadcast_count=0, broadcast_sale=0, cost=0):
        """행 생성 (6개 칼럼: 거래선, 방송횟수, 방송매출, 소요비용, 방송효율, 회당매출)
        broadcast_count: 방송횟수 (정수)
        broadcast_sale: 방송매출 (원 단위 또는 백만원, float) → 소수점 1자리
        cost: 소요비용 (원 단위 또는 백만원, float) → 소수점 2자리
        """
        row_class = "total-row" if is_total else "data-row"
        html_row = f'<tr class="{row_class}"><td class="agency-col">{agency_name}</td>'
        
        # 방송횟수 (정수)
        html_row += f'<td class="number">{format_display_value(int(broadcast_count))}</td>'
        
        # 방송매출 (원 단위를 백만 단위로 변환, 소수점 1자리, 천단위 쉼표)
        if isinstance(broadcast_sale, (int, float)):
            # 원 단위인지 백만 단위인지 판단 (1000000 이상이면 원 단위)
            if broadcast_sale >= 1000000:
                sale_million = broadcast_sale / 1000000
            else:
                sale_million = broadcast_sale
            html_row += f'<td class="number">{round(sale_million, 1):,.1f}</td>'
        else:
            html_row += f'<td class="number">-</td>'
        
        # 소요비용 (원 단위를 백만 단위로 변환, 소수점 2자리, 천단위 쉼표)
        if isinstance(cost, (int, float)) and cost > 0:
            if cost >= 1000000:
                cost_million = cost / 1000000
            else:
                cost_million = cost
            html_row += f'<td class="number">{round(cost_million, 2):,.2f}</td>'
        else:
            html_row += f'<td class="number">-</td>'
        
        # 방송효율 = 방송매출 / 소요비용 (소수점 2자리)
        if isinstance(cost, (int, float)) and cost > 0 and isinstance(broadcast_sale, (int, float)):
            efficiency = round(broadcast_sale / cost, 2)
            html_row += f'<td class="number">{efficiency:.2f}</td>'
        else:
            html_row += f'<td class="number">-</td>'
        
        # 회당매출 = 방송매출 / 방송횟수 (백만원, 소수점 1자리, 천단위 쉼표)
        if isinstance(broadcast_count, (int, float)) and broadcast_count > 0 and isinstance(broadcast_sale, (int, float)):
            if broadcast_sale >= 1000000:
                per_broadcast = broadcast_sale / broadcast_count / 1000000
            else:
                per_broadcast = broadcast_sale / broadcast_count
            per_broadcast_rounded = round(per_broadcast, 1)
            html_row += f'<td class="number">{per_broadcast_rounded:,.1f}</td>'
        else:
            html_row += f'<td class="number">-</td>'
        
        html_row += '</tr>'
        return html_row
    
    # 계 (전체) 행
    if "전체" in data_dict:
        total = data_dict["전체"]
        html += add_row(
            "계",
            is_total=True,
            broadcast_count=total.get('방송횟수', 0),
            broadcast_sale=total.get('방송매출', 0),
            cost=total.get('소요비용', 0)
        )
    
    # 거래선별 행
    for agency in AGENCIES:
        if agency in data_dict:
            agency_data = data_dict[agency]
            html += add_row(
                agency,
                is_total=False,
                broadcast_count=agency_data.get('방송횟수', 0),
                broadcast_sale=agency_data.get('방송매출', 0),
                cost=agency_data.get('소요비용', 0)
            )
    
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)




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
                <th class="header-tier2">크리에이터 운영수</th>
                <th class="header-tier2">운영모델</th>
                <th class="header-tier2">주문건수</th>
                <th class="header-tier2">주문금액(백만)</th>
                <th class="header-tier2">크리에이터 운영수</th>
                <th class="header-tier2">운영모델</th>
                <th class="header-tier2">유입수</th>
                <th class="header-tier2">상품주문</th>
                <th class="header-tier2">전환율(%)</th>
                <th class="header-tier2">주문금액(백만)</th>
                <th class="header-tier2">크리에이터 운영수</th>
                <th class="header-tier2">운영모델</th>
                <th class="header-tier2">상품주문</th>
                <th class="header-tier2">주문금액(백만)</th>
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
            if sales_data['live_commerce']:
                # 8월 데이터 있는지 확인
                if '8월' in sales_data['live_commerce'] and '월별' in sales_data['live_commerce']['8월']:
                    months_data = sales_data['live_commerce']['8월']['월별']
                    months_list = sorted([m for m in months_data.keys() if isinstance(months_data[m], dict)], reverse=True)
                    
                    if months_list:
                        latest_month = months_list[0]
                        st.write(f"**{latest_month} 현황**")
                        
                        month_data = months_data[latest_month]
                        display_data = {}
                        if '전체' in month_data:
                            display_data['전체'] = month_data['전체']
                        for agency in AGENCIES:
                            if agency in month_data:
                                display_data[agency] = month_data[agency]
                        
                        create_live_commerce_table(display_data, "")
                    else:
                        st.info("라이브커머스 데이터가 없습니다")
                else:
                    st.info("라이브커머스 데이터가 없습니다")
            else:
                st.info("라이브커머스 데이터가 없습니다")
        
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
    # 라이브커머스
    elif current_page == "라이브":
        st.subheader("📹 라이브커머스")
        
        live_commerce_data = sales_data.get('live_commerce', {})
        
        if live_commerce_data:
            # 드롭다운: 월 선택
            all_months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
            selected_month = st.selectbox("월 선택", all_months, key="live_month_select")
            
            # 월별 주차 매핑 (weeks_2026 로드)
            try:
                with open('weeks_2026.json', 'r', encoding='utf-8') as f:
                    weeks_2026 = json.load(f)
            except:
                weeks_2026 = {}
            
            def get_weeks_for_live(month):
                """해당 월의 주차 리스트 반환"""
                month_num = int(month.replace('월', ''))
                weeks_list = ["계"]  # 첫 번째는 "계" (전체)
                
                for week, info in weeks_2026.items():
                    month_info = info['month']
                    
                    if isinstance(month_info, int):
                        if month_info == month_num:
                            weeks_list.append(week)
                    elif isinstance(month_info, list):
                        if month_num in month_info:
                            if month_num == month_info[0]:
                                weeks_list.append(f"{week}A")
                            else:
                                weeks_list.append(f"{week}B")
                
                def sort_key(w):
                    if w == "계":
                        return -1
                    num = int(''.join(filter(str.isdigit, w)))
                    return num
                
                return sorted(weeks_list, key=sort_key)
            
            # 드롭다운: 주차 선택
            available_weeks = get_weeks_for_live(selected_month)
            if available_weeks:
                selected_week = st.selectbox("주차 선택", available_weeks, key="live_week_select")
            else:
                st.warning(f"{selected_month}에 주차 데이터가 없습니다")
                selected_week = None
            
            st.write("---")
            
            if selected_week:
                # 데이터 표시
                if selected_week == "계":
                    st.write(f"**📊 {selected_month} 라이브커머스 실적 (월 전체)**")
                else:
                    st.write(f"**📊 {selected_month} {selected_week} 라이브커머스 실적**")
                
                # 월별 데이터
                if selected_month in live_commerce_data and selected_week == "계":
                    if '월별' in live_commerce_data and selected_month in live_commerce_data['월별']:
                        month_data = live_commerce_data['월별'][selected_month]
                        
                        # 소요비용 데이터 로드
                        live_cost_data = {}
                        try:
                            with open('live_commerce_cost_data.json', 'r', encoding='utf-8') as f:
                                live_cost_data = json.load(f)
                                for agency in live_cost_data:
                                    live_cost_data[agency]['소요비용'] = live_cost_data[agency].get('소요비용', 0) / 12
                        except:
                            live_cost_data = {}
                        
                        # 데이터 구성
                        display_data = {}
                        if '전체' in month_data:
                            display_data['전체'] = month_data['전체'].copy()
                            total_cost = sum([data.get('소요비용', 0) for data in live_cost_data.values()])
                            display_data['전체']['소요비용'] = total_cost
                        
                        for agency in AGENCIES:
                            if agency in month_data:
                                display_data[agency] = month_data[agency].copy()
                                if agency in live_cost_data:
                                    display_data[agency]['소요비용'] = live_cost_data[agency]['소요비용']
                                else:
                                    display_data[agency]['소요비용'] = 0
                        
                        create_live_commerce_table(display_data, f"📊 {selected_month} 라이브커머스 실적")
                    else:
                        st.info("해당 월의 데이터가 없습니다")
                
                # 주차별 데이터
                else:
                    week_base = selected_week.replace('A', '').replace('B', '')
                    
                    # 8월 데이터 확인
                    if selected_month == "8월" and '8월' in live_commerce_data and '주차별' in live_commerce_data['8월']:
                        weeks_data = live_commerce_data['8월']['주차별']
                        
                        # 주차명 매핑
                        week_mapping = {
                            "31B주": "W31B", "32주": "W32", "33주": "W33",
                            "34주": "W34", "35주": "W35", "36A주": "W36A"
                        }
                        
                        # 역 매핑 (W35 → 35주)
                        reverse_mapping = {v: k for k, v in week_mapping.items()}
                        
                        selected_week_key = reverse_mapping.get(selected_week, selected_week)
                        
                        if selected_week_key in weeks_data:
                            week_data = weeks_data[selected_week_key]
                            
                            # 소요비용 데이터 로드
                            live_cost_data = {}
                            try:
                                with open('live_commerce_cost_data.json', 'r', encoding='utf-8') as f:
                                    live_cost_data = json.load(f)
                            except:
                                live_cost_data = {}
                            
                            # 데이터 구성
                            display_data = {}
                            if '전체' in week_data:
                                display_data['전체'] = week_data['전체'].copy()
                                total_cost = sum([data.get('소요비용', 0) for data in live_cost_data.values()])
                                display_data['전체']['소요비용'] = total_cost
                            
                            for agency in AGENCIES:
                                if agency in week_data:
                                    display_data[agency] = week_data[agency].copy()
                                    if agency in live_cost_data:
                                        display_data[agency]['소요비용'] = live_cost_data[agency]['소요비용']
                                    else:
                                        display_data[agency]['소요비용'] = 0
                            
                            create_live_commerce_table(display_data, f"📊 {selected_week} 라이브커머스 실적")
                        else:
                            st.info("해당 주차의 데이터가 없습니다")
                    else:
                        st.info("해당 월/주차의 데이터가 없습니다")
        else:
            st.warning("라이브커머스 데이터가 없습니다")
    
    # 어필리에이트
    elif current_page == "어필":
        st.subheader("🤝 어필리에이트 실적")
        
        affiliate_data = sales_data.get('affiliate', {})
        
        if affiliate_data:
            # 드롭다운: 월 선택
            all_months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
            selected_month = st.selectbox("월 선택", all_months, key="affiliate_month_select")
            
            # 월별 주차 매핑 (weeks_2026 로드)
            try:
                with open('weeks_2026.json', 'r', encoding='utf-8') as f:
                    weeks_2026 = json.load(f)
            except:
                weeks_2026 = {}
            
            def get_weeks_for_affiliate(month):
                """해당 월의 주차 리스트 반환"""
                month_num = int(month.replace('월', ''))
                weeks_list = ["계"]  # 첫 번째는 "계" (전체)
                
                for week, info in weeks_2026.items():
                    month_info = info['month']
                    
                    if isinstance(month_info, int):
                        if month_info == month_num:
                            weeks_list.append(week)
                    elif isinstance(month_info, list):
                        if month_num in month_info:
                            if month_num == month_info[0]:
                                weeks_list.append(f"{week}A")
                            else:
                                weeks_list.append(f"{week}B")
                
                def sort_key(w):
                    if w == "계":
                        return -1
                    num = int(''.join(filter(str.isdigit, w)))
                    return num
                
                return sorted(weeks_list, key=sort_key)
            
            # 드롭다운: 주차 선택
            available_weeks = get_weeks_for_affiliate(selected_month)
            if available_weeks:
                selected_week = st.selectbox("주차 선택", available_weeks, key="affiliate_week_select")
            else:
                st.warning(f"{selected_month}에 주차 데이터가 없습니다")
                selected_week = None
            
            st.write("---")
            
            if selected_week:
                # 데이터 표시
                st.write(f"**📊 {selected_month} {selected_week} 어필리에이트 실적**")
                
                # 월별 데이터
                months = affiliate_data.get('월별', {})
                if selected_month in months and selected_week == "계":
                    create_affiliate_table(months[selected_month], f"📊 {selected_month} 어필리에이트 실적")
                
                # 주차별 데이터
                weeks = affiliate_data.get('주차별', {})
                
                # W35A, W35B 등으로 저장된 데이터 찾기
                week_base = selected_week.replace('A', '').replace('B', '')
                if selected_week.endswith('A') or selected_week.endswith('B'):
                    week_key = selected_week
                else:
                    week_key = selected_week
                
                if week_key in weeks:
                    create_affiliate_table(weeks[week_key], f"📊 {selected_week} 어필리에이트 실적")
                elif selected_week != "계":
                    st.info("해당 주차의 데이터가 없습니다")
        else:
            st.warning("어필리에이트 데이터가 없습니다")
    
    # 거래선 입력
    elif current_page == "거래선입력":
        st.subheader("✏️ 거래선 주차별 입력")
        
        # 2026년 주차 정보 로드
        try:
            with open('weeks_2026.json', 'r', encoding='utf-8') as f:
                weeks_2026 = json.load(f)
        except:
            st.error("weeks_2026.json 파일을 찾을 수 없습니다")
            weeks_2026 = {}
        
        # 월별 주차 매핑
        def get_weeks_by_month(month):
            """해당 월의 주차 리스트 반환 (A/B 표시 포함, 역순)"""
            month_num = int(month.replace('월', ''))
            weeks_with_suffix = []
            
            for week, info in weeks_2026.items():
                month_info = info['month']
                
                # 단일 월인 경우 (A/B 없음)
                if isinstance(month_info, int):
                    if month_info == month_num:
                        weeks_with_suffix.append(week)
                
                # 리스트인 경우 (월 경계, A/B 있음)
                elif isinstance(month_info, list):
                    if month_num in month_info:
                        # A/B 결정
                        if month_num == month_info[0]:  # 첫 번째 월 (A)
                            weeks_with_suffix.append(f"{week}A")
                        else:  # 두 번째 월 (B)
                            weeks_with_suffix.append(f"{week}B")
            
            # 주차 숫자로 정렬 후 역순
            def sort_key(w):
                # "W35" → 35, "W35A" → 35, "W35B" → 35
                num = int(''.join(filter(str.isdigit, w)))
                return num
            
            return sorted(weeks_with_suffix, key=sort_key, reverse=True)
        
        # Form 외부에서 월/주차 선택 (form 내에서 업데이트 안 되는 문제 해결)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            input_agency = st.selectbox("거래선 선택", AGENCIES, key="input_agency")
        
        with col2:
            # 월 선택 (1-12월 동적)
            all_months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
            input_month = st.selectbox("월 선택", all_months, key="input_month")
        
        with col3:
            # 선택된 월의 주차 리스트
            available_weeks = get_weeks_by_month(input_month)
            if available_weeks:
                input_week = st.selectbox("주차 선택", available_weeks, key="input_week")
            else:
                st.warning(f"{input_month}에 데이터가 없습니다")
                input_week = None
        
        st.write("---")
        
        with st.form("weekly_form"):
            st.subheader("📝 1️⃣ 네이버 스마트 스토어")
            col1, col2, col3 = st.columns(3)
            with col1:
                ss_new_interest = st.number_input("신규 관심고객수", min_value=0, step=1, key="ss_new_interest_input")
            with col2:
                ss_new_buyer = st.number_input("신규구매 구매자수", min_value=0, step=1, key="ss_new_buyer_input")
            with col3:
                ss_repurchase = st.number_input("재구매 구매자수", min_value=0, step=1, key="ss_repurchase_input")
            
            ss_activity = st.text_area("📌 마케팅활동", placeholder="이번 주 스마트스토어 마케팅 활동을 작성해주세요", height=60, key="ss_activity_input")
            
            st.write("---")
            st.subheader("📱 2️⃣ 어필리에이트")
            
            # 쇼핑커넥트
            st.write("🔹 **쇼핑커넥트**")
            col1, col2, col3 = st.columns(3)
            with col1:
                sc_creator = st.number_input("크리에이터 운영 수", min_value=0, step=1, key="sc_creator_input")
            with col2:
                sc_model = st.number_input("운영 모델 수", min_value=0, step=1, key="sc_model_input")
            with col3:
                sc_visits = st.number_input("유입수", min_value=0, step=1, key="sc_visits_input")
            
            col1, col2 = st.columns(2)
            with col1:
                sc_orders = st.number_input("상품주문건수", min_value=-999, step=1, key="sc_orders_input")
            with col2:
                sc_amount = st.number_input("주문금액 (백만)", min_value=-999.0, step=0.1, key="sc_amount_input")
            
            sc_activity = st.text_area("📌 마케팅활동", placeholder="쇼핑커넥트 마케팅 활동을 작성해주세요", height=60, key="sc_activity_input")
            
            st.write("")
            
            # 공동구매
            st.write("🔹 **공동구매**")
            col1, col2, col3 = st.columns(3)
            with col1:
                cj_creator = st.number_input("크리에이터 운영 수", min_value=0, step=1, key="cj_creator_input")
            with col2:
                cj_model = st.number_input("운영 모델 수", min_value=0, step=1, key="cj_model_input")
            with col3:
                st.write("")
            
            col1, col2 = st.columns(2)
            with col1:
                cj_orders = st.number_input("상품주문건수", min_value=-999, step=1, key="cj_orders_input")
            with col2:
                cj_amount = st.number_input("주문금액 (백만)", min_value=-999.0, step=0.1, key="cj_amount_input")
            
            cj_activity = st.text_area("📌 마케팅활동", placeholder="공동구매 마케팅 활동을 작성해주세요", height=60, key="cj_activity_input")
            
            st.write("---")
            st.subheader("🎥 3️⃣ AI 라이브")
            col1, col2, col3 = st.columns(3)
            with col1:
                live_count = st.number_input("방송횟수", min_value=0, step=1, key="live_count_input")
            with col2:
                live_sale = st.number_input("방송매출 (백만)", min_value=0.0, step=0.1, key="live_sale_input")
            with col3:
                live_cost = st.number_input("소요비용 (백만)", min_value=0.0, step=0.01, key="live_cost_input")
            
            live_activity = st.text_area("📌 마케팅활동", placeholder="AI 라이브 마케팅 활동을 작성해주세요", height=60, key="live_activity_input")
            
            st.write("---")
            st.subheader("🎯 당주 주요활동")
            
            activity_AI라이브효율증대 = st.text_area("📌 AI 라이브 효율 증대", placeholder="AI 라이브 효율 증대 관련 활동을 작성해주세요", height=50, key="activity_AI라이브효율증대_input")
            activity_어필리에이트내재화 = st.text_area("📌 어필리에이트 내재화", placeholder="어필리에이트 내재화 관련 활동을 작성해주세요", height=50, key="activity_어필리에이트내재화_input")
            activity_구독활성화 = st.text_area("📌 구독활성화", placeholder="구독활성화 관련 활동을 작성해주세요", height=50, key="activity_구독활성화_input")
            activity_기타신규프로젝트 = st.text_area("📌 기타 신규 프로젝트", placeholder="기타 신규 프로젝트를 작성해주세요", height=50, key="activity_기타신규프로젝트_input")
            
            st.write("---")
            
            submit_button = st.form_submit_button("💾 저장", use_container_width=True)
            
            if submit_button:
                if input_week is None:
                    st.error("주차를 선택해주세요")
                else:
                    # 주차에서 A/B 제거 (저장용 기본 주차명)
                    # 예: "W35B" → "W35"
                    base_week = input_week.replace('A', '').replace('B', '')
                    
                    # 데이터 조합 (새로운 구조)
                    new_data = {
                        "거래선": input_agency,
                        "월": input_month,
                        "주차": base_week,  # A/B 제거한 주차명 저장
                        "주차_표시": input_week,  # 화면에 보여줬던 형식 저장 (A/B 포함)
                        "네이버스마트스토어": {
                            "신규관심고객수": ss_new_interest,
                            "신규구매구매자수": ss_new_buyer,
                            "재구매구매자수": ss_repurchase,
                            "마케팅활동": ss_activity
                        },
                        "쇼핑커넥트": {
                            "크리에이터운영수": sc_creator,
                            "운영모델수": sc_model,
                            "유입수": sc_visits,
                            "상품주문건수": sc_orders,
                            "주문금액": sc_amount,
                            "마케팅활동": sc_activity
                        },
                        "공동구매": {
                            "크리에이터운영수": cj_creator,
                            "운영모델수": cj_model,
                            "상품주문건수": cj_orders,
                            "주문금액": cj_amount,
                            "마케팅활동": cj_activity
                        },
                        "AI라이브": {
                            "방송횟수": live_count,
                            "방송매출": live_sale,
                            "소요비용": live_cost,
                            "마케팅활동": live_activity
                        },
                        "당주주요활동": {
                            "AI라이브효율증대": activity_AI라이브효율증대,
                            "어필리에이트내재화": activity_어필리에이트내재화,
                            "구독활성화": activity_구독활성화,
                            "기타신규프로젝트": activity_기타신규프로젝트
                        }
                    }
                    
                    # weekly_data.json에 저장
                    if os.path.exists("weekly_data.json"):
                        try:
                            with open("weekly_data.json", "r", encoding='utf-8') as f:
                                loaded_data = json.load(f)
                                # 리스트인지 확인, 아니면 빈 리스트로
                                weekly_data_list = loaded_data if isinstance(loaded_data, list) else []
                        except:
                            weekly_data_list = []
                    else:
                        weekly_data_list = []
                    
                    # 중복 확인 및 업데이트
                    found = False
                    for idx, item in enumerate(weekly_data_list):
                        # item이 딕셔너리인지 확인
                        if isinstance(item, dict) and (item.get("거래선") == input_agency and 
                            item.get("월") == input_month and 
                            item.get("주차") == base_week):
                            weekly_data_list[idx] = new_data
                            found = True
                            break
                    
                    if not found:
                        weekly_data_list.append(new_data)
                    
                    with open("weekly_data.json", "w", encoding='utf-8') as f:
                        json.dump(weekly_data_list, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"✅ {input_agency} - {input_month} {input_week} 데이터가 저장되었습니다!")
                    st.balloons()
    
    # 스마트스토어
    elif current_page == "스마트":
        st.subheader("🛒 스마트스토어 실적")
        
        smartstore_data = sales_data.get('smartstore', {})
        
        if smartstore_data:
            # 월별 데이터만 (월_주차 제외)
            months = [m for m in smartstore_data.keys() if '주차' not in m]
            if months:
                months_list = sorted(months, reverse=True)
                selected_month = st.selectbox("월 선택", months_list, key="ss_month_select")
                
                if selected_month in smartstore_data:
                    month_data = smartstore_data[selected_month]
                    
                    # 테이블 생성
                    st.markdown(f"### 📊 {selected_month} 스마트스토어 실적")
                    
                    html = """
                    <style>
                        .ss-table { width: 100%; border-collapse: collapse; font-size: 13px; }
                        .ss-table th, .ss-table td { border: 1px solid #d0d0d0; padding: 8px 6px; text-align: center; height: 26px; }
                        .ss-header { background: #4472c4; color: white; font-weight: 600; }
                        .ss-total { background: #fff2cc; font-weight: 600; border-top: 2px solid #333; }
                        .ss-data { background: #f9f9f9; }
                        .ss-data:nth-child(even) { background: #ffffff; }
                        .ss-agency { text-align: left; font-weight: 500; padding-left: 8px; }
                        .ss-number { text-align: right; padding-right: 4px; font-family: 'Courier New', monospace; }
                    </style>
                    <table class="ss-table">
                        <thead>
                            <tr>
                                <th class="ss-header">거래선</th>
                                <th class="ss-header">고객수</th>
                                <th class="ss-header">신규유입</th>
                                <th class="ss-header">전월차</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    
                    # 전체 행
                    if '전체' in month_data:
                        total = month_data['전체']
                        html += f"""
                            <tr class="ss-total">
                                <td class="ss-agency">전체</td>
                                <td class="ss-number">{total.get('고객수', 0):,}</td>
                                <td class="ss-number">{total.get('신규유입', 0):,}</td>
                                <td class="ss-number">{total.get('전월차', 0):+,}</td>
                            </tr>
                        """
                    
                    # 거래선별 행
                    for agency in AGENCIES:
                        if agency in month_data:
                            data = month_data[agency]
                            html += f"""
                                <tr class="ss-data">
                                    <td class="ss-agency">{agency}</td>
                                    <td class="ss-number">{data.get('고객수', 0):,}</td>
                                    <td class="ss-number">{data.get('신규유입', 0):,}</td>
                                    <td class="ss-number">{data.get('전월차', 0):+,}</td>
                                </tr>
                            """
                    
                    html += """
                        </tbody>
                    </table>
                    """
                    st.markdown(html, unsafe_allow_html=True)
        else:
            st.warning("스마트스토어 데이터가 없습니다")
    
    # 프리미엄
    elif current_page == "프리미엄":
        st.subheader("💎 프리미엄 제품별 실적")
        
        # 프리미엄 데이터 로드
        premium_data = {}
        premium_products = ['냉장고', '세탁기', '식기세척기', '정수기']
        
        for product in premium_products:
            try:
                with open(f'premium_{product}.json', 'r', encoding='utf-8') as f:
                    premium_data[product] = json.load(f)
            except:
                premium_data[product] = {}
        
        if premium_data:
            # 제품별 Expander
            for product in premium_products:
                if premium_data[product]:
                    with st.expander(f"💎 {product}", expanded=False):
                        # 월별 선택
                        months = sorted([m for m in premium_data[product].keys() if isinstance(premium_data[product].get(m), dict)], reverse=True)
                        
                        if months:
                            selected_month = st.selectbox(f"{product} 월 선택", months, key=f"prem_{product}_month")
                            
                            if selected_month in premium_data[product]:
                                month_data = premium_data[product][selected_month]
                                
                                # 테이블 생성
                                st.markdown(f"### {selected_month} {product} 실적")
                                
                                html = f"""
                                <style>
                                    .prem-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
                                    .prem-table th, .prem-table td {{ border: 1px solid #d0d0d0; padding: 8px 6px; text-align: center; height: 26px; }}
                                    .prem-header {{ background: #9966cc; color: white; font-weight: 600; }}
                                    .prem-total {{ background: #fff2cc; font-weight: 600; border-top: 2px solid #333; }}
                                    .prem-data {{ background: #f9f9f9; }}
                                    .prem-data:nth-child(even) {{ background: #ffffff; }}
                                    .prem-agency {{ text-align: left; font-weight: 500; padding-left: 8px; }}
                                    .prem-number {{ text-align: right; padding-right: 4px; font-family: 'Courier New', monospace; }}
                                </style>
                                <table class="prem-table">
                                    <thead>
                                        <tr>
                                            <th class="prem-header">거래선</th>
                                            <th class="prem-header">매출(백만)</th>
                                            <th class="prem-header">판매량</th>
                                            <th class="prem-header">전월비</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                """
                                
                                # 합계 행
                                if '합계' in month_data:
                                    total = month_data['합계']
                                    html += f"""
                                        <tr class="prem-total">
                                            <td class="prem-agency">합계</td>
                                            <td class="prem-number">{total.get('매출', 0):,.1f}</td>
                                            <td class="prem-number">{total.get('판매량', 0):,}</td>
                                            <td class="prem-number">{total.get('전월비', '0'):}</td>
                                        </tr>
                                    """
                                
                                # 거래선별 행
                                for agency in AGENCIES:
                                    if agency in month_data and agency != '합계':
                                        data = month_data[agency]
                                        html += f"""
                                            <tr class="prem-data">
                                                <td class="prem-agency">{agency}</td>
                                                <td class="prem-number">{data.get('매출', 0):,.1f}</td>
                                                <td class="prem-number">{data.get('판매량', 0):,}</td>
                                                <td class="prem-number">{data.get('전월비', '0'):}</td>
                                            </tr>
                                        """
                                
                                html += """
                                    </tbody>
                                </table>
                                """
                                st.markdown(html, unsafe_allow_html=True)
        else:
            st.warning("프리미엄 데이터가 없습니다")
    
    # 거래선 현황
    elif current_page == "거래선현황":
        st.subheader("📋 거래선 현황")
        
        # weekly_data.json 로드
        weekly_data_list = []
        if os.path.exists("weekly_data.json"):
            try:
                with open("weekly_data.json", "r", encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    weekly_data_list = loaded_data if isinstance(loaded_data, list) else []
            except:
                weekly_data_list = []
        
        # 거래선별 데이터 필터링
        selected_agency = st.selectbox("거래선 선택", AGENCIES, key="view_agency")
        
        # 선택한 거래선의 데이터만 필터링
        agency_data = [item for item in weekly_data_list if item.get("거래선") == selected_agency]
        
        if agency_data:
            # 주차명 정렬 함수 (숫자만 추출해서 정렬)
            def get_week_num(week_str):
                num_str = ''.join(c for c in week_str if c.isdigit())
                return int(num_str) if num_str else 0
            
            # 최신 주차순으로 정렬
            agency_data_sorted = sorted(agency_data, key=lambda x: (get_week_num(x.get("주차", "W00")), x.get("월", "")), reverse=True)
            
            st.write(f"**총 {len(agency_data_sorted)}개 주차 데이터**")
            st.write("")
            
            # 순회용 인덱스
            for idx, data in enumerate(agency_data_sorted):
                week_raw = data.get("주차", "")
                month = data.get("월", "")
                
                # 주차명 정리: 숫자만 추출 후 W + 숫자로 표시
                week_num = ''.join(c for c in week_raw if c.isdigit())
                week_clean = f"W{week_num}" if week_num else week_raw
                
                week_display = f"**{week_clean}** ({month})"
                unique_key = f"{selected_agency}_{week_clean}_{month}_{idx}"
                
                with st.expander(week_display, expanded=False):
                    # 1. 네이버 스마트 스토어
                    st.subheader("1️⃣ 네이버 스마트 스토어")
                    ss = data.get("네이버스마트스토어", {})
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("신규 관심고객", f"{ss.get('신규관심고객수', 0):,}")
                    with col2:
                        st.metric("신규구매 구매자", f"{ss.get('신규구매구매자수', 0):,}")
                    with col3:
                        st.metric("재구매 구매자", f"{ss.get('재구매구매자수', 0):,}")
                    
                    if ss.get("마케팅활동"):
                        st.info(f"📌 **마케팅활동**: {ss.get('마케팅활동')}")
                    
                    st.divider()
                    
                    # 2. 어필리에이트
                    st.subheader("2️⃣ 어필리에이트")
                    
                    sc = data.get("쇼핑커넥트", {})
                    col_sc1, col_sc2 = st.columns(2)
                    with col_sc1:
                        st.write("🔹 **쇼핑커넥트**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("크리에이터", f"{sc.get('크리에이터운영수', 0)}")
                            st.metric("모델", f"{sc.get('운영모델수', 0)}")
                        with col2:
                            st.metric("유입수", f"{sc.get('유입수', 0):,}")
                            st.metric("주문", f"{sc.get('상품주문건수', 0)}")
                        st.metric("금액(백만)", f"{sc.get('주문금액', 0):.1f}")
                        if sc.get("마케팅활동"):
                            st.caption(f"📌 {sc.get('마케팅활동')}")
                    
                    cj = data.get("공동구매", {})
                    with col_sc2:
                        st.write("🔹 **공동구매**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("크리에이터", f"{cj.get('크리에이터운영수', 0)}")
                            st.metric("모델", f"{cj.get('운영모델수', 0)}")
                        with col2:
                            st.metric("주문", f"{cj.get('상품주문건수', 0)}")
                        st.metric("금액(백만)", f"{cj.get('주문금액', 0):.1f}")
                        if cj.get("마케팅활동"):
                            st.caption(f"📌 {cj.get('마케팅활동')}")
                    
                    st.divider()
                    
                    # 3. AI 라이브
                    st.subheader("🎥 3️⃣ AI 라이브")
                    live = data.get("AI라이브", {})
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("방송횟수", f"{live.get('방송횟수', 0)}")
                    with col2:
                        st.metric("방송매출(백만)", f"{live.get('방송매출', 0):.1f}")
                    with col3:
                        st.metric("소요비용(백만)", f"{live.get('소요비용', 0):.2f}")
                    
                    if live.get("마케팅활동"):
                        st.info(f"📌 **마케팅활동**: {live.get('마케팅활동')}")
                    
                    st.divider()
                    
                    # 4. 당주 주요활동
                    st.subheader("🎯 당주 주요활동")
                    activity = data.get("당주주요활동", {})
                    
                    activity_items = [
                        ("📌 AI 라이브 효율 증대", "AI라이브효율증대"),
                        ("📌 어필리에이트 내재화", "어필리에이트내재화"),
                        ("📌 구독활성화", "구독활성화"),
                        ("📌 기타 신규 프로젝트", "기타신규프로젝트")
                    ]
                    
                    for label, key in activity_items:
                        if activity.get(key):
                            with st.expander(label, key=f"act_{key}_{unique_key}"):
                                st.write(activity.get(key))
                            st.write("")  # spacing
                    
                    st.divider()
                    st.subheader("⚙️ 데이터 관리")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("✏️ 수정", key=f"edit_{unique_key}", use_container_width=True):
                            st.session_state.edit_data = data
                            st.session_state.edit_index = weekly_data_list.index(data)
                            st.session_state.edit_mode = True
                    
                    with col2:
                        if st.button("🗑️ 삭제", key=f"delete_{unique_key}", use_container_width=True):
                            weekly_data_list.remove(data)
                            with open("weekly_data.json", "w", encoding='utf-8') as f:
                                json.dump(weekly_data_list, f, ensure_ascii=False, indent=2)
                            st.success(f"✅ {selected_agency} - {week_clean} ({month}) 데이터 삭제됨!")
                            st.rerun()
        else:
            st.info(f"등록된 데이터가 없습니다")
    
    # 담당자 피드백
    elif current_page == "담당자피드백":
        st.subheader("💬 담당자 피드백")
        
        # weekly_data.json 로드
        weekly_data_list = []
        if os.path.exists("weekly_data.json"):
            try:
                with open("weekly_data.json", "r", encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    weekly_data_list = loaded_data if isinstance(loaded_data, list) else []
            except:
                weekly_data_list = []
        
        # feedback.json 로드
        feedback_data = {}
        if os.path.exists("feedback.json"):
            try:
                with open("feedback.json", "r", encoding='utf-8') as f:
                    feedback_data = json.load(f)
            except:
                feedback_data = {}
        
        # 거래선별 필터링
        selected_agency = st.selectbox("거래선 선택", AGENCIES, key="feedback_agency")
        
        # 선택한 거래선의 데이터만 필터링
        agency_data = [item for item in weekly_data_list if item.get("거래선") == selected_agency]
        
        if agency_data:
            # 주차명 정렬 함수
            def get_week_num(week_str):
                num_str = ''.join(c for c in week_str if c.isdigit())
                return int(num_str) if num_str else 0
            
            # 최신 주차순으로 정렬
            agency_data_sorted = sorted(agency_data, key=lambda x: (get_week_num(x.get("주차", "W00")), x.get("월", "")), reverse=True)
            
            for idx, data in enumerate(agency_data_sorted):
                week_raw = data.get("주차", "")
                month = data.get("월", "")
                
                # 주차명 정리
                week_num = ''.join(c for c in week_raw if c.isdigit())
                week_clean = f"W{week_num}" if week_num else week_raw
                week_key = f"{selected_agency}_{week_clean}_{month}_{idx}"
                
                with st.expander(f"**{week_clean}** ({month})", expanded=False):
                    # ===== 데이터 대시보드 =====
                    st.subheader("📊 입력 데이터 & 분석")
                    st.divider()
                    
                    # 1. 스마트스토어
                    st.write("**🛒 네이버 스마트 스토어**")
                    ss = data.get("네이버스마트스토어", {})
                    
                    col_ss1, col_ss2 = st.columns([2, 1])
                    with col_ss1:
                        # 테이블
                        ss_data = {
                            "항목": ["신규 관심고객", "신규구매 구매자", "재구매 구매자", "합계"],
                            "수량": [
                                ss.get('신규관심고객수', 0),
                                ss.get('신규구매구매자수', 0),
                                ss.get('재구매구매자수', 0),
                                ss.get('신규관심고객수', 0) + ss.get('신규구매구매자수', 0) + ss.get('재구매구매자수', 0)
                            ]
                        }
                        ss_df = pd.DataFrame(ss_data)
                        st.dataframe(ss_df, use_container_width=True, hide_index=True)
                    
                    with col_ss2:
                        # 파이 차트 (구매 비율)
                        if ss.get('신규구매구매자수', 0) > 0 or ss.get('재구매구매자수', 0) > 0:
                            pie_data = {
                                "유형": ["신규구매", "재구매"],
                                "수량": [ss.get('신규구매구매자수', 0), ss.get('재구매구매자수', 0)]
                            }
                            pie_df = pd.DataFrame(pie_data)
                            pie_chart = px.pie(pie_df, names="유형", values="수량", title="구매자 구성")
                            st.plotly_chart(pie_chart, use_container_width=True)
                    
                    if ss.get("마케팅활동"):
                        st.info(f"📌 활동: {ss.get('마케팅활동')}")
                    
                    st.divider()
                    
                    # 2. 어필리에이트
                    st.write("**📱 어필리에이트**")
                    sc = data.get("쇼핑커넥트", {})
                    cj = data.get("공동구매", {})
                    
                    col_af1, col_af2 = st.columns([1, 2])
                    
                    with col_af1:
                        # 테이블
                        af_data = {
                            "채널": ["쇼핑커넥트", "공동구매"],
                            "크리에이터": [sc.get('크리에이터운영수', 0), cj.get('크리에이터운영수', 0)],
                            "주문건수": [sc.get('상품주문건수', 0), cj.get('상품주문건수', 0)],
                            "금액(백만)": [f"{sc.get('주문금액', 0):.1f}", f"{cj.get('주문금액', 0):.1f}"]
                        }
                        af_df = pd.DataFrame(af_data)
                        st.dataframe(af_df, use_container_width=True, hide_index=True)
                    
                    with col_af2:
                        # 막대 차트
                        chart_data = {
                            "채널": ["쇼핑커넥트", "공동구매"],
                            "주문건수": [sc.get('상품주문건수', 0), cj.get('상품주문건수', 0)],
                            "금액(백만)": [sc.get('주문금액', 0), cj.get('주문금액', 0)]
                        }
                        chart_df = pd.DataFrame(chart_data)
                        bar_chart = px.bar(chart_df, x="채널", y=["주문건수", "금액(백만)"], barmode="group", title="쇼핑커넥트 vs 공동구매")
                        st.plotly_chart(bar_chart, use_container_width=True)
                    
                    if sc.get("마케팅활동") or cj.get("마케팅활동"):
                        st.info(f"📌 쇼핑커넥트: {sc.get('마케팅활동', '-')} | 공동구매: {cj.get('마케팅활동', '-')}")
                    
                    st.divider()
                    
                    # 3. AI 라이브
                    st.write("**🎥 AI 라이브**")
                    live = data.get("AI라이브", {})
                    
                    col_live1, col_live2 = st.columns([2, 1])
                    
                    with col_live1:
                        # 테이블
                        live_cost = live.get('소요비용', 0.1)
                        live_efficiency = live.get('방송매출', 0) / live_cost if live_cost > 0 else 0
                        
                        live_data = {
                            "항목": ["방송횟수", "방송매출(백만)", "소요비용(백만)", "효율(매출/비용)"],
                            "값": [
                                live.get('방송횟수', 0),
                                f"{live.get('방송매출', 0):.1f}",
                                f"{live_cost:.2f}",
                                f"{live_efficiency:.2f}"
                            ]
                        }
                        live_df = pd.DataFrame(live_data)
                        st.dataframe(live_df, use_container_width=True, hide_index=True)
                    
                    with col_live2:
                        if live.get('방송횟수', 0) > 0:
                            # 효율 게이지
                            efficiency_color = "🟢" if live_efficiency > 1 else "🟡" if live_efficiency > 0.5 else "🔴"
                            st.metric("효율도", f"{live_efficiency:.2f}배", delta=f"{efficiency_color} {'우수' if live_efficiency > 1 else '보통' if live_efficiency > 0.5 else '개선필요'}")
                    
                    if live.get("마케팅활동"):
                        st.info(f"📌 활동: {live.get('마케팅활동')}")
                    
                    st.divider()
                    
                    # ===== 담당자 피드백 입력 =====
                    st.subheader("📝 담당자 피드백")
                    
                    # 기존 피드백 로드
                    existing_feedback = feedback_data.get(week_key, {})
                    
                    with st.form(f"feedback_form_{week_key}"):
                        # 각 영역별 피드백
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**🛒 네이버 스마트 스토어**")
                            ss_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("네이버스마트스토어", ""),
                                height=70,
                                key=f"ss_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        with col2:
                            st.write("**📱 어필리에이트**")
                            af_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("어필리에이트", ""),
                                height=70,
                                key=f"af_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**🎥 AI 라이브**")
                            live_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("AI라이브", ""),
                                height=70,
                                key=f"live_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        with col2:
                            st.write("**🎯 당주 주요활동**")
                            activity_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("당주주요활동", ""),
                                height=70,
                                key=f"activity_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        st.write("---")
                        
                        if st.form_submit_button("💾 피드백 저장", use_container_width=True):
                            # 피드백 데이터 저장
                            feedback_data[week_key] = {
                                "거래선": selected_agency,
                                "주차": week_clean,
                                "월": month,
                                "네이버스마트스토어": ss_feedback,
                                "어필리에이트": af_feedback,
                                "AI라이브": live_feedback,
                                "당주주요활동": activity_feedback,
                                "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # feedback.json에 저장
                            with open("feedback.json", "w", encoding='utf-8') as f:
                                json.dump(feedback_data, f, ensure_ascii=False, indent=2)
                            
                            st.success("✅ 피드백이 저장되었습니다!")
                            st.rerun()
                    
                    st.write("")
        else:
            st.info(f"등록된 데이터가 없습니다")
                                label_visibility="collapsed"
                            )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**🎥 AI 라이브**")
                            live_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("AI라이브", ""),
                                height=80,
                                key=f"live_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        with col2:
                            st.write("**🎯 당주 주요활동**")
                            activity_feedback = st.text_area(
                                "피드백",
                                value=existing_feedback.get("당주주요활동", ""),
                                height=80,
                                key=f"activity_fb_{week_key}",
                                label_visibility="collapsed"
                            )
                        
                        st.write("---")
                        
                        if st.form_submit_button("💾 피드백 저장", use_container_width=True):
                            # 피드백 데이터 저장
                            feedback_data[week_key] = {
                                "거래선": selected_agency,
                                "주차": week,
                                "월": month,
                                "네이버스마트스토어": ss_feedback,
                                "어필리에이트": af_feedback,
                                "AI라이브": live_feedback,
                                "당주주요활동": activity_feedback,
                                "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # feedback.json에 저장
                            with open("feedback.json", "w", encoding='utf-8') as f:
                                json.dump(feedback_data, f, ensure_ascii=False, indent=2)
                            
                            st.success("✅ 피드백이 저장되었습니다!")
                            st.rerun()
        else:
            st.info(f"등록된 데이터가 없습니다")

# 메인
if st.session_state.user_name is None:
    login_page()
else:
    dashboard()