from __future__ import annotations

from math import atan2, degrees, sqrt

from .config import FailureThresholds, NominalPoseConfig
from .models import CalibrationResult, DeviationResult


def _require_cv2():
    try:
        import cv2  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError("OpenCV is required for deviation analysis. Run `uv sync` first.") from exc
    return cv2


class DeviationAnalyzer:
    def __init__(self, thresholds: FailureThresholds) -> None:
        self.thresholds = thresholds
        self.cv2 = _require_cv2()

    def compute_deviation(
        self,
        calibration_result: CalibrationResult,
        nominal_pose: NominalPoseConfig,
        pose_margin_scale: float = 1.0,
    ) -> DeviationResult | None:
        if calibration_result.mean_pose_rvec is None or calibration_result.mean_pose_tvec_mm is None:
            return None

        rotation_matrix, _ = self.cv2.Rodrigues(calibration_result.mean_pose_rvec)
        pitch_deg, yaw_deg, roll_deg = self._rotation_matrix_to_euler(rotation_matrix)

        tx_mm = calibration_result.mean_pose_tvec_mm[0] - nominal_pose.tx_mm
        ty_mm = calibration_result.mean_pose_tvec_mm[1] - nominal_pose.ty_mm
        tz_mm = calibration_result.mean_pose_tvec_mm[2] - nominal_pose.tz_mm

        pitch_delta = pitch_deg - nominal_pose.pitch_deg
        yaw_delta = yaw_deg - nominal_pose.yaw_deg
        roll_delta = roll_deg - nominal_pose.roll_deg

        aggregate_pose_error = sqrt(
            pitch_delta**2 + yaw_delta**2 + roll_delta**2 + tx_mm**2 + ty_mm**2 + tz_mm**2
        )

        angle_tolerance = self.thresholds.pose_angle_tolerance_deg * pose_margin_scale
        translation_tolerance = self.thresholds.pose_translation_tolerance_mm * pose_margin_scale

        within_nominal_bounds = (
            abs(pitch_delta) <= angle_tolerance
            and abs(yaw_delta) <= angle_tolerance
            and abs(roll_delta) <= angle_tolerance
            and abs(tx_mm) <= translation_tolerance
            and abs(ty_mm) <= translation_tolerance
            and abs(tz_mm) <= translation_tolerance
        )

        return DeviationResult(
            pitch_deg=pitch_delta,
            yaw_deg=yaw_delta,
            roll_deg=roll_delta,
            tx_mm=tx_mm,
            ty_mm=ty_mm,
            tz_mm=tz_mm,
            aggregate_pose_error=aggregate_pose_error,
            within_nominal_bounds=within_nominal_bounds,
            pose_margin_scale=pose_margin_scale,
        )

    def _rotation_matrix_to_euler(self, rotation_matrix) -> tuple[float, float, float]:
        sy = sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
        singular = sy < 1e-6

        if not singular:
            pitch = atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
            yaw = atan2(-rotation_matrix[2, 0], sy)
            roll = atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
        else:
            pitch = atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
            yaw = atan2(-rotation_matrix[2, 0], sy)
            roll = 0.0
        return degrees(pitch), degrees(yaw), degrees(roll)
