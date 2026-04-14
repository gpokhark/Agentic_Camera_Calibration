from __future__ import annotations

import json
import subprocess

from ..config import ControllerConfig
from ..models import ControllerState, RecoveryDecision, to_jsonable
from .base import RecoveryController
from .heuristic_controller import HeuristicController


class AgentController(RecoveryController):
    def __init__(self, config: ControllerConfig) -> None:
        self.config = config
        self.heuristic_fallback = HeuristicController(config)

    def decide(self, state: ControllerState) -> RecoveryDecision:
        if not self.config.agent_command:
            fallback = self.heuristic_fallback.decide(state)
            return RecoveryDecision(
                diagnosis=f"Agent fallback used heuristic logic. {fallback.diagnosis}",
                actions=fallback.actions,
                confidence=min(0.7, fallback.confidence),
                declare_unrecoverable=fallback.declare_unrecoverable,
            )

        payload = {
            "system_prompt": (
                "You are a camera calibration recovery controller. "
                "Use only allowed actions, return JSON only, and prefer minimal interventions."
            ),
            "controller_state": to_jsonable(state),
            "required_schema": {
                "diagnosis": "string",
                "actions": [{"action": "string", "params": "object"}],
                "confidence": "number[0,1]",
                "declare_unrecoverable": "bool",
            },
        }

        result = subprocess.run(
            self.config.agent_command,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
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
