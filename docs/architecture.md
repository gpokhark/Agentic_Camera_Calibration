Good. This is the right next step.

I’m going to give you a buildable package in this order:

1. **Minimum dataset**
2. **Minimum experiments**
3. **System design / software architecture**
4. **Module APIs**
5. **Pseudocode**
6. **Heuristic rule table**
7. **Agent prompt + JSON schema side by side**

This will be scoped for a **single USB camera + ChArUco board** and designed so you can later extend it.

---

# 1. Minimum Dataset You Should Collect

You are not training a neural network. So your dataset should be **small, controlled, scenario-based, and repeatable**.

## 1.1 Hardware Setup

Use:

* 1 USB camera
* 1 printed ChArUco board mounted flat on rigid backing
* tripod or desk clamp for the camera
* adjustable desk lamp
* books / spacers / wedges to vary camera height and angle
* optional reflective object near board to simulate reflections

## 1.2 Board Recommendation

Use:

* **ChArUco board**
* medium size, ideally A4 or A3
* high print quality
* mounted flat so it does not bend

Record:

* square length in mm
* marker length in mm
* board rows and columns
* ArUco dictionary used

---

## 1.3 Dataset Structure

Organize by scenario and run.

```text
dataset/
  S0_nominal/
    run_01/
      frame_001.png
      frame_002.png
      ...
      metadata.json
    run_02/
  S1_overexposed/
    run_01/
  S2_low_light/
  S3_pose_deviation/
  S4_height_variation/
  S5_partial_visibility/
```

Each `metadata.json` should contain at least:

```json
{
  "scenario": "S3_pose_deviation",
  "run_id": "run_04",
  "camera_id": "usb_cam_01",
  "board_type": "charuco",
  "board_config": {
    "squares_x": 7,
    "squares_y": 5,
    "square_length_mm": 30.0,
    "marker_length_mm": 22.0,
    "dictionary": "DICT_4X4_50"
  },
  "notes": "camera pitched downward about 8 degrees relative to nominal"
}
```

---

## 1.4 Minimum Scenarios

Use exactly these **6 scenarios**.

### S0 Nominal

Normal light, good visibility, near-nominal pose.

Purpose:

* establish baseline
* verify pipeline works
* produce nominal reference behavior

### S1 Overexposed / Glare

Strong lamp causes highlight saturation and glare on board.

Purpose:

* simulate plant bright light and floor glare

### S2 Low Light

Dim environment or underexposed capture.

Purpose:

* simulate poor plant lighting

### S3 Pose Deviation

Camera angle intentionally shifted from nominal using wedge/shim.

Purpose:

* simulate assembly angle tolerance

### S4 Height Variation

Raise or lower camera relative to nominal height using spacers/books.

Purpose:

* simulate ride-height-like geometric shift

### S5 Partial Visibility / Occlusion

Board only partly visible or partly occluded.

Purpose:

* simulate incomplete target visibility

That is enough for a serious first study.

---

## 1.5 Number of Runs

Use:

* **10 runs per scenario**
* **12 to 20 frames per run**

So total:

* 6 scenarios × 10 runs = **60 runs**
* roughly 720 to 1200 frames total

That is the right size for this project.

Bigger is not better here. Bigger just means more debugging.

---

## 1.6 What a Run Should Contain

Each run is a single calibration attempt under one scenario condition.

Within one run, capture **diverse frames**, meaning the board appears with different geometry in the image.

Each run should include:

* 3 to 4 frames with board near center
* 3 to 4 frames with board near left/right/top/bottom
* 3 to 4 frames with tilted board pose
* 2 to 4 frames at different distances or scale

Do not capture 20 nearly identical images. That is weak data.

---

## 1.7 Reserve Extra Frames for Recovery

This matters.

For each run, capture:

* **12 primary frames**
* **4 to 8 reserved extra frames**

Why:

* the heuristic and agent both need a fair way to "request additional views"
* in offline experiments, that means they can pull from reserved frames

So total per run can be 16 to 20 frames, but only 12 are the initial attempt set.

---

# 2. Minimum Experiments You Should Run

You need a clean comparison with **three systems**:

