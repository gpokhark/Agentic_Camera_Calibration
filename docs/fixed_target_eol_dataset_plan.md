# Fixed-Target EOL-Style Dataset Plan

This file is the dedicated fixed-target benchmark reference.

For the consolidated operational guide that also includes the older
moving-target workflow, use
[dataset_capture_playbook.md](/D:/github/Agentic_Camera_Calibration/docs/dataset_capture_playbook.md).

## 1. Goal

This benchmark is designed to make the desk experiment more comparable to
automotive end-of-line calibration:

- the calibration target remains at one station location
- the nominal geometry is known in advance
- the camera or environment changes relative to that nominal setup
- the pipeline estimates deviation from nominal
- the decision layer must choose accept, retry, recover, or fail

The fixed-target benchmark is the main dataset to prioritize for paper-quality
results.

## 2. Core Protocol

Within each fixed-target run:

- do not move the board between shots
- keep the board in one marked station location
- keep the disturbance fixed for the whole run
- keep framing and timing as repeatable as practical

Between runs:

- change only the intended disturbance variable
- document the change clearly in the notes

## 3. Per-Run Frame Structure

Every fixed-target run should aim to collect:

- `3` reference frames
- `6` primary frames
- `3` reserved frames

### 3.1 Reference Frames

Reference frames are for:

- nominal-versus-disturbed visual comparison
- paper figures
- manual sanity checks
- documenting the station view before the disturbance is applied

Recommended location:

```text
dataset/.../run_01/reference_frames/
```

Reference frames should be:

- sharp
- clean
- easy to interpret
- captured before the disturbed run when that comparison is meaningful

### 3.2 Primary Frames

Primary frames are the main frames used for the initial calibration attempt.

For fixed-target runs:

- the board remains fixed
- the disturbance remains fixed
- repeated frames represent station-like repeated observations

### 3.3 Reserved Frames

Reserved frames are held back for recovery logic.

For fixed-target runs:

- they should stay under the same disturbance condition
- they may be slightly harder than the primary set
- they should not all be impossible

## 4. Setup Labels And Dataset Splits

Every fixed-target run should record:

- `setup_type = benchmark_fixed_target`
- `dataset_split = eval` for final benchmark runs

Recommended split usage:

- `dev`: warm-up fixed-target collection for checking logic
- `eval`: held-out benchmark runs used for the paper
- `train`: only if you later create a learned model from labels

Important:

- `eval` is a dataset split, not a separate frame type
- reference frames can still exist inside an `eval` run
- the primary and reserved frames are the actual evaluation evidence

## 5. Metadata Expectations

Each run should record:

- scenario name
- run id
- disturbance description
- disturbance severity bucket such as `mild`, `moderate`, or `strong`
- camera pose or height description where relevant
- whether reference frames were captured
- approximate notes for light level, crop direction, or occluder type

Recommended note styles:

- `fixed target nominal run`
- `camera pitched downward about 4 degrees from nominal against fixed target`
- `camera raised about 25 mm above nominal against fixed target`
- `matte card occluding upper-right board corner against fixed target`

## 6. Scenario Set

Recommended core fixed-target scenarios:

- `S0_nominal_fixed`
- `S1_overexposed_fixed`
- `S2_low_light_fixed`
- `S3_pose_deviation_fixed`
- `S4_height_variation_fixed`
- `S5_partial_visibility_fixed`

Recommended counts:

- `5` runs minimum per scenario
- `10` runs preferred per scenario

Optional mixed scenarios for later:

- `M1_fixed_overexposed_pose`
- `M2_fixed_lowlight_partial`
- `M3_fixed_glare_height`

## 7. Detailed Capture Guidance By Scenario

### 7.1 S0 Nominal Fixed

Goal:

- establish the clean station baseline
- provide clean acceptance examples
- provide the nominal visual reference for later disturbed runs

What stays fixed:

- board location
- camera pose
- camera height
- lighting

Reference frames:

- capture `3`
- board fully visible
- nominal lighting
- no disturbance

Primary frames:

- capture `6`
- keep the station unchanged
- do not intentionally degrade image quality

Reserved frames:

- capture `3`
- same nominal condition
- keep them clean and representative

Best use:

- baseline acceptance measurements
- paper figures for nominal reference
- sanity-check anchor for disturbed scenarios

### 7.2 S1 Overexposed Fixed

Goal:

- preserve nominal geometry while disturbing lighting only

What stays fixed:

- board location
- camera pose
- camera height

What changes:

- illumination level or directed brightness

Reference frames:

- capture `3` clean nominal-light views before applying the brighter condition

Primary frames:

- capture `6`
- keep overexposure consistent across the run
- ensure at least some marker structure remains visible

Reserved frames:

- capture `3`
- may be slightly harsher than the primary set
- avoid making all three fully washed out

