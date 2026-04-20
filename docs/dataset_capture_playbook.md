# Dataset Capture Playbook

This is the consolidated operational guide for dataset capture in this repo.

It consolidates:

- the older moving-target workflow
- the newer fixed-target EOL-style benchmark
- frame-type guidance for reference, primary, reserved, and eval usage
- scenario-specific capture instructions and command templates

The older files are intentionally kept for historical continuity and for
interpreting already-collected runs. Going forward, this file should be the
main operational reference.

## 1. What This Repo Now Supports

There are two valid capture styles in the repo.

### 1.1 Legacy Moving-Target Workflow

Use this when:

- you are extending or auditing the older dataset already collected
- you want geometric diversity by moving the board between shots
- you are comparing against the original exploratory setup

Key behavior:

- the camera is usually fixed within a run
- the board moves between frames
- `S3` changes camera pose
- `S4` changes camera height
- `S5` changes visibility by cropping or occluding the board

Metadata recommendation:

- `setup_type = legacy_moving_target`

### 1.2 Fixed-Target EOL-Style Benchmark

Use this for the main publishable benchmark.

Key behavior:

- the board stays in one marked station position
- the disturbance stays fixed within the run
- the camera and environment emulate an end-of-line calibration station more
  closely
- the pipeline estimates deviation from a known nominal setup

Metadata recommendation:

- `setup_type = benchmark_fixed_target`
- `dataset_split = eval` for final benchmark runs

## 2. Frame Types And What They Mean

Every run can contain up to three frame groups.

### 2.1 Reference Frames

Purpose:

- before-versus-disturbed visual comparison
- sanity checks
- paper figures
- documentation of the nominal view for that run

Recommended count:

- `3` frames per run for the fixed-target benchmark
- optional for the older moving-target workflow

Recommended location:

```text
dataset/.../run_01/reference_frames/
```

Important:

- reference frames are not the same as evaluation frames
- reference frames are support material and should remain clean and easy to
  interpret

### 2.2 Primary Frames

Purpose:

- initial calibration attempt
- the main evidence shown to baseline, heuristic, learned, and agent modes

Recommended count:

- `12` frames per run for the legacy moving-target workflow
- `6` frames per run for the fixed-target benchmark

### 2.3 Reserved Frames

Purpose:

- held back for recovery logic
- only used if a controller requests additional evidence or retries

Recommended count:

- `6` frames per run for the legacy moving-target workflow
- `3` frames per run for the fixed-target benchmark

Important:

- reserved frames should stay under the same disturbance condition as the run
- they may be slightly harder than the primary set, but should not all be
  impossible

### 2.4 Eval Split

`eval` is a dataset split, not a separate frame category.

Recommended split usage:

- `train`: only if you later build a learned model from labels
- `dev`: tuning thresholds, prompts, or controller logic
- `eval`: held-out benchmark numbers for the paper

For the fixed-target benchmark:

- reference frames can be captured alongside an `eval` run
- the run's primary and reserved frames are still the actual evaluation data

## 3. Common Capture Rules

These rules apply to both workflows.

### 3.1 Keep The Physical Setup Documented

Record:

- camera model
- image resolution
- board print size
- `squares_x`
- `squares_y`
- `square_length_mm`
- `marker_length_mm`
- ArUco dictionary

### 3.2 Keep The Board Flat And Clean

If the board bends, curls, or reflects strongly in an uncontrolled way, the
results become harder to interpret.

### 3.3 Do Not Mix Disturbances Unintentionally

Within a scenario run, change only the intended disturbance unless the run is
explicitly a mixed-condition benchmark.

### 3.4 Use Notes Aggressively

Notes are especially valuable for:

- approximate angle changes
- approximate height offsets
- lighting severity
- crop direction
- occluder type

## 4. Folder Structure

### 4.1 Legacy Moving-Target Example

```text
dataset/
  S3_pose_deviation/
    run_01/
      frame_001.png
      ...
      metadata.json
```

### 4.2 Fixed-Target Benchmark Example

