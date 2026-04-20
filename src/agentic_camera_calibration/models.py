from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


@dataclass(slots=True)
class FrameRecord:
    frame_id: str
    scenario: str
    run_id: str
    setup_type: str = "unspecified"
    dataset_split: str = "unspecified"
    image_path: Path | None = None
    image: Any | None = None
    is_reserved: bool = False
    metadata: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class RunRecord:
    run_id: str
    scenario: str
    run_path: Path
    frames: list[FrameRecord]
    setup_type: str = "unspecified"
    dataset_split: str = "unspecified"
    metadata: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class DetectionResult:
    frame_id: str
    detection_success: bool
    markers_detected: int
    charuco_corners_detected: int
    coverage_score: float
    marker_ids: Any | None = None
    marker_corners: Any | None = None
    charuco_ids: Any | None = None
    charuco_corners: Any | None = None
    pose_rvec: tuple[float, float, float] | None = None
    pose_tvec_mm: tuple[float, float, float] | None = None


@dataclass(slots=True)
class QualityMetrics:
    frame_id: str
    mean_brightness: float
    contrast_score: float
    blur_score: float
    saturation_ratio: float
    glare_score: float
    usable: bool
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CalibrationResult:
    success: bool
    reprojection_error: float | None
    camera_matrix: Any | None
    distortion_coeffs: Any | None
    valid_frames_used: int
    rejected_frames: int
    failure_reasons: list[str] = field(default_factory=list)
    image_size: tuple[int, int] | None = None
    mean_pose_rvec: tuple[float, float, float] | None = None
    mean_pose_tvec_mm: tuple[float, float, float] | None = None


@dataclass(slots=True)
class DeviationResult:
    pitch_deg: float
    yaw_deg: float
    roll_deg: float
    tx_mm: float
    ty_mm: float
    tz_mm: float
    aggregate_pose_error: float
    within_nominal_bounds: bool
    pose_margin_scale: float = 1.0


@dataclass(slots=True)
class FailureEvaluation:
    status: str
    reason_codes: list[str]
    confidence: float
    warning_codes: list[str] = field(default_factory=list)
    hard_fail_codes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ControllerState:
    run_id: str
    scenario: str
    retry_index: int
    frames_total: int
    frames_active: int
    frames_reserved_remaining: int
    mean_brightness: float
    mean_saturation_ratio: float
    mean_blur_score: float
    mean_glare_score: float
    mean_marker_count: float
    mean_charuco_corner_count: float
    mean_coverage_score: float
    calibration_success: bool
    reprojection_error: float | None
    deviation_result: DeviationResult | None
    reason_codes: list[str]
    attempted_actions: list[JsonDict]
    allowed_actions: list[str]
    setup_type: str = "unspecified"
    dataset_split: str = "unspecified"


@dataclass(slots=True)
class RecoveryDecision:
    diagnosis: str
    actions: list[JsonDict]
    confidence: float
    declare_unrecoverable: bool


@dataclass(slots=True)
class ExperimentRunResult:
    mode: str
    status: str
    run_id: str
    scenario: str
    retry_index: int
    setup_type: str = "unspecified"
    dataset_split: str = "unspecified"
    calibration_result: CalibrationResult | None = None
    deviation_result: DeviationResult | None = None
    attempted_actions: list[JsonDict] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    warning_codes: list[str] = field(default_factory=list)
    hard_fail_codes: list[str] = field(default_factory=list)
    decision: RecoveryDecision | None = None


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "tolist"):
        return value.tolist()
    return value
