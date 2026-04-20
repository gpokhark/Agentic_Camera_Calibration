from __future__ import annotations

from math import sqrt
from pathlib import Path
from statistics import mean

from .calibration_engine import CalibrationEngine
from .charuco_detector import CharucoDetector
from .config import CalibrationConfig, FailureThresholds, NominalPoseConfig
from .dataset_loader import DatasetLoader
from .deviation_analyzer import DeviationAnalyzer
from .failure_detector import FailureDetector
from .quality_analyzer import QualityAnalyzer


def canonicalize_scenario(name: str) -> str:
    lowered = name.lower()
    if "nominal" in lowered:
        return "S0_nominal"
    if "overexposed" in lowered:
        return "S1_overexposed"
    if "low_light" in lowered or "lowlight" in lowered:
        return "S2_low_light"
    if "pose" in lowered:
        return "S3_pose_deviation"
    if "height" in lowered:
        return "S4_height_variation"
    if "occlusion" in lowered or "partial" in lowered:
        return "S5_partial_visibility"
    return name


def is_eligible_nominal_reference(metrics: dict) -> bool:
    if not metrics["calibration_success"]:
        return False
    if metrics["usable_rate"] < 0.75:
        return False
    if metrics["detection_success_rate"] < 0.80:
        return False
    if metrics["mean_charuco_corners"] < 12.0:
        return False
    if metrics["reprojection_error"] is None or metrics["reprojection_error"] > 1.0:
        return False
    if any(
        code in metrics["reason_codes"]
        for code in ("low_light", "overexposure", "blur_or_low_detail", "glare")
    ):
        return False
    return all(
        metrics[field] is not None
        for field in (
            "estimated_pitch_deg",
            "estimated_yaw_deg",
            "estimated_roll_deg",
            "estimated_tx_mm",
            "estimated_ty_mm",
            "estimated_tz_mm",
        )
    )


def derive_empirical_nominal_reference(run_reports: list[dict]) -> dict | None:
    eligible_reports = [
        report
        for report in run_reports
        if report["canonical_scenario"] == "S0_nominal"
        and is_eligible_nominal_reference(report["initial_metrics"])
    ]
    if not eligible_reports:
        return None

    initial_metrics = [report["initial_metrics"] for report in eligible_reports]
    return {
        "source": "empirical_s0",
        "run_count": len(eligible_reports),
        "run_ids": [report["run_id"] for report in eligible_reports],
        "pitch_deg": round(mean(metrics["estimated_pitch_deg"] for metrics in initial_metrics), 3),
        "yaw_deg": round(mean(metrics["estimated_yaw_deg"] for metrics in initial_metrics), 3),
        "roll_deg": round(mean(metrics["estimated_roll_deg"] for metrics in initial_metrics), 3),
        "tx_mm": round(mean(metrics["estimated_tx_mm"] for metrics in initial_metrics), 3),
        "ty_mm": round(mean(metrics["estimated_ty_mm"] for metrics in initial_metrics), 3),
        "tz_mm": round(mean(metrics["estimated_tz_mm"] for metrics in initial_metrics), 3),
        "derived_from": "mean pose estimate over primary frames of good S0 runs",
    }


def default_nominal_reference(config: CalibrationConfig) -> dict:
    nominal = config.nominal_pose
    return {
        "source": "config_defaults",
        "run_count": 0,
        "run_ids": [],
        "pitch_deg": round(nominal.pitch_deg, 3),
        "yaw_deg": round(nominal.yaw_deg, 3),
        "roll_deg": round(nominal.roll_deg, 3),
        "tx_mm": round(nominal.tx_mm, 3),
        "ty_mm": round(nominal.ty_mm, 3),
        "tz_mm": round(nominal.tz_mm, 3),
        "derived_from": "config/defaults.toml nominal_pose",
    }


