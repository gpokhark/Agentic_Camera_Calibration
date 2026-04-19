from __future__ import annotations

import unittest

from agentic_camera_calibration.evaluator import Evaluator
from agentic_camera_calibration.models import CalibrationResult, ExperimentRunResult


def _result(run_id: str, mode: str, status: str, scenario: str = "S0_nominal", reprojection_error: float | None = None, retry_index: int = 0) -> ExperimentRunResult:
    calibration = CalibrationResult(
        success=status == "success",
        reprojection_error=reprojection_error,
        camera_matrix=None,
        distortion_coeffs=None,
        valid_frames_used=10,
        rejected_frames=2,
    )
    return ExperimentRunResult(
        mode=mode,
        status=status,
        run_id=run_id,
        scenario=scenario,
        retry_index=retry_index,
        calibration_result=calibration,
    )


class ComputePaperMetricsTests(unittest.TestCase):
    def test_recovery_rate_counts_baseline_failures_recovered_by_controller(self) -> None:
        results = [
            _result("run_01", "baseline", "failed"),
            _result("run_01", "heuristic", "success"),
            _result("run_02", "baseline", "failed"),
            _result("run_02", "heuristic", "failed"),
        ]
        metrics = Evaluator().compute_paper_metrics(results)
        # 1 recovered out of 2 baseline failures
        self.assertAlmostEqual(metrics["recovery_rate"], 0.5)

    def test_false_reject_rate_counts_baseline_successes_failed_by_controller(self) -> None:
        results = [
            _result("run_01", "baseline", "success"),
            _result("run_01", "heuristic", "failed"),
            _result("run_02", "baseline", "success"),
            _result("run_02", "heuristic", "success"),
        ]
        metrics = Evaluator().compute_paper_metrics(results)
        # 1 false reject out of 2 baseline successes
        self.assertAlmostEqual(metrics["false_reject_rate"], 0.5)

    def test_returns_none_rates_when_no_applicable_runs(self) -> None:
        results = [_result("run_01", "baseline", "success")]
        metrics = Evaluator().compute_paper_metrics(results)
        self.assertIsNone(metrics["false_reject_rate"] if metrics["false_reject_denominator"] == 0 else None)
        self.assertIsNone(metrics["recovery_rate"])


class SummarizeByScenarioTests(unittest.TestCase):
    def test_groups_by_scenario_and_mode(self) -> None:
        results = [
            _result("run_01", "baseline", "success", scenario="S0_nominal", reprojection_error=0.5),
            _result("run_01", "heuristic", "success", scenario="S0_nominal", reprojection_error=0.6),
            _result("run_02", "baseline", "failed", scenario="S1_overexposed"),
            _result("run_02", "heuristic", "success", scenario="S1_overexposed", reprojection_error=1.2),
        ]
        breakdown = Evaluator().summarize_by_scenario(results)
        self.assertIn("S0_nominal", breakdown)
        self.assertIn("S1_overexposed", breakdown)
        self.assertAlmostEqual(breakdown["S0_nominal"]["baseline"]["success_rate"], 1.0)
        self.assertAlmostEqual(breakdown["S1_overexposed"]["baseline"]["success_rate"], 0.0)
        self.assertAlmostEqual(breakdown["S1_overexposed"]["heuristic"]["success_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
