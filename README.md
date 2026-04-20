# Agentic Camera Calibration

This repository implements a single-camera ChArUco calibration experiment
pipeline for comparing four recovery modes under controlled disturbance
scenarios:

- `baseline`: one-pass calibration with no recovery controller
- `heuristic`: rule-based recovery over a fixed action space
- `learned`: lightweight structured-policy baseline over the same action space
- `agent`: external LLM-backed recovery over the same action space

The project is designed around an offline experimental loop:

1. capture scenario-based runs from a USB camera
2. audit the dataset quality and disturbance fit
3. run baseline, heuristic, learned, and agent comparisons
4. export summary metrics and per-run outputs for analysis

Reference design notes live in [docs/PRD.md](docs/PRD.md),
[docs/architecture.md](docs/architecture.md), and
[docs/dataset_capture_playbook.md](docs/dataset_capture_playbook.md). The
fixed-target benchmark protocol is documented in
[docs/fixed_target_eol_dataset_plan.md](docs/fixed_target_eol_dataset_plan.md).
The research north star for keeping the repo aligned with a publishable paper
is documented in [docs/paper_north_star.md](docs/paper_north_star.md).

## Setup

Create the virtual environment with `uv`:

```powershell
$env:UV_CACHE_DIR = "$PWD\\.uv-cache"
uv venv --python 3.12 .venv
```

Install dependencies:

```powershell
$env:UV_CACHE_DIR = "$PWD\\.uv-cache"
uv sync
```

Run the unit tests:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

## Complete Workflow

The normal workflow is capture -> audit -> experiment run -> inspect results.

### 1. Capture a Dataset Run

Use guided capture for the main run:

```powershell
.venv\Scripts\accal capture-guided `
  --camera-index 0 `
  --output-dir dataset/S0_nominal/run_01 `
  --scenario S0_nominal `
  --run-id run_01 `
  --primary-count 12 `
  --reserved-count 6 `
  --setup-type pilot_moving_target `
  --dataset-split dev `
  --notes "nominal capture run"
```

Use fixed reference-frame capture when you want a small set of stable comparison
images for disturbed scenarios:

```powershell
.venv\Scripts\accal capture-reference `
  --camera-index 0 `
  --output-dir dataset/S3_pose_deviation/run_01/reference_frames `
  --scenario S3_pose_deviation `
  --run-id run_01 `
  --frame-count 3 `
  --setup-type benchmark_fixed_target `
  --dataset-split eval `
  --notes "fixed reference frames before disturbed capture"
```

What gets written:

- `frame_001.png`, `frame_002.png`, ... for guided capture
- `ref_001.png`, `ref_002.png`, ... for reference capture
- `metadata.json` describing scenario, run id, setup type, dataset split, board config, notes, and frame tags

Useful metadata values:

- `--setup-type pilot_moving_target` for the older moving-board development workflow
- `--setup-type benchmark_fixed_target` for the new fixed-target EOL-style benchmark
- `--dataset-split train`, `dev`, or `eval` when you want to separate tuning and final evaluation data

For the fixed-target benchmark, the recommended run shape is:

- `3` reference frames
- `6` primary frames
- `3` reserved frames

The older moving-target workflow still uses `12` primary and `6` reserved.

### 2. Audit the Dataset Before Running Experiments

Run the dataset auditor first. This is the fastest way to find weak runs before
spending time on the full comparison pipeline.

```powershell
.venv\Scripts\accal audit-dataset `
  --dataset-root dataset `
  --output-dir results/dataset_audit `
  --setup-type benchmark_fixed_target `
  --dataset-split eval
```

This generates:

- `results/dataset_audit/dataset_audit.md`
- `results/dataset_audit/dataset_audit.json`
- `results/dataset_audit/dataset_audit.csv`

The auditor checks:

- frame counts and metadata presence
- ChArUco detection success
- quality metrics such as brightness, blur, saturation, and glare
- calibration success and reprojection error
- whether the run actually looks like the intended scenario
- whether a run should be kept, kept with notes, or recaptured
- which setup type and dataset split the run belongs to

When usable `S0_nominal` runs exist, the auditor also derives an empirical
nominal reference pose and uses it when judging `S3_pose_deviation` and
`S4_height_variation`.

### 3. Run the Full Comparison Analysis

Run all experiment modes across the dataset:

```powershell
.venv\Scripts\accal run-experiments `
  --dataset-root dataset `
  --output-dir results/comparison_run `
  --setup-type benchmark_fixed_target `
  --dataset-split eval
```

This produces:

- `results/comparison_run/results.json`
- `results/comparison_run/summary.json`
- `results/comparison_run/paper_metrics.json`
- `results/comparison_run/scenario_summary.json`
- `results/comparison_run/nominal_reference.json`

What this stage does:

- loads every run under `dataset/`
- splits each run into primary and reserved frames
- derives an effective nominal reference from good `S0_nominal` runs
- executes `baseline`, `heuristic`, `learned`, and `agent` modes on each run
- summarizes calibration success, acceptance success, warning accepts, recovery rate, false reject rate, reprojection error, and retries

Cheap iterative runs are now supported directly from the CLI:

Run only the offline modes, with no LLM API key required:

```powershell
.venv\Scripts\accal run-experiments `
  --dataset-root dataset `
  --output-dir results/comparison_offline `
  --mode baseline `
  --mode heuristic `
  --mode learned
```

