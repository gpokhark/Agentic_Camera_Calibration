# Two-Week Paper Execution Checklist

This is the short execution companion to
[paper_north_star.md](/D:/github/Agentic_Camera_Calibration/docs/paper_north_star.md).

Use this checklist when deciding what to do next over the next two weeks.

The goal is not to "improve the repo" in a general sense.
The goal is to make the project more publishable.

## Week 1

### 1. Lock The Benchmark Scope

Done when:

- the main paper benchmark is treated as `benchmark_fixed_target`
- the fixed-target capture protocol is treated as the main benchmark
- the older moving-target data is treated as `dev` or supplementary evidence

Practical check:

- do not spend time expanding legacy moving-target capture unless it helps
  debugging or ablations

### 2. Capture The Small Fixed-Target Starter Set

Capture these first:

- `S0_nominal_fixed`
- `S3_pose_deviation_fixed`
- `S4_height_variation_fixed`
- `S5_partial_visibility_fixed`

Minimum target:

- `3` runs each to start
- `3` reference + `6` primary + `3` reserved per run

Done when:

- each of the four scenarios has at least `3` clean fixed-target runs
- metadata includes `setup_type = benchmark_fixed_target`
- metadata includes `dataset_split = eval` unless intentionally collecting a
  small dev set

### 3. Audit Immediately After Capture

Run:

```powershell
.venv\Scripts\accal audit-dataset --dataset-root dataset --output-dir results/dataset_audit_fixed --setup-type benchmark_fixed_target --dataset-split eval
```

Done when:

- the auditor does not incorrectly flag good fixed-target `6 + 3` runs for
  frame count
- scenario fit looks believable
- obviously weak runs are identified before more capture time is spent

### 4. Run Offline Comparison First

Run:

```powershell
.venv\Scripts\accal run-experiments --dataset-root dataset --output-dir results/comparison_fixed_offline --setup-type benchmark_fixed_target --dataset-split eval --mode baseline --mode heuristic --mode learned
```

Done when:

- offline comparison completes on the small fixed-target subset
- results are no longer dominated by obviously misleading benchmark behavior
- scenario-wise outputs are interpretable enough to discuss

## Week 2

### 5. Review Whether The Benchmark Is Discriminative

Inspect:

- `summary.json`
- `scenario_summary.json`
- `paper_metrics.json`
- `results.json`

Questions to answer:

- do `baseline`, `heuristic`, and `learned` separate meaningfully?
- are `S3`, `S4`, and `S5` producing informative differences?
- are acceptance metrics more realistic than before?
- are we seeing recoveries, false rejects, warnings, and unrecoverables in a
  believable way?

Done when:

- we can explain what the offline benchmark is showing
- we can identify which scenario is hardest and most useful for selective agent
  evaluation

### 6. Run Selective Agent Evaluation

Do not run the agent broadly yet.

Start with:

- the hardest `S3_pose_deviation_fixed` runs
- the hardest `S4_height_variation_fixed` runs
- the hardest `S5_partial_visibility_fixed` runs

Suggested pattern:

```powershell
.venv\Scripts\accal run-experiments --dataset-root dataset --output-dir results/comparison_agent_targeted --scenario S3_pose_deviation_fixed --run-id run_03 --setup-type benchmark_fixed_target --dataset-split eval --mode baseline --mode heuristic --mode learned --mode agent
```

Done when:

- agent results exist on a curated hard subset
- cost stays controlled
- we can describe where the agent helps and where it does not

### 7. Decide Whether Mixed Scenarios Are Needed Immediately

If the single-disturbance benchmark is too easy or too separable, plan the next
capture step around mixed conditions:

- `M1_fixed_overexposed_pose`
- `M2_fixed_lowlight_partial`
- `M3_fixed_glare_height`

Done when:

- we have a clear yes/no answer on whether mixed scenarios are required next
- that answer is based on outputs, not intuition alone

## Deliverables By The End Of Two Weeks

The ideal outcome is:

- a small audited fixed-target benchmark subset exists
- offline comparison exists for `baseline`, `heuristic`, and `learned`
- targeted `agent` comparison exists on the hardest cases
- we can clearly explain the paper claim using actual outputs from the repo

## What Not To Spend Time On

Avoid spending significant time on:

- GUI polish unrelated to benchmark quality
- large refactors with no experimental payoff
- expanding legacy moving-target capture as the main dataset
- broad full-dataset agent runs before the offline benchmark is understood
- adding features that blur the fixed-target paper story

## Daily Decision Rule

Before starting any task, ask:

1. Does this strengthen the fixed-target benchmark?
2. Does this strengthen the comparison across controllers?
3. Does this improve the credibility of the future paper?

If the answer is mostly no, it is probably not the right task for now.