```text
dataset/
  fixed_target_benchmark/
    eval/
      S3_pose_deviation_fixed/
        run_01/
          frame_001.png
          ...
          metadata.json
          reference_frames/
            frame_001.png
            frame_002.png
            frame_003.png
```

This structure is recommended, not mandatory. The critical part is that
metadata correctly records:

- `scenario`
- `run_id`
- `setup_type`
- `dataset_split`

## 5. Command Templates

### 5.1 Guided Run Capture

```powershell
.venv\Scripts\accal capture-guided `
  --camera-index 0 `
  --output-dir dataset\fixed_target_benchmark\eval\S0_nominal_fixed\run_01 `
  --scenario S0_nominal_fixed `
  --run-id run_01 `
  --primary-count 6 `
  --reserved-count 3 `
  --setup-type benchmark_fixed_target `
  --dataset-split eval `
  --notes "fixed target nominal eval run"
```

### 5.2 Reference Frame Capture

```powershell
.venv\Scripts\accal capture-reference `
  --camera-index 0 `
  --output-dir dataset\fixed_target_benchmark\eval\S0_nominal_fixed\run_01\reference_frames `
  --scenario S0_nominal_fixed `
  --run-id run_01 `
  --frame-count 3 `
  --setup-type benchmark_fixed_target `
  --dataset-split eval `
  --notes "clean reference frames before disturbed capture"
```

### 5.3 Legacy Moving-Target Example

```powershell
.venv\Scripts\accal capture-guided `
  --camera-index 0 `
  --output-dir dataset\S0_nominal\run_01 `
  --scenario S0_nominal `
  --run-id run_01 `
  --primary-count 12 `
  --reserved-count 6 `
  --setup-type legacy_moving_target `
  --dataset-split dev `
  --notes "legacy moving-target nominal run"
```

## 6. Legacy Moving-Target Workflow Summary

This remains useful for already-collected data and for earlier experiments.

### 6.1 Legacy Shot Pattern

For each run:

1. Capture `12` primary frames.
2. Capture `6` reserved frames.
3. Move the board between shots unless the scenario specifically disturbs the
   camera.

Suggested shot order:

1. `center_01`
2. `center_02`
3. `center_03`
4. `edge_left`
5. `edge_right`
6. `edge_top`
7. `edge_bottom`
8. `tilt_left`
9. `tilt_right`
10. `tilt_vertical`
11. `close`
12. `far`
13. `reserve_edge_01`
14. `reserve_edge_02`
15. `reserve_tilt_01`
16. `reserve_tilt_02`
17. `reserve_close`
18. `reserve_far`

### 6.2 Legacy Scenario Summary

`S0_nominal`

- camera fixed
- board moved between frames
- even lighting

`S1_overexposed`

- geometry similar to nominal
- stronger lighting or saturation

`S2_low_light`

- geometry similar to nominal
- darker, noisier frames

`S3_pose_deviation`

- camera pose changed and held constant within the run
- board still moved between frames

`S4_height_variation`

- camera height changed and held constant within the run
- board still moved between frames

`S5_partial_visibility`

- camera nominal
- board still moved between frames
- target visibility reduced by crop or occluder

### 6.3 Legacy Scenario Commands

Use these as scenario-level templates for the older moving-target workflow.
Update `run_01` and the note text per run.

`S0_nominal`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S0_nominal\run_01 --scenario S0_nominal --run-id run_01 --primary-count 12 --reserved-count 6 --setup-type legacy_moving_target --dataset-split dev --notes "legacy nominal moving-target run"
```

`S1_overexposed`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S1_overexposed\run_01 --scenario S1_overexposed --run-id run_01 --primary-count 12 --reserved-count 6 --setup-type legacy_moving_target --dataset-split dev --notes "legacy moving-target overexposed run"
```

`S2_low_light`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S2_low_light\run_01 --scenario S2_low_light --run-id run_01 --primary-count 12 --reserved-count 6 --setup-type legacy_moving_target --dataset-split dev --notes "legacy moving-target low-light run"
```

`S3_pose_deviation`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_01 --scenario S3_pose_deviation --run-id run_01 --primary-count 12 --reserved-count 6 --setup-type legacy_moving_target --dataset-split dev --notes "legacy moving-target pose-deviation run"
```

