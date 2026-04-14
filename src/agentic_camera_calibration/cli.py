from __future__ import annotations

import argparse
import json

from .capture import capture_dataset_frames, guided_capture_run, write_capture_metadata
from .config import load_config
from .experiment_runner import ExperimentRunner
from .models import to_jsonable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agentic camera calibration runner")
    parser.add_argument("--config", default="config/defaults.toml", help="Path to TOML config")

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-experiments", help="Run all experiment modes on a dataset")
    run_parser.add_argument("--dataset-root", default=None, help="Override dataset root")
    run_parser.add_argument("--output-dir", default=None, help="Override results output directory")

    capture_parser = subparsers.add_parser("capture", help="Capture a dataset run from a USB camera")
    capture_parser.add_argument("--camera-index", type=int, default=0)
    capture_parser.add_argument("--output-dir", required=True)
    capture_parser.add_argument("--scenario", required=True)
    capture_parser.add_argument("--run-id", required=True)
    capture_parser.add_argument("--frame-count", type=int, default=12)
    capture_parser.add_argument("--camera-id", default="usb_cam_01")
    capture_parser.add_argument("--notes", default="")

    guided_capture_parser = subparsers.add_parser(
        "capture-guided",
        help="Guided OpenCV capture session with on-screen shot prompts",
    )
    guided_capture_parser.add_argument("--camera-index", type=int, default=0)
    guided_capture_parser.add_argument("--output-dir", required=True)
    guided_capture_parser.add_argument("--scenario", required=True)
    guided_capture_parser.add_argument("--run-id", required=True)
    guided_capture_parser.add_argument("--primary-count", type=int, default=12)
    guided_capture_parser.add_argument("--reserved-count", type=int, default=6)
    guided_capture_parser.add_argument("--camera-id", default="usb_cam_01")
    guided_capture_parser.add_argument("--notes", default="")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "run-experiments":
        runner = ExperimentRunner(config)
        results = runner.run_all(dataset_root=args.dataset_root, output_dir=args.output_dir)
        print(json.dumps([to_jsonable(result) for result in results], indent=2))
        return

    if args.command == "capture":
        frames = capture_dataset_frames(
            camera_index=args.camera_index,
            output_dir=args.output_dir,
            frame_count=args.frame_count,
            scenario=args.scenario,
            run_id=args.run_id,
        )
        write_capture_metadata(
            output_dir=args.output_dir,
            scenario=args.scenario,
            run_id=args.run_id,
            board_config=config.board,
            camera_id=args.camera_id,
            notes=args.notes,
            frames=frames,
        )
        print(json.dumps([frame.frame_id for frame in frames], indent=2))
        return

    if args.command == "capture-guided":
        frames = guided_capture_run(
            camera_index=args.camera_index,
            output_dir=args.output_dir,
            scenario=args.scenario,
            run_id=args.run_id,
            board_config=config.board,
            quality_thresholds=config.quality,
            primary_count=args.primary_count,
            reserved_count=args.reserved_count,
            camera_id=args.camera_id,
            notes=args.notes,
        )
        print(json.dumps([frame.frame_id for frame in frames], indent=2))
        return

    raise SystemExit(f"Unhandled command: {args.command}")
