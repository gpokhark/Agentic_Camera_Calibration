# Paper Idea Design: Agentic Recovery for Camera Calibration

- **Date:** 2026-04-19 (revised after full codebase re-analysis)
- **Target venue:** IEEE CASE / ICMA or arXiv
- **Status:** Approved — ready for implementation planning

---

## 1. Title

> *Agentic Recovery for Camera Calibration Under Real-World Variability: A Controlled Comparison of Heuristic and LLM-Based Decision Making*

---

## 2. Abstract Frame

Camera calibration in production environments fails not because the geometry is wrong, but because the decision system cannot distinguish recoverable failures from genuine misalignment. We present a calibration recovery framework that interposes a decision layer — heuristic or LLM-based — between a standard ChArUco/OpenCV pipeline and its retry logic. The framework first derives an empirical nominal reference pose from collected S0 data, grounding all deviation comparisons in the actual camera geometry rather than hardcoded assumptions. Using a controlled dataset of five disturbance scenarios (overexposure, low light, pose deviation, height variation, and compound combinations), we show that the LLM agent reduces false reject rate on nominal-adjacent runs while recovering a larger fraction of compound failures than a carefully engineered heuristic baseline. Both systems share identical inputs, action space, retry budget, and executor — making the comparison a direct measure of decision quality.

---

## 3. Core Claim

1. A rule-based heuristic over-triggers on recoverable runs and under-performs on interacting failures.
2. An LLM agent operating over the same compact structured state is more calibrated in both directions — reducing unnecessary aborts while recovering more compound failures.

---

## 4. System Architecture

```
S0 Frames → EmpiricalNominalEstimator ─────────────────────────────┐
                                                                    ↓ (NominalPoseConfig)
Frames → CharucoDetector → QualityAnalyzer → CalibrationEngine
                                                      ↓
                                            DeviationAnalyzer (vs empirical nominal)
                                                      ↓
                                            FailureDetector
                                                      ↓ (if fail)
                                            AgentController._compact_state()
                                                      ↓ (JSON payload via subprocess)
                                            openai_agent.py → gpt-5-mini (Responses API)
                                            OR HeuristicController (threshold + compound rules)
                                                      ↓
                                            RecoveryExecutor.execute()
                                                      ↓
                                              re-run calibration
```

**Empirical nominal reference:** Before running any experiment, `EmpiricalNominalEstimator` analyzes S0 runs, selects those with good calibration quality (reprojection < 1.0 px, usable rate ≥ 0.75, no lighting failures), and computes mean pose estimates as the dataset-specific nominal. This replaces the hardcoded `[nominal_pose]` in `config/defaults.toml` and prevents false `pose_out_of_range` alarms from config-default mismatch.

**LLM agent:** `AgentController` calls `openai_agent.py` via subprocess, passing a compact JSON state (last 2 attempted actions, rounded metrics) and `agent_settings` (model, reasoning effort, token cap, cache key). `openai_agent.py` calls the OpenAI Responses API using stdlib `urllib` — no external SDK dependency. Default model: `gpt-5-mini`, reasoning effort: `minimal`, max output tokens: `180`. The heuristic fallback has been removed; if `agent_command` is empty, `AgentController` raises `RuntimeError`.

### Fairness of Comparison

| Component | Baseline | Heuristic | LLM Agent |
|---|---|---|---|
| Input state (`ControllerState`) | shared | shared | shared (compact form) |
| Action space | none | shared | shared |
| Retry budget | shared | shared | shared |
| Executor (`RecoveryExecutor`) | shared | shared | shared |
| Nominal pose (derived from S0) | shared | shared | shared |
| Decision logic | none | threshold + compound rules | gpt-5-mini via Responses API |

---

## 5. Four Stated Contributions

1. **Formalization** — calibration failure as a structured decision problem with typed state (`ControllerState`), typed output (`RecoveryDecision`), and a fixed action vocabulary, separating decision intelligence from geometric estimation.

2. **Empirical nominal reference** — a data-driven nominal pose derived from S0 runs that grounds deviation comparisons in the actual camera geometry, eliminating false `pose_out_of_range` alarms from config-default mismatch.

3. **Empirical comparison** — a controlled experiment across five real disturbance scenarios with three systems sharing all infrastructure except the decision layer, measuring both recovery rate and false reject rate.

4. **Two-sided result** — the LLM agent is more calibrated than a non-trivial heuristic baseline in both directions: it fires less on recoverable/nominal-adjacent runs and recovers more compound failures.

---

## 6. Experimental Design