`S4_height_variation`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_01 --scenario S4_height_variation --run-id run_01 --primary-count 12 --reserved-count 6 --setup-type legacy_moving_target --dataset-split dev --notes "legacy moving-target height-variation run"
```

`S5_partial_visibility`

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_01 --scenario S5_partial_visibility --run-id run_01 --primary-count 12 --reserved-count 6 --setup-type legacy_moving_target --dataset-split dev --notes "legacy moving-target partial-visibility run"
```

## 7. Fixed-Target EOL-Style Benchmark

This is the main benchmark to prioritize for the paper.

### 7.1 Fixed-Target Rule Set

Within a run:

- keep the board in one marked station location
- do not sweep the board around the image
- keep the disturbance fixed
- keep framing as repeatable as practical

Between runs:

- change only the intended disturbance
- record the disturbance severity in notes

Recommended per-run frame set:

- `3` reference frames
- `6` primary frames
- `3` reserved frames

Recommended scenario names:

- `S0_nominal_fixed`
- `S1_overexposed_fixed`
- `S2_low_light_fixed`
- `S3_pose_deviation_fixed`
- `S4_height_variation_fixed`
- `S5_partial_visibility_fixed`

### 7.2 What "Reference" Means In Fixed-Target Capture

For the fixed-target benchmark, reference frames should show the same station
before the disturbance is applied when that comparison is meaningful.

Good examples:

- nominal board view before a pose-deviation run
- nominal board view before lowering the light level
- clean board view before adding an occluder

Reference frames should be:

- sharp
- fully visible when possible
- easy to compare against the disturbed run

### 7.3 What "Reserved" Means In Fixed-Target Capture

Reserved frames should stay under the same station condition as the primary
frames.

Good reserved-frame strategy:

- same geometry and disturbance
- slightly different timing
- slightly harsher but still interpretable views only when that makes sense

Examples:

- for `S1_overexposed_fixed`, reserved frames can be slightly more saturated
- for `S5_partial_visibility_fixed`, reserved frames can have slightly stronger
  occlusion
- for `S3_pose_deviation_fixed`, reserved frames should keep the same deviated
  pose and not introduce a new angle

## 8. Scenario-By-Scenario Fixed-Target Protocol

The following sections are the practical protocol to follow during capture.

### 8.1 S0 Nominal Fixed

Purpose:

- establish the station's nominal baseline
- provide clean acceptance examples
- provide the nominal visual reference for later disturbed scenarios

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
- keep the scene unchanged
- small natural timing variation is fine

Reserved frames:

- capture `3`
- same nominal condition
- do not intentionally degrade them

Recommended run count:

- `5` minimum
- `10` preferred

