from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .config import CalibrationConfig
from .controllers import AgentController, HeuristicController, LearnedController
from .dataset_loader import DatasetLoader
from .evaluator import Evaluator
from .models import ExperimentRunResult
from .nominal_reference import EmpiricalNominalEstimator, nominal_reference_to_config
from .orchestrator import CalibrationOrchestrator
from .reporter import Reporter


class ExperimentRunner:
    def __init__(self, config: CalibrationConfig) -> None:
        self.config = config
        self.loader = DatasetLoader(config)
        self.nominal_estimator = EmpiricalNominalEstimator(config)
        self.evaluator = Evaluator()
        self.reporter = Reporter()

    def run_all(
        self,
        dataset_root: str | Path | None = None,
        output_dir: str | Path | None = None,
        scenarios: list[str] | None = None,
        run_ids: list[str] | None = None,
        modes: list[str] | None = None,
        setup_types: list[str] | None = None,
        dataset_splits: list[str] | None = None,
    ) -> list[ExperimentRunResult]:
        dataset_root = Path(dataset_root or self.config.dataset_root)
        output_dir = Path(output_dir or self.config.results_root)
        all_runs = self.loader.discover_runs(dataset_root)
        nominal_reference = self.nominal_estimator.derive_for_dataset(runs=all_runs)
        runs = self._filter_runs(
            all_runs,
            scenarios=scenarios,
            run_ids=run_ids,
            setup_types=setup_types,
            dataset_splits=dataset_splits,
        )
        selected_modes = self._normalize_modes(modes)

        effective_config = deepcopy(self.config)
        effective_config.nominal_pose = nominal_reference_to_config(nominal_reference)
        orchestrator = CalibrationOrchestrator(effective_config)
        heuristic_controller = HeuristicController(effective_config.controller)
        learned_controller = LearnedController(effective_config.controller) if "learned" in selected_modes else None
        agent_controller = AgentController(effective_config.controller) if "agent" in selected_modes else None

        results: list[ExperimentRunResult] = []
        for run in runs:
            initial_frames, reserved_frames = self.loader.split_initial_and_reserved(run.frames)

            if "baseline" in selected_modes:
                results.append(
                    orchestrator.run(
                        initial_frames=deepcopy(initial_frames),
                        reserved_frames=deepcopy(reserved_frames),
                        controller=None,
                        run_id=run.run_id,
                        scenario=run.scenario,
                        setup_type=run.setup_type,
                        dataset_split=run.dataset_split,
                        mode_name="baseline",
                    )
                )
            if "heuristic" in selected_modes:
                results.append(
                    orchestrator.run(
                        initial_frames=deepcopy(initial_frames),
                        reserved_frames=deepcopy(reserved_frames),
                        controller=heuristic_controller,
                        run_id=run.run_id,
                        scenario=run.scenario,
                        setup_type=run.setup_type,
                        dataset_split=run.dataset_split,
                        mode_name="heuristic",
                    )
                )
            if "learned" in selected_modes and learned_controller is not None:
                results.append(
                    orchestrator.run(
                        initial_frames=deepcopy(initial_frames),
                        reserved_frames=deepcopy(reserved_frames),
                        controller=learned_controller,
                        run_id=run.run_id,
                        scenario=run.scenario,
                        setup_type=run.setup_type,
                        dataset_split=run.dataset_split,
                        mode_name="learned",
                    )
                )
            if "agent" in selected_modes and agent_controller is not None:
                results.append(
                    orchestrator.run(
                        initial_frames=deepcopy(initial_frames),
                        reserved_frames=deepcopy(reserved_frames),
                        controller=agent_controller,
                        run_id=run.run_id,
                        scenario=run.scenario,
                        setup_type=run.setup_type,
                        dataset_split=run.dataset_split,
                        mode_name="agent",
                    )
                )

        summary = self.evaluator.summarize(results)
        paper_metrics = self.evaluator.compute_paper_metrics(results)
        scenario_summary = self.evaluator.summarize_by_scenario(results)
        self.reporter.write_results(output_dir, results, summary, paper_metrics=paper_metrics, scenario_summary=scenario_summary)
        (output_dir / "nominal_reference.json").write_text(
            json.dumps(nominal_reference, indent=2),
            encoding="utf-8",
        )
        return results

    def _filter_runs(
        self,
        runs: list,
        scenarios: list[str] | None = None,
        run_ids: list[str] | None = None,
        setup_types: list[str] | None = None,
        dataset_splits: list[str] | None = None,
    ) -> list:
        scenario_filter = {item.casefold() for item in scenarios or []}
        run_id_filter = {item.casefold() for item in run_ids or []}
        setup_type_filter = {item.casefold() for item in setup_types or []}
        dataset_split_filter = {item.casefold() for item in dataset_splits or []}

        filtered = [
            run
            for run in runs
            if (not scenario_filter or run.scenario.casefold() in scenario_filter)
            and (not run_id_filter or run.run_id.casefold() in run_id_filter)
            and (not setup_type_filter or run.setup_type.casefold() in setup_type_filter)
            and (not dataset_split_filter or run.dataset_split.casefold() in dataset_split_filter)
        ]
        if not filtered:
            raise ValueError(
                "No dataset runs matched the provided --scenario/--run-id/--setup-type/--dataset-split filters."
            )
        return filtered

    def _normalize_modes(self, modes: list[str] | None) -> list[str]:
        requested = [mode.casefold() for mode in (modes or ["baseline", "heuristic", "learned", "agent"])]
        allowed = {"baseline", "heuristic", "learned", "agent"}
        invalid = [mode for mode in requested if mode not in allowed]
        if invalid:
            raise ValueError(f"Unsupported experiment mode(s): {', '.join(invalid)}")

        ordered: list[str] = []
        for mode in requested:
            if mode not in ordered:
                ordered.append(mode)
        if not ordered:
            raise ValueError("At least one experiment mode must be selected.")
        return ordered
