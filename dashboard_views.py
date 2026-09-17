"""Period selectors and empty-safe analytical views."""
import re
import pandas as pd
from report_data import smartstore_dataset, read_file, display_number

BUILD_ID = "20260917-w37"


def grouped_table_html(frame):
    """Escape values and merge repeated two-level headings/first-column groups."""
    from html import escape
    columns = list(frame.columns)
    multi = isinstance(frame.columns, pd.MultiIndex)
    header = "<thead><tr>"
    if multi:
        index = 0
        while index < len(columns):
            top, bottom = columns[index]
            if top == bottom:
                header += '<th rowspan="2">' + escape(str(top)) + '</th>'
                index += 1
            else:
                end = index + 1
                while end < len(columns) and columns[end][0] == top:
                    end += 1
                header += f'<th colspan="{end-index}">' + escape(str(top)) + '</th>'
                index = end
        header += '</tr><tr>' + ''.join('<th>' + escape(str(b)) + '</th>' for a, b in columns if a != b)
    else:
        header += ''.join('<th>' + escape(str(c)) + '</th>' for c in columns)
    header += '</tr></thead>'
    values = frame.values.tolist(); body = '<tbody>'; skip_until = -1
    for index, row in enumerate(values):
        body += '<tr>'
        for col, value in enumerate(row):
            if col == 0 and index < skip_until:
                continue
            span = 1
            if col == 0:
                while index + span < len(values) and values[index+span][0] == value:
                    span += 1
                skip_until = index + span
            body += f'<td rowspan="{span}">' + escape(str(value)) + '</td>'
        body += '</tr>'
    return ('<style>.pp3-table{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}'
            '.pp3-table th,.pp3-table td{text-align:center;padding:9px 4px;border:1px solid #dfe5ed;overflow-wrap:anywhere}'
            '.pp3-table th{background:#eef3fa;color:#17395e}.pp3-table tbody tr:nth-child(even){background:#f8fafc}</style>'
            '<table class="pp3-table">' + header + body + '</tbody></table>')


def render_grouped_table(st, frame):
    st.markdown(grouped_table_html(frame), unsafe_allow_html=True)


def period_controls(st, star, prefix):
    months = [f"{m}월" for m in range(12, 0, -1)]
    left, right = st.columns(2)
    with left:
        month = st.selectbox("대상 월", months, index=4, key=prefix + "_month")
    weekly = star.get("금액", {}).get("주차별", {})
    def order(label):
        match = re.match(r"(\d+)주([AB]?)", label)
        return (int(match[1]), match[2]) if match else (-1, "")
    weeks = sorted((w for w, bucket in weekly.items() if bucket.get("month") == month), key=order, reverse=True)
    with right:
        week = st.selectbox("대상 주차", ["계"] + weeks, key=prefix + "_week_" + month)
    if week in ("계", "월간"):
        n = int(month[:-1])
        return "월별", month, f"{n-1}월" if n > 1 else None
    timeline = sorted(weekly, key=order)
    index = timeline.index(week)
    return "주차별", week, timeline[index-1] if index else None


def source_caption(st, star):
    sources = star.get("_sources", {})
    if sources.get("2026", "").startswith("reference_data/"):
        st.caption("첨부받은 2026 STAR 기준 데이터를 표시합니다. 최신 실적은 담당자 피드백의 STAR 업로드로 반영할 수 있습니다.")


def purchase_rows(current, previous, agencies):
    rows = []
    for agency in agencies:
        values = current.get(agency, {})
        prior = previous.get(agency, {})
        row = {"거래선": agency}
        for label, field in (("신규", "신규구매고객수"), ("재구매", "재구매고객수")):
            value = values.get(field)
            old = prior.get(field)
            row[label + "구매고객(명)"] = display_number(value)
            ratio_key = label + "구매비중"
            row[label + "구매비중(%)"] = display_number(values.get(ratio_key), 1)
            change = (value - old) / old * 100 if isinstance(value, (int, float)) and isinstance(old, (int, float)) and old > 0 else None
            row[label + "구매 증감(%)"] = display_number(change, 1, signed=True)
        rows.append(row)
    return rows


