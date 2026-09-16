import json
from pathlib import Path
import unittest
from executive_report import (
    AGENCIES, load_star_xlsx, report_rows, render_month_week_analysis,
    render_product_performance, star_approved_sop_totals, star_overall_totals,
    star_partner_totals, star_partner_yoy_totals, strict_sum, weeks_for_month,
)

ROOT = Path(__file__).resolve().parent


class UI:
    def __init__(self, month, week="월간"):
        self.month, self.week, self.metrics, self.charts = month, week, [], []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def columns(self, sizes): return [self] * (sizes if isinstance(sizes, int) else len(sizes))
    def selectbox(self, label, *args, **kwargs):
        if label == "대상 주차":
            return self.week
        if label == "거래선 선택":
            return "평강"
        if label == "품목":
            return "전체"
        return self.month
    def metric(self, *args, **kwargs): self.metrics.append(args)
    def radio(self, label, options, **kwargs): return options[0]
    def bar_chart(self, data, **kwargs): self.charts.append(data)
    def line_chart(self, data, **kwargs): self.charts.append(data)
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

    def test_august_month_report(self):
        ui = UI("8월")
        render_month_week_analysis(ui, ROOT)
        self.assertEqual(ui.metrics[0][1], "42")
        self.assertEqual(ui.metrics[1][1], "1")
        self.assertEqual(ui.metrics[2][1], "△213")
        self.assertEqual(ui.metrics[3][1], "640")
        self.assertEqual(ui.metrics[4][1], "410")
        self.assertTrue(ui.charts)

    def test_empty_december(self):
        ui = UI("12월")
        render_month_week_analysis(ui, ROOT)
        self.assertTrue(all(value == "미제공" for _, value in ui.metrics[:2]))
        # 스마트스토어 원본에는 12월 0이 실제 기재되어 있어 미제공으로 바꾸지 않는다.
        self.assertEqual(ui.metrics[2][1], "0")
        self.assertTrue(ui.charts)

    def test_all_months_render(self):
        for month in range(1, 13):
            with self.subTest(month=month):
                render_month_week_analysis(UI(f"{month}월"), ROOT)

    def test_week_month_mapping(self):
        calendar = json.loads((ROOT / "weeks_2026.json").read_text(encoding="utf-8"))
        self.assertEqual(weeks_for_month(calendar, "8월")[:2], ["W35A", "W34"])

    def test_weekly_report(self):
        ui = UI("8월", "W32")
        render_month_week_analysis(ui, ROOT)
        self.assertEqual(ui.metrics[0][1], "12")

    def test_product_report(self):
        ui = UI("8월")
        render_product_performance(ui, ROOT)
        self.assertGreaterEqual(len(ui.charts), 2)

    def test_star_partner_exposure_is_limited_to_approved_seven(self):
        star, errors = load_star_xlsx(ROOT)
        self.assertFalse(errors)
        exposed = set()
        for bucket in star["금액"]["월별"].values():
            for status in ("실적", "FCST"):
                exposed.update(bucket[status].get("partner", {}))
        self.assertEqual(exposed, set(AGENCIES))
        self.assertNotIn("유니씨앤씨", exposed)
        self.assertNotIn("(주)클릭나라", exposed)
        self.assertIn("클릭나라", exposed)

    def test_star_product_total_keeps_full_population(self):
        star, _ = load_star_xlsx(ROOT)
        overall = star_overall_totals(star, "월별", "8월")
        approved_so = star_approved_sop_totals(star, "월별", "8월")["S/O_금액"]
        self.assertGreater(overall["S/O_금액"], approved_so)
        self.assertAlmostEqual(overall["S/O_금액"], 40968971651.30801, places=2)

    def test_star_2025_partner_comparison_is_available(self):
        star, _ = load_star_xlsx(ROOT)
        previous = star_partner_yoy_totals(star, "월별", "8월", "평강")
        self.assertNotEqual(previous["S/I_금액"], 0)
        self.assertNotEqual(previous["S/O_금액"], 0)

if __name__ == "__main__":
    unittest.main()