Suggested severity buckets:

- mild
- moderate
- strong but still partly readable

Suggested run grouping:

- `run_01` to `run_03`: mild
- `run_04` to `run_07`: moderate
- `run_08` to `run_10`: strong

### 7.3 S2 Low Light Fixed

Goal:

- preserve nominal geometry while reducing illumination

What stays fixed:

- board location
- camera pose
- camera height

What changes:

- the scene becomes darker

Reference frames:

- capture `3` clean nominal-light views before dimming the scene

Primary frames:

- capture `6`
- keep the dim condition stable across the run
- avoid zero-signal darkness

Reserved frames:

- capture `3`
- may be slightly darker than the primary set
- still keep partial detectability in at least some frames

Suggested severity buckets:

- mild dimming
- moderate dimming
- strong but still partly usable dimming

Suggested run grouping:

- `run_01` to `run_03`: mild
- `run_04` to `run_07`: moderate
- `run_08` to `run_10`: strong

### 7.4 S3 Pose Deviation Fixed

Goal:

- emulate camera mounting angle error against a stationary target

What stays fixed:

- board location
- lighting
- camera height as much as practical

What changes:

- camera pitch, yaw, or roll

Reference frames:

- capture `3` at nominal pose before applying the disturbance

Primary frames:

- capture `6`
- keep the disturbed pose fixed for the full run

Reserved frames:

- capture `3`
- keep the exact same pose disturbance

Recommended 10-run matrix:

| Run ID | Disturbance | Target Amount | Practical Hint |
| --- | --- | --- | --- |
| run_01 | pitch down | `3-4 deg` | raise rear of camera slightly |
| run_02 | pitch down | `6-7 deg` | raise rear more than `run_01` |
| run_03 | pitch up | `3-4 deg` | raise front slightly |
| run_04 | pitch up | `6-7 deg` | raise front more than `run_03` |
| run_05 | yaw left | `3-4 deg` | rotate camera slightly left |
| run_06 | yaw left | `6-7 deg` | rotate further left |
| run_07 | yaw right | `3-4 deg` | rotate camera slightly right |
| run_08 | yaw right | `6-7 deg` | rotate further right |
| run_09 | roll clockwise | `4-5 deg` | tilt camera clockwise |
| run_10 | roll counterclockwise | `4-5 deg` | tilt camera counterclockwise |

Important note:

- relative consistency matters more than exact angle measurement

### 7.5 S4 Height Variation Fixed

Goal:

- emulate camera height or ride-height shift against a stationary target

What stays fixed:

- board location
- lighting
- camera pitch, yaw, and roll as close to nominal as possible

What changes:

- camera height

Reference frames:

- capture `3` at nominal height before applying the new height

Primary frames:

- capture `6`
- keep the disturbed height fixed for the full run

Reserved frames:

- capture `3`
- same disturbed height

Recommended 10-run matrix:

| Run ID | Disturbance | Target Amount | Practical Hint |
| --- | --- | --- | --- |
| run_01 | raised | `+10-15 mm` | add one thin spacer |
| run_02 | raised | `+20-25 mm` | use a thicker spacer |
| run_03 | raised | `+30-35 mm` | add a stable block |
| run_04 | raised | `+40-50 mm` | taller rigid stack |
| run_05 | raised | `+55-60 mm` | highest practical stable setup |
| run_06 | lowered | `-10-15 mm` | remove one thin spacer |
| run_07 | lowered | `-20-25 mm` | lower the support further |
| run_08 | lowered | `-30-35 mm` | clearly lower mounting position |
| run_09 | lowered | `-40-50 mm` | lower further while keeping level |
| run_10 | lowered | `-55-60 mm` | lowest practical stable setup |

Important note:

- avoid unintentionally adding tilt while changing height

### 7.6 S5 Partial Visibility Fixed

Goal:

- emulate missing target evidence while the target remains stationary

What stays fixed:

- board location
- camera pose
- camera height
- lighting

What changes:

- visible portion of the board through crop or occlusion

Reference frames:

- capture `3`
- strongly recommended for every run
- capture them with no occluder first

Primary frames:

- capture `6`
- use mild to medium occlusion so the run remains analyzable

Reserved frames:

- capture `3`
- may be slightly stronger than the primary set
- avoid making every reserved frame impossible

Recommended 10-run matrix:

| Run ID | Disturbance | Severity | Practical Hint |
| --- | --- | --- | --- |
| run_01 | left crop | mild | left edge just outside image |
| run_02 | left crop | medium | move further left |
| run_03 | right crop | mild | right edge just outside image |
| run_04 | right crop | medium | move further right |
| run_05 | top crop | mild | top edge partly outside image |
| run_06 | top crop | medium | move higher |
| run_07 | bottom crop | mild | bottom edge partly outside image |
| run_08 | bottom crop | medium | move lower |
| run_09 | side occluder | medium | cover one vertical strip with matte card |
| run_10 | corner occluder | medium-strong | cover one corner region |

