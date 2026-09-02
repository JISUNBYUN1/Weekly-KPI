import streamlit as st
import json
from datetime import datetime
import os

st.set_page_config(page_title="거래선별 마케팅 대시보드", page_icon="📊", layout="wide")

# 거래선 목록
AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]

# 세션 상태
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "selected_agency" not in st.session_state:
    st.session_state.selected_agency = None

# 데이터 함수
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
def login():
    st.title("📊 거래선별 마케팅 대시보드")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 거래선 로그인")
        agency = st.selectbox("거래선 선택", AGENCIES)
        if st.button("입장", key="agency_btn", use_container_width=True):
            st.session_state.user_role = "agency"
            st.session_state.selected_agency = agency
            st.rerun()
    
    with col2:
        st.subheader("👔 담당자 로그인")
        if st.button("담당자 입장", key="manager_btn", use_container_width=True):
            st.session_state.user_role = "manager"
            st.rerun()

# 거래선 대시보드
def agency_dashboard():
    agency = st.session_state.selected_agency
    
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.title(f"📍 {agency}")
    with col2:
        if st.button("←로그아웃"):
            st.session_state.user_role = None
            st.session_state.selected_agency = None
            st.rerun()
    
    st.divider()
    
    weekly_data = load_weekly_data()
    feedback_data = load_feedback()
    
    tab1, tab2, tab3 = st.tabs(["📝 주차별 입력", "📊 입력 현황", "💬 담당자 피드백"])
    
    # TAB 1
    with tab1:
        st.subheader("주차별 데이터 입력")
        
        with st.form("weekly_form"):
            week = st.number_input("주차 (1-52)", min_value=1, max_value=52, step=1)
            
            st.write("---")
            st.subheader("1️⃣ 스마트스토어 고객수")
            col1, col2, col3 = st.columns(3)
            with col1:
                ss_total = st.number_input("총 고객수", min_value=0, step=1, key="ss_total")
            with col2:
                ss_new = st.number_input("신규 고객수", min_value=0, step=1, key="ss_new")
            with col3:
                ss_repeat = st.number_input("재구매 고객수", min_value=0, step=1, key="ss_repeat")
            
            st.write("---")
            st.subheader("2️⃣ 어필리에이트 현황")
            col1, col2 = st.columns(2)
            with col1:
                af_sales = st.number_input("판매액 (원)", min_value=0, step=100000, key="af_sales")
            with col2:
                af_visits = st.number_input("방문수", min_value=0, step=1, key="af_visits")
            af_notes = st.text_area("특이사항", height=80, key="af_notes")
            
            st.write("---")
            st.subheader("3️⃣ AI 라이브커머스 현황")
            col1, col2 = st.columns(2)
            with col1:
                live_count = st.number_input("방송 횟수", min_value=0, step=1, key="live_count")
            with col2:
                live_sales = st.number_input("판매액 (원)", min_value=0, step=100000, key="live_sales")
            live_notes = st.text_area("특이사항", height=80, key="live_notes")
            
            st.write("---")
            st.subheader("4️⃣ 마케팅활동")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write("**□ 어플리에이트**")
                aff_activity = st.text_area("어플리에이트 활동", height=100, key="aff_activity")
            with col2:
                st.write("**□ 네이버**")
                nav_activity = st.text_area("네이버 활동", height=100, key="nav_activity")
            with col3:
                st.write("**□ 광고운영**")
                ad_activity = st.text_area("광고운영 활동", height=100, key="ad_activity")
            
            st.write("---")
            
            if st.form_submit_button("💾 저장", use_container_width=True):
                if agency not in weekly_data:
                    weekly_data[agency] = {}
                
                weekly_data[agency][str(week)] = {
                    "등록일": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "스마트스토어": {"총고객수": ss_total, "신규고객": ss_new, "재구매": ss_repeat},
                    "어필리에이트": {"판매액": af_sales, "방문수": af_visits, "특이사항": af_notes},
                    "라이브커머스": {"방송횟수": live_count, "판매액": live_sales, "특이사항": live_notes},
                    "마케팅활동": {"어플리에이트": aff_activity, "네이버": nav_activity, "광고운영": ad_activity}
                }
                
                save_weekly_data(weekly_data)
                st.success(f"✅ {week}주차 데이터가 저장되었습니다!")
    
    # TAB 2
    with tab2:
        st.subheader("📊 입력 현황")
        
        if agency in weekly_data:
            for week in sorted(weekly_data[agency].keys(), key=lambda x: int(x), reverse=True):
                data = weekly_data[agency][week]
                
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
                        if af.get('특이사항'):
                            st.info(f"💬 {af.get('특이사항')}")
                    
                    with col3:
                        st.subheader("📹 라이브커머스")
                        lc = data.get('라이브커머스', {})
                        st.metric("방송 횟수", f"{lc.get('방송횟수', 0)}")
                        st.metric("판매액", f"{lc.get('판매액', 0):,}")
                        if lc.get('특이사항'):
                            st.info(f"💬 {lc.get('특이사항')}")
                    
                    st.write("---")
                    st.subheader("📢 마케팅활동")
                    ma = data.get('마케팅활동', {})
                    
                    if ma.get('어플리에이트'):
                        with st.expander("□ 어플리에이트"):
                            st.write(ma.get('어플리에이트', '-'))
                    if ma.get('네이버'):
                        with st.expander("□ 네이버"):
                            st.write(ma.get('네이버', '-'))
                    if ma.get('광고운영'):
                        with st.expander("□ 광고운영"):
                            st.write(ma.get('광고운영', '-'))
        else:
            st.info("등록된 데이터가 없습니다")
    
    # TAB 3
    with tab3:
        st.subheader("💬 담당자 피드백")
        
        if agency in feedback_data:
            for week in sorted(feedback_data[agency].keys(), key=lambda x: int(x), reverse=True):
                fb = feedback_data[agency][week]
                
                with st.container(border=True):
                    if fb.get('type') == 'praise':
                        st.success(f"✅ **{week}주차 피드백**")
                        st.write(f"👍 {fb.get('comment', '-')}")
                    else:
                        st.warning(f"⚠️ **{week}주차 확인요청**")
                        st.write(f"🔍 {fb.get('comment', '-')}")
                    st.caption(f"작성일: {fb.get('date', '-')}")
        else:
            st.info("담당자 피드백이 없습니다")

