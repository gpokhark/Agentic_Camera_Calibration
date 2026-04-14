from __future__ import annotations

from collections import defaultdict
from statistics import mean

from .models import ExperimentRunResult


class Evaluator:
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
