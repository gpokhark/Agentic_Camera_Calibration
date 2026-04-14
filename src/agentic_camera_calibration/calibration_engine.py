from __future__ import annotations

from .capture import load_frame_image
from .charuco_detector import CharucoDetector, mean_pose_components
from .config import FailureThresholds
from .models import CalibrationResult, DetectionResult, FrameRecord


def _require_cv2_and_numpy():
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError(
            "OpenCV and NumPy are required for calibration. Run `uv sync` first."
        ) from exc
    return cv2, np


class CalibrationEngine:
    def __init__(self, detector: CharucoDetector, failure_thresholds: FailureThresholds) -> None:
        self.detector = detector
        self.failure_thresholds = failure_thresholds
        self.cv2, self.np = _require_cv2_and_numpy()

    def calibrate(
        self,
        frames: list[FrameRecord],
        detections: list[DetectionResult],
        mode: str = "charuco_standard",
    ) -> CalibrationResult:
        del mode

        valid_pairs = [
            (frame, detection)
            for frame, detection in zip(frames, detections, strict=False)
            if detection.detection_success
            and detection.charuco_corners is not None
            and detection.charuco_ids is not None
            and detection.charuco_corners_detected >= 4
        ]

        if len(valid_pairs) < self.failure_thresholds.min_usable_frames:
            return CalibrationResult(
                success=False,
                reprojection_error=None,
                camera_matrix=None,
                distortion_coeffs=None,
                valid_frames_used=len(valid_pairs),
                rejected_frames=max(0, len(frames) - len(valid_pairs)),
                failure_reasons=["insufficient_usable_frames"],
            )

        first_frame = load_frame_image(valid_pairs[0][0])
        image_height, image_width = first_frame.image.shape[:2]

        try:
            retval, camera_matrix, distortion_coeffs, _, _ = self.cv2.aruco.calibrateCameraCharuco(
                charucoCorners=[item[1].charuco_corners for item in valid_pairs],
                charucoIds=[item[1].charuco_ids for item in valid_pairs],
                board=self.detector.board,
                imageSize=(image_width, image_height),
                cameraMatrix=None,
                distCoeffs=None,
            )
        except self.cv2.error as exc:
            return CalibrationResult(
                success=False,
                reprojection_error=None,
                camera_matrix=None,
                distortion_coeffs=None,
                valid_frames_used=len(valid_pairs),
                rejected_frames=max(0, len(frames) - len(valid_pairs)),
                failure_reasons=[f"opencv_calibration_error: {exc}"],
            )

        calibration = CalibrationResult(
            success=True,
            reprojection_error=float(retval),
            camera_matrix=camera_matrix,
            distortion_coeffs=distortion_coeffs,
            valid_frames_used=len(valid_pairs),
            rejected_frames=max(0, len(frames) - len(valid_pairs)),
            failure_reasons=[],
            image_size=(image_width, image_height),
        )

        pose_enriched = [self.detector.estimate_pose(detection, calibration) for _, detection in valid_pairs]
        mean_rvec, mean_tvec = mean_pose_components(pose_enriched)
        calibration.mean_pose_rvec = mean_rvec
        calibration.mean_pose_tvec_mm = mean_tvec
        return calibration