# 담당자 대시보드
def manager_dashboard():
    st.title("👔 담당자 피드백 관리")
    
    col1, col2 = st.columns([0.9, 0.1])
    with col2:
        if st.button("←로그아웃"):
            st.session_state.user_role = None
            st.rerun()
    
    st.divider()
    
    selected_agency = st.selectbox("거래선 선택", AGENCIES, key="manager_select")
    st.divider()
    
    weekly_data = load_weekly_data()
    feedback_data = load_feedback()
    
    st.subheader(f"📋 {selected_agency} 주차별 데이터")
    
    if selected_agency in weekly_data:
        recent_weeks = sorted(weekly_data[selected_agency].items(), key=lambda x: int(x[0]), reverse=True)[:5]
        
        for week, data in recent_weeks:
            st.write(f"### {week}주차")
            
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
                if af.get('특이사항'):
                    st.info(f"💬 {af.get('특이사항')}")
            
            with col3:
                st.subheader("📹 라이브커머스")
                lc = data.get('라이브커머스', {})
                st.metric("방송 횟수", f"{lc.get('방송횟수', 0)}")
                st.metric("판매액", f"{lc.get('판매액', 0):,}")
                if lc.get('특이사항'):
                    st.info(f"💬 {lc.get('특이사항')}")
            
            st.write("---")
            st.subheader("📢 마케팅활동")
            
            ma = data.get('마케팅활동', {})
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if ma.get('어플리에이트'):
                    st.write("**□ 어플리에이트**")
                    with st.expander("📄 내용 보기"):
                        st.write(ma.get('어플리에이트', '-'))
            with col2:
                if ma.get('네이버'):
                    st.write("**□ 네이버**")
                    with st.expander("📄 내용 보기"):
                        st.write(ma.get('네이버', '-'))
            with col3:
                if ma.get('광고운영'):
                    st.write("**□ 광고운영**")
                    with st.expander("📄 내용 보기"):
                        st.write(ma.get('광고운영', '-'))
            
            st.write("---")
            
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                feedback_type = st.radio("평가", ["✅ 칭찬", "⚠️ 확인요청"], horizontal=True, key=f"type_{selected_agency}_{week}")
            
            comment = st.text_area("담당자 의견", placeholder="이번 주 성과에 대한 의견을 작성하세요", height=100, key=f"comment_{selected_agency}_{week}")
            
            if st.button("💾 피드백 저장", key=f"save_{selected_agency}_{week}", use_container_width=True):
                if selected_agency not in feedback_data:
                    feedback_data[selected_agency] = {}
                
                feedback_data[selected_agency][week] = {
                    "type": "praise" if "칭찬" in feedback_type else "request",
                    "comment": comment,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                save_feedback(feedback_data)
                st.success("✅ 피드백이 저장되었습니다!")
            
            st.divider()
    else:
        st.info(f"{selected_agency}에 입력된 데이터가 없습니다")
    
    st.subheader(f"📝 {selected_agency} 피드백 이력")
    
    if selected_agency in feedback_data:
        for week in sorted(feedback_data[selected_agency].keys(), key=lambda x: int(x), reverse=True):
            fb = feedback_data[selected_agency][week]
            
            with st.container(border=True):
                if fb.get('type') == 'praise':
                    st.success(f"**{week}주차** ✅ 칭찬")
                else:
                    st.warning(f"**{week}주차** ⚠️ 확인요청")
                st.write(f"{fb.get('comment', '-')}")
                st.caption(f"작성일: {fb.get('date', '-')}")
    else:
        st.info("피드백 이력이 없습니다")

# 메인
if st.session_state.user_role is None:
    login()
elif st.session_state.user_role == "agency":
    agency_dashboard()
elif st.session_state.user_role == "manager":
    manager_dashboard()