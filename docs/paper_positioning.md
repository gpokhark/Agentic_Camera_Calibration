# Paper Positioning Memo

Use [paper_north_star.md](/D:/github/Agentic_Camera_Calibration/docs/paper_north_star.md)
as the canonical source of truth for the paper direction. This memo is a
reviewer-facing assessment layered on top of that north star.

This memo is a reviewer-facing assessment of the current project state and what
should be strengthened before treating it as paper-ready.

It is written to answer four practical questions:

1. What is already strong?
2. What will a reviewer likely challenge?
3. What should be fixed before submission?
4. How should the experiments be redesigned to better match the automotive
   end-of-line framing?

## 1. Current Thesis

The current thesis is still strong and still aligned with the original idea:

> Classical camera calibration remains unchanged, while a decision layer
> diagnoses failure causes and selects recovery actions to reduce false rejects
> under real-world variability.

That is still a publishable idea because it is:

- grounded in a real industrial problem
- experimentally testable with a desk-scale proxy setup
- measurable using structured diagnostics and controlled disturbances
- not trying to replace established geometry with an opaque model

The cleanest paper framing is:

- classical geometry does the calibration
- the new contribution is decision intelligence under failure
- the comparison is baseline vs heuristic vs agent
- the real target is false reject reduction under realistic disturbances

## 2. What Is Already Strong

### 2.1 The Problem Motivation Is Real

The automotive end-of-line calibration framing is credible:

- plant lighting can create overexposure and glare
- assembly tolerances can shift effective camera pose
- ride-height-like variation can change geometry
- partial visibility and weak coverage can corrupt target evidence

That motivation is not artificial. It maps naturally to your desk setup.

### 2.2 The System Decomposition Is Good

The architecture separates concerns well:

- ChArUco detection and calibration stay classical
- quality analysis and failure detection are explicit
- the controller only selects from a fixed action set
- heuristic and agent share the same state and same executor

This is a major strength because it makes the comparison interpretable.

### 2.3 The Dataset Is More Useful Than It Looks

The current dataset is not a failure.

From the existing audit:

- almost all runs are considered usable for analysis
- nominal runs are mostly stable enough to derive an empirical reference
- disturbed scenarios are visibly expressed in the metrics

This means the collection effort was worthwhile. The current issue is mostly
not data scarcity; it is evaluation semantics.

### 2.4 The Cost-Aware Agent Direction Is Sensible

The recent workflow improvements are good research engineering:

- offline `baseline` and `heuristic` runs can be done without any API key
- selective `--scenario`, `--run-id`, and `--mode` filters reduce agent spend
- the agent can be reserved for a curated subset of difficult runs

That is not only practical. It can also become part of the paper story:

- use cheap deterministic logic broadly
- use the agent selectively for ambiguous failure states

That selective escalation framing is much stronger than "run an LLM on every
case."

## 3. What Reviewers Will Likely Challenge

### 3.1 The Current Success Metric Is Not Realistic Enough

This is the biggest issue.

The current experiment results show zero success in both baseline and heuristic
mode, even though most runs still calibrate successfully at the OpenCV level.
That means the present pass/fail metric is too strict to reflect realistic
acceptance behavior.

A reviewer may say:

- the pipeline is not actually comparing recovery quality
- it is collapsing warning-level signals into hard failures
- the benchmark is misaligned with the stated false-reject problem

That criticism would be valid unless the evaluation logic is refined.

### 3.2 The Heuristic Baseline Can Still Be Criticized

The current heuristic is reasonable, but not yet reviewer-proof.

A critical reviewer may ask:

- Was the heuristic strong enough?
- Were combination rules fully implemented?
- Were thresholds tuned fairly and frozen before evaluation?
- Is the heuristic artificially weak so the agent looks better?

If the main claim is "agent beats heuristic," then the heuristic must be hard to
beat and fully documented.

### 3.3 The Dataset Still Lacks Mixed-Failure Coverage

The original idea depends on interacting causes:

- glare + coverage loss
- low light + blur
- pose deviation + partial visibility

Without mixed-condition data, the strongest advantage of the agent is not being
tested.

A reviewer may conclude:

- single-disturbance scenarios are not enough to justify an agentic approach
- a stronger heuristic might handle most of the current cases

### 3.4 The Automotive Mapping Must Be Framed Carefully

