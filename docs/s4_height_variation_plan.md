# S4 Height Variation Run Plan

This document gives a concrete 10-run capture plan for the
`S4_height_variation` scenario.

Use it as the reference when collecting the height-variation dataset so the
runs are varied, repeatable, and easy to describe later.

## Core Idea

For `S4_height_variation`, the disturbance is the **camera height**, not the
board pose.

That means:

- change the camera vertical position away from the nominal setup
- keep that camera height fixed for the whole run
- still move the board between frames using the normal shot plan

So within one run:

- camera height = fixed but offset from nominal
- board position = moves between frames

## What To Keep Constant

For all `S4` runs, keep these as consistent as possible:

- same camera
- same board
- same board print size
- same room and basic lighting
- same camera pitch, yaw, and roll as the nominal setup
- same `12` primary + `6` reserved frame structure

## What Changes In S4

Only the camera height changes intentionally.

You can create this by:

- placing the camera on books, acrylic blocks, or rigid spacers
- lowering the camera by removing spacers from the nominal setup
- adjusting a tripod center column up or down without changing the tilt

The main goal is to simulate a vertical mounting or ride-height shift while
keeping the viewing direction as nominal as possible.

## Do Not Do This

Avoid these common mistakes:

- changing the camera height from frame to frame inside one run
- tilting the camera while trying to raise or lower it
- keeping the board fixed in one place for all 18 shots
- mixing strong lighting changes into the same run
- making the height change so extreme that the board is barely usable

## Recommended 10-Run Matrix

This matrix gives good vertical coverage without requiring precision lab
fixtures.

### Run Plan

| Run ID | Main Deviation | Target Amount | Practical Setup Hint | Example Notes |
| ------ | -------------- | ------------- | -------------------- | ------------- |
| run_01 | Raised         | `+10-15 mm`   | add one thin spacer under the camera base | camera raised mildly above nominal |
| run_02 | Raised         | `+20-25 mm`   | stack a slightly thicker spacer | camera raised moderately above nominal |
| run_03 | Raised         | `+30-35 mm`   | add a stable block under the mount | camera raised clearly above nominal |
| run_04 | Raised         | `+40-50 mm`   | use a taller rigid stack, check stability | camera raised strongly above nominal |
| run_05 | Raised         | `+55-60 mm`   | tallest practical raised setup | camera raised near upper planned limit |
| run_06 | Lowered        | `-10-15 mm`   | remove one thin spacer from nominal | camera lowered mildly below nominal |
| run_07 | Lowered        | `-20-25 mm`   | lower tripod or remove more support | camera lowered moderately below nominal |
| run_08 | Lowered        | `-30-35 mm`   | use a clearly lower mounting position | camera lowered clearly below nominal |
| run_09 | Lowered        | `-40-50 mm`   | lower further while keeping the camera level | camera lowered strongly below nominal |
| run_10 | Lowered        | `-55-60 mm`   | lowest practical stable setup | camera lowered near lower planned limit |

This is a strong first-pass dataset because it covers:

- upward height changes
- downward height changes
- mild, moderate, and strong offsets
- a symmetric range around the nominal setup

## If You Cannot Measure Height Exactly

That is completely fine.

You do **not** need exact precision like `23 mm`.

Instead, aim for:

- clearly above or below nominal
- consistent within the run
- visibly different from the nearby run

What matters is:

- `run_03` should be more raised than `run_02`
- `run_08` should be more lowered than `run_07`
- the `raised` and `lowered` groups should both be represented clearly

Relative consistency matters more than exact measurement.

## Important Practical Note

If your physical setup makes it hard to create both raised and lowered runs,
you have two safe options:

1. Choose a nominal middle height first, then capture some runs above and some
below that reference.
2. If lowering is physically limited, still document the actual offset in the
notes and keep the direction labels honest.