### Dataset Status (as of 2026-04-19)

| Scenario | Runs | Status |
|---|---|---|
| S0 — Nominal | 9 usable | collected ✓ |
| S1 — Overexposed | 10 | collected ✓ |
| S2 — Low light | 10 | collected ✓ |
| S3 — Pose deviation | 10 | collected ✓ |
| S4 — Height variation | 10 | collected ✓ |
| Mixed-1: S1+S3 (overexposure + pose deviation) | 3 | **to collect** |
| Mixed-2: S2+S4 (low light + height variation) | 3 | **to collect** |
| Mixed-3: S1+S4 (overexposure + height variation) | 3 | **to collect** |

All single-scenario data (S0–S4) is collected. Only mixed-failure runs remain.

**Total target:** 58 runs, ~870–1160 frames.

### Comparison Modes

- **Baseline** — no controller, hard pass/fail on initial frame set
- **Heuristic** — threshold + compound-condition rule controller (`heuristic_controller.py`)
- **LLM Agent** — `gpt-5-mini` via `openai_agent.py`, compact state, same action space

### Experimental Matrix

- **S0 runs** → all three modes (measures false reject rate on nominal data)
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
(runs failed by controller) / (runs succeeded by baseline)
```

### Secondary (Table 2, per-scenario breakdown)

- Final reprojection error on successful runs (accuracy not degraded)
- Mean retries to success (efficiency)
- Unrecoverable declaration rate by scenario
- Nominal reference source and run count (audit transparency)

---

## 8. Expected Results

| Scenario type | Baseline | Heuristic | LLM Agent |
|---|---|---|---|
| S0 nominal | passes | may false-reject on `low_marker_coverage` or quality thresholds | passes or intervenes minimally |
| S1–S4 single-cause | fails often | recovers most | similar to heuristic |
| Mixed failures | fails | partially recovers | clearly better |

The paper's key result: **the agent's advantage is sharpest at the intersection of compound failures and false alarm suppression** — exactly where fixed rules break down.

**Risk mitigation:** If the LLM agent doesn't clearly outperform heuristics on mixed runs, reframe as a compound-failure focus paper. The experimental design supports this pivot without recollecting data.

---

## 9. Paper Structure

| Section | Content |
|---|---|
| I. Introduction | EOL calibration false reject problem, cost motivation, agent decision layer idea |
| II. Related Work | (handled separately) |
| III. System | Pipeline architecture (incl. empirical nominal), compact state design, action space, heuristic rule table, LLM agent design and cost controls |
| IV. Experimental Setup | Dataset (S0–S4 + 3 mixed), hardware, board config (7×5 ChArUco, 25 mm squares, DICT_4X4_50), three comparison modes |
| V. Results | Table 1: recovery rate + false reject rate. Table 2: per-scenario breakdown. Figure: agent vs heuristic on mixed runs |
| VI. Discussion | Where agent wins and why, failure analysis, nominal reference impact, limitations |
| VII. Conclusion | Summary, EOL generalization, future work (S5, multi-camera) |

---

## 10. Implementation Status and Remaining Work

### Already implemented

| Component | Status |
|---|---|
| `openai_agent.py` — OpenAI Responses API subprocess entry point | done ✓ |
| `config/defaults.toml` — `agent_command` + agent settings | done ✓ |
| `ControllerConfig` — new agent settings fields | done ✓ |
| `AgentController` — `_compact_state()`, `_build_payload()`, timeout, no fallback | done ✓ |
| `nominal_reference.py` — empirical nominal derivation | done ✓ |
| `experiment_runner.py` — two-pass: derive nominal → run modes | done ✓ |
| `dataset_auditor.py` — two-pass audit with empirical nominal | done ✓ |
| S0–S4 dataset (49 usable runs) | done ✓ |

### Remaining work

| Step | Task |
|---|---|
| 1 | Add compound-condition rules to heuristic controller |
| 2 | Add tests for `nominal_reference.py` (`is_eligible`, `default_nominal_reference`, `nominal_reference_to_config`) |
| 3 | Add tests for `openai_agent.py` (`_build_request_body`, `_extract_output_text`, integration) |
| 4 | Add tests for `AgentController._compact_state` and `_build_payload` |
| 5 | Add `compute_paper_metrics()` + `summarize_by_scenario()` to `Evaluator` |
| 6 | Update `Reporter` + `ExperimentRunner` to write `paper_metrics.json` + `scenario_summary.json` |
| 7 | Collect 9 mixed-failure runs (manual) |
| 8 | Run full experiment and verify output |
