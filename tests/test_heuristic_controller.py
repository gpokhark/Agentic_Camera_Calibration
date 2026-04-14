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


if __name__ == "__main__":
    unittest.main()
