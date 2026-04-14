Below is a **detailed PRD specifically for your 1-camera desk setup + experiments**, structured so you can directly implement and also translate it into an IEEE-style paper later.

---

# 📄 Product Requirements Document (PRD)

## Project Title

**Agentic AI-Based Calibration Recovery for Single-Camera Systems Under Adverse Conditions**

---

# 1. 🎯 Objective

Build a **single-camera calibration system** using a USB camera and ChArUco board that:

1. Performs standard calibration using OpenCV
2. Detects calibration failure due to:

   * lighting issues
   * pose deviation
   * insufficient coverage
3. Uses an **LLM-based agent** to:

   * diagnose failure cause
   * select recovery actions
   * retry calibration
4. Demonstrates **improved recovery rate vs baseline**

---

# 2. 📌 Scope

## Included

* USB camera-based calibration
* ChArUco target detection
* Failure simulation (lighting, pose, occlusion)
* Agent-based recovery loop
* Controlled experiment evaluation

## Excluded

* Real vehicle system
* Multi-camera synchronization
* Production deployment
* Safety-critical validation

---

# 3. 👤 Target Users

* Computer vision researchers
* Calibration engineers
* ADAS / surround view engineers
* Manufacturing test engineers

---

# 4. 🧩 System Overview

## High-Level Pipeline

```text
Capture Frames
      ↓
ChArUco Detection
      ↓
Quality Analysis
      ↓
Calibration (OpenCV)
      ↓
Deviation + Metrics
      ↓
Failure Detection
      ↓
[ IF FAIL ]
      ↓
Agent Decision
      ↓
Recovery Actions
      ↓
Re-run Calibration
```

---

# 5. 🔧 Functional Requirements

---

## FR-1: Frame Acquisition

### Description

Capture frames from USB camera or load dataset.

### Inputs

* camera index OR dataset path
* frame count (12–20 per run)

### Outputs

* list of frames

### Acceptance Criteria

* frames saved with timestamps
* reproducible dataset structure

---

## FR-2: ChArUco Detection

### Description

Detect ArUco markers and interpolate ChArUco corners.

### Inputs

* image frame

### Outputs

* marker count
* charuco corner count
* detection success flag
* coverage score

### Acceptance Criteria

* robust detection under nominal conditions
* partial detection allowed

---

## FR-3: Image Quality Analysis

### Description

Compute quality metrics per frame.

### Metrics

* brightness
* saturation ratio
* blur score
* contrast
* glare estimate

### Acceptance Criteria

* each frame labeled usable / unusable
* reasons logged

---

## FR-4: Calibration Engine

### Description

Perform camera calibration using ChArUco detections.

### Outputs

* camera matrix
* distortion coefficients
* reprojection error
* valid frame count

### Acceptance Criteria

* stable results under nominal scenario
* failure cases correctly flagged

---

## FR-5: Deviation Estimation

### Description

Estimate camera pose deviation from nominal.

### Outputs

* pitch, yaw, roll deviation
* translation deviation
* aggregate error

### Acceptance Criteria

* consistent results across nominal runs
* threshold comparison supported

---

## FR-6: Failure Detection

### Description

Determine whether calibration is reliable.

### Failure Conditions

* reprojection error too high
* too few usable frames
* low corner detection
* poor coverage
* excessive pose deviation
* bad image quality

### Output

```json
{
  "status": "pass | intervene",
  "reason_codes": [...]
}
```

---

## FR-7: Agent Invocation

### Description

Call LLM when failure detected.

### Inputs

* structured metrics
* failure reasons
* previous attempts
* allowed actions

### Outputs

* diagnosis
* recovery actions
* confidence

---

## FR-8: Recovery Execution

### Description

Apply agent-selected actions.

### Supported Actions

* reject bad frames
* filter frames by quality
* request new frames (simulated)
* apply preprocessing
* retry calibration
* relax nominal thresholds
* declare failure

---

## FR-9: Iterative Recovery Loop

### Description

Repeat calibration until:

* success
* retry limit reached
* unrecoverable

### Acceptance Criteria

* max retries configurable (e.g., 3)
* each iteration logged

