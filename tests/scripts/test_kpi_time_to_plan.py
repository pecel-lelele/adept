"""Run without app dependencies: python -m unittest discover -s tests/scripts."""

import unittest

try:
    from src.scripts.kpi_time_to_plan import analyse, template
except ModuleNotFoundError:
    from scripts.kpi_time_to_plan import analyse, template


class PlanningKpiTests(unittest.TestCase):
    def test_unrun_template_is_not_an_achievement(self) -> None:
        report = analyse(template())
        self.assertIsNone(report["paired_median_reduction_percent"])
        self.assertEqual(report["paired_valid_n"], 0)
        self.assertFalse(report["all_pairs_valid"])

    def test_matched_medians_and_valid_share(self) -> None:
        rows = template()
        for row in rows:
            row.update(status="completed", valid=True)
            row["elapsed_seconds"] = 600 if row["workflow"] == "manual" else 420
        report = analyse(rows)
        self.assertEqual(report["paired_valid_n"], 15)
        self.assertEqual(report["paired_median_reduction_percent"], 30)
        self.assertTrue(report["all_pairs_valid"])

    def test_failures_count_and_pairs_use_same_cases(self) -> None:
        rows = template()[:4]
        for row in rows:
            row.update(status="completed", valid=True, elapsed_seconds=600)
        rows[1].update(status="failed", valid=False, elapsed_seconds=60)
        rows[3]["elapsed_seconds"] = 300
        report = analyse(rows)
        self.assertEqual(report["paired_valid_n"], 1)
        self.assertEqual(report["paired_median_reduction_percent"], 50)
        self.assertEqual(report["workflows"]["adept"]["valid_plan_percent"], 50)
        self.assertEqual(report["missing_records"], 26)

    def test_rejects_invalid_and_duplicate_records(self) -> None:
        for elapsed in (0, -1, float("nan"), float("inf"), True, "20"):
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                row = template()[0]
                row.update(status="completed", elapsed_seconds=elapsed)
                analyse([row])
        with self.assertRaises(ValueError):
            analyse([template()[0], template()[0]])
        with self.assertRaises(ValueError):
            analyse([{**template()[0], "valid": True}])

    def test_empty_has_no_baseline(self) -> None:
        self.assertIsNone(analyse([])["paired_median_reduction_percent"])


if __name__ == "__main__":
    unittest.main()