Run only one scenario:

```powershell
.venv\Scripts\accal run-experiments `
  --dataset-root dataset `
  --output-dir results/comparison_s3 `
  --scenario S3_pose_deviation_fixed `
  --setup-type benchmark_fixed_target `
  --mode baseline `
  --mode heuristic `
  --mode learned
```

Run one specific run with the agent enabled:

```powershell
.venv\Scripts\accal run-experiments `
  --dataset-root dataset `
  --output-dir results/comparison_run03_agent `
  --scenario S3_pose_deviation_fixed `
  --run-id run_03 `
  --setup-type benchmark_fixed_target `
  --dataset-split eval `
  --mode baseline `
  --mode heuristic `
  --mode learned `
  --mode agent
```

The nominal reference is still derived from the full discovered dataset before
filters are applied, so these targeted reruns stay cheaper without changing the
reference logic.

### 4. Review the Outputs

Use the outputs for different levels of analysis:

- `dataset_audit.md` for human review of run quality and recapture decisions
- `results.json` for per-run debugging and controller traces
- `summary.json` for overall mode-level metrics
- `scenario_summary.json` for scenario-by-scenario tables
- `summary.json` now separates clean accepts from `accept_with_warning`
- `paper_metrics.json` for headline comparison numbers such as recovery rate

## Agent Configuration

Agent mode no longer falls back to the heuristic controller. It runs a real
external agent command and fails fast if that command fails.

The default controller config is in [config/defaults.toml](config/defaults.toml)
and currently points to:

- `uv run python -m agentic_camera_calibration.openai_agent`
- model `gpt-5-mini`
- reasoning effort `minimal`
- max output tokens `180`
- prompt cache key `accal-controller-v1`

Before running agent-backed experiments, set `OPENAI_API_KEY` in your shell:

```powershell
$env:OPENAI_API_KEY = "your-key-here"
```

If you want to work on the classical pipeline only, audit the dataset and run
tests first, then run `baseline`, `heuristic`, and `learned` modes without any
LLM API key. Add `--mode agent` only for the scenarios or run ids you actually
want to spend API budget on.

## Dataset Layout

The runner expects a scenario/run directory layout like this:

```text
dataset/
  S0_nominal/
    run_01/
      frame_001.png
      frame_002.png
      metadata.json
  S1_overexposed/
    run_01/
  S2_low_light/
    run_01/
  S3_pose_deviation/
    run_01/
  S4_height_variation/
    run_01/
  S5_partial_visibility/
    run_01/
```

Frames after the configured `initial_frame_count` are treated as reserved unless
`metadata.json` explicitly marks them.

For the publishable fixed-target benchmark, it is useful to add setup-type and
split structure either in metadata or in the directory layout. For example:

```text
dataset/
  fixed_target_benchmark/
    eval/
      S3_pose_deviation_fixed/
        run_01/
          frame_001.png
          metadata.json
```

If folder names do not encode this, the loader still reads `setup_type` and
`dataset_split` from `metadata.json`.

## Current Pipeline Architecture

The runtime pipeline is:

```text
USB camera or dataset frames
  -> dataset loading / capture metadata
  -> ChArUco detection
  -> image quality analysis
  -> camera calibration
  -> pose deviation analysis
  -> failure detection
  -> controller decision
  -> recovery execution
  -> retry loop or terminal result
  -> experiment summaries and reports
