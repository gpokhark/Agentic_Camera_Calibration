from __future__ import annotations

import json
from pathlib import Path

from .config import CalibrationConfig
from .models import FrameRecord, RunRecord


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _infer_setup_type(run_dir: Path, metadata: dict, scenario: str) -> str:
    explicit = str(metadata.get("setup_type", "")).strip()
    if explicit:
        return explicit

    if scenario.casefold().endswith("_fixed"):
        return "benchmark_fixed_target"

    lowered_parts = {part.casefold() for part in run_dir.parts}
    if "fixed_target_benchmark" in lowered_parts:
        return "benchmark_fixed_target"
    if "pilot_moving_target" in lowered_parts:
        return "pilot_moving_target"
    return "unspecified"


def _infer_dataset_split(run_dir: Path, metadata: dict) -> str:
    explicit = str(metadata.get("dataset_split", metadata.get("split", ""))).strip()
    if explicit:
        return explicit

    lowered_parts = {part.casefold() for part in run_dir.parts}
    for split_name in ("train", "dev", "eval"):
        if split_name in lowered_parts:
            return split_name
    return "unspecified"


class DatasetLoader:
    def __init__(self, config: CalibrationConfig) -> None:
        self.config = config

    def discover_runs(self, dataset_root: str | Path) -> list[RunRecord]:
        dataset_path = Path(dataset_root)
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset root does not exist: {dataset_path}")

        runs: list[RunRecord] = []
        for scenario_dir in sorted(path for path in dataset_path.iterdir() if path.is_dir()):
            for run_dir in sorted(path for path in scenario_dir.iterdir() if path.is_dir()):
                runs.append(self.load_run(run_dir))
        return runs

    def load_run(self, run_path: str | Path) -> RunRecord:
        run_dir = Path(run_path)
        metadata_path = run_dir / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        scenario = metadata.get("scenario", run_dir.parent.name)
        run_id = metadata.get("run_id", run_dir.name)
        reserved_ids = set(metadata.get("reserved_frame_ids", []))
        setup_type = _infer_setup_type(run_dir, metadata, scenario)
        dataset_split = _infer_dataset_split(run_dir, metadata)
        metadata = dict(metadata)
        metadata.setdefault("setup_type", setup_type)
        metadata.setdefault("dataset_split", dataset_split)

        frames: list[FrameRecord] = []
        image_paths = sorted(path for path in run_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
        initial_limit = self.config.experiment.initial_frame_count

        for index, image_path in enumerate(image_paths):
            frame_id = image_path.name
            is_reserved = frame_id in reserved_ids or index >= initial_limit
            frames.append(
                FrameRecord(
                    frame_id=frame_id,
                    scenario=scenario,
                    run_id=run_id,
                    setup_type=setup_type,
                    dataset_split=dataset_split,
                    image_path=image_path,
                    is_reserved=is_reserved,
                    metadata=metadata.get("frame_metadata", {}).get(frame_id, {}),
                )
            )

        return RunRecord(
            run_id=run_id,
            scenario=scenario,
            run_path=run_dir,
            frames=frames,
            setup_type=setup_type,
            dataset_split=dataset_split,
            metadata=metadata,
        )

    def split_initial_and_reserved(
        self, frames: list[FrameRecord]
    ) -> tuple[list[FrameRecord], list[FrameRecord]]:
        initial = [frame for frame in frames if not frame.is_reserved]
        reserved = [frame for frame in frames if frame.is_reserved]
        if not initial:
            initial = frames[: self.config.experiment.initial_frame_count]
            reserved = frames[self.config.experiment.initial_frame_count :]
        return initial, reserved
