from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Iterable

from .models import ExperimentRunResult


class Evaluator:
    def _acceptance_success(self, result: ExperimentRunResult) -> bool:
        return result.status in {"success", "accept_with_warning"}

    def _warning_accept(self, result: ExperimentRunResult) -> bool:
        return result.status == "accept_with_warning"

    def _clean_accept(self, result: ExperimentRunResult) -> bool:
        return result.status == "success"

    def _calibration_success(self, result: ExperimentRunResult) -> bool:
        return bool(result.calibration_result is not None and result.calibration_result.success)

    def compute_paper_metrics(self, results: list[ExperimentRunResult]) -> dict:
        by_run: dict[tuple[str, str, str, str], dict[str, ExperimentRunResult]] = defaultdict(dict)
        for r in results:
            by_run[(r.setup_type, r.dataset_split, r.scenario, r.run_id)][r.mode] = r

        acceptance_recovery_numerator = 0
        acceptance_recovery_denominator = 0
        acceptance_false_reject_numerator = 0
        acceptance_false_reject_denominator = 0
        calibration_recovery_numerator = 0
        calibration_recovery_denominator = 0
        calibration_false_reject_numerator = 0
        calibration_false_reject_denominator = 0

        for _run_key, modes in by_run.items():
            baseline = modes.get("baseline")
            if baseline is None:
                continue
            baseline_acceptance_success = self._acceptance_success(baseline)
            baseline_calibration_success = self._calibration_success(baseline)

            for mode, result in modes.items():
                if mode == "baseline":
                    continue
                controller_acceptance_success = self._acceptance_success(result)
                controller_calibration_success = self._calibration_success(result)

                if not baseline_acceptance_success:
                    acceptance_recovery_denominator += 1
                    if controller_acceptance_success:
                        acceptance_recovery_numerator += 1
                else:
                    acceptance_false_reject_denominator += 1
                    if not controller_acceptance_success:
                        acceptance_false_reject_numerator += 1

                if not baseline_calibration_success:
                    calibration_recovery_denominator += 1
                    if controller_calibration_success:
                        calibration_recovery_numerator += 1
                else:
                    calibration_false_reject_denominator += 1
                    if not controller_calibration_success:
                        calibration_false_reject_numerator += 1

        acceptance_recovery_rate = (
            None
            if acceptance_recovery_denominator == 0
            else round(acceptance_recovery_numerator / acceptance_recovery_denominator, 4)
        )
        acceptance_false_reject_rate = (
            None
            if acceptance_false_reject_denominator == 0
            else round(acceptance_false_reject_numerator / acceptance_false_reject_denominator, 4)
        )
        calibration_recovery_rate = (
            None
            if calibration_recovery_denominator == 0
            else round(calibration_recovery_numerator / calibration_recovery_denominator, 4)
        )
        calibration_false_reject_rate = (
            None
            if calibration_false_reject_denominator == 0
            else round(calibration_false_reject_numerator / calibration_false_reject_denominator, 4)
        )

        return {
            "recovery_rate": acceptance_recovery_rate,
            "false_reject_rate": acceptance_false_reject_rate,
            "recovery_numerator": acceptance_recovery_numerator,
            "recovery_denominator": acceptance_recovery_denominator,
            "false_reject_numerator": acceptance_false_reject_numerator,
            "false_reject_denominator": acceptance_false_reject_denominator,
            "acceptance_recovery_rate": acceptance_recovery_rate,
            "acceptance_false_reject_rate": acceptance_false_reject_rate,
            "acceptance_recovery_numerator": acceptance_recovery_numerator,
            "acceptance_recovery_denominator": acceptance_recovery_denominator,
            "acceptance_false_reject_numerator": acceptance_false_reject_numerator,
            "acceptance_false_reject_denominator": acceptance_false_reject_denominator,
            "calibration_recovery_rate": calibration_recovery_rate,
            "calibration_false_reject_rate": calibration_false_reject_rate,
            "calibration_recovery_numerator": calibration_recovery_numerator,
            "calibration_recovery_denominator": calibration_recovery_denominator,
            "calibration_false_reject_numerator": calibration_false_reject_numerator,
            "calibration_false_reject_denominator": calibration_false_reject_denominator,
        }

    def summarize_by_scenario(self, results: list[ExperimentRunResult]) -> dict:
        grouped: dict[tuple[str, str], list[ExperimentRunResult]] = defaultdict(list)
        for r in results:
            grouped[(r.scenario, r.mode)].append(r)

        scenarios: dict[str, dict[str, dict]] = defaultdict(dict)
        for (scenario, mode), items in grouped.items():
            acceptance_success_count = sum(1 for r in items if self._acceptance_success(r))
            clean_accept_count = sum(1 for r in items if self._clean_accept(r))
            warning_accept_count = sum(1 for r in items if self._warning_accept(r))
            calibration_success_count = sum(1 for r in items if self._calibration_success(r))
            total = len(items)
            reprojection_errors = [
                r.calibration_result.reprojection_error
                for r in items
                if r.calibration_result is not None and r.calibration_result.reprojection_error is not None
            ]
            retries = [r.retry_index for r in items]
            scenarios[scenario][mode] = {
                "runs": total,
                "success_rate": 0.0 if total == 0 else round(acceptance_success_count / total, 4),
                "acceptance_success_rate": 0.0 if total == 0 else round(acceptance_success_count / total, 4),
                "clean_accept_rate": 0.0 if total == 0 else round(clean_accept_count / total, 4),
                "warning_accept_rate": 0.0 if total == 0 else round(warning_accept_count / total, 4),
                "calibration_success_rate": 0.0 if total == 0 else round(calibration_success_count / total, 4),
                "acceptance_success_count": acceptance_success_count,
                "clean_accept_count": clean_accept_count,
                "warning_accept_count": warning_accept_count,
                "calibration_success_count": calibration_success_count,
                "mean_reprojection_error": None if not reprojection_errors else round(mean(reprojection_errors), 4),
                "mean_retries": 0.0 if not retries else round(mean(retries), 4),
            }
        return dict(scenarios)

    def summarize(self, results: list[ExperimentRunResult]) -> dict:
        grouped: dict[str, list[ExperimentRunResult]] = defaultdict(list)
        for result in results:
            grouped[result.mode].append(result)

        summary: dict[str, dict] = {}
        for mode, mode_results in grouped.items():
            acceptance_success_count = sum(1 for item in mode_results if self._acceptance_success(item))
            clean_accept_count = sum(1 for item in mode_results if self._clean_accept(item))
            warning_accept_count = sum(1 for item in mode_results if self._warning_accept(item))
            calibration_success_count = sum(1 for item in mode_results if self._calibration_success(item))
            total = len(mode_results)
            reprojection_errors = [
                item.calibration_result.reprojection_error
                for item in mode_results
                if item.calibration_result is not None and item.calibration_result.reprojection_error is not None
            ]
            retries = [item.retry_index for item in mode_results]
            summary[mode] = {
                "runs": total,
                "success_rate": 0.0 if total == 0 else acceptance_success_count / total,
                "acceptance_success_rate": 0.0 if total == 0 else acceptance_success_count / total,
                "clean_accept_rate": 0.0 if total == 0 else clean_accept_count / total,
                "warning_accept_rate": 0.0 if total == 0 else warning_accept_count / total,
                "calibration_success_rate": 0.0 if total == 0 else calibration_success_count / total,
                "acceptance_success_count": acceptance_success_count,
                "clean_accept_count": clean_accept_count,
                "warning_accept_count": warning_accept_count,
                "calibration_success_count": calibration_success_count,
                "mean_reprojection_error": None if not reprojection_errors else mean(reprojection_errors),
                "mean_retries": 0.0 if not retries else mean(retries),
            }
        return summary
