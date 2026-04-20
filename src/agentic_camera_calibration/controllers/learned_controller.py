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


class LearnedController(RecoveryController):
    """Lightweight feature-scored structured controller baseline.

    This intentionally avoids external ML dependencies while still behaving
    differently from the heuristic controller: it scores candidate recovery
    actions from the structured state and selects the highest-scoring bounded
    action set.
    """

    def __init__(self, config: ControllerConfig) -> None:
        self.config = config

    def decide(self, state: ControllerState) -> RecoveryDecision:
        reasons = set(state.reason_codes)
        if _repeated_reason_pattern(state.attempted_actions, state.reason_codes):
            return RecoveryDecision(
                diagnosis="Learned controller observed a repeated failure signature and predicts low recovery value.",
                actions=[],
                confidence=0.84,
                declare_unrecoverable=True,
            )

        candidate_scores: list[tuple[float, dict]] = []

        saturation_excess = max(0.0, state.mean_saturation_ratio - 0.15)
        blur_deficit = max(0.0, 50.0 - state.mean_blur_score) / 50.0
        low_brightness = max(0.0, 45.0 - state.mean_brightness) / 45.0
        glare_level = max(0.0, state.mean_glare_score - 0.1)
        coverage_deficit = max(0.0, 0.35 - state.mean_coverage_score) / 0.35
        corner_deficit = max(0.0, 12.0 - state.mean_charuco_corner_count) / 12.0
        reprojection_excess = max(0.0, (state.reprojection_error or 0.0) - 2.0) / 2.0

        quality_good = (
            state.mean_saturation_ratio <= 0.15
            and state.mean_blur_score >= 50.0
            and state.mean_glare_score < 0.1
        )

        def add_candidate(score: float, action: str, params: dict) -> None:
            if action not in state.allowed_actions:
                return
            if score < self.config.learned_min_action_score:
                return
            candidate_scores.append((score, {"action": action, "params": params}))

        add_candidate(
            1.2 + saturation_excess * 8.0 + (0.4 if "overexposure" in reasons else 0.0),
            "reject_bad_frames",
            {"max_saturation_ratio": 0.12},
        )
        add_candidate(
            1.0 + blur_deficit * 4.0 + (0.3 if "blur_or_low_detail" in reasons else 0.0),
            "reject_bad_frames",
            {"min_blur_score": 50},
        )
        add_candidate(
            0.9 + low_brightness * 3.0 + (0.7 if "low_light" in reasons else 0.0) + (0.4 if "low_corner_count" in reasons else 0.0),
            "apply_preprocessing",
            {"mode": "clahe"},
        )
        add_candidate(
            0.9 + glare_level * 4.0 + (0.6 if "glare" in reasons else 0.0),
            "apply_preprocessing",
            {"mode": "contrast_normalization"},
        )
        add_candidate(
            0.8 + corner_deficit * 3.0 + (0.8 if "low_corner_count" in reasons else 0.0),
            "request_additional_views",
            {"count": 4, "pattern": "general_diversity"},
        )
        if state.frames_reserved_remaining >= 4:
            add_candidate(
                0.9
                + coverage_deficit * 4.0
                + (0.9 if "low_marker_coverage" in reasons else 0.0)
                + (1.0 if "partial_visibility" in reasons else 0.0),
                "request_additional_views",
                {
                    "count": 6 if "partial_visibility" in reasons else 4,
                    "pattern": "edge_and_tilt" if "partial_visibility" in reasons else "edge_coverage",
                },
            )
        add_candidate(
            0.9 + reprojection_excess * 3.5 + (0.5 if "high_reprojection_error" in reasons else 0.0),
            "retry_with_filtered_subset",
            {"top_k": 8},
        )
        add_candidate(
            (1.0 if "pose_out_of_range" in reasons else 0.0) + (0.8 if quality_good else 0.0) - (0.5 if "overexposure" in reasons else 0.0),
            "relax_nominal_prior",
            {"pose_margin_scale": 1.25},
        )

        ranked_actions = [action for _score, action in sorted(candidate_scores, key=lambda item: item[0], reverse=True)]
        deduped_actions = _deduplicate_actions(ranked_actions)[: self.config.max_actions_per_decision]

        if not deduped_actions:
            return RecoveryDecision(
                diagnosis="Learned controller found no action with enough predicted recovery value.",
                actions=[],
                confidence=0.66,
                declare_unrecoverable=True,
            )

        return RecoveryDecision(
            diagnosis="Learned structured policy selected the highest-scoring bounded recovery actions.",
            actions=deduped_actions,
            confidence=0.74,
            declare_unrecoverable=False,
        )
