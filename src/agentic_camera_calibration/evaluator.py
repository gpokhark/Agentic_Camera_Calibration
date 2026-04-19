from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Iterable

from .models import ExperimentRunResult


class Evaluator:
    def compute_paper_metrics(self, results: list[ExperimentRunResult]) -> dict:
        by_run: dict[str, dict[str, ExperimentRunResult]] = defaultdict(dict)
        for r in results:
            by_run[r.run_id][r.mode] = r

        recovery_numerator = 0
        recovery_denominator = 0
        false_reject_numerator = 0
        false_reject_denominator = 0

        for _run_id, modes in by_run.items():
            baseline = modes.get("baseline")
            if baseline is None:
                continue
            baseline_success = baseline.status == "success"

            for mode, result in modes.items():
                if mode == "baseline":
                    continue
                controller_success = result.status == "success"
                if not baseline_success:
                    recovery_denominator += 1
                    if controller_success:
                        recovery_numerator += 1
                else:
                    false_reject_denominator += 1
                    if not controller_success:
                        false_reject_numerator += 1

        return {
            "recovery_rate": (
                None if recovery_denominator == 0
                else round(recovery_numerator / recovery_denominator, 4)
            ),
            "false_reject_rate": (
                None if false_reject_denominator == 0
                else round(false_reject_numerator / false_reject_denominator, 4)
            ),
            "recovery_numerator": recovery_numerator,
            "recovery_denominator": recovery_denominator,
            "false_reject_numerator": false_reject_numerator,
            "false_reject_denominator": false_reject_denominator,
        }

    def summarize_by_scenario(self, results: list[ExperimentRunResult]) -> dict:
        grouped: dict[tuple[str, str], list[ExperimentRunResult]] = defaultdict(list)
        for r in results:
            grouped[(r.scenario, r.mode)].append(r)

        scenarios: dict[str, dict[str, dict]] = defaultdict(dict)
        for (scenario, mode), items in grouped.items():
            success_count = sum(1 for r in items if r.status == "success")
            total = len(items)
            reprojection_errors = [
                r.calibration_result.reprojection_error
                for r in items
                if r.calibration_result is not None and r.calibration_result.reprojection_error is not None
            ]
            retries = [r.retry_index for r in items]
            scenarios[scenario][mode] = {
                "runs": total,
                "success_rate": 0.0 if total == 0 else round(success_count / total, 4),
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
            success_count = sum(1 for item in mode_results if item.status == "success")
            total = len(mode_results)
            reprojection_errors = [
                item.calibration_result.reprojection_error
                for item in mode_results
                if item.calibration_result is not None and item.calibration_result.reprojection_error is not None
            ]
            retries = [item.retry_index for item in mode_results]
            summary[mode] = {
                "runs": total,
                "success_rate": 0.0 if total == 0 else success_count / total,
                "mean_reprojection_error": None if not reprojection_errors else mean(reprojection_errors),
                "mean_retries": 0.0 if not retries else mean(retries),
            }
        return summary
