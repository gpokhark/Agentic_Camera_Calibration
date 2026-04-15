from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean

from .calibration_engine import CalibrationEngine
from .charuco_detector import CharucoDetector
from .config import CalibrationConfig
from .dataset_loader import DatasetLoader
from .deviation_analyzer import DeviationAnalyzer
from .failure_detector import FailureDetector
from .quality_analyzer import QualityAnalyzer


def _canonicalize_scenario(name: str) -> str:
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


def _expected_run_ids() -> list[str]:
    return [f"run_{index:02d}" for index in range(1, 11)]


def _count_existing_runs(run_ids: list[str]) -> list[str]:
    existing = set(run_ids)
    return [run_id for run_id in _expected_run_ids() if run_id not in existing]


def _classify_run(
    canonical_scenario: str,
    initial_metrics: dict,
    all_metrics: dict,
    metadata_present: bool,
    initial_frame_count: int,
    reserved_frame_count: int,
    quality_floor_brightness: float,
) -> dict:
    notes: list[str] = []
    recapture_recommended = False

    if not metadata_present:
        notes.append("metadata.json missing or unreadable")
        recapture_recommended = True
    if initial_frame_count < 12:
        notes.append(f"only {initial_frame_count} primary frames found; expected at least 12")
        recapture_recommended = True
    if reserved_frame_count < 4:
        notes.append(f"only {reserved_frame_count} reserved frames found; expected at least 4")
        recapture_recommended = True
    if not all_metrics["calibration_success"]:
        notes.append("calibration failed on the full run")
        recapture_recommended = True
    if all_metrics["detection_success_rate"] < 0.80:
        notes.append("too many frames failed ChArUco detection")
        recapture_recommended = True
    if all_metrics["mean_charuco_corners"] < 12.0:
        notes.append("mean ChArUco corner count is too low")
        recapture_recommended = True

    scenario_fit_ok = True
    if canonical_scenario == "S0_nominal":
        if initial_metrics["usable_rate"] < 0.75:
            notes.append("nominal run has too many frames failing image-quality thresholds")
            recapture_recommended = True
        if initial_metrics["reprojection_error"] is None or initial_metrics["reprojection_error"] > 0.5:
            notes.append("nominal run reprojection error is higher than expected")
            recapture_recommended = True
        if any(
            code in initial_metrics["reason_codes"]
            for code in ("low_light", "overexposure", "blur_or_low_detail", "glare")
        ):
            notes.append("nominal run shows disturbance-like quality issues")
            recapture_recommended = True
        if "low_marker_coverage" in all_metrics["reason_codes"]:
            notes.append("coverage is a bit weak; keep if no stronger nominal replacement exists")
        if "pose_out_of_range" in all_metrics["reason_codes"]:
            notes.append("pose warning likely reflects nominal-pose thresholding rather than bad images")
    elif canonical_scenario == "S1_overexposed":
        scenario_fit_ok = (
            all_metrics["mean_saturation_ratio"] > 0.01 or all_metrics["mean_glare"] > 0.03
        )
        if not scenario_fit_ok:
            notes.append("overexposure/glare signal looks weak for S1")
            recapture_recommended = True
    elif canonical_scenario == "S2_low_light":
        scenario_fit_ok = all_metrics["mean_brightness"] < quality_floor_brightness
        if not scenario_fit_ok:
            notes.append("brightness does not look low enough for S2")
            recapture_recommended = True
        if all_metrics["detection_success_rate"] >= 0.80 and all_metrics["calibration_success"]:
            notes.append("strong low-light disturbance but still analyzable")
    elif canonical_scenario == "S3_pose_deviation":
        scenario_fit_ok = (
            ("pose_out_of_range" in all_metrics["reason_codes"])
            or (all_metrics["deviation_within_nominal_bounds"] is False)
            or (all_metrics["deviation_aggregate_pose_error"] is not None and all_metrics["deviation_aggregate_pose_error"] > 5.0)
        )
        if not scenario_fit_ok:
            notes.append("pose deviation is not clearly observable from calibration metrics")
            recapture_recommended = True
    elif canonical_scenario == "S4_height_variation":
        scenario_fit_ok = (
            ("pose_out_of_range" in all_metrics["reason_codes"])
            or (all_metrics["tz_mm"] is not None and abs(all_metrics["tz_mm"]) > 10.0)
        )
        if not scenario_fit_ok:
            notes.append("height variation is not clearly observable from calibration metrics")
            recapture_recommended = True
    elif canonical_scenario == "S5_partial_visibility":
        scenario_fit_ok = (
            all_metrics["mean_coverage"] < 0.35
            or "low_marker_coverage" in all_metrics["reason_codes"]
            or all_metrics["detection_success_rate"] < 0.95
        )
        if not scenario_fit_ok:
            notes.append("partial-visibility effect looks weak for S5")
            recapture_recommended = True

    usable_for_analysis = (
        all_metrics["calibration_success"]
        and all_metrics["detection_success_rate"] >= 0.80
        and all_metrics["mean_charuco_corners"] >= 12.0
    )
    if canonical_scenario == "S0_nominal":
        usable_for_analysis = usable_for_analysis and initial_metrics["usable_rate"] >= 0.75

    if recapture_recommended:
        status = "recapture"
    elif notes:
        status = "keep_with_note"
    else:
        status = "keep"

    return {
        "status": status,
        "usable_for_analysis": usable_for_analysis,
        "recapture_recommended": recapture_recommended,
        "scenario_fit_ok": scenario_fit_ok,
        "notes": notes,
    }


