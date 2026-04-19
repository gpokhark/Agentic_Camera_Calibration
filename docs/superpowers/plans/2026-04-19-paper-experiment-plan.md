# Paper Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire a real Claude LLM agent into the calibration recovery pipeline, strengthen the heuristic baseline, add two-sided metrics (recovery rate + false reject rate), collect mixed-failure data, and run the full experiment to produce paper-ready results.

**Architecture:** The existing `AgentController` already calls an external subprocess via `agent_command`. We create a `claude_agent.py` script that reads a JSON payload from stdin, calls the Claude API, and returns a `RecoveryDecision` JSON to stdout. The heuristic gets compound-condition rules added. The `Evaluator` gains cross-mode false reject rate computation. Everything else (executor, orchestrator, dataset) is unchanged.

**Tech Stack:** Python 3.12, `anthropic` SDK, OpenCV, uv, pytest

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `pyproject.toml` | Modify | Add `anthropic` dependency |
| `src/agentic_camera_calibration/claude_agent.py` | Create | Claude API subprocess entry point |
| `config/defaults.toml` | Modify | Set `agent_command` to invoke `claude_agent.py` |
| `src/agentic_camera_calibration/controllers/heuristic_controller.py` | Modify | Add 3 compound-condition rules |
| `src/agentic_camera_calibration/evaluator.py` | Modify | Add false reject rate + per-scenario breakdown |
| `src/agentic_camera_calibration/reporter.py` | Modify | Write `scenario_summary.json` |
| `tests/test_heuristic_controller.py` | Modify | Add tests for new compound rules |
| `tests/test_evaluator.py` | Create | Tests for false reject rate + scenario summary |
| `tests/test_claude_agent.py` | Create | Test agent stdin/stdout contract |

---

## Task 1: Add anthropic dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add anthropic to dependencies**

Edit `pyproject.toml` — replace the `dependencies` block:

```toml
dependencies = [
  "numpy>=2.2",
  "opencv-contrib-python>=4.11",
  "anthropic>=0.40",
]
```

- [ ] **Step 2: Sync environment**

```bash
uv sync --extra dev
```

Expected: resolves without error, `anthropic` appears in the lock.

- [ ] **Step 3: Verify import**

```bash
uv run python -c "import anthropic; print(anthropic.__version__)"
```

Expected: prints a version string like `0.40.x`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add anthropic SDK dependency"
```

---

## Task 2: Create claude_agent.py subprocess entry point

**Files:**
- Create: `src/agentic_camera_calibration/claude_agent.py`
- Create: `tests/test_claude_agent.py`

The `AgentController` already calls `agent_command` as a subprocess, pipes a JSON payload to stdin, and reads a JSON `RecoveryDecision` from stdout. The payload shape is:

```json
{
  "system_prompt": "...",
  "controller_state": { ... },
  "required_schema": { ... }
}
```

- [ ] **Step 1: Write the failing test**

Create `tests/test_claude_agent.py`:

```python
import json
import subprocess
import sys