For analysis in this repo, the height change should be large enough to produce a
clear effect. As a rule of thumb, try to make the offset at least
`10 mm` from nominal so it is more likely to show up in the later audit.

## Practical Capture Procedure For Each Run

Follow this sequence:

1. Reset the board area and lighting to nominal.
2. Adjust the camera to the planned height for that run.
3. Check the camera remains level and does not accidentally tilt.
4. Check the setup is stable and will not sag during the run.
5. Leave the camera untouched for the whole run.
6. Move the board between frames according to the guided capture prompts.
7. Save all `18` frames.
8. Record the height change in `metadata.json` notes.

## Board Movement Pattern During S4

Even though this is a height-variation scenario, the board should still move
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
The camera height is the disturbance.
You need both.

## How To Place The Target

Place the board the same way you do for `S0_nominal`:

- use the guided prompts as normal
- move the board around the frame between shots
- do not try to reproduce the exact physical board coordinates from `S0`

You do **not** need the exact same board locations as `S0`.
That level of physical repeatability is not required.

What matters is:

- the board covers a good range of image positions
- the board appears at several distances and tilts
- the camera height disturbance is the main intentional change in the run

## Notes Template

Use notes like these when you capture:

- `camera raised about 15 mm above nominal`
- `camera raised about 35 mm above nominal using two spacers`
- `camera lowered about 20 mm below nominal`
- `camera lowered about 50 mm below nominal with tripod column lowered`

If you used a physical support, you can also note:

- `1 thin book added under camera base`
- `2 acrylic spacers added under mount`
- `tripod column lowered by about 30 mm`

That kind of note is useful even if the height is only approximate.

## Command Template

Use this command pattern for each run:

```powershell
.venv\Scripts\accal capture-guided `
  --camera-index 0 `
  --output-dir dataset\S4_height_variation\run_01 `
  --scenario S4_height_variation `
  --run-id run_01 `
  --primary-count 12 `
  --reserved-count 6 `
  --notes "camera raised about 15 mm above nominal"
```

Then update the path, run id, and note for each run.

## Suggested Commands For All 10 Runs

```powershell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_01 --scenario S4_height_variation --run-id run_01 --primary-count 12 --reserved-count 6 --notes "camera raised about 15 mm above nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_02 --scenario S4_height_variation --run-id run_02 --primary-count 12 --reserved-count 6 --notes "camera raised about 25 mm above nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_03 --scenario S4_height_variation --run-id run_03 --primary-count 12 --reserved-count 6 --notes "camera raised about 35 mm above nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_04 --scenario S4_height_variation --run-id run_04 --primary-count 12 --reserved-count 6 --notes "camera raised about 50 mm above nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_05 --scenario S4_height_variation --run-id run_05 --primary-count 12 --reserved-count 6 --notes "camera raised about 60 mm above nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_06 --scenario S4_height_variation --run-id run_06 --primary-count 12 --reserved-count 6 --notes "camera lowered about 15 mm below nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_07 --scenario S4_height_variation --run-id run_07 --primary-count 12 --reserved-count 6 --notes "camera lowered about 25 mm below nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_08 --scenario S4_height_variation --run-id run_08 --primary-count 12 --reserved-count 6 --notes "camera lowered about 35 mm below nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_09 --scenario S4_height_variation --run-id run_09 --primary-count 12 --reserved-count 6 --notes "camera lowered about 50 mm below nominal"
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_10 --scenario S4_height_variation --run-id run_10 --primary-count 12 --reserved-count 6 --notes "camera lowered about 60 mm below nominal"
```

## If A Run Looks Too Hard

If almost every frame becomes unreadable:

- reduce the height change a little
- keep the direction the same
- update the note accordingly

It is better to have a usable moderate run than a useless extreme run.

## Recommendation

For your first pass, follow the matrix exactly.

Do not improvise mixed pose-plus-height conditions yet.
Get one clean 10-run `S4_height_variation` dataset first.
After that, if needed, you can add stronger or mixed runs later.
