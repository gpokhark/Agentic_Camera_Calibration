# Paper Experiment Implementation Plan: Publishable Pipeline Roadmap

Goal: evolve the current repo from a useful prototype into a publishable
fixed-target EOL-style benchmark with strong baselines and cost-aware agentic
evaluation.

This plan replaces the earlier implementation-only checklist. The earlier plan
was useful for getting the prototype running, but it no longer reflects the
pipeline changes needed for a credible paper.

---

## 1. Current State

Already in place:

- USB capture and guided capture workflow
- dataset auditing
- classical ChArUco detection and calibration
- empirical nominal reference derivation
- acceptance-versus-calibration split in evaluator outputs
- warning vs hard-fail classification
- baseline, heuristic, and agent modes
- offline comparison without an LLM API key
- targeted experiment filters such as `--scenario`, `--run-id`, and `--mode`

Still missing for a publishable benchmark:

- fixed-target dataset support as a first-class concept
- a learned structured-policy baseline
- explicit dataset splits
- explicit `accept_with_warning` terminal semantics
- richer sequential controller state
- cost-aware agent gating
- fixed-target mixed-failure data

---

## 2. Publishability-Critical Deliverables

- [ ] Add fixed-target metadata and filtering support
- [ ] Add explicit acceptance bands and `accept_with_warning`
- [ ] Add a learned structured controller baseline
- [ ] Strengthen and freeze the heuristic baseline
- [ ] Extend controller state with retry history and budget tracking
- [ ] Add deterministic gating for selective agent invocation
- [ ] Add dataset split support for train / dev / eval
- [ ] Capture fixed-target core scenarios
- [ ] Capture fixed-target mixed scenarios
- [ ] Produce final comparison tables for baseline / heuristic / learned / agent

---

## 3. File Map For Required Changes

| File | Action | Purpose |
|---|---|---|
| `src/agentic_camera_calibration/models.py` | Modify | Add setup metadata, split info, richer terminal status, retry-history fields |
| `src/agentic_camera_calibration/config.py` | Modify | Add acceptance bands, gating settings, dataset split config |
| `config/defaults.toml` | Modify | Store thresholds and gating defaults |
| `src/agentic_camera_calibration/capture.py` | Modify | Support `--setup-type` and richer metadata writes |
| `src/agentic_camera_calibration/cli.py` | Modify | Add CLI flags for setup type and split-aware filtering |
| `src/agentic_camera_calibration/dataset_loader.py` | Modify | Load setup type, split info, and filtering support |
| `src/agentic_camera_calibration/dataset_auditor.py` | Modify | Report by setup type and identify fixed-target benchmark readiness |
| `src/agentic_camera_calibration/failure_detector.py` | Modify | Enforce acceptance-band semantics and non-overridable hard guards |
| `src/agentic_camera_calibration/orchestrator.py` | Modify | Track retry outcomes, warning acceptance, and agent gating |
| `src/agentic_camera_calibration/controllers/heuristic_controller.py` | Modify | Strengthen compound-condition rules and freeze documented baseline |
| `src/agentic_camera_calibration/controllers/learned_controller.py` | Create | Add compact learned-policy baseline |
| `src/agentic_camera_calibration/controllers/agent_controller.py` | Modify | Include retry history, budget, and gated invocation path |
| `src/agentic_camera_calibration/experiment_runner.py` | Modify | Support setup filtering, split filtering, and learned mode |
| `src/agentic_camera_calibration/evaluator.py` | Modify | Add unsafe-accept, per-split, per-setup, and agent-usage metrics |
| `src/agentic_camera_calibration/reporter.py` | Modify | Write richer experiment outputs and summary tables |
| `tests/` | Modify | Add coverage for all new semantics and controllers |
| `docs/` | Modify | Keep specs, plans, and capture guidance aligned |

---

## 4. Phase A: Fixed-Target Benchmark Support

Objective: make the repo explicitly aware of moving-target pilot data versus
fixed-target benchmark data.

### Task A1: Add Fixed-Target Metadata

- [ ] Add metadata fields:
  - `setup_type`
  - `camera_motion`
  - `target_motion`
  - `reference_pose_id`
  - `disturbance_bucket`
  - `dataset_split`
- [ ] Ensure they are written into `metadata.json` during capture
- [ ] Default old datasets safely when these fields are missing

### Task A2: Update Capture Commands

- [ ] Add `--setup-type` to `capture-guided`
- [ ] Add `--setup-type` to `capture-reference`
- [ ] Document expected values:
  - `pilot_moving_target`
  - `benchmark_fixed_target`

### Task A3: Add Setup-Type Filtering

- [ ] Add `--setup-type` filter to `audit-dataset`
- [ ] Add `--setup-type` filter to `run-experiments`
- [ ] Reflect selected setup type in report headers and JSON outputs

Definition of done:

- the repo can evaluate old pilot data and new fixed-target data separately

---

## 5. Phase B: Acceptance And Safety Semantics

Objective: make results look like a realistic station decision instead of a
binary pass/fail artifact.

### Task B1: Add Explicit Acceptance Bands

- [ ] Define config bands for:
  - nominal accept
  - accept with warning
  - hard fail
- [ ] Make these bands visible in config and docs

### Task B2: Add First-Class `accept_with_warning`

- [ ] Add explicit terminal status in models and results
- [ ] Preserve reason codes, warning codes, and hard-fail codes in outputs
- [ ] Ensure evaluator reports warning acceptance separately from clean success

### Task B3: Non-Overridable Hard Safety Guards

- [ ] Define which failures the agent may not override
- [ ] Keep catastrophic calibration failure and extreme reprojection error as
  hard fail regardless of controller output
- [ ] Add tests covering these guards

Definition of done:

- station-style outcomes are modeled explicitly