Recommended per-run sequence:

1. capture `3` clean reference frames
2. apply the crop or occluder
3. capture `6` primary frames
4. capture `3` reserved frames

## 8. Eval Strategy

Use the fixed-target benchmark primarily as:

- `dataset_split = eval`

Why:

- this benchmark should remain held out from development tuning
- this is the benchmark most likely to be reported in the paper

If you want a small warm-up set first, you can capture:

- `dataset_split = dev`

but keep the final reported numbers on held-out `eval` runs.

## 9. Recommended Capture Order

Capture in this order:

1. `S0_nominal_fixed`
2. `S3_pose_deviation_fixed`
3. `S4_height_variation_fixed`
4. `S5_partial_visibility_fixed`
5. `S1_overexposed_fixed`
6. `S2_low_light_fixed`
7. optional mixed scenarios

This order is efficient because it establishes the nominal station first and
captures the most automotive-representative geometry disturbances before
spending extra time on lighting sweeps.

## 10. Command Templates

### 10.1 Fixed-Target Reference Frames

```powershell
.venv\Scripts\accal capture-reference `
  --camera-index 0 `
  --output-dir dataset\fixed_target_benchmark\eval\S3_pose_deviation_fixed\run_01\reference_frames `
  --scenario S3_pose_deviation_fixed `
  --run-id run_01 `
  --frame-count 3 `
  --setup-type benchmark_fixed_target `
  --dataset-split eval `
  --notes "clean fixed reference frames before pose-deviation run"
```

### 10.2 Fixed-Target Eval Run

```powershell
.venv\Scripts\accal capture-guided `
  --camera-index 0 `
  --output-dir dataset\fixed_target_benchmark\eval\S3_pose_deviation_fixed\run_01 `
  --scenario S3_pose_deviation_fixed `
  --run-id run_01 `
  --primary-count 6 `
  --reserved-count 3 `
  --setup-type benchmark_fixed_target `
  --dataset-split eval `
  --notes "camera pitched downward about 4 degrees from nominal against fixed target"
```

### 10.3 Scenario Commands

Use these as scenario-level templates. Update `run_01` and the note text per
run.

`S0_nominal_fixed`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S0_nominal_fixed\run_01 --scenario S0_nominal_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target nominal eval run"
```

`S1_overexposed_fixed`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S1_overexposed_fixed\run_01 --scenario S1_overexposed_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target overexposed run"
```

`S2_low_light_fixed`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S2_low_light_fixed\run_01 --scenario S2_low_light_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target low-light run"
```

`S3_pose_deviation_fixed`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S3_pose_deviation_fixed\run_01 --scenario S3_pose_deviation_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target pose-deviation run"
```

`S4_height_variation_fixed`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S4_height_variation_fixed\run_01 --scenario S4_height_variation_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target height-variation run"
```

`S5_partial_visibility_fixed`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S5_partial_visibility_fixed\run_01 --scenario S5_partial_visibility_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target partial-visibility run"
```

### 10.4 Reference Commands For Disturbed Fixed-Target Scenarios

Use the same reference-frame pattern for disturbed scenarios when you want
clean nominal comparison images.

`S1_overexposed_fixed`

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S1_overexposed_fixed\run_01\reference_frames --scenario S1_overexposed_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target overexposure run"
```

`S2_low_light_fixed`

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S2_low_light_fixed\run_01\reference_frames --scenario S2_low_light_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target low-light run"
```

`S3_pose_deviation_fixed`

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S3_pose_deviation_fixed\run_01\reference_frames --scenario S3_pose_deviation_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target pose-deviation run"
```

`S4_height_variation_fixed`

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S4_height_variation_fixed\run_01\reference_frames --scenario S4_height_variation_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target height-variation run"
```

`S5_partial_visibility_fixed`

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S5_partial_visibility_fixed\run_01\reference_frames --scenario S5_partial_visibility_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target partial-visibility run"
```

## 11. Relationship To Older Docs

The older moving-target capture docs are still intentionally kept in the repo.

Use them when you need:

- historical context
- interpretation of already-collected runs
- continuity with the earlier exploratory workflow

For the main benchmark going forward:

- use this file for fixed-target-only planning
- use [dataset_capture_playbook.md](/D:/github/Agentic_Camera_Calibration/docs/dataset_capture_playbook.md) for the consolidated operational guide

## 12. Bottom Line

For the publishable benchmark:

- keep the target fixed
- capture `3` reference + `6` primary + `3` reserved when practical
- label runs as `benchmark_fixed_target`
- keep final paper runs in `dataset_split = eval`

That is the cleanest EOL-style protocol currently defined in the repo.
