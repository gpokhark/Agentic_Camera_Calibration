# Image Capture Guide

This guide explains exactly how to collect the images needed for the
single-camera ChArUco calibration experiments in this repository.

It translates the high-level dataset requirements from
`docs/architecture.md` into a practical capture workflow you can follow at
your desk.

## Goal

Capture a controlled dataset that lets us compare:

- baseline calibration
- heuristic recovery
- agent-driven recovery

The dataset must be:

- repeatable
- diverse enough for calibration
- organized by scenario and run
- fair across all three modes

## Minimum Dataset Size

Capture the following minimum dataset:

- `6` scenarios
- `10` runs per scenario
- `12` primary frames per run
- `4` to `8` reserved recovery frames per run

That gives:

- `60` total runs
- `720` primary frames minimum
- `240` to `480` reserved frames
- `960` to `1200` total frames overall

If time is tight, do not reduce scenario count first. Keep all `6` scenarios
and reduce only the reserved frames from `8` down to `4`.

## Scenario List

Capture these exact scenarios:

1. `S0_nominal`
2. `S1_overexposed`
3. `S2_low_light`
4. `S3_pose_deviation`
5. `S4_height_variation`
6. `S5_partial_visibility`

## Hardware Setup

Use the same core hardware throughout the dataset:

- `1` USB camera
- `1` printed ChArUco board on rigid backing
- tripod, clamp, or other fixed mount for the camera
- desk or table with enough room to move the board
- adjustable light source
- books, shims, or spacers for pose and height variation

## Board Setup

Before capturing anything:

1. Print the ChArUco board at high quality.
2. Mount it on stiff backing so it does not bend.
3. Measure and record:
   - `squares_x`
   - `squares_y`
   - `square_length_mm`
   - `marker_length_mm`
   - ArUco dictionary
4. Keep the board clean and flat for the entire dataset.

If the board curls or warps, calibration quality drops and the results become
harder to interpret.

## Camera Setup

Use one camera setup as your nominal reference:

- fixed mounting position
- fixed nominal height
- fixed nominal angle
- fixed nominal distance to the board

Recommended camera settings:

- use the same resolution for all runs
- prefer manual focus if your camera supports it
- prefer fixed white balance if available
- prefer fixed gain and exposure for `S0`
- change only the variables needed for the disturbance scenario

If your camera software allows it, disable autofocus and autoexposure during
nominal capture. For disturbed scenarios, only change the parameter that is
part of the scenario. That keeps the dataset easier to analyze later.

## Folder Structure

Store the dataset like this:

```text
dataset/
  S0_nominal/
    run_01/
      frame_001.png
      frame_002.png
      ...
      metadata.json
  S1_overexposed/
    run_01/
  S2_low_light/
  S3_pose_deviation/
  S4_height_variation/
  S5_partial_visibility/
```

## What A Run Means

A run is one calibration attempt under one scenario condition.

Example:

- `dataset/S1_overexposed/run_03/`

That directory should contain all images from one overexposed calibration
attempt, not a mixture of different conditions.

## How Many Images Per Run

Each run should contain:

- `12` primary frames
- `4` to `8` reserved frames

The first `12` are the initial calibration attempt.
The reserved frames are held back so recovery logic can request additional
views later.

Recommended default:

- `12` primary frames
- `6` reserved frames
- `18` total frames per run

## How To Compose The 12 Primary Frames

Do not take 12 nearly identical images.

The board must appear in different positions and scales across the image so
OpenCV gets good geometric coverage.

Use this pattern for the `12` primary frames:

1. `3` center-focused frames
2. `4` edge-coverage frames
3. `3` tilted board frames
4. `2` distance or scale variation frames

### 1. Center-Focused Frames

Capture `3` frames where:

- the board is fully visible
- the board is near the center
- the camera-board geometry is close to nominal

Purpose:

- establish stable baseline detections
- ensure at least a few easy frames exist in every run

### 2. Edge-Coverage Frames

Capture `4` frames where the board is placed:

- near left side
- near right side
- near top
- near bottom

Keep the full board visible if possible.

Purpose:

