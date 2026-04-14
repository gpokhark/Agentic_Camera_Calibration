from __future__ import annotations

from dataclasses import replace

from .capture import load_frame_image
from .models import DetectionResult, FrameRecord, QualityMetrics, RecoveryDecision


def _require_cv2():
    try:
        import cv2  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError("OpenCV is required for recovery preprocessing. Run `uv sync` first.") from exc
    return cv2


class RecoveryExecutor:
    def __init__(self) -> None:
        self.cv2 = None

    def execute(
        self,
        decision: RecoveryDecision,
        active_frames: list[FrameRecord],
        reserved_frames: list[FrameRecord],
        detections: list[DetectionResult],
        quality_metrics: list[QualityMetrics],
    ) -> tuple[list[FrameRecord], list[FrameRecord], dict]:
        exec_log = {"applied_actions": [], "state_updates": {}}
        detection_map = {item.frame_id: item for item in detections}
        quality_map = {item.frame_id: item for item in quality_metrics}

        for action_obj in decision.actions:
            action = action_obj["action"]
            params = action_obj.get("params", {})

            if action == "reject_bad_frames":
                active_frames = self._filter_frames(active_frames, quality_map, detection_map, params)
                exec_log["applied_actions"].append({"action": action, "params": params})

            elif action == "apply_preprocessing":
                active_frames = [self._preprocess_frame(frame, params.get("mode", "clahe")) for frame in active_frames]
                exec_log["applied_actions"].append({"action": action, "params": params})

            elif action == "request_additional_views":
                selected, reserved_frames = self._pull_reserved_frames(
                    reserved_frames,
                    count=int(params.get("count", 4)),
                    pattern=str(params.get("pattern", "general_diversity")),
                )
                active_frames.extend(selected)
                exec_log["applied_actions"].append(
                    {
                        "action": action,
                        "params": params,
                        "added_frame_ids": [frame.frame_id for frame in selected],
                    }
                )

            elif action == "retry_with_filtered_subset":
                active_frames = self._keep_top_k_frames(
                    active_frames,
                    quality_map,
                    detection_map,
                    top_k=int(params.get("top_k", 8)),
                )
                exec_log["applied_actions"].append({"action": action, "params": params})

            elif action == "relax_nominal_prior":
                exec_log["state_updates"]["pose_margin_scale"] = float(params.get("pose_margin_scale", 1.0))
                exec_log["applied_actions"].append({"action": action, "params": params})

        return active_frames, reserved_frames, exec_log

    def _filter_frames(
        self,
        active_frames: list[FrameRecord],
        quality_map: dict[str, QualityMetrics],
        detection_map: dict[str, DetectionResult],
        params: dict,
    ) -> list[FrameRecord]:
        filtered: list[FrameRecord] = []
        for frame in active_frames:
            quality = quality_map.get(frame.frame_id)
            detection = detection_map.get(frame.frame_id)
            keep = True
            if quality is not None:
                if quality.saturation_ratio > float(params.get("max_saturation_ratio", 1.0)):
                    keep = False
                if quality.blur_score < float(params.get("min_blur_score", 0.0)):
                    keep = False
            if detection is not None:
                if detection.charuco_corners_detected < int(params.get("min_charuco_corners", 0)):
                    keep = False
                if detection.coverage_score < float(params.get("min_coverage_score", 0.0)):
                    keep = False
            if keep:
                filtered.append(frame)
        return filtered or active_frames

    def _preprocess_frame(self, frame: FrameRecord, mode: str) -> FrameRecord:
        if self.cv2 is None:
            self.cv2 = _require_cv2()
        frame = load_frame_image(frame)
        image = frame.image

        if mode == "clahe":
            lab = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2LAB)
            l_chan, a_chan, b_chan = self.cv2.split(lab)
            clahe = self.cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            merged = self.cv2.merge((clahe.apply(l_chan), a_chan, b_chan))
            processed = self.cv2.cvtColor(merged, self.cv2.COLOR_LAB2BGR)
        elif mode == "gamma_correction":
            processed = self.cv2.convertScaleAbs(image, alpha=1.2, beta=0)
        elif mode == "contrast_normalization":
            processed = self.cv2.normalize(image, None, 0, 255, self.cv2.NORM_MINMAX)
        else:
            processed = image

        metadata = dict(frame.metadata)
        metadata["preprocessing"] = mode
        return replace(frame, image=processed, metadata=metadata)

    def _pull_reserved_frames(
        self,
        reserved_frames: list[FrameRecord],
        count: int,
        pattern: str,
    ) -> tuple[list[FrameRecord], list[FrameRecord]]:
        def ranking_key(frame: FrameRecord) -> tuple[int, str]:
            tags = frame.metadata.get("tags", [])
            if not isinstance(tags, list):
                tags = [str(tags)]
            score = 0
            if pattern == "edge_coverage" and "edge" in tags:
                score -= 2
            if pattern == "edge_and_tilt" and ("edge" in tags or "tilt" in tags):
                score -= 2
            if pattern == "general_diversity" and "diverse" in tags:
                score -= 1
            return score, frame.frame_id

        ordered = sorted(reserved_frames, key=ranking_key)
        selected = ordered[:count]
        selected_ids = {frame.frame_id for frame in selected}
        remaining = [frame for frame in reserved_frames if frame.frame_id not in selected_ids]
        return selected, remaining

    def _keep_top_k_frames(
        self,
        active_frames: list[FrameRecord],
        quality_map: dict[str, QualityMetrics],
        detection_map: dict[str, DetectionResult],
        top_k: int,
    ) -> list[FrameRecord]:
        def score(frame: FrameRecord) -> float:
            quality = quality_map.get(frame.frame_id)
            detection = detection_map.get(frame.frame_id)
            quality_component = 0.0
            detection_component = 0.0
            if quality is not None:
                quality_component = (
                    quality.blur_score * 0.4
                    + quality.contrast_score * 0.2
                    + (1.0 - quality.saturation_ratio) * 100.0 * 0.2
                    + (1.0 - quality.glare_score) * 100.0 * 0.2
                )
            if detection is not None:
                detection_component = (
                    detection.charuco_corners_detected * 2.0 + detection.coverage_score * 100.0
                )
            return quality_component + detection_component

        ordered = sorted(active_frames, key=score, reverse=True)
        return ordered[:top_k] if len(ordered) > top_k else ordered
