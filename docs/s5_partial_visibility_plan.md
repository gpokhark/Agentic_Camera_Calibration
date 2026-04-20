# S5 Partial Visibility Run Plan

This document gives a concrete 10-run capture plan for the
`S5_partial_visibility` scenario.

Use it as the reference when collecting the partial-visibility dataset so the
runs are varied, repeatable, and still usable for analysis.

## Core Idea

For `S5_partial_visibility`, the disturbance is **missing target evidence**.

That means:

- part of the board is intentionally outside the image
- or part of the board is intentionally covered by a neutral occluder
- enough of the board should still remain visible for at least partial
  detection in many frames

So within one run:

- camera pose and height = nominal
- lighting = nominal
- board movement = still follows the normal shot plan
- visibility = intentionally reduced

## What To Keep Constant

For all `S5` runs, keep these as consistent as possible:

- same camera
- same board
- same board print size
- same room and basic lighting
- same camera height and angle as the nominal setup
- same `12` primary + `6` reserved frame structure

## What Changes In S5

Only the **visible amount of the board** changes intentionally.

You can create this by:

- placing the board so one side is partly out of frame
- covering part of the board with a matte, non-reflective object
- keeping the occlusion pattern broadly consistent within a run

Good occluders:

- matte black card
- plain white card
- neutral cardboard
- a flat book with a non-glossy cover

Avoid reflective or textured objects that add glare or confusing patterns.

## Do Not Do This

Avoid these common mistakes:

- hiding the entire board
- changing lighting at the same time
- changing camera pose or camera height during the run
- using a shiny occluder that introduces glare instead of clean occlusion
- making every frame equally impossible to detect

The goal is **partial evidence**, not zero evidence.

## Recommended Visibility Levels

You do not need exact percentages, but aim roughly for these bands:

- mild partial visibility: about `70` to `85` percent of the board visible
- medium partial visibility: about `50` to `70` percent visible
- stronger partial visibility: about `35` to `50` percent visible

Try not to go below roughly one-third visible for most of the run, or the
dataset may become too weak to calibrate and less useful for comparison.

## Recommended 10-Run Matrix

This matrix gives good directional and occlusion-type coverage without needing
special fixtures.

### Run Plan

| Run ID | Main Disturbance | Target Amount | Practical Setup Hint | Example Notes |
| ------ | ---------------- | ------------- | -------------------- | ------------- |
| run_01 | Left crop        | mild          | keep left edge of board just outside image | board cropped mildly on left side |
| run_02 | Left crop        | medium        | move board further left so more is missing | board cropped moderately on left side |
| run_03 | Right crop       | mild          | keep right edge just outside image | board cropped mildly on right side |
| run_04 | Right crop       | medium        | move board further right | board cropped moderately on right side |
| run_05 | Top crop         | mild          | keep top edge partly outside image | board cropped mildly on top side |
| run_06 | Top crop         | medium        | move board higher so more is cut off | board cropped moderately on top side |
| run_07 | Bottom crop      | mild          | keep bottom edge partly outside image | board cropped mildly on bottom side |
| run_08 | Bottom crop      | medium        | move board lower so more is cut off | board cropped moderately on bottom side |
| run_09 | Side occluder    | medium        | cover one vertical strip with matte card | matte card occluding left-side markers |
| run_10 | Corner occluder  | medium-strong | cover one corner region with matte card | upper-right corner partially occluded |

This is a strong first-pass dataset because it covers:

- left and right loss
- top and bottom loss
- cropping-based partial visibility
- occluder-based partial visibility

## If You Cannot Estimate Visibility Exactly

That is completely fine.

You do **not** need exact measurements like `63 percent visible`.

Instead, aim for:

- clearly visible but incomplete
- consistent within the run
- milder or stronger than the nearby run

What matters is:

- `run_02` should be more cropped than `run_01`
- `run_04` should be more cropped than `run_03`
- occluder runs should clearly remove meaningful marker area

Relative consistency matters more than exact percentages.

## Practical Capture Procedure For Each Run

Follow this sequence:

1. Reset the camera and lighting to nominal.
2. Set the planned crop or occluder pattern for that run.
3. Check that a meaningful part of the board is still visible.
4. Capture the run while keeping the same general partial-visibility pattern.
5. Use the normal guided board movement prompts where possible.
6. Save all `18` frames.
7. Record the disturbance in `metadata.json` notes.