- improve calibration coverage across the image plane
- reduce the risk of a center-only dataset

### 3. Tilted Board Frames

Capture `3` frames where the board is still visible but rotated slightly:

- one mild left tilt
- one mild right tilt
- one upward or downward tilt

Purpose:

- add perspective diversity
- make the calibration set stronger

### 4. Distance / Scale Variation Frames

Capture `2` frames where the board appears:

- slightly closer
- slightly farther

Purpose:

- vary apparent board scale
- improve geometric diversity

## How To Capture The Reserved Frames

Capture `4` to `8` extra frames after the primary `12`.

These reserved frames should be more diverse than the first set.

Recommended reserved mix:

- `2` more edge-coverage frames
- `2` stronger tilt frames
- `1` closer frame
- `1` farther frame

If you collect `8` reserved frames, add:

- `1` partially cropped but still detectable frame
- `1` alternate lighting angle frame

If you collect only `4`, prioritize:

- edge coverage
- tilt
- one distance change

## How To Physically Capture Each Image

For each frame:

1. Move the board or camera to the intended position.
2. Pause briefly to avoid motion blur.
3. Make sure the board is visible and not blocked by your hand.
4. Check that the board is reasonably sharp.
5. Capture the image.
6. Move to the next planned pose.

Good practice:

- keep the camera fixed for most runs and move the board
- for pose or height scenarios, move the camera only when that is the
  intended disturbance
- avoid touching the camera during nominal runs

## Scenario-Specific Capture Instructions

### `S0_nominal`

Purpose:

- establish baseline performance
- define nominal reference behavior

How to capture:

- use even lighting
- keep the board fully visible
- keep the camera at the reference height and angle
- collect the full 12-frame diversity pattern

Target count:

- `10` runs
- `16` to `20` frames per run

### `S1_overexposed`

Purpose:

- simulate bright reflections or saturated lighting

How to capture:

- add a strong lamp or reflective light source
- intentionally create bright highlights on the board
- do not overdo it to the point where every frame becomes completely useless
- keep geometry similar to nominal unless the shot plan requires variation

Capture tip:

- verify that some board regions are saturated, but marker structure is still
  partially visible in at least some frames

Target count:

- `10` runs
- `16` to `20` frames per run

### `S2_low_light`

Purpose:

- simulate underexposed or noisy capture

How to capture:

- dim the room
- reduce direct light on the board
- keep the board visible, but darker than nominal
- try to produce a mix of usable and difficult frames

Capture tip:

- avoid making all frames pitch black; the point is degraded evidence, not a
  completely impossible dataset

Target count:

- `10` runs
- `16` to `20` frames per run

### `S3_pose_deviation`

Purpose:

- simulate camera mount angle error

How to capture:

- change camera angle using a wedge or shim
- keep the changed pose consistent within a run
- use a few different deviation magnitudes across the 10 runs

Recommended deviations:

- mild: about `3` to `5` degrees
- medium: about `6` to `8` degrees
- stronger: about `9` to `12` degrees

Target count:

- `10` runs
- `16` to `20` frames per run

Detailed per-run plan:

- see `docs/s3_pose_deviation_plan.md`

### `S4_height_variation`

Purpose:

- simulate camera height shift

How to capture:

- raise or lower the camera using books or spacers
- keep the changed height consistent within a run
- vary the amount of height change across runs

Recommended height changes:

- mild: `10` to `20` mm
- medium: `20` to `40` mm
- stronger: `40` to `60` mm

Target count:

- `10` runs
- `16` to `20` frames per run

### `S5_partial_visibility`

Purpose:

- simulate incomplete target visibility or occlusion

How to capture:

- crop part of the board out of frame
- or partially occlude the board with a neutral object
- keep enough visible structure in some frames for partial detection
- include a few frames with stronger occlusion in the reserved set

Capture tip:

- do not hide the entire board; the point is partial evidence, not zero evidence

Target count:

- `10` runs
- `16` to `20` frames per run

## Run Planning Template

Use this pattern for every run:

1. Set the scenario condition.
2. Capture `12` primary frames in the planned sequence.
3. Capture `4` to `8` reserved frames.
4. Save `metadata.json`.
5. Quickly review the images before moving on.

