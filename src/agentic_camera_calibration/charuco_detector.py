from __future__ import annotations

from dataclasses import replace
from statistics import mean

from .capture import load_frame_image
from .config import BoardConfig
from .models import CalibrationResult, DetectionResult, FrameRecord


def _require_cv2_and_numpy():
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError(
            "OpenCV and NumPy are required for ChArUco detection. Run `uv sync` first."
        ) from exc
    return cv2, np


class CharucoDetector:
    def __init__(self, board_config: BoardConfig) -> None:
        self.board_config = board_config
        self.cv2, self.np = _require_cv2_and_numpy()
        dictionary_id = getattr(self.cv2.aruco, board_config.dictionary_name)
        self.dictionary = self.cv2.aruco.getPredefinedDictionary(dictionary_id)
        self.board = self.cv2.aruco.CharucoBoard(
            (board_config.squares_x, board_config.squares_y),
            board_config.square_length_mm,
            board_config.marker_length_mm,
            self.dictionary,
        )
        self.detector = self.cv2.aruco.ArucoDetector(self.dictionary)

    def detect(self, frame: FrameRecord) -> DetectionResult:
        frame = load_frame_image(frame)
        image = frame.image
        gray = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2GRAY)
        marker_corners, marker_ids, _ = self.detector.detectMarkers(gray)

        if marker_ids is None or len(marker_ids) == 0:
            return DetectionResult(
                frame_id=frame.frame_id,
                detection_success=False,
                markers_detected=0,
                charuco_corners_detected=0,
                coverage_score=0.0,
            )

        charuco_retval, charuco_corners, charuco_ids = self.cv2.aruco.interpolateCornersCharuco(
            marker_corners,
            marker_ids,
            gray,
            self.board,
        )
        charuco_count = int(charuco_retval) if charuco_retval is not None else 0
        coverage = self._coverage_score(image.shape[1], image.shape[0], marker_corners, charuco_corners)

        return DetectionResult(
            frame_id=frame.frame_id,
            detection_success=charuco_count >= 4,
            markers_detected=len(marker_ids),
            charuco_corners_detected=charuco_count,
            coverage_score=coverage,
            marker_ids=marker_ids,
            marker_corners=marker_corners,
            charuco_ids=charuco_ids,
            charuco_corners=charuco_corners,
        )

    def estimate_pose(
        self,
        detection: DetectionResult,
        calibration_result: CalibrationResult,
    ) -> DetectionResult:
        if (
            not detection.detection_success
            or detection.charuco_corners is None
            or detection.charuco_ids is None
            or calibration_result.camera_matrix is None
            or calibration_result.distortion_coeffs is None
        ):
            return detection

        success, rvec, tvec = self.cv2.aruco.estimatePoseCharucoBoard(
            detection.charuco_corners,
            detection.charuco_ids,
            self.board,
            calibration_result.camera_matrix,
            calibration_result.distortion_coeffs,
            None,
            None,
        )
        if not success:
            return detection

        return replace(
            detection,
            pose_rvec=tuple(float(value) for value in rvec.flatten()),
            pose_tvec_mm=tuple(float(value) for value in tvec.flatten()),
        )

    def _coverage_score(self, width: int, height: int, marker_corners, charuco_corners) -> float:
        points = []
        if marker_corners:
            for corner_group in marker_corners:
                for point in corner_group.reshape(-1, 2):
                    points.append(point)
        elif charuco_corners is not None:
            for point in charuco_corners.reshape(-1, 2):
                points.append(point)

        if len(points) < 4:
            return 0.0

        points_array = self.np.array(points)
        min_x = max(float(points_array[:, 0].min()), 0.0)
        min_y = max(float(points_array[:, 1].min()), 0.0)
        max_x = min(float(points_array[:, 0].max()), float(width))
        max_y = min(float(points_array[:, 1].max()), float(height))
        area = max(0.0, max_x - min_x) * max(0.0, max_y - min_y)
        full_area = float(width * height)
        return 0.0 if full_area <= 0 else min(1.0, area / full_area)


def mean_pose_components(
    detections: list[DetectionResult],
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | tuple[None, None]:
    pose_detections = [item for item in detections if item.pose_rvec is not None and item.pose_tvec_mm is not None]
    if not pose_detections:
        return None, None

    mean_rvec = tuple(mean(item.pose_rvec[index] for item in pose_detections) for index in range(3))
    mean_tvec = tuple(mean(item.pose_tvec_mm[index] for item in pose_detections) for index in range(3))
    return mean_rvec, mean_tvec
