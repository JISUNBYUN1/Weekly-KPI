"""배포용 STAR CSV와 거래선 활동 JSON을 원본 엑셀에서 생성한다."""
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
AGENCIES = {"평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"}


def star_to_csv(year):
    source = ROOT / f"STAR_{year}.xlsx"
    preview = pd.read_excel(source, sheet_name=0, header=None, nrows=20, engine="openpyxl")
    header_row = next(index for index in preview.index
                      if "기준품목" in preview.iloc[index].astype(str).tolist())
    frame = pd.read_excel(source, sheet_name=0, header=header_row, engine="openpyxl")
    frame.to_csv(ROOT / f"STAR_{year}.csv", index=False, encoding="utf-8-sig")


def activity_to_json():
    source = ROOT / "주차별 거래선활동.xlsx"
    frame = pd.read_excel(source, sheet_name=0, header=None, engine="openpyxl")
    week, period, records = None, "", []
    for _, row in frame.iterrows():
        week_cell = row.iloc[1] if len(row) > 1 else None
        agency_cell = row.iloc[2] if len(row) > 2 else None
        if isinstance(week_cell, str):
            match = re.match(r"(\d+)주차\s*\(([^)]+)\)", week_cell)
            if match:
                week, period = f"W{int(match.group(1)):02d}", match.group(2).strip()
        agency = agency_cell.strip() if isinstance(agency_cell, str) else ""
        if week and agency in AGENCIES:
            values = [row.iloc[index] for index in (4, 5) if len(row) > index]
            body = "\n".join(str(value).strip() for value in values
                             if isinstance(value, str) and value.strip())
            if body:
                records.append({"거래선": agency, "주차": week, "기간": period, "주요활동": body})
    (ROOT / "activity_history.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    star_to_csv(2025)
    star_to_csv(2026)
    activity_to_json()
