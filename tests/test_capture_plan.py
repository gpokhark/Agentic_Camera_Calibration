import json
import shutil
import unittest
from pathlib import Path

from agentic_camera_calibration.capture import build_capture_plan, write_capture_metadata
from agentic_camera_calibration.config import BoardConfig
from agentic_camera_calibration.models import FrameRecord


class CapturePlanTests(unittest.TestCase):
    def test_build_capture_plan_marks_reserved_frames(self) -> None:
        plan = build_capture_plan(primary_count=12, reserved_count=6)
        self.assertEqual(len(plan), 18)
        self.assertFalse(any(shot.reserved for shot in plan[:12]))
        self.assertTrue(all(shot.reserved for shot in plan[12:]))

    def test_write_capture_metadata_records_reserved_and_tags(self) -> None:
        output_dir = Path("tests/.tmp_capture_plan")
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            frames = [
                FrameRecord(
                    frame_id="frame_001.png",
                    scenario="S0_nominal",
                    run_id="run_01",
                    image_path=output_dir / "frame_001.png",
                    is_reserved=False,
                    metadata={"shot_name": "center_01", "tags": ["center"]},
                ),
                FrameRecord(
                    frame_id="frame_013.png",
                    scenario="S0_nominal",
                    run_id="run_01",
                    image_path=output_dir / "frame_013.png",
                    is_reserved=True,
                    metadata={"shot_name": "reserve_edge_01", "tags": ["reserved", "edge"]},
                ),
            ]

            metadata_path = write_capture_metadata(
                output_dir=output_dir,
                scenario="S0_nominal",
                run_id="run_01",
                board_config=BoardConfig(),
                camera_id="usb_cam_01",
                notes="test run",
                frames=frames,
            )

            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["reserved_frame_ids"], ["frame_013.png"])
            self.assertEqual(payload["frame_metadata"]["frame_001.png"]["shot_name"], "center_01")
            self.assertTrue(payload["frame_metadata"]["frame_013.png"]["reserved"])
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