---

## 6. Phase C: Strong Baselines

Objective: make the non-agent baselines hard to dismiss.

### Task C1: Strengthen Heuristic Controller

- [ ] Add missing compound-condition rules
- [ ] Add scenario-aware rules where justified
- [ ] Add tests for all compound policies
- [ ] Freeze thresholds after development tuning
- [ ] Export the heuristic rule table to documentation

### Task C2: Add Learned Structured Controller

- [ ] Create `learned_controller.py`
- [ ] Define deterministic features extracted from `ControllerState`
- [ ] Add a small model training utility or serialized artifact loader
- [ ] Support `--mode learned`
- [ ] Ensure the learned controller selects from the same bounded action set

### Task C3: Compare All Four Modes

- [ ] Update experiment runner to support:
  - `baseline`
  - `heuristic`
  - `learned`
  - `agent`
- [ ] Keep downstream executor and budgets identical

Definition of done:

- a reviewer can no longer say the comparison is only against a weak heuristic

---

## 7. Phase D: Sequential Agent Design And Cost Control

Objective: ensure the agent is solving a genuinely different problem from a
single-shot classifier, while keeping API cost under control.

### Task D1: Extend Controller State

- [ ] Include previous actions
- [ ] Include previous failure reasons
- [ ] Include attempt outcomes
- [ ] Include remaining retry budget
- [ ] Include remaining agent-call budget if applicable

### Task D2: Add Agent Gating

- [ ] Define deterministic escalation criteria
- [ ] Call the agent only on:
  - ambiguous cases
  - repeated failures
  - multi-factor cases
- [ ] Keep easy cases on heuristic or learned policy only

### Task D3: Log Agent Usage

- [ ] Record whether the agent was invoked for each run
- [ ] Record invocation count
- [ ] Report aggregate agent usage frequency

Definition of done:

- the agent is bounded, selective, and cheaper to evaluate

---

## 8. Phase E: Dataset Split Support

Objective: avoid tuning leakage and make the benchmark statistically cleaner.

### Task E1: Add Split Labels

- [ ] Support:
  - `train`
  - `dev`
  - `eval`
- [ ] Store split labels in metadata or a manifest file

### Task E2: Respect Splits In Tooling

- [ ] Allow audit and experiment tools to filter by split
- [ ] Ensure learned-controller training uses `train` and optionally `dev`
- [ ] Ensure final paper metrics are generated from `eval`

Definition of done:

- the final benchmark is separated from tuning data

---

## 9. Phase F: Fixed-Target Data Collection

Objective: collect the physically aligned benchmark.

### Task F1: Core Fixed-Target Scenarios

- [ ] Capture:
  - `S0_nominal_fixed`
  - `S1_overexposed_fixed`
  - `S2_low_light_fixed`
  - `S3_pose_deviation_fixed`
  - `S4_height_variation_fixed`
  - `S5_partial_visibility_fixed`
- [ ] Start with 5 runs per scenario
- [ ] Expand to 10 runs if quality and time allow

### Task F2: Held-Out Reference Runs

- [ ] Capture 5 nominal held-out runs
- [ ] Capture small held-out subsets for pose and height buckets

### Task F3: Mixed Fixed-Target Scenarios

- [ ] Capture:
  - `M1_fixed`
  - `M2_fixed`
  - `M3_fixed`
- [ ] Start with 3 runs per mixed scenario

Definition of done:

- the benchmark reflects fixed-target EOL logic rather than moving-target
  convenience capture

---

## 10. Phase G: Reporting And Paper Outputs

Objective: produce the tables and evidence a reviewer expects.

### Task G1: Expand Metrics

- [ ] Report:
  - calibration success rate
  - acceptance success rate
  - warning acceptance rate
  - false reject rate
  - recovery rate
  - unsafe accept rate
  - mean retries
  - unrecoverable rate
  - agent invocation frequency

### Task G2: Expand Breakdowns

- [ ] Add per-scenario breakdown
- [ ] Add per-setup-type breakdown
- [ ] Add per-split breakdown
- [ ] Add clean vs warning acceptance breakdown

### Task G3: Produce Final Artifacts

- [ ] `summary.json`
- [ ] `paper_metrics.json`
- [ ] `scenario_summary.json`
- [ ] `split_summary.json`
- [ ] `setup_summary.json`
- [ ] `nominal_reference.json`

Definition of done:

- results can be lifted directly into a paper figure or table

---

## 11. Recommended Execution Order

1. implement fixed-target metadata and filtering
2. implement explicit acceptance bands and warning acceptance
3. strengthen and freeze heuristic baseline
4. add learned structured controller
5. extend controller state and agent gating
6. add dataset split support
7. capture fixed-target core scenarios
8. capture fixed-target mixed scenarios
9. run offline baseline / heuristic / learned sweeps
10. run selective agent evaluation on ambiguous cases

---

## 12. Concrete Definition Of Publishable

This repo is ready for a strong paper submission when all of the following are
true:

- the main benchmark is fixed-target
- the old moving-target dataset is clearly labeled as pilot / development data
- baseline, heuristic, learned, and agent all run on the same bounded action
  space
- acceptance semantics are realistic and explicit
- the heuristic is strong and frozen
- the learned structured baseline is included
- the agent is selective and cost usage is reported
- the final gains appear on ambiguous multi-factor cases

---

## 13. Immediate Next Coding Tasks

If implementation starts now, the best next code changes are:

- [ ] add `setup_type` metadata support end-to-end
- [ ] add explicit `accept_with_warning` terminal status
- [ ] add `learned` mode skeleton and controller interface wiring
- [ ] extend `ControllerState` with retry-history summaries
- [ ] add agent gating settings to config and CLI

Those tasks create the foundation needed before more data collection and final
comparisons.
