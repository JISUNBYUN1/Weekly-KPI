"""거래선 활동 이력, 거래선 분석, 코멘트, 어필리에이트 요약 화면."""
import json
import re
from datetime import datetime
from pathlib import Path
from report_data import display_number, activity_ledger, with_weekly_entries

import pandas as pd

from executive_report import (business_week_to_star_label, load_star_xlsx, star_partner_totals,
                              star_overall_totals, star_partner_product_totals,
                              star_partner_yoy_totals, star_week_sort_key)

AGENCIES = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _week_key(label):
    match = re.fullmatch(r"W(\d{1,2})([AB]?)", str(label or ""))
    return (int(match.group(1)), match.group(2)) if match else (-1, "")


def _read_json(root, name, default):
    try:
        return with_weekly_entries(root, name, json.loads((Path(root) / name).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return default


def _write_json(path, value):
    """작은 사용자 편집 파일을 UTF-8 JSON으로 저장한다."""
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_activity_history(root):
    return [row for row in activity_ledger(root) if row.get("거래선") in AGENCIES]


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


def partner_metrics(root, agency, month, week, star_data=None):
    calendar = _read_json(root, "weeks_2026.json", {})
    live = _read_json(root, "live_commerce_data.json", {})
    affiliate = _read_json(root, "affiliate_data.json", {})
    smart = _read_json(root, "smartstore_data.json", {})
    live_row = _live_period(live, month, week).get(agency, {})
    affiliate_row = affiliate_period(affiliate, calendar, month, week).get(agency, {})
    smart_row = _smart_period(smart, month, week).get(agency, {})
    smart_field = "신규관심고객수"
    if star_data is None:
        star_data, _ = load_star_xlsx(root)
    star_scope_type = "월별" if week == "월간" else "주차별"
    star_scope = month if week == "월간" else business_week_to_star_label(week)
    star = star_partner_totals(star_data, star_scope_type, star_scope, agency) if star_data else {}
    return {
        "셀인 금액": star.get("S/I_금액", 0),
        "셀아웃 금액": star.get("S/O_금액", 0),
        "라이브 매출(백만)": live_row.get("방송매출", 0) / 1e6 if _number(live_row.get("방송매출", 0)) else 0,
        "방송횟수": live_row.get("방송횟수", 0),
        "어필리에이트 주문금액(백만)": _affiliate_total(affiliate_row) / 1e6,
        "신규 관심고객": smart_row.get(smart_field, 0),
    }


def _previous_period(calendar, month, week):
    if week == "월간":
        value = int(month.replace("월", ""))
        return (f"{value - 1}월", "월간") if value > 1 else (None, None)
    timeline = []
    for base_week, info in calendar.items():
        months = info.get("month", [])
        months = months if isinstance(months, list) else [months]
        if len(months) > 1:
            timeline.extend([(f"{months[0]}월", base_week + "A"), (f"{months[1]}월", base_week + "B")])
        elif months:
            timeline.append((f"{months[0]}월", base_week))
    index = next((idx for idx, item in enumerate(timeline) if item == (month, week)), -1)
    return timeline[index - 1] if index > 0 else (None, None)


def _format_delta(current, previous, unit=""):
    if not _number(previous):
        return "비교 기준 없음"
    value = current - previous
    return f"+{value:,.0f}{unit}" if value > 0 else f"△{abs(value):,.0f}{unit}" if value < 0 else f"0{unit}"


def _format_value(value):
    if not _number(value):
        return "미제공"
    return f"△{abs(value):,.0f}" if value < 0 else display_number(value, 0)


def _activity_highlights(records, limit=5):
    """활동 원문의 핵심 문장을 중복 없이 짧게 추린다."""
    highlights = []
    for record in records:
        text = re.sub(r"\s+", " ", record.get("주요활동", "")).strip()
        for part in re.split(r"[•●▪■▶]|(?<=다)\.", text):
            part = part.strip(" -·")
            if len(part) < 5 or part in highlights:
                continue
            highlights.append(part if len(part) <= 90 else part[:89] + "…")
    return highlights[:limit]


def _linked_recommendations(current, previous, records, label, previous_records=None,
                            monthly=False, activity_context=None):
    """기록 활동과 같은 기간의 KPI 방향을 연결해 근거·판단·실행안을 만든다."""
    previous_records = previous_records or []
    source_records = previous_records + records
    activity_text = " ".join(row.get("주요활동", "") for row in source_records)
    activity_timing = activity_context or ("전기 활동" if previous_records else "당기 활동")
    amount_unit, amount_scale = ("억원", 100)
    specs = [
        ("라이브 매출(백만)", "라이브커머스", ("라이브", "방송"), "회당 매출", "성과 상위 시간대·상품 조합으로 1회 재편성"),
        ("어필리에이트 주문금액(백만)", "어필리에이트", ("어필리에이트", "크리에이터", "공동구매", "쇼핑커넥트"), "크리에이터당 주문·전환율", "주문 발생 크리에이터와 재고 보유 상품에 콘텐츠 집중"),
        ("신규 관심고객", "관심고객", ("관심", "구독", "스토어", "찜"), "신규 관심→구매 전환율", "유입 소재·혜택을 분리 테스트하고 구매 전환까지 추적"),
    ]
    results = []
    for field, topic, keywords, kpi, action in specs:
        cur, prev = current.get(field, 0), previous.get(field) if previous else None
        delta = cur - prev if _number(prev) else None
        matched = [word for word in keywords if word in activity_text]
        activity_parts = [re.sub(r"\s+", " ", part).strip(" -·□")
                          for part in re.split(r"[\n•●▪■▶]|(?<=다)\.", activity_text)
                          if any(word in part for word in keywords)
                          and len(re.sub(r"\s+", " ", part).strip(" -·□")) > len(topic) + 2]
        excerpt = activity_parts[0] if activity_parts else topic
        excerpt = excerpt if len(excerpt) <= 55 else excerpt[:54] + "…"
        if matched and _number(delta):
            judgment = ("활동과 KPI가 동반 상승했습니다. 활동별 전환·주문 연결 확인 전에는 기여를 확정하지 않습니다" if delta > 0 else
                        "활동은 있었지만 KPI 상승으로 연결되지 않아 전환 구간 점검이 필요합니다" if delta < 0 else
                        "활동 이후 KPI가 보합으로, 실행 강도와 대상 적합성을 재검토해야 합니다")
            scale = 1 if field == "신규 관심고객" else amount_scale
            unit = "명" if field == "신규 관심고객" else amount_unit
            evidence = f"{activity_timing} {', '.join(matched[:2])} · {label} {_format_delta(cur / scale, prev / scale, unit)}"
            if delta > 0:
                tailored_action = f"‘{excerpt}’ 운영을 유지하되 성과 모델·대상 고객을 기록하고 인접 상품 1개에 제한 확대"
            elif delta < 0:
                tailored_action = f"‘{excerpt}’ 실행을 대상·소재·상품별로 분리해 확인 KPI가 낮은 조합을 중단하고, {action}"
            else:
                tailored_action = f"‘{excerpt}’의 집행 강도와 대상 적합성을 재점검하고, {action}"
        elif matched:
            judgment = "활동은 확인되지만 비교 실적이 없어 효과 판단을 보류합니다"
            evidence = f"{activity_timing} {', '.join(matched[:2])} · 비교 기준 없음"
            tailored_action = f"‘{excerpt}’에 목표값과 비교군을 지정해 다음 기간 {kpi}를 측정"
        elif _number(delta) and delta < 0:
            judgment = "KPI 하락 구간에 직접 연결되는 활동 기록이 부족합니다"
            scale = 1 if field == "신규 관심고객" else amount_scale
            unit = "명" if field == "신규 관심고객" else amount_unit
            evidence = f"{label} {_format_delta(cur / scale, prev / scale, unit)}"
            tailored_action = action
        else:
            continue
        results.append({"영역": topic, "근거": evidence, "판단": judgment,
                        "차기 실행 제안": tailored_action, "확인 KPI": kpi})
    if not results:
        comparable = [(field, topic, kpi, action, current.get(field, 0), previous.get(field))
                      for field, topic, _, kpi, action in specs if _number(previous.get(field))]
        if comparable:
            field, topic, kpi, action, cur, prev = min(comparable, key=lambda item: item[4] - item[5])
            scale = 1 if field == "신규 관심고객" else amount_scale
            unit = "명" if field == "신규 관심고객" else amount_unit
            results.append({"영역": topic, "근거": f"{label} {_format_delta(cur / scale, prev / scale, unit)}",
                            "판단": "선택 기간 실적 변동 기준 우선 점검 영역",
                            "차기 실행 제안": action, "확인 KPI": kpi})
        else:
            results.append({"영역": "판매 전환", "근거": f"셀아웃 {_format_value(current.get('셀아웃 금액', 0) / (1e8))}{amount_unit}",
                            "판단": "현재 실적 기준으로 판매 전환 효율 점검이 우선",
                            "차기 실행 제안": "셀인 상위·셀아웃 하위 모델을 분리해 재고·가격·노출 우선순위 재설정",
                            "확인 KPI": "모델별 셀인-셀아웃 차이·재고일수"})
    return results


def render_partner_activity(st, root, allowed_agencies):
    st.subheader("거래선 활동 기록")
    st.caption("주차별 활동을 선택해 확인·수정합니다. 실적 그래프는 STAR의 해당 대표거래선 셀인·셀아웃입니다.")
    records = load_activity_history(root)
    if not records:
        st.info("활동 이력이 없습니다.")
        return
    agency = st.selectbox("거래선", allowed_agencies, key="activity_record_agency")
    rows = sorted([row for row in records if row["거래선"] == agency], key=lambda value: _week_key(value["주차"]), reverse=True)
    if not rows:
        st.info("선택 거래선의 활동 기록이 없습니다.")
        return
    week = st.selectbox("활동 주차", [row["주차"] for row in rows], key=f"activity_week_{agency}")
    row = next(item for item in rows if item["주차"] == week)

    star_data, _ = load_star_xlsx(root)
    if star_data:
        all_weeks = sorted(star_data.get("금액", {}).get("주차별", {}), key=star_week_sort_key)
        selected_star_week = business_week_to_star_label(week)
        end = all_weeks.index(selected_star_week) + 1 if selected_star_week in all_weeks else len(all_weeks)
        trend_weeks = all_weeks[max(0, end - 8):end]
        trend = []
        for label in trend_weeks:
            totals = star_partner_totals(star_data, "주차별", label, agency)
            trend.append({"주차": label, "셀인(억원)": totals["S/I_금액"] / 1e8,
                          "셀아웃(억원)": totals["S/O_금액"] / 1e8})
        if trend:
            st.line_chart(pd.DataFrame(trend).set_index("주차"), color=["#164c96", "#66a3ff"], height=240)
            st.caption(f"STAR 대표거래선 기준 {agency} 주차별 셀인·셀아웃 실적(억원)입니다.")

    st.markdown(f"#### {week} · {row['기간']}")
    if row.get("수정일시"):
        st.caption(f"최근 수정: {row['수정일시']}")
    st.write(row["주요활동"])
    override_path = Path(root) / "activity_overrides.json"
    overrides = _read_json(root, "activity_overrides.json", {"edits": {}, "deleted": []})
    record_key = f"{agency}|{week}"
    left, right = st.columns([4, 1])
    with left:
        with st.form(f"edit_activity_{record_key}"):
            edited = st.text_area("활동 내용 수정", value=row["주요활동"], height=150)
            if st.form_submit_button("수정 저장"):
                overrides.setdefault("edits", {})[record_key] = {"주요활동": edited, "수정일시": datetime.now().strftime("%Y-%m-%d %H:%M")}
                _write_json(override_path, overrides)
                st.success("활동 기록을 수정했습니다.")
                st.rerun()
    with right:
        st.write("")
        st.write("")
        if st.button("삭제", key=f"delete_activity_{record_key}", type="secondary"):
            overrides.setdefault("deleted", []).append(record_key)
            overrides.get("edits", {}).pop(record_key, None)
            _write_json(override_path, overrides)
            st.success("활동 기록을 삭제했습니다.")
            st.rerun()


def render_partner_analysis(st, root, allowed_agencies, is_group_manager, user_name):
    st.subheader("거래선별 주간·월간 분석")
    calendar = _read_json(root, "weeks_2026.json", {})
    months = [f"{value}월" for value in range(12, 0, -1)]
    month = st.selectbox("대상 월", months, index=4, key="partner_analysis_month")
    week = st.selectbox("대상 주차", ["월간"] + weeks_for_month(calendar, month), key="partner_analysis_week")
    agency = st.selectbox("거래선", allowed_agencies, key="partner_analysis_agency")
    star_data, star_errors = load_star_xlsx(root)
    current = partner_metrics(root, agency, month, week, star_data)
    prev_month, prev_week = _previous_period(calendar, month, week)
    previous = partner_metrics(root, agency, prev_month, prev_week, star_data) if prev_month else {}
    label = "전월비" if week == "월간" else "전주비"
    monthly = week == "월간"
    if not monthly:
        st.caption("STAR와 활동은 주차 날짜 경계가 다릅니다. 번호 기준 비교이며 활동 효과는 참고 가설입니다.")
    amount_unit, amount_scale = ("억원", 100)
    columns = st.columns(5)
    for column, (name, title, unit, scale) in zip(columns, [
            ("셀인 금액", "셀인 실적", amount_unit, 1e8),
            ("셀아웃 금액", "셀아웃 실적", amount_unit, 1e8),
            ("라이브 매출(백만)", "라이브커머스 매출", amount_unit, amount_scale),
            ("어필리에이트 주문금액(백만)", "어필리에이트 주문금액", amount_unit, amount_scale),
            ("신규 관심고객", "신규 관심고객", "명", 1)]):
        with column:
            value = current[name]
            displayed = value / scale if _number(value) else None
            prior_displayed = previous.get(name) / scale if _number(previous.get(name)) else None
            st.metric(f"{title}({unit})", _format_value(displayed),
                      delta=f"{_format_delta(displayed, prior_displayed, unit)} ({label})" if _number(displayed) else None)
    peer_rows = [{"거래선": item, **partner_metrics(root, item, month, week, star_data)} for item in (AGENCIES if is_group_manager else allowed_agencies)]
    peer = pd.DataFrame(peer_rows)
    st.markdown("#### 거래선별 성과 위치")
    left, right = st.columns([1.1, 1])
    with left:
        star_peer = peer[["거래선", "셀인 금액", "셀아웃 금액"]].copy()
        star_peer[["셀인 금액", "셀아웃 금액"]] = star_peer[["셀인 금액", "셀아웃 금액"]] / (1e8)
        st.bar_chart(star_peer.set_index("거래선"), height=280)
    with right:
        for field, text, unit in [("셀아웃 금액", "셀아웃", amount_unit), ("라이브 매출(백만)", "라이브", amount_unit), ("어필리에이트 주문금액(백만)", "어필리에이트", amount_unit), ("신규 관심고객", "신규 관심고객", "명")]:
            rank_value = peer[field].rank(method="min", ascending=False)[peer["거래선"] == agency].iloc[0]
            if not _number(rank_value) or pd.isna(rank_value) or not _number(current.get(field)):
                st.write(f"- {text}: 미제공")
                continue
            rank = int(rank_value)
            if field in ("셀인 금액", "셀아웃 금액"):
                display_value, display_unit = current[field] / (1e8), amount_unit
            else:
                display_value = current[field] / (amount_scale if "백만" in field else 1)
                display_unit = amount_unit if "백만" in field else unit
            st.write(f"- {text}: " + (f"{rank}위 / " if is_group_manager else "") + f"{_format_value(display_value)}{display_unit}")
    if star_data:
        star_scope_type = "월별" if monthly else "주차별"
        star_scope = month if monthly else business_week_to_star_label(week)
        yoy = star_partner_yoy_totals(star_data, star_scope_type, star_scope, agency)
        yoy_rows = []
        scale = 1e8
        for label_name, current_key, yoy_key in (("셀인", "셀인 금액", "S/I_금액"), ("셀아웃", "셀아웃 금액", "S/O_금액")):
            current_value, previous_year = current[current_key], yoy[yoy_key]
            change = (current_value - previous_year) / previous_year * 100 if previous_year else None
            yoy_rows.append({"지표": label_name,
                             f"2026 실적({amount_unit})": _format_value(current_value / scale),
                             f"2025 동기간({amount_unit})": _format_value(previous_year / scale),
                             "전년비(%)": f"+{change:.1f}" if _number(change) and change > 0 else f"△{abs(change):.1f}" if _number(change) and change < 0 else "0.0" if change == 0 else "N/A"})
        st.dataframe(pd.DataFrame(yoy_rows), use_container_width=True, hide_index=True)
    if star_errors:
        st.caption(" · ".join(star_errors))
    history = load_activity_history(root)
    valid_weeks = {value.rstrip("AB") for value in weeks_for_month(calendar, month)}
    records = [row for row in history if row["거래선"] == agency and
               ((week == "월간" and row["주차"].rstrip("AB") in valid_weeks) or
                row["주차"].rstrip("AB") == week.rstrip("AB"))]
    previous_records = [row for row in history if row["거래선"] == agency and prev_week and
                        ((prev_week == "월간" and row["주차"].rstrip("AB") in {w.rstrip("AB") for w in weeks_for_month(calendar, prev_month)}) or row["주차"].rstrip("AB") == prev_week.rstrip("AB"))]
    analysis_records = records
    activity_context = None
    if not analysis_records:
        cutoff = max((_week_key(value)[0] for value in (valid_weeks if week == "월간" else [week])), default=99)
        eligible = [row for row in history if row["거래선"] == agency and _week_key(row["주차"])[0] <= cutoff]
        if eligible:
            latest_week = max(eligible, key=lambda row: _week_key(row["주차"]))["주차"]
            analysis_records = [row for row in eligible if row["주차"] == latest_week]
            activity_context = f"최근 {latest_week} 활동"
    st.markdown("#### 선택 기간 활동 핵심 요약")
    highlights = _activity_highlights(analysis_records)
    if highlights:
        if not records:
            st.caption(f"선택 기간의 직접 기록이 없어 {activity_context}을 참고합니다.")
        for item in highlights:
            st.markdown(f"- {item}")
    else:
        st.info("연결 가능한 활동 기록이 없어 실적 변동을 기준으로 제안합니다.")

    st.markdown("#### 활동–실적 연계 분석 및 실행 제언")
    st.caption("동일 기간의 활동과 실적 방향을 함께 관찰한 결과이며, 직접적인 인과로 단정하지 않습니다.")
    recommendation_rows = _linked_recommendations(
        current, previous, analysis_records, label, previous_records,
        monthly=monthly, activity_context=activity_context)
    if star_data and previous:
        current_scope = month if monthly else business_week_to_star_label(week)
        previous_scope = prev_month if monthly else business_week_to_star_label(prev_week)
        current_products = star_partner_product_totals(star_data, "월별" if monthly else "주차별", current_scope, agency)
        previous_products = star_partner_product_totals(star_data, "월별" if monthly else "주차별", previous_scope, agency)
        product_changes = []
        for product in set(current_products) | set(previous_products):
            current_so = current_products.get(product, {}).get("S/O", 0)
            previous_so = previous_products.get(product, {}).get("S/O", 0)
            product_changes.append((product, current_so - previous_so, current_so, previous_so))
        if product_changes:
            product_changes.sort(key=lambda item: item[1])
            declining, growing = product_changes[0], product_changes[-1]
            scale = 1e8
            if declining[1] < 0:
                recommendation_rows.insert(0, {
                    "영역": f"셀아웃·{declining[0]}",
                    "근거": f"{label} △{abs(declining[1]) / scale:,.0f}{amount_unit} · 당기 {_format_value(declining[2] / scale)}{amount_unit}",
                    "판단": "선택 기간 셀아웃 감소 기여가 가장 큰 품목",
                    "차기 실행 제안": f"{declining[0]}의 가격·재고·노출 변화를 확인하고, 전기 활동 중 해당 품목 유입 활동의 주문 전환을 재점검",
                    "확인 KPI": f"{declining[0]} 셀아웃·재고일수·구매 전환율",
                })
            if growing[1] > 0:
                recommendation_rows.insert(0, {
                    "영역": f"셀아웃·{growing[0]}",
                    "근거": f"{label} +{growing[1] / scale:,.0f}{amount_unit} · 당기 {_format_value(growing[2] / scale)}{amount_unit}",
                    "판단": "선택 기간 셀아웃 증가 기여가 가장 큰 품목",
                    "차기 실행 제안": f"{growing[0]}에서 성과가 난 모델·혜택·콘텐츠 조합을 유지하고 인접 품목 1개에 확장",
                    "확인 KPI": f"{growing[0]} 셀아웃·모델별 매출·행사 전환율",
                })
        si_so_gap = current.get("셀인 금액", 0) - current.get("셀아웃 금액", 0)
        if si_so_gap > 0:
            recommendation_rows.insert(0, {
                "영역": "재고 회전",
                "근거": f"셀인이 셀아웃보다 {si_so_gap / (1e8):,.0f}{amount_unit} 높음",
                "판단": "입고가 판매보다 앞서 재고 부담 가능성 확인 필요",
                "차기 실행 제안": "셀인 상위·셀아웃 하위 모델을 추려 가격·광고·라이브 노출을 우선 배정",
                "확인 KPI": "모델별 셀인-셀아웃 차이·재고일수",
            })
    recommendation_df = pd.DataFrame(recommendation_rows)
    for _, proposal in recommendation_df.iterrows():
        with st.expander(str(proposal.get("영역", "실행 제안")), expanded=True):
            for key, value in proposal.items():
                st.markdown(f"**{key}** · {value}")
    if analysis_records:
        with st.expander("선택 기간의 활동 기록" if records else f"참고 활동 기록 · {activity_context}", expanded=False):
            for row in analysis_records:
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
    star_data, _ = load_star_xlsx(root)
    data = [partner_metrics(root, agency, month, week, star_data) for agency in AGENCIES]
    total_fields = ["셀인 금액", "셀아웃 금액", "라이브 매출(백만)", "어필리에이트 주문금액(백만)", "신규 관심고객"]
    totals = {field: sum(item.get(field, 0) for item in data) for field in total_fields}
    monthly = week == "월간"
    if not monthly:
        st.caption("STAR와 활동은 주차 날짜 경계가 다릅니다. 번호 기준 비교이며 활동 효과는 참고 가설입니다.")
    if star_data:
        star_scope_type = "월별" if monthly else "주차별"
        star_scope = month if monthly else business_week_to_star_label(week)
        overall = star_overall_totals(star_data, star_scope_type, star_scope)
        totals["셀인 금액"] = overall["S/I_금액"]
        totals["셀아웃 금액"] = overall["S/O_금액"]
    columns = st.columns(5)
    for column, (field, label, unit, scale) in zip(columns, [
            ("셀인 금액", "셀인 실적", "억원", 1e8),
            ("셀아웃 금액", "셀아웃 실적", "억원", 1e8),
            ("라이브 매출(백만)", "라이브커머스 매출", "억원", 100),
            ("어필리에이트 주문금액(백만)", "어필리에이트 주문금액", "억원", 100),
            ("신규 관심고객", "신규 관심고객", "명", 1)]):
        with column:
            st.metric(f"{label}({unit})", _format_value(totals[field] / scale))
    st.caption("셀인·셀아웃은 품목 기준 전체 4개 채널 합계입니다. 개별 SOP 실적과 활동 기록은 거래선별 분석 메뉴에서 권한 범위 내에서만 표시됩니다.")
def render_affiliate_dashboard(st, root, allowed_agencies):
    st.subheader("어필리에이트 실적")
    calendar = _read_json(root, "weeks_2026.json", {})
    affiliate = _read_json(root, "affiliate_data.json", {"월별": {}, "주차별": {}})
    months = [f"{value}월" for value in range(12, 6, -1)]
    default_index = months.index("8월") if "8월" in months else 0
    month = st.selectbox("대상 월", months, index=default_index, key="affiliate_month")
    weekly_source = affiliate.get("주차별", {})
    available = ["계"] + [week for week in weeks_for_month(calendar, month)
                           if week in weekly_source or week.rstrip("AB") in weekly_source]
    week = st.selectbox("대상 주차", available, key="affiliate_week")
    data = affiliate_period(affiliate, calendar, month, "월간" if week == "계" else week)
    monthly = week == "계"
    amount_unit, amount_scale = ("억원", 1e8)
    sales_rows, operation_rows, chart_values = [], [], []
    for agency in allowed_agencies:
        channels = data.get(agency, {})
        shop, joint = channels.get("쇼핑커넥트", {}), channels.get("공동구매", {})
        total_orders = sum(v.get("상품주문건수", 0) for v in (shop, joint))
        total_creators = sum(v.get("크리에이터운영수", 0) for v in (shop, joint))
        sales_rows.append({
            ("거래선", "거래선"): agency,
            ("전체", "주문(건)"): display_number(total_orders, 0),
            ("전체", f"금액({amount_unit})"): display_number(_affiliate_total(channels) / amount_scale, 0),
            ("쇼핑커넥트", "주문(건)"): display_number(shop.get('상품주문건수', 0), 0),
            ("쇼핑커넥트", f"금액({amount_unit})"): display_number(shop.get('주문금액', 0) / amount_scale, 0),
            ("공동구매", "주문(건)"): display_number(joint.get('상품주문건수', 0), 0),
            ("공동구매", f"금액({amount_unit})"): display_number(joint.get('주문금액', 0) / amount_scale, 0),
        })
        inflow, shop_orders = shop.get("유입수", 0), shop.get("상품주문건수", 0)
        operation_rows.append({
            ("거래선", "거래선"): agency,
            ("전체", "크리에이터"): display_number(total_creators, 0),
            ("쇼핑커넥트", "크리에이터"): display_number(shop.get('크리에이터운영수', 0), 0),
            ("쇼핑커넥트", "모델"): display_number(shop.get('운영모델', shop.get('운영모델수', 0)), 0),
            ("쇼핑커넥트", "유입"): display_number(inflow, 0),
            ("쇼핑커넥트", "전환율(%)"): display_number(shop_orders / inflow * 100, 1) if inflow else "0.0",
            ("공동구매", "크리에이터"): display_number(joint.get('크리에이터운영수', 0), 0),
            ("공동구매", "모델"): display_number(joint.get('운영모델', joint.get('운영모델수', 0)), 0),
        })
        chart_values.append({"거래선": agency, "쇼핑커넥트": shop.get("주문금액", 0) / amount_scale,
                             "공동구매": joint.get("주문금액", 0) / amount_scale})
    sales_frame, operation_frame = pd.DataFrame(sales_rows), pd.DataFrame(operation_rows)
    if not sales_frame.empty:
        sales_frame.columns = pd.MultiIndex.from_tuples(sales_frame.columns)
        operation_frame.columns = pd.MultiIndex.from_tuples(operation_frame.columns)
    total_amount = sum(_affiliate_total(data.get(agency, {})) for agency in allowed_agencies) / amount_scale
    total_orders = sum(sum(data.get(agency, {}).get(ch, {}).get("상품주문건수", 0) for ch in ("쇼핑커넥트", "공동구매")) for agency in allowed_agencies)
    total_creators = sum(sum(data.get(agency, {}).get(ch, {}).get("크리에이터운영수", 0) for ch in ("쇼핑커넥트", "공동구매")) for agency in allowed_agencies)
    card1, card2, card3 = st.columns(3)
    card1.metric(f"전체 주문금액({amount_unit})", display_number(total_amount, 0))
    card2.metric("전체 주문(건)", display_number(total_orders, 0))
    card3.metric("전체 크리에이터(명)", display_number(total_creators, 0))
    st.markdown("#### 거래선별·채널별 매출 성과")
    st.dataframe(sales_frame, use_container_width=True, hide_index=True)
    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### 채널 주문금액 비교")
        chart = pd.DataFrame(chart_values).set_index("거래선")
        st.bar_chart(chart, height=300)
    with right:
        st.markdown("#### 운영·전환 상세")
        st.dataframe(operation_frame, use_container_width=True, hide_index=True, height=300)
    st.caption("월간 값은 월별 원천이 있으면 사용하고, 없으면 해당 월의 주차 데이터를 자동 합산합니다.")