1. **Baseline**
2. **Heuristic recovery**
3. **Agent recovery**

Anything less is weak.

---

## 2.1 Experiment A: Baseline Validation

### Goal

Show the standard OpenCV ChArUco pipeline works under nominal conditions.

### Data

* S0 only

### System

* baseline only

### Outputs

* calibration success rate
* reprojection error
* valid frame count
* detected marker/corner statistics
* deviation stability

### Expected result

* near-perfect success
* low reprojection error
* stable results

If this fails, nothing else matters.

---

## 2.2 Experiment B: Failure Characterization

### Goal

Show how baseline fails under disturbances.

### Data

* S1 to S5

### System

* baseline only

### Outputs

* failure rate by scenario
* reprojection error by scenario
* common failure reasons
* frame quality degradation patterns

### Why this matters

This defines the problem your recovery methods are solving.

---

## 2.3 Experiment C: Baseline vs Heuristic vs Agent

### Goal

Main experiment.

### Systems

* baseline
* heuristic
* agent

### Data

* S1 to S5

### Metrics

* success rate
* recovery rate
* final reprojection error
* retries used
* percentage declared unrecoverable

### Primary metric

**Recovery rate**:

[
Recovery\ Rate = \frac{\text{runs failed by baseline but recovered by method}}{\text{runs failed by baseline}}
]

This is probably your headline result.

---

## 2.4 Experiment D: Mixed-Failure Stress Test

This is where the agent has the best chance to prove value.

### Add combined scenarios

You do not need a full new dataset. Just create a small subset:

* overexposure + pose deviation
* low light + partial visibility
* glare + height variation

Collect:

* **3 runs per mixed scenario**

So:

* 3 mixed scenarios × 3 runs = **9 extra runs**

### Why this matters

Heuristics usually do okay on single-cause failures.
The agent should do better on interacting failures.

This is where your paper becomes interesting.

---

## 2.5 Minimal Experimental Matrix

| Scenario              | Runs | Baseline | Heuristic | Agent |
| --------------------- | ---: | -------: | --------: | ----: |
| S0 Nominal            |   10 |      Yes |        No |    No |
| S1 Overexposed        |   10 |      Yes |       Yes |   Yes |
| S2 Low Light          |   10 |      Yes |       Yes |   Yes |
| S3 Pose Deviation     |   10 |      Yes |       Yes |   Yes |
| S4 Height Variation   |   10 |      Yes |       Yes |   Yes |
| S5 Partial Visibility |   10 |      Yes |       Yes |   Yes |
| Mixed 1               |    3 |      Yes |       Yes |   Yes |
| Mixed 2               |    3 |      Yes |       Yes |   Yes |
| Mixed 3               |    3 |      Yes |       Yes |   Yes |

That is enough for a good first paper.

---

# 3. Evaluation Metrics

Use these and do not overcomplicate.

## 3.1 Primary Metrics

### Success Rate

Percentage of runs that produce acceptable calibration.

### Recovery Rate

Percentage of baseline failures recovered by heuristic or agent.

### Final Reprojection Error

Mean reprojection error on successful runs.

---

## 3.2 Secondary Metrics

### Retries Used

Mean retries to success.

### Valid Frames Used

Mean number of usable frames in successful calibration.

### Unrecoverable Precision

How often the system correctly gives up instead of forcing bad calibration.

### Scenario-wise Performance

Performance broken down by S1 to S5 and mixed scenarios.

This breakdown is mandatory.

---

# 4. System Design / Software Architecture

Use one shared pipeline with pluggable controllers.

## 4.1 Top-Level Architecture

```text
           +----------------------+
           | Dataset / USB Camera |
           +----------+-----------+
                      |
                      v
           +----------------------+
           | Frame Acquisition     |
           +----------+-----------+
                      |
                      v
           +----------------------+
           | ChArUco Detection     |
           +----------+-----------+
                      |
                      v
           +----------------------+
           | Quality Analysis      |
           +----------+-----------+
                      |
                      v
           +----------------------+
           | Calibration Engine    |
           | (OpenCV)              |
           +----------+-----------+
                      |
                      v
           +----------------------+
           | Deviation Analyzer    |
           +----------+-----------+
                      |
                      v
           +----------------------+
           | Failure Detector      |
           +----------+-----------+
                      |
            pass      |      intervene
                      v
           +----------------------+
           | Recovery Controller   |
           |  - Heuristic          |
           |  - Agent              |
           +----------+-----------+
                      |
                      v
           +----------------------+
           | Recovery Executor     |
           +----------+-----------+
                      |
                      v
           +----------------------+
           | Re-run Calibration    |
           +----------------------+
```

