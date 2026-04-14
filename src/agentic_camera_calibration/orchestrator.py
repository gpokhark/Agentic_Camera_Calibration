from __future__ import annotations

from statistics import mean

from .calibration_engine import CalibrationEngine
from .charuco_detector import CharucoDetector
from .config import CalibrationConfig
from .controllers.base import RecoveryController
from .deviation_analyzer import DeviationAnalyzer
from .failure_detector import FailureDetector
from .models import ControllerState, DetectionResult, ExperimentRunResult, FrameRecord, QualityMetrics
from .quality_analyzer import QualityAnalyzer
from .recovery_executor import RecoveryExecutor


class CalibrationOrchestrator:
    def __init__(self, config: CalibrationConfig) -> None:
        self.config = config
        self.detector = CharucoDetector(config.board)
        self.quality_analyzer = QualityAnalyzer(config.quality)
        self.calibration_engine = CalibrationEngine(self.detector, config.failure)
        self.deviation_analyzer = DeviationAnalyzer(config.failure)
        self.failure_detector = FailureDetector(config.failure, config.quality)
        self.recovery_executor = RecoveryExecutor()

    def run(
        self,
        initial_frames: list[FrameRecord],
        reserved_frames: list[FrameRecord],
        controller: RecoveryController | None,
        run_id: str,
        scenario: str,
        mode_name: str,
    ) -> ExperimentRunResult:
        active_frames = list(initial_frames)
        reserve_pool = list(reserved_frames)
        attempted_actions: list[dict] = []
        pose_margin_scale = 1.0

        for retry_index in range(self.config.experiment.max_retries + 1):
            detections = [self.detector.detect(frame) for frame in active_frames]
            quality = [self.quality_analyzer.analyze(frame) for frame in active_frames]

            calibration_result = self.calibration_engine.calibrate(active_frames, detections)
            deviation = None
            if calibration_result.success:
                deviation = self.deviation_analyzer.compute_deviation(
                    calibration_result,
                    self.config.nominal_pose,
                    pose_margin_scale=pose_margin_scale,
                )

            failure_eval = self.failure_detector.evaluate(
                calibration_result,
                deviation,
                quality,
                detections,
            )

            if failure_eval.status == "pass":
                return ExperimentRunResult(
                    mode=mode_name,
                    status="success",
                    run_id=run_id,
                    scenario=scenario,
                    retry_index=retry_index,
                    calibration_result=calibration_result,
                    deviation_result=deviation,
                    attempted_actions=attempted_actions,
                )

            if controller is None or retry_index == self.config.experiment.max_retries:
                return ExperimentRunResult(
                    mode=mode_name,
                    status="failed",
                    run_id=run_id,
                    scenario=scenario,
                    retry_index=retry_index,
                    calibration_result=calibration_result,
                    deviation_result=deviation,
                    attempted_actions=attempted_actions,
                    reason_codes=failure_eval.reason_codes,
                )

            state = self._build_controller_state(
                run_id=run_id,
                scenario=scenario,
                retry_index=retry_index,
                active_frames=active_frames,
                reserved_frames=reserve_pool,
                detections=detections,
                quality_metrics=quality,
                calibration_success=calibration_result.success,
                reprojection_error=calibration_result.reprojection_error,
                deviation=deviation,
                reason_codes=failure_eval.reason_codes,
                attempted_actions=attempted_actions,
            )

            decision = controller.decide(state)
            if decision.declare_unrecoverable:
                return ExperimentRunResult(
                    mode=mode_name,
                    status="failed_unrecoverable",
                    run_id=run_id,
                    scenario=scenario,
                    retry_index=retry_index,
                    attempted_actions=attempted_actions,
                    reason_codes=failure_eval.reason_codes,
                    decision=decision,
                )

            active_frames, reserve_pool, execution_log = self.recovery_executor.execute(
                decision,
                active_frames,
                reserve_pool,
                detections,
                quality,
            )
            pose_margin_scale = min(
                self.config.failure.max_pose_margin_scale,
                float(execution_log.get("state_updates", {}).get("pose_margin_scale", pose_margin_scale)),
            )
            attempted_actions.append(
                {
                    "retry_index": retry_index,
                    "reason_codes": list(failure_eval.reason_codes),
                    "decision": decision,
                    "execution": execution_log,
                }
            )

        return ExperimentRunResult(
            mode=mode_name,
            status="failed",
            run_id=run_id,
            scenario=scenario,
            retry_index=self.config.experiment.max_retries,
            attempted_actions=attempted_actions,
        )

    def _build_controller_state(
        self,
        run_id: str,
        scenario: str,
        retry_index: int,
        active_frames: list[FrameRecord],
        reserved_frames: list[FrameRecord],
        detections: list[DetectionResult],
        quality_metrics: list[QualityMetrics],
        calibration_success: bool,
        reprojection_error: float | None,
        deviation,
        reason_codes: list[str],
        attempted_actions: list[dict],
    ) -> ControllerState:
        mean_brightness = mean(metric.mean_brightness for metric in quality_metrics) if quality_metrics else 0.0
        mean_saturation_ratio = mean(metric.saturation_ratio for metric in quality_metrics) if quality_metrics else 0.0
        mean_blur_score = mean(metric.blur_score for metric in quality_metrics) if quality_metrics else 0.0
        mean_glare_score = mean(metric.glare_score for metric in quality_metrics) if quality_metrics else 0.0
        successful_detections = [item for item in detections if item.detection_success]
        mean_marker_count = mean(item.markers_detected for item in successful_detections) if successful_detections else 0.0
        mean_charuco_corner_count = (
            mean(item.charuco_corners_detected for item in successful_detections)
            if successful_detections
            else 0.0
        )
        mean_coverage_score = mean(item.coverage_score for item in successful_detections) if successful_detections else 0.0

        return ControllerState(
            run_id=run_id,
            scenario=scenario,
            retry_index=retry_index,
            frames_total=len(active_frames) + len(reserved_frames),
            frames_active=len(active_frames),
            frames_reserved_remaining=len(reserved_frames),
            mean_brightness=mean_brightness,
            mean_saturation_ratio=mean_saturation_ratio,
            mean_blur_score=mean_blur_score,
            mean_glare_score=mean_glare_score,
            mean_marker_count=mean_marker_count,
            mean_charuco_corner_count=mean_charuco_corner_count,
            mean_coverage_score=mean_coverage_score,
            calibration_success=calibration_success,
            reprojection_error=reprojection_error,
            deviation_result=deviation,
            reason_codes=reason_codes,
            attempted_actions=attempted_actions,
            allowed_actions=list(self.config.controller.allowed_actions),
        )
