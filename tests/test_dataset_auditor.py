import unittest

from agentic_camera_calibration.config import FailureThresholds
from agentic_camera_calibration.dataset_auditor import (
    _apply_nominal_reference,
    _canonicalize_scenario,
    _classify_run,
    _derive_empirical_nominal_reference,
)


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
        "estimated_pitch_deg": 0.0,
        "estimated_yaw_deg": 0.0,
        "estimated_roll_deg": 0.0,
        "estimated_tx_mm": 0.0,
        "estimated_ty_mm": 0.0,
        "estimated_tz_mm": 300.0,
        "nominal_reference_source": "config_defaults",
        "nominal_reference_run_count": 0,
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
            setup_type="legacy_moving_target",
            initial_metrics=initial,
            all_metrics=all_frames,
            metadata_present=True,
            initial_frame_count=12,
            reserved_frame_count=6,
            required_primary_frame_count=12,
            required_reserved_frame_count=4,
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
            setup_type="legacy_moving_target",
            initial_metrics=initial,
            all_metrics=all_frames,
            metadata_present=True,
            initial_frame_count=12,
            reserved_frame_count=6,
            required_primary_frame_count=12,
            required_reserved_frame_count=4,
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
            setup_type="legacy_moving_target",
            initial_metrics=initial,
            all_metrics=all_frames,
            metadata_present=True,
            initial_frame_count=12,
            reserved_frame_count=6,
            required_primary_frame_count=12,
            required_reserved_frame_count=4,
            quality_floor_brightness=45.0,
        )
        self.assertEqual(decision["status"], "recapture")
        self.assertTrue(decision["recapture_recommended"])

    def test_fixed_target_run_with_six_plus_three_is_not_flagged_for_frame_count(self) -> None:
        initial = _base_metrics()
        all_frames = _base_metrics()
        decision = _classify_run(
            canonical_scenario="S3_pose_deviation",
            setup_type="benchmark_fixed_target",
            initial_metrics=initial,
            all_metrics=all_frames,
            metadata_present=True,
            initial_frame_count=6,
            reserved_frame_count=3,
            required_primary_frame_count=6,
            required_reserved_frame_count=3,
            quality_floor_brightness=45.0,
        )
        self.assertNotEqual(decision["status"], "recapture")
        self.assertFalse(
            any("primary frames found" in note or "reserved frames found" in note for note in decision["notes"])
        )

    def test_legacy_run_with_six_plus_three_is_still_flagged_for_frame_count(self) -> None:
        initial = _base_metrics()
        all_frames = _base_metrics()
        decision = _classify_run(
            canonical_scenario="S3_pose_deviation",
            setup_type="legacy_moving_target",
            initial_metrics=initial,
            all_metrics=all_frames,
            metadata_present=True,
            initial_frame_count=6,
            reserved_frame_count=3,
            required_primary_frame_count=12,
            required_reserved_frame_count=4,
            quality_floor_brightness=45.0,
        )
        self.assertEqual(decision["status"], "recapture")
        self.assertTrue(decision["recapture_recommended"])

    def test_empirical_nominal_reference_uses_good_s0_runs(self) -> None:
        report_a = {
            "canonical_scenario": "S0_nominal",
            "run_id": "run_01",
            "initial_metrics": {
                **_base_metrics(),
                "estimated_pitch_deg": 1.0,
                "estimated_yaw_deg": 2.0,
                "estimated_roll_deg": 3.0,
                "estimated_tx_mm": 10.0,
                "estimated_ty_mm": 0.0,
                "estimated_tz_mm": 305.0,
            },
        }
        report_b = {
            "canonical_scenario": "S0_nominal",
            "run_id": "run_02",
            "initial_metrics": {
                **_base_metrics(),
                "estimated_pitch_deg": 3.0,
                "estimated_yaw_deg": 4.0,
                "estimated_roll_deg": 5.0,
                "estimated_tx_mm": 14.0,
                "estimated_ty_mm": 2.0,
                "estimated_tz_mm": 315.0,
            },
        }

        baseline = _derive_empirical_nominal_reference([report_a, report_b])

        self.assertIsNotNone(baseline)
        self.assertEqual(baseline["source"], "empirical_s0")
        self.assertEqual(baseline["run_count"], 2)
        self.assertEqual(baseline["run_ids"], ["run_01", "run_02"])
        self.assertEqual(baseline["pitch_deg"], 2.0)
        self.assertEqual(baseline["yaw_deg"], 3.0)
        self.assertEqual(baseline["roll_deg"], 4.0)
        self.assertEqual(baseline["tx_mm"], 12.0)
        self.assertEqual(baseline["ty_mm"], 1.0)
        self.assertEqual(baseline["tz_mm"], 310.0)

    def test_apply_nominal_reference_recomputes_pose_delta_and_reason_codes(self) -> None:
        metrics = {
            **_base_metrics(),
            "reason_codes": ["low_marker_coverage", "pose_out_of_range"],
            "estimated_pitch_deg": 4.0,
            "estimated_yaw_deg": 2.0,
            "estimated_roll_deg": 1.0,
            "estimated_tx_mm": 12.0,
            "estimated_ty_mm": 0.0,
            "estimated_tz_mm": 321.0,
        }
        baseline = {
            "source": "empirical_s0",
            "run_count": 3,
            "run_ids": ["run_01", "run_02", "run_03"],
            "pitch_deg": 1.0,
            "yaw_deg": 2.0,
            "roll_deg": 1.0,
            "tx_mm": 12.0,
            "ty_mm": 0.0,
            "tz_mm": 300.0,
            "derived_from": "test",
        }

        updated = _apply_nominal_reference(metrics, baseline, FailureThresholds())

        self.assertEqual(updated["nominal_reference_source"], "empirical_s0")
        self.assertEqual(updated["nominal_reference_run_count"], 3)
        self.assertEqual(updated["pitch_deg"], 3.0)
        self.assertEqual(updated["yaw_deg"], 0.0)
        self.assertEqual(updated["roll_deg"], 0.0)
        self.assertEqual(updated["tx_mm"], 0.0)
        self.assertEqual(updated["ty_mm"], 0.0)
        self.assertEqual(updated["tz_mm"], 21.0)
        self.assertFalse(updated["deviation_within_nominal_bounds"])
        self.assertIn("pose_out_of_range", updated["reason_codes"])
        self.assertIn("low_marker_coverage", updated["reason_codes"])


if __name__ == "__main__":
    unittest.main()
