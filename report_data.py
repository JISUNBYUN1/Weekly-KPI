"""Shared activity ledger and presentation rules. No writes during reads."""
import json
import math
from pathlib import Path

BUILD_ID = "20260917-w37"
REFERENCE_FILES = {"activity_history.json", "smartstore_data.json", "affiliate_data.json",
                   "live_commerce_data.json", "weeks_2026.json"}


def display_number(value, decimals=0, signed=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return "미제공"
    prefix = "△" if value < 0 else "+" if signed and value > 0 else ""
    return prefix + ("<1" if decimals == 0 and 0 < abs(value) < 0.5 else format(abs(value), f",.{decimals}f"))


def read_file(root, name, default):
    import copy
    base = default
    for path in [Path(root) / name, Path(root) / "reference_data" / name] if name in REFERENCE_FILES else [Path(root) / name]:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(value, type(default)):
                base = value
                break
        except (OSError, ValueError):
            continue
    if name not in REFERENCE_FILES: return base
    try:
        snapshot = json.loads((Path(root) / "snapshot_w37" / name).read_text(encoding="utf-8"))
    except (OSError, ValueError): return base
    if name == "weeks_2026.json": return snapshot
    if isinstance(base, list):
        combined = {(v.get("거래선"),v.get("주차")):v for v in base if isinstance(v,dict)}
        combined.update({(v.get("거래선"),v.get("주차")):v for v in snapshot})
        return list(combined.values())
    def merge(old,new):
        for k,v in new.items():
            if isinstance(v,dict) and isinstance(old.get(k),dict): merge(old[k],v)
            else: old[k]=v
        return old
    result = merge(copy.deepcopy(base),snapshot)
    # Future zero-filled template columns are not closed actuals. Runtime inputs
    # are overlaid afterwards and may legitimately add subsequent weeks.
    import re
    def closed_only(node):
        if not isinstance(node,dict): return
        for key in list(node):
            match=re.fullmatch(r"W(\d+)[AB]?",key)
            month=re.fullmatch(r"(\d+)월",key)
            if (match and int(match[1])>37) or (month and int(month[1])>9): node.pop(key)
            else: closed_only(node[key])
    closed_only(result)
    return result


def activity_ledger(root):
    records = {}
    for row in read_file(root, "activity_history.json", []):
        if isinstance(row, dict) and row.get("거래선") and row.get("주차"):
            records[(row["거래선"], row["주차"])] = dict(row)
            records[(row["거래선"], row["주차"])].setdefault("기간", "")
    for row in read_file(root, "weekly_data.json", []):
        if not isinstance(row, dict):
            continue
        week = row.get("주차_표시") or row.get("주차")
        agency = row.get("거래선")
        if not agency or not week:
            continue
        parts = []
        for section, values in row.items():
            if isinstance(values, dict):
                if section == "당주주요활동":
                    parts.extend(f"{key}: {value}" for key, value in values.items() if value)
                elif values.get("마케팅활동"):
                    parts.append(f"{section}: {values['마케팅활동']}")
        records[(agency, week)] = {"거래선": agency, "주차": week,
                                  "월": row.get("월"), "기간": row.get("월", ""),
                                  "주요활동": "\n".join(parts)}
    overrides = read_file(root, "activity_overrides.json", {})
    deleted = set(overrides.get("deleted", []))
    edits = overrides.get("edits", {})
    result = []
    for (agency, week), row in records.items():
        key = f"{agency}|{week}"
        if key not in deleted:
            result.append({**row, **edits.get(key, {})})
    return result


def smartstore_dataset(root):
    """Keep purchase counts missing when the source has none; never copy monthly counts into weeks."""
    data = with_weekly_entries(root, "smartstore_data.json", read_file(root, "smartstore_data.json", {}))
    purchases = data.setdefault("구매비중", {}).setdefault("주차별", {})
    history = read_file(Path(root) / "reference_data", "smartstore_purchase_history.json", {})
    for week, agencies in history.items():
        if (Path(root) / "snapshot_w37").exists() and int(week[1:].rstrip("AB")) > 37: continue
        for agency, values in agencies.items():
            purchases.setdefault(week, {}).setdefault(agency, values)
    for row in read_file(root, "weekly_data.json", []):
        if not isinstance(row, dict):
            continue
        week = row.get("주차_표시") or row.get("주차")
        agency = row.get("거래선")
        source = row.get("네이버스마트스토어", {})
        new = source.get("신규구매구매자수")
        repeat = source.get("재구매구매자수")
        if not week or not agency or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in (new, repeat)):
            continue
        total = new + repeat
        purchases.setdefault(week, {})[agency] = {
            "신규구매고객수": new, "재구매고객수": repeat,
            "신규구매비중": new / total * 100 if total else None,
            "재구매비중": repeat / total * 100 if total else None,
        }
    return data