def render_smartstore(st, root):
    st.subheader("스마트스토어")
    data = smartstore_dataset(root)
    calendar = read_file(root, "weeks_2026.json", {})
    left, right = st.columns(2)
    with left:
        month = st.selectbox("대상 월", [f"{m}월" for m in range(12, 0, -1)], index=3, key="smart_month")
    from executive_report import weeks_for_month, previous_week_label
    source_months = read_file(root / "reference_data", "smartstore_week_months.json", {})
    def week_order(label):
        match = re.fullmatch(r"W(\d+)([AB]?)", label)
        return (int(match[1]), match[2]) if match else (-1, "")
    available = set(data.get("신규관심고객", {}).get("주차별", {})) | set(data.get("구매비중", {}).get("주차별", {}))
    weeks = sorted({w for w in available if source_months.get(w) == month} |
                   {w for w in weeks_for_month(calendar, month) if w not in source_months and w in available},
                   key=week_order, reverse=True)
    with right:
        week = st.selectbox("대상 주차", ["계"] + weeks, key="smart_week_" + month)
    monthly = week in ("계", "월간")
    scope, key = ("월별", month) if monthly else ("주차별", week)
    if monthly:
        n = int(month[:-1]); prior_key = f"{n-1}월" if n > 1 else None
    else:
        timeline = sorted(available, key=week_order)
        index = timeline.index(week) if week in timeline else -1
        prior_key = timeline[index-1] if index > 0 else None
    comparison = "전월비" if monthly else "전주비"
    interests = data.get("신규관심고객", {}).get(scope, {})
    current = interests.get(key, {})
    previous = interests.get(prior_key, {})
    if monthly and month == "9월":
        previous = {}
        st.caption("9/13 마감 누계 · 전월 전체와 비교 제외")
    st.markdown("### 신규 관심고객 유입 현황")
    rows = []
    for agency, values in current.items():
        value = values.get("신규관심고객수"); old = previous.get(agency, {}).get("신규관심고객수")
        change = value - old if isinstance(value, (int, float)) and isinstance(old, (int, float)) else None
        rows.append({"거래선": agency, "신규 관심고객(명)": display_number(value),
                     comparison + "(명)": display_number(change, signed=True)})
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.bar_chart(pd.DataFrame([{"거래선": a, "신규 관심고객(명)": v.get("신규관심고객수")}
                                   for a, v in current.items()]).set_index("거래선"))
    else:
        st.info("선택 기간의 관심고객 데이터가 없습니다.")
    st.markdown("### 구매비중 변화 · " + comparison)
    if not monthly:
        st.caption("취합본의 주차별 신규·재구매 구매자 수를 복원했습니다. 거래선 신규 입력이 있으면 그 값을 우선합니다.")
    purchases = data.get("구매비중", {}).get(scope, {})
    now, before = purchases.get(key, {}), purchases.get(prior_key, {})
    if monthly and month == "9월": before = {}
    agencies = ["평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"]
    st.dataframe(pd.DataFrame(purchase_rows(now, before, agencies)), use_container_width=True, hide_index=True)
    if not now:
        st.info("이 기간의 신규·재구매 구매자 수가 원본에 없습니다. 거래선입력에서 해당 주차의 구매자 수를 저장하면 비중이 자동 계산됩니다. 월간 값을 주간 값으로 대체하지 않습니다.")
    else:
        chart = pd.DataFrame([{"거래선": a, "신규 구매(명)": v.get("신규구매고객수"),
                               "재구매(명)": v.get("재구매고객수")} for a, v in now.items()]).set_index("거래선")
        st.bar_chart(chart)


def render_premium(st, root):
    from executive_report import load_star_xlsx, build_premium_segment_table
    st.subheader("프리미엄 세그먼트 판매 비중")
    star, errors = load_star_xlsx(root)
    scope, value, _ = period_controls(st, star, "premium")
    source_caption(st, star)
    if not star:
        st.warning("STAR 실적을 읽을 수 없습니다. 기준 데이터 폴더 포함 여부 또는 STAR 업로드를 확인해주세요.")
        for error in errors:
            st.caption(error)
        return
    frame = build_premium_segment_table(star, scope, value)
    if frame.empty:
        st.info("선택 기간의 프리미엄 집계가 없습니다.")
        return
    render_grouped_table(st, frame)
    for basis in ("수량", "금액(억원)"):
        rows = frame[frame[("구분", "구분")] == basis]
        def numeric(v):
            try:
                return float(str(v).replace(",", "").replace("△", "-"))
            except ValueError:
                return float("nan")
        chart = pd.DataFrame({"품목": rows[("품목", "품목")],
                              "셀인 비중(%)": rows[("S/I", "비중(%)")].map(numeric),
                              "셀아웃 비중(%)": rows[("S/O", "비중(%)")].map(numeric)}).set_index("품목")
        st.markdown("**" + basis + " 프리미엄 비중**")
        st.bar_chart(chart)