class DatasetAuditor:
    def __init__(self, config: CalibrationConfig) -> None:
        self.config = config
        self.loader = DatasetLoader(config)
        self.detector = CharucoDetector(config.board)
        self.quality_analyzer = QualityAnalyzer(config.quality)
        self.calibration_engine = CalibrationEngine(self.detector, config.failure)
        self.deviation_analyzer = DeviationAnalyzer(config.failure)
        self.failure_detector = FailureDetector(config.failure, config.quality)

    def audit_dataset(
        self,
        dataset_root: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> dict:
        dataset_root = Path(dataset_root or self.config.dataset_root)
        output_dir = Path(output_dir or (self.config.results_root / "dataset_audit"))
        runs = self.loader.discover_runs(dataset_root)

        run_reports = [self._audit_run(run) for run in runs]
        scenario_summary = self._summarize_scenarios(run_reports)
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset_root": str(dataset_root),
            "run_count": len(run_reports),
            "scenario_summary": scenario_summary,
            "runs": run_reports,
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "dataset_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (output_dir / "dataset_audit.md").write_text(self._build_markdown_report(report), encoding="utf-8")
        self._write_csv_report(output_dir / "dataset_audit.csv", run_reports)
        return report

    def _audit_run(self, run) -> dict:
        initial_frames, reserved_frames = self.loader.split_initial_and_reserved(run.frames)
        initial_metrics = self._analyze_frames(initial_frames)
        all_metrics = self._analyze_frames(run.frames)
        canonical_scenario = _canonicalize_scenario(run.scenario)
        classification = _classify_run(
            canonical_scenario=canonical_scenario,
            initial_metrics=initial_metrics,
            all_metrics=all_metrics,
            metadata_present=bool(run.metadata),
            initial_frame_count=len(initial_frames),
            reserved_frame_count=len(reserved_frames),
            quality_floor_brightness=self.config.quality.min_brightness,
        )

        return {
            "scenario": run.scenario,
            "canonical_scenario": canonical_scenario,
            "run_id": run.run_id,
            "run_path": str(run.run_path),
            "metadata_present": bool(run.metadata),
            "primary_frame_count": len(initial_frames),
            "reserved_frame_count": len(reserved_frames),
            "initial_metrics": initial_metrics,
            "all_frame_metrics": all_metrics,
            **classification,
        }

    def _analyze_frames(self, frames: list) -> dict:
        detections = [self.detector.detect(frame) for frame in frames]
        quality_metrics = [self.quality_analyzer.analyze(frame) for frame in frames]
        calibration = self.calibration_engine.calibrate(frames, detections)
        deviation = None
        if calibration.success:
            deviation = self.deviation_analyzer.compute_deviation(calibration, self.config.nominal_pose)
        failure = self.failure_detector.evaluate(calibration, deviation, quality_metrics, detections)

        successful_detections = [item for item in detections if item.detection_success]
        quality_reason_counts = Counter(reason for metric in quality_metrics for reason in metric.reasons)
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
            "quality_reason_counts": dict(quality_reason_counts),
            "deviation_within_nominal_bounds": None if deviation is None else deviation.within_nominal_bounds,
            "deviation_aggregate_pose_error": None if deviation is None else round(deviation.aggregate_pose_error, 3),
            "pitch_deg": None if deviation is None else round(deviation.pitch_deg, 3),
            "yaw_deg": None if deviation is None else round(deviation.yaw_deg, 3),
            "roll_deg": None if deviation is None else round(deviation.roll_deg, 3),
            "tx_mm": None if deviation is None else round(deviation.tx_mm, 3),
            "ty_mm": None if deviation is None else round(deviation.ty_mm, 3),
            "tz_mm": None if deviation is None else round(deviation.tz_mm, 3),
        }

    def _summarize_scenarios(self, run_reports: list[dict]) -> list[dict]:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for report in run_reports:
            grouped[report["canonical_scenario"]].append(report)

        summaries: list[dict] = []
        for canonical_scenario, reports in sorted(grouped.items()):
            statuses = Counter(report["status"] for report in reports)
            usable_count = sum(1 for report in reports if report["usable_for_analysis"])
            run_ids = [report["run_id"] for report in reports]
            summaries.append(
                {
                    "scenario": canonical_scenario,
                    "runs_found": len(reports),
                    "usable_runs": usable_count,
                    "keep_runs": statuses.get("keep", 0),
                    "keep_with_note_runs": statuses.get("keep_with_note", 0),
                    "recapture_runs": statuses.get("recapture", 0),
                    "missing_expected_runs": _count_existing_runs(run_ids),
                }
            )
        return summaries

    def _build_markdown_report(self, report: dict) -> str:
        lines: list[str] = []
        lines.append("# Dataset Audit Report")
        lines.append("")
        lines.append(f"- Generated: `{report['generated_at']}`")
        lines.append(f"- Dataset root: `{report['dataset_root']}`")
        lines.append(f"- Runs audited: `{report['run_count']}`")
        lines.append("")
        lines.append("## Scenario Summary")
        lines.append("")
        lines.append("| Scenario | Runs Found | Usable | Keep | Keep With Note | Recapture | Missing Expected Runs |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
        for item in report["scenario_summary"]:
            missing = ", ".join(item["missing_expected_runs"]) if item["missing_expected_runs"] else "-"
            lines.append(
                f"| {item['scenario']} | {item['runs_found']} | {item['usable_runs']} | "
                f"{item['keep_runs']} | {item['keep_with_note_runs']} | {item['recapture_runs']} | {missing} |"
            )

        grouped: dict[str, list[dict]] = defaultdict(list)
        for run_report in report["runs"]:
            grouped[run_report["canonical_scenario"]].append(run_report)

        for scenario, reports in sorted(grouped.items()):
            lines.append("")
            lines.append(f"## {scenario}")
            lines.append("")
            for run_report in sorted(reports, key=lambda item: item["run_id"]):
                initial = run_report["initial_metrics"]
                all_frames = run_report["all_frame_metrics"]
                lines.append(f"### {run_report['run_id']}")
                lines.append("")
                lines.append(f"- Status: `{run_report['status']}`")
                lines.append(f"- Usable for analysis: `{run_report['usable_for_analysis']}`")
                lines.append(f"- Recapture recommended: `{run_report['recapture_recommended']}`")
                lines.append(f"- Primary / reserved frames: `{run_report['primary_frame_count']}` / `{run_report['reserved_frame_count']}`")
                lines.append(
                    f"- Initial metrics: detection rate `{initial['detection_success_rate']}`, "
                    f"usable rate `{initial['usable_rate']}`, reprojection `{initial['reprojection_error']}`"
                )
                lines.append(
                    f"- Full-run metrics: detection rate `{all_frames['detection_success_rate']}`, "
                    f"mean corners `{all_frames['mean_charuco_corners']}`, "
                    f"brightness `{all_frames['mean_brightness']}`, "
                    f"reprojection `{all_frames['reprojection_error']}`"
                )
                if run_report["notes"]:
                    lines.append("- Notes:")
                    for note in run_report["notes"]:
                        lines.append(f"  - {note}")
                if all_frames["reason_codes"]:
                    lines.append(f"- Failure-detector reason codes: `{', '.join(all_frames['reason_codes'])}`")
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _write_csv_report(self, path: Path, run_reports: list[dict]) -> None:
        fieldnames = [
            "scenario",
            "canonical_scenario",
            "run_id",
            "run_path",
            "status",
            "usable_for_analysis",
            "recapture_recommended",
            "scenario_fit_ok",
            "metadata_present",
            "primary_frame_count",
            "reserved_frame_count",
            "initial_detection_success_rate",
            "initial_usable_rate",
            "initial_mean_brightness",
            "initial_mean_blur",
            "initial_mean_charuco_corners",
            "initial_mean_coverage",
            "initial_reprojection_error",
            "all_detection_success_rate",
            "all_usable_rate",
            "all_mean_brightness",
            "all_mean_blur",
            "all_mean_saturation_ratio",
            "all_mean_glare",
            "all_mean_charuco_corners",
            "all_mean_coverage",
            "all_reprojection_error",
            "all_failure_status",
            "all_reason_codes",
            "all_quality_reason_counts",
            "deviation_within_nominal_bounds",
            "deviation_aggregate_pose_error",
            "pitch_deg",
            "yaw_deg",
            "roll_deg",
            "tx_mm",
            "ty_mm",
            "tz_mm",
            "notes",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for report in run_reports:
                initial = report["initial_metrics"]
                all_frames = report["all_frame_metrics"]
                writer.writerow(
                    {
                        "scenario": report["scenario"],
                        "canonical_scenario": report["canonical_scenario"],
                        "run_id": report["run_id"],
                        "run_path": report["run_path"],
                        "status": report["status"],
                        "usable_for_analysis": report["usable_for_analysis"],
                        "recapture_recommended": report["recapture_recommended"],
                        "scenario_fit_ok": report["scenario_fit_ok"],
                        "metadata_present": report["metadata_present"],
                        "primary_frame_count": report["primary_frame_count"],
                        "reserved_frame_count": report["reserved_frame_count"],
                        "initial_detection_success_rate": initial["detection_success_rate"],
                        "initial_usable_rate": initial["usable_rate"],
                        "initial_mean_brightness": initial["mean_brightness"],
                        "initial_mean_blur": initial["mean_blur"],
                        "initial_mean_charuco_corners": initial["mean_charuco_corners"],
                        "initial_mean_coverage": initial["mean_coverage"],
                        "initial_reprojection_error": initial["reprojection_error"],
                        "all_detection_success_rate": all_frames["detection_success_rate"],
                        "all_usable_rate": all_frames["usable_rate"],
                        "all_mean_brightness": all_frames["mean_brightness"],
                        "all_mean_blur": all_frames["mean_blur"],
                        "all_mean_saturation_ratio": all_frames["mean_saturation_ratio"],
                        "all_mean_glare": all_frames["mean_glare"],
                        "all_mean_charuco_corners": all_frames["mean_charuco_corners"],
                        "all_mean_coverage": all_frames["mean_coverage"],
                        "all_reprojection_error": all_frames["reprojection_error"],
                        "all_failure_status": all_frames["failure_status"],
                        "all_reason_codes": "; ".join(all_frames["reason_codes"]),
                        "all_quality_reason_counts": json.dumps(all_frames["quality_reason_counts"]),
                        "deviation_within_nominal_bounds": all_frames["deviation_within_nominal_bounds"],
                        "deviation_aggregate_pose_error": all_frames["deviation_aggregate_pose_error"],
                        "pitch_deg": all_frames["pitch_deg"],
                        "yaw_deg": all_frames["yaw_deg"],
                        "roll_deg": all_frames["roll_deg"],
                        "tx_mm": all_frames["tx_mm"],
                        "ty_mm": all_frames["ty_mm"],
                        "tz_mm": all_frames["tz_mm"],
                        "notes": " | ".join(report["notes"]),
                    }
                )
