# Paper Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen the heuristic baseline, add missing test coverage for three new modules, add two-sided paper metrics (recovery rate + false reject rate), collect mixed-failure data, and run the full experiment to produce paper-ready results.

**Architecture:** `openai_agent.py` (OpenAI Responses API via stdlib urllib), `agent_command` wiring, and `EmpiricalNominalEstimator` are all already implemented. Remaining work: compound heuristic rules, test coverage for `nominal_reference.py` / `openai_agent.py` / `AgentController` new methods, paper metrics in `Evaluator`/`Reporter`/`ExperimentRunner`, mixed-failure data capture, and the experiment run.

**Tech Stack:** Python 3.12, OpenCV, OpenAI Responses API (no new SDK — uses stdlib urllib), uv, pytest

---

## Implementation Status at Plan Start

| Component | Status |
|---|---|
| `openai_agent.py` — OpenAI Responses API subprocess | **done** |
| `config/defaults.toml` — `agent_command` + agent settings | **done** |
| `ControllerConfig` — agent settings fields | **done** |
| `AgentController` — `_compact_state`, `_build_payload`, timeout, no fallback | **done** |
| `nominal_reference.py` — empirical nominal derivation | **done** |
| `experiment_runner.py` — two-pass: derive nominal → run modes | **done** |
| `dataset_auditor.py` — two-pass audit with empirical nominal | **done** |
| S0–S4 dataset (49 usable runs) | **done** |

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `src/agentic_camera_calibration/controllers/heuristic_controller.py` | Modify | Add 3 compound-condition rules |
| `src/agentic_camera_calibration/evaluator.py` | Modify | Add `compute_paper_metrics()` and `summarize_by_scenario()` |
| `src/agentic_camera_calibration/reporter.py` | Modify | Accept and write `paper_metrics` + `scenario_breakdown` |
| `src/agentic_camera_calibration/experiment_runner.py` | Modify | Pass new metrics to reporter; preserve existing `nominal_reference.json` write |
| `tests/test_heuristic_controller.py` | Modify | Add tests for 3 compound rules |
| `tests/test_evaluator.py` | Create | Tests for false reject rate + scenario summary |
| `tests/test_nominal_reference.py` | Create | Tests for `is_eligible_nominal_reference`, `default_nominal_reference`, `nominal_reference_to_config` |
| `tests/test_openai_agent.py` | Create | Tests for `_build_request_body`, `_extract_output_text`, integration |
| `tests/test_agent_controller.py` | Create | Tests for `_compact_state` and `_build_payload` |

---

## Task 1: Strengthen heuristic with compound-condition rules

**Files:**
- Modify: `src/agentic_camera_calibration/controllers/heuristic_controller.py`
- Modify: `tests/test_heuristic_controller.py`

Three gaps in the current heuristic:

1. **Overexposure + pose_out_of_range**: `relax_nominal_prior` rule checks `glare < 0.1` and `blur >= 50` but not saturation — so it fires incorrectly when images are overexposed. Fix: add `mean_saturation_ratio <= 0.15` guard.
2. **partial_visibility + low_marker_coverage**: missing — should use `edge_and_tilt` pattern with count=6 instead of generic patterns.
3. **overexposure + low_corner_count**: should also trigger `apply_preprocessing(clahe)` alongside frame rejection to help corner detection recover.

- [ ] **Step 1: Write failing tests for the three compound cases**

Add to `tests/test_heuristic_controller.py` inside `class HeuristicControllerTests`:

```python
    def test_does_not_relax_pose_when_overexposed(self) -> None:
        controller = HeuristicController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S1_overexposed",
            retry_index=0,
            frames_total=16,
            frames_active=12,
            frames_reserved_remaining=4,
            mean_brightness=220.0,
            mean_saturation_ratio=0.22,
            mean_blur_score=70.0,
            mean_glare_score=0.08,
            mean_marker_count=9.0,
            mean_charuco_corner_count=11.0,
            mean_coverage_score=0.28,
            calibration_success=False,
            reprojection_error=2.5,
            deviation_result=None,
            reason_codes=["overexposure", "pose_out_of_range"],
            attempted_actions=[],
            allowed_actions=ControllerConfig().allowed_actions,
        )
        decision = controller.decide(state)
        action_names = [a["action"] for a in decision.actions]
        self.assertNotIn("relax_nominal_prior", action_names)

    def test_uses_edge_and_tilt_for_partial_visibility_with_low_coverage(self) -> None:
        controller = HeuristicController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S5_partial_visibility",
            retry_index=0,
            frames_total=16,
            frames_active=12,
            frames_reserved_remaining=6,
            mean_brightness=100.0,
            mean_saturation_ratio=0.02,
            mean_blur_score=80.0,
            mean_glare_score=0.02,
            mean_marker_count=5.0,
            mean_charuco_corner_count=8.0,
            mean_coverage_score=0.15,
            calibration_success=False,
            reprojection_error=3.1,
            deviation_result=None,
            reason_codes=["partial_visibility", "low_marker_coverage", "low_corner_count"],
            attempted_actions=[],
            allowed_actions=ControllerConfig().allowed_actions,
        )
        decision = controller.decide(state)
        additional = [a for a in decision.actions if a["action"] == "request_additional_views"]
        self.assertTrue(len(additional) > 0)
        self.assertEqual(additional[0]["params"]["pattern"], "edge_and_tilt")

    def test_adds_clahe_when_overexposure_and_low_corners_together(self) -> None:
        controller = HeuristicController(ControllerConfig())
        state = ControllerState(
            run_id="run_01",
            scenario="S1_overexposed",
            retry_index=0,
            frames_total=16,
            frames_active=12,
            frames_reserved_remaining=4,
            mean_brightness=225.0,
            mean_saturation_ratio=0.20,
            mean_blur_score=72.0,
            mean_glare_score=0.40,
            mean_marker_count=8.0,
            mean_charuco_corner_count=10.0,
            mean_coverage_score=0.24,
            calibration_success=False,
            reprojection_error=2.7,
            deviation_result=None,
            reason_codes=["overexposure", "glare", "low_corner_count"],
            attempted_actions=[],
            allowed_actions=ControllerConfig().allowed_actions,
        )
        decision = controller.decide(state)
        action_names = [a["action"] for a in decision.actions]
        self.assertIn("reject_bad_frames", action_names)
        self.assertIn("apply_preprocessing", action_names)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_heuristic_controller.py -v
```

