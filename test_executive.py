import json
from pathlib import Path
import unittest
from executive_report import report_rows, strict_sum, render_executive

ROOT = Path(__file__).resolve().parent


class UI:
    def __init__(self, month):
        self.month, self.metrics, self.charts = month, [], []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def columns(self, sizes): return [self] * (sizes if isinstance(sizes, int) else len(sizes))
    def selectbox(self, *args, **kwargs): return self.month
    def metric(self, *args, **kwargs): self.metrics.append(args)
    def bar_chart(self, data, **kwargs): self.charts.append(data)
    def expander(self, *args, **kwargs): return self
    def __getattr__(self, name): return lambda *args, **kwargs: None


class Tests(unittest.TestCase):
    def test_missing_not_zero(self):
        self.assertIsNone(strict_sum([0, None]))
        self.assertEqual(strict_sum([0, 0]), 0)
        self.assertIsNone(strict_sum([True, 1]))

    def test_subtotals_not_doubled(self):
        rows = report_rows({}, {"평강": {"쇼핑커넥트": {"주문금액": 1000000},
                                      "공동구매": {"주문금액": 2000000},
                                      "계": {"주문금액": 3000000}}}, {})
        self.assertEqual(rows[0]["어필리에이트 주문금액(백만)"], 3)
        self.assertIsNone(rows[1]["어필리에이트 주문금액(백만)"])

    def test_august_report(self):
        ui = UI("8월")
        render_executive(ui, ROOT)
        self.assertEqual(ui.metrics[0][1], "4,187.38 백만원")
        self.assertEqual(ui.metrics[1][1], "미제공")
        self.assertEqual(ui.metrics[2][1], "-213 명")
        self.assertEqual(len(ui.charts[0]), 7)

    def test_empty_december(self):
        ui = UI("12월")
        render_executive(ui, ROOT)
        self.assertTrue(all(value == "미제공" for _, value in ui.metrics[:2]))
        # 스마트스토어 원본에는 12월 0이 실제 기재되어 있어 미제공으로 바꾸지 않는다.
        self.assertEqual(ui.metrics[2][1], "0 명")
        self.assertFalse(ui.charts)

    def test_all_months_render(self):
        for month in range(1, 13):
            with self.subTest(month=month):
                render_executive(UI(f"{month}월"), ROOT)

if __name__ == "__main__":
    unittest.main()
