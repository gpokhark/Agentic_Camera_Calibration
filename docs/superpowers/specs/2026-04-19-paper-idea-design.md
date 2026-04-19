# Paper Idea Design: Agentic Recovery for Camera Calibration

- **Date:** 2026-04-19
- **Target venue:** IEEE CASE / ICMA or arXiv
- **Status:** Approved — ready for implementation planning

---

## 1. Title

> *Agentic Recovery for Camera Calibration Under Real-World Variability: A Controlled Comparison of Heuristic and LLM-Based Decision Making*

---

## 2. Abstract Frame

Camera calibration in production environments fails not because the geometry is wrong, but because the decision system cannot distinguish recoverable failures from genuine misalignment. We present a calibration recovery framework that interposes a decision layer — heuristic or LLM-based — between a standard ChArUco/OpenCV pipeline and its retry logic. Using a controlled dataset of five disturbance scenarios (overexposure, low light, pose deviation, height variation, and compound combinations), we show that the LLM agent reduces false reject rate on nominal-adjacent runs while recovering a larger fraction of compound failures than a carefully engineered heuristic baseline. Both systems share identical inputs, action space, retry budget, and executor — making the comparison a direct measure of decision quality.

---

## 3. Core Claim

1. A rule-based heuristic over-triggers on recoverable runs and under-performs on interacting failures.
2. An LLM agent operating over the same structured state is more calibrated in both directions — reducing unnecessary aborts while recovering more compound failures.

---

## 4. System Architecture

```
Frames → CharucoDetector → QualityAnalyzer → CalibrationEngine
                                                      ↓
                                            DeviationAnalyzer → FailureDetector
                                                                       ↓ (if fail)
                                                             RecoveryController.decide()
                                                             [Heuristic | LLM Agent]
                                                                       ↓
                                                             RecoveryExecutor.execute()
                                                                       ↓
                                                               re-run calibration
```

### Fairness of Comparison

| Component | Baseline | Heuristic | LLM Agent |
|---|---|---|---|
| Input state (`ControllerState`) | shared | shared | shared |
| Action space | none | shared | shared |
| Retry budget | shared | shared | shared |
| Executor (`RecoveryExecutor`) | shared | shared | shared |
| Decision logic | none | threshold rules | Claude API |

This parity is the methodological backbone of the paper — the comparison isolates decision quality, not infrastructure.

---

## 5. Three Stated Contributions

1. **Formalization** — calibration failure as a structured decision problem with typed state (`ControllerState`), typed output (`RecoveryDecision`), and a fixed action vocabulary, separating decision intelligence from geometric estimation.

2. **Empirical comparison** — a controlled experiment across five real disturbance scenarios with three systems sharing all infrastructure except the decision layer, measuring both recovery rate and false reject rate.

3. **Two-sided result** — the LLM agent is more calibrated than a non-trivial heuristic baseline in both directions: it fires less on recoverable/nominal-adjacent runs and recovers more compound failures.

---

## 6. Experimental Design

### Dataset

| Scenario | Runs | Status |
|---|---|---|
| S0 — Nominal | 9 usable | collected |
| S1 — Overexposed | 10 | collected |
| S2 — Low light | 10 | collected |
| S3 — Pose deviation | 10 | collected |
| S4 — Height variation | 10 | collected |
| Mixed-1: S1+S3 (overexposure + pose deviation) | 3 | to collect |
| Mixed-2: S2+S4 (low light + height variation) | 3 | to collect |
| Mixed-3: S1+S4 (overexposure + height variation) | 3 | to collect |

**Total:** 58 runs, ~870–1160 frames.

### Comparison Modes

- **Baseline** — no controller, hard pass/fail on initial frame set
- **Heuristic** — full 12-rule threshold controller (`heuristic_controller.py`)
- **LLM Agent** — Claude API via `agent_command`, same structured JSON state, same action space

### Experimental Matrix

- **S0 runs** → all three modes (measures false reject rate on nominal-adjacent data — S0 already triggers `pose_out_of_range` and `low_marker_coverage` at reprojection ~0.15 px, so false alarms come from real data, not synthetic injection)
- **S1–S4 runs** → all three modes (single-cause failure recovery)
- **Mixed runs** → all three modes (compound failure recovery — primary differentiator)

---

## 7. Metrics

### Primary (Table 1)

**Recovery Rate:**
```
(runs failed by baseline, succeeded by controller) / (runs failed by baseline)
```

**False Reject Rate:**
```
(runs aborted by controller) / (runs that succeed under baseline or with minimal intervention)
```

### Secondary (Table 2, per-scenario breakdown)

- Final reprojection error on successful runs (accuracy not degraded)
- Mean retries to success (efficiency)
- Unrecoverable declaration rate by scenario
- Agent confidence scores across scenario types (LLM agent only)

---

## 8. Expected Results

| Scenario type | Baseline | Heuristic | LLM Agent |
|---|---|---|---|
| S0 nominal | passes | may false-reject (over-triggers on coverage/pose codes) | passes or intervenes minimally |
| S1–S4 single-cause | fails often | recovers most | similar to heuristic |
| Mixed failures | fails | partially recovers | clearly better |

The paper's key result: **the agent's advantage is sharpest at the intersection of compound failures and false alarm suppression** — exactly where fixed rules break down.

**Risk mitigation:** If the LLM agent doesn't clearly outperform heuristics on mixed runs, reframe as a compound-failure focus paper (Approach C). The experimental design supports this pivot without recollecting data.

---

## 9. Paper Structure

| Section | Content |
|---|---|
| I. Introduction | EOL calibration false reject problem, cost motivation, agent decision layer idea |
| II. Related Work | (handled separately) |
| III. System | Pipeline architecture, ControllerState schema, action space, heuristic rule table, LLM prompt + schema |
| IV. Experimental Setup | Dataset (S0–S4 + 3 mixed), hardware, board config, three comparison modes |
| V. Results | Table 1: recovery rate + false reject rate. Table 2: per-scenario breakdown. Figure: agent vs heuristic on mixed runs |
| VI. Discussion | Where agent wins and why, failure analysis, limitations |
| VII. Conclusion | Summary, EOL generalization, future work (S5, multi-camera) |

---

## 10. Action Plan

| Step | Task | Depends on |
|---|---|---|
| 1 | Wire Claude API into `agent_command` in `config/defaults.toml` | — |
| 2 | Strengthen heuristic with combined-condition rules (reviewer-proof baseline) | — |
| 3 | Collect 9 mixed-failure runs (3 × Mixed-1/2/3) | — |
| 4 | Run full experiment: `accal run-experiments` across all 58 runs | 1, 3 |
| 5 | Compute primary + secondary metrics from `results/results.json` | 4 |
| 6 | Write paper using this design as skeleton | 5 |

Steps 1, 2, and 3 can proceed in parallel. Step 4 requires 1 and 3. Steps 5 and 6 are sequential after 4.
