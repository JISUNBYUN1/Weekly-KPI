"""표준 라이브러리 테스트. 실제 Streamlit 브라우저 테스트를 대체하지 않는다."""
import ast
import copy
import json
import math
import os
from pathlib import Path
import re
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_helpers():
    # 앱 UI를 실행하지 않고, 배포 파일 안의 실제 함수를 그대로 테스트한다.
    tree = ast.parse((ROOT / "streamlit_app.py").read_text(encoding="utf-8"))
    definitions = [node for node in tree.body if
                   (isinstance(node, ast.FunctionDef) and node.name.startswith("live_")) or
                   (isinstance(node, ast.Assign) and any(
                       isinstance(target, ast.Name) and target.id == "AGENCIES" for target in node.targets))]
    namespace = dict(json=json, math=math, os=os, re=re, tempfile=tempfile,
                     Path=Path, __file__=str(ROOT / "streamlit_app.py"))
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "streamlit_app.py", "exec"), namespace)
    return namespace


H = load_helpers()


class FakeStreamlit:
    """선택지/표/안내문 인자를 검증하는 UI 대역. Streamlit 자체는 실행하지 않는다."""
    def __init__(self, month=None, week="계"):
        self.month, self.week = month, week
        self.calls, self.options, self.tables = [], {}, []

    def selectbox(self, label, options, index=0, key=None):
        self.options[label] = list(options)
        self.calls.append(("selectbox", key))
        value = (self.month or options[index]) if label == "월 선택" else self.week
        if value not in options:
            raise AssertionError(f"선택지에 없는 값: {value}")
        return value

    def dataframe(self, data, **kwargs):
        self.tables.append(data)
        assert kwargs == {"use_container_width": True, "hide_index": True}

    def expander(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.calls.append((name, args))


class LiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = H["live_load_data"]()
        cls.calendar = json.loads((ROOT / "weeks_2026.json").read_text(encoding="utf-8"))

    def test_python38_grammar(self):
        ast.parse((ROOT / "streamlit_app.py").read_text(encoding="utf-8"), feature_version=(3, 8))

    def test_august_calendar(self):
        self.assertEqual(H["live_weeks_for_month"](self.calendar, "8월"),
                         ["계", "W35A", "W34", "W33", "W32", "W31B"])

    def test_september_calendar(self):
        weeks = H["live_weeks_for_month"](self.calendar, "9월")
        self.assertEqual(weeks, ["계", "W39", "W38", "W37", "W36", "W35B"])

    def test_every_month_total_first_descending_unique(self):
        for month in range(1, 13):
            weeks = H["live_weeks_for_month"](self.calendar, f"{month}월")
            self.assertEqual(weeks[0], "계")
            self.assertEqual(weeks[1:], sorted(set(weeks[1:]), key=H["live_week_sort_key"], reverse=True))

    def test_numeric_and_suffix_sort(self):
        self.assertEqual(sorted(["W2", "W10", "W9", "W36A", "W36B"],
                                key=H["live_week_sort_key"], reverse=True),
                         ["W36B", "W36A", "W10", "W9", "W2"])

    def test_pre_split_calendar_keys(self):
        calendar = {"W35A": {"month": [8, 9]}, "W35B": {"month": [8, 9]},
                    "W53B": {"month": [12]}}
        self.assertEqual(H["live_weeks_for_month"](calendar, "8월"), ["계", "W35A"])
        self.assertEqual(H["live_weeks_for_month"](calendar, "9월"), ["계", "W35B"])
        self.assertEqual(H["live_weeks_for_month"](calendar, "12월"), ["계", "W53B"])

    def test_missing_calendar(self):
        self.assertEqual(H["live_weeks_for_month"]({}, "8월"), ["계"])

    def test_invalid_calendar(self):
        with self.assertRaises(ValueError):
            H["live_weeks_for_month"]({"W35": {"month": [8, 13]}}, "8월")

    def test_month_total_is_not_all_weeks(self):
        july, _ = H["live_select_period"](self.data, self.calendar, "7월", "계")
        self.assertEqual(july["평강"]["방송매출"], 5944932440)
        self.assertNotEqual(july, self.data["주차별"]["계"])

    def test_cross_month_week_not_visible(self):
        result, _ = H["live_select_period"](self.data, self.calendar, "7월", "W32")
        self.assertEqual(result, {})

    def test_future_month_is_missing_not_zero(self):
        result, _ = H["live_select_period"](self.data, self.calendar, "12월", "계")
        self.assertEqual(result, {})

    def test_unprovided_week_is_missing(self):
        result, _ = H["live_select_period"](self.data, self.calendar, "7월", "W27")
        self.assertEqual(result, {})

    def test_missing_month_uses_labeled_partial_weeks(self):
        data = copy.deepcopy(self.data)
        del data["월별"]["8월"]
        result, note = H["live_select_period"](data, self.calendar, "8월", "계")
        self.assertIn("월 마감 실적 아님", note)
        self.assertEqual(result["평강"]["방송횟수"], 252)

    def test_display_units_and_original_unchanged(self):
        data = {"평강": {"방송횟수": 1234, "방송매출": 5500000, "소요비용": 500000,
                       "마케팅활동": "방송 소재 테스트"}}
        before = copy.deepcopy(data)
        row = H["live_table_rows"](data)[1]
        self.assertEqual(row, {"거래선": "평강", "방송횟수": "1,234", "방송매출(백만)": "5.50",
                               "소요비용(백만)": "0.50", "마케팅활동": "방송 소재 테스트"})
        self.assertEqual(data, before)

    def test_zero_distinct_from_missing(self):
        rows = H["live_table_rows"]({"평강": {"방송횟수": 0, "방송매출": 0, "소요비용": None}})
        self.assertEqual(rows[1]["방송횟수"], "0")
        self.assertEqual(rows[1]["방송매출(백만)"], "0.00")
        self.assertEqual(rows[1]["소요비용(백만)"], "미제공")
        self.assertEqual(rows[2]["방송횟수"], "미제공")
        self.assertEqual(rows[0]["방송횟수"], "미제공")

    def test_eight_rows_and_five_columns(self):
        rows = H["live_table_rows"](self.data["월별"]["8월"])
        self.assertEqual([r["거래선"] for r in rows], ["전체"] + H["AGENCIES"])
        self.assertTrue(all(len(row) == 5 for row in rows))
        self.assertEqual(rows[0]["방송매출(백만)"], "4,187.38")

    def test_imported_data_no_period_cost_invented(self):
        for section in ("월별", "주차별"):
            for period in self.data[section].values():
                self.assertTrue(all(r["소요비용"] is None for r in period.values()))

    def test_imported_august_reconciliation(self):
        self.assertEqual(sum(r["방송횟수"] for r in self.data["월별"]["8월"].values()), 694)
        self.assertEqual(sum(r["방송매출"] for r in self.data["월별"]["8월"].values()), 4187376060)
        for agency in H["AGENCIES"]:
            for metric in ("방송횟수", "방송매출"):
                self.assertEqual(self.data["월별"]["8월"][agency][metric],
                                 self.data["주차별"]["계"][agency][metric])

    def test_unmatched_week_preserved_not_remapped(self):
        self.assertEqual(self.data["확인필요"][0]["원본주차"], "36A주")
        self.assertIn("원본데이터", self.data["확인필요"][0])
        self.assertNotIn("W36A", self.data["주차별"])
        self.assertNotIn("W36", self.data["주차별"])

    def test_recomputed_total_ignores_existing_total(self):
        data = copy.deepcopy(self.data)
        data["주차별"]["계"]["평강"]["방송매출"] = 999999999999
        result = H["live_validate_data"](data)
        self.assertEqual(result["주차별"]["계"]["평강"]["방송매출"], 1241996400)
        self.assertEqual(data["주차별"]["계"]["평강"]["방송매출"], 999999999999)

    def test_invalid_record_values(self):
        for value in (True, -1, "100", float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                H["live_validate_data"]({"월별": {"8월": {"평강": {"방송매출": value}}}})

    def test_invalid_record_shape(self):
        for data in ([], {"월별": []}, {"월별": {"13월": {}}},
                     {"주차별": {"W99": {}}}, {"월별": {"8월": {"없는거래선": {}}}},
                     {"월별": {"8월": {"평강": {"방송횟수": 1.5}}}},
                     {"월별": {"8월": {"평강": {"마케팅활동": 123}}}}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                H["live_validate_data"](data)

    def test_empty_schema(self):
        self.assertEqual(H["live_validate_data"]({}), {"월별": {}, "주차별": {"계": {}}})

    def test_wrong_unit_year_or_schema_rejected(self):
        for data in ({"금액단위": "백만"}, {"기준연도": 2027}, {"schema_version": 2}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                H["live_validate_data"](data)

    def test_page_missing_data_file_still_shows_selectors(self):
        st = FakeStreamlit("8월")
        with patch.dict(H, st=st, live_load_data=lambda: (_ for _ in ()).throw(FileNotFoundError())):
            H["live_render_page"]()
        self.assertEqual(st.options["주차 선택"][0], "계")
        self.assertTrue(any(name == "warning" for name, _ in st.calls))
        self.assertFalse(st.tables)

    def test_page_missing_calendar_keeps_monthly_view(self):
        st = FakeStreamlit("8월")
        with patch.dict(H, st=st, pd=types.SimpleNamespace(DataFrame=lambda rows: rows),
                        live_load_data=lambda: self.data), patch.object(Path, "open", side_effect=FileNotFoundError()):
            H["live_render_page"]()
        self.assertEqual(st.options["주차 선택"], ["계"])
        self.assertEqual(st.tables[0][0]["방송횟수"], "694")

    def test_page_marketing_activity_remains_plain_text(self):
        data = copy.deepcopy(self.data)
        data["월별"]["8월"]["평강"]["마케팅활동"] = "<script>alert(1)</script>"
        st = FakeStreamlit("8월")
        with patch.dict(H, st=st, pd=types.SimpleNamespace(DataFrame=lambda rows: rows),
                        live_load_data=lambda: data):
            H["live_render_page"]()
        self.assertIn(("text", ("<script>alert(1)</script>",)), st.calls)

    def test_activity_aggregation_deduplicates_without_inventing(self):
        result = H["live_sum_records"]([{"마케팅활동": " A "}, {"마케팅활동": "A"}, {"마케팅활동": "B"}])
        self.assertEqual(result["마케팅활동"], "A\nB")
        self.assertIsNone(result["소요비용"])

    def test_save_load_roundtrip_and_no_auto_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "live_commerce_data.json"
            H["live_save_data"](self.data, path)
            self.assertEqual(H["live_load_data"](path), self.data)
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_invalid_save_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "live_commerce_data.json"
            H["live_save_data"](self.data, path)
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                H["live_save_data"]({"월별": []}, path)
            self.assertEqual(path.read_bytes(), original)

    def test_failed_replace_preserves_existing_and_cleans_own_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "live_commerce_data.json"
            H["live_save_data"](self.data, path)
            original = path.read_bytes()
            with patch.object(os, "replace", side_effect=OSError("test failure")), self.assertRaises(OSError):
                H["live_save_data"](self.data, path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_missing_or_corrupt_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                H["live_load_data"](path)
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(ValueError):
                H["live_load_data"](path)

    def test_page_dropdowns_table_and_warning(self):
        st = FakeStreamlit("8월", "W32")
        with patch.dict(H, st=st, pd=types.SimpleNamespace(DataFrame=lambda rows: rows)):
            H["live_render_page"]()
        self.assertEqual(st.options["월 선택"], [f"{m}월" for m in range(12, 0, -1)])
        self.assertEqual(st.options["주차 선택"], ["계", "W35A", "W34", "W33", "W32", "W31B"])
        self.assertEqual(st.tables[0][0]["방송횟수"], "227")
        self.assertEqual(st.tables[0][0]["방송매출(백만)"], "1,197.35")
        self.assertTrue(any(name == "warning" for name, _ in st.calls))

    def test_page_month_change_scopes_widget_key(self):
        for month in ("8월", "9월", "12월"):
            st = FakeStreamlit(month)
            with patch.dict(H, st=st, pd=types.SimpleNamespace(DataFrame=lambda rows: rows)):
                H["live_render_page"]()
            self.assertIn(("selectbox", f"live_week_select_{month}"), st.calls)
            if month != "8월":
                self.assertFalse(st.tables)
                self.assertTrue(any(name == "info" for name, _ in st.calls))

    def test_page_defaults_to_latest_available_month(self):
        st = FakeStreamlit()
        with patch.dict(H, st=st, pd=types.SimpleNamespace(DataFrame=lambda rows: rows)):
            H["live_render_page"]()
        self.assertEqual(st.tables[0][0]["방송횟수"], "694")

    def test_page_corrupt_data_is_visible_error(self):
        st = FakeStreamlit()
        with patch.dict(H, st=st, live_load_data=lambda: (_ for _ in ()).throw(ValueError("broken"))):
            H["live_render_page"]()
        self.assertTrue(any(name == "error" for name, _ in st.calls))
        self.assertFalse(st.tables)


if __name__ == "__main__":
    unittest.main(verbosity=2)