---

## 4.2 Design Principle

Everything must be shared except the decision layer.

Shared:

* dataset
* detection
* quality metrics
* calibration engine
* failure detector
* action executor
* retry budget
* success thresholds

Different:

* heuristic decision logic
* agent decision logic

That keeps the comparison fair.

---

# 5. Module Breakdown

Suggested project structure:

```text
src/
  config.py
  models.py
  dataset_loader.py
  capture.py
  charuco_detector.py
  quality_analyzer.py
  calibration_engine.py
  deviation_analyzer.py
  failure_detector.py
  controllers/
    base.py
    heuristic_controller.py
    agent_controller.py
  recovery_executor.py
  orchestrator.py
  reporter.py
  experiment_runner.py
  evaluator.py
```

---

# 6. Core Data Models

Use typed models so your interface stays sane.

## 6.1 FrameRecord

```python
from dataclasses import dataclass
from typing import Optional, Any
import numpy as np

@dataclass
class FrameRecord:
    frame_id: str
    image: np.ndarray
    scenario: str
    run_id: str
    is_reserved: bool
    metadata: dict
```

## 6.2 DetectionResult

```python
@dataclass
class DetectionResult:
    frame_id: str
    detection_success: bool
    markers_detected: int
    charuco_corners_detected: int
    coverage_score: float
    marker_ids: Optional[np.ndarray]
    marker_corners: Optional[list]
    charuco_ids: Optional[np.ndarray]
    charuco_corners: Optional[np.ndarray]
```

## 6.3 QualityMetrics

```python
@dataclass
class QualityMetrics:
    frame_id: str
    mean_brightness: float
    contrast_score: float
    blur_score: float
    saturation_ratio: float
    glare_score: float
    usable: bool
    reasons: list[str]
```

## 6.4 CalibrationResult

```python
@dataclass
class CalibrationResult:
    success: bool
    reprojection_error: float | None
    camera_matrix: np.ndarray | None
    distortion_coeffs: np.ndarray | None
    valid_frames_used: int
    rejected_frames: int
    failure_reasons: list[str]
```

## 6.5 DeviationResult

```python
@dataclass
class DeviationResult:
    pitch_deg: float
    yaw_deg: float
    roll_deg: float
    tx_mm: float
    ty_mm: float
    tz_mm: float
    aggregate_pose_error: float
    within_nominal_bounds: bool
```

## 6.6 FailureEvaluation

```python
@dataclass
class FailureEvaluation:
    status: str  # "pass" or "intervene"
    reason_codes: list[str]
    confidence: float
```

## 6.7 AgentState / ControllerState

This should be identical for heuristic and agent.

```python
@dataclass
class ControllerState:
    run_id: str
    scenario: str
    retry_index: int
    frames_total: int
    frames_active: int
    frames_reserved_remaining: int
    mean_brightness: float
    mean_saturation_ratio: float
    mean_blur_score: float
    mean_glare_score: float
    mean_marker_count: float
    mean_charuco_corner_count: float
    mean_coverage_score: float
    calibration_success: bool
    reprojection_error: float | None
    deviation_result: DeviationResult | None
    reason_codes: list[str]
    attempted_actions: list[dict]
    allowed_actions: list[str]
```

## 6.8 RecoveryDecision

```python
@dataclass
class RecoveryDecision:
    diagnosis: str
    actions: list[dict]
    confidence: float
    declare_unrecoverable: bool
```

---

# 7. Module APIs

## 7.1 dataset_loader.py

```python
class DatasetLoader:
    def load_run(self, run_path: str) -> list[FrameRecord]:
        ...

    def split_initial_and_reserved(self, frames: list[FrameRecord]) -> tuple[list[FrameRecord], list[FrameRecord]]:
        ...
```

