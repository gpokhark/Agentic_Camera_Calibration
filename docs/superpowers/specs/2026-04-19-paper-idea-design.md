# Paper Idea Design: Publishable EOL-Proxy Direction

- Date: 2026-04-19
- Target venue: IEEE CASE / IROS workshop / arXiv
- Status: revised after pipeline review and EOL-alignment discussion

---

## 1. Working Title

Agentic Recovery for Target-Based Camera Pose Estimation and Calibration
Acceptance Under End-of-Line-Like Disturbances

---

## 2. Problem Frame

In automotive end-of-line calibration, a vehicle arrives at a station that has
a fixed floor calibration target. The system already has nominal camera
geometry from CAD and flashed configuration. The station then observes the
fixed target, estimates how the real installed camera differs from nominal, and
uses that deviation estimate to support downstream view correction and
stitching.

The practical failure problem is not only geometric estimation. It is also a
decision problem:

- is the evidence trustworthy enough to accept?
- should the system retry, filter, or request another view?
- is the issue true misalignment or degraded observation quality?

This repo should therefore be positioned as a desk-scale, single-camera proxy
for the per-camera EOL recovery problem, not as a full surround-view deployment
replica.

---

## 3. What The Paper Should Claim

### 3.1 Core Claim

Classical geometry remains responsible for target detection, calibration, and
deviation estimation. The contribution is a bounded recovery controller that
decides how to respond when the observed evidence is degraded or ambiguous.

### 3.2 Publishable Claim

We study calibration acceptance and recovery as a bounded sequential decision
problem around classical estimation. We compare:

- baseline acceptance logic
- a strong deterministic heuristic controller
- a compact structured learned controller
- a selective LLM-based agent controller

All controllers share the same diagnostics, action vocabulary, retry budget,
and safety guards. The agent is only justified if it improves decisions on
ambiguous multi-factor failures without increasing unsafe accepts.

### 3.3 What The Paper Should Not Claim

The paper should not claim:

- that the LLM performs calibration
- that the desk setup reproduces full 4-camera surround-view stitching
- that moving the target is equivalent to the real EOL physical mechanism
- that an LLM is required for simple thresholding over a few metrics

---

## 4. Automotive EOL To Desk-Proxy Mapping

| Automotive EOL concept | Desk proxy in this repo |
|---|---|
| flashed nominal camera geometry | configured or empirically derived nominal pose |
| fixed floor calibration target | fixed ChArUco board |
| vehicle arrives with mount error | disturbed camera pose relative to the fixed board |
| ride-height or suspension variation | camera height variation relative to the fixed board |
| plant lighting / reflections | overexposure, low light, glare |
| target contamination / occlusion | partial visibility |
| per-camera correction for stitching | accepted deviation estimate from the proxy pipeline |

This mapping is credible only if the main benchmark uses a fixed target and
varies the camera or environment around it.

---

## 5. Revised System Architecture

```text
Fixed-target dataset or live capture
  -> metadata-aware dataset loading
  -> ChArUco detection
  -> image-quality analysis
  -> calibration / pose estimation
  -> deviation analysis versus nominal reference
  -> failure detector with warning vs hard-fail codes
  -> controller state assembly with retry history
  -> controller decision
       - heuristic
       - learned structured policy
       - LLM agent
  -> recovery executor
  -> retry loop
  -> acceptance / warning / hard-fail reporting
```

### Shared Components

All modes must share:

- dataset loader and metadata
- detection and quality analysis
- calibration and deviation estimation
- failure detector
- action executor
- retry budget
- hard safety guards

### Variable Component

Only the decision policy should vary across controllers.

---

## 6. Why This Is Not "Just Robust Estimation"

Robust estimation remains important, but it solves a different problem.

Robust estimation helps:

- fit geometry under outliers
- reduce sensitivity to bad observations
- stabilize calibration from noisy evidence

The recovery controller decides:

- whether the current result is acceptable
- whether evidence is too degraded to trust
- which bounded intervention to try next
- whether to stop or continue under a retry budget

This distinction only becomes convincing if the controller is evaluated as a
sequential bounded policy with retry history and cost-aware escalation.

---

## 7. Comparison Systems Required For A Strong Paper

### 7.1 Baseline

- one-pass classical pipeline
- no recovery controller
- shared safety thresholds

### 7.2 Heuristic

- deterministic threshold and compound-condition policy
- scenario-aware where justified
- same bounded action space as all other controllers

### 7.3 Learned Structured Policy

- compact decision tree, random forest, or gradient-boosted model
- same structured state used by the heuristic and agent
- trained only on development data
- same bounded action space

### 7.4 Agent

- compact structured state
- retry history
- bounded actions
- same safety guards
- selective escalation only on ambiguous or repeated-failure cases

