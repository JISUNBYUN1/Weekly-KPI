# ========================================
# 거래선 주차별 입력 (수정된 전체 코드)
# ========================================

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
        """해당 월의 주차 리스트 반환"""
        month_num = int(month.replace('월', ''))
        weeks_list = []
        
        for week, info in weeks_2026.items():
            month_info = info['month']
            if isinstance(month_info, list):
                if month_num in month_info:
                    weeks_list.append(week)
            elif month_info == month_num:
                weeks_list.append(week)
        
        return sorted(weeks_list)
    
    with st.form("weekly_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            input_agency = st.selectbox("거래선 선택", AGENCIES, key="input_agency")
        
        with col2:
            input_month = st.selectbox("월 선택", ["7월", "8월"], key="input_month")
        
        with col3:
            # 선택된 월의 주차 리스트
            available_weeks = get_weeks_by_month(input_month)
            if available_weeks:
                input_week = st.selectbox("주차 선택", available_weeks, key="input_week")
            else:
                st.warning(f"{input_month}에 데이터가 없습니다")
                input_week = None
        
        st.write("---")
        
        if input_week:
            # 선택된 주차 정보 표시
            week_info = weeks_2026.get(input_week, {})
            st.caption(f"📅 {input_week}: {week_info.get('start', '')} ~ {week_info.get('end', '')}")
        
        st.subheader("1️⃣ 스마트스토어")
        col1, col2, col3 = st.columns(3)
        with col1:
            ss_total = st.number_input("총 고객수", min_value=0, step=1, key="ss_total_input")
        with col2:
            ss_new = st.number_input("신규 고객수", min_value=0, step=1, key="ss_new_input")
        with col3:
            ss_orders = st.number_input("주문건수", min_value=0, step=1, key="ss_orders_input")
        
        ss_amount = st.number_input("판매액 (백만)", min_value=0.0, step=0.1, key="ss_amount_input")
        
        st.write("---")
        st.subheader("2️⃣ 어필리에이트")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**어필리에이트**")
            af_creator = st.number_input("크리에이터 운영수", min_value=0, step=1, key="af_creator_input")
            af_model = st.number_input("운영모델", min_value=0, step=1, key="af_model_input")
            af_orders = st.number_input("주문건수", min_value=-999, step=1, key="af_orders_input")
            af_amount = st.number_input("주문금액 (백만)", min_value=-999.0, step=0.1, key="af_amount_input")
        
        with col2:
            st.write("**쇼핑커넥트**")
            sc_creator = st.number_input("크리에이터 운영수 (SC)", min_value=0, step=1, key="sc_creator_input")
            sc_model = st.number_input("운영모델 (SC)", min_value=0, step=1, key="sc_model_input")
            sc_visits = st.number_input("유입수", min_value=0, step=1, key="sc_visits_input")
            sc_orders = st.number_input("상품주문", min_value=-999, step=1, key="sc_orders_input")
            sc_amount = st.number_input("주문금액 (백만) (SC)", min_value=-999.0, step=0.1, key="sc_amount_input")
        
        st.write("---")
        st.subheader("3️⃣ 공동구매")
        col1, col2 = st.columns(2)
        with col1:
            cj_creator = st.number_input("크리에이터 운영수 (공동)", min_value=0, step=1, key="cj_creator_input")
            cj_model = st.number_input("운영모델 (공동)", min_value=0, step=1, key="cj_model_input")
        with col2:
            cj_orders = st.number_input("상품주문 (공동)", min_value=0, step=1, key="cj_orders_input")
            cj_amount = st.number_input("주문금액 (백만) (공동)", min_value=0.0, step=0.1, key="cj_amount_input")
        
        st.write("---")
        st.subheader("4️⃣ 라이브커머스")
        col1, col2, col3 = st.columns(3)
        with col1:
            live_count = st.number_input("방송횟수", min_value=0, step=1, key="live_count_input")
        with col2:
            live_sale = st.number_input("방송매출 (백만)", min_value=0.0, step=0.1, key="live_sale_input")
        with col3:
            live_cost = st.number_input("소요비용 (백만)", min_value=0.0, step=0.1, key="live_cost_input")
        
        st.write("---")
        
        submit_button = st.form_submit_button("💾 저장", use_container_width=True)
        
        if submit_button:
            if input_week is None:
                st.error("주차를 선택해주세요")
            else:
                # 데이터 조합
                new_data = {
                    "거래선": input_agency,
                    "월": input_month,
                    "주차": input_week,
                    "스마트스토어": {
                        "총고객수": ss_total,
                        "신규고객수": ss_new,
                        "주문건수": ss_orders,
                        "판매액": ss_amount
                    },
                    "어필리에이트": {
                        "크리에이터": af_creator,
                        "운영모델": af_model,
                        "주문건수": af_orders,
                        "주문금액": af_amount
                    },
                    "쇼핑커넥트": {
                        "크리에이터": sc_creator,
                        "운영모델": sc_model,
                        "유입수": sc_visits,
                        "주문건수": sc_orders,
                        "주문금액": sc_amount
                    },
                    "공동구매": {
                        "크리에이터": cj_creator,
                        "운영모델": cj_model,
                        "주문건수": cj_orders,
                        "주문금액": cj_amount
                    },
                    "라이브커머스": {
                        "방송횟수": live_count,
                        "방송매출": live_sale,
                        "소요비용": live_cost
                    }
                }
                
                # weekly_data.json에 저장
                if os.path.exists("weekly_data.json"):
                    with open("weekly_data.json", "r", encoding='utf-8') as f:
                        weekly_data = json.load(f)
                else:
                    weekly_data = []
                
                # 중복 확인 및 업데이트
                found = False
                for idx, item in enumerate(weekly_data):
                    if (item.get("거래선") == input_agency and 
                        item.get("월") == input_month and 
                        item.get("주차") == input_week):
                        weekly_data[idx] = new_data
                        found = True
                        break
                
                if not found:
                    weekly_data.append(new_data)
                
                with open("weekly_data.json", "w", encoding='utf-8') as f:
                    json.dump(weekly_data, f, ensure_ascii=False, indent=2)
                
                st.success(f"✅ {input_agency} - {input_month} {input_week} 데이터가 저장되었습니다!")
                st.balloons()

