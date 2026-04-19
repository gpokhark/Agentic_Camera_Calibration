from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any


@dataclass(slots=True)
class BoardConfig:
    squares_x: int = 7
    squares_y: int = 5
    square_length_mm: float = 30.0
    marker_length_mm: float = 22.0
    dictionary_name: str = "DICT_4X4_50"


@dataclass(slots=True)
class QualityThresholds:
    min_brightness: float = 45.0
    max_brightness: float = 235.0
    min_contrast: float = 20.0
    min_blur_score: float = 50.0
    max_saturation_ratio: float = 0.15
    max_glare_score: float = 0.35


@dataclass(slots=True)
class FailureThresholds:
    max_reprojection_error: float = 2.0
    min_usable_frames: int = 8
    min_charuco_corners: int = 12
    min_coverage_score: float = 0.35
    pose_translation_tolerance_mm: float = 20.0
    pose_angle_tolerance_deg: float = 5.0
    max_pose_margin_scale: float = 1.5


@dataclass(slots=True)
class ControllerConfig:
    allowed_actions: list[str] = field(
        default_factory=lambda: [
            "reject_bad_frames",
            "apply_preprocessing",
            "request_additional_views",
            "retry_with_filtered_subset",
            "relax_nominal_prior",
            "declare_unrecoverable",
        ]
    )
    max_actions_per_decision: int = 3
    agent_command: list[str] = field(default_factory=list)
    agent_backend: str = "openai"
    agent_model: str = "gpt-5-mini"
    agent_reasoning_effort: str = "minimal"
    agent_max_output_tokens: int = 180
    agent_timeout_seconds: int = 45
    agent_history_limit: int = 2
    agent_prompt_cache_key: str = "accal-controller-v1"
    agent_prompt_cache_retention: str = "24h"
    claude_agent_model: str = "claude-haiku-4-5-20251001"
    lm_studio_model: str = "local-model"
    lm_studio_base_url: str = "http://localhost:1234/v1"


@dataclass(slots=True)
class ExperimentConfig:
    dataset_root: str = "dataset"
    results_root: str = "results"
    max_retries: int = 3
    initial_frame_count: int = 12
    reserved_frame_count: int = 8


@dataclass(slots=True)
class NominalPoseConfig:
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    roll_deg: float = 0.0
    tx_mm: float = 0.0
    ty_mm: float = 0.0
    tz_mm: float = 300.0


@dataclass(slots=True)
class CalibrationConfig:
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)
    board: BoardConfig = field(default_factory=BoardConfig)
    quality: QualityThresholds = field(default_factory=QualityThresholds)
    failure: FailureThresholds = field(default_factory=FailureThresholds)
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    nominal_pose: NominalPoseConfig = field(default_factory=NominalPoseConfig)

    @property
    def dataset_root(self) -> Path:
        return Path(self.experiment.dataset_root)

    @property
    def results_root(self) -> Path:
        return Path(self.experiment.results_root)


def _merge_dataclass(instance: Any, payload: dict[str, Any]) -> Any:
    for key, value in payload.items():
        if not hasattr(instance, key):
            continue
        setattr(instance, key, value)
    return instance


def load_config(path: str | Path | None = None) -> CalibrationConfig:
    config = CalibrationConfig()
    selected_path = Path(path) if path is not None else Path("config/defaults.toml")
    if not selected_path.exists():
        return config

    with selected_path.open("rb") as handle:
        payload = tomllib.load(handle)

    _merge_dataclass(config.experiment, payload.get("experiment", {}))
    _merge_dataclass(config.board, payload.get("board", {}))
    _merge_dataclass(config.quality, payload.get("quality", {}))
    _merge_dataclass(config.failure, payload.get("failure", {}))
    _merge_dataclass(config.controller, payload.get("controller", {}))
    _merge_dataclass(config.nominal_pose, payload.get("nominal_pose", {}))
    return config
