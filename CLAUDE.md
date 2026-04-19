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
accal capture-reference --camera-index 0 --output-dir dataset/S3_pose_deviation/run_01/reference_frames --scenario S3_pose_deviation --run-id run_01 --frame-count 3
```

**Audit captured dataset runs:**
```bash
accal --config config/defaults.toml audit-dataset --dataset-root dataset --output-dir results/dataset_audit
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

The system runs three calibration modes on every dataset run — **baseline** (no controller), **heuristic**, and **agent** — to compare recovery performance. This is the core paper experiment: measuring recovery rate and false reject rate across controlled failure scenarios.

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

`CalibrationOrchestrator` (`orchestrator.py`) drives this retry loop. `ExperimentRunner` (`experiment_runner.py`) does a **two-pass** run: first derives an empirical nominal pose from S0 runs via `EmpiricalNominalEstimator`, then runs the orchestrator three times per dataset run (baseline/heuristic/agent) using that pose as the reference.

### Controllers

All controllers implement `RecoveryController.decide(state: ControllerState) -> RecoveryDecision` (`controllers/base.py`).

- **`HeuristicController`** — rule-based: single-condition rules (saturation, blur, lighting, corner count, coverage, pose) plus three compound-condition rules: overexposure+low_corner_count → CLAHE; partial_visibility+low_marker_coverage → edge_and_tilt views; pose_out_of_range blocked when overexposure is present.
- **`AgentController`** — calls an external subprocess with a compact JSON state on stdin, reads a `{diagnosis, actions, confidence, declare_unrecoverable}` JSON object on stdout. No heuristic fallback — raises `RuntimeError` if the command cannot be resolved.

### Agent backend selection

`AgentController._resolved_command()` picks the subprocess from `agent_backend` in config (unless `agent_command` is set explicitly as a full override):

| `agent_backend` | Module invoked | API key required |
|---|---|---|
| `"openai"` (default) | `openai_agent.py` — OpenAI Responses API | `OPENAI_API_KEY` |
| `"claude"` | `claude_agent.py` — Anthropic Messages API | `ANTHROPIC_API_KEY` |
| `"lm_studio"` | `lm_studio_agent.py` — OpenAI-compatible Chat Completions | none |

All three agents share the same stdin/stdout JSON contract. `lm_studio_agent.py` targets `lm_studio_base_url` (default `http://localhost:1234/v1`) and sets `temperature=0` for deterministic output.

To switch backends, change one line in `config/defaults.toml`:
```toml
agent_backend = "claude"          # and set ANTHROPIC_API_KEY
agent_backend = "lm_studio"       # and start LM Studio local server
```

To wire a fully custom agent subprocess:
```toml
agent_command = ["python", "my_agent.py"]   # overrides agent_backend
```

### Empirical nominal reference

Before experiments run, `EmpiricalNominalEstimator` (`nominal_reference.py`) analyzes S0 runs and computes a mean pose from those with reprojection error < 1.0 px, usable rate ≥ 0.75, and no lighting failure codes. This replaces the hardcoded `[nominal_pose]` in `defaults.toml` and prevents false `pose_out_of_range` alarms. If no S0 runs qualify, it falls back to `config/defaults.toml` values. The derived reference is written to `results/nominal_reference.json`.

`DatasetAuditor` (`dataset_auditor.py`) runs the same two-pass logic independently for audit reports.

### Failure reason codes

`FailureDetector.evaluate()` produces these string codes (used as keys by both controllers):

| Code | Trigger |
|---|---|
| `calibration_failed` | `CalibrationResult.success == False` |
| `high_reprojection_error` | reprojection error > `max_reprojection_error` (2.0 px) |
| `insufficient_usable_frames` | usable frame count < `min_usable_frames` (8) |
| `overexposure` | mean saturation ratio > 0.15 |
| `low_light` | mean brightness < 45 |
| `blur_or_low_detail` | mean blur score < 50 |
| `glare` | mean glare score > 0.35 |
| `low_corner_count` | mean ChArUco corners < 12 |
| `low_marker_coverage` | mean coverage score < 0.35 |
| `partial_visibility` | no frames had successful detection |
| `pose_out_of_range` | deviation not within nominal bounds |

### Recovery actions

| Action | Effect |
|---|---|
| `reject_bad_frames` | Filter active frames by quality/detection thresholds |
| `apply_preprocessing` | Apply CLAHE, gamma correction, or contrast normalization |
| `request_additional_views` | Pull frames from the reserved pool (tag-ranked) |
| `retry_with_filtered_subset` | Keep top-K frames scored by quality + detection |
| `relax_nominal_prior` | Scale pose tolerance (up to `max_pose_margin_scale`) |
| `declare_unrecoverable` | Abort and mark run as unrecoverable |

**Reserved frame selection:** `capture-guided` assigns tags (`center`, `edge`, `tilt`, `distance`, `diverse`) via `DEFAULT_CAPTURE_PLAN` in `capture.py`. `RecoveryExecutor._pull_reserved_frames` ranks reserved frames by tag to match the requested pattern (`edge_coverage`, `edge_and_tilt`, `general_diversity`).

### Configuration

`config/defaults.toml` is the single source of truth. `load_config(path)` (`config.py`) merges TOML sections into the `CalibrationConfig` dataclass tree. Key sections: `[board]`, `[quality]`, `[failure]`, `[controller]`, `[nominal_pose]`, `[experiment]`.

Notable `[controller]` fields: `agent_backend`, `agent_model` (OpenAI), `claude_agent_model`, `lm_studio_model`, `lm_studio_base_url`, `agent_history_limit` (how many past attempts to include in compact state), `agent_max_output_tokens`.

### Dataset layout

```
dataset/
  S0_nominal/            # good lighting, proper pose, full visibility (baseline)
  S1_overexposed/        # strong lamp, saturated regions
  S2_low_light/          # dim environment, noisy detection
  S3_pose_deviation/     # tilted camera or board, simulated mount error
  S4_height_variation/   # camera height changed
  S5_partial_visibility/ # board cropped or partially occluded
    run_01/
      frame_001.png
      ...
      metadata.json      # scenario, run_id, board_config, reserved_frame_ids, frame_metadata
```

Frames beyond `initial_frame_count` (default 12) are auto-classified as reserved. They can be listed explicitly in `metadata.json["reserved_frame_ids"]`.

### Output files

| File | Content |
|---|---|
| `results/results.json` | One `ExperimentRunResult` per (run × mode) |
| `results/summary.json` | Success rate, mean reprojection error, mean retries per mode |
| `results/paper_metrics.json` | Recovery rate + false reject rate across baseline/controller modes |
| `results/scenario_summary.json` | Per-scenario breakdown of the same metrics |
| `results/nominal_reference.json` | Derived nominal pose used for the experiment run |
| `results/dataset_audit/dataset_audit.json` + `.md` | Per-run quality audit with recapture recommendations |

### Key data models (`models.py`)

- `ControllerState` — aggregated metrics fed to both controllers; compacted by `AgentController._compact_state()` before sending to subprocess
- `RecoveryDecision` — `{diagnosis, actions, confidence, declare_unrecoverable}`
- `ExperimentRunResult` — final outcome per run/mode including `calibration_result`, `deviation_result`, `attempted_actions`
