from __future__ import annotations

from statistics import mean

from .config import FailureThresholds, QualityThresholds
from .models import CalibrationResult, DeviationResult, DetectionResult, FailureEvaluation, QualityMetrics


class FailureDetector:
    def __init__(self, failure_thresholds: FailureThresholds, quality_thresholds: QualityThresholds) -> None:
        self.failure_thresholds = failure_thresholds
        self.quality_thresholds = quality_thresholds

    def evaluate(
        self,
        calibration_result: CalibrationResult,
        deviation_result: DeviationResult | None,
        quality_metrics: list[QualityMetrics],
        detections: list[DetectionResult],
    ) -> FailureEvaluation:
        reason_codes: list[str] = []

        if not calibration_result.success:
            reason_codes.extend(calibration_result.failure_reasons or ["calibration_failed"])

        if (
            calibration_result.reprojection_error is not None
            and calibration_result.reprojection_error > self.failure_thresholds.max_reprojection_error
        ):
            reason_codes.append("high_reprojection_error")

        usable_frames = sum(1 for metric in quality_metrics if metric.usable)
        if usable_frames < self.failure_thresholds.min_usable_frames:
            reason_codes.append("insufficient_usable_frames")

        if quality_metrics:
            mean_saturation = mean(metric.saturation_ratio for metric in quality_metrics)
            mean_brightness = mean(metric.mean_brightness for metric in quality_metrics)
            mean_blur = mean(metric.blur_score for metric in quality_metrics)
            mean_glare = mean(metric.glare_score for metric in quality_metrics)

            if mean_saturation > self.quality_thresholds.max_saturation_ratio:
                reason_codes.append("overexposure")
            if mean_brightness < self.quality_thresholds.min_brightness:
                reason_codes.append("low_light")
            if mean_blur < self.quality_thresholds.min_blur_score:
                reason_codes.append("blur_or_low_detail")
            if mean_glare > self.quality_thresholds.max_glare_score:
                reason_codes.append("glare")

        successful_detections = [item for item in detections if item.detection_success]
        if successful_detections:
            mean_corners = mean(item.charuco_corners_detected for item in successful_detections)
            mean_coverage = mean(item.coverage_score for item in successful_detections)
        else:
            mean_corners = 0.0
            mean_coverage = 0.0

        if mean_corners < self.failure_thresholds.min_charuco_corners:
            reason_codes.append("low_corner_count")
        if mean_coverage < self.failure_thresholds.min_coverage_score:
            reason_codes.append("low_marker_coverage")
        if not successful_detections:
            reason_codes.append("partial_visibility")

        if deviation_result is not None and not deviation_result.within_nominal_bounds:
            reason_codes.append("pose_out_of_range")

        unique_reason_codes = list(dict.fromkeys(reason_codes))
        if not unique_reason_codes:
            return FailureEvaluation(status="pass", reason_codes=[], confidence=0.95)

        confidence = min(0.95, 0.35 + len(unique_reason_codes) * 0.08)
        return FailureEvaluation(
            status="intervene",
            reason_codes=unique_reason_codes,
            confidence=confidence,
        )
