from __future__ import annotations

import json
import subprocess

from ..config import ControllerConfig
from ..models import ControllerState, RecoveryDecision, to_jsonable
from .base import RecoveryController


class AgentController(RecoveryController):
    def __init__(self, config: ControllerConfig) -> None:
        self.config = config

    def _resolved_command(self) -> list[str]:
        if self.config.agent_command:
            return self.config.agent_command
        backend = self.config.agent_backend
        if backend == "openai":
            return ["uv", "run", "python", "-m", "agentic_camera_calibration.openai_agent"]
        if backend == "claude":
            return ["uv", "run", "python", "-m", "agentic_camera_calibration.claude_agent"]
        raise RuntimeError(
            f"Unknown agent_backend: {backend!r}. Set agent_backend to 'openai' or 'claude', "
            "or set agent_command explicitly for a custom agent."
        )

    def decide(self, state: ControllerState) -> RecoveryDecision:
        cmd = self._resolved_command()
        payload = self._build_payload(state)

        result = subprocess.run(
            cmd,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
            timeout=self.config.agent_timeout_seconds,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Agent command failed with exit code {result.returncode}: {result.stderr.strip()}"
            )

        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Agent command returned invalid JSON: {result.stdout!r}") from exc
        return self._validate_decision(parsed, state)

    def _build_payload(self, state: ControllerState) -> dict:
        model = (
            self.config.claude_agent_model
            if self.config.agent_backend == "claude"
            else self.config.agent_model
        )
        return {
            "system_prompt": (
                "You are a camera calibration recovery controller. "
                "Use only allowed actions, return JSON only, and prefer the smallest effective action set."
            ),
            "controller_state": self._compact_state(state),
            "required_schema": {
                "diagnosis": "string",
                "actions": [{"action": "string", "params": "object"}],
                "confidence": "number[0,1]",
                "declare_unrecoverable": "bool",
            },
            "agent_settings": {
                "model": model,
                "reasoning_effort": self.config.agent_reasoning_effort,
                "max_output_tokens": self.config.agent_max_output_tokens,
                "timeout_seconds": self.config.agent_timeout_seconds,
                "prompt_cache_key": self.config.agent_prompt_cache_key,
                "prompt_cache_retention": self.config.agent_prompt_cache_retention,
            },
        }

    def _compact_state(self, state: ControllerState) -> dict:
        compact = {
            "run_id": state.run_id,
            "scenario": state.scenario,
            "retry_index": state.retry_index,
            "frames_total": state.frames_total,
            "frames_active": state.frames_active,
            "frames_reserved_remaining": state.frames_reserved_remaining,
            "mean_brightness": round(state.mean_brightness, 3),
            "mean_saturation_ratio": round(state.mean_saturation_ratio, 4),
            "mean_blur_score": round(state.mean_blur_score, 3),
            "mean_glare_score": round(state.mean_glare_score, 4),
            "mean_marker_count": round(state.mean_marker_count, 3),
            "mean_charuco_corner_count": round(state.mean_charuco_corner_count, 3),
            "mean_coverage_score": round(state.mean_coverage_score, 4),
            "calibration_success": state.calibration_success,
            "reprojection_error": None if state.reprojection_error is None else round(state.reprojection_error, 4),
            "reason_codes": list(state.reason_codes),
            "allowed_actions": list(state.allowed_actions),
            "attempted_actions": state.attempted_actions[-self.config.agent_history_limit :],
        }
        if state.deviation_result is None:
            compact["deviation_result"] = None
        else:
            compact["deviation_result"] = {
                "pitch_deg": round(state.deviation_result.pitch_deg, 3),
                "yaw_deg": round(state.deviation_result.yaw_deg, 3),
                "roll_deg": round(state.deviation_result.roll_deg, 3),
                "tx_mm": round(state.deviation_result.tx_mm, 3),
                "ty_mm": round(state.deviation_result.ty_mm, 3),
                "tz_mm": round(state.deviation_result.tz_mm, 3),
                "aggregate_pose_error": round(state.deviation_result.aggregate_pose_error, 3),
                "within_nominal_bounds": state.deviation_result.within_nominal_bounds,
                "pose_margin_scale": round(state.deviation_result.pose_margin_scale, 3),
            }
        return to_jsonable(compact)

    def _validate_decision(self, payload: dict, state: ControllerState) -> RecoveryDecision:
        diagnosis = str(payload.get("diagnosis", "")).strip()
        confidence = float(payload.get("confidence", 0.0))
        declare_unrecoverable = bool(payload.get("declare_unrecoverable", False))
        actions = payload.get("actions", [])

        if not diagnosis:
            raise ValueError("Agent output is missing a diagnosis.")
        if not isinstance(actions, list):
            raise ValueError("Agent output field `actions` must be a list.")
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("Agent output confidence must be between 0.0 and 1.0.")
        if len(actions) > self.config.max_actions_per_decision:
            raise ValueError("Agent output exceeded the maximum allowed action count.")

        validated_actions: list[dict] = []
        for action in actions:
            action_name = action.get("action")
            params = action.get("params", {})
            if action_name not in state.allowed_actions:
                raise ValueError(f"Agent returned disallowed action: {action_name}")
            if not isinstance(params, dict):
                raise ValueError(f"Agent returned invalid params for action {action_name}")
            validated_actions.append({"action": action_name, "params": params})

        return RecoveryDecision(
            diagnosis=diagnosis,
            actions=validated_actions,
            confidence=confidence,
            declare_unrecoverable=declare_unrecoverable,
        )
