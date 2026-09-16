import io
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd
from executive_report import _parse_star_dataframe, load_historical_activities, star_overall_totals, _latest_activity
from partner_views import load_activity_history, render_partner_analysis
from report_data import activity_ledger, apply_star_upload, display_number, with_weekly_entries
from test_executive import UI

ROOT = Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def test_actual_columns_exclude_forecast(self):
        frame = pd.DataFrame([{"기준품목": "냉장고", "메져_구분": "금액", "영업그룹": "홈쇼핑",
                               "월(AB)": "26Y09M", "주(AB)": "26Y38W", "◆_매출": 200,
                               "◆_실판매_모바일/유통직판 포함": 120,
                               "◆_AP1_S/I FCST_예상": 900, "◆_AP1_S/O FCST_예상": 800}])
        result = star_overall_totals(_parse_star_dataframe(frame), "월별", "9월")
        self.assertEqual(result["S/I_금액"], 200)
        self.assertEqual(result["S/O_금액"], 120)

    def test_activity_edits_deletes_and_new_entries_reach_both_views(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "activity_history.json": [{"거래선": "평강", "주차": "W01", "주요활동": "원문"},
                                          {"거래선": "평강", "주차": "W02", "주요활동": "삭제할 활동"}],
                "weekly_data.json": [{"거래선": "평강", "월": "9월", "주차": "W37",
                                      "AI라이브": {"마케팅활동": "냉장고 라이브 재편성"}}],
                "activity_overrides.json": {"edits": {"평강|W01": {"주요활동": "수정한 활동"}},
                                            "deleted": ["평강|W02"]}}
            for name, value in files.items():
                (root / name).write_text(json.dumps(value), encoding="utf-8")
            rows = load_activity_history(root)
            summary = load_historical_activities(root)
            self.assertEqual({r["주차"] for r in rows}, {"W01", "W37"})
            self.assertEqual({r["주차"] for r in summary}, {"W01", "W37"})
            self.assertIn("수정한 활동", str(summary))
            self.assertIn("냉장고 라이브 재편성", str(summary))

    def test_future_activity_not_used_for_past_analysis(self):
        rows = [{"거래선": "평강", "주차": "W37", "당주주요활동": {"활동": "미래 활동"}}]
        self.assertEqual(_latest_activity(rows, "평강", "W01")[0], [])

    def test_weekly_replacement_updates_month_by_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "weekly_data.json").write_text(json.dumps([{"거래선": "평강", "월": "9월", "주차": "W37",
                "AI라이브": {"방송횟수": 3, "방송매출": 2.5}}]))
            data = {"월별": {"9월": {"평강": {"방송횟수": 6, "방송매출": 6000000}}},
                    "주차별": {"W37": {"평강": {"방송횟수": 1, "방송매출": 1000000}}}}
            result = with_weekly_entries(root, "live_commerce_data.json", data)
            self.assertEqual(result["월별"]["9월"]["평강"]["방송매출"], 7500000)
            self.assertEqual(result["주차별"]["W37"]["평강"]["방송횟수"], 3)
            self.assertEqual(data["월별"]["9월"]["평강"]["방송매출"], 6000000)

    def test_partner_chart_excludes_other_partners(self):
        ui = UI("8월")
        original_select = ui.selectbox
        ui.selectbox = lambda label, *args, **kwargs: "평강" if label == "거래선" else original_select(label, *args, **kwargs)
        ui.text_area = lambda *args, **kwargs: ""
        render_partner_analysis(ui, ROOT, ["평강"], False, "백미란")
        peers = [chart for chart in ui.charts if chart.index.name == "거래선"]
        self.assertTrue(peers)
        self.assertTrue(all(set(chart.index) <= {"평강"} for chart in peers))

    def test_formatting(self):
        self.assertEqual(display_number(-12345), "△12,345")
        self.assertEqual(display_number(1234.56, 1, True), "+1,234.6")
        self.assertEqual(display_number(float("nan")), "미제공")

    def test_invalid_upload_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "STAR_2026.csv"
            target.write_text("unchanged")
            upload = io.BytesIO(b"bad,column\n1,2")
            upload.name = "STAR_2026.csv"
            with self.assertRaises(ValueError):
                apply_star_upload(directory, upload)
            self.assertEqual(target.read_text(), "unchanged")

    def test_valid_upload_is_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            columns = {"영업그룹": "SOP", "대표거래선": "평강", "기준품목": "냉장고", "월(AB)": "26Y09M",
                       "주(AB)": "26Y37W", "메져_구분": "금액", "◆_매출": 123, "◆_실판매_모바일/유통직판 포함": 100}
            upload = io.BytesIO(pd.DataFrame([columns]).to_csv(index=False).encode("utf-8-sig"))
            upload.name = "STAR_2026.csv"
            self.assertEqual(apply_star_upload(directory, upload), 1)
            result = pd.read_csv(Path(directory) / "STAR_2026.csv")
            self.assertEqual(result.iloc[0]["◆_매출"], 123)