---

## FR-10: Reporting

### Description

Generate final result.

### Outputs

* success/failure
* reprojection error
* deviation
* actions taken
* confidence

---

# 6. 🧪 Experiment Design

---

## 6.1 Scenarios

You must implement these **6 scenarios**:

---

### S0: Nominal

* good lighting
* proper pose
* full visibility

Purpose: baseline

---

### S1: Overexposure

![Image](https://images.openai.com/static-rsc-4/0hbZrGmVlaVFdcZUqf2X0uTkB1JBkelyRAxbfsK6iDKV8LTjiYH5dswUWOIb4B491VDB6z634UpgSPOoP0_yKZG2mVg3BBmDq1u6wuRzTd8t2wZltFAr0k44XVCkT6Fgts2FVIS0caVghK3zFq7wDbo8hZlTRSET6PxoTm07Gxf7HExO80MHkWPg0vLhAbcZ?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/iHjTyqkDp8575LRABD3_AOtZDDVSEL6Eh6IzJVt0rUFLCRdR1zJZ5b8bZmliyNS9dDetE0NVmMxdl2jCutZ9dqoDNKNPY-GSsn_r26yBGIj6i3tnQi-0lmOX4snJu7afPA0cucRSuR0LiPJP7pWlTW5vReyorE9Ap1xJKIzVkPkb43i5Sdk5bgCa4pPvE4dq?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/fH9ekjTmgVLskOhZyvYZjRIvuyf1qPyBuYokQtlKnlfLJnsfzj5x5HcSY6d9NIs4YRebe0swvA49f60qPErlJmJqBnRNUU4fgUWhCaQ7ULjwlc7WRtbdjkkOx7FZ47r__S8Qw_VmiDh1_nVp8mivtxFt6voS8hZF0yzhU_tZ1iB1rcIFCq7AwfvJVc4aQN4A?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/LHx154S_7vPgUJPOa17AOmGqfDOadWLMlp7qpb-RF_a6lgzEe0YRAn26PSTecIgUNMSSSyzBKAztyD_jW112LZXQci3vJyHG2s4yMZAEj3AL8IZziKaksVx7s8PVRb4bnSnKFJK770y4RR9mpxoQqviFjyId_MmTxS7c3m6evZc-Ryygoa7pLpkZb9THcr0d?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/VuIPJKj76F2VZLgJx-I38jeb2nFokt8NM5yt-UxVeYsX1ZG2yzNVL2i5dqhCs1Vvw8YKWlI-UIfZ2P_zz7wHylVwb2uphBpIadVc988AuxQMreJd98fOKSzji5i_encdE-_DKX_3NwOaA4MRF-s_eKqXr2WYsyzAVVTsqp_PlImGGze505iIo4NQd2rZLMEd?purpose=fullsize)

* strong lamp
* saturated regions

---

### S2: Low Light

![Image](https://images.openai.com/static-rsc-4/-9ezwLCIiSNEAc_7iK8ayoVmq_bfhe_P0O-4FZ5AsjEIUDPeS67yi0IhQ6hOZiFnNeQjyHPVyzajt34RhvddBLOXb0mmmjlHg0WPHN_L3aWSCriHwVdKpHOzQsUPaNwq4FiGnWC6DxJwp26fevfTYOxSW4cqwNbJJ_Ss3pdlYSlMPoR0NrOjGgU27DSAMHtL?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/bmlNVHea1hO0rmDPtoAI4yLUw7aPsnVFWk0a93pQw4wO_pPpVaeIMUWHkEXBiZB1Hp7Fd40H-2P9uY9_OCt5wY84UbDzDm9lqMVlv6VYtD07qYb24g-pUANkBMvafs7Dj8pooGQkuiJ5GMf6FuvLiobQUtbmawpZ5-nmev3rmJQ-xS5Zd5nYGbGM-YijlocR?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/6ck0H02H3ANxzqtq4qzzFSgBbN-E6FlsXMMAg3mb2N75orSwMcb5EWKNp9MroAFGXJA01ZNEkp4y8LHQHJiIQuuHvBjqrgnBa0AfC16oNCArDMkjbUHKgDyKEzfem6diujUSloX09GehVZcb7nzu1kKZsVZw1mde45pxXV_rsGCJMg4ucJ1Ssg-WSAM6BENr?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/DiIceHt4xmgvnPHAVZpdhL_VYy4yawSLrVAsV2gJPdqcWcvJbQPSi4sDt-S5i34db3jLSh0AKmYptnxv13Y6leB6bmiIPWnqxNgZxsiyhNvQTA0XjBeOeo7lnQW9L4F6ioSxzMp74ymRIHIMuAVNHMZBclhQG4hzXr9KzSih22mMoVn2m0Vl2X2VgVHocMrf?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/TDQZAW4EGeZT85S1CgNZjAop3cT6jA40tvU5YAs_AIHqCEcbPv3rGg744lQlo6tljABubEmss0Wp-ZH-5C6g3QXnJWi44MJr6L6aSKhtsnCKOMLBxk9ICbtk_L26Wl9v2MEMbPBvsFW5ut4mDNm5rsyRjcurxmSu83lFZR_cA5IcXWR8BLjobChF2M8M9apB?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/a8z3dZD8HrFbMGgZ4eLODPj6ub8Upl8-SxQmgjwaX0CVGDZqBlPUHPn8ZJMPpBWniz6d2ymaO-5YD2nJ5EK_lKSlrjCYH9F1SbmEsYsMv51kkFnA3DPSV4OeDmiS3B5tQ4HN9gCPM_avghbXM427A_WVgGT2gYWshg1zaep7IMdZPl__6OWByClrggt9Em8j?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/rP8K3fHnLoJP4wJ8_5YCe5VvQc_OHr4gGIIlCwYkbQ7hJ2E-e0OnmgFLmBzBt3sZrO_pcZgymZmAZ0-zqW4CulEDzs5c1bUCzTE1oLx4HTuc7NKSV6klA7lOVZ0d1TrLTFBqFMiylw1zx9-Eagla558E5T5a0vdqRU2ymEoOcVPDGikigSX-AoePskR6G55a?purpose=fullsize)

* dim environment
* noisy detection

---

### S3: Pose Deviation

* tilt camera or board
* simulate mount error

---

### S4: Height Variation

* change camera height
* use books or stands

---

### S5: Partial Visibility

![Image](https://images.openai.com/static-rsc-4/kz4E3u32KdFKgq2alIZKB8h1QIuPrujHZSY4h_6yxBkcNObBFVGFIn__k2u6mTr0RExakeFgLee172mEdENb20BwrgRchEgX05Pz--YOUO39oyj-39OLCQyxEUesLGNChaNrdnIlAfC4RCTHY-lEBhyCkAb4xl18KvZGL703DEuxzWb0VfGqgeEpiMXWE77v?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/-9ezwLCIiSNEAc_7iK8ayoVmq_bfhe_P0O-4FZ5AsjEIUDPeS67yi0IhQ6hOZiFnNeQjyHPVyzajt34RhvddBLOXb0mmmjlHg0WPHN_L3aWSCriHwVdKpHOzQsUPaNwq4FiGnWC6DxJwp26fevfTYOxSW4cqwNbJJ_Ss3pdlYSlMPoR0NrOjGgU27DSAMHtL?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/bmlNVHea1hO0rmDPtoAI4yLUw7aPsnVFWk0a93pQw4wO_pPpVaeIMUWHkEXBiZB1Hp7Fd40H-2P9uY9_OCt5wY84UbDzDm9lqMVlv6VYtD07qYb24g-pUANkBMvafs7Dj8pooGQkuiJ5GMf6FuvLiobQUtbmawpZ5-nmev3rmJQ-xS5Zd5nYGbGM-YijlocR?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/PNv8cPTsVVcuoc5vRxBdaJfuDbHqUwU4tKqaF-aNXR2ZX1JF980HxeOSIPh2NsVtqkMS3QpJHuFYehl17KyRJAnrDzOU-DQCufcCzcUMhOl5cPACooGozaNkwJwADu-GflW4k3tjGuVv1iF6QtduOwmlJhPmN9h-JXeIXvxgiwX1YLZNL-CMZ4LUUoUmTtri?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/iWXad0RsDYRVvQvShPFPR4qwXypN7M-4TSEMU25tH39oGHc0uKJRvlllmGJ3uapkYcu1TGotrljmDhihQd9MqQFvgEkgZlbeJPlgzsyfLlBViNJqB4wtva8oAoMzjgdORk-M8E8MlNT17nrsVS4H13dNzxNg9naFE7fyXJ46Dsp7gq67kDHm7e-OPNOGZZGm?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/Ug1Mm9ddh7j537KcEvIB9jlRkkbas8-r7HxUEGN778DsA1uf3sc8hB7Bz2grtxMADdQs1sy3Dzp9P0HLgx3B5yoHVcTPQ6q5dZNf3jqhcVNPakRHXFe4CvoWouQ0i97guiOzGqt-5yn_7vxZk1fyDV6aJRT_zn-mYzGX1bVrMwc-2M2MMHJ8SjnBhENOgWwb?purpose=fullsize)

* crop board
* occlude part

---

## 6.2 Dataset Size

* 6 scenarios
* 10 runs each
* 12–20 frames per run

👉 Total: ~60 runs (~1000 frames)

---

## 6.3 Frame Diversity (MANDATORY)

Each run must include:

* center frames
* edge frames
* tilted frames
* different distances

---

# 7. 📊 Evaluation Metrics

---

## Primary Metrics

### 1. Success Rate

% runs with valid calibration

---

### 2. Recovery Rate

% failed baseline runs recovered by agent

---

### 3. Reprojection Error

Accuracy of calibration

---

## Secondary Metrics

* retry count
* usable frame count
* failure classification accuracy

---

# 8. 🧠 Agent Design

---

## Input (Structured)

* reprojection error
* corner count
* brightness
* blur
* saturation
* coverage
* deviation

---

## Output

```json
{
  "diagnosis": "...",
  "actions": [...],
  "confidence": 0.8
}
```

---

## Constraints

* only allowed actions
* no direct math changes
* no hallucination of results

---

# 9. 🏗️ System Architecture

---

## Modules

```text
capture/
detection/
quality/
calibration/
deviation/
failure/
agent/
recovery/
orchestrator/
reporting/
```

---

## Core Flow

```text
frames → detection → quality → calibration → failure check
                                      ↓
                              agent intervention
                                      ↓
                               recovery actions
                                      ↓
                               recalibration
```

---

# 10. 🔁 Orchestrator Logic

---

### Pseudocode

```python
for run in dataset:
    frames = load(run)

    detections = detect(frames)
    quality = analyze(frames)

    result = calibrate(detections)

    if is_valid(result):
        return success

    for i in range(max_retries):
        state = build_agent_state(result, quality, detections)

        decision = agent.decide(state)

        if decision.unrecoverable:
            return fail

        frames = apply_actions(frames, decision)

        result = calibrate(detections)

        if is_valid(result):
            return success
```

---

# 11. ⚠️ Risks

---

## Risk 1: Weak baseline

Fix by:

* ensuring good nominal calibration

---

## Risk 2: Agent adds no value

Fix by:

* comparing with heuristic recovery

---

## Risk 3: Overfitting experiment

Fix by:

* using multiple failure scenarios

---

## Risk 4: Poor dataset diversity

Fix by:

* enforcing capture checklist

---

# 12. 📦 Deliverables

---

## Code

* calibration pipeline
* agent module
* recovery executor

---

## Data

* structured dataset
* logs

---

## Results

* comparison tables
* recovery plots

---

## Paper

* problem formulation
* method
* experiments
* results

---

# 13. 🚀 Success Criteria

You are done when you can show:

1. Baseline fails under real conditions
2. Agent recovers significant portion of failures
3. Accuracy is not degraded
4. Results are reproducible

---

# 🏁 Final Advice (Important)

Do NOT:

* overbuild
* overcomplicate
* add unnecessary features

Focus on:
👉 clean experiment
👉 clear improvement
👉 strong narrative

---