import unittest

from agentic_camera_calibration.dataset_auditor import _canonicalize_scenario, _classify_run


def _base_metrics() -> dict:
    return {
        "usable_rate": 1.0,
        "reprojection_error": 0.2,
        "reason_codes": [],
        "calibration_success": True,
        "detection_success_rate": 1.0,
        "mean_charuco_corners": 24.0,
        "mean_brightness": 120.0,
        "mean_saturation_ratio": 0.0,
        "mean_glare": 0.0,
        "deviation_within_nominal_bounds": False,
        "deviation_aggregate_pose_error": 6.0,
        "tz_mm": 0.0,
    }


class DatasetAuditorTests(unittest.TestCase):
    def test_canonicalize_known_aliases(self) -> None:
        self.assertEqual(_canonicalize_scenario("S3_pose_dev"), "S3_pose_deviation")
        self.assertEqual(_canonicalize_scenario("S5_occlusion"), "S5_partial_visibility")
        self.assertEqual(_canonicalize_scenario("S2_low_light"), "S2_low_light")

    def test_nominal_clean_run_is_kept(self) -> None:
        initial = _base_metrics()
        all_frames = _base_metrics()
        all_frames["reason_codes"] = ["low_marker_coverage", "pose_out_of_range"]
        decision = _classify_run(
            canonical_scenario="S0_nominal",
            initial_metrics=initial,
            all_metrics=all_frames,
            metadata_present=True,
            initial_frame_count=12,
            reserved_frame_count=6,
            quality_floor_brightness=45.0,
        )
        self.assertEqual(decision["status"], "keep_with_note")
        self.assertTrue(decision["usable_for_analysis"])
        self.assertFalse(decision["recapture_recommended"])

    def test_low_light_run_can_be_kept_when_disturbance_is_present(self) -> None:
        initial = _base_metrics()
        all_frames = _base_metrics()
        initial["usable_rate"] = 0.0
        initial["mean_brightness"] = 20.0
        initial["reason_codes"] = ["low_light", "blur_or_low_detail"]
        all_frames["mean_brightness"] = 20.0
        all_frames["reason_codes"] = ["low_light", "blur_or_low_detail"]
        decision = _classify_run(
            canonical_scenario="S2_low_light",
            initial_metrics=initial,
            all_metrics=all_frames,
            metadata_present=True,
            initial_frame_count=12,
            reserved_frame_count=6,
            quality_floor_brightness=45.0,
        )
        self.assertIn(decision["status"], {"keep", "keep_with_note"})
        self.assertTrue(decision["usable_for_analysis"])
        self.assertFalse(decision["recapture_recommended"])

    def test_overexposed_run_is_flagged_if_effect_is_weak(self) -> None:
        initial = _base_metrics()
        all_frames = _base_metrics()
        all_frames["mean_saturation_ratio"] = 0.001
        all_frames["mean_glare"] = 0.0
        decision = _classify_run(
            canonical_scenario="S1_overexposed",
            initial_metrics=initial,
            all_metrics=all_frames,
            metadata_present=True,
            initial_frame_count=12,
            reserved_frame_count=6,
            quality_floor_brightness=45.0,
        )
        self.assertEqual(decision["status"], "recapture")
        self.assertTrue(decision["recapture_recommended"])


if __name__ == "__main__":
    unittest.main()