Expected: 3 new tests FAIL, existing 2 PASS.

- [ ] **Step 3: Replace heuristic_controller.py with compound rules**

Replace the full content of `src/agentic_camera_calibration/controllers/heuristic_controller.py`:

```python
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

        # --- Single-signal rules ---

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

        # --- Compound-condition rules ---

        # H8: overexposure + low_corner_count → CLAHE improves contrast for corner detection
        if (
            "overexposure" in reasons
            and "low_corner_count" in reasons
            and "apply_preprocessing" in state.allowed_actions
        ):
            actions.append({"action": "apply_preprocessing", "params": {"mode": "clahe"}})

        # H9: partial_visibility + low_marker_coverage → edge_and_tilt is more targeted than generic
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
        else:
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

        # H10: pose relaxation only when image quality is adequate — no overexposure, no glare, no blur
        if (
            "pose_out_of_range" in reasons
            and state.mean_saturation_ratio <= 0.15
            and state.mean_glare_score < 0.1
            and state.mean_blur_score >= 50
            and "relax_nominal_prior" in state.allowed_actions
        ):
            actions.append(
                {"action": "relax_nominal_prior", "params": {"pose_margin_scale": 1.25}}
            )

        if (
            state.frames_reserved_remaining == 0
            and state.reprojection_error is not None
            and state.reprojection_error > 2.0
        ):
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
            diagnosis="Heuristic recovery selected from threshold and compound-condition rules.",
            actions=deduped_actions,
            confidence=0.72,
            declare_unrecoverable=False,
        )
```

- [ ] **Step 4: Run all heuristic tests**

```bash
uv run pytest tests/test_heuristic_controller.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/agentic_camera_calibration/controllers/heuristic_controller.py tests/test_heuristic_controller.py
git commit -m "feat: add compound-condition recovery rules to heuristic controller"
```

---

## Task 2: Add tests for nominal_reference.py

**Files:**
- Create: `tests/test_nominal_reference.py`

`test_dataset_auditor.py` already tests `derive_empirical_nominal_reference` and `apply_nominal_reference` via re-exported aliases. This task covers the remaining untested surface: `is_eligible_nominal_reference`, `default_nominal_reference`, and `nominal_reference_to_config`.

- [ ] **Step 1: Write the tests**

Create `tests/test_nominal_reference.py`:

```python
import pytest
from agentic_camera_calibration.config import CalibrationConfig, NominalPoseConfig
from agentic_camera_calibration.nominal_reference import (
    default_nominal_reference,
    is_eligible_nominal_reference,
    nominal_reference_to_config,
)


def _good_metrics(**overrides) -> dict:
    base = {
        "calibration_success": True,
        "usable_rate": 0.9,
        "detection_success_rate": 1.0,
        "mean_charuco_corners": 24.0,
        "reprojection_error": 0.18,
        "reason_codes": [],
        "estimated_pitch_deg": 2.1,
        "estimated_yaw_deg": -1.3,
        "estimated_roll_deg": 0.5,
        "estimated_tx_mm": 3.0,
        "estimated_ty_mm": -1.5,
        "estimated_tz_mm": 310.0,
    }
    base.update(overrides)
    return base


def test_eligible_nominal_good_run():
    assert is_eligible_nominal_reference(_good_metrics()) is True


def test_ineligible_calibration_failed():
    assert is_eligible_nominal_reference(_good_metrics(calibration_success=False)) is False


def test_ineligible_high_reprojection():
    assert is_eligible_nominal_reference(_good_metrics(reprojection_error=1.5)) is False


def test_ineligible_low_usable_rate():
    assert is_eligible_nominal_reference(_good_metrics(usable_rate=0.5)) is False


def test_ineligible_low_detection_rate():
    assert is_eligible_nominal_reference(_good_metrics(detection_success_rate=0.7)) is False


def test_ineligible_low_corner_count():
    assert is_eligible_nominal_reference(_good_metrics(mean_charuco_corners=8.0)) is False


def test_ineligible_lighting_failure_codes():
    for code in ("low_light", "overexposure", "blur_or_low_detail", "glare"):
        assert is_eligible_nominal_reference(_good_metrics(reason_codes=[code])) is False, code


def test_ineligible_missing_pose_field():
    for field in (
        "estimated_pitch_deg",
        "estimated_yaw_deg",
        "estimated_roll_deg",
        "estimated_tx_mm",
        "estimated_ty_mm",
        "estimated_tz_mm",
    ):
        assert is_eligible_nominal_reference(_good_metrics(**{field: None})) is False, field


def test_default_nominal_reference_uses_config_values():
    config = CalibrationConfig()
    result = default_nominal_reference(config)
    assert result["source"] == "config_defaults"
    assert result["run_count"] == 0
    assert result["run_ids"] == []
    assert result["pitch_deg"] == config.nominal_pose.pitch_deg
    assert result["yaw_deg"] == config.nominal_pose.yaw_deg
    assert result["roll_deg"] == config.nominal_pose.roll_deg
    assert result["tx_mm"] == config.nominal_pose.tx_mm
    assert result["ty_mm"] == config.nominal_pose.ty_mm
    assert result["tz_mm"] == config.nominal_pose.tz_mm


def test_nominal_reference_to_config_produces_nominal_pose_config():
    nominal = {
        "pitch_deg": 2.1,
        "yaw_deg": -1.3,
        "roll_deg": 0.5,
        "tx_mm": 3.0,
        "ty_mm": -1.5,
        "tz_mm": 310.0,
    }
    config = nominal_reference_to_config(nominal)
    assert isinstance(config, NominalPoseConfig)
    assert config.pitch_deg == pytest.approx(2.1)
    assert config.yaw_deg == pytest.approx(-1.3)
    assert config.roll_deg == pytest.approx(0.5)
    assert config.tx_mm == pytest.approx(3.0)
    assert config.ty_mm == pytest.approx(-1.5)
    assert config.tz_mm == pytest.approx(310.0)
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_nominal_reference.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_nominal_reference.py
git commit -m "test: add coverage for nominal_reference eligibility, default, and config conversion"
```

---

## Task 3: Add tests for openai_agent.py

**Files:**
- Create: `tests/test_openai_agent.py`

`openai_agent.py` has no test coverage. Test `_build_request_body` and `_extract_output_text` without hitting the API. The integration test requires `OPENAI_API_KEY` and is skipped when missing.

- [ ] **Step 1: Write the tests**

Create `tests/test_openai_agent.py`:

