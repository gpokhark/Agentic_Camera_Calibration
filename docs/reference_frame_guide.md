# Reference Frame Capture Guide

This guide explains how to capture **fixed reference frames** that can be used
for cleaner nominal-versus-disturbed comparison, especially for:

- `S0_nominal`
- `S3_pose_deviation`
- `S4_height_variation`

These reference frames are **in addition to** the normal guided capture run.
They are intended for:

- cleaner pose comparison against nominal
- manual validation and paper figures
- future analysis improvements

They are not required for the current pipeline to run, but they are strongly
recommended for future captures.

## Why Reference Frames Help

In the normal dataset:

- the board moves between frames
- this is good for calibration diversity
- but it makes direct geometry comparison noisier

A fixed reference frame solves that by keeping the board in one standard
position while only the intended disturbance changes.

That gives a cleaner answer to:

- how does this disturbed run differ from nominal?
- is the change really pose-related or height-related?

## When To Capture Them

Capture reference frames:

- for at least `3` to `5` good `S0_nominal` runs
- for every `S3_pose_deviation` run if possible
- for every `S4_height_variation` run if possible

You may also capture them for other scenarios, but they matter most for `S3`
and `S4`.

## How Many To Capture

Recommended:

- `3` reference frames per run

Minimum if time is tight:

- `2` reference frames per run

Why `3` is better:

- it reduces the chance that one slightly blurry shot becomes your only
  reference
- it gives a small amount of repeatability evidence without creating much extra
  work

## Command To Use

Use the dedicated `capture-reference` command:

```powershell
.venv\Scripts\accal capture-reference `
  --camera-index 0 `
  --output-dir dataset\S3_pose_deviation\run_01\reference_frames `
  --scenario S3_pose_deviation `
  --run-id run_01 `
  --frame-count 3 `
  --notes "fixed reference frames captured before moving-board run"
```

This command:

- opens the live capture GUI
- captures `ref_001.png`, `ref_002.png`, and `ref_003.png`
- stores them in the `reference_frames/` subfolder
- writes a local `metadata.json` in that subfolder

Recommended examples:

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\S0_nominal\run_01\reference_frames --scenario S0_nominal --run-id run_01 --frame-count 3 --notes "fixed nominal reference frames"
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\S3_pose_deviation\run_01\reference_frames --scenario S3_pose_deviation --run-id run_01 --frame-count 3 --notes "fixed reference frames before pose-deviation run"
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\S4_height_variation\run_01\reference_frames --scenario S4_height_variation --run-id run_01 --frame-count 3 --notes "fixed reference frames before height-variation run"
```

After the reference frames are saved, run the normal guided capture command for
the full dataset run.

## Where To Store Them

Store reference frames in a subfolder inside the run directory:

```text
dataset/
  S3_pose_deviation/
    run_01/
      frame_001.png
      frame_002.png
      ...
      metadata.json
      reference_frames/
        ref_001.png
        ref_002.png
        ref_003.png
