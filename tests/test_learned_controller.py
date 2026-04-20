import unittest

from agentic_camera_calibration.config import ControllerConfig
from agentic_camera_calibration.controllers.learned_controller import LearnedController
from agentic_camera_calibration.models import ControllerState


class LearnedControllerTests(unittest.TestCase):
    def test_selects_edge_and_tilt_for_partial_visibility(self) -> None:
        controller = LearnedController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S5_partial_visibility_fixed",
            retry_index=0,
            frames_total=16,
            frames_active=12,
            frames_reserved_remaining=6,
            mean_brightness=100.0,
            mean_saturation_ratio=0.03,
            mean_blur_score=72.0,
            mean_glare_score=0.03,
            mean_marker_count=5.0,
            mean_charuco_corner_count=8.0,
            mean_coverage_score=0.16,
            calibration_success=False,
            reprojection_error=2.5,
            deviation_result=None,
            reason_codes=["partial_visibility", "low_marker_coverage", "low_corner_count"],
            attempted_actions=[],
            allowed_actions=ControllerConfig().allowed_actions,
        )

        decision = controller.decide(state)
        self.assertFalse(decision.declare_unrecoverable)
        patterns = [
            action.get("params", {}).get("pattern")
            for action in decision.actions
            if action["action"] == "request_additional_views"
        ]
        self.assertIn("edge_and_tilt", patterns)

    def test_selects_filtered_subset_for_high_reprojection(self) -> None:
        controller = LearnedController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S3_pose_deviation_fixed",
            retry_index=0,
            frames_total=16,
            frames_active=12,
            frames_reserved_remaining=4,
            mean_brightness=120.0,
            mean_saturation_ratio=0.02,
            mean_blur_score=90.0,
            mean_glare_score=0.02,
            mean_marker_count=12.0,
            mean_charuco_corner_count=15.0,
            mean_coverage_score=0.42,
            calibration_success=False,
            reprojection_error=3.4,
            deviation_result=None,
            reason_codes=["high_reprojection_error", "pose_out_of_range"],
            attempted_actions=[],
            allowed_actions=ControllerConfig().allowed_actions,
        )

        decision = controller.decide(state)
        action_names = [action["action"] for action in decision.actions]
        self.assertIn("retry_with_filtered_subset", action_names)

    def test_declares_unrecoverable_on_repeated_signature(self) -> None:
        controller = LearnedController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S2_low_light_fixed",
            retry_index=2,
            frames_total=12,
            frames_active=8,
            frames_reserved_remaining=0,
            mean_brightness=20.0,
            mean_saturation_ratio=0.01,
            mean_blur_score=35.0,
            mean_glare_score=0.05,
            mean_marker_count=4.0,
            mean_charuco_corner_count=6.0,
            mean_coverage_score=0.12,
            calibration_success=False,
            reprojection_error=3.2,
            deviation_result=None,
            reason_codes=["low_light", "low_corner_count", "low_marker_coverage"],
            attempted_actions=[
                {"reason_codes": ["low_light", "low_corner_count", "low_marker_coverage"]},
                {"reason_codes": ["low_light", "low_corner_count", "low_marker_coverage"]},
            ],
            allowed_actions=ControllerConfig().allowed_actions,
        )

        decision = controller.decide(state)
        self.assertTrue(decision.declare_unrecoverable)
        self.assertEqual(decision.actions, [])


if __name__ == "__main__":
    unittest.main()
