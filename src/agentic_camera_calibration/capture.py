from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from pathlib import Path

from .config import BoardConfig, QualityThresholds
from .models import DetectionResult, FrameRecord, QualityMetrics


def _require_cv2():
    try:
        import cv2  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError(
            "OpenCV is required for image loading/capture. Run `uv sync` first."
        ) from exc
    return cv2


@dataclass(slots=True)
class CaptureShot:
    name: str
    tags: list[str]
    reserved: bool = False


@dataclass(slots=True)
class LiveCaptureFeedback:
    detection: DetectionResult
    quality: QualityMetrics
    usability_label: str
    usability_color: tuple[int, int, int]
    reason_summary: str


DEFAULT_CAPTURE_PLAN: list[CaptureShot] = [
    CaptureShot("center_01", ["center"]),
    CaptureShot("center_02", ["center"]),
    CaptureShot("center_03", ["center"]),
    CaptureShot("edge_left", ["edge", "left"]),
    CaptureShot("edge_right", ["edge", "right"]),
    CaptureShot("edge_top", ["edge", "top"]),
    CaptureShot("edge_bottom", ["edge", "bottom"]),
    CaptureShot("tilt_left", ["tilt", "left"]),
    CaptureShot("tilt_right", ["tilt", "right"]),
    CaptureShot("tilt_vertical", ["tilt", "vertical"]),
    CaptureShot("close", ["distance", "close"]),
    CaptureShot("far", ["distance", "far"]),
    CaptureShot("reserve_edge_01", ["reserved", "diverse", "edge"], reserved=True),
    CaptureShot("reserve_edge_02", ["reserved", "diverse", "edge"], reserved=True),
    CaptureShot("reserve_tilt_01", ["reserved", "diverse", "tilt"], reserved=True),
    CaptureShot("reserve_tilt_02", ["reserved", "diverse", "tilt"], reserved=True),
    CaptureShot("reserve_close", ["reserved", "diverse", "close"], reserved=True),
    CaptureShot("reserve_far", ["reserved", "diverse", "far"], reserved=True),
]


