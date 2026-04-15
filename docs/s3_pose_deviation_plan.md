# S3 Pose Deviation Run Plan

This document gives a concrete 10-run capture plan for the
`S3_pose_deviation` scenario.

Use it as the reference when collecting the pose-deviation dataset so the runs
are varied, repeatable, and easy to describe later.

## Core Idea

For `S3_pose_deviation`, the disturbance is the **camera pose**, not the board.

That means:

- change the camera angle away from the nominal mounting pose
- keep that camera deviation fixed for the whole run
- still move the board between frames using the normal shot plan

So within one run:

- camera pose = fixed but deviated
- board position = moves between frames

## What To Keep Constant

For all `S3` runs, keep these as consistent as possible:

- same camera
- same board
- same board print size
- same room and basic lighting
- same camera height, unless height changes accidentally with the shim
- same `12` primary + `6` reserved frame structure

## What Changes In S3

Only the camera angle changes intentionally.

You can create this by:

- placing a wedge under one side of the camera mount
- shimming the tripod head slightly
- tilting the clamp or bracket a controlled amount

## Do Not Do This

Avoid these common mistakes:

- changing the camera angle from frame to frame inside one run
- keeping the board fixed in one place for all 18 shots
- mixing glare or low-light changes into the same run
- using such a strong tilt that the board becomes unusable in almost every frame

## Recommended 10-Run Matrix

This matrix gives good directional coverage without requiring precise lab
equipment.

### Run Plan

| Run ID | Main Deviation | Target Amount | Practical Setup Hint | Example Notes |
| ------ | -------------- | ------------- | -------------------- | ------------- |
| run_01 | Pitch down     | `3-4 deg`     | raise rear of camera slightly | camera pitched downward mildly |
| run_02 | Pitch down     | `6-7 deg`     | raise rear more than run_01 | camera pitched downward moderately |
| run_03 | Pitch up       | `3-4 deg`     | raise front of camera slightly | camera pitched upward mildly |
| run_04 | Pitch up       | `6-7 deg`     | raise front more than run_03 | camera pitched upward moderately |
| run_05 | Yaw left       | `3-4 deg`     | rotate camera slightly left | camera yawed left mildly |
| run_06 | Yaw left       | `6-7 deg`     | rotate further left | camera yawed left moderately |
| run_07 | Yaw right      | `3-4 deg`     | rotate camera slightly right | camera yawed right mildly |
| run_08 | Yaw right      | `6-7 deg`     | rotate further right | camera yawed right moderately |
| run_09 | Roll clockwise | `4-5 deg`     | tilt camera clockwise | camera rolled clockwise mildly |
| run_10 | Roll counterclockwise | `4-5 deg` | tilt camera counterclockwise | camera rolled counterclockwise mildly |

This is a strong first-pass dataset because it covers:

- pitch
- yaw
- roll
- mild and moderate deviations

## If You Cannot Measure Angles Exactly

That is completely fine.

You do **not** need exact precision like `6.3 degrees`.

Instead, aim for:

- visibly different from nominal
- consistent within the run
- clearly milder or stronger than the nearby run

What matters is:

- `run_02` should be more deviated than `run_01`
- `run_06` should be more deviated than `run_05`
- `run_08` should be more deviated than `run_07`

Relative consistency matters more than exact measurement.

## Practical Capture Procedure For Each Run

Follow this sequence:

1. Reset the board area and lighting to nominal.
2. Adjust the camera to the planned deviated pose for that run.
3. Check the camera is stable and does not wobble.
4. Leave the camera untouched for the whole run.
5. Move the board between frames according to the guided capture prompts.
6. Save all `18` frames.
7. Record the deviation in `metadata.json` notes.

## Board Movement Pattern During S3

Even though this is a pose-deviation scenario, the board should still move
between frames exactly like other scenarios.

Use the standard pattern:

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

The board movement gives geometric diversity.
The camera deviation is the disturbance.
You need both.

## Notes Template

Use notes like these when you capture:

- `camera pitched downward about 4 degrees from nominal`
- `camera pitched upward about 7 degrees from nominal`
- `camera yawed left about 6 degrees from nominal`
- `camera rolled clockwise about 5 degrees from nominal`

If you used a physical shim, you can also note:

- `rear shim: 1 folded card`
- `front shim: 2 folded cards`
- `left mount lifted with 5 mm spacer`

That kind of note is useful even if the angle is only approximate.

## Command Template

Use this command pattern for each run:

```powershell
.venv\Scripts\accal capture-guided `
  --camera-index 0 `
  --output-dir dataset\S3_pose_deviation\run_01 `
  --scenario S3_pose_deviation `
  --run-id run_01 `
  --primary-count 12 `
  --reserved-count 6 `
  --notes "camera pitched downward about 4 degrees from nominal"
```

Then update the path, run id, and note for each run.

## Suggested Commands For All 10 Runs

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_01 --scenario S3_pose_deviation --run-id run_01 --primary-count 12 --reserved-count 6 --notes "camera pitched downward about 4 degrees from nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_02 --scenario S3_pose_deviation --run-id run_02 --primary-count 12 --reserved-count 6 --notes "camera pitched downward about 7 degrees from nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_03 --scenario S3_pose_deviation --run-id run_03 --primary-count 12 --reserved-count 6 --notes "camera pitched upward about 4 degrees from nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_04 --scenario S3_pose_deviation --run-id run_04 --primary-count 12 --reserved-count 6 --notes "camera pitched upward about 7 degrees from nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_05 --scenario S3_pose_deviation --run-id run_05 --primary-count 12 --reserved-count 6 --notes "camera yawed left about 4 degrees from nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_06 --scenario S3_pose_deviation --run-id run_06 --primary-count 12 --reserved-count 6 --notes "camera yawed left about 7 degrees from nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_07 --scenario S3_pose_deviation --run-id run_07 --primary-count 12 --reserved-count 6 --notes "camera yawed right about 4 degrees from nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_08 --scenario S3_pose_deviation --run-id run_08 --primary-count 12 --reserved-count 6 --notes "camera yawed right about 7 degrees from nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_09 --scenario S3_pose_deviation --run-id run_09 --primary-count 12 --reserved-count 6 --notes "camera rolled clockwise about 5 degrees from nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_10 --scenario S3_pose_deviation --run-id run_10 --primary-count 12 --reserved-count 6 --notes "camera rolled counterclockwise about 5 degrees from nominal"
```

## If A Run Looks Too Hard

If almost every frame becomes unreadable:

- reduce the deviation a little
- keep the direction the same
- update the note accordingly

It is better to have a usable moderate run than a useless extreme run.

## Recommendation

For your first pass, follow the matrix exactly.

Do not improvise different combinations yet.
Get one clean 10-run `S3_pose_deviation` dataset first.
After that, if needed, you can add stronger or mixed pose runs later.
