from __future__ import annotations

import unittest
from unittest.mock import patch

from agentic_camera_calibration.config import CalibrationConfig
from agentic_camera_calibration.experiment_runner import ExperimentRunner
from agentic_camera_calibration.models import CalibrationResult, ExperimentRunResult, FrameRecord, RunRecord


class _StubLoader:
    def __init__(self, runs: list[RunRecord]) -> None:
        self._runs = runs

    def discover_runs(self, dataset_root) -> list[RunRecord]:
        return list(self._runs)

    def split_initial_and_reserved(self, frames: list[FrameRecord]) -> tuple[list[FrameRecord], list[FrameRecord]]:
        return list(frames[:1]), list(frames[1:])


class _StubNominalEstimator:
    def __init__(self) -> None:
        self.last_runs: list[RunRecord] | None = None

    def derive_for_dataset(self, dataset_root=None, runs=None) -> dict:
        self.last_runs = list(runs or [])
        return {
            "source": "config_defaults",
            "run_count": 0,
            "run_ids": [],
            "pitch_deg": 0.0,
            "yaw_deg": 0.0,
            "roll_deg": 0.0,
            "tx_mm": 0.0,
            "ty_mm": 0.0,
            "tz_mm": 300.0,
            "derived_from": "test",
        }


class _StubReporter:
    def __init__(self) -> None:
        self.last_results: list[ExperimentRunResult] | None = None

    def write_results(self, output_dir, results, summary, paper_metrics=None, scenario_summary=None) -> None:
        self.last_results = list(results)


class _StubEvaluator:
    def summarize(self, results: list[ExperimentRunResult]) -> dict:
        return {"count": len(results)}

    def compute_paper_metrics(self, results: list[ExperimentRunResult]) -> dict:
        return {"count": len(results)}

    def summarize_by_scenario(self, results: list[ExperimentRunResult]) -> dict:
        return {"count": len(results)}


class _FakeOrchestrator:
    calls: list[tuple[str, str, str]] = []

    def __init__(self, config: CalibrationConfig) -> None:
        self.config = config

    def run(
        self,
        initial_frames: list[FrameRecord],
        reserved_frames: list[FrameRecord],
        controller,
        run_id: str,
        scenario: str,
        setup_type: str,
        dataset_split: str,
        mode_name: str,
    ) -> ExperimentRunResult:
        self.__class__.calls.append((run_id, scenario, mode_name))
        return ExperimentRunResult(
            mode=mode_name,
            status="success",
            run_id=run_id,
            scenario=scenario,
            retry_index=0,
            setup_type=setup_type,
            dataset_split=dataset_split,
            calibration_result=CalibrationResult(
                success=True,
                reprojection_error=0.5,
                camera_matrix=None,
                distortion_coeffs=None,
                valid_frames_used=len(initial_frames),
                rejected_frames=0,
            ),
        )


def _make_run(scenario: str, run_id: str) -> RunRecord:
    frames = [
        FrameRecord(frame_id="frame_001.png", scenario=scenario, run_id=run_id),
        FrameRecord(frame_id="frame_002.png", scenario=scenario, run_id=run_id, is_reserved=True),
    ]
    setup_type = "benchmark_fixed_target" if scenario.endswith("_fixed") else "pilot_moving_target"
    dataset_split = "eval" if scenario.endswith("_fixed") else "dev"
    return RunRecord(
        run_id=run_id,
        scenario=scenario,
        run_path=None,
        frames=frames,
        setup_type=setup_type,
        dataset_split=dataset_split,
    )  # type: ignore[arg-type]


class ExperimentRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = ExperimentRunner(CalibrationConfig())
        self.runner.loader = _StubLoader(
            [
                _make_run("S0_nominal", "run_01"),
                _make_run("S3_pose_deviation_fixed", "run_02"),
                _make_run("S3_pose_deviation_fixed", "run_03"),
            ]
        )
        self.runner.nominal_estimator = _StubNominalEstimator()
        self.runner.evaluator = _StubEvaluator()
        self.runner.reporter = _StubReporter()
        _FakeOrchestrator.calls = []

    def test_run_all_can_skip_agent_mode(self) -> None:
        with patch("agentic_camera_calibration.experiment_runner.CalibrationOrchestrator", _FakeOrchestrator):
            with patch("agentic_camera_calibration.experiment_runner.HeuristicController", lambda config: "heuristic-controller"):
                with patch("agentic_camera_calibration.experiment_runner.AgentController") as agent_controller_cls:
                    results = self.runner.run_all(modes=["baseline", "heuristic", "learned"])

        self.assertEqual(len(results), 9)
        self.assertEqual({result.mode for result in results}, {"baseline", "heuristic", "learned"})
        agent_controller_cls.assert_not_called()

    def test_run_all_filters_by_scenario_and_run_id(self) -> None:
        with patch("agentic_camera_calibration.experiment_runner.CalibrationOrchestrator", _FakeOrchestrator):
            with patch("agentic_camera_calibration.experiment_runner.HeuristicController", lambda config: "heuristic-controller"):
                with patch("agentic_camera_calibration.experiment_runner.AgentController", lambda config: "agent-controller"):
                    results = self.runner.run_all(
                        scenarios=["S3_pose_deviation_fixed"],
                        run_ids=["run_03"],
                        modes=["baseline"],
                    )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].scenario, "S3_pose_deviation_fixed")
        self.assertEqual(results[0].run_id, "run_03")
        self.assertEqual(_FakeOrchestrator.calls, [("run_03", "S3_pose_deviation_fixed", "baseline")])

    def test_nominal_reference_is_derived_from_full_dataset_before_filters(self) -> None:
        with patch("agentic_camera_calibration.experiment_runner.CalibrationOrchestrator", _FakeOrchestrator):
            with patch("agentic_camera_calibration.experiment_runner.HeuristicController", lambda config: "heuristic-controller"):
                with patch("agentic_camera_calibration.experiment_runner.AgentController", lambda config: "agent-controller"):
                    self.runner.run_all(scenarios=["S3_pose_deviation_fixed"], modes=["baseline"])

        assert self.runner.nominal_estimator.last_runs is not None
        self.assertEqual(len(self.runner.nominal_estimator.last_runs), 3)

    def test_run_all_raises_when_filters_match_no_runs(self) -> None:
        with self.assertRaises(ValueError):
            self.runner.run_all(scenarios=["S9_unknown"], modes=["baseline"])

    def test_run_all_filters_by_setup_type(self) -> None:
        with patch("agentic_camera_calibration.experiment_runner.CalibrationOrchestrator", _FakeOrchestrator):
            with patch("agentic_camera_calibration.experiment_runner.HeuristicController", lambda config: "heuristic-controller"):
                with patch("agentic_camera_calibration.experiment_runner.LearnedController", lambda config: "learned-controller"):
                    with patch("agentic_camera_calibration.experiment_runner.AgentController", lambda config: "agent-controller"):
                        results = self.runner.run_all(setup_types=["benchmark_fixed_target"], modes=["baseline"])

        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.setup_type == "benchmark_fixed_target" for result in results))

    def test_run_all_filters_by_dataset_split(self) -> None:
        with patch("agentic_camera_calibration.experiment_runner.CalibrationOrchestrator", _FakeOrchestrator):
            with patch("agentic_camera_calibration.experiment_runner.HeuristicController", lambda config: "heuristic-controller"):
                with patch("agentic_camera_calibration.experiment_runner.LearnedController", lambda config: "learned-controller"):
                    with patch("agentic_camera_calibration.experiment_runner.AgentController", lambda config: "agent-controller"):
                        results = self.runner.run_all(dataset_splits=["eval"], modes=["baseline"])

        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.dataset_split == "eval" for result in results))


if __name__ == "__main__":
    unittest.main()
