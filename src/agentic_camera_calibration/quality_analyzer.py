from __future__ import annotations

from .capture import load_frame_image
from .config import QualityThresholds
from .models import FrameRecord, QualityMetrics


def _require_cv2_and_numpy():
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError(
            "OpenCV and NumPy are required for quality analysis. Run `uv sync` first."
        ) from exc
    return cv2, np


class QualityAnalyzer:
    def __init__(self, thresholds: QualityThresholds) -> None:
        self.thresholds = thresholds
        self.cv2, self.np = _require_cv2_and_numpy()

    def analyze(self, frame: FrameRecord) -> QualityMetrics:
        frame = load_frame_image(frame)
        image = frame.image
        gray = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2GRAY)
        hsv = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2HSV)

        mean_brightness = float(gray.mean())
        contrast_score = float(gray.std())
        blur_score = float(self.cv2.Laplacian(gray, self.cv2.CV_64F).var())

        value_channel = hsv[:, :, 2]
        saturation_channel = hsv[:, :, 1]
        saturated_mask = (value_channel >= 250) | ((value_channel >= 240) & (saturation_channel <= 30))
        saturation_ratio = float(saturated_mask.mean())

        glare_mask = (value_channel >= 245) & (gray >= 235)
        glare_score = float(min(1.0, glare_mask.mean() * 2.5))

        reasons: list[str] = []
        if mean_brightness < self.thresholds.min_brightness:
            reasons.append("low_brightness")
        if mean_brightness > self.thresholds.max_brightness:
            reasons.append("high_brightness")
        if contrast_score < self.thresholds.min_contrast:
            reasons.append("low_contrast")
        if blur_score < self.thresholds.min_blur_score:
            reasons.append("blur_or_low_detail")
        if saturation_ratio > self.thresholds.max_saturation_ratio:
            reasons.append("overexposure")
        if glare_score > self.thresholds.max_glare_score:
            reasons.append("glare")

        return QualityMetrics(
            frame_id=frame.frame_id,
            mean_brightness=mean_brightness,
            contrast_score=contrast_score,
            blur_score=blur_score,
            saturation_ratio=saturation_ratio,
            glare_score=glare_score,
            usable=not reasons,
            reasons=reasons,
        )
