## Title (working)

**Agentic Recovery for End-of-Line Camera Calibration under Real-World Variability**

---

# 1. Problem Motivation (Automotive EOL)

In vehicle manufacturing, surround-view/ADAS cameras are calibrated at end-of-line (EOL) using a known ground target. The pipeline (typically implemented in OpenCV) assumes:

* stable lighting
* sufficient target visibility
* nominal camera pose/height

In practice, these assumptions are violated:

* **assembly tolerances** → camera pitch/yaw drift
* **ride height variation** → vertical geometry shift
* **plant lighting** → overexposure / low light
* **glare / reflections** → corrupted target detection

**Current behavior:**

* calibration is a **hard pass/fail**
* failure of **one camera → whole system fails**
* many failures are **false rejects** (not true misalignment)

👉 This causes:

* rework
* manual intervention
* increased cycle time
* reduced throughput

---

# 2. Core Idea

Introduce a **decision layer** that sits on top of classical calibration:

> An LLM-based agent that interprets structured diagnostics from the calibration pipeline and selects recovery actions to reduce false failures.

Key constraint:

* The agent **does not perform calibration**
* It only:

  * diagnoses failure causes
  * selects actions from a fixed set
  * triggers controlled retries

---

# 3. Why This Research is Needed

## 3.1 Gap in Existing Systems

Current systems:

* optimize **geometry (calibration math)**
* improve **feature detection (markers, targets)**

But they **lack decision intelligence** when things go wrong.

👉 There is no mechanism to answer:

* *Is this a real misalignment or bad data?*
* *Should we retry, filter, or fail?*

---

## 3.2 Calibration is a System-Level Problem

Calibration failure is rarely caused by a single factor:

* glare + low coverage
* pose deviation + partial visibility
* low light + blur

These are **multi-factor interactions**, not isolated issues.

---

# 4. Why Heuristics Are Not Enough

Heuristics = fixed rules like:

* if brightness high → reduce exposure
* if corners low → request more frames

## 4.1 Rule Explosion Problem

As conditions combine, rules grow combinatorially:

| Factors | Possible combinations |
| ------- | --------------------- |
| 2       | manageable            |
| 3–4     | complex               |
| 5+      | impractical           |

👉 You cannot realistically encode all combinations.

---

## 4.2 Lack of Contextual Reasoning

Heuristics cannot answer:

* Is high reprojection error due to **bad geometry** or **bad image quality**?
* Should we **relax pose constraints** or **improve data first**?

They treat symptoms independently, not causally.

---

## 4.3 Brittle Behavior

Heuristics:

* work for known cases
* fail silently for unseen combinations

👉 Leads to:

* unnecessary failures
* inconsistent recovery

---

# 5. Proposed Approach

## 5.1 System Architecture

* **Perception layer**

  * ChArUco detection
  * image quality metrics

* **Calibration layer**

  * standard OpenCV calibration
  * deviation estimation

* **Failure detection**

  * identifies unreliable results

* **Decision layer (new contribution)**

  * heuristic controller OR LLM agent

* **Recovery actions**

  * frame filtering
  * preprocessing
  * additional view selection
  * parameter relaxation

---

## 5.2 Agent Behavior

Input:

* structured metrics (brightness, blur, coverage, reprojection error, deviation)

Output:

* diagnosis
* ranked recovery actions
* confidence
* termination decision

Key capability:
👉 **reasoning over multiple signals simultaneously**

---

# 6. Experimental Validation (Desk Setup)

Use:

* single USB camera
* ChArUco board

Simulate:

* overexposure
* low light
* pose deviation
* height variation
* partial visibility
* mixed conditions

Compare:

1. baseline (no recovery)
2. heuristic recovery
3. agent-based recovery

Metrics:

* recovery rate
* success rate
* reprojection error

---

# 7. Why This Approach is Better

## 7.1 Separates Concerns Cleanly

* geometry → classical methods
* decision-making → agent

👉 avoids replacing reliable math

---

## 7.2 Handles Multi-Factor Failures

Agent can:

* weigh competing signals
* prioritize actions
* avoid premature decisions

Heuristics cannot do this reliably.

---

## 7.3 Reduces False Rejects

Key benefit in EOL:

* identifies **recoverable failures**
* avoids unnecessary calibration aborts

---

## 7.4 Scales to Multi-Camera Systems

The same framework extends to:

* 4-camera surround view
* multi-sensor calibration

Agent can reason:

* per-camera issues
* global vs local failures

---

# 8. Extension to Automotive Systems

## Desk → Vehicle Mapping

| Desk Setup         | Vehicle Equivalent      |
| ------------------ | ----------------------- |
| pose deviation     | assembly tolerance      |
| height variation   | ride height variation   |
| glare on board     | floor target glare      |
| partial visibility | occluded target regions |

---

## Multi-Camera Extension

Agent input becomes:

* per-camera diagnostics
* cross-camera consistency

Agent decides:

* isolate failing camera
* retry selectively
* adjust global assumptions

---

# 9. Key Contribution

1. **Formalization of calibration failure as a decision problem**
2. **Structured state representation for calibration diagnostics**
3. **Comparison of heuristic vs agent-based recovery**
4. **Demonstration of improved robustness under real-world conditions**

---

# 10. Expected Outcome

* baseline fails frequently under disturbances
* heuristic recovers simple cases
* agent recovers **more complex multi-factor failures**

---

# 11. One-Line Summary (for abstract)

> We introduce an agentic recovery framework that augments classical camera calibration with decision-making capabilities, improving robustness under real-world failure conditions without modifying the underlying geometric estimation.

---

# 🏁 Final Reality Check

This idea is strong because:

* grounded in real automotive problem
* experimentally testable
* clear comparison
* measurable improvement

It will fail only if:

* agent does not outperform heuristics in mixed conditions
* experiments are weak or biased

