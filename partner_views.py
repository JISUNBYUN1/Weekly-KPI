"""거래선 활동 이력, 거래선 분석, 코멘트, 어필리에이트 요약 화면."""
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _week_key(label):
    match = re.fullmatch(r"W(\d{1,2})([AB]?)", str(label or ""))
    return (int(match.group(1)), match.group(2)) if match else (-1, "")


def _read_json(root, name, default):
    try:
        return json.loads((Path(root) / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_activity_history(root):
    """업로드된 활동 원장을 거래선/주차 단위로 정규화한다."""
    source = Path(root) / "주차별 거래선활동.xlsx"
    if not source.exists():
        return []
    frame = pd.read_excel(source, header=None)
    week, period, rows = None, "", []
    for _, row in frame.iterrows():
        week_cell, agency_cell = row.iloc[1], row.iloc[2]
        if isinstance(week_cell, str):
            match = re.match(r"(\d+)주차\s*\(([^)]+)\)", week_cell)
            if match:
                week, period = f"W{int(match.group(1)):02d}", match.group(2)
        if week and isinstance(agency_cell, str) and agency_cell.strip() in AGENCIES:
            body = "\n".join(str(value).strip() for value in (row.iloc[4], row.iloc[5])
                             if isinstance(value, str) and value.strip())
            if body:
                rows.append({"거래선": agency_cell.strip(), "주차": week, "기간": period, "주요활동": body})
    return rows


def weeks_for_month(calendar, month):
    month_num = int(str(month).replace("월", ""))
    result = []
    for base_week, info in calendar.items():
        months = info.get("month", [])
        months = months if isinstance(months, list) else [months]
        if month_num not in months:
            continue
        result.append(base_week if len(months) == 1 else base_week + ("A" if months.index(month_num) == 0 else "B"))
    return sorted(result, key=_week_key, reverse=True)


def affiliate_period(affiliate, calendar, month, week):
    """월별 원천이 없어도 월에 포함되는 주차를 합산한다."""
    if week != "월간":
        return affiliate.get("주차별", {}).get(week, affiliate.get("주차별", {}).get(str(week).rstrip("AB"), {}))
    direct = affiliate.get("월별", {}).get(month)
    if direct:
        return direct
    merged = {}
    for week_label in weeks_for_month(calendar, month):
        source_week = affiliate.get("주차별", {}).get(week_label, affiliate.get("주차별", {}).get(week_label.rstrip("AB"), {}))
        for agency, channel_data in source_week.items():
            for channel, values in channel_data.items():
                target = merged.setdefault(agency, {}).setdefault(channel, {})
                for field, value in values.items():
                    if field == "전환율":
                        continue
                    if _number(value):
                        target[field] = target.get(field, 0) + value
        
    for channel_data in merged.values():
        for channel, values in channel_data.items():
            inflow, orders = values.get("유입수", 0), values.get("상품주문건수", 0)
            values["전환율"] = orders / inflow * 100 if inflow else 0
    return merged


def _affiliate_total(channel_data):
    return sum(values.get("주문금액", 0) for channel, values in channel_data.items()
               if channel in ("쇼핑커넥트", "공동구매") and _number(values.get("주문금액", 0)))


def _live_period(live, month, week):
    return live.get("월별" if week == "월간" else "주차별", {}).get(month if week == "월간" else week, {})


def _smart_period(smart, month, week):
    return smart.get("신규관심고객", {}).get("월별" if week == "월간" else "주차별", {}).get(month if week == "월간" else week, {})


def partner_metrics(root, agency, month, week):
    calendar = _read_json(root, "weeks_2026.json", {})
    live = _read_json(root, "live_commerce_data.json", {})
    affiliate = _read_json(root, "affiliate_data.json", {})
    smart = _read_json(root, "smartstore_data.json", {})
    live_row = _live_period(live, month, week).get(agency, {})
    affiliate_row = affiliate_period(affiliate, calendar, month, week).get(agency, {})
    smart_row = _smart_period(smart, month, week).get(agency, {})
    return {
        "라이브 매출(백만)": live_row.get("방송매출", 0) / 1e6 if _number(live_row.get("방송매출", 0)) else 0,
        "방송횟수": live_row.get("방송횟수", 0),
        "어필리에이트 주문금액(백만)": _affiliate_total(affiliate_row) / 1e6,
        "신규 관심고객": smart_row.get("신규관심고객수", 0),
    }


def _previous_period(calendar, month, week):
    if week == "월간":
        value = int(month.replace("월", ""))
        return (f"{value - 1}월", "월간") if value > 1 else (None, None)
    options = weeks_for_month(calendar, month)
    index = options.index(week) if week in options else -1
    return (month, options[index + 1]) if 0 <= index < len(options) - 1 else (None, None)


def _format_delta(current, previous, unit=""):
    if not _number(previous):
        return "비교 기준 없음"
    value = current - previous
    return f"+{value:,.0f}{unit}" if value > 0 else f"△{abs(value):,.0f}{unit}" if value < 0 else f"0{unit}"


def render_partner_activity(st, root, allowed_agencies):
    st.subheader("거래선 활동 기록")
    st.caption("1~35주차 활동 원문을 거래선별로 확인합니다.")
    records = load_activity_history(root)
    if not records:
        st.info("활동 이력이 없습니다.")
        return
    agency = st.selectbox("거래선", allowed_agencies, key="activity_record_agency")
    rows = [row for row in records if row["거래선"] == agency]
    chart = pd.DataFrame({"주차": [row["주차"] for row in rows], "기록 건수": [1] * len(rows)})
    st.bar_chart(chart.set_index("주차"), color="#164c96", height=180)
    for row in sorted(rows, key=lambda value: _week_key(value["주차"]), reverse=True):
        with st.expander(f"{row['주차']} · {row['기간']}"):
            st.write(row["주요활동"])


def render_partner_analysis(st, root, allowed_agencies, is_group_manager, user_name):
    st.subheader("거래선별 주간·월간 분석")
    calendar = _read_json(root, "weeks_2026.json", {})
    months = [f"{value}월" for value in range(12, 0, -1)]
    month = st.selectbox("대상 월", months, index=4, key="partner_analysis_month")
    week = st.selectbox("대상 주차", ["월간"] + weeks_for_month(calendar, month), key="partner_analysis_week")
    agency = st.selectbox("거래선", allowed_agencies, key="partner_analysis_agency")
    current = partner_metrics(root, agency, month, week)
    prev_month, prev_week = _previous_period(calendar, month, week)
    previous = partner_metrics(root, agency, prev_month, prev_week) if prev_month else {}
    label = "전월비" if week == "월간" else "전주비"
    columns = st.columns(3)
    for column, (name, unit) in zip(columns, [("라이브 매출(백만)", "백만원"), ("어필리에이트 주문금액(백만)", "백만원"), ("신규 관심고객", "명")]):
        with column:
            value = current[name]
            st.metric(name.replace("(백만)", ""), f"{value:,.1f} {unit}" if unit == "백만원" else f"{value:,.0f} {unit}",
                      delta=f"{_format_delta(value, previous.get(name), unit)} ({label})")
    peer_rows = [{"거래선": item, **partner_metrics(root, item, month, week)} for item in AGENCIES]
    peer = pd.DataFrame(peer_rows)
    st.markdown("#### 거래선 위치와 특이 신호")
    left, right = st.columns([1.1, 1])
    with left:
        st.bar_chart(peer.set_index("거래선")[["라이브 매출(백만)", "어필리에이트 주문금액(백만)"]], height=280)
    with right:
        for field, text, unit in [("라이브 매출(백만)", "라이브", "백만원"), ("어필리에이트 주문금액(백만)", "어필리에이트", "백만원"), ("신규 관심고객", "신규 관심고객", "명")]:
            rank = peer[field].rank(method="min", ascending=False)[peer["거래선"] == agency].iloc[0]
            st.write(f"- {text}: {int(rank)}위 / {current[field]:,.1f}{unit}")
    records = [row for row in load_activity_history(root) if row["거래선"] == agency and (week == "월간" or row["주차"] == week)]
    st.markdown("#### 활동 기반 분석 및 제언")
    if current["어필리에이트 주문금액(백만)"] == 0:
        st.warning("어필리에이트 주문금액이 없거나 낮습니다. 크리에이터별 유입·주문·취소를 분리하고, 성과 상위 콘텐츠 유형을 다음 캠페인에 우선 적용하세요.")
    elif previous and current["어필리에이트 주문금액(백만)"] < previous.get("어필리에이트 주문금액(백만)", 0):
        st.warning("어필리에이트가 직전 기간보다 감소했습니다. 콘텐츠 발행 수보다 주문 발생 크리에이터와 출고 가능 상품을 우선 점검하세요.")
    else:
        st.success("어필리에이트 성과가 유지·확대되고 있습니다. 성과가 난 상품·크리에이터 조합을 다음 주에도 재활용하고, 주문 취소율을 함께 확인하세요.")
    if current["라이브 매출(백만)"] > 0:
        st.info("라이브는 방송 횟수뿐 아니라 회당 매출과 시간대별 전환을 기록해 고효율 편성으로 재배분하세요.")
    if records:
        with st.expander("선택 기간의 활동 기록", expanded=False):
            for row in records:
                st.write(f"**{row['주차']} · {row['기간']}**")
                st.write(row["주요활동"])
    comments = _read_json(root, "manager_comments.json", {})
    comment_key = f"{agency}|{month}|{week}"
    existing = comments.get(comment_key, {})
    st.markdown("#### 영업 담당 코멘트")
    if existing:
        st.info(f"**{existing.get('작성자', '')}** · {existing.get('저장일시', '')}\n\n{existing.get('코멘트', '')}")
        if existing.get("반영사항"):
            st.success(f"**추가 수정 반영**\n\n{existing['반영사항']}")
    if is_group_manager:
        with st.form(f"comment_{comment_key}"):
            comment = st.text_area("담당자 코멘트", value=existing.get("코멘트", ""), height=100)
            reflection = st.text_area("코멘트 반영 내용", value=existing.get("반영사항", ""), height=80)
            if st.form_submit_button("코멘트 저장"):
                comments[comment_key] = {"거래선": agency, "월": month, "주차": week, "작성자": user_name,
                                         "코멘트": comment, "반영사항": reflection,
                                         "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M")}
                (Path(root) / "manager_comments.json").write_text(json.dumps(comments, ensure_ascii=False, indent=2), encoding="utf-8")
                st.success("저장했습니다.")


def render_common_summary(st, root):
    """거래선 담당자에게도 노출 가능한 그룹 공통 요약. 개별 거래선 값은 제외한다."""
    st.subheader("월간·주간 공통 요약")
    calendar = _read_json(root, "weeks_2026.json", {})
    months = [f"{value}월" for value in range(12, 0, -1)]
    month = st.selectbox("대상 월", months, index=4, key="common_summary_month")
    week = st.selectbox("대상 주차", ["월간"] + weeks_for_month(calendar, month), key="common_summary_week")
    data = [partner_metrics(root, agency, month, week) for agency in AGENCIES]
    totals = {field: sum(item.get(field, 0) for item in data) for field in ["라이브 매출(백만)", "어필리에이트 주문금액(백만)", "신규 관심고객"]}
    columns = st.columns(3)
    for column, (field, label, unit) in zip(columns, [("라이브 매출(백만)", "라이브커머스 매출", "백만원"), ("어필리에이트 주문금액(백만)", "어필리에이트 주문금액", "백만원"), ("신규 관심고객", "스마트스토어 신규 관심고객", "명")]):
        with column:
            st.metric(label, f"{totals[field]:,.1f} {unit}" if unit == "백만원" else f"{totals[field]:,.0f} {unit}")
    st.caption("개별 거래선 실적과 활동 기록은 거래선별 분석 메뉴에서 권한 범위 내에서만 표시됩니다.")
def render_affiliate_dashboard(st, root, allowed_agencies):
    st.subheader("어필리에이트 실적")
    calendar = _read_json(root, "weeks_2026.json", {})
    affiliate = _read_json(root, "affiliate_data.json", {"월별": {}, "주차별": {}})
    months = [f"{value}월" for value in range(12, 0, -1)]
    month = st.selectbox("대상 월", months, index=4, key="affiliate_month")
    available = ["월간"] + [week for week in weeks_for_month(calendar, month) if week in affiliate.get("주차별", {})]
    week = st.selectbox("대상 주차", available, key="affiliate_week")
    data = affiliate_period(affiliate, calendar, month, week)
    rows = []
    for agency in allowed_agencies:
        channels = data.get(agency, {})
        shop, joint = channels.get("쇼핑커넥트", {}), channels.get("공동구매", {})
        rows.append({
            "거래선": agency,
            "쇼핑커넥트 크리에이터": shop.get("크리에이터운영수", 0), "쇼핑커넥트 유입": shop.get("유입수", 0),
            "쇼핑커넥트 주문": shop.get("상품주문건수", 0), "쇼핑커넥트 금액(백만)": shop.get("주문금액", 0) / 1e6,
            "공동구매 크리에이터": joint.get("크리에이터운영수", 0), "공동구매 주문": joint.get("상품주문건수", 0),
            "공동구매 금액(백만)": joint.get("주문금액", 0) / 1e6,
        })
    frame = pd.DataFrame(rows)
    left, right = st.columns([1.35, 1])
    with left:
        st.dataframe(frame, use_container_width=True, hide_index=True)
    with right:
        chart = frame.set_index("거래선")[["쇼핑커넥트 금액(백만)", "공동구매 금액(백만)"]]
        st.bar_chart(chart, height=310)
    st.caption("월간 값은 월별 원천이 있으면 사용하고, 없으면 해당 월의 주차 데이터를 자동 합산합니다.")