def load_frame_image(frame: FrameRecord) -> FrameRecord:
    if frame.image is not None:
        return frame
    if frame.image_path is None:
        raise ValueError(f"Frame {frame.frame_id} does not have an image payload or path.")

    cv2 = _require_cv2()
    image = cv2.imread(str(frame.image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not load image for frame {frame.frame_id}: {frame.image_path}")
    return replace(frame, image=image)


def capture_dataset_frames(
    camera_index: int,
    output_dir: str | Path,
    frame_count: int,
    scenario: str,
    run_id: str,
    image_prefix: str = "frame",
) -> list[FrameRecord]:
    cv2 = _require_cv2()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open camera index {camera_index}.")

    try:
        frames: list[FrameRecord] = []
        for index in range(frame_count):
            success, image = capture.read()
            if not success:
                raise RuntimeError(f"Camera read failed at frame {index + 1}.")
            frame_name = f"{image_prefix}_{index + 1:03d}.png"
            frame_path = output_path / frame_name
            cv2.imwrite(str(frame_path), image)
            frames.append(
                FrameRecord(
                    frame_id=frame_name,
                    scenario=scenario,
                    run_id=run_id,
                    image_path=frame_path,
                    image=image,
                )
            )
        return frames
    finally:
        capture.release()


def build_capture_plan(primary_count: int = 12, reserved_count: int = 6) -> list[CaptureShot]:
    if primary_count < 1:
        raise ValueError("primary_count must be at least 1.")
    if reserved_count < 0:
        raise ValueError("reserved_count cannot be negative.")

    primary_shots = [shot for shot in DEFAULT_CAPTURE_PLAN if not shot.reserved]
    reserved_shots = [shot for shot in DEFAULT_CAPTURE_PLAN if shot.reserved]

    plan: list[CaptureShot] = []
    for index in range(primary_count):
        template = primary_shots[index] if index < len(primary_shots) else CaptureShot(
            f"primary_extra_{index - len(primary_shots) + 1:02d}",
            ["primary", "extra"],
        )
        plan.append(CaptureShot(template.name, list(template.tags), reserved=False))

    for index in range(reserved_count):
        template = reserved_shots[index] if index < len(reserved_shots) else CaptureShot(
            f"reserve_extra_{index - len(reserved_shots) + 1:02d}",
            ["reserved", "diverse", "extra"],
            reserved=True,
        )
        plan.append(CaptureShot(template.name, list(template.tags), reserved=True))

    return plan


def guided_capture_run(
    camera_index: int,
    output_dir: str | Path,
    scenario: str,
    run_id: str,
    board_config: BoardConfig,
    quality_thresholds: QualityThresholds | None = None,
    primary_count: int = 12,
    reserved_count: int = 6,
    camera_id: str = "usb_cam_01",
    notes: str = "",
    window_name: str = "Agentic Capture",
) -> list[FrameRecord]:
    cv2 = _require_cv2()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open camera index {camera_index}.")

    plan = build_capture_plan(primary_count=primary_count, reserved_count=reserved_count)
    captured_frames: list[FrameRecord] = []
    captured_shots: list[CaptureShot] = []
    quality_thresholds = quality_thresholds or QualityThresholds()
    feedback_engine = _LiveFeedbackEngine(board_config=board_config, quality_thresholds=quality_thresholds)
    last_feedback: LiveCaptureFeedback | None = None
    last_feedback_at = 0.0

    try:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1440, 1080)
        plan_index = 0

        while plan_index < len(plan):
            success, image = capture.read()
            if not success:
                raise RuntimeError("Camera read failed during guided capture.")

            shot = plan[plan_index]
            preview = image.copy()
            now = time.monotonic()
            if last_feedback is None or (now - last_feedback_at) >= 0.20:
                last_feedback = feedback_engine.analyze_preview_image(image)
                last_feedback_at = now
            _draw_capture_overlay(
                cv2,
                preview,
                shot=shot,
                shot_index=plan_index + 1,
                total_shots=len(plan),
                scenario=scenario,
                run_id=run_id,
                feedback=last_feedback,
            )
            display_frame = _compose_capture_view(cv2, preview, shot, plan_index + 1, len(plan), scenario, run_id, last_feedback)
            cv2.imshow(window_name, display_frame)

            key = cv2.waitKey(20) & 0xFF
            if key in (27, ord("q")):
                raise RuntimeError("Capture cancelled by user.")
            if key in (13, 32, ord("c")):
                frame_name = f"frame_{plan_index + 1:03d}.png"
                frame_path = output_path / frame_name
                cv2.imwrite(str(frame_path), image)
                captured_frames.append(
                    FrameRecord(
                        frame_id=frame_name,
                        scenario=scenario,
                        run_id=run_id,
                        image_path=frame_path,
                        image=image,
                        is_reserved=shot.reserved,
                        metadata={"shot_name": shot.name, "tags": list(shot.tags)},
                    )
                )
                captured_shots.append(shot)
                plan_index += 1
                continue
            if key in (8, ord("b")) and captured_frames:
                last_frame = captured_frames.pop()
                last_shot = captured_shots.pop()
                if last_frame.image_path is not None and last_frame.image_path.exists():
                    last_frame.image_path.unlink()
                plan_index = max(0, plan_index - 1)
                plan[plan_index] = last_shot
                continue
    finally:
        capture.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    write_capture_metadata(
        output_dir=output_path,
        scenario=scenario,
        run_id=run_id,
        board_config=board_config,
        camera_id=camera_id,
        notes=notes,
        frames=captured_frames,
    )
    return captured_frames


def write_capture_metadata(
    output_dir: str | Path,
    scenario: str,
    run_id: str,
    board_config: BoardConfig,
    camera_id: str,
    notes: str,
    frames: list[FrameRecord],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    reserved_frame_ids = [frame.frame_id for frame in frames if frame.is_reserved]
    frame_metadata = {
        frame.frame_id: {
            "shot_name": frame.metadata.get("shot_name"),
            "tags": frame.metadata.get("tags", []),
            "reserved": frame.is_reserved,
        }
        for frame in frames
    }
    metadata = {
        "scenario": scenario,
        "run_id": run_id,
        "camera_id": camera_id,
        "board_type": "charuco",
        "board_config": {
            "squares_x": board_config.squares_x,
            "squares_y": board_config.squares_y,
            "square_length_mm": board_config.square_length_mm,
            "marker_length_mm": board_config.marker_length_mm,
            "dictionary": board_config.dictionary_name,
        },
        "notes": notes,
        "reserved_frame_ids": reserved_frame_ids,
        "frame_metadata": frame_metadata,
    }
    metadata_path = output_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata_path


class _LiveFeedbackEngine:
    def __init__(self, board_config: BoardConfig, quality_thresholds: QualityThresholds) -> None:
        from .charuco_detector import CharucoDetector
        from .quality_analyzer import QualityAnalyzer

        self.detector = CharucoDetector(board_config)
        self.quality_analyzer = QualityAnalyzer(quality_thresholds)
        self.cv2 = _require_cv2()

    def analyze_preview_image(self, image) -> LiveCaptureFeedback:
        preview_frame = FrameRecord(
            frame_id="preview",
            scenario="preview",
            run_id="preview",
            image=image,
        )
        detection = self.detector.detect(preview_frame)
        quality = self.quality_analyzer.analyze(preview_frame)
        label, color, reason_summary = _summarize_live_feedback(detection, quality)
        return LiveCaptureFeedback(
            detection=detection,
            quality=quality,
            usability_label=label,
            usability_color=color,
            reason_summary=reason_summary,
        )


def _summarize_live_feedback(
    detection: DetectionResult,
    quality: QualityMetrics,
) -> tuple[str, tuple[int, int, int], str]:
    issues: list[str] = []
    if detection.charuco_corners_detected < 8:
        issues.append("low_corners")
    if detection.coverage_score < 0.20:
        issues.append("low_coverage")
    if quality.reasons:
        issues.extend(quality.reasons)

    if not issues:
        return "USABLE", (50, 180, 60), "Good frame for capture."
    if len(issues) <= 2:
        return "CAUTION", (0, 200, 255), ", ".join(issues[:3])
    return "POOR", (0, 80, 255), ", ".join(issues[:4])


def _draw_capture_overlay(
    cv2,
    image,
    shot: CaptureShot,
    shot_index: int,
    total_shots: int,
    scenario: str,
    run_id: str,
    feedback: LiveCaptureFeedback | None,
) -> None:
    if feedback is not None:
        _draw_detection_annotations(cv2, image, feedback.detection)


def _draw_detection_annotations(cv2, image, detection: DetectionResult) -> None:
    if detection.marker_corners is not None and detection.marker_ids is not None:
        cv2.aruco.drawDetectedMarkers(image, detection.marker_corners, detection.marker_ids)
    if detection.charuco_corners is not None and detection.charuco_ids is not None:
        cv2.aruco.drawDetectedCornersCharuco(
            image,
            detection.charuco_corners,
            detection.charuco_ids,
            (0, 255, 0),
        )


def _compose_capture_view(
    cv2,
    image,
    shot: CaptureShot,
    shot_index: int,
    total_shots: int,
    scenario: str,
    run_id: str,
    feedback: LiveCaptureFeedback | None,
):
    lines = [
        f"Scenario: {scenario}",
        f"Run: {run_id}",
        f"Shot {shot_index}/{total_shots}: {shot.name}",
        f"Tags: {', '.join(shot.tags)}",
        "Keys: [Space/C/Enter] capture  [B/Backspace] undo  [Q/Esc] quit",
    ]
    if shot.reserved:
        lines.append("This frame will be tagged as RESERVED.")
    if feedback is not None:
        lines.extend(
            [
                f"Live status: {feedback.usability_label}",
                (
                    "Detection: "
                    f"markers={feedback.detection.markers_detected}  "
                    f"charuco={feedback.detection.charuco_corners_detected}  "
                    f"coverage={feedback.detection.coverage_score:.2f}"
                ),
                (
                    "Quality: "
                    f"brightness={feedback.quality.mean_brightness:.1f}  "
                    f"blur={feedback.quality.blur_score:.1f}  "
                    f"glare={feedback.quality.glare_score:.2f}"
                ),
                f"Why: {feedback.reason_summary}",
            ]
        )

    panel_height = max(220, 30 + len(lines) * 28)
    panel = _make_info_panel(cv2, width=image.shape[1], height=panel_height, lines=lines, feedback=feedback)
    return cv2.vconcat([image, panel])


def _make_info_panel(cv2, width: int, height: int, lines: list[str], feedback: LiveCaptureFeedback | None):
    panel = cv2.UMat(height, width, cv2.CV_8UC3).get()
    panel[:, :] = (24, 24, 24)

    cv2.rectangle(panel, (0, 0), (width - 1, height - 1), (0, 180, 255), 2)
    divider_y = 52
    cv2.line(panel, (0, divider_y), (width - 1, divider_y), (60, 60, 60), 1)

    title = "Agentic Camera Capture"
    cv2.putText(
        panel,
        title,
        (24, 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    for index, line in enumerate(lines):
        color = (235, 235, 235)
        if feedback is not None and line.startswith("Live status:"):
            color = feedback.usability_color
        cv2.putText(
            panel,
            line,
            (24, 84 + index * 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            color,
            2,
            cv2.LINE_AA,
        )

    return panel
