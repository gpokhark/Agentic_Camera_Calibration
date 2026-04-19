from __future__ import annotations

import unittest

from agentic_camera_calibration.config import CalibrationConfig, NominalPoseConfig
from agentic_camera_calibration.nominal_reference import (
    default_nominal_reference,
    is_eligible_nominal_reference,
    nominal_reference_to_config,
)


def _good_metrics() -> dict:
    return {
        "calibration_success": True,
        "usable_rate": 0.85,
        "detection_success_rate": 0.90,
        "mean_charuco_corners": 15.0,
        "reprojection_error": 0.45,
        "reason_codes": [],
        "estimated_pitch_deg": 2.5,
        "estimated_yaw_deg": -1.2,
        "estimated_roll_deg": 0.3,
        "estimated_tx_mm": 5.0,
        "estimated_ty_mm": -3.0,
        "estimated_tz_mm": 295.0,
    }


class IsEligibleNominalReferenceTests(unittest.TestCase):
    def test_good_metrics_are_eligible(self) -> None:
        self.assertTrue(is_eligible_nominal_reference(_good_metrics()))

    def test_calibration_failure_is_ineligible(self) -> None:
        m = _good_metrics()
        m["calibration_success"] = False
        self.assertFalse(is_eligible_nominal_reference(m))

    def test_low_usable_rate_is_ineligible(self) -> None:
        m = _good_metrics()
        m["usable_rate"] = 0.70
        self.assertFalse(is_eligible_nominal_reference(m))

    def test_high_reprojection_error_is_ineligible(self) -> None:
        m = _good_metrics()
        m["reprojection_error"] = 1.05
        self.assertFalse(is_eligible_nominal_reference(m))

    def test_none_reprojection_error_is_ineligible(self) -> None:
        m = _good_metrics()
        m["reprojection_error"] = None
        self.assertFalse(is_eligible_nominal_reference(m))

    def test_low_charuco_corners_is_ineligible(self) -> None:
        m = _good_metrics()
        m["mean_charuco_corners"] = 11.5
        self.assertFalse(is_eligible_nominal_reference(m))

    def test_lighting_failure_code_is_ineligible(self) -> None:
        m = _good_metrics()
        m["reason_codes"] = ["low_light"]
        self.assertFalse(is_eligible_nominal_reference(m))

    def test_overexposure_failure_code_is_ineligible(self) -> None:
        m = _good_metrics()
        m["reason_codes"] = ["overexposure"]
        self.assertFalse(is_eligible_nominal_reference(m))

    def test_none_pose_field_is_ineligible(self) -> None:
        m = _good_metrics()
        m["estimated_pitch_deg"] = None
        self.assertFalse(is_eligible_nominal_reference(m))


class DefaultNominalReferenceTests(unittest.TestCase):
    def test_source_is_config_defaults(self) -> None:
        config = CalibrationConfig()
        ref = default_nominal_reference(config)
        self.assertEqual(ref["source"], "config_defaults")
        self.assertEqual(ref["run_count"], 0)
        self.assertEqual(ref["run_ids"], [])

    def test_values_match_config_nominal_pose(self) -> None:
        config = CalibrationConfig(
            nominal_pose=NominalPoseConfig(
                pitch_deg=1.0, yaw_deg=2.0, roll_deg=3.0,
                tx_mm=10.0, ty_mm=20.0, tz_mm=300.0,
            )
        )
        ref = default_nominal_reference(config)
        self.assertAlmostEqual(ref["pitch_deg"], 1.0)
        self.assertAlmostEqual(ref["tz_mm"], 300.0)


class NominalReferenceToConfigTests(unittest.TestCase):
    def test_converts_to_nominal_pose_config(self) -> None:
        ref = {
            "pitch_deg": 2.5,
            "yaw_deg": -1.2,
            "roll_deg": 0.3,
            "tx_mm": 5.0,
            "ty_mm": -3.0,
            "tz_mm": 295.0,
        }
        pose = nominal_reference_to_config(ref)
        self.assertIsInstance(pose, NominalPoseConfig)
        self.assertAlmostEqual(pose.pitch_deg, 2.5)
        self.assertAlmostEqual(pose.tz_mm, 295.0)

    def test_converts_all_six_fields(self) -> None:
        ref = {
            "pitch_deg": 1.1,
            "yaw_deg": 2.2,
            "roll_deg": 3.3,
            "tx_mm": 4.4,
            "ty_mm": 5.5,
            "tz_mm": 6.6,
        }
        pose = nominal_reference_to_config(ref)
        self.assertAlmostEqual(pose.yaw_deg, 2.2)
        self.assertAlmostEqual(pose.roll_deg, 3.3)
        self.assertAlmostEqual(pose.tx_mm, 4.4)
        self.assertAlmostEqual(pose.ty_mm, 5.5)


if __name__ == "__main__":
    unittest.main()