```

The important architectural rule is that `baseline`, `heuristic`, `learned`,
and `agent` share the same detection, quality, calibration, deviation, failure,
and action execution layers. The only thing that changes is the decision layer.

## File Map

This is the quickest way to understand which file is responsible for what in
the current codebase.

### Entry Points And Configuration

- [src/agentic_camera_calibration/cli.py](src/agentic_camera_calibration/cli.py)
  defines the `accal` CLI commands: `capture`, `capture-guided`,
  `capture-reference`, `audit-dataset`, and `run-experiments`.
- [src/agentic_camera_calibration/config.py](src/agentic_camera_calibration/config.py)
  defines all configuration dataclasses and loads `config/defaults.toml`.
- [config/defaults.toml](config/defaults.toml) stores experiment thresholds,
  controller defaults, board geometry, and nominal pose values.

### Shared Data Models

- [src/agentic_camera_calibration/models.py](src/agentic_camera_calibration/models.py)
  defines the dataclasses passed across the pipeline: `FrameRecord`,
  `DetectionResult`, `QualityMetrics`, `CalibrationResult`,
  `DeviationResult`, `ControllerState`, `RecoveryDecision`, and
  `ExperimentRunResult`.

### Capture And Dataset Preparation

- [src/agentic_camera_calibration/capture.py](src/agentic_camera_calibration/capture.py)
  handles USB camera capture, guided capture plans, live OpenCV preview,
  reference-frame capture, and writing `metadata.json`.
- [src/agentic_camera_calibration/dataset_loader.py](src/agentic_camera_calibration/dataset_loader.py)
  discovers scenario/run folders, loads run metadata, constructs `FrameRecord`
  objects, and splits primary versus reserved frames.
- [src/agentic_camera_calibration/dataset_auditor.py](src/agentic_camera_calibration/dataset_auditor.py)
  runs a full dataset quality audit, classifies runs as keep or recapture, and
  writes Markdown, JSON, and CSV reports.
- [src/agentic_camera_calibration/nominal_reference.py](src/agentic_camera_calibration/nominal_reference.py)
  canonicalizes scenario names, derives empirical nominal pose baselines from
  good `S0_nominal` runs, and reapplies that baseline to run metrics.

### Per-Frame And Per-Run Analysis

- [src/agentic_camera_calibration/charuco_detector.py](src/agentic_camera_calibration/charuco_detector.py)
  performs ArUco and ChArUco detection and estimates per-frame pose when
  possible.
- [src/agentic_camera_calibration/quality_analyzer.py](src/agentic_camera_calibration/quality_analyzer.py)
  computes brightness, contrast, blur, saturation, glare, and per-frame
  usability flags.
- [src/agentic_camera_calibration/calibration_engine.py](src/agentic_camera_calibration/calibration_engine.py)
  runs the OpenCV ChArUco calibration from the active frame set.
- [src/agentic_camera_calibration/deviation_analyzer.py](src/agentic_camera_calibration/deviation_analyzer.py)
  converts calibration output into pitch, yaw, roll, `tx`, `ty`, `tz`, and
  aggregate pose error relative to the nominal pose.
- [src/agentic_camera_calibration/failure_detector.py](src/agentic_camera_calibration/failure_detector.py)
  converts calibration, quality, and detection signals into reason codes and a
  pass-versus-intervene decision.

### Controllers And Recovery

- [src/agentic_camera_calibration/controllers/base.py](src/agentic_camera_calibration/controllers/base.py)
  defines the abstract recovery-controller interface.
- [src/agentic_camera_calibration/controllers/heuristic_controller.py](src/agentic_camera_calibration/controllers/heuristic_controller.py)
  implements the rule-based controller over the shared action space.
- [src/agentic_camera_calibration/controllers/learned_controller.py](src/agentic_camera_calibration/controllers/learned_controller.py)
  implements the lightweight feature-scored structured-policy baseline over the
  same action space.
- [src/agentic_camera_calibration/controllers/agent_controller.py](src/agentic_camera_calibration/controllers/agent_controller.py)
  packages `ControllerState`, invokes an external agent command, and validates
  the returned JSON decision.
- [src/agentic_camera_calibration/openai_agent.py](src/agentic_camera_calibration/openai_agent.py)
  is the OpenAI Responses API wrapper used by the default external agent mode.
- [src/agentic_camera_calibration/claude_agent.py](src/agentic_camera_calibration/claude_agent.py)
  is the Anthropic-compatible external agent wrapper.
- [src/agentic_camera_calibration/lm_studio_agent.py](src/agentic_camera_calibration/lm_studio_agent.py)
  is the local LM Studio agent wrapper.
- [src/agentic_camera_calibration/recovery_executor.py](src/agentic_camera_calibration/recovery_executor.py)
  applies recovery actions such as filtering frames, preprocessing images,
  pulling reserved frames, selecting top-k subsets, and relaxing pose margins.
- [src/agentic_camera_calibration/orchestrator.py](src/agentic_camera_calibration/orchestrator.py)
  is the main retry loop that runs detection, quality, calibration, deviation,
  failure evaluation, controller decision, and recovery execution until success
  or termination.

### Experiment Execution And Reporting

- [src/agentic_camera_calibration/experiment_runner.py](src/agentic_camera_calibration/experiment_runner.py)
  coordinates full-dataset experiments across `baseline`, `heuristic`, and
  `agent` modes and writes the derived nominal reference used for the run.
- [src/agentic_camera_calibration/evaluator.py](src/agentic_camera_calibration/evaluator.py)
  computes summary metrics, paper metrics, and scenario-wise aggregates.
- [src/agentic_camera_calibration/reporter.py](src/agentic_camera_calibration/reporter.py)
  writes experiment outputs to JSON files under the chosen results directory.

## Typical Analysis Sequence

If you want one concrete sequence to follow on a fresh machine, use this:

```powershell
$env:UV_CACHE_DIR = "$PWD\\.uv-cache"
uv venv --python 3.12 .venv
uv sync
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\accal audit-dataset --dataset-root dataset --output-dir results/dataset_audit --setup-type benchmark_fixed_target --dataset-split eval
.venv\Scripts\accal run-experiments --dataset-root dataset --output-dir results/comparison_run --setup-type benchmark_fixed_target --dataset-split eval --mode baseline --mode heuristic --mode learned
```

If you are also collecting new data, insert `capture-guided` and optional
`capture-reference` commands before the audit step.
