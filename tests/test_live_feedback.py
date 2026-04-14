import unittest

from agentic_camera_calibration.capture import _summarize_live_feedback
from agentic_camera_calibration.models import DetectionResult, QualityMetrics


class LiveFeedbackTests(unittest.TestCase):
    def test_summary_marks_clean_frame_usable(self) -> None:
        detection = DetectionResult(
            frame_id="preview",
            detection_success=True,
            markers_detected=15,
            charuco_corners_detected=18,
            coverage_score=0.48,
        )
        quality = QualityMetrics(
            frame_id="preview",
            mean_brightness=120.0,
            contrast_score=40.0,
            blur_score=180.0,
            saturation_ratio=0.02,
            glare_score=0.03,
            usable=True,
            reasons=[],
        )

        label, _, reason = _summarize_live_feedback(detection, quality)
        self.assertEqual(label, "USABLE")
        self.assertEqual(reason, "Good frame for capture.")

    def test_summary_marks_multiple_issues_poor(self) -> None:
        detection = DetectionResult(
            frame_id="preview",
            detection_success=False,
            markers_detected=2,
            charuco_corners_detected=3,
            coverage_score=0.10,
        )
        quality = QualityMetrics(
            frame_id="preview",
            mean_brightness=15.0,
            contrast_score=8.0,
            blur_score=10.0,
            saturation_ratio=0.22,
            glare_score=0.42,
            usable=False,
            reasons=["low_brightness", "blur_or_low_detail", "overexposure"],
        )

        label, _, reason = _summarize_live_feedback(detection, quality)
        self.assertEqual(label, "POOR")
        self.assertIn("low_corners", reason)


if __name__ == "__main__":
    unittest.main()