def nominal_reference_to_config(nominal_reference: dict) -> NominalPoseConfig:
    return NominalPoseConfig(
        pitch_deg=float(nominal_reference["pitch_deg"]),
        yaw_deg=float(nominal_reference["yaw_deg"]),
        roll_deg=float(nominal_reference["roll_deg"]),
        tx_mm=float(nominal_reference["tx_mm"]),
        ty_mm=float(nominal_reference["ty_mm"]),
        tz_mm=float(nominal_reference["tz_mm"]),
    )


def apply_nominal_reference(metrics: dict, nominal_reference: dict, thresholds: FailureThresholds) -> dict:
    updated = dict(metrics)
    updated["nominal_reference_source"] = nominal_reference["source"]
    updated["nominal_reference_run_count"] = nominal_reference["run_count"]

    required_fields = (
        "estimated_pitch_deg",
        "estimated_yaw_deg",
        "estimated_roll_deg",
        "estimated_tx_mm",
        "estimated_ty_mm",
        "estimated_tz_mm",
    )
    if any(updated[field] is None for field in required_fields):
        updated["deviation_within_nominal_bounds"] = None
        updated["deviation_aggregate_pose_error"] = None
        updated["pitch_deg"] = None
        updated["yaw_deg"] = None
        updated["roll_deg"] = None
        updated["tx_mm"] = None
        updated["ty_mm"] = None
        updated["tz_mm"] = None
        updated["reason_codes"] = [code for code in updated["reason_codes"] if code != "pose_out_of_range"]
        return updated

    pitch_delta = updated["estimated_pitch_deg"] - nominal_reference["pitch_deg"]
    yaw_delta = updated["estimated_yaw_deg"] - nominal_reference["yaw_deg"]
    roll_delta = updated["estimated_roll_deg"] - nominal_reference["roll_deg"]
    tx_mm = updated["estimated_tx_mm"] - nominal_reference["tx_mm"]
    ty_mm = updated["estimated_ty_mm"] - nominal_reference["ty_mm"]
    tz_mm = updated["estimated_tz_mm"] - nominal_reference["tz_mm"]

    aggregate_pose_error = sqrt(
        pitch_delta**2 + yaw_delta**2 + roll_delta**2 + tx_mm**2 + ty_mm**2 + tz_mm**2
    )
    within_nominal_bounds = (
        abs(pitch_delta) <= thresholds.pose_angle_tolerance_deg
        and abs(yaw_delta) <= thresholds.pose_angle_tolerance_deg
        and abs(roll_delta) <= thresholds.pose_angle_tolerance_deg
        and abs(tx_mm) <= thresholds.pose_translation_tolerance_mm
        and abs(ty_mm) <= thresholds.pose_translation_tolerance_mm
        and abs(tz_mm) <= thresholds.pose_translation_tolerance_mm
    )

    updated["deviation_within_nominal_bounds"] = within_nominal_bounds
    updated["deviation_aggregate_pose_error"] = round(aggregate_pose_error, 3)
    updated["pitch_deg"] = round(pitch_delta, 3)
    updated["yaw_deg"] = round(yaw_delta, 3)
    updated["roll_deg"] = round(roll_delta, 3)
    updated["tx_mm"] = round(tx_mm, 3)
    updated["ty_mm"] = round(ty_mm, 3)
    updated["tz_mm"] = round(tz_mm, 3)

    reason_codes = [code for code in updated["reason_codes"] if code != "pose_out_of_range"]
    if not within_nominal_bounds:
        reason_codes.append("pose_out_of_range")
    updated["reason_codes"] = reason_codes
    return updated