The desk setup is valid as a proxy, but only if you make claims carefully.

A reviewer may object if the paper implies:

- full vehicle realism
- direct production readiness
- automotive-grade validation

The defensible claim is:

- desk-scale experimental proxy for EOL disturbance patterns
- useful for testing decision-layer recovery concepts
- not a full vehicle deployment study

### 3.5 The Nominal Reference Strategy Could Be Challenged

At the moment, the empirical nominal reference is derived from the same pool of
nominal runs used in evaluation.

A reviewer may argue that:

- this weakens independence of the reference
- it may shrink pose deltas artificially
- it reduces rigor for nominal-versus-disturbed comparisons

This can be improved without redoing the whole project.

### 3.6 A Reviewer May Ask "Why Not Just Use Robust Estimation Or A Small Classifier?"

This is a valid challenge and should be addressed directly in the paper.

If the problem is framed as:

- a small set of scalar diagnostics
- a small menu of recovery actions
- one-shot decision making

then a reviewer is right to ask why the controller is not simply:

- a stronger estimator inside the calibration stage
- a deterministic rule table
- a decision tree
- or a compact learned classifier

The response should not be "LLMs are smarter."

The response should be that the repo is not trying to replace geometric
estimation. It is trying to solve a different problem:

- robust estimation improves the geometric fit under outliers
- the recovery controller decides what to do when evidence is mixed,
  ambiguous, or incomplete

That distinction only becomes convincing if the controller is evaluated as a
bounded sequential policy rather than a one-shot metric classifier. In other
words, the paper should emphasize:

- retry history
- bounded actions
- operational cost budget
- mixed-failure interactions
- acceptance-versus-fail decisions under uncertainty

Without that framing, the reviewer criticism remains strong.

## 4. Is The Dataset Bad?

No. The dataset is not bad.

More precise answer:

- it is good enough for development and early experimentation
- it is probably good enough for a workshop-style or systems-positioning paper
- it is not yet complete enough for the strongest possible submission

What is already good:

- `S0_nominal` exists and mostly works
- `S1_overexposed`, `S2_low_light`, `S3_pose_deviation`, and
  `S4_height_variation` all appear to contain meaningful disturbance
- the audit considers almost all runs usable for analysis

What is still missing:

- `S5_partial_visibility` should be completed
- mixed scenarios should be added
- a held-out reference set would make the pose analysis stronger

So the right move is not "throw away the dataset." The right move is
"incrementally strengthen it."

## 5. Do You Need To Capture Additional Data?

Yes, but selectively.

### 5.1 Data You Should Definitely Add

- `S5_partial_visibility` complete run set
- 3 mixed-condition scenario groups
- 3-5 runs per mixed-condition group
- a small held-out nominal reference set

Suggested mixed scenarios:

- `M1`: overexposure + pose deviation
- `M2`: low light + partial visibility
- `M3`: glare + height variation

These are the cases most likely to reveal a real difference between heuristic
and agent reasoning.

### 5.2 Data You Probably Do Not Need To Recollect

- the existing `S0` through `S4` runs, unless later found unusable
- old `S3` and `S4` runs just because the exact deviations cannot be reproduced

Exact reproduction is not necessary. What matters is controlled directional
variation and documented disturbance intent.

### 5.3 Data Collection Priority

If time is limited, collect in this order:

1. held-out nominal reference captures
2. `S5_partial_visibility`
3. mixed-condition runs
4. severity-level variants for `S1` to `S4`

## 6. Where The Project Has Drifted

The project has not drifted away from the core research idea.

The drift is in how success is currently measured.

Original goal:

- reduce false rejects
- distinguish true misalignment from bad data
- decide whether to retry, filter, relax, or fail

Current implementation issue:

- many runs that calibrate successfully are still counted as hard failures
- disturbed runs are treated as unsuccessful merely because disturbance evidence
  remains visible

That is a metric-design problem, not a core-concept problem.

So the answer is:

- no, the research goal has not been lost
- yes, the evaluation logic has drifted away from the industrial question

## 7. How To Make The Paper More Realistic And Impactful

### 7.1 Split "Calibration Success" From "Acceptance Success"

This is the most important fix.

Use at least three evaluation layers:

- `calibration_success`: OpenCV produced a valid calibration result
- `acceptance_success`: the run meets the station acceptance criteria
- `recovery_success`: a run that would otherwise fail becomes acceptable after recovery