```python
import json
import os
import subprocess
import sys
import unittest

from agentic_camera_calibration.openai_agent import (
    _build_request_body,
    _extract_output_text,
)


def _minimal_payload() -> dict:
    return {
        "system_prompt": "You are a calibration recovery controller.",
        "controller_state": {
            "run_id": "run_01",
            "scenario": "S1_overexposed",
            "retry_index": 0,
            "frames_total": 12,
            "frames_active": 12,
            "frames_reserved_remaining": 4,
            "mean_brightness": 220.0,
            "mean_saturation_ratio": 0.22,
            "mean_blur_score": 68.0,
            "mean_glare_score": 0.38,
            "mean_marker_count": 9.0,
            "mean_charuco_corner_count": 11.0,
            "mean_coverage_score": 0.26,
            "calibration_success": False,
            "reprojection_error": 2.9,
            "deviation_result": None,
            "reason_codes": ["overexposure", "low_corner_count"],
            "attempted_actions": [],
            "allowed_actions": [
                "reject_bad_frames",
                "apply_preprocessing",
                "request_additional_views",
                "retry_with_filtered_subset",
                "relax_nominal_prior",
                "declare_unrecoverable",
            ],
        },
        "required_schema": {
            "diagnosis": "string",
            "actions": [{"action": "string", "params": "object"}],
            "confidence": "number[0,1]",
            "declare_unrecoverable": "bool",
        },
        "agent_settings": {
            "model": "gpt-5-mini",
            "reasoning_effort": "minimal",
            "max_output_tokens": 180,
            "timeout_seconds": 45,
            "prompt_cache_key": "accal-controller-v1",
            "prompt_cache_retention": "24h",
        },
    }


class BuildRequestBodyTests(unittest.TestCase):
    def test_uses_model_from_agent_settings(self):
        body = _build_request_body(_minimal_payload())
        self.assertEqual(body["model"], "gpt-5-mini")

    def test_uses_default_model_when_settings_absent(self):
        payload = _minimal_payload()
        del payload["agent_settings"]
        body = _build_request_body(payload)
        self.assertEqual(body["model"], "gpt-5-mini")

    def test_sets_max_output_tokens(self):
        body = _build_request_body(_minimal_payload())
        self.assertEqual(body["max_output_tokens"], 180)

    def test_sets_prompt_cache_key(self):
        body = _build_request_body(_minimal_payload())
        self.assertEqual(body["prompt_cache_key"], "accal-controller-v1")

    def test_adds_reasoning_when_effort_set(self):
        body = _build_request_body(_minimal_payload())
        self.assertIn("reasoning", body)
        self.assertEqual(body["reasoning"]["effort"], "minimal")

    def test_omits_reasoning_when_effort_empty(self):
        payload = _minimal_payload()
        payload["agent_settings"]["reasoning_effort"] = ""
        body = _build_request_body(payload)
        self.assertNotIn("reasoning", body)

    def test_includes_system_and_user_messages(self):
        body = _build_request_body(_minimal_payload())
        roles = [msg["role"] for msg in body["input"]]
        self.assertIn("system", roles)
        self.assertIn("user", roles)

    def test_controller_state_serialized_into_user_message(self):
        body = _build_request_body(_minimal_payload())
        user_msg = next(m for m in body["input"] if m["role"] == "user")
        user_text = user_msg["content"][0]["text"]
        self.assertIn("S1_overexposed", user_text)

    def test_metadata_includes_scenario_and_retry(self):
        body = _build_request_body(_minimal_payload())
        self.assertEqual(body["metadata"]["scenario"], "S1_overexposed")
        self.assertEqual(body["metadata"]["retry_index"], "0")


class ExtractOutputTextTests(unittest.TestCase):
    def test_extracts_output_text_field(self):
        response = {"output_text": '{"diagnosis": "ok", "actions": [], "confidence": 0.9, "declare_unrecoverable": false}'}
        text = _extract_output_text(response)
        self.assertIn("diagnosis", text)

    def test_extracts_from_output_array(self):
        response = {
            "output": [
                {
                    "content": [
                        {"text": '{"diagnosis": "ok", "actions": [], "confidence": 0.8, "declare_unrecoverable": false}'}
                    ]
                }
            ]
        }
        text = _extract_output_text(response)
        self.assertIn("diagnosis", text)

    def test_raises_on_empty_response(self):
        with self.assertRaises(RuntimeError):
            _extract_output_text({})


@unittest.skipUnless(os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY not set")
class IntegrationTest(unittest.TestCase):
    def test_subprocess_returns_valid_decision(self):
        payload = _minimal_payload()
        result = subprocess.run(
            [sys.executable, "-m", "agentic_camera_calibration.openai_agent"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")
        parsed = json.loads(result.stdout)
        self.assertIsInstance(parsed["diagnosis"], str)
        self.assertIsInstance(parsed["actions"], list)
        self.assertGreaterEqual(parsed["confidence"], 0.0)
        self.assertLessEqual(parsed["confidence"], 1.0)
        self.assertIsInstance(parsed["declare_unrecoverable"], bool)
        for action in parsed["actions"]:
            self.assertIn(action["action"], payload["controller_state"]["allowed_actions"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run unit tests (no API key needed)**

```bash
uv run pytest tests/test_openai_agent.py -v -k "not Integration"
```

Expected: all non-integration tests PASS.

- [ ] **Step 3: Run integration test (requires OPENAI_API_KEY)**

```bash
uv run pytest tests/test_openai_agent.py::IntegrationTest -v
```

Expected: PASS (or skipped if key not set).

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest
```

Expected: all tests PASS (integration skipped if no key).

- [ ] **Step 5: Commit**

```bash
git add tests/test_openai_agent.py
git commit -m "test: add unit and integration tests for openai_agent"
```

---

## Task 4: Add tests for AgentController new methods

**Files:**
- Create: `tests/test_agent_controller.py`

`AgentController` was recently refactored: heuristic fallback removed, `_compact_state` and `_build_payload` added. No tests exist for these new methods.

- [ ] **Step 1: Write the tests**

Create `tests/test_agent_controller.py`:

```python
import unittest

from agentic_camera_calibration.config import ControllerConfig
from agentic_camera_calibration.controllers.agent_controller import AgentController
from agentic_camera_calibration.models import ControllerState, DeviationResult


def _make_state(**overrides) -> ControllerState:
    base = dict(
        run_id="run_01",
        scenario="S1_overexposed",
        retry_index=1,
        frames_total=16,
        frames_active=12,
        frames_reserved_remaining=4,
        mean_brightness=220.0,
        mean_saturation_ratio=0.22,
        mean_blur_score=68.0,
        mean_glare_score=0.38,
        mean_marker_count=9.0,
        mean_charuco_corner_count=11.0,
        mean_coverage_score=0.26,
        calibration_success=False,
        reprojection_error=2.9,
        deviation_result=None,
        reason_codes=["overexposure", "low_corner_count"],
        attempted_actions=[
            {"retry_index": 0, "reason_codes": ["overexposure"]},
            {"retry_index": 1, "reason_codes": ["overexposure", "low_corner_count"]},
            {"retry_index": 2, "reason_codes": ["overexposure", "low_corner_count"]},
        ],
        allowed_actions=[
            "reject_bad_frames",
            "apply_preprocessing",
            "request_additional_views",
            "retry_with_filtered_subset",
            "relax_nominal_prior",
            "declare_unrecoverable",
        ],
    )
    base.update(overrides)
    return ControllerState(**base)


class CompactStateTests(unittest.TestCase):
    def test_history_truncated_to_agent_history_limit(self):
        config = ControllerConfig(agent_history_limit=2)
        controller = AgentController(config)
        state = _make_state()
        compact = controller._compact_state(state)
        self.assertEqual(len(compact["attempted_actions"]), 2)

    def test_metrics_are_rounded(self):
        config = ControllerConfig(agent_history_limit=2)
        controller = AgentController(config)
        state = _make_state(mean_brightness=220.123456)
        compact = controller._compact_state(state)
        self.assertEqual(compact["mean_brightness"], round(220.123456, 3))

    def test_deviation_result_none_is_preserved(self):
        config = ControllerConfig(agent_history_limit=2)
        controller = AgentController(config)
        compact = controller._compact_state(_make_state(deviation_result=None))
        self.assertIsNone(compact["deviation_result"])

    def test_deviation_result_is_compacted(self):
        config = ControllerConfig(agent_history_limit=2)
        controller = AgentController(config)
        deviation = DeviationResult(
            pitch_deg=3.1,
            yaw_deg=-1.2,
            roll_deg=0.5,
            tx_mm=2.0,
            ty_mm=-1.0,
            tz_mm=15.0,
            aggregate_pose_error=4.5,
            within_nominal_bounds=False,
            pose_margin_scale=1.0,
        )
        compact = controller._compact_state(_make_state(deviation_result=deviation))
        self.assertIsNotNone(compact["deviation_result"])
        self.assertEqual(compact["deviation_result"]["pitch_deg"], 3.1)
        self.assertIn("within_nominal_bounds", compact["deviation_result"])


class BuildPayloadTests(unittest.TestCase):
    def test_payload_includes_agent_settings(self):
        config = ControllerConfig(
            agent_command=["dummy"],
            agent_model="gpt-5-mini",
            agent_reasoning_effort="minimal",
            agent_max_output_tokens=180,
            agent_timeout_seconds=45,
            agent_prompt_cache_key="accal-controller-v1",
            agent_prompt_cache_retention="24h",
        )
        controller = AgentController(config)
        payload = controller._build_payload(_make_state())
        settings = payload["agent_settings"]
        self.assertEqual(settings["model"], "gpt-5-mini")
        self.assertEqual(settings["reasoning_effort"], "minimal")
        self.assertEqual(settings["max_output_tokens"], 180)
        self.assertEqual(settings["prompt_cache_key"], "accal-controller-v1")

    def test_payload_includes_required_schema(self):
        config = ControllerConfig(agent_command=["dummy"])
        controller = AgentController(config)
        payload = controller._build_payload(_make_state())
        self.assertIn("required_schema", payload)
        self.assertIn("diagnosis", payload["required_schema"])

    def test_raises_when_agent_command_empty(self):
        config = ControllerConfig(agent_command=[])
        controller = AgentController(config)
        with self.assertRaises(RuntimeError):
            controller.decide(_make_state())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_agent_controller.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_agent_controller.py
git commit -m "test: add coverage for AgentController compact_state and build_payload"
```

---

## Task 5: Add false reject rate and per-scenario metrics to Evaluator

**Files:**
- Modify: `src/agentic_camera_calibration/evaluator.py`
- Create: `tests/test_evaluator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_evaluator.py`:

```python
from agentic_camera_calibration.evaluator import Evaluator
from agentic_camera_calibration.models import CalibrationResult, ExperimentRunResult


def _make_result(mode: str, run_id: str, scenario: str, status: str) -> ExperimentRunResult:
    calib = CalibrationResult(
        success=status == "success",
        reprojection_error=0.2 if status == "success" else 3.0,
        camera_matrix=None,
        distortion_coeffs=None,
        valid_frames_used=10 if status == "success" else 3,
        rejected_frames=2,
    )
    return ExperimentRunResult(
        mode=mode,
        status=status,
        run_id=run_id,
        scenario=scenario,
        retry_index=1,
        calibration_result=calib,
    )


def test_recovery_rate_computed_correctly():
    results = [
        _make_result("baseline", "run_01", "S1_overexposed", "failed"),
        _make_result("heuristic", "run_01", "S1_overexposed", "success"),
        _make_result("agent", "run_01", "S1_overexposed", "success"),
        _make_result("baseline", "run_02", "S1_overexposed", "failed"),
        _make_result("heuristic", "run_02", "S1_overexposed", "failed"),
        _make_result("agent", "run_02", "S1_overexposed", "success"),
    ]
    evaluator = Evaluator()
    metrics = evaluator.compute_paper_metrics(results)
    assert metrics["heuristic"]["recovery_rate"] == 0.5
    assert metrics["agent"]["recovery_rate"] == 1.0


def test_false_reject_rate_computed_correctly():
    results = [
        _make_result("baseline", "run_01", "S0_nominal", "success"),
        _make_result("heuristic", "run_01", "S0_nominal", "failed"),
        _make_result("agent", "run_01", "S0_nominal", "success"),
        _make_result("baseline", "run_02", "S0_nominal", "success"),
        _make_result("heuristic", "run_02", "S0_nominal", "success"),
        _make_result("agent", "run_02", "S0_nominal", "success"),
    ]
    evaluator = Evaluator()
    metrics = evaluator.compute_paper_metrics(results)
    assert metrics["heuristic"]["false_reject_rate"] == 0.5
    assert metrics["agent"]["false_reject_rate"] == 0.0


def test_scenario_breakdown_keys_and_success_rate():
    results = [
        _make_result("baseline", "run_01", "S1_overexposed", "failed"),
        _make_result("heuristic", "run_01", "S1_overexposed", "success"),
        _make_result("agent", "run_01", "S1_overexposed", "success"),
        _make_result("baseline", "run_01", "S2_low_light", "failed"),
        _make_result("heuristic", "run_01", "S2_low_light", "failed"),
        _make_result("agent", "run_01", "S2_low_light", "success"),
    ]
    evaluator = Evaluator()
    breakdown = evaluator.summarize_by_scenario(results)
    assert "S1_overexposed" in breakdown
    assert "S2_low_light" in breakdown
    assert "heuristic" in breakdown["S1_overexposed"]
    assert breakdown["S2_low_light"]["agent"]["success_rate"] == 1.0
    assert breakdown["S2_low_light"]["heuristic"]["success_rate"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_evaluator.py -v
```

Expected: all 3 tests FAIL.

- [ ] **Step 3: Implement the new methods**

Replace the full content of `src/agentic_camera_calibration/evaluator.py`:

```python
from __future__ import annotations

from collections import defaultdict
from statistics import mean

from .models import ExperimentRunResult


class Evaluator:
    def summarize(self, results: list[ExperimentRunResult]) -> dict:
        grouped: dict[str, list[ExperimentRunResult]] = defaultdict(list)
        for result in results:
            grouped[result.mode].append(result)

        summary: dict[str, dict] = {}
        for mode, mode_results in grouped.items():
            success_count = sum(1 for item in mode_results if item.status == "success")
            total = len(mode_results)
            reprojection_errors = [
                item.calibration_result.reprojection_error
                for item in mode_results
                if item.calibration_result is not None
                and item.calibration_result.reprojection_error is not None
            ]
            retries = [item.retry_index for item in mode_results]
            summary[mode] = {
                "runs": total,
                "success_rate": 0.0 if total == 0 else success_count / total,
                "mean_reprojection_error": (
                    None if not reprojection_errors else mean(reprojection_errors)
                ),
                "mean_retries": 0.0 if not retries else mean(retries),
            }
        return summary

    def compute_paper_metrics(self, results: list[ExperimentRunResult]) -> dict:
        """Compute recovery rate and false reject rate per non-baseline mode.

        Recovery rate: fraction of baseline-failed runs recovered by each controller.
        False reject rate: fraction of baseline-success runs that each controller fails.
        """
        by_key: dict[tuple[str, str], dict[str, ExperimentRunResult]] = defaultdict(dict)
        for result in results:
            by_key[(result.run_id, result.scenario)][result.mode] = result

        baseline_failed: list[tuple[str, str]] = []
        baseline_success: list[tuple[str, str]] = []
        for key, modes in by_key.items():
            baseline = modes.get("baseline")
            if baseline is None:
                continue
            if baseline.status == "success":
                baseline_success.append(key)
            else:
                baseline_failed.append(key)

        controller_modes = sorted({r.mode for r in results if r.mode != "baseline"})
        metrics: dict[str, dict] = {}
        for mode in controller_modes:
            recovered = sum(
                1
                for key in baseline_failed
                if by_key[key].get(mode) is not None
                and by_key[key][mode].status == "success"
            )
            false_rejected = sum(
                1
                for key in baseline_success
                if by_key[key].get(mode) is not None
                and by_key[key][mode].status != "success"
            )
            metrics[mode] = {
                "recovery_rate": (
                    0.0 if not baseline_failed else recovered / len(baseline_failed)
                ),
                "false_reject_rate": (
                    0.0 if not baseline_success else false_rejected / len(baseline_success)
                ),
                "baseline_failures_total": len(baseline_failed),
                "baseline_success_total": len(baseline_success),
                "recovered_count": recovered,
                "false_rejected_count": false_rejected,
            }
        return metrics

    def summarize_by_scenario(self, results: list[ExperimentRunResult]) -> dict:
        """Per-scenario success rate and mean reprojection error per mode."""
        by_scenario: dict[str, list[ExperimentRunResult]] = defaultdict(list)
        for result in results:
            by_scenario[result.scenario].append(result)

        breakdown: dict[str, dict] = {}
        for scenario, scenario_results in by_scenario.items():
            by_mode: dict[str, list[ExperimentRunResult]] = defaultdict(list)
            for result in scenario_results:
                by_mode[result.mode].append(result)
            breakdown[scenario] = {}
            for mode, mode_results in by_mode.items():
                total = len(mode_results)
                success_count = sum(1 for r in mode_results if r.status == "success")
                reprojection_errors = [
                    r.calibration_result.reprojection_error
                    for r in mode_results
                    if r.calibration_result is not None
                    and r.calibration_result.reprojection_error is not None
                ]
                breakdown[scenario][mode] = {
                    "runs": total,
                    "success_rate": 0.0 if total == 0 else success_count / total,
                    "mean_reprojection_error": (
                        None if not reprojection_errors else mean(reprojection_errors)
                    ),
                }
        return breakdown
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_evaluator.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/agentic_camera_calibration/evaluator.py tests/test_evaluator.py
git commit -m "feat: add recovery rate, false reject rate, and per-scenario metrics to Evaluator"
```