---

## 7.2 charuco_detector.py

```python
class CharucoDetector:
    def __init__(self, board, aruco_dict, detector_params):
        ...

    def detect(self, frame: FrameRecord) -> DetectionResult:
        ...
```

---

## 7.3 quality_analyzer.py

```python
class QualityAnalyzer:
    def analyze(self, frame: FrameRecord) -> QualityMetrics:
        ...
```

Metrics to compute:

* mean brightness
* contrast score
* blur score using Laplacian variance
* saturation ratio
* glare score
* usable yes/no

---

## 7.4 calibration_engine.py

```python
class CalibrationEngine:
    def calibrate(
        self,
        frames: list[FrameRecord],
        detections: list[DetectionResult],
        mode: str = "charuco_standard"
    ) -> CalibrationResult:
        ...
```

---

## 7.5 deviation_analyzer.py

```python
class DeviationAnalyzer:
    def compute_deviation(
        self,
        calibration_result: CalibrationResult,
        nominal_pose: dict
    ) -> DeviationResult | None:
        ...
```

---

## 7.6 failure_detector.py

```python
class FailureDetector:
    def evaluate(
        self,
        calibration_result: CalibrationResult,
        deviation_result: DeviationResult | None,
        quality_metrics: list[QualityMetrics],
        detections: list[DetectionResult]
    ) -> FailureEvaluation:
        ...
```

---

## 7.7 controllers/base.py

```python
from abc import ABC, abstractmethod

class RecoveryController(ABC):
    @abstractmethod
    def decide(self, state: ControllerState) -> RecoveryDecision:
        pass
```

---

## 7.8 controllers/heuristic_controller.py

```python
class HeuristicController(RecoveryController):
    def decide(self, state: ControllerState) -> RecoveryDecision:
        ...
```

---

## 7.9 controllers/agent_controller.py

```python
class AgentController(RecoveryController):
    def decide(self, state: ControllerState) -> RecoveryDecision:
        ...
```

---

## 7.10 recovery_executor.py

```python
class RecoveryExecutor:
    def execute(
        self,
        decision: RecoveryDecision,
        active_frames: list[FrameRecord],
        reserved_frames: list[FrameRecord],
        detections: list[DetectionResult],
        quality_metrics: list[QualityMetrics]
    ) -> tuple[list[FrameRecord], list[FrameRecord], dict]:
        ...
```

This returns:

* new active frame set
* updated reserved frame set
* action execution log

---

## 7.11 orchestrator.py

```python
class CalibrationOrchestrator:
    def run(
        self,
        initial_frames: list[FrameRecord],
        reserved_frames: list[FrameRecord],
        controller: RecoveryController,
        run_id: str,
        scenario: str
    ) -> dict:
        ...
```

---

## 7.12 experiment_runner.py

```python
class ExperimentRunner:
    def run_all(self, dataset_root: str) -> None:
        ...
```

This should run each run through:

* baseline
* heuristic
* agent

---

# 8. Orchestrator Pseudocode

This is the core logic.

