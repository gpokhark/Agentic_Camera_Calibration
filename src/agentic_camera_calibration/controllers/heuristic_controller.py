from __future__ import annotations

from ..config import ControllerConfig
from ..models import ControllerState, RecoveryDecision
from .base import RecoveryController


def _deduplicate_actions(actions: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple[str, tuple[tuple[str, object], ...]]] = set()
    for action in actions:
        params = tuple(sorted(action.get("params", {}).items()))
        key = (action["action"], params)
        if key in seen:
            continue
        deduped.append(action)
        seen.add(key)
    return deduped


def _repeated_reason_pattern(attempted_actions: list[dict], reason_codes: list[str]) -> bool:
    reason_set = set(reason_codes)
    repeated = 0
    for attempt in reversed(attempted_actions):
        previous = set(attempt.get("reason_codes", []))
        if previous == reason_set:
            repeated += 1
    return repeated >= 2


class HeuristicController(RecoveryController):
    def __init__(self, config: ControllerConfig) -> None:
        self.config = config

    def decide(self, state: ControllerState) -> RecoveryDecision:
        actions: list[dict] = []
        reasons = set(state.reason_codes)

        if _repeated_reason_pattern(state.attempted_actions, state.reason_codes):
            return RecoveryDecision(
                diagnosis="Repeated failure pattern indicates recovery is unlikely.",
                actions=[],
                confidence=0.82,
                declare_unrecoverable=True,
            )

        if state.mean_saturation_ratio > 0.15 and "reject_bad_frames" in state.allowed_actions:
            actions.append(
                {"action": "reject_bad_frames", "params": {"max_saturation_ratio": 0.12}}
            )

        if state.mean_blur_score < 50 and "reject_bad_frames" in state.allowed_actions:
            actions.append({"action": "reject_bad_frames", "params": {"min_blur_score": 50}})

        if "low_light" in reasons and "apply_preprocessing" in state.allowed_actions:
            actions.append({"action": "apply_preprocessing", "params": {"mode": "clahe"}})

        if "glare" in reasons and "apply_preprocessing" in state.allowed_actions:
            actions.append(
                {"action": "apply_preprocessing", "params": {"mode": "contrast_normalization"}}
            )

        if "low_corner_count" in reasons and state.frames_reserved_remaining >= 4:
            actions.append(
                {
                    "action": "request_additional_views",
                    "params": {"count": 4, "pattern": "general_diversity"},
                }
            )

        if "low_marker_coverage" in reasons and state.frames_reserved_remaining >= 4:
            actions.append(
                {
                    "action": "request_additional_views",
                    "params": {"count": 4, "pattern": "edge_coverage"},
                }
            )

        if (
            state.reprojection_error is not None
            and state.reprojection_error > 2.0
            and "retry_with_filtered_subset" in state.allowed_actions
        ):
            actions.append({"action": "retry_with_filtered_subset", "params": {"top_k": 8}})

        if (
            "pose_out_of_range" in reasons
            and "overexposure" not in reasons
            and state.mean_saturation_ratio <= 0.15
            and state.mean_glare_score < 0.1
            and state.mean_blur_score >= 50
            and "relax_nominal_prior" in state.allowed_actions
        ):
            actions.append(
                {"action": "relax_nominal_prior", "params": {"pose_margin_scale": 1.25}}
            )

        if (
            "overexposure" in reasons
            and "low_corner_count" in reasons
            and "apply_preprocessing" in state.allowed_actions
        ):
            actions.append({"action": "apply_preprocessing", "params": {"mode": "clahe"}})

        if (
            "partial_visibility" in reasons
            and "low_marker_coverage" in reasons
            and state.frames_reserved_remaining >= 4
            and "request_additional_views" in state.allowed_actions
        ):
            actions.append(
                {
                    "action": "request_additional_views",
                    "params": {"count": 6, "pattern": "edge_and_tilt"},
                }
            )

        if state.frames_reserved_remaining == 0 and state.reprojection_error and state.reprojection_error > 2.0:
            return RecoveryDecision(
                diagnosis="No reserved frames remain and reprojection error is still high.",
                actions=[],
                confidence=0.76,
                declare_unrecoverable=True,
            )

        deduped_actions = _deduplicate_actions(actions)[: self.config.max_actions_per_decision]
        if not deduped_actions:
            return RecoveryDecision(
                diagnosis="No safe deterministic recovery action remains.",
                actions=[],
                confidence=0.64,
                declare_unrecoverable=True,
            )

        return RecoveryDecision(
            diagnosis="Heuristic recovery selected from shared threshold rules.",
            actions=deduped_actions,
            confidence=0.72,
            declare_unrecoverable=False,
        )