Example command:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S0_nominal_fixed\run_01 --scenario S0_nominal_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target nominal eval run"
```

### 8.2 S1 Overexposed Fixed

Purpose:

- simulate station lighting saturation or glare-like over-bright conditions
- keep geometry nominal while image quality degrades

What stays fixed:

- board location
- camera pose
- camera height

What changes:

- illumination level or strong directed brightness

Reference frames:

- capture `3` clean nominal-light frames before introducing stronger light

Primary frames:

- capture `6`
- keep brightness disturbance consistent for the whole run
- ensure some marker structure remains visible

Reserved frames:

- capture `3`
- may be slightly brighter than the primary set
- avoid making all three completely washed out

Recommended severity buckets:

- mild
- moderate
- strong but still partially readable

Run planning suggestion:

- `run_01` to `run_03`: mild
- `run_04` to `run_07`: moderate
- `run_08` to `run_10`: strong

Example note styles:

- `fixed target mild overexposure with board still readable`
- `fixed target moderate overexposure from right-side lamp`
- `fixed target strong overexposure with partial marker saturation`

### 8.3 S2 Low Light Fixed

Purpose:

- simulate dark station conditions or weak illumination
- keep geometry nominal while the image becomes dimmer and noisier

What stays fixed:

- board location
- camera pose
- camera height

What changes:

- illumination is reduced

Reference frames:

- capture `3` clean nominal-light frames before dimming

Primary frames:

- capture `6`
- keep the dim condition consistent
- avoid zero-signal darkness

Reserved frames:

- capture `3`
- may be slightly darker than the primary set
- still aim for partial detectability in at least some frames

Recommended severity buckets:

- mild dimming
- moderate dimming
- strong but still partly usable dimming

Run planning suggestion:

- `run_01` to `run_03`: mild
- `run_04` to `run_07`: moderate
- `run_08` to `run_10`: strong

Example note styles:

- `fixed target mild low-light run with acceptable marker visibility`
- `fixed target moderate low-light run with increased noise`
- `fixed target strong low-light run with partial marker loss`

### 8.4 S3 Pose Deviation Fixed

Purpose:

- emulate camera mounting angle error against a stationary floor target

What stays fixed:

- board location
- lighting
- camera height as much as practical

What changes:

- camera pitch, yaw, or roll

Reference frames:

- capture `3` at nominal pose before applying the deviation

Primary frames:

- capture `6`
- keep the deviated pose fixed for the full run

Reserved frames:

- capture `3`
- same deviated pose
- no new disturbance type introduced

Recommended 10-run matrix:

| Run ID | Disturbance | Target Amount | Practical Hint |
| --- | --- | --- | --- |
| run_01 | pitch down | `3-4 deg` | raise rear of camera slightly |
| run_02 | pitch down | `6-7 deg` | raise rear more than `run_01` |
| run_03 | pitch up | `3-4 deg` | raise front slightly |
| run_04 | pitch up | `6-7 deg` | raise front more than `run_03` |
| run_05 | yaw left | `3-4 deg` | rotate slightly left |
| run_06 | yaw left | `6-7 deg` | rotate further left |
| run_07 | yaw right | `3-4 deg` | rotate slightly right |
| run_08 | yaw right | `6-7 deg` | rotate further right |
| run_09 | roll clockwise | `4-5 deg` | tilt camera clockwise |
| run_10 | roll counterclockwise | `4-5 deg` | tilt camera counterclockwise |

Important note:

- relative consistency matters more than exact angle measurement

Example command:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S3_pose_deviation_fixed\run_01 --scenario S3_pose_deviation_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "camera pitched downward about 4 degrees from nominal against fixed target"
```

### 8.5 S4 Height Variation Fixed

Purpose:

- emulate camera height or ride-height deviation against a stationary target

What stays fixed:

- board location
- lighting
- camera pitch, yaw, and roll as close to nominal as possible

What changes:

- camera height

Reference frames:

- capture `3` at nominal height before changing the mount height

Primary frames:

- capture `6`
- keep the new height fixed for the full run

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

- do not unintentionally add tilt while changing height

Example command:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S4_height_variation_fixed\run_01 --scenario S4_height_variation_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "camera raised about 15 mm above nominal against fixed target"
```

### 8.6 S5 Partial Visibility Fixed

Purpose:

- emulate a stationary target that is only partially visible because of crop,
  occlusion, or missing evidence

What stays fixed:

- board location
- camera pose
- camera height
- lighting

What changes:

- visible portion of the board

Reference frames:

- capture `3`
- strongly recommended for every run
- capture them with no occluder and with the board fully visible first

Primary frames:

- capture `6`
- use mild to medium occlusion so the run remains analyzable

Reserved frames:

- capture `3`
- may be slightly stronger than the primary set
- do not make every reserved frame impossible

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
| run_09 | side occluder | medium | cover vertical strip with matte card |
| run_10 | corner occluder | medium-strong | cover one corner region |

Recommended per-run order:

1. capture `3` clean reference frames with no occluder
2. apply the planned crop or occluder
3. capture `6` primary frames
4. capture `3` reserved frames

Important note:

- this scenario is most interpretable when the reference frames are present

Example command:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S5_partial_visibility_fixed\run_01 --scenario S5_partial_visibility_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target mild left-side crop for partial visibility"
```

