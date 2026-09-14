"""경영 보고 화면의 단위·기호·활동·제언 규칙 회귀 테스트."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from executive_report import (
    fmt_delta, load_historical_activities, load_star_xlsx, read_json,
    render_month_week_analysis, report_rows, tailored_sop_actions,
    affiliate_period_data, weeks_for_month,
)
from partner_views import load_activity_history
from test_executive import UI


ROOT = Path(__file__).resolve().parents[1]


class ReportingRulesTests(unittest.TestCase):
    def test_monthly_cards_use_억원_and_integer_values(self):
        ui = UI("8월", "월간")
        render_month_week_analysis(ui, ROOT)
        self.assertEqual(ui.metrics[:5], [
            ("라이브커머스 매출(억원)", "42"),
            ("어필리에이트 주문금액(억원)", "1"),
            ("스마트스토어 누적 관심고객(명)", "1,003,588"),
            ("셀인 실적(억원)", "640"),
            ("셀아웃 실적(억원)", "410"),
        ])
        self.assertTrue(all("." not in value for _, value in ui.metrics[:5]))

    def test_change_signs_are_plus_and_triangle(self):
        self.assertEqual(fmt_delta(1234, "명"), "+1,234명")
        self.assertEqual(fmt_delta(-1234, "명"), "△1,234명")
        self.assertEqual(fmt_delta(1.26, "%", 1), "+1.3%")
        self.assertEqual(fmt_delta(-1.26, "%", 1), "△1.3%")

    def test_star_failure_keeps_sellin_sellout_cards(self):
        ui = UI("8월", "월간")
        with patch("executive_report.load_star_xlsx", return_value=({}, ["STAR 읽기 오류"])):
            render_month_week_analysis(ui, ROOT)
        self.assertEqual(ui.metrics[3], ("셀인 실적", "미제공"))
        self.assertEqual(ui.metrics[4], ("셀아웃 실적", "미제공"))

    def test_normalized_activity_history_has_all_partner_weeks(self):
        records = load_activity_history(ROOT)
        self.assertEqual(len(records), 241)
        self.assertEqual(set(row["거래선"] for row in records),
                         {"평강", "문성", "케이디엘", "하나로", "회산", "현성", "클릭나라"})
        self.assertTrue(any(row["주차"] == "W35" and row["거래선"] == "평강" for row in records))
        self.assertEqual(len(load_historical_activities(ROOT)), 241)

    def test_activity_override_is_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shutil.copy(ROOT / "activity_history.json", target / "activity_history.json")
            (target / "activity_overrides.json").write_text(
                json.dumps({"edits": {"평강|W01": {"주요활동": "수정 확인", "수정일시": "2026-09-14 16:00"}},
                            "deleted": []}, ensure_ascii=False), encoding="utf-8")
            row = next(item for item in load_activity_history(target)
                       if item["거래선"] == "평강" and item["주차"] == "W01")
            self.assertEqual(row["주요활동"], "수정 확인")
            self.assertIn("수정일시", row)

    def test_tailored_actions_use_actual_activity_and_are_not_uniform(self):
        errors = []
        live = read_json(ROOT, "live_commerce_data.json", errors)
        affiliate = read_json(ROOT, "affiliate_data.json", errors)
        smart = read_json(ROOT, "smartstore_data.json", errors)
        calendar = read_json(ROOT, "weeks_2026.json", errors)
        weekly = read_json(ROOT, "weekly_data.json", errors, []) + load_historical_activities(ROOT)
        star, star_errors = load_star_xlsx(ROOT)
        self.assertFalse(errors + star_errors)

        def rows(month):
            return report_rows(live.get("월별", {}).get(month, {}),
                               affiliate_period_data(affiliate, calendar, month, "월간"),
                               smart.get("신규관심고객", {}).get("월별", {}).get(month, {}))

        result = tailored_sop_actions(
            star, "월별", "8월", "7월", rows("8월"), rows("7월"), weekly,
            set(weeks_for_month(calendar, "8월")), True)
        self.assertEqual(len(result), 7)
        self.assertGreaterEqual(len(set(row["차월 실행 제안"] for row in result)), 5)
        self.assertTrue(all("활동 기록 미연결" not in row["활동 근거"] for row in result))
        self.assertTrue(all(row["확인 KPI"] for row in result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