def with_weekly_entries(root, filename, data):
    """Overlay input weeks; update month totals by the replaced week's delta.

    A closed month with no comparable weekly baseline stays authoritative.
    This avoids counting a historical re-entry twice.
    """
    import copy
    data = copy.deepcopy(data)
    if filename not in {"live_commerce_data.json", "affiliate_data.json", "smartstore_data.json"}:
        return data
    latest = {}
    for row in read_file(root, "weekly_data.json", []):
        if isinstance(row, dict) and row.get("거래선") and row.get("월"):
            latest[(row["거래선"], row.get("주차_표시") or row.get("주차"))] = row
    for (agency, week), row in latest.items():
        if not week:
            continue
        month = row["월"]
        bucket = data
        if filename == "live_commerce_data.json":
            source = row.get("AI라이브", {})
            replacement = {"방송횟수": source.get("방송횟수", 0), "방송매출": source.get("방송매출", 0) * 1e6}
        elif filename == "affiliate_data.json":
            replacement = {}
            for channel in ("쇼핑커넥트", "공동구매"):
                source = row.get(channel, {})
                replacement[channel] = {**source, "주문금액": source.get("주문금액", 0) * 1e6}
                replacement[channel]["운영모델"] = source.get("운영모델수", 0)
        else:
            bucket = data.setdefault("신규관심고객", {})
            replacement = {"신규관심고객수": row.get("네이버스마트스토어", {}).get("신규관심고객수", 0)}
        weekly = bucket.setdefault("주차별", {}).setdefault(week, {})
        old = weekly.get(agency)
        weekly[agency] = replacement
        monthly = bucket.setdefault("월별", {}).setdefault(month, {})
        if agency in monthly and old is None:
            # Source monthly totals cannot safely be decomposed without a weekly baseline.
            continue
        current = monthly.setdefault(agency, {})

        def update(target, new, previous):
            for key, value in new.items():
                if isinstance(value, dict):
                    update(target.setdefault(key, {}), value, previous.get(key, {}))
                elif isinstance(value, (int, float)) and key not in ("전환율", "누적관심고객수"):
                    target[key] = target.get(key, 0) + value - previous.get(key, 0)
        update(current, replacement, old or {})
        if filename == "affiliate_data.json":
            for channels in (weekly[agency], current):
                channels.pop("계", None)
                for values in channels.values():
                    if isinstance(values, dict):
                        values["전환율"] = values.get("상품주문건수", 0) / values["유입수"] * 100 if values.get("유입수") else 0
    return data


def apply_star_upload(root, upload):
    """Validate a named STAR source before replacing its canonical CSV."""
    import io
    import re
    import pandas as pd
    match = re.fullmatch(r"STAR_(2025|2026)\.(xlsx|csv)", Path(upload.name).name, re.I)
    if not match:
        raise ValueError("실적 반영 파일명은 STAR_2025.xlsx 또는 STAR_2026.xlsx (CSV 가능)이어야 합니다.")
    content = io.BytesIO(bytes(upload.getbuffer()))
    if match[2].lower() == "csv":
        frame = pd.read_csv(content, encoding="utf-8-sig")
    else:
        preview = pd.read_excel(content, header=None, nrows=20)
        header = next((i for i in preview.index if "기준품목" in preview.iloc[i].astype(str).tolist()), None)
        if header is None:
            raise ValueError("기준품목 헤더가 없습니다.")
        content.seek(0)
        frame = pd.read_excel(content, header=header)
    required = {"영업그룹", "대표거래선", "기준품목", "월(AB)", "주(AB)", "메져_구분", "◆_매출", "◆_실판매_모바일/유통직판 포함"}
    if not required.issubset(frame.columns) or frame.empty:
        raise ValueError("STAR 필수 열 또는 데이터가 없습니다. 기존 실적을 유지합니다.")
    if not frame["월(AB)"].dropna().astype(str).str.startswith(match[1][2:] + "Y").all():
        raise ValueError("파일명 연도와 데이터 연도가 다릅니다.")
    destination = Path(root) / f"STAR_{match[1]}.csv"
    temporary = destination.with_suffix(".csv.tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(destination)
    return len(frame)