The learned structured policy is necessary to answer the review question:
"Why not just use a small classifier?"

---

## 8. Publishability-Critical Pipeline Changes

These are the implementation changes that move the repo from a useful prototype
to a publishable benchmark.

### 8.1 Fixed-Target Benchmark Support

The pipeline must support datasets where the board stays fixed and the camera or
environment changes.

Required additions:

- metadata fields: `setup_type`, `camera_motion`, `target_motion`,
  `reference_pose_id`, `disturbance_bucket`
- CLI capture support for `--setup-type`
- dataset filtering by setup type in audit and experiment runs

### 8.2 Acceptance Bands

The pipeline must explicitly separate:

- calibration success
- acceptance success
- accept with warning
- hard fail

Required additions:

- config-defined nominal / warning / hard-fail bands
- explicit terminal status for `accept_with_warning`
- reporting for unsafe-accept risk

### 8.3 Sequential Controller State

The controller state must show more than the current metric snapshot.

Required additions:

- previous actions
- previous failure reasons
- attempt outcomes
- remaining retry budget
- escalation budget or agent-call budget

### 8.4 Learned Policy Baseline

Add a new controller mode:

- `learned`

Required implementation:

- `learned_controller.py`
- train / load lightweight model artifact
- deterministic feature extraction from `ControllerState`
- integration into CLI and experiment runner

### 8.5 Stronger Heuristic Baseline

The heuristic must be reviewer-proof.

Required improvements:

- compound-condition rules
- scenario-aware rules where justified
- documented threshold freeze procedure
- exported rule table in documentation

### 8.6 Dataset Split Support

To avoid tuning leakage, the pipeline should distinguish:

- train
- development
- evaluation

Required additions:

- split tags in metadata or split manifest support
- filtering in training and experiment utilities
- evaluator reporting that makes the split explicit

### 8.7 Cost-Aware Agent Gating

The paper should not position the agent as the default controller for all runs.

Required behavior:

- deterministic screening first
- escalate to the agent only on ambiguous states or repeated failure
- log when the agent was invoked and how often

### 8.8 Stronger Reporting

Required outputs:

- recovery rate
- false reject rate
- unsafe accept rate
- acceptance success rate
- calibration success rate
- retries per accepted run
- agent invocation frequency
- per-scenario breakdown
- per-split breakdown

---

## 9. Revised Dataset Requirement

### 9.1 Keep Existing Data

The current moving-target dataset remains useful as:

- development data
- threshold-tuning data
- prompt and payload debugging data
- supplementary robustness evidence

### 9.2 New Fixed-Target Core Scenarios

Minimum fixed-target benchmark:

- `S0_nominal_fixed`
- `S1_overexposed_fixed`
- `S2_low_light_fixed`
- `S3_pose_deviation_fixed`
- `S4_height_variation_fixed`
- `S5_partial_visibility_fixed`

Recommended minimum:

- 5 runs each initially
- 10 runs each if time allows

### 9.3 Mixed Fixed-Target Scenarios

Recommended:

- `M1_fixed`: overexposed + pose deviation
- `M2_fixed`: low light + partial visibility
- `M3_fixed`: glare + height variation

Recommended minimum:

- 3-5 runs each

### 9.4 Held-Out Reference Runs

Capture a small held-out fixed-target reference set not used for tuning:

- 5 nominal held-out runs
- small held-out subsets for pose and height buckets

---

## 10. Revised Experimental Design

### Development Stage

- use current moving-target dataset plus early fixed-target runs
- tune heuristic thresholds
- train the learned policy
- validate safety guards

### Final Evaluation Stage

- evaluate only on held-out fixed-target runs
- compare baseline, heuristic, learned, and agent
- run the agent only after deterministic escalation criteria are met

### Key Result To Seek

The most publishable outcome is:

- heuristic and learned controller perform well on simple single-factor cases
- agent is comparable on easy cases
- agent improves recovery or reduces false rejects on ambiguous multi-factor
  failures without increasing unsafe accepts

---

## 11. Success Criteria

This project is publishable if the final benchmark shows all of the following:

1. the benchmark is physically aligned with fixed-target EOL logic
2. the baseline and heuristic are strong and well documented
3. the learned structured baseline is included
4. the agent is evaluated selectively and cost is reported
5. gains appear on ambiguous multi-factor cases rather than trivial cases
6. acceptance semantics are realistic and not collapsed into hard pass/fail

---

## 12. Bottom Line

The research idea remains strong, but the publishable version is more precise
than the current prototype:

- fixed target, not moving target, for the main benchmark
- target-based pose estimation and acceptance, not full surround-view deployment
- strong heuristic and learned baselines
- selective, bounded, sequential agentic recovery

That is the clearest path to a credible automotive EOL-inspired paper.
