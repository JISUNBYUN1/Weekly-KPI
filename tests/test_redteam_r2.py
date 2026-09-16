"""Ten failure-oriented deployment/data checks; no browser simulation claim."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from executive_report import load_star_xlsx, render_product_performance
from partner_views import load_activity_history
from report_data import smartstore_dataset, activity_ledger
from dashboard_views import render_smartstore, render_premium, purchase_rows
from test_executive import UI

ROOT = Path(__file__).resolve().parents[1]


class StrictUI(UI):
    def __init__(self, month="8월", week="계"):
        super().__init__(month, week)
        self.options = {}; self.tables = []; self.notices = []; self.html = []
    def selectbox(self, label, options, **kwargs):
        self.options[label] = options
        value = self.week if label == "대상 주차" else self.month if label == "대상 월" else options[0]
        if value not in options:
            raise AssertionError(f"invalid selection {value}: {options}")
        return value
    def dataframe(self, data, **kwargs): self.tables.append(data)
    def markdown(self, body, **kwargs): self.html.append(body)
    def info(self, message): self.notices.append(message)
    def warning(self, message): self.notices.append(message)


class RedTeamTests(unittest.TestCase):
    def isolated(self, directory):
        root = Path(directory)
        shutil.copytree(ROOT / "reference_data", root / "reference_data")
        return root

    def test_01_non_excel_activity_never_crashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.isolated(directory)
            (root / "주차별 거래선활동.xlsx").write_bytes(b"not an xlsx")
            with patch("pandas.read_excel", side_effect=AssertionError("activity must not use Excel")):
                self.assertEqual(len(load_activity_history(root)), 241)

    def test_02_broken_star_and_missing_csv_use_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.isolated(directory)
            (root / "STAR_2026.xlsx").write_bytes(b"unreadable")
            (root / "STAR_2026.csv").write_text("version https://git-lfs.github.com/spec/v1")
            star, errors = load_star_xlsx(root)
            self.assertTrue(star); self.assertFalse(errors)
            self.assertEqual(star["_sources"]["2026"], "reference_data/STAR_2026.csv")

    def test_03_missing_all_sources_keeps_period_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            ui = StrictUI()
            render_product_performance(ui, Path(directory))
            self.assertEqual(ui.options["대상 월"][0], "12월")
            self.assertEqual(ui.options["대상 주차"][0], "계")

    def test_04_premium_renders_both_quantity_and_money(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.isolated(directory); ui = StrictUI()
            render_premium(ui, root)
            self.assertTrue(any("rowspan" in value for value in ui.html))
            self.assertEqual(len(ui.charts), 2)
            self.assertTrue(any("금액(억원)" in value and "수량" in value for value in ui.html))

    def test_05_restored_week_purchase_counts(self):
        data = smartstore_dataset(ROOT)
        row = data["구매비중"]["주차별"]["W32"]["평강"]
        self.assertEqual(row["신규구매고객수"], 218)
        self.assertEqual(row["재구매고객수"], 23)
        self.assertAlmostEqual(row["신규구매비중"] + row["재구매비중"], 100)
        ui = StrictUI(week="W32"); render_smartstore(ui, ROOT)
        self.assertGreaterEqual(len(ui.tables), 2)

    def test_06_new_input_overrides_reference_purchase(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.isolated(directory)
            (root / "weekly_data.json").write_text(json.dumps([{"거래선": "평강", "월": "8월", "주차": "W32",
                "네이버스마트스토어": {"신규구매구매자수": 80, "재구매구매자수": 20}}]))
            row = smartstore_dataset(root)["구매비중"]["주차별"]["W32"]["평강"]
            self.assertEqual(row["신규구매비중"], 80)

    def test_07_missing_purchase_never_fabricates_zero(self):
        rows = purchase_rows({}, {}, ["평강"])
        self.assertTrue(all(value == "미제공" for key, value in rows[0].items() if key != "거래선"))

    def test_08_reference_does_not_overwrite_live_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.isolated(directory)
            path = root / "weekly_data.json"
            path.write_text('[{"거래선":"평강","주차":"W39","월":"9월","당주주요활동":{"기타":"새 활동"}}]')
            before = path.read_bytes(); rows = activity_ledger(root)
            self.assertTrue(any(r["주차"] == "W39" for r in rows))
            self.assertEqual(before, path.read_bytes())

    def test_09_month_filter_does_not_offer_other_months(self):
        ui = StrictUI(week="W36A"); render_smartstore(ui, ROOT)
        self.assertIn("W36A", ui.options["대상 주차"])
        self.assertNotIn("W36B", ui.options["대상 주차"])

    def test_10_invalid_json_and_valid_reference_are_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.isolated(directory)
            (root / "activity_history.json").write_text("{bad")
            self.assertEqual(len(activity_ledger(root)), 241)
            (root / "activity_overrides.json").write_text("[]")
            self.assertEqual(len(activity_ledger(root)), 241)