```python
def run_pipeline(initial_frames, reserved_frames, controller, config, run_id, scenario):
    active_frames = initial_frames[:]
    attempted_actions = []
    max_retries = config.max_retries

    for retry_index in range(max_retries + 1):
        detections = [detector.detect(f) for f in active_frames]
        quality = [quality_analyzer.analyze(f) for f in active_frames]

        calib_result = calibration_engine.calibrate(active_frames, detections)
        deviation = None
        if calib_result.success:
            deviation = deviation_analyzer.compute_deviation(
                calib_result, config.nominal_pose
            )

        failure_eval = failure_detector.evaluate(
            calib_result, deviation, quality, detections
        )

        if failure_eval.status == "pass":
            return {
                "status": "success",
                "run_id": run_id,
                "scenario": scenario,
                "retry_index": retry_index,
                "calibration_result": calib_result,
                "deviation_result": deviation,
                "attempted_actions": attempted_actions
            }

        if controller is None:
            return {
                "status": "failed",
                "run_id": run_id,
                "scenario": scenario,
                "retry_index": retry_index,
                "calibration_result": calib_result,
                "deviation_result": deviation,
                "attempted_actions": attempted_actions,
                "reason_codes": failure_eval.reason_codes
            }

        if retry_index == max_retries:
            return {
                "status": "failed",
                "run_id": run_id,
                "scenario": scenario,
                "retry_index": retry_index,
                "calibration_result": calib_result,
                "deviation_result": deviation,
                "attempted_actions": attempted_actions,
                "reason_codes": failure_eval.reason_codes
            }

        state = build_controller_state(
            run_id=run_id,
            scenario=scenario,
            retry_index=retry_index,
            active_frames=active_frames,
            reserved_frames=reserved_frames,
            detections=detections,
            quality=quality,
            calib_result=calib_result,
            deviation=deviation,
            failure_eval=failure_eval,
            attempted_actions=attempted_actions,
            allowed_actions=config.allowed_actions
        )

        decision = controller.decide(state)

        if decision.declare_unrecoverable:
            return {
                "status": "failed_unrecoverable",
                "run_id": run_id,
                "scenario": scenario,
                "retry_index": retry_index,
                "attempted_actions": attempted_actions,
                "decision": decision
            }

        active_frames, reserved_frames, exec_log = recovery_executor.execute(
            decision, active_frames, reserved_frames, detections, quality
        )

        attempted_actions.append({
            "retry_index": retry_index,
            "decision": decision,
            "execution": exec_log
        })
```

---

# 9. Failure Detector Pseudocode

Keep this shared.

```python
def evaluate(calibration_result, deviation_result, quality_metrics, detections):
    reason_codes = []

    if not calibration_result.success:
        reason_codes.append("calibration_failed")

    if calibration_result.reprojection_error is not None and calibration_result.reprojection_error > 2.0:
        reason_codes.append("high_reprojection_error")

    usable_frames = [q for q in quality_metrics if q.usable]
    if len(usable_frames) < 8:
        reason_codes.append("insufficient_usable_frames")

    mean_sat = np.mean([q.saturation_ratio for q in quality_metrics]) if quality_metrics else 0
    if mean_sat > 0.15:
        reason_codes.append("overexposure")

    mean_blur = np.mean([q.blur_score for q in quality_metrics]) if quality_metrics else 0
    if mean_blur < 50:
        reason_codes.append("blur_or_low_detail")

    mean_corners = np.mean(
        [d.charuco_corners_detected for d in detections if d.detection_success]
    ) if detections else 0
    if mean_corners < 12:
        reason_codes.append("low_corner_count")

    mean_coverage = np.mean(
        [d.coverage_score for d in detections if d.detection_success]
    ) if detections else 0
    if mean_coverage < 0.35:
        reason_codes.append("low_marker_coverage")

    if deviation_result is not None and not deviation_result.within_nominal_bounds:
        reason_codes.append("pose_out_of_range")

    if not reason_codes:
        return FailureEvaluation(status="pass", reason_codes=[], confidence=0.95)

    return FailureEvaluation(
        status="intervene",
        reason_codes=reason_codes,
        confidence=0.35
    )
```

---

# 10. Heuristic Rule Table

This needs to be credible, not intentionally dumb.

## 10.1 Rule Philosophy

The heuristic controller should:

* handle simple failures deterministically
* support multi-step actions
* stop after repeated similar failures

It should not be trivial.

---

## 10.2 Heuristic Rule Table

