import unittest

from agentic_camera_calibration.config import FailureThresholds, QualityThresholds
from agentic_camera_calibration.failure_detector import FailureDetector
from agentic_camera_calibration.models import CalibrationResult, DetectionResult, DeviationResult, QualityMetrics


class FailureDetectorTests(unittest.TestCase):
    def test_marks_nominal_result_as_pass(self) -> None:
        detector = FailureDetector(FailureThresholds(), QualityThresholds())
        calibration = CalibrationResult(
            success=True,
            reprojection_error=0.42,
            camera_matrix=None,
            distortion_coeffs=None,
            valid_frames_used=12,
            rejected_frames=0,
        )
        detections = [
            DetectionResult(
                frame_id=f"frame_{index}",
                detection_success=True,
                markers_detected=16,
                charuco_corners_detected=20,
                coverage_score=0.6,
            )
            for index in range(12)
        ]
        quality = [
            QualityMetrics(
                frame_id=f"frame_{index}",
                mean_brightness=120.0,
                contrast_score=40.0,
                blur_score=150.0,
                saturation_ratio=0.02,
                glare_score=0.05,
                usable=True,
            )
            for index in range(12)
        ]

        result = detector.evaluate(calibration, None, quality, detections)
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.reason_codes, [])

    def test_flags_multiple_failure_causes(self) -> None:
        detector = FailureDetector(FailureThresholds(), QualityThresholds())
        calibration = CalibrationResult(
            success=False,
            reprojection_error=3.5,
            camera_matrix=None,
            distortion_coeffs=None,
            valid_frames_used=4,
            rejected_frames=8,
            failure_reasons=["calibration_failed"],
        )
        detections = [
            DetectionResult(
                frame_id="frame_bad",
                detection_success=False,
                markers_detected=2,
                charuco_corners_detected=3,
                coverage_score=0.1,
            )
        ]
        quality = [
            QualityMetrics(
                frame_id="frame_bad",
                mean_brightness=20.0,
                contrast_score=10.0,
                blur_score=12.0,
                saturation_ratio=0.25,
                glare_score=0.5,
                usable=False,
                reasons=["low_brightness", "blur_or_low_detail"],
            )
        ]

        result = detector.evaluate(calibration, None, quality, detections)
        self.assertEqual(result.status, "intervene")
        self.assertIn("calibration_failed", result.reason_codes)
        self.assertIn("high_reprojection_error", result.reason_codes)
        self.assertIn("low_light", result.reason_codes)
        self.assertIn("low_marker_coverage", result.reason_codes)
        self.assertIn("calibration_failed", result.hard_fail_codes)

    def test_low_light_can_be_warning_when_calibration_is_still_good(self) -> None:
        detector = FailureDetector(FailureThresholds(), QualityThresholds())
        calibration = CalibrationResult(
            success=True,
            reprojection_error=0.18,
            camera_matrix=None,
            distortion_coeffs=None,
            valid_frames_used=12,
            rejected_frames=0,
        )
        detections = [
            DetectionResult(
                frame_id=f"frame_{index}",
                detection_success=True,
                markers_detected=16,
                charuco_corners_detected=22,
                coverage_score=0.42,
            )
            for index in range(12)
        ]
        quality = [
            QualityMetrics(
                frame_id=f"frame_{index}",
                mean_brightness=20.0,
                contrast_score=22.0,
                blur_score=70.0,
                saturation_ratio=0.01,
                glare_score=0.02,
                usable=False,
                reasons=["low_light"],
            )
            for index in range(12)
        ]

        result = detector.evaluate(calibration, None, quality, detections, scenario="S2_low_light")
        self.assertEqual(result.status, "pass")
        self.assertIn("low_light", result.warning_codes)
        self.assertIn("insufficient_usable_frames", result.warning_codes)
        self.assertEqual(result.hard_fail_codes, [])

    def test_pose_out_of_range_is_warning_for_pose_scenario(self) -> None:
        detector = FailureDetector(FailureThresholds(), QualityThresholds())
        calibration = CalibrationResult(
            success=True,
            reprojection_error=0.12,
            camera_matrix=None,
            distortion_coeffs=None,
            valid_frames_used=12,
            rejected_frames=0,
        )
        detections = [
            DetectionResult(
                frame_id=f"frame_{index}",
                detection_success=True,
                markers_detected=16,
                charuco_corners_detected=22,
                coverage_score=0.45,
            )
            for index in range(12)
        ]
        quality = [
            QualityMetrics(
                frame_id=f"frame_{index}",
                mean_brightness=120.0,
                contrast_score=40.0,
                blur_score=120.0,
                saturation_ratio=0.02,
                glare_score=0.02,
                usable=True,
            )
            for index in range(12)
        ]
        deviation = DeviationResult(
            pitch_deg=9.0,
            yaw_deg=1.0,
            roll_deg=0.5,
            tx_mm=2.0,
            ty_mm=1.0,
            tz_mm=15.0,
            aggregate_pose_error=17.6,
            within_nominal_bounds=False,
        )

        result = detector.evaluate(
            calibration,
            deviation,
            quality,
            detections,
            scenario="S3_pose_deviation",
        )
        self.assertEqual(result.status, "pass")
        self.assertIn("pose_out_of_range", result.warning_codes)

    def test_low_marker_coverage_can_be_warning_with_strong_geometry(self) -> None:
        detector = FailureDetector(FailureThresholds(), QualityThresholds())
        calibration = CalibrationResult(
            success=True,
            reprojection_error=0.16,
            camera_matrix=None,
            distortion_coeffs=None,
            valid_frames_used=12,
            rejected_frames=0,
        )
        detections = [
            DetectionResult(
                frame_id=f"frame_{index}",
                detection_success=True,
                markers_detected=16,
                charuco_corners_detected=24,
                coverage_score=0.22,
            )
            for index in range(12)
        ]
        quality = [
            QualityMetrics(
                frame_id=f"frame_{index}",
                mean_brightness=120.0,
                contrast_score=40.0,
                blur_score=120.0,
                saturation_ratio=0.02,
                glare_score=0.02,
                usable=True,
            )
            for index in range(12)
        ]

        result = detector.evaluate(calibration, None, quality, detections, scenario="S0_nominal")
        self.assertEqual(result.status, "pass")
        self.assertIn("low_marker_coverage", result.warning_codes)


if __name__ == "__main__":
    unittest.main()
