# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Setup (uses uv):**
```bash
uv sync --extra dev
```

**Run experiments:**
```bash
accal --config config/defaults.toml run-experiments --dataset-root dataset --output-dir results
```

**Capture dataset frames from USB camera:**
```bash
accal capture --camera-index 0 --output-dir dataset/S0_nominal/run_01 --scenario S0_nominal --run-id run_01
accal capture-guided --camera-index 0 --output-dir dataset/S0_nominal/run_01 --scenario S0_nominal --run-id run_01 --primary-count 12 --reserved-count 6
```

**Run all tests:**
```bash
uv run pytest
```

**Run a single test file:**
```bash
uv run pytest tests/test_failure_detector.py
```

**Lint:**
```bash
uv run ruff check src tests
```

## Architecture

The system runs three calibration modes on every dataset run — **baseline** (no controller), **heuristic**, and **agent** — to compare recovery performance.

### Pipeline (per run)

```
frames → CharucoDetector → QualityAnalyzer → CalibrationEngine
                                                     ↓
                                           DeviationAnalyzer → FailureDetector
                                                                      ↓ (if fail)
                                                            RecoveryController.decide()
                                                                      ↓
                                                            RecoveryExecutor.execute()
                                                                      ↓
                                                              re-run calibration
```

The `CalibrationOrchestrator` (`orchestrator.py`) drives this retry loop. `ExperimentRunner` (`experiment_runner.py`) runs the orchestrator three times per dataset run (baseline/heuristic/agent) and hands results to `Evaluator` and `Reporter`.

### Controllers

All controllers implement `RecoveryController.decide(state: ControllerState) -> RecoveryDecision` (`controllers/base.py`).

- **`HeuristicController`** — rule-based: maps reason codes and metric thresholds to a fixed action list.
- **`AgentController`** — calls an external process (`config.controller.agent_command`) via subprocess, passing a JSON payload with `controller_state` and `system_prompt`. Falls back to `HeuristicController` when `agent_command` is empty.

### Recovery actions (allowed set configured in `config/defaults.toml`)

| Action | Effect |
|---|---|
| `reject_bad_frames` | Filter active frames by quality/detection thresholds |
| `apply_preprocessing` | Apply CLAHE, gamma correction, or contrast normalization |
| `request_additional_views` | Pull frames from the reserved pool (tag-ranked) |
| `retry_with_filtered_subset` | Keep top-K frames scored by quality + detection |
| `relax_nominal_prior` | Scale pose tolerance (up to `max_pose_margin_scale`) |
| `declare_unrecoverable` | Abort and mark run as unrecoverable |

### Configuration

`config/defaults.toml` is the single source of truth. `load_config(path)` (`config.py`) merges TOML sections into the `CalibrationConfig` dataclass tree. Key sections: `[board]`, `[quality]`, `[failure]`, `[controller]`, `[nominal_pose]`, `[experiment]`.

To wire an agent command:
```toml
[controller]
agent_command = ["python", "my_agent.py"]
```
The subprocess receives JSON on stdin and must return a JSON object matching `{diagnosis, actions, confidence, declare_unrecoverable}`.

### Dataset layout

```
dataset/
  S0_nominal/
    run_01/
      frame_001.png
      ...
      metadata.json   # scenario, run_id, board_config, reserved_frame_ids, frame_metadata
```

Frames beyond `initial_frame_count` (default 12) are auto-classified as reserved. They can be explicitly listed in `metadata.json["reserved_frame_ids"]`.

### Output

`results/results.json` — one `ExperimentRunResult` per (run × mode).  
`results/summary.json` — success rate, mean reprojection error, mean retries per mode.

### Key data models (`models.py`)

- `ControllerState` — aggregated metrics fed to both controllers
- `RecoveryDecision` — `{diagnosis, actions, confidence, declare_unrecoverable}`
- `ExperimentRunResult` — final outcome per run/mode including `calibration_result`, `deviation_result`, `attempted_actions`
