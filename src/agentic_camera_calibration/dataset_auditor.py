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
from .nominal_reference import (
    apply_nominal_reference as _apply_nominal_reference,
    canonicalize_scenario as _canonicalize_scenario,
    default_nominal_reference as _default_nominal_reference,
    derive_empirical_nominal_reference as _derive_empirical_nominal_reference,
    EmpiricalNominalEstimator,
    is_eligible_nominal_reference as _is_eligible_nominal_reference,
)
from .quality_analyzer import QualityAnalyzer


def _expected_run_ids() -> list[str]:
    return [f"run_{index:02d}" for index in range(1, 11)]


def _count_existing_runs(run_ids: list[str]) -> list[str]:
    existing = set(run_ids)
    return [run_id for run_id in _expected_run_ids() if run_id not in existing]



def _classify_run(
    canonical_scenario: str,
    setup_type: str,
    initial_metrics: dict,
    all_metrics: dict,
    metadata_present: bool,
    initial_frame_count: int,
    reserved_frame_count: int,
    required_primary_frame_count: int,
    required_reserved_frame_count: int,
    quality_floor_brightness: float,
) -> dict:
    notes: list[str] = []
    recapture_recommended = False

    if not metadata_present:
        notes.append("metadata.json missing or unreadable")
        recapture_recommended = True
    if initial_frame_count < required_primary_frame_count:
        notes.append(
            f"only {initial_frame_count} primary frames found; "
            f"expected at least {required_primary_frame_count} for {setup_type}"
        )
        recapture_recommended = True
    if reserved_frame_count < required_reserved_frame_count:
        notes.append(
            f"only {reserved_frame_count} reserved frames found; "
            f"expected at least {required_reserved_frame_count} for {setup_type}"
        )
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
        self.nominal_estimator = EmpiricalNominalEstimator(config)

    def audit_dataset(
        self,
        dataset_root: str | Path | None = None,
        output_dir: str | Path | None = None,
        setup_types: list[str] | None = None,
        dataset_splits: list[str] | None = None,
    ) -> dict:
        dataset_root = Path(dataset_root or self.config.dataset_root)
        output_dir = Path(output_dir or (self.config.results_root / "dataset_audit"))
        runs = self._filter_runs(
            self.loader.discover_runs(dataset_root),
            setup_types=setup_types,
            dataset_splits=dataset_splits,
        )

        preliminary_reports = [self._collect_run_metrics(run) for run in runs]
        nominal_reference = self.nominal_estimator.derive_for_dataset(runs=runs)
        run_reports = [self._finalize_run_report(report, nominal_reference) for report in preliminary_reports]
        scenario_summary = self._summarize_scenarios(run_reports)
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset_root": str(dataset_root),
            "selected_setup_types": list(setup_types or []),
            "selected_dataset_splits": list(dataset_splits or []),
            "run_count": len(run_reports),
            "nominal_reference": nominal_reference,
            "scenario_summary": scenario_summary,
            "setup_summary": self._summarize_setup_types(run_reports),
            "split_summary": self._summarize_dataset_splits(run_reports),
            "runs": run_reports,
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "dataset_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (output_dir / "dataset_audit.md").write_text(self._build_markdown_report(report), encoding="utf-8")
        self._write_csv_report(output_dir / "dataset_audit.csv", run_reports)
        return report

    def _collect_run_metrics(self, run) -> dict:
        initial_frames, reserved_frames = self.loader.split_initial_and_reserved(run.frames)
        initial_metrics = self._analyze_frames(initial_frames)
        all_metrics = self._analyze_frames(run.frames)

        return {
            "scenario": run.scenario,
            "canonical_scenario": _canonicalize_scenario(run.scenario),
            "run_id": run.run_id,
            "setup_type": run.setup_type,
            "dataset_split": run.dataset_split,
            "run_path": str(run.run_path),
            "metadata_present": bool(run.metadata),
            "primary_frame_count": len(initial_frames),
            "reserved_frame_count": len(reserved_frames),
            "initial_metrics": initial_metrics,
            "all_frame_metrics": all_metrics,
        }

    def _finalize_run_report(self, report: dict, nominal_reference: dict) -> dict:
        initial_metrics = _apply_nominal_reference(
            report["initial_metrics"],
            nominal_reference,
            self.config.failure,
        )
        all_metrics = _apply_nominal_reference(
            report["all_frame_metrics"],
            nominal_reference,
            self.config.failure,
        )
        required_primary_frame_count, required_reserved_frame_count = self._required_frame_counts(
            report["setup_type"]
        )
        classification = _classify_run(
            canonical_scenario=report["canonical_scenario"],
            setup_type=report["setup_type"],
            initial_metrics=initial_metrics,
            all_metrics=all_metrics,
            metadata_present=report["metadata_present"],
            initial_frame_count=report["primary_frame_count"],
            reserved_frame_count=report["reserved_frame_count"],
            required_primary_frame_count=required_primary_frame_count,
            required_reserved_frame_count=required_reserved_frame_count,
            quality_floor_brightness=self.config.quality.min_brightness,
        )

        finalized_report = dict(report)
        finalized_report["initial_metrics"] = initial_metrics
        finalized_report["all_frame_metrics"] = all_metrics
        finalized_report["required_primary_frame_count"] = required_primary_frame_count
        finalized_report["required_reserved_frame_count"] = required_reserved_frame_count
        finalized_report.update(classification)
        return finalized_report

    def _required_frame_counts(self, setup_type: str) -> tuple[int, int]:
        if setup_type.casefold() == "benchmark_fixed_target":
            return (
                self.config.experiment.fixed_target_audit_min_primary_frames,
                self.config.experiment.fixed_target_audit_min_reserved_frames,
            )
        return (
            self.config.experiment.audit_min_primary_frames,
            self.config.experiment.audit_min_reserved_frames,
        )

    def _analyze_frames(self, frames: list) -> dict:
        detections = [self.detector.detect(frame) for frame in frames]
        quality_metrics = [self.quality_analyzer.analyze(frame) for frame in frames]
        calibration = self.calibration_engine.calibrate(frames, detections)
        absolute_pose = None
        if calibration.success:
            absolute_pose = self.deviation_analyzer.compute_deviation(
                calibration,
                nominal_pose=self.config.nominal_pose.__class__(
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
            "estimated_pitch_deg": None if absolute_pose is None else round(absolute_pose.pitch_deg, 3),
            "estimated_yaw_deg": None if absolute_pose is None else round(absolute_pose.yaw_deg, 3),
            "estimated_roll_deg": None if absolute_pose is None else round(absolute_pose.roll_deg, 3),
            "estimated_tx_mm": None if absolute_pose is None else round(absolute_pose.tx_mm, 3),
            "estimated_ty_mm": None if absolute_pose is None else round(absolute_pose.ty_mm, 3),
            "estimated_tz_mm": None if absolute_pose is None else round(absolute_pose.tz_mm, 3),
            "nominal_reference_source": "config_defaults",
            "nominal_reference_run_count": 0,
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

    def _summarize_setup_types(self, run_reports: list[dict]) -> list[dict]:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for report in run_reports:
            grouped[report["setup_type"]].append(report)

        summaries: list[dict] = []
        for setup_type, reports in sorted(grouped.items()):
            statuses = Counter(report["status"] for report in reports)
            usable_count = sum(1 for report in reports if report["usable_for_analysis"])
            summaries.append(
                {
                    "setup_type": setup_type,
                    "runs_found": len(reports),
                    "usable_runs": usable_count,
                    "keep_runs": statuses.get("keep", 0),
                    "keep_with_note_runs": statuses.get("keep_with_note", 0),
                    "recapture_runs": statuses.get("recapture", 0),
                }
            )
        return summaries

    def _summarize_dataset_splits(self, run_reports: list[dict]) -> list[dict]:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for report in run_reports:
            grouped[report["dataset_split"]].append(report)

        summaries: list[dict] = []
        for dataset_split, reports in sorted(grouped.items()):
            statuses = Counter(report["status"] for report in reports)
            usable_count = sum(1 for report in reports if report["usable_for_analysis"])
            summaries.append(
                {
                    "dataset_split": dataset_split,
                    "runs_found": len(reports),
                    "usable_runs": usable_count,
                    "keep_runs": statuses.get("keep", 0),
                    "keep_with_note_runs": statuses.get("keep_with_note", 0),
                    "recapture_runs": statuses.get("recapture", 0),
                }
            )
        return summaries

    def _filter_runs(
        self,
        runs: list,
        setup_types: list[str] | None = None,
        dataset_splits: list[str] | None = None,
    ) -> list:
        setup_type_filter = {item.casefold() for item in setup_types or []}
        dataset_split_filter = {item.casefold() for item in dataset_splits or []}

        filtered = [
            run
            for run in runs
            if (not setup_type_filter or run.setup_type.casefold() in setup_type_filter)
            and (not dataset_split_filter or run.dataset_split.casefold() in dataset_split_filter)
        ]
        if not filtered:
            raise ValueError("No dataset runs matched the provided --setup-type/--dataset-split filters.")
        return filtered

    def _build_markdown_report(self, report: dict) -> str:
        lines: list[str] = []
        lines.append("# Dataset Audit Report")
        lines.append("")
        lines.append(f"- Generated: `{report['generated_at']}`")
        lines.append(f"- Dataset root: `{report['dataset_root']}`")
        lines.append(f"- Runs audited: `{report['run_count']}`")
        if report["selected_setup_types"]:
            lines.append(f"- Setup type filter: `{', '.join(report['selected_setup_types'])}`")
        if report["selected_dataset_splits"]:
            lines.append(f"- Dataset split filter: `{', '.join(report['selected_dataset_splits'])}`")
        lines.append("")
        lines.append("## Nominal Reference")
        lines.append("")
        nominal_reference = report["nominal_reference"]
        lines.append(f"- Source: `{nominal_reference['source']}`")
        lines.append(f"- Derived from: `{nominal_reference['derived_from']}`")
        if nominal_reference["run_ids"]:
            lines.append(f"- Runs used: `{', '.join(nominal_reference['run_ids'])}`")
        lines.append(
            f"- Reference pose: pitch `{nominal_reference['pitch_deg']}`, yaw `{nominal_reference['yaw_deg']}`, "
            f"roll `{nominal_reference['roll_deg']}`, tx `{nominal_reference['tx_mm']}` mm, "
            f"ty `{nominal_reference['ty_mm']}` mm, tz `{nominal_reference['tz_mm']}` mm"
        )
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
        lines.append("")
        lines.append("## Setup Summary")
        lines.append("")
        lines.append("| Setup Type | Runs Found | Usable | Keep | Keep With Note | Recapture |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for item in report["setup_summary"]:
            lines.append(
                f"| {item['setup_type']} | {item['runs_found']} | {item['usable_runs']} | "
                f"{item['keep_runs']} | {item['keep_with_note_runs']} | {item['recapture_runs']} |"
            )
        lines.append("")
        lines.append("## Split Summary")
        lines.append("")
        lines.append("| Dataset Split | Runs Found | Usable | Keep | Keep With Note | Recapture |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for item in report["split_summary"]:
            lines.append(
                f"| {item['dataset_split']} | {item['runs_found']} | {item['usable_runs']} | "
                f"{item['keep_runs']} | {item['keep_with_note_runs']} | {item['recapture_runs']} |"
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
                lines.append(f"- Setup type: `{run_report['setup_type']}`")
                lines.append(f"- Dataset split: `{run_report['dataset_split']}`")
                lines.append(f"- Usable for analysis: `{run_report['usable_for_analysis']}`")
                lines.append(f"- Recapture recommended: `{run_report['recapture_recommended']}`")
                lines.append(f"- Primary / reserved frames: `{run_report['primary_frame_count']}` / `{run_report['reserved_frame_count']}`")
                lines.append(
                    f"- Required primary / reserved minimum: "
                    f"`{run_report['required_primary_frame_count']}` / `{run_report['required_reserved_frame_count']}`"
                )
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
                if all_frames["estimated_tz_mm"] is not None:
                    lines.append(
                        f"- Pose estimate vs `{all_frames['nominal_reference_source']}`: "
                        f"pitch `{all_frames['pitch_deg']}`, yaw `{all_frames['yaw_deg']}`, "
                        f"roll `{all_frames['roll_deg']}`, tx `{all_frames['tx_mm']}` mm, "
                        f"ty `{all_frames['ty_mm']}` mm, tz `{all_frames['tz_mm']}` mm"
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
            "setup_type",
            "dataset_split",
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
            "estimated_pitch_deg",
            "estimated_yaw_deg",
            "estimated_roll_deg",
            "estimated_tx_mm",
            "estimated_ty_mm",
            "estimated_tz_mm",
            "nominal_reference_source",
            "nominal_reference_run_count",
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
                        "setup_type": report["setup_type"],
                        "dataset_split": report["dataset_split"],
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
                        "estimated_pitch_deg": all_frames["estimated_pitch_deg"],
                        "estimated_yaw_deg": all_frames["estimated_yaw_deg"],
                        "estimated_roll_deg": all_frames["estimated_roll_deg"],
                        "estimated_tx_mm": all_frames["estimated_tx_mm"],
                        "estimated_ty_mm": all_frames["estimated_ty_mm"],
                        "estimated_tz_mm": all_frames["estimated_tz_mm"],
                        "nominal_reference_source": all_frames["nominal_reference_source"],
                        "nominal_reference_run_count": all_frames["nominal_reference_run_count"],
                        "notes": " | ".join(report["notes"]),
                    }
                )