## How To Place The Target

For `S5`, you should still move the board between frames like the nominal run,
but maintain the intended missing-region effect.

That means:

- if the run is a left-crop run, keep the board positioned so the left side is
  usually outside the frame
- if the run is a top-crop run, keep the board high enough that the top stays
  partly missing
- if the run uses an occluder, keep that occluder covering the planned board
  region throughout the run

You do **not** need to match the exact physical board positions from `S0`.

What matters is:

- the board still moves enough to provide geometric diversity
- the same visibility disturbance remains present across the run
- enough markers remain visible in many frames for partial detection

## Primary And Reserved Frame Strategy

For the `12` primary frames:

- aim for mild to medium partial visibility
- keep the run analyzable
- make sure the board is still reasonably detectable in many frames

For the `6` reserved frames:

- you can make the occlusion a little stronger
- include a few harder examples
- avoid making all reserved frames completely unusable

This gives the recovery pipeline a realistic mix of usable and difficult data.

## Board Movement Pattern During S5

Use the standard pattern, but maintain the run's planned crop or occlusion:

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

If a specific prompt would completely remove the board from view, adjust it
slightly so the board remains partially visible rather than fully absent.

## Notes Template

Use notes like these when you capture:

- `board cropped mildly on left side for partial visibility`
- `board cropped moderately on top side`
- `matte card covering left vertical strip of board`
- `upper-right board corner partially occluded with matte card`

If helpful, also note:

- `roughly 70 percent of board visible`
- `roughly half the right side visible`
- `reserved frames captured with slightly stronger occlusion`

That kind of note is useful even if the visibility estimate is approximate.

## Command Template

Use this command pattern for each run:

```powershell
.venv\Scripts\accal capture-guided `
  --camera-index 0 `
  --output-dir dataset\S5_partial_visibility\run_01 `
  --scenario S5_partial_visibility `
  --run-id run_01 `
  --primary-count 12 `
  --reserved-count 6 `
  --notes "board cropped mildly on left side for partial visibility"
```

Then update the path, run id, and note for each run.

## Suggested Commands For All 10 Runs

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_01 --scenario S5_partial_visibility --run-id run_01 --primary-count 12 --reserved-count 6 --notes "board cropped mildly on left side for partial visibility"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_02 --scenario S5_partial_visibility --run-id run_02 --primary-count 12 --reserved-count 6 --notes "board cropped moderately on left side for partial visibility"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_03 --scenario S5_partial_visibility --run-id run_03 --primary-count 12 --reserved-count 6 --notes "board cropped mildly on right side for partial visibility"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_04 --scenario S5_partial_visibility --run-id run_04 --primary-count 12 --reserved-count 6 --notes "board cropped moderately on right side for partial visibility"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_05 --scenario S5_partial_visibility --run-id run_05 --primary-count 12 --reserved-count 6 --notes "board cropped mildly on top side for partial visibility"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_06 --scenario S5_partial_visibility --run-id run_06 --primary-count 12 --reserved-count 6 --notes "board cropped moderately on top side for partial visibility"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_07 --scenario S5_partial_visibility --run-id run_07 --primary-count 12 --reserved-count 6 --notes "board cropped mildly on bottom side for partial visibility"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_08 --scenario S5_partial_visibility --run-id run_08 --primary-count 12 --reserved-count 6 --notes "board cropped moderately on bottom side for partial visibility"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_09 --scenario S5_partial_visibility --run-id run_09 --primary-count 12 --reserved-count 6 --notes "matte card covering left vertical strip of board"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S5_partial_visibility\run_10 --scenario S5_partial_visibility --run-id run_10 --primary-count 12 --reserved-count 6 --notes "upper-right board corner partially occluded with matte card"
```

## If A Run Looks Too Hard

If almost every frame becomes unreadable:

- reduce the crop or occlusion slightly
- keep the same side or occlusion type
- update the note accordingly

It is better to have a usable moderate run than a useless extreme run.

## Recommendation

For your first pass, follow the matrix exactly.

Do not mix glare, low light, pose error, or height variation into `S5` yet.
Get one clean 10-run `S5_partial_visibility` dataset first.
After that, if needed, you can add mixed-condition runs later.