class EmpiricalNominalEstimator:
    def __init__(self, config: CalibrationConfig) -> None:
        self.config = config
        self.loader = DatasetLoader(config)
        self.detector = CharucoDetector(config.board)
        self.quality_analyzer = QualityAnalyzer(config.quality)
        self.calibration_engine = CalibrationEngine(self.detector, config.failure)
        self.deviation_analyzer = DeviationAnalyzer(config.failure)
        self.failure_detector = FailureDetector(config.failure, config.quality)

    def derive_for_dataset(
        self,
        dataset_root: str | Path | None = None,
        runs: list | None = None,
    ) -> dict:
        if runs is None:
            dataset_root = Path(dataset_root or self.config.dataset_root)
            runs = self.loader.discover_runs(dataset_root)

        run_reports = []
        for run in runs:
            canonical_scenario = canonicalize_scenario(run.scenario)
            if canonical_scenario != "S0_nominal":
                continue
            initial_frames, _ = self.loader.split_initial_and_reserved(run.frames)
            run_reports.append(
                {
                    "canonical_scenario": canonical_scenario,
                    "run_id": run.run_id,
                    "initial_metrics": self._analyze_frames(initial_frames),
                }
            )

        return derive_empirical_nominal_reference(run_reports) or default_nominal_reference(self.config)

    def _analyze_frames(self, frames: list) -> dict:
        detections = [self.detector.detect(frame) for frame in frames]
        quality_metrics = [self.quality_analyzer.analyze(frame) for frame in frames]
        calibration = self.calibration_engine.calibrate(frames, detections)
        absolute_pose = None
        if calibration.success:
            absolute_pose = self.deviation_analyzer.compute_deviation(
                calibration,
                nominal_pose=NominalPoseConfig(
                    pitch_deg=0.0,
                    yaw_deg=0.0,
                    roll_deg=0.0,
                    tx_mm=0.0,
                    ty_mm=0.0,
                    tz_mm=0.0,
                ),
            )
        deviation = self.deviation_analyzer.compute_deviation(calibration, self.config.nominal_pose) if calibration.success else None
        failure = self.failure_detector.evaluate(calibration, deviation, quality_metrics, detections)

        successful_detections = [item for item in detections if item.detection_success]
        detection_success_rate = 0.0 if not frames else len(successful_detections) / len(frames)
        usable_rate = 0.0 if not frames else sum(1 for metric in quality_metrics if metric.usable) / len(frames)

        return {
            "frame_count": len(frames),
            "usable_frames": sum(1 for metric in quality_metrics if metric.usable),
            "usable_rate": round(usable_rate, 3),
            "detection_success_frames": len(successful_detections),
            "detection_success_rate": round(detection_success_rate, 3),
            "mean_brightness": round(mean(metric.mean_brightness for metric in quality_metrics), 2) if quality_metrics else None,
            "mean_blur": round(mean(metric.blur_score for metric in quality_metrics), 2) if quality_metrics else None,
            "mean_saturation_ratio": round(mean(metric.saturation_ratio for metric in quality_metrics), 4) if quality_metrics else None,
            "mean_glare": round(mean(metric.glare_score for metric in quality_metrics), 4) if quality_metrics else None,
            "mean_charuco_corners": round(mean(item.charuco_corners_detected for item in successful_detections), 2) if successful_detections else 0.0,
            "mean_coverage": round(mean(item.coverage_score for item in successful_detections), 3) if successful_detections else 0.0,
            "calibration_success": calibration.success,
            "reprojection_error": round(calibration.reprojection_error, 4) if calibration.reprojection_error is not None else None,
            "reason_codes": failure.reason_codes,
            "failure_status": failure.status,
            "estimated_pitch_deg": None if absolute_pose is None else round(absolute_pose.pitch_deg, 3),
            "estimated_yaw_deg": None if absolute_pose is None else round(absolute_pose.yaw_deg, 3),
            "estimated_roll_deg": None if absolute_pose is None else round(absolute_pose.roll_deg, 3),
            "estimated_tx_mm": None if absolute_pose is None else round(absolute_pose.tx_mm, 3),
            "estimated_ty_mm": None if absolute_pose is None else round(absolute_pose.ty_mm, 3),
            "estimated_tz_mm": None if absolute_pose is None else round(absolute_pose.tz_mm, 3),
        }
