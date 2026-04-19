import unittest

from agentic_camera_calibration.config import ControllerConfig
from agentic_camera_calibration.controllers.heuristic_controller import HeuristicController
from agentic_camera_calibration.models import ControllerState


class HeuristicControllerTests(unittest.TestCase):
    def test_prefers_evidence_improvement_before_pose_relaxation(self) -> None:
        controller = HeuristicController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S1_overexposed",
            retry_index=0,
            frames_total=16,
            frames_active=12,
            frames_reserved_remaining=4,
            mean_brightness=220.0,
            mean_saturation_ratio=0.21,
            mean_blur_score=70.0,
            mean_glare_score=0.3,
            mean_marker_count=9.0,
            mean_charuco_corner_count=10.0,
            mean_coverage_score=0.25,
            calibration_success=False,
            reprojection_error=2.8,
            deviation_result=None,
            reason_codes=["overexposure", "low_corner_count", "low_marker_coverage"],
            attempted_actions=[],
            allowed_actions=ControllerConfig().allowed_actions,
        )

        decision = controller.decide(state)
        action_names = [action["action"] for action in decision.actions]
        self.assertIn("reject_bad_frames", action_names)
        self.assertIn("request_additional_views", action_names)
        self.assertNotIn("relax_nominal_prior", action_names)

    def test_declares_unrecoverable_on_repeated_same_failure(self) -> None:
        controller = HeuristicController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S5_partial_visibility",
            retry_index=2,
            frames_total=12,
            frames_active=8,
            frames_reserved_remaining=0,
            mean_brightness=80.0,
            mean_saturation_ratio=0.01,
            mean_blur_score=80.0,
            mean_glare_score=0.02,
            mean_marker_count=4.0,
            mean_charuco_corner_count=6.0,
            mean_coverage_score=0.1,
            calibration_success=False,
            reprojection_error=3.0,
            deviation_result=None,
            reason_codes=["low_corner_count", "low_marker_coverage"],
            attempted_actions=[
                {"reason_codes": ["low_corner_count", "low_marker_coverage"]},
                {"reason_codes": ["low_corner_count", "low_marker_coverage"]},
            ],
            allowed_actions=ControllerConfig().allowed_actions,
        )

        decision = controller.decide(state)
        self.assertTrue(decision.declare_unrecoverable)
        self.assertEqual(decision.actions, [])


    def test_overexposure_with_low_corner_count_adds_clahe(self) -> None:
        controller = HeuristicController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S1_overexposed",
            retry_index=0,
            frames_total=16,
            frames_active=12,
            frames_reserved_remaining=0,
            mean_brightness=230.0,
            mean_saturation_ratio=0.22,
            mean_blur_score=65.0,
            mean_glare_score=0.05,
            mean_marker_count=7.0,
            mean_charuco_corner_count=9.0,
            mean_coverage_score=0.4,
            calibration_success=False,
            reprojection_error=1.8,
            deviation_result=None,
            reason_codes=["overexposure", "low_corner_count"],
            attempted_actions=[],
            allowed_actions=ControllerConfig().allowed_actions,
        )

        decision = controller.decide(state)
        action_names = [action["action"] for action in decision.actions]
        self.assertIn("apply_preprocessing", action_names)
        clahe_actions = [a for a in decision.actions if a["action"] == "apply_preprocessing" and a.get("params", {}).get("mode") == "clahe"]
        self.assertTrue(clahe_actions, "Expected apply_preprocessing with mode=clahe")

    def test_partial_visibility_with_low_coverage_uses_edge_and_tilt(self) -> None:
        controller = HeuristicController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S5_partial_visibility",
            retry_index=0,
            frames_total=16,
            frames_active=12,
            frames_reserved_remaining=6,
            mean_brightness=100.0,
            mean_saturation_ratio=0.05,
            mean_blur_score=70.0,
            mean_glare_score=0.04,
            mean_marker_count=5.0,
            mean_charuco_corner_count=8.0,
            mean_coverage_score=0.2,
            calibration_success=False,
            reprojection_error=None,
            deviation_result=None,
            reason_codes=["partial_visibility", "low_marker_coverage"],
            attempted_actions=[],
            allowed_actions=ControllerConfig().allowed_actions,
        )

        decision = controller.decide(state)
        edge_tilt_actions = [
            a for a in decision.actions
            if a["action"] == "request_additional_views"
            and a.get("params", {}).get("pattern") == "edge_and_tilt"
        ]
        self.assertTrue(edge_tilt_actions, "Expected request_additional_views with pattern=edge_and_tilt")

    def test_pose_out_of_range_with_overexposure_does_not_relax_prior(self) -> None:
        controller = HeuristicController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S1_overexposed",
            retry_index=0,
            frames_total=16,
            frames_active=12,
            frames_reserved_remaining=4,
            mean_brightness=228.0,
            mean_saturation_ratio=0.20,
            mean_blur_score=72.0,
            mean_glare_score=0.05,
            mean_marker_count=11.0,
            mean_charuco_corner_count=14.0,
            mean_coverage_score=0.45,
            calibration_success=True,
            reprojection_error=1.5,
            deviation_result=None,
            reason_codes=["overexposure", "pose_out_of_range"],
            attempted_actions=[],
            allowed_actions=ControllerConfig().allowed_actions,
        )

        decision = controller.decide(state)
        action_names = [action["action"] for action in decision.actions]
        self.assertNotIn("relax_nominal_prior", action_names)


if __name__ == "__main__":
    unittest.main()