MINIMAL_PAYLOAD = {
    "system_prompt": "You are a calibration recovery controller. Return JSON only.",
    "controller_state": {
        "run_id": "test_run",
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
}


def test_agent_returns_valid_recovery_decision():
    result = subprocess.run(
        [sys.executable, "-m", "agentic_camera_calibration.claude_agent"],
        input=json.dumps(MINIMAL_PAYLOAD),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    parsed = json.loads(result.stdout)
    assert isinstance(parsed["diagnosis"], str) and parsed["diagnosis"]
    assert isinstance(parsed["actions"], list)
    assert 0.0 <= parsed["confidence"] <= 1.0
    assert isinstance(parsed["declare_unrecoverable"], bool)
    for action in parsed["actions"]:
        assert action["action"] in MINIMAL_PAYLOAD["controller_state"]["allowed_actions"]
        assert isinstance(action["params"], dict)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_claude_agent.py::test_agent_returns_valid_recovery_decision -v
```

Expected: FAIL — `ModuleNotFoundError` or similar (file doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `src/agentic_camera_calibration/claude_agent.py`:

```python
"""Subprocess entry point for the Claude-based calibration recovery agent.

Reads a JSON payload from stdin:
  {
    "system_prompt": str,
    "controller_state": dict,
    "required_schema": dict
  }

Writes a JSON RecoveryDecision to stdout:
  {
    "diagnosis": str,
    "actions": [{"action": str, "params": dict}, ...],
    "confidence": float,
    "declare_unrecoverable": bool
  }
"""

from __future__ import annotations

import json
import sys

import anthropic

SYSTEM_PROMPT_SUFFIX = """
Important rules:
1. Only use actions from allowed_actions in the controller_state.
2. Base your reasoning only on the provided structured metrics.
3. Do not claim calibration is correct if the evidence is weak.
4. Prefer minimal interventions — at most 3 actions per decision.
5. If repeated failures indicate recovery is unlikely, set declare_unrecoverable to true.
6. Return valid JSON only. No markdown fences, no prose outside the JSON object.
7. The output must match the required_schema exactly.
8. Prioritise improving image evidence (reject bad frames, preprocessing) before relaxing
   geometric assumptions (relax_nominal_prior) when image quality is poor.

Metric interpretation:
- mean_saturation_ratio > 0.15 → likely overexposure or glare
- mean_blur_score < 50 → focus or motion blur
- mean_charuco_corner_count < 12 or mean_coverage_score < 0.35 → insufficient target evidence
- pose_out_of_range only meaningful when image quality is adequate
- If attempted_actions shows the same reason_codes repeating, declare_unrecoverable
"""

USER_PROMPT_TEMPLATE = """\
Calibration recovery request.

Current controller state:
{state_json}

Required output schema:
{schema_json}

Select recovery actions and return a JSON object matching the schema above. No other text.
"""


def main() -> None:
    raw = sys.stdin.read()
    payload = json.loads(raw)

    system_prompt: str = payload.get("system_prompt", "")
    controller_state: dict = payload["controller_state"]
    required_schema: dict = payload.get("required_schema", {})

    full_system = system_prompt.strip() + "\n" + SYSTEM_PROMPT_SUFFIX.strip()

    user_prompt = USER_PROMPT_TEMPLATE.format(
        state_json=json.dumps(controller_state, indent=2),
        schema_json=json.dumps(required_schema, indent=2),
    )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=full_system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = message.content[0].text.strip()
    decision = json.loads(raw_text)

    sys.stdout.write(json.dumps(decision))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Ensure `ANTHROPIC_API_KEY` is set in your environment, then:

```bash
uv run pytest tests/test_claude_agent.py::test_agent_returns_valid_recovery_decision -v
```

Expected: PASS. If the key is not set, set it first:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 5: Commit**

```bash
git add src/agentic_camera_calibration/claude_agent.py tests/test_claude_agent.py
git commit -m "feat: add Claude API subprocess agent entry point"
```

---

## Task 3: Wire agent_command into config

**Files:**
- Modify: `config/defaults.toml`

- [ ] **Step 1: Add agent_command to [controller] section**

Edit `config/defaults.toml` — add one line inside `[controller]`:

```toml
[controller]
allowed_actions = [
  "reject_bad_frames",
  "apply_preprocessing",
  "request_additional_views",
  "retry_with_filtered_subset",
  "relax_nominal_prior",
  "declare_unrecoverable",
]
max_actions_per_decision = 3
agent_command = ["uv", "run", "python", "-m", "agentic_camera_calibration.claude_agent"]
```

- [ ] **Step 2: Verify config loads correctly**

```bash
uv run python -c "
from agentic_camera_calibration.config import load_config
cfg = load_config('config/defaults.toml')
print(cfg.controller.agent_command)
"
```

Expected: `['uv', 'run', 'python', '-m', 'agentic_camera_calibration.claude_agent']`

- [ ] **Step 3: Verify AgentController no longer falls back to heuristic**

```bash
uv run python -c "
from agentic_camera_calibration.config import load_config
from agentic_camera_calibration.controllers import AgentController
cfg = load_config('config/defaults.toml')
ac = AgentController(cfg.controller)
print('agent_command set:', bool(cfg.controller.agent_command))
"
```

Expected: `agent_command set: True`

- [ ] **Step 4: Commit**

```bash
git add config/defaults.toml
git commit -m "config: wire Claude agent_command for experiment runs"
```

---

## Task 4: Strengthen heuristic with compound-condition rules

**Files:**
- Modify: `src/agentic_camera_calibration/controllers/heuristic_controller.py`
- Modify: `tests/test_heuristic_controller.py`

Three gaps in the current heuristic relative to the architecture doc:

1. **Overexposure + pose_out_of_range**: current code may try `relax_nominal_prior` even when saturation is high. Fix: add `mean_saturation_ratio <= 0.15` guard to the pose-relaxation rule.
2. **partial_visibility + low_marker_coverage**: missing — should use `edge_and_tilt` pattern with count=6 instead of generic `edge_coverage`.
3. **overexposure + low_corner_count together**: should apply `apply_preprocessing(clahe)` in addition to frame rejection, not just `reject_bad_frames` alone.

- [ ] **Step 1: Write failing tests for the three compound cases**

Add to `tests/test_heuristic_controller.py`:

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
        # Should not relax pose when image quality is poor (high saturation)
        self.assertNotIn("relax_nominal_prior", action_names)

    def test_uses_edge_and_tilt_pattern_for_partial_visibility_with_low_coverage(self) -> None:
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
        additional_views = [
            a for a in decision.actions if a["action"] == "request_additional_views"
        ]
        self.assertTrue(len(additional_views) > 0)
        self.assertEqual(additional_views[0]["params"]["pattern"], "edge_and_tilt")

    def test_adds_preprocessing_when_overexposure_and_low_corners_together(self) -> None:
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

Expected: the 3 new tests FAIL, existing 2 tests PASS.

- [ ] **Step 3: Update heuristic_controller.py with compound rules**

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

        # --- Compound-condition rules (H8–H10) ---

        # H8: overexposure + low_corner_count → also apply CLAHE to recover contrast
        if (
            "overexposure" in reasons
            and "low_corner_count" in reasons
            and "apply_preprocessing" in state.allowed_actions
        ):
            actions.append({"action": "apply_preprocessing", "params": {"mode": "clahe"}})

        # H9: partial_visibility + low_marker_coverage → use edge_and_tilt pattern (more targeted)
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
            # Standard single-signal coverage/corner rules
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

        # H10: pose relaxation only when image quality is adequate (no overexposure, no glare, no blur)
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

## Task 5: Add false reject rate and per-scenario metrics to Evaluator

**Files:**
- Modify: `src/agentic_camera_calibration/evaluator.py`
- Create: `tests/test_evaluator.py`

**Definitions:**
- **False reject**: a run where the controller fails/declares-unrecoverable but the baseline succeeded on the same `(run_id, scenario)`.
- **Recovery rate**: among runs the baseline failed, how many did the controller succeed on.

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
        # baseline fails on run_01, heuristic recovers it
        _make_result("baseline", "run_01", "S1_overexposed", "failed"),
        _make_result("heuristic", "run_01", "S1_overexposed", "success"),
        _make_result("agent", "run_01", "S1_overexposed", "success"),
        # baseline fails on run_02, neither recovers
        _make_result("baseline", "run_02", "S1_overexposed", "failed"),
        _make_result("heuristic", "run_02", "S1_overexposed", "failed"),
        _make_result("agent", "run_02", "S1_overexposed", "success"),
    ]
    evaluator = Evaluator()
    metrics = evaluator.compute_paper_metrics(results)
    # heuristic recovered 1 of 2 baseline failures
    assert metrics["heuristic"]["recovery_rate"] == 0.5
    # agent recovered 2 of 2 baseline failures
    assert metrics["agent"]["recovery_rate"] == 1.0


def test_false_reject_rate_computed_correctly():
    results = [
        # baseline succeeds on S0 run_01
        _make_result("baseline", "run_01", "S0_nominal", "success"),
        # heuristic aborts it (false reject)
        _make_result("heuristic", "run_01", "S0_nominal", "failed"),
        # agent passes it correctly
        _make_result("agent", "run_01", "S0_nominal", "success"),
        # baseline succeeds on S0 run_02, both controllers also pass
        _make_result("baseline", "run_02", "S0_nominal", "success"),
        _make_result("heuristic", "run_02", "S0_nominal", "success"),
        _make_result("agent", "run_02", "S0_nominal", "success"),
    ]
    evaluator = Evaluator()
    metrics = evaluator.compute_paper_metrics(results)
    # heuristic false rejected 1 of 2 baseline-success runs
    assert metrics["heuristic"]["false_reject_rate"] == 0.5
    # agent false rejected 0 of 2
    assert metrics["agent"]["false_reject_rate"] == 0.0


def test_scenario_breakdown_keys():
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_evaluator.py -v
```

Expected: all 3 tests FAIL — `compute_paper_metrics` and `summarize_by_scenario` don't exist yet.

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

        controller_modes = sorted(
            {r.mode for r in results if r.mode != "baseline"}
        )
        metrics: dict[str, dict] = {}
        for mode in controller_modes:
            recovered = sum(
                1
                for key in baseline_failed
                if by_key[key].get(mode, None) is not None
                and by_key[key][mode].status == "success"
            )
            false_rejected = sum(
                1
                for key in baseline_success
                if by_key[key].get(mode, None) is not None
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

## Task 6: Update Reporter to write paper metrics

**Files:**
- Modify: `src/agentic_camera_calibration/reporter.py`
- Modify: `src/agentic_camera_calibration/experiment_runner.py`

- [ ] **Step 1: Update Reporter to write two new output files**

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

- [ ] **Step 2: Update ExperimentRunner to pass paper metrics to reporter**

Edit `src/agentic_camera_calibration/experiment_runner.py` — replace the last 4 lines of `run_all`:

```python
        summary = self.evaluator.summarize(results)
        paper_metrics = self.evaluator.compute_paper_metrics(results)
        scenario_breakdown = self.evaluator.summarize_by_scenario(results)
        self.reporter.write_results(
            output_dir, results, summary, paper_metrics, scenario_breakdown
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

This task is physical — it requires the camera and the desk setup. Follow these steps for each mixed scenario.

- [ ] **Step 1: Capture Mixed-1 — S1+S3 (overexposure + pose deviation)**

Point the strong lamp at the board (same as S1) AND tilt the camera or board by ~8–12 degrees (same as S3). Capture 3 runs:

```bash
accal capture-guided --camera-index 0 --output-dir dataset/S1S3_mixed/run_01 --scenario S1S3_mixed --run-id run_01 --primary-count 12 --reserved-count 6
accal capture-guided --camera-index 0 --output-dir dataset/S1S3_mixed/run_02 --scenario S1S3_mixed --run-id run_02 --primary-count 12 --reserved-count 6
accal capture-guided --camera-index 0 --output-dir dataset/S1S3_mixed/run_03 --scenario S1S3_mixed --run-id run_03 --primary-count 12 --reserved-count 6
```

Expected: each run folder contains `frame_001.png` through `frame_018.png` and `metadata.json`.

- [ ] **Step 2: Capture Mixed-2 — S2+S4 (low light + height variation)**

Dim the lights (same as S2) AND raise or lower the camera by 5–10 cm on books (same as S4):

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

Check `results/dataset_audit/dataset_audit.md` — all 9 mixed runs should appear with `usable: True`.

- [ ] **Step 5: Commit mixed dataset metadata**

```bash
git add dataset/S1S3_mixed dataset/S2S4_mixed dataset/S1S4_mixed
git commit -m "data: add mixed-failure dataset runs (S1+S3, S2+S4, S1+S4)"
```

---

## Task 8: Run full experiment

**Files:** (no code changes — operational only)

- [ ] **Step 1: Verify ANTHROPIC_API_KEY is set**

```bash
echo $ANTHROPIC_API_KEY
```

Expected: non-empty key string.

- [ ] **Step 2: Run experiments across all scenarios**

```bash
accal --config config/defaults.toml run-experiments --dataset-root dataset --output-dir results
```

This runs baseline, heuristic, and agent across all runs in S0–S4 and the 3 mixed scenarios. With 58 runs × 3 modes = 174 orchestrator calls, and up to 3 retries per agent call, expect this to take 20–40 minutes depending on API latency.

- [ ] **Step 3: Verify output files exist**

```bash
ls results/
```

Expected: `results.json`, `summary.json`, `paper_metrics.json`, `scenario_summary.json`.

- [ ] **Step 4: Spot-check paper_metrics.json**

```bash
uv run python -c "
import json
m = json.load(open('results/paper_metrics.json'))
for mode, vals in m.items():
    print(f'{mode}: recovery={vals[\"recovery_rate\"]:.2f}, false_reject={vals[\"false_reject_rate\"]:.2f}')
"
```

Expected: agent recovery rate >= heuristic recovery rate on mixed scenarios; agent false reject rate <= heuristic false reject rate on S0.

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

Expected: S0 baseline ~1.0 success rate; S1–S4 baseline lower; heuristic and agent higher than baseline on disturbance scenarios.

---

## Self-Review Checklist

**Spec coverage:**
- [x] Wire Claude API agent_command → Task 2 + Task 3
- [x] Strengthen heuristic compound rules → Task 4
- [x] Collect 9 mixed-failure runs → Task 7
- [x] Run full experiment → Task 8
- [x] Recovery rate metric → Task 5
- [x] False reject rate metric → Task 5
- [x] Per-scenario breakdown → Task 5 + Task 6
- [x] `paper_metrics.json` and `scenario_summary.json` written → Task 6

**Placeholder scan:** None found. All code blocks are complete.

**Type consistency:** `compute_paper_metrics` and `summarize_by_scenario` defined in Task 5 and called in Task 6 with matching signatures. `Reporter.write_results` signature updated in Task 6 matches the call in `experiment_runner.py`.