| Rule ID | Trigger Condition                                            | Interpretation                                | Action(s)                                              |
| ------- | ------------------------------------------------------------ | --------------------------------------------- | ------------------------------------------------------ |
| H1      | mean_saturation_ratio > 0.15                                 | overexposure likely corrupting detections     | reject_bad_frames with max_saturation_ratio=0.12       |
| H2      | mean_blur_score < 50                                         | blur or low detail harming corner detection   | reject_bad_frames with min_blur_score=50               |
| H3      | contrast_score low across many frames                        | low contrast reducing marker decoding         | apply_preprocessing mode=clahe                         |
| H4      | mean_charuco_corner_count < 12 and reserved frames available | current set lacks enough usable corners       | request_additional_views count=4                       |
| H5      | mean_coverage_score < 0.35                                   | board positions lack image coverage diversity | request_additional_views pattern=edge_coverage count=4 |
| H6      | reprojection_error > 2.0 and sufficient detections exist     | some frames likely are outliers               | retry_with_filtered_subset top_k=8                     |
| H7      | pose_out_of_range and glare low and blur acceptable          | true geometry may exceed nominal assumption   | relax_nominal_prior pose_margin_scale=1.25             |
| H8      | overexposure and low_corner_count together                   | brightness likely primary failure source      | reject_bad_frames + apply_preprocessing                |
| H9      | low_light inferred and low_corner_count together             | poor visibility likely primary cause          | apply_preprocessing + request_additional_views         |
| H10     | partial_visibility and low_coverage together                 | board coverage insufficient                   | request_additional_views pattern=edge_and_tilt count=6 |
| H11     | same reason pattern repeated for 2 retries                   | recovery unlikely with current actions        | declare_unrecoverable                                  |
| H12     | no reserved frames left and reprojection still high          | cannot improve evidence further               | declare_unrecoverable                                  |

---

## 10.3 Example Heuristic Decision Logic

```python
def decide(state):
    actions = []
    reasons = set(state.reason_codes)

    if state.mean_saturation_ratio > 0.15:
        actions.append({
            "action": "reject_bad_frames",
            "params": {"max_saturation_ratio": 0.12}
        })

    if state.mean_blur_score < 50:
        actions.append({
            "action": "reject_bad_frames",
            "params": {"min_blur_score": 50}
        })

    if "low_corner_count" in reasons and state.frames_reserved_remaining >= 4:
        actions.append({
            "action": "request_additional_views",
            "params": {"count": 4, "pattern": "general_diversity"}
        })

    if "low_marker_coverage" in reasons and state.frames_reserved_remaining >= 4:
        actions.append({
            "action": "request_additional_views",
            "params": {"count": 4, "pattern": "edge_coverage"}
        })

    if state.reprojection_error is not None and state.reprojection_error > 2.0:
        actions.append({
            "action": "retry_with_filtered_subset",
            "params": {"top_k": 8}
        })

    if "pose_out_of_range" in reasons and state.mean_glare_score < 0.1 and state.mean_blur_score >= 50:
        actions.append({
            "action": "relax_nominal_prior",
            "params": {"pose_margin_scale": 1.25}
        })

    if repeated_reason_pattern(state.attempted_actions, state.reason_codes):
        return RecoveryDecision(
            diagnosis="Repeated failure pattern, further recovery unlikely.",
            actions=[],
            confidence=0.78,
            declare_unrecoverable=True
        )

    if not actions:
        return RecoveryDecision(
            diagnosis="No useful deterministic recovery action available.",
            actions=[],
            confidence=0.6,
            declare_unrecoverable=True
        )

    return RecoveryDecision(
        diagnosis="Heuristic recovery selected based on threshold rules.",
        actions=deduplicate_actions(actions),
        confidence=0.72,
        declare_unrecoverable=False
    )
```

---

# 11. Agent Prompt + JSON Schema Side by Side

This is what you asked for explicitly.

The idea is:

* same input state as heuristic
* same allowed actions
* strict structured output

---

## 11.1 Shared Input State Example

```json
{
  "run_id": "S1_run_03",
  "scenario": "overexposed",
  "retry_index": 1,
  "frames_total": 12,
  "frames_active": 8,
  "frames_reserved_remaining": 4,
  "mean_brightness": 228.4,
  "mean_saturation_ratio": 0.21,
  "mean_blur_score": 71.3,
  "mean_glare_score": 0.36,
  "mean_marker_count": 9.8,
  "mean_charuco_corner_count": 11.2,
  "mean_coverage_score": 0.29,
  "calibration_success": false,
  "reprojection_error": 2.94,
  "deviation_result": {
    "pitch_deg": 4.8,
    "yaw_deg": 2.1,
    "roll_deg": 1.5,
    "tx_mm": 1.1,
    "ty_mm": 0.7,
    "tz_mm": 14.2,
    "aggregate_pose_error": 5.6,
    "within_nominal_bounds": false
  },
  "reason_codes": [
    "overexposure",
    "low_corner_count",
    "low_marker_coverage",
    "pose_out_of_range"
  ],
  "attempted_actions": [],
  "allowed_actions": [
    "reject_bad_frames",
    "apply_preprocessing",
    "request_additional_views",
    "retry_with_filtered_subset",
    "relax_nominal_prior",
    "declare_unrecoverable"
  ]
}
```