Suggested shot list:

1. center_01
2. center_02
3. center_03
4. edge_left
5. edge_right
6. edge_top
7. edge_bottom
8. tilt_left
9. tilt_right
10. tilt_up_or_down
11. close
12. far
13. reserve_edge_01
14. reserve_edge_02
15. reserve_tilt_01
16. reserve_tilt_02
17. reserve_close
18. reserve_far

## Metadata To Save

Each run should include a `metadata.json` file like this:

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
  "notes": "camera pitched downward about 8 degrees from nominal",
  "reserved_frame_ids": [
    "frame_013.png",
    "frame_014.png",
    "frame_015.png",
    "frame_016.png",
    "frame_017.png",
    "frame_018.png"
  ],
  "frame_metadata": {
    "frame_004.png": {
      "tags": ["edge", "left"]
    },
    "frame_009.png": {
      "tags": ["tilt", "right"]
    },
    "frame_013.png": {
      "tags": ["diverse", "edge", "reserved"]
    }
  }
}
```

The `frame_metadata.tags` field is optional, but it helps the recovery
executor choose reserved frames more intelligently.

## Quick Quality Check Before Leaving A Run

Before moving on to the next run, quickly confirm:

- images are not all identical
- board is visible in most frames
- intended disturbance is actually present
- at least some frames are sharp enough to detect markers
- filenames are saved correctly
- `metadata.json` exists

If a whole run is unusable, repeat it immediately while the setup is still in
place.

## Common Capture Mistakes

Avoid these mistakes:

- taking nearly identical frames
- changing too many conditions at once
- mixing scenario types in one run
- letting your hand occlude the board unintentionally
- using a bent board
- capturing frames with motion blur because the camera or board is still moving
- forgetting reserved frames
- forgetting metadata

## Recommended Capture Order

To reduce setup time, collect runs in this order:

1. `S0_nominal`
2. `S1_overexposed`
3. `S2_low_light`
4. `S3_pose_deviation`
5. `S4_height_variation`
6. `S5_partial_visibility`

This order keeps the nominal reference first and then moves through the more
deliberate disturbances.

## Guided OpenCV Capture Script

This repository now includes a guided OpenCV capture command that opens a live
camera preview and walks you through the shot plan from this guide.

Use:

```powershell
.venv\Scripts\accal capture-guided `
  --camera-index 0 `
  --output-dir dataset/S0_nominal/run_01 `
  --scenario S0_nominal `
  --run-id run_01 `
  --primary-count 12 `
  --reserved-count 6
```

What it does:

- shows a live USB camera preview
- overlays the current shot name and tags
- shows live ChArUco and image-quality feedback before you save
- saves frames with `frame_001.png`, `frame_002.png`, and so on
- automatically marks reserved frames in `metadata.json`
- writes per-frame shot tags into `metadata.json`

Live preview feedback includes:

- detected marker count
- detected ChArUco corner count
- approximate coverage score
- brightness, blur, and glare estimates
- a simple status label: `USABLE`, `CAUTION`, or `POOR`

Keyboard controls:

- `Space`, `C`, or `Enter`: capture current frame
- `B` or `Backspace`: undo last captured frame
- `Q` or `Esc`: quit the session

Important:

- you still need to physically reposition the board or camera between shots
- the script does not move the board for you; it guides the order and saves the frames
- it writes `metadata.json` automatically using the configured board settings

## Simple Burst Capture Script

If you want a simpler non-guided burst capture, you can still use:

```powershell
.venv\Scripts\accal capture `
  --camera-index 0 `
  --output-dir dataset/S0_nominal/run_01 `
  --scenario S0_nominal `
  --run-id run_01 `
  --frame-count 18
```

This simpler mode captures sequentially without the on-screen shot prompts.

## Recommended Minimum You Should Actually Collect

If you want one clear target to follow, use this:

- `6` scenarios
- `10` runs per scenario
- `18` frames per run
  - `12` primary
  - `6` reserved

That gives:

- `60` runs
- `1080` total images

This is the best balance between project seriousness and practical workload.