```

This is safe with the current repo because the dataset loader only reads images
from the **top level** of the run folder. Files inside `reference_frames/` will
not interfere with the existing calibration pipeline.

## Core Rule

For a reference frame:

- the **camera stays fixed** for that run
- the **board goes to one standard reference position**
- the **board does not move between the 2 to 3 reference captures**

The only thing that should differ across scenarios is the scenario disturbance:

- `S0`: nominal camera setup
- `S3`: changed camera angle
- `S4`: changed camera height

## Standard Reference Pose

Use one standard board placement and repeat it every time.

Recommended reference pose:

- board centered in the image
- board fully visible
- board roughly front-facing to the camera
- board not strongly tilted
- board not cropped
- board large enough for reliable ChArUco detection
- small margin visible on all four sides of the board

Practical guidance:

- place the board near the middle of your usual working area
- keep it flat and stable
- avoid strong glare or shadow for the reference captures
- do not use the `close`, `far`, or edge prompts for the reference frames

Think of the reference pose as your "clean, centered comparison shot."

## Best Practical Setup

To make this repeatable, mark the board reference position physically:

- put small tape marks on the table for the board corners
- or mark the board center point and bottom edge position
- if you use a stand, mark the stand location too

That way, for every run, you can return the board to nearly the same place.

You do **not** need metrology-grade precision.
You just want the reference placement to be much more consistent than the
normal moving-board captures.

## Capture Sequence For `S0_nominal`

For a nominal run:

1. Set the camera to the normal nominal setup.
2. Place the board at the taped or marked reference position.
3. Check the board is fully visible and reasonably centered.
4. Capture `ref_001.png`.
5. Without changing camera or board position, capture `ref_002.png`.
6. Capture `ref_003.png`.
7. After that, start the normal guided run and move the board through the usual
   18-frame pattern.

## Capture Sequence For `S3_pose_deviation`

For a pose-deviation run:

1. Apply the planned camera tilt or yaw for that run.
2. Leave the camera fixed in that disturbed pose.
3. Place the board at the exact same reference position used for nominal.
4. Capture `ref_001.png`, `ref_002.png`, and `ref_003.png`.
5. Then do the normal guided run with the moving-board pattern.

Important:

- do not move the camera between the reference captures
- do not compensate by moving the board to "fix" the disturbed geometry

The point is to preserve the disturbed camera pose and compare it against the
same board reference placement.

## Capture Sequence For `S4_height_variation`

For a height-variation run:

1. Raise or lower the camera to the planned height for that run.
2. Keep the camera angle as close to nominal as possible.
3. Place the board at the same reference position used for nominal.
4. Capture `ref_001.png`, `ref_002.png`, and `ref_003.png`.
5. Then perform the normal guided run with the moving-board pattern.

Important:

- do not change the board reference placement to compensate for the new camera
  height
- do not tilt the camera just to make the image look more like nominal

The point is to observe how the changed camera height affects the same
reference scene.

## What Not To Do

Avoid these mistakes:

- capturing reference frames after you already started moving the board
- changing the board distance between `ref_001` and `ref_003`
- trying to make every disturbed reference frame "look like" nominal
- using occlusion, glare, or low light in the reference captures for `S3` or
  `S4`
- storing the reference images in the run root where they might be treated like
  normal frames

## File Naming

Use simple names:

- `ref_001.png`
- `ref_002.png`
- `ref_003.png`

If you want, add a small note file in the same folder:

```text
reference_frames/
  ref_001.png
  ref_002.png
  ref_003.png
  notes.txt
```

Example `notes.txt` contents:

- scenario and run id
- disturbance description
- whether the board was taped to a marked location
- any issue such as mild glare or slight tilt

## Recommended Minimal Workflow

If you want the simplest practical version, do this:

1. Mark one board reference position on the table.
2. For each `S0`, `S3`, and `S4` run, capture `3` fixed reference frames
   first.
3. Save them in `reference_frames/`.
4. Then do the normal guided capture run.

That alone is enough to make future comparison much stronger.

## Efficient Workflow For Future Capture

To avoid doubling your effort, use this sequence for each new `S3` or `S4`
run:

1. Set the camera disturbance for the run.
2. Place the board at the marked reference position.
3. Run `capture-reference` and save `3` fixed reference images.
4. Without changing the camera disturbance, start `capture-guided`.
5. Move the board through the normal `12 + 6` capture sequence.

This adds only a small amount of extra time per run and gives you much cleaner
comparison data.

## Important Note About Older Data

Your already-collected data is still useful even if it has no reference frames.

Reference frames are best viewed as:

- an improvement for future capture
- an aid for cleaner interpretation
- a way to make the paper easier to defend

They are **not** a reason to discard older `S3` or `S4` runs that are already
usable.

## Efficient Retrofit Strategy For Older Data

If you already collected `S3` and `S4` runs, do **not** recollect the whole
dataset.

Use this priority order instead:

1. Keep the existing full runs exactly as they are.
2. Add reference frames only to new runs going forward.
3. If time allows, retrofit reference frames for a small subset of the most
   important older runs.

A practical retrofit target is:

- `3` to `5` good `S0_nominal` runs
- `3` representative `S3_pose_deviation` runs
- `3` representative `S4_height_variation` runs

That already gives you a much stronger story for the paper without repeating
every run.

If you retrofit an older run, create the matching subfolder and capture only
the fixed reference images:

```powershell
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\S3_pose_deviation\run_04\reference_frames --scenario S3_pose_deviation --run-id run_04 --frame-count 3 --notes "retrofit fixed reference frames captured after original run"
```

This approach augments the older dataset rather than replacing it.
