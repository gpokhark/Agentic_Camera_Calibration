# Paper North Star

This document is the canonical source of truth for the research direction of
this repository.

For the short practical execution companion, use
[paper_execution_checklist.md](/D:/github/Agentic_Camera_Calibration/docs/paper_execution_checklist.md).

When the repo evolves, this file should be used to answer one question first:

> Does this change make the project more likely to become a strong,
> publishable research paper?

If the answer is unclear, this document should override local convenience,
feature drift, and implementation inertia.

## 1. Core Research Idea

The paper is not about replacing camera calibration with a language model.

The paper is about a **decision layer for calibration recovery**:

- the geometric calibration pipeline remains classical
- the target setup is framed as an end-of-line-style fixed-target station
- disturbances create ambiguous or degraded calibration evidence
- a controller decides whether to accept, retry, recover, or fail
- the comparison is made across multiple controllers over the same action space

The clean paper claim is:

> A fixed-target, EOL-style calibration recovery benchmark can be used to
> compare baseline, heuristic, learned, and agentic controllers that operate
> over the same structured diagnostics and bounded recovery actions, while
> keeping the classical calibration backbone unchanged.

## 2. What The Paper Is Actually Claiming

The publishable claim should be:

- classical ChArUco/OpenCV calibration remains the perception and geometry
  backbone
- real-world disturbances can cause false rejects, unstable retries, or
  ambiguous acceptance decisions
- recovery is a structured operational decision problem, not just a geometric
  estimation problem
- bounded controllers can be compared fairly because they share:
  - the same diagnostics
  - the same retry budget
  - the same downstream action space
- the agent should be evaluated as a bounded sequential policy, not as a magic
  black box

## 3. The Main Benchmark We Are Building

The main benchmark is:

- `setup_type = benchmark_fixed_target`
- target remains stationary
- camera or environment changes relative to a nominal setup
- final reported results should come from `dataset_split = eval`

The fixed-target benchmark is the paper benchmark because it is the closest
desk-scale proxy to automotive end-of-line calibration logic.

The older moving-target data is still useful, but only as:

- development data
- ablation support
- historical context
- debugging and threshold-tuning support

It is not the main paper benchmark.

## 4. The Scientific Comparison

The comparison should always remain:

- `baseline`
- `heuristic`
- `learned`
- `agent`

The fairness rule is critical:

- same detector
- same quality analyzer
- same calibration engine
- same deviation analysis
- same failure detector
- same recovery executor
- same retry budget
- same action space

Only the decision policy should change.

## 5. What Makes This Publishable

This becomes a credible paper if we can show:

1. The fixed-target benchmark is representative enough of the EOL problem to be
   scientifically meaningful.
2. The failure and recovery problem is not reducible to simple pass/fail
   calibration accuracy alone.
3. The heuristic is strong and fully documented.
4. The learned baseline is a credible non-LLM alternative.
5. The agent helps most on ambiguous, interacting, or multi-factor failures.
6. The agent is used in a cost-aware and operationally realistic way.

The strongest final claim is not:

> The LLM is better at calibration.

It is:

> The agentic controller improves recovery decisions under difficult or mixed
> failure conditions while leaving the calibration math unchanged.

## 6. What Reviewers Will Challenge

We should assume reviewers will ask:

- Why not just use robust estimation?
- Why not use a stronger heuristic?
- Why not use a small classifier or decision tree?
- Is the fixed-target desk setup truly representative of EOL calibration?
- Is the agent genuinely different from a heuristic fallback?
- Is the heuristic intentionally weak?
- Are the metrics aligned with false-reject reduction rather than just
  geometric success?

Every major implementation and data decision should be made so these questions
become easier to answer, not harder.

## 7. What The Agent Must Be

The agent must not be positioned as:

- a replacement for calibration geometry
- a hidden heuristic fallback
- a one-shot classifier over a handful of scalar thresholds

The agent should be positioned as:

- a bounded sequential controller
- operating over structured diagnostics
- aware of retry history and remaining budget
- selecting from a fixed action set
- especially useful for ambiguous and interacting failures

The stronger framing is selective escalation:

- deterministic screening first
- agent invoked for harder or ambiguous cases
- cost tracked explicitly

## 8. Metrics That Matter

The paper should emphasize:

- `calibration_success`
- `acceptance_success`
- `warning_accept_rate`
- `clean_accept_rate`
- `recovery_rate`
- `false_reject_rate`
- retries per run
- agent invocation frequency
- unrecoverable rate

If a future change improves only raw implementation complexity but does not
improve these outputs or their interpretability, it is likely not core paper
work.

## 9. What Counts As Core Work From Now On

Core work:

- fixed-target benchmark capture and audit
- stronger benchmark realism
- stronger baselines
- clearer acceptance semantics
- mixed-condition scenarios
- cost-aware selective agent evaluation
- paper-quality summaries, tables, and ablations

Secondary work:

- GUI polish that does not affect experiments
- convenience automation not tied to benchmark rigor
- large refactors that do not strengthen the paper story
- exploratory features that blur the benchmark definition

If time is limited, always choose core work first.

## 10. Concrete Next Milestones

The next milestones should remain:

1. Capture a small fixed-target benchmark subset:
   - `S0_nominal_fixed`
   - `S3_pose_deviation_fixed`
   - `S4_height_variation_fixed`
   - `S5_partial_visibility_fixed`
2. Audit that subset and verify the benchmark behaves sensibly.
3. Run offline comparison on:
   - `baseline`
   - `heuristic`
   - `learned`
4. Inspect where the benchmark is discriminative and where it is not.
5. Run selective `agent` evaluation only on the hardest scenarios or runs.
6. Add mixed-condition fixed-target scenarios if the single-disturbance results
   are too easy.

## 11. Rules For Future Repo Changes

Before making a substantial change, ask:

1. Does this make the benchmark more representative of EOL calibration?
2. Does this make the comparison fairer or stronger?
3. Does this make the agent more genuinely distinct from heuristics?
4. Does this improve reproducibility, auditability, or paper-quality evidence?
5. Does this help produce better results tables, figures, or reviewer answers?

If the answer is mostly no, the change is likely out of scope for the paper.

## 12. Short Version

The north star for this repo is:

> Build a publishable fixed-target, end-of-line-style calibration recovery
> benchmark where classical calibration remains unchanged and baseline,
> heuristic, learned, and agentic controllers are compared fairly on structured
> recovery decisions under realistic disturbances.

That is the idea we should keep protecting.
