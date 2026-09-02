import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

st.set_page_config(page_title="PP3G 통합 대시보드", page_icon="📊", layout="wide")

# 거래선 목록
AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]
PRODUCT_ORDER = ["냉장고", "김치냉장고", "의류케어", "조리기기", "정수기"]

# 세션 상태
if "user_name" not in st.session_state:
    st.session_state.user_name = None

# 데이터 로드
@st.cache_data
def load_sales_data():
    """KPI 데이터 로드"""
    data = {}
    
    # bizplan 로드
    bizplan = {}
    for f in ['bizplan_SOP.json', 'bizplan_쿠팡.json', 'bizplan_종합몰.json', 'bizplan_홈쇼핑.json']:
        try:
            with open(f, encoding='utf-8') as file:
                bizplan.update(json.load(file))
        except:
            pass
    data['bizplan'] = bizplan
    
    # premium 로드
    premium = {}
    for f in ['premium_냉장고.json', 'premium_세탁기.json', 'premium_식기세척기.json', 'premium_정수기.json']:
        try:
            with open(f, encoding='utf-8') as file:
                premium.update(json.load(file))
        except:
            pass
    data['premium'] = premium
    
    # 기타 데이터
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

# 마케팅 데이터
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

# 통합 대시보드
def dashboard():
    user_name = st.session_state.user_name
    
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.title(f"📊 PP3G 통합 대시보드")
        st.caption(f"사용자: {user_name}")
    with col2:
        if st.button("←로그아웃"):
            st.session_state.user_name = None
            st.rerun()
    
    st.divider()
    
    # 데이터 로드
    sales_data = load_sales_data()
    weekly_data = load_weekly_data()
    feedback_data = load_feedback()
    
    # 탭 구성
    tabs = st.tabs([
        "📊 전체", 
        "📈 FCST", 
        "💎 프리미엄",
        "🛒 스마트", 
        "📹 라이브", 
        "🤝 어필",
        "📦 PPM",
        "✏️ 거래선입력",
        "📋 거래선현황",
        "💬 담당자피드백"
    ])
    
    # TAB 1: 전체
    with tabs[0]:
        st.subheader("📊 전체 현황")
        
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
            
            rows = []
            grand_total_sales = sum(sum(p.get("SALES", {}).values()) for p in all_products.values())
            grand_total_annual = sum(sum(p.get("ANNUAL", {}).values()) for p in all_products.values())
            
            rows.append({
                "제품": "그룹 계",
                "실적(수량)": f"{grand_total_sales:,.0f}",
                "경영비(%)": f"{(grand_total_sales/grand_total_annual):.2f}%" if grand_total_annual > 0 else "-"
            })
            
            for product_name in PRODUCT_ORDER:
                if product_name in all_products:
                    product_data = all_products[product_name]
                    sales_total = sum(product_data.get("SALES", {}).values())
                    annual_total = sum(product_data.get("ANNUAL", {}).values())
                    
                    rows.append({
                        "제품": product_name,
                        "실적(수량)": f"{sales_total:,.0f}",
                        "경영비(%)": f"{(sales_total/annual_total):.2f}%" if annual_total > 0 else "-"
                    })
            
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    
    # TAB 2: FCST
    with tabs[1]:
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
                           key=lambda x: int(x.replace("월", "")) if "월" in x else 0)
            
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
    
    # TAB 3: 프리미엄
    with tabs[2]:
        st.subheader("💎 프리미엄 비중")
        
        if sales_data['premium']:
            premium_data = sales_data['premium']
            selected_product = st.selectbox("제품", list(premium_data.keys()), key="premium_product")
            
            if selected_product in premium_data:
                st.write(f"**{selected_product}** 프리미엄 비중")
                st.info("프리미엄 데이터 표시 준비 중")
    
    # TAB 4: 스마트스토어
    with tabs[3]:
        st.subheader("🛒 스마트스토어")
        
        if sales_data['smartstore'] and '월별' in sales_data['smartstore']:
            months = list(sales_data['smartstore']['월별'].keys())
            selected_month = st.selectbox("월", months, key="ss_month")
            
            st.dataframe(pd.DataFrame([
                {"대리점": k, **v} 
                for k, v in sales_data['smartstore']['월별'][selected_month].items() 
                if isinstance(v, dict)
            ]), use_container_width=True, hide_index=True)
    
    # TAB 5: 라이브
    with tabs[4]:
        st.subheader("📹 라이브커머스")
        
        if sales_data['live_commerce'] and '월별' in sales_data['live_commerce']:
            months = list(sales_data['live_commerce']['월별'].keys())
            selected_month = st.selectbox("월", months, key="live_month")
            
            st.dataframe(pd.DataFrame([
                {"대리점": k, **v} 
                for k, v in sales_data['live_commerce']['월별'][selected_month].items() 
                if isinstance(v, dict)
            ]), use_container_width=True, hide_index=True)
    
    # TAB 6: 어필
    with tabs[5]:
        st.subheader("🤝 어필리에이트")
        
        if sales_data['affiliate']:
            months = list(sales_data['affiliate'].keys())
            selected_month = st.selectbox("월", months, key="aff_month")
            
            if selected_month in sales_data['affiliate']:
                channels = list(sales_data['affiliate'][selected_month].keys())
                selected_channel = st.selectbox("채널", channels, key="aff_channel")
                
                st.dataframe(pd.DataFrame([
                    {"대리점": k, **v} 
                    for k, v in sales_data['affiliate'][selected_month][selected_channel].items() 
                    if isinstance(v, dict)
                ]), use_container_width=True, hide_index=True)
    
    # TAB 7: PPM
    with tabs[6]:
        st.subheader("📦 쿠팡 PPM")
        
        if sales_data['coupang_ppm']:
            weeks = list(sales_data['coupang_ppm'].keys())
            selected_week = st.selectbox("주차", weeks, key="ppm_week")
            
            if selected_week in sales_data['coupang_ppm']:
                for product, models in sales_data['coupang_ppm'][selected_week].items():
                    st.write(f"**{product}**")
                    if isinstance(models, list) and models and isinstance(models[0], dict):
                        st.dataframe(pd.DataFrame(models), use_container_width=True, hide_index=True)
    
    # TAB 8: 거래선 입력
    with tabs[7]:
        st.subheader("✏️ 거래선 주차별 입력")
        
        with st.form("weekly_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                agency = st.selectbox("거래선", AGENCIES, key="input_agency")
            with col2:
                week = st.number_input("주차", min_value=1, max_value=52, step=1, key="input_week")
            with col3:
                pass
            
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
                st.write("**□ 어플리에이트**")
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
                    "등록일": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "스마트스토어": {"총고객수": ss_total, "신규고객": ss_new, "재구매": ss_repeat},
                    "어필리에이트": {"판매액": af_sales, "방문수": af_visits, "특이사항": af_notes},
                    "라이브커머스": {"방송횟수": live_count, "판매액": live_sales, "특이사항": live_notes},
                    "마케팅활동": {"어플리에이트": aff_activity, "네이버": nav_activity, "광고운영": ad_activity}
                }
                save_weekly_data(weekly_data)
                st.success(f"✅ {agency} {week}주차 저장됨!")
    
    # TAB 9: 거래선 현황
    with tabs[8]:
        st.subheader("📋 거래선 현황")
        
        selected_agency = st.selectbox("거래선 선택", AGENCIES, key="view_agency")
        
        if selected_agency in weekly_data:
            for week in sorted(weekly_data[selected_agency].keys(), key=lambda x: int(x), reverse=True):
                data = weekly_data[selected_agency][week]
                
                with st.expander(f"**{week}주차** ({data.get('등록일', '-')})"):
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
                    
                    if ma.get('어플리에이트'):
                        with st.expander("□ 어플리에이트"):
                            st.write(ma.get('어플리에이트'))
                    if ma.get('네이버'):
                        with st.expander("□ 네이버"):
                            st.write(ma.get('네이버'))
                    if ma.get('광고운영'):
                        with st.expander("□ 광고운영"):
                            st.write(ma.get('광고운영'))
        else:
            st.info("등록된 데이터가 없습니다")
    
    # TAB 10: 담당자 피드백
    with tabs[9]:
        st.subheader("💬 담당자 피드백")
        
        feedback_agency = st.selectbox("거래선 선택", AGENCIES, key="feedback_agency")
        
        if feedback_agency in weekly_data:
            recent_weeks = sorted(weekly_data[feedback_agency].items(), key=lambda x: int(x[0]), reverse=True)[:5]
            
            for week, data in recent_weeks:
                st.write(f"### {week}주차")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("스마트스토어", f"{data.get('스마트스토어', {}).get('총고객수', 0):,}")
                with col2:
                    st.metric("어필리에이트", f"{data.get('어필리에이트', {}).get('판매액', 0):,}")
                with col3:
                    st.metric("라이브", f"{data.get('라이브커머스', {}).get('방송횟수', 0)}")
                
                st.write("---")
                
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    feedback_type = st.radio("평가", ["✅ 칭찬", "⚠️ 확인요청"], horizontal=True, key=f"fb_type_{feedback_agency}_{week}")
                
                comment = st.text_area("의견", height=80, key=f"fb_comment_{feedback_agency}_{week}")
                
                if st.button("💾 저장", key=f"fb_save_{feedback_agency}_{week}", use_container_width=True):
                    if feedback_agency not in feedback_data:
                        feedback_data[feedback_agency] = {}
                    
                    feedback_data[feedback_agency][week] = {
                        "type": "praise" if "칭찬" in feedback_type else "request",
                        "comment": comment,
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