### 8.7 Fixed-Target Scenario Commands

Use these as scenario-level templates for the main benchmark. Update `run_01`
and the note text per run. For disturbed scenarios, capture the `3` reference
frames immediately before the guided run when you want a nominal-versus-
disturbed comparison set.

`S0_nominal_fixed`

Reference frames:

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S0_nominal_fixed\run_01\reference_frames --scenario S0_nominal_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target nominal reference frames"
```

Run capture:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S0_nominal_fixed\run_01 --scenario S0_nominal_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target nominal eval run"
```

`S1_overexposed_fixed`

Reference frames:

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S1_overexposed_fixed\run_01\reference_frames --scenario S1_overexposed_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target overexposure run"
```

Run capture:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S1_overexposed_fixed\run_01 --scenario S1_overexposed_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target overexposed run"
```

`S2_low_light_fixed`

Reference frames:

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S2_low_light_fixed\run_01\reference_frames --scenario S2_low_light_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target low-light run"
```

Run capture:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S2_low_light_fixed\run_01 --scenario S2_low_light_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target low-light run"
```

`S3_pose_deviation_fixed`

Reference frames:

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S3_pose_deviation_fixed\run_01\reference_frames --scenario S3_pose_deviation_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target pose-deviation run"
```

Run capture:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S3_pose_deviation_fixed\run_01 --scenario S3_pose_deviation_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target pose-deviation run"
```

`S4_height_variation_fixed`

Reference frames:

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S4_height_variation_fixed\run_01\reference_frames --scenario S4_height_variation_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target height-variation run"
```

Run capture:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S4_height_variation_fixed\run_01 --scenario S4_height_variation_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target height-variation run"
```

`S5_partial_visibility_fixed`

Reference frames:

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S5_partial_visibility_fixed\run_01\reference_frames --scenario S5_partial_visibility_fixed --run-id run_01 --frame-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "reference frames before fixed-target partial-visibility run"
```

Run capture:

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\fixed_target_benchmark\eval\S5_partial_visibility_fixed\run_01 --scenario S5_partial_visibility_fixed --run-id run_01 --primary-count 6 --reserved-count 3 --setup-type benchmark_fixed_target --dataset-split eval --notes "fixed target partial-visibility run"
```

## 9. Efficient Capture Strategy

This is the best practical strategy if capture time is limited and you do not
want to discard older data.

### 9.1 Keep Older Data

Do not discard the older moving-target dataset.

Use it as:

- exploratory evidence
- ablation data
- development data
- historical context in the paper or appendix

### 9.2 Capture Fixed-Target Data Incrementally

Recommended order:

1. `S0_nominal_fixed`
2. `S3_pose_deviation_fixed`
3. `S4_height_variation_fixed`
4. `S5_partial_visibility_fixed`
5. `S1_overexposed_fixed`
6. `S2_low_light_fixed`

Why this order helps:

- it establishes the nominal station first
- it captures the most automotive-representative geometry disturbances early
- it gives you usable comparison data before spending time on all lighting runs

### 9.3 Reference Frames Without Doubling Work

To keep the workflow efficient:

1. mark the fixed board station on the desk
2. mark the nominal camera station
3. before each disturbed run, capture `3` quick reference frames
4. immediately apply the disturbance and capture the run

This adds only a small amount of extra time and gives much better paper figures
and stronger sanity checks.

## 10. Quick Quality Checklist

Before leaving a run, verify:

- the intended disturbance is actually visible
- the board and camera station did not drift unintentionally
- images are sharp enough to be interpretable
- `metadata.json` exists
- `setup_type` and `dataset_split` are correct
- reference frames exist when expected

## 11. Bottom Line

Use this playbook as the main capture reference.

For publishable benchmark data:

- prioritize the fixed-target EOL-style setup
- capture `3` reference + `6` primary + `3` reserved when practical
- label those runs `setup_type = benchmark_fixed_target`
- keep final benchmark runs in `dataset_split = eval`

For already-collected data:

- keep the older moving-target runs
- label and analyze them separately rather than throwing them away
