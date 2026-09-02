import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
from anthropic import Anthropic

st.set_page_config(page_title="거래선별 마케팅 대시보드", page_icon="📊", layout="wide")

# Anthropic 클라이언트 초기화
client = Anthropic()

# 거래선 목록
AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]

# 세션 상태
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "selected_agency" not in st.session_state:
    st.session_state.selected_agency = None

# 데이터 로드/저장
def load_weekly_data():
    """주차별 거래선 데이터 로드"""
    if os.path.exists("weekly_data.json"):
        with open("weekly_data.json", encoding='utf-8') as f:
            return json.load(f)
    return {agency: {} for agency in AGENCIES}

def save_weekly_data(data):
    """주차별 거래선 데이터 저장"""
    with open("weekly_data.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_feedback():
    """담당자 피드백 로드"""
    if os.path.exists("feedback.json"):
        with open("feedback.json", encoding='utf-8') as f:
            return json.load(f)
    return {agency: {} for agency in AGENCIES}

def save_feedback(data):
    """담당자 피드백 저장"""
    with open("feedback.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# AI 분석 함수
@st.cache_data(show_spinner=False)
def analyze_marketing_activity(text, activity_type):
    """마케팅활동 텍스트를 AI로 분석하여 요약 및 주요 내용 추출"""
    if not text or text.strip() == "":
        return {"요약": "-", "주요_내용": "-"}
    
    try:
        prompt = f"""
다음은 {activity_type} 마케팅활동에 대한 상세 기록입니다. 
이를 분석하여 요약과 주요 내용을 추출해주세요.

[마케팅활동 내용]
{text}

다음 형식으로 답변해주세요:
📌 요약: (한 문장으로 핵심 내용 요약)
📊 주요내용: (bullet point로 3-5개 항목 나열)

JSON 형식으로 반환:
{{"요약": "...", "주요_내용": "..."}}
"""
        
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # 응답 파싱
        response_text = response.content[0].text
        
        # JSON 추출
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
        
        return {"요약": response_text[:100], "주요_내용": response_text}
    
    except Exception as e:
        return {"요약": "분석 중 오류 발생", "주요_내용": str(e)}

# 로그인 페이지
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

# ============================================
# 거래선 대시보드
# ============================================
def agency_dashboard():
    agency = st.session_state.selected_agency
    
    # 헤더
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
    
    # 탭
    tab1, tab2, tab3 = st.tabs(["📝 주차별 입력", "📊 입력 현황", "💬 담당자 피드백"])
    
    # TAB 1: 주차별 입력
    with tab1:
        st.subheader("주차별 데이터 입력")
        
        with st.form("weekly_form"):
            week = st.number_input("주차 (1-52)", min_value=1, max_value=52, step=1)
            
            st.write("---")
            
            # 1. 스마트스토어 고객수
            st.subheader("1️⃣ 스마트스토어 고객수")
            col1, col2, col3 = st.columns(3)
            with col1:
                smartstore_total = st.number_input("총 고객수", min_value=0, step=1, key="ss_total")
            with col2:
                smartstore_new = st.number_input("신규 고객수", min_value=0, step=1, key="ss_new")
            with col3:
                smartstore_repeat = st.number_input("재구매 고객수", min_value=0, step=1, key="ss_repeat")
            
            st.write("---")
            
            # 2. 어필리에이트 현황
            st.subheader("2️⃣ 어필리에이트 현황")
            col1, col2 = st.columns(2)
            with col1:
                affiliate_sales = st.number_input("판매액 (원)", min_value=0, step=100000, key="aff_sales")
            with col2:
                affiliate_visits = st.number_input("방문수", min_value=0, step=1, key="aff_visits")
            affiliate_notes = st.text_area("특이사항", height=80, key="aff_notes")
            
            st.write("---")
            
            # 3. AI 라이브커머스 현황
            st.subheader("3️⃣ AI 라이브커머스 현황")
            col1, col2 = st.columns(2)
            with col1:
                livecommerce_count = st.number_input("방송 횟수", min_value=0, step=1, key="live_count")
            with col2:
                livecommerce_sales = st.number_input("판매액 (원)", min_value=0, step=100000, key="live_sales")
            livecommerce_notes = st.text_area("특이사항", height=80, key="live_notes")
            
            st.write("---")
            
            # 4. 마케팅활동
            st.subheader("4️⃣ 마케팅활동")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write("**□ 어플리에이트**")
                affiliate_activity = st.text_area(
                    "어플리에이트 활동",
                    height=100,
                    placeholder="예: 김치냉장고 3도어 단품 및 키친핏 패키지 컨텐츠 발행...",
                    key="aff_activity"
                )
            
            with col2:
                st.write("**□ 네이버**")
                naver_activity = st.text_area(
                    "네이버 활동",
                    height=100,
                    placeholder="예: 멤버십데이 라이브 연계 프로모션 안내...",
                    key="naver_activity"
                )
            
            with col3:
                st.write("**□ 광고운영**")
                ad_activity = st.text_area(
                    "광고운영 활동",
                    height=100,
                    placeholder="예: SA/DA 광고 전환 효율 최적화...",
                    key="ad_activity"
                )
            
            st.write("---")
            
            if st.form_submit_button("💾 저장", use_container_width=True):
                with st.spinner("데이터 분석 중..."):
                    if agency not in weekly_data:
                        weekly_data[agency] = {}
                    
                    # AI 분석 수행
                    aff_analysis = analyze_marketing_activity(affiliate_activity, "어플리에이트")
                    nav_analysis = analyze_marketing_activity(naver_activity, "네이버")
                    ad_analysis = analyze_marketing_activity(ad_activity, "광고운영")
                    
                    weekly_data[agency][str(week)] = {
                        "등록일": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "스마트스토어": {
                            "총고객수": smartstore_total,
                            "신규고객": smartstore_new,
                            "재구매": smartstore_repeat
                        },
                        "어필리에이트": {
                            "판매액": affiliate_sales,
                            "방문수": affiliate_visits,
                            "특이사항": affiliate_notes
                        },
                        "라이브커머스": {
                            "방송횟수": livecommerce_count,
                            "판매액": livecommerce_sales,
                            "특이사항": livecommerce_notes
                        },
                        "마케팅활동": {
                            "어플리에이트": {
                                "원문": affiliate_activity,
                                "분석": aff_analysis
                            },
                            "네이버": {
                                "원문": naver_activity,
                                "분석": nav_analysis
                            },
                            "광고운영": {
                                "원문": ad_activity,
                                "분석": ad_analysis
                            }
                        }
                    }
                    
                    save_weekly_data(weekly_data)
                    st.success(f"✅ {week}주차 데이터가 저장되었습니다!")
    
    # TAB 2: 입력 현황
    with tab2:
        st.subheader("📊 입력 현황")
        
        if agency in weekly_data and weekly_data[agency]:
            for week in sorted(weekly_data[agency].keys(), key=lambda x: int(x), reverse=True):
                data = weekly_data[agency][week]
                
                with st.expander(f"**{week}주차** ({data.get('등록일', '-')})", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    # 스마트스토어
                    with col1:
                        st.subheader("🛒 스마트스토어")
                        ss = data.get('스마트스토어', {})
                        st.metric("총 고객수", f"{ss.get('총고객수', 0):,}")
                        st.metric("신규 고객", f"{ss.get('신규고객', 0):,}")
                        st.metric("재구매", f"{ss.get('재구매', 0):,}")
                    
                    # 어필리에이트
                    with col2:
                        st.subheader("📱 어필리에이트")
                        af = data.get('어필리에이트', {})
                        st.metric("판매액", f"{af.get('판매액', 0):,}")
                        st.metric("방문수", f"{af.get('방문수', 0):,}")
                        if af.get('특이사항'):
                            st.info(f"💬 {af.get('특이사항')}")
                    
                    # 라이브커머스
                    with col3:
                        st.subheader("📹 라이브커머스")
                        lc = data.get('라이브커머스', {})
                        st.metric("방송 횟수", f"{lc.get('방송횟수', 0)}")
                        st.metric("판매액", f"{lc.get('판매액', 0):,}")
                        if lc.get('특이사항'):
                            st.info(f"💬 {lc.get('특이사항')}")
                    
                    # 마케팅활동
                    st.write("---")
                    st.subheader("📢 마케팅활동")
                    
                    ma = data.get('마케팅활동', {})
                    
                    if ma.get('어플리에이트'):
                        with st.expander("□ 어플리에이트"):
                            st.write(ma.get('어플리에이트').get('원문', '-'))
                    
                    if ma.get('네이버'):
                        with st.expander("□ 네이버"):
                            st.write(ma.get('네이버').get('원문', '-'))
                    
                    if ma.get('광고운영'):
                        with st.expander("□ 광고운영"):
                            st.write(ma.get('광고운영').get('원문', '-'))
        else:
            st.info("등록된 데이터가 없습니다")
    
    # TAB 3: 담당자 피드백
    with tab3:
        st.subheader("💬 담당자 피드백")
        
        if agency in feedback_data and feedback_data[agency]:
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

# ============================================
# 담당자 대시보드
# ============================================
def manager_dashboard():
    st.title("👔 담당자 피드백 관리")
    
    col1, col2 = st.columns([0.9, 0.1])
    with col2:
        if st.button("←로그아웃"):
            st.session_state.user_role = None
            st.rerun()
    
    st.divider()
    
    # 거래선 선택
    selected_agency = st.selectbox("거래선 선택", AGENCIES, key="manager_select")
    
    st.divider()
    
    weekly_data = load_weekly_data()
    feedback_data = load_feedback()
    
    # 거래선의 데이터 표시
    st.subheader(f"📋 {selected_agency} 주차별 데이터")
    
    if selected_agency in weekly_data and weekly_data[selected_agency]:
        # 최근 5개 주차 표시
        recent_weeks = sorted(
            weekly_data[selected_agency].items(),
            key=lambda x: int(x[0]),
            reverse=True
        )[:5]
        
        for week, data in recent_weeks:
            st.write(f"### {week}주차")
            
            col1, col2, col3 = st.columns(3)
            
            # 스마트스토어
            with col1:
                st.subheader("🛒 스마트스토어")
                ss = data.get('스마트스토어', {})
                st.metric("총 고객수", f"{ss.get('총고객수', 0):,}")
                st.metric("신규 고객", f"{ss.get('신규고객', 0):,}")
                st.metric("재구매", f"{ss.get('재구매', 0):,}")
            
            # 어필리에이트
            with col2:
                st.subheader("📱 어필리에이트")
                af = data.get('어필리에이트', {})
                st.metric("판매액", f"{af.get('판매액', 0):,}")
                st.metric("방문수", f"{af.get('방문수', 0):,}")
                if af.get('특이사항'):
                    st.info(f"💬 {af.get('특이사항')}")
            
            # 라이브커머스
            with col3:
                st.subheader("📹 라이브커머스")
                lc = data.get('라이브커머스', {})
                st.metric("방송 횟수", f"{lc.get('방송횟수', 0)}")
                st.metric("판매액", f"{lc.get('판매액', 0):,}")
                if lc.get('특이사항'):
                    st.info(f"💬 {lc.get('특이사항')}")
            
            # 마케팅활동 - AI 요약본 표시
            st.write("---")
            st.subheader("📢 마케팅활동")
            
            ma = data.get('마케팅활동', {})
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if ma.get('어플리에이트'):
                    analysis = ma['어플리에이트'].get('분석', {})
                    st.write("**□ 어플리에이트**")
                    st.info(f"📌 {analysis.get('요약', '-')}")
                    with st.expander("📄 상세 내용"):
                        st.write(ma['어플리에이트'].get('원문', '-'))
            
            with col2:
                if ma.get('네이버'):
                    analysis = ma['네이버'].get('분석', {})
                    st.write("**□ 네이버**")
                    st.info(f"📌 {analysis.get('요약', '-')}")
                    with st.expander("📄 상세 내용"):
                        st.write(ma['네이버'].get('원문', '-'))
            
            with col3:
                if ma.get('광고운영'):
                    analysis = ma['광고운영'].get('분석', {})
                    st.write("**□ 광고운영**")
                    st.info(f"📌 {analysis.get('요약', '-')}")
                    with st.expander("📄 상세 내용"):
                        st.write(ma['광고운영'].get('원문', '-'))
            
            # 피드백 작성 폼
            st.write("---")
            
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                feedback_type = st.radio(
                    "평가",
                    ["✅ 칭찬", "⚠️ 확인요청"],
                    horizontal=True,
                    key=f"type_{selected_agency}_{week}"
                )