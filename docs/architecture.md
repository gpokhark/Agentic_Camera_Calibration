# Current Pipeline Architecture

This document describes the current implemented architecture of the repository.
It is meant to stay aligned with the README and the Python code in
`src/agentic_camera_calibration/`.

The project compares three execution modes over the same calibration pipeline:

- `baseline`: no recovery controller
- `heuristic`: deterministic rule-based controller
- `agent`: external LLM-backed controller using the same action space

## 1. Design Goal

The core design rule is fairness of comparison.

The following layers are shared across all modes:

- dataset loading and frame records
- ChArUco detection
- image-quality analysis
- calibration engine
- deviation analysis
- failure detection
- recovery action executor
- retry budget and thresholds

The only layer that changes between `heuristic` and `agent` is the decision
policy that selects recovery actions.

## 2. End-To-End Workflow

The current workflow in the repo is:

1. Capture or load a dataset run.
2. Audit the dataset to identify weak runs and scenario-fit issues.
3. Derive an effective nominal reference from good `S0_nominal` runs when available.
4. Run the comparison pipeline in `baseline`, `heuristic`, and `agent` modes.
5. Export per-run and aggregate outputs for review.

## 3. Runtime Pipeline

The runtime path for a single run is:

```text
Frames from USB camera or dataset
  -> Frame records + metadata
  -> ChArUco detection
  -> Image quality analysis
  -> Camera calibration
  -> Pose deviation analysis
  -> Failure detection
  -> Recovery decision
  -> Recovery action execution
  -> Retry loop or terminal result
  -> Experiment summaries and reports
```

The same flow shown as a block diagram:

```text
          +-----------------------------+
          | USB camera or dataset files |
          +-------------+---------------+
                        |
                        v
          +-----------------------------+
          | Capture / Dataset loading   |
          | metadata + frame records    |
          +-------------+---------------+
                        |
                        v
          +-----------------------------+
          | ChArUco detection           |
          +-------------+---------------+
                        |
                        v
          +-----------------------------+
          | Image quality analysis      |
          +-------------+---------------+
                        |
                        v
          +-----------------------------+
          | Calibration engine          |
          +-------------+---------------+
                        |
                        v
          +-----------------------------+
          | Deviation analysis          |
          +-------------+---------------+
                        |
                        v
          +-----------------------------+
          | Failure detector            |
          +------+------+---------------+
                 | pass | intervene
                 |      v
                 |  +-------------------+
                 |  | Controller        |
                 |  | heuristic/agent   |
                 |  +---------+---------+
                 |            |
                 |            v
                 |  +-------------------+
                 |  | Recovery executor |
                 |  +---------+---------+
                 |            |
                 +------------+
                              v
                    retry or terminal result
```

## 4. Dataset And Run Model

The expected dataset layout is:

```text
dataset/
  S0_nominal/
    run_01/
      frame_001.png
      frame_002.png
      ...
      metadata.json
  S1_overexposed/
  S2_low_light/
  S3_pose_deviation/
  S4_height_variation/
  S5_partial_visibility/
```

Each run is represented in memory as:

- `RunRecord`: one scenario/run directory and its frame list
- `FrameRecord`: one image, its path, scenario, run id, reserved flag, and metadata

Primary versus reserved frames:

- the first `initial_frame_count` frames are the initial active set
- later frames are recovery reserve frames unless `metadata.json` marks them explicitly
- reserve frames are used by the recovery executor when a controller requests additional views

Reference frames:

- optional `reference_frames/` folders can be captured for human comparison
- they are intentionally separate from the main run loader path
- they do not change the experiment runner unless you explicitly incorporate them into analysis

## 5. Main Commands

The CLI entry point is `accal`, implemented in
`src/agentic_camera_calibration/cli.py`.

Current commands:

- `capture`
- `capture-guided`
- `capture-reference`
- `audit-dataset`
- `run-experiments`

Typical usage order:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset/S0_nominal/run_01 --scenario S0_nominal --run-id run_01 --primary-count 12 --reserved-count 6
.venv\Scripts\accal audit-dataset --dataset-root dataset --output-dir results/dataset_audit
.venv\Scripts\accal run-experiments --dataset-root dataset --output-dir results/comparison_run
```

## 6. Module Responsibilities

This section maps the current codebase to the implemented pipeline.

### 6.1 Entry Points And Configuration

- `src/agentic_camera_calibration/cli.py`
  Parses CLI arguments and dispatches to capture, audit, and experiment flows.
- `src/agentic_camera_calibration/config.py`
  Defines configuration dataclasses for board geometry, quality thresholds,
  failure thresholds, controller settings, experiment settings, and nominal pose.
- `config/defaults.toml`
  Stores the default runtime configuration used by the CLI.

### 6.2 Shared Data Models

- `src/agentic_camera_calibration/models.py`
  Defines the pipeline dataclasses:
  `FrameRecord`, `RunRecord`, `DetectionResult`, `QualityMetrics`,
  `CalibrationResult`, `DeviationResult`, `FailureEvaluation`,
  `ControllerState`, `RecoveryDecision`, and `ExperimentRunResult`.

### 6.3 Capture And Dataset Preparation

- `src/agentic_camera_calibration/capture.py`
  Handles camera capture, guided capture plans, live preview overlays,
  reference-frame capture, and `metadata.json` generation.
- `src/agentic_camera_calibration/dataset_loader.py`
  Discovers runs, loads image files and metadata, and splits initial and reserved
  frame sets.
- `src/agentic_camera_calibration/dataset_auditor.py`
  Audits every run in the dataset and generates keep/recapture reports in
  Markdown, JSON, and CSV form.
- `src/agentic_camera_calibration/nominal_reference.py`
  Canonicalizes scenario names, derives empirical nominal references from good
  `S0_nominal` runs, and reapplies those references to metric dictionaries.

### 6.4 Per-Frame And Per-Run Analysis

- `src/agentic_camera_calibration/charuco_detector.py`
  Detects ArUco markers and ChArUco corners and estimates frame pose when
  possible.
- `src/agentic_camera_calibration/quality_analyzer.py`
  Computes frame quality metrics such as brightness, contrast, blur, saturation,
  glare, and frame usability.
- `src/agentic_camera_calibration/calibration_engine.py`
  Performs ChArUco calibration on the active frame set.
- `src/agentic_camera_calibration/deviation_analyzer.py`
  Computes pose deviation relative to the configured or empirically derived
  nominal pose.
- `src/agentic_camera_calibration/failure_detector.py`
  Converts calibration, quality, and detection signals into a pass/intervene
  decision plus reason codes.

### 6.5 Controllers And Action Execution

- `src/agentic_camera_calibration/controllers/base.py`
  Defines the common recovery-controller interface.
- `src/agentic_camera_calibration/controllers/heuristic_controller.py`
  Implements rule-based recovery decisions using the shared controller state.
- `src/agentic_camera_calibration/controllers/agent_controller.py`
  Serializes controller state, invokes an external agent process, and validates
  the returned JSON response.
- `src/agentic_camera_calibration/openai_agent.py`
  Implements the OpenAI-backed external agent wrapper.
- `src/agentic_camera_calibration/claude_agent.py`
  Implements the Anthropic-backed external agent wrapper.
- `src/agentic_camera_calibration/lm_studio_agent.py`
  Implements the local LM Studio-backed external agent wrapper.
- `src/agentic_camera_calibration/recovery_executor.py`
  Applies controller-selected actions:
  frame filtering, preprocessing, reserved-frame promotion, top-k subset
  selection, and nominal-prior relaxation.

### 6.6 Orchestration And Reporting

- `src/agentic_camera_calibration/orchestrator.py`
  Runs the retry loop for one run in one mode:
  detect -> analyze -> calibrate -> evaluate -> decide -> execute -> retry.
- `src/agentic_camera_calibration/experiment_runner.py`
  Runs all dataset runs across `baseline`, `heuristic`, and `agent` modes and
  writes the effective nominal reference used for the comparison.
- `src/agentic_camera_calibration/evaluator.py`
  Computes overall summaries, scenario summaries, recovery rate, and false reject rate.
- `src/agentic_camera_calibration/reporter.py`
  Writes experiment outputs to disk.

## 7. Decision Layer Details

The repo currently uses one shared action space for both recovery controllers.

Allowed actions are configured in `config/defaults.toml` and currently include:

- `reject_bad_frames`
- `apply_preprocessing`
- `request_additional_views`
- `retry_with_filtered_subset`
- `relax_nominal_prior`
- `declare_unrecoverable`

This is important because it keeps the heuristic-versus-agent comparison
defensible: both controllers can only choose from the same set of downstream
operations.

## 8. Retry Loop Semantics

For each run and mode:

1. Start with the primary frame set.
2. Detect markers and corners.
3. Compute image quality metrics.
4. Attempt calibration.
5. If calibration succeeds, compute deviation.
6. Evaluate whether the result should pass or trigger intervention.
7. If intervention is needed and a controller exists, build `ControllerState`.
8. Ask the controller for a `RecoveryDecision`.
9. Execute the selected recovery actions.
10. Retry until success, unrecoverable termination, or retry budget exhaustion.

`baseline` stops immediately on failure because it has no controller.

## 9. Outputs

### 9.1 Dataset Audit Outputs

`audit-dataset` writes:

- `dataset_audit.md`
- `dataset_audit.json`
- `dataset_audit.csv`

These outputs are intended for:

- human review of run quality
- identifying runs to recapture
- checking whether each scenario actually produced the intended disturbance

### 9.2 Experiment Outputs

`run-experiments` writes:

- `results.json`
- `summary.json`
- `paper_metrics.json`
- `scenario_summary.json`
- `nominal_reference.json`

These outputs are intended for:

- per-run debugging
- aggregate comparison across modes
- scenario-level reporting for paper tables and figures

## 10. Current Limitations

The current implementation is intentionally scoped for a single-camera desk
setup, not a full production automotive deployment.

Current boundaries:

- single USB camera
- offline replay from saved frames
- ChArUco-based calibration only
- fixed recovery action space
- optional external LLM controller process

That scope is deliberate: it keeps the geometric pipeline classical and makes
the research contribution about recovery decision-making rather than replacing
calibration math.