---

## Task 6: Update Reporter and ExperimentRunner to write paper metrics

**Files:**
- Modify: `src/agentic_camera_calibration/reporter.py`
- Modify: `src/agentic_camera_calibration/experiment_runner.py`

**Important:** `experiment_runner.py` was recently refactored to a two-pass approach:
1. `EmpiricalNominalEstimator.derive_for_dataset()` runs first
2. `orchestrator`, `heuristic_controller`, `agent_controller` are instantiated inside `run_all()` with `effective_config`
3. The final block already writes `nominal_reference.json`

Extend only the reporting tail — add `paper_metrics` and `scenario_breakdown` to the reporter call while preserving the existing `nominal_reference.json` write.

- [ ] **Step 1: Update Reporter**

Replace the full content of `src/agentic_camera_calibration/reporter.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from .models import ExperimentRunResult, to_jsonable


class Reporter:
    def write_results(
        self,
        output_dir: str | Path,
        results: list[ExperimentRunResult],
        summary: dict,
        paper_metrics: dict | None = None,
        scenario_breakdown: dict | None = None,
    ) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "results.json").write_text(
            json.dumps([to_jsonable(result) for result in results], indent=2),
            encoding="utf-8",
        )
        (output_path / "summary.json").write_text(
            json.dumps(to_jsonable(summary), indent=2),
            encoding="utf-8",
        )
        if paper_metrics is not None:
            (output_path / "paper_metrics.json").write_text(
                json.dumps(to_jsonable(paper_metrics), indent=2),
                encoding="utf-8",
            )
        if scenario_breakdown is not None:
            (output_path / "scenario_summary.json").write_text(
                json.dumps(to_jsonable(scenario_breakdown), indent=2),
                encoding="utf-8",
            )
```

- [ ] **Step 2: Update ExperimentRunner**

In `src/agentic_camera_calibration/experiment_runner.py`, find the final block after the run loop and replace it:

```python
        summary = self.evaluator.summarize(results)
        paper_metrics = self.evaluator.compute_paper_metrics(results)
        scenario_breakdown = self.evaluator.summarize_by_scenario(results)
        self.reporter.write_results(
            output_dir, results, summary, paper_metrics, scenario_breakdown
        )
        (output_dir / "nominal_reference.json").write_text(
            json.dumps(nominal_reference, indent=2),
            encoding="utf-8",
        )
        return results
```

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/agentic_camera_calibration/reporter.py src/agentic_camera_calibration/experiment_runner.py
git commit -m "feat: write paper_metrics.json and scenario_summary.json to results"
```

---

## Task 7: Collect mixed-failure dataset runs (manual)

**Files:**
- Create: `dataset/S1S3_mixed/run_01/`, `run_02/`, `run_03/`
- Create: `dataset/S2S4_mixed/run_01/`, `run_02/`, `run_03/`
- Create: `dataset/S1S4_mixed/run_01/`, `run_02/`, `run_03/`

- [ ] **Step 1: Capture Mixed-1 — S1+S3 (overexposure + pose deviation)**

Strong lamp AND tilt camera or board ~8–12 degrees from nominal:

```bash
accal capture-guided --camera-index 0 --output-dir dataset/S1S3_mixed/run_01 --scenario S1S3_mixed --run-id run_01 --primary-count 12 --reserved-count 6
accal capture-guided --camera-index 0 --output-dir dataset/S1S3_mixed/run_02 --scenario S1S3_mixed --run-id run_02 --primary-count 12 --reserved-count 6
accal capture-guided --camera-index 0 --output-dir dataset/S1S3_mixed/run_03 --scenario S1S3_mixed --run-id run_03 --primary-count 12 --reserved-count 6
```

- [ ] **Step 2: Capture Mixed-2 — S2+S4 (low light + height variation)**

Dim lights AND raise or lower camera 5–10 cm:

```bash
accal capture-guided --camera-index 0 --output-dir dataset/S2S4_mixed/run_01 --scenario S2S4_mixed --run-id run_01 --primary-count 12 --reserved-count 6
accal capture-guided --camera-index 0 --output-dir dataset/S2S4_mixed/run_02 --scenario S2S4_mixed --run-id run_02 --primary-count 12 --reserved-count 6
accal capture-guided --camera-index 0 --output-dir dataset/S2S4_mixed/run_03 --scenario S2S4_mixed --run-id run_03 --primary-count 12 --reserved-count 6
```

- [ ] **Step 3: Capture Mixed-3 — S1+S4 (overexposure + height variation)**

Strong lamp AND height change:

```bash
accal capture-guided --camera-index 0 --output-dir dataset/S1S4_mixed/run_01 --scenario S1S4_mixed --run-id run_01 --primary-count 12 --reserved-count 6
accal capture-guided --camera-index 0 --output-dir dataset/S1S4_mixed/run_02 --scenario S1S4_mixed --run-id run_02 --primary-count 12 --reserved-count 6
accal capture-guided --camera-index 0 --output-dir dataset/S1S4_mixed/run_03 --scenario S1S4_mixed --run-id run_03 --primary-count 12 --reserved-count 6
```

- [ ] **Step 4: Audit the mixed runs**

```bash
accal --config config/defaults.toml audit-dataset --dataset-root dataset --output-dir results/dataset_audit
```

Check `results/dataset_audit/dataset_audit.md` — all 9 mixed runs should appear with `usable: True`. Also verify `nominal_reference` section shows `source: empirical_s0` derived from multiple S0 runs.

- [ ] **Step 5: Commit mixed dataset metadata**

```bash
git add dataset/S1S3_mixed dataset/S2S4_mixed dataset/S1S4_mixed
git commit -m "data: add mixed-failure dataset runs (S1+S3, S2+S4, S1+S4)"
```

---

## Task 8: Run full experiment

**Files:** (no code changes — operational only)

- [ ] **Step 1: Verify OPENAI_API_KEY is set**

```bash
echo $OPENAI_API_KEY
```

Expected: non-empty key string.

- [ ] **Step 2: Run experiments across all scenarios**

```bash
accal --config config/defaults.toml run-experiments --dataset-root dataset --output-dir results
```

Runs baseline, heuristic, and agent across all discovered runs (~58 runs × 3 modes). The agent path calls `openai_agent.py` via subprocess for each recovery decision. Expect 20–40 minutes.

- [ ] **Step 3: Verify output files exist**

```bash
ls results/
```

Expected: `results.json`, `summary.json`, `paper_metrics.json`, `scenario_summary.json`, `nominal_reference.json`.

- [ ] **Step 4: Spot-check paper_metrics.json**

```bash
uv run python -c "
import json
m = json.load(open('results/paper_metrics.json'))
for mode, vals in m.items():
    print(f'{mode}: recovery={vals[\"recovery_rate\"]:.2f}, false_reject={vals[\"false_reject_rate\"]:.2f}')
"
```

Expected: agent recovery rate >= heuristic; agent false reject rate <= heuristic.

- [ ] **Step 5: Spot-check scenario_summary.json**

```bash
uv run python -c "
import json
s = json.load(open('results/scenario_summary.json'))
for scenario, modes in sorted(s.items()):
    for mode, vals in sorted(modes.items()):
        print(f'{scenario}/{mode}: success={vals[\"success_rate\"]:.2f}')
"
```

Expected: S0 baseline ~1.0; S1–S4 baseline lower; heuristic and agent higher on disturbance scenarios.

- [ ] **Step 6: Check nominal_reference.json**

```bash
uv run python -c "
import json
n = json.load(open('results/nominal_reference.json'))
print('source:', n['source'])
print('derived from', n['run_count'], 'S0 runs:', n['run_ids'])
print('reference tz_mm:', n['tz_mm'])
"
```

Expected: `source: empirical_s0`, multiple run IDs, `tz_mm` near actual camera distance.

---

## Self-Review Checklist

**Spec coverage:**
- [x] Compound heuristic rules → Task 1
- [x] Tests for `nominal_reference.py` (`is_eligible`, `default_nominal`, `to_config`) → Task 2
- [x] Tests for `openai_agent.py` (`_build_request_body`, `_extract_output_text`, integration) → Task 3
- [x] Tests for `AgentController._compact_state` and `_build_payload` → Task 4
- [x] Recovery rate + false reject rate → Task 5
- [x] Per-scenario breakdown → Task 5 + Task 6
- [x] `paper_metrics.json` + `scenario_summary.json` written → Task 6
- [x] `nominal_reference.json` preserved in ExperimentRunner → Task 6 Step 2
- [x] Mixed-failure dataset → Task 7
- [x] Full experiment run → Task 8
- [x] OpenAI agent, config wiring, ControllerConfig fields: already done, no tasks needed

**Placeholder scan:** None found. All code blocks are complete.

**Type consistency:** `compute_paper_metrics` and `summarize_by_scenario` defined in Task 5, called in Task 6 with matching signatures. `Reporter.write_results` updated in Task 6 Step 1 matches the call site in Task 6 Step 2. `nominal_reference_to_config` tested in Task 2 matches its definition in `nominal_reference.py`. `_compact_state` and `_build_payload` tested in Task 4 match their definitions in the refactored `agent_controller.py`.