---

## 11.2 Side-by-Side: Heuristic vs Agent

| Aspect         | Heuristic Controller        | Agent Controller                       |
| -------------- | --------------------------- | -------------------------------------- |
| Input          | structured controller state | exact same structured controller state |
| Decision basis | fixed threshold rules       | LLM reasoning over state               |
| Action space   | fixed allowed actions       | exact same allowed actions             |
| Output format  | RecoveryDecision object     | validated JSON matching same schema    |
| Retry budget   | shared                      | shared                                 |
| Executor       | shared                      | shared                                 |

That parity is what makes the comparison defensible.

---

## 11.3 Agent System Prompt

```text
You are a camera calibration recovery controller.

You are given structured diagnostics from a ChArUco-based camera calibration pipeline.
Your job is to select safe recovery actions when calibration fails or becomes unreliable.

Important rules:
1. Do not invent new actions.
2. Only use actions from the allowed_actions list.
3. Base your reasoning only on the provided structured metrics.
4. Do not claim calibration is correct if the evidence is weak.
5. Prefer minimal interventions.
6. If repeated failures indicate recovery is unlikely, declare unrecoverable.
7. Return valid JSON only.
8. The output must follow the provided schema exactly.
9. Explain the likely primary cause and choose actions in a sensible order.
10. Do not use more than 3 actions in one decision unless absolutely necessary.
```

---

## 11.4 Agent User Prompt Template

```text
Calibration recovery request.

Current controller state:
{{controller_state_json}}

Return JSON with:
- diagnosis
- actions
- confidence
- declare_unrecoverable

Interpretation guidance:
- High saturation suggests overexposure or glare.
- Low blur score suggests poor focus or motion blur.
- Low ChArUco corners or low coverage suggests insufficient target evidence.
- Pose out of range may indicate true geometric deviation, but only trust that if image quality is adequate.
- If image quality is poor, prioritize improving evidence before relaxing geometric assumptions.
- If similar failures have already repeated, declare unrecoverable.
```

---

## 11.5 JSON Output Schema

Use a strict schema.

```json
{
  "type": "object",
  "properties": {
    "diagnosis": {
      "type": "string"
    },
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "action": {
            "type": "string",
            "enum": [
              "reject_bad_frames",
              "apply_preprocessing",
              "request_additional_views",
              "retry_with_filtered_subset",
              "relax_nominal_prior",
              "declare_unrecoverable"
            ]
          },
          "params": {
            "type": "object"
          }
        },
        "required": ["action", "params"],
        "additionalProperties": false
      }
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "declare_unrecoverable": {
      "type": "boolean"
    }
  },
  "required": [
    "diagnosis",
    "actions",
    "confidence",
    "declare_unrecoverable"
  ],
  "additionalProperties": false
}
```

---

## 11.6 Example Agent Output

```json
{
  "diagnosis": "Primary failure cause is overexposure and glare, which reduces usable ChArUco detections and makes the current pose estimate unreliable. Improve image evidence before relaxing geometric assumptions.",
  "actions": [
    {
      "action": "reject_bad_frames",
      "params": {
        "max_saturation_ratio": 0.12
      }
    },
    {
      "action": "apply_preprocessing",
      "params": {
        "mode": "clahe"
      }
    },
    {
      "action": "request_additional_views",
      "params": {
        "count": 4,
        "pattern": "edge_coverage"
      }
    }
  ],
  "confidence": 0.84,
  "declare_unrecoverable": false
}
```

---

# 12. Recovery Executor Behavior

The executor must be the same for heuristic and agent.

## 12.1 Supported Actions

### reject_bad_frames

Filter out frames violating quality constraints.

Parameters:

* `max_saturation_ratio`
* `min_blur_score`
* `min_charuco_corners`
* `min_coverage_score`

### apply_preprocessing

Allowed modes:

* `clahe`
* `gamma_correction`
* `contrast_normalization`

### request_additional_views

In offline experiments:

* move `count` frames from reserved to active set according to requested pattern

Patterns:

* `general_diversity`
* `edge_coverage`
* `edge_and_tilt`

### retry_with_filtered_subset

Keep best `top_k` frames based on combined quality score.

### relax_nominal_prior

Update deviation acceptance range for next attempt within fixed safety bounds.

### declare_unrecoverable

No-op in executor, terminal in orchestrator.

---

## 12.2 Executor Pseudocode

```python
def execute(decision, active_frames, reserved_frames, detections, quality_metrics):
    exec_log = {"applied_actions": []}

    for action_obj in decision.actions:
        action = action_obj["action"]
        params = action_obj["params"]

        if action == "reject_bad_frames":
            active_frames = filter_frames(active_frames, quality_metrics, detections, params)
            exec_log["applied_actions"].append({"action": action, "params": params})

        elif action == "apply_preprocessing":
            active_frames = preprocess_frames(active_frames, mode=params["mode"])
            exec_log["applied_actions"].append({"action": action, "params": params})

        elif action == "request_additional_views":
            selected, reserved_frames = pull_reserved_frames(
                reserved_frames,
                count=params.get("count", 4),
                pattern=params.get("pattern", "general_diversity")
            )
            active_frames.extend(selected)
            exec_log["applied_actions"].append({
                "action": action,
                "params": params,
                "added_frame_ids": [f.frame_id for f in selected]
            })

        elif action == "retry_with_filtered_subset":
            active_frames = keep_top_k_frames(active_frames, quality_metrics, detections, params["top_k"])
            exec_log["applied_actions"].append({"action": action, "params": params})

        elif action == "relax_nominal_prior":
            exec_log["applied_actions"].append({"action": action, "params": params})

    return active_frames, reserved_frames, exec_log
```

---

# 13. Experiment Runner Logic

Run each non-nominal run through all three modes.

```python
for run in all_runs:
    initial_frames, reserved_frames = loader.split_initial_and_reserved(run.frames)

    result_baseline = orchestrator.run(
        initial_frames=copy(initial_frames),
        reserved_frames=copy(reserved_frames),
        controller=None,
        run_id=run.run_id,
        scenario=run.scenario
    )

    result_heuristic = orchestrator.run(
        initial_frames=copy(initial_frames),
        reserved_frames=copy(reserved_frames),
        controller=heuristic_controller,
        run_id=run.run_id,
        scenario=run.scenario
    )

    result_agent = orchestrator.run(
        initial_frames=copy(initial_frames),
        reserved_frames=copy(reserved_frames),
        controller=agent_controller,
        run_id=run.run_id,
        scenario=run.scenario
    )

    save_results(result_baseline, result_heuristic, result_agent)
```

---

# 14. What Results You Should Expect if This Is Working

## Baseline

* strong on S0
* weak on S1 to S5
* especially weak on mixed scenarios

## Heuristic

* recovers simple single-cause cases
* still struggles on interacting failures

## Agent

* should be similar to heuristic on easy cases
* should outperform heuristic on mixed-cause cases

If the agent does not outperform heuristic on mixed failures, your LLM contribution is weak.

That is the hard truth.

---

# 15. Recommended Build Order

Do it exactly like this:

## Step 1

Implement ChArUco detection and baseline calibration.

## Step 2

Implement quality metrics and failure detector.

## Step 3

Collect S0 to S5 dataset.

## Step 4

Run baseline and characterize failures.

## Step 5

Implement heuristic controller.

## Step 6

Implement agent controller using same input and same actions.

## Step 7

Run full comparison.

This order avoids wasting time.

---

# 16. Final Recommendation

Your minimum serious implementation is:

* **1 USB camera**
* **1 ChArUco board**
* **60 core runs + 9 mixed runs**
* **3 comparison modes**
* **shared pipeline**
* **shared action space**
* **strict agent schema**
* **scenario-wise evaluation**

That is enough for a credible first paper.