This gives a much more realistic EOL interpretation.

### 7.2 Recast The Disturbed Scenarios Properly

Scenarios like `S3_pose_deviation` and `S4_height_variation` should not be
treated as failures simply because they are out of nominal bounds.

Instead, ask:

- Was the disturbance correctly detected?
- Was the system right to attempt recovery or escalate?
- Did recovery improve the evidence without hiding a true geometry issue?

That is far closer to the real manufacturing question.

### 7.3 Strengthen And Freeze The Heuristic

Before final comparisons:

- add more combined-condition rules
- tune thresholds on a development subset
- freeze the heuristic before final evaluation
- publish the full rule table in the paper

This makes the baseline harder to criticize.

### 7.4 Add Mixed-Failure Experiments

If the agent only matches heuristic on simple single-cause scenarios, the paper
is less compelling.

The most publishable outcome is:

- heuristic works well on simple cases
- agent is similar on easy cases
- agent is better on interacting, ambiguous, or multi-factor failures

That is a much more believable claim.

### 7.5 Add A Selective-Escalation Story

Instead of positioning the agent as the default controller, position it as a
targeted escalation policy.

That means:

- run deterministic logic first
- invoke the agent only on ambiguous or repeated-failure cases
- reduce cost while preserving quality

This is practically stronger and publication-wise more interesting.

### 7.6 Align Metrics With EOL Manufacturing Concerns

The most impactful metrics are not just reprojection error.

You should report:

- false reject rate
- recovery rate
- retries per run
- escalation-to-agent frequency
- unrecoverable rate
- unsafe accept risk

If possible, define:

- a nominal acceptance band
- a warning band
- a hard-fail band

That makes the comparison more production-like.

### 7.7 Move The Main Benchmark To A Fixed-Target Protocol

For stronger automotive end-of-line relevance, the main benchmark should use a
fixed target and vary the camera or the environment around that fixed target.

This better matches the actual plant logic:

- the calibration mat stays in one station location
- the arriving camera pose changes from vehicle to vehicle
- lighting, glare, height, and occlusion vary while the target stays fixed

The current moving-board dataset is still useful for development, threshold
tuning, and supplementary analysis, but the fixed-target protocol should become
the primary paper benchmark.

## 8. Recommended Experimental Redesign

### Phase A: Fix Evaluation Semantics

Do this before collecting much more data.

Actions:

- add dual reporting for calibration success and acceptance success
- classify reason codes into warnings vs hard failures
- treat disturbance persistence differently from unrecoverable failure

Expected outcome:

- the current dataset becomes interpretable
- the offline benchmark stops collapsing everything to zero success

### Phase B: Strengthen Baselines

Actions:

- upgrade heuristic with combined-condition rules
- add a compact structured-policy baseline such as a decision tree, random
  forest, or gradient-boosted classifier over the same diagnostics
- document threshold tuning
- freeze the heuristic for final comparisons

Expected outcome:

- reviewer criticism about a weak baseline becomes much weaker
- the agent is compared against both expert rules and a small structured model

### Phase C: Expand Data Selectively

Actions:

- add `S5`
- add held-out nominal references
- add fixed-target versions of the core scenarios
- add mixed scenarios under the fixed-target protocol

Expected outcome:

- the agent is tested in the regime where it should genuinely matter

### Phase D: Cost-Aware Agent Evaluation

Actions:

- use `baseline` and `heuristic` for full-dataset offline sweeps
- use `--scenario`, `--run-id`, and `--mode` to run the agent only on hard cases
- log how often the agent is actually invoked

Expected outcome:

- better practical story
- lower experimental cost
- more defensible deployment framing

## 9. What A Strong Final Claim Would Look Like

A strong and defensible claim would be something like:

> We present a decision-layer recovery framework for target-based camera pose
> estimation and calibration acceptance under end-of-line-like disturbance
> conditions. The framework preserves classical geometric estimation, compares
> deterministic and LLM-based controllers over the same bounded action space,
> and reduces false rejects on ambiguous multi-factor failures. The agent is
> used selectively, after deterministic screening, to control inference cost.

That is much stronger than:

> We used an LLM and it did better than heuristic rules.

## 10. Required Implementation Changes

The repo should be extended in a few specific ways to support a publishable
comparison.

### 10.1 Add A Stronger Structured Baseline

