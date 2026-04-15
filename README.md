# Agentic Camera Calibration

This repository implements a single-camera ChArUco calibration pipeline with
three comparison modes:

- baseline calibration
- heuristic recovery
- agent-style recovery with the same action space

The implementation follows the design in `docs/PRD.md` and
`docs/architecture.md`.

For data collection instructions, see `docs/capture_guide.md`.

## Quick start

1. Create the virtual environment:

```powershell
$env:UV_CACHE_DIR = "$PWD\\.uv-cache"
uv venv --python 3.12 .venv
```

2. Install dependencies:

```powershell
$env:UV_CACHE_DIR = "$PWD\\.uv-cache"
uv sync
```

3. Run the unit tests:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

4. Run experiments on a dataset:

```powershell
.venv\Scripts\accal run-experiments --dataset-root dataset --output-dir results
```

4a. Audit the captured dataset and generate a keep/recapture report:

```powershell
.venv\Scripts\accal audit-dataset `
  --dataset-root dataset `
  --output-dir results/dataset_audit
```

This produces `dataset_audit.md`, `dataset_audit.json`, and `dataset_audit.csv`
for review in Markdown, code, or spreadsheet tools.

5. Run a guided USB-camera capture session:

```powershell
.venv\Scripts\accal capture-guided `
  --camera-index 0 `
  --output-dir dataset/S0_nominal/run_01 `
  --scenario S0_nominal `
  --run-id run_01 `
  --primary-count 12 `
  --reserved-count 6
```

The guided preview now shows live ChArUco detection and basic image-quality
feedback before you save each frame.

## Dataset expectations

The runner expects the scenario/run structure described in `docs/architecture.md`:

```text
dataset/
  S0_nominal/
    run_01/
      frame_001.png
      frame_002.png
      metadata.json
```

Frames beyond the configured `initial_frame_count` are treated as reserved
recovery frames unless `metadata.json` explicitly marks them.