Add a compact non-LLM learned controller that consumes the same structured
diagnostics as the heuristic and agent.

Recommended scope:

- new controller mode: `learned`
- train on development runs only
- choose from the same bounded recovery actions already used by
  `heuristic` and `agent`
- keep the same retry budget and executor

This directly answers the "why not just use a classifier?" objection.

### 10.2 Make The Agent Explicitly Sequential And Budget-Aware

The agent should not behave like a one-shot metric classifier.

It should see:

- current diagnostics
- previous actions
- previous failure reasons
- retry index
- remaining retry budget

That means extending `ControllerState`, compact agent payloads, and
experiment-time logging so the agent is clearly solving a sequential bounded
decision problem.

### 10.3 Make Acceptance Bands Explicit

The warning-vs-hard-fail split should remain, but the reporting should become
more explicit.

Recommended changes:

- define nominal, warning, and hard-fail acceptance bands in config
- expose `accept_with_warning` as a first-class terminal result in reports
- report unsafe-accept risk separately from recovery rate
- keep hard safety guards non-overridable by the agent

### 10.4 Upgrade And Freeze The Heuristic

The heuristic baseline should be intentionally strong and fully documented.

Recommended changes:

- add compound-condition rules
- add scenario-aware rule behavior where justified
- freeze thresholds after development tuning
- document the final rule table in the repo

### 10.5 Separate Development And Evaluation Data

To avoid reviewer concerns about tuning leakage:

- add dataset split support for `train`, `dev`, and `eval`
- tune thresholds and learned-policy parameters on development data only
- keep final evaluation runs separate

### 10.6 Add Fixed-Target Metadata

The dataset should distinguish moving-board pilot data from fixed-target
benchmark data.

Recommended metadata additions:

- `setup_type`
- `camera_motion`
- `target_motion`
- `reference_pose_id`
- `disturbance_bucket`

This allows the old data to remain useful without pretending it is identical to
the stronger EOL-style benchmark.

## 11. What New Data Should Be Captured

The current dataset should be kept, but new capture should focus on a
fixed-target benchmark.

### 11.1 Keep The Existing Dataset

Do not discard the moving-board data. Use it as:

- development data
- threshold-tuning data
- prompt and payload debugging data
- supplementary robustness evidence

### 11.2 Capture A Fixed-Target Core Benchmark

Recommended new scenarios:

- `S0_nominal_fixed`
- `S1_overexposed_fixed`
- `S2_low_light_fixed`
- `S3_pose_deviation_fixed`
- `S4_height_variation_fixed`
- `S5_partial_visibility_fixed`

Recommended minimum:

- 5 runs per scenario to start
- 10 runs per scenario if time allows

### 11.3 Capture Held-Out Reference Runs

Add a small held-out fixed-target reference set that is not used for tuning:

- 5 held-out nominal runs
- small reference subsets for pose and height severity buckets

This improves the rigor of nominal-versus-disturbed comparisons.

### 11.4 Capture Mixed-Failure Fixed-Target Runs

These are the most important scenarios for demonstrating value beyond simple
rules.

Recommended mixed scenarios:

- `M1_fixed`: overexposed + pose deviation
- `M2_fixed`: low light + partial visibility
- `M3_fixed`: glare + height variation

Recommended minimum:

- 3-5 runs per mixed scenario

### 11.5 Capture Priority

If collection time is limited, capture in this order:

1. fixed-target `S0_nominal`
2. fixed-target `S3_pose_deviation`
3. fixed-target `S4_height_variation`
4. fixed-target `S5_partial_visibility`
5. fixed-target `S1_overexposed`
6. fixed-target `S2_low_light`
7. fixed-target mixed scenarios

## 12. Bottom Line

The project is still viable and still publishable.

The current bottleneck is not that the dataset is unusable or that the core
idea has drifted. The bottleneck is that the present evaluation logic is too
strict and is obscuring the signal you actually want to study.

The highest-value next steps are:

1. move the main benchmark to a fixed-target protocol
2. add a strong structured learned baseline in addition to the heuristic
3. strengthen and freeze the heuristic baseline
4. capture held-out reference and mixed-condition fixed-target data
5. evaluate the agent selectively on the ambiguous cases where contextual
   reasoning should matter

If those steps are done, the work becomes much closer to a strong and credible
paper on agentic recovery for calibration failures in an EOL-inspired setting.
