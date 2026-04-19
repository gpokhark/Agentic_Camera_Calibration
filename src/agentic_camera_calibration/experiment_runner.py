from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .config import CalibrationConfig
from .controllers import AgentController, HeuristicController
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
    ) -> list[ExperimentRunResult]:
        dataset_root = Path(dataset_root or self.config.dataset_root)
        output_dir = Path(output_dir or self.config.results_root)
        runs = self.loader.discover_runs(dataset_root)
        nominal_reference = self.nominal_estimator.derive_for_dataset(runs=runs)

        effective_config = deepcopy(self.config)
        effective_config.nominal_pose = nominal_reference_to_config(nominal_reference)
        orchestrator = CalibrationOrchestrator(effective_config)
        heuristic_controller = HeuristicController(effective_config.controller)
        agent_controller = AgentController(effective_config.controller)

        results: list[ExperimentRunResult] = []
        for run in runs:
            initial_frames, reserved_frames = self.loader.split_initial_and_reserved(run.frames)

            results.append(
                orchestrator.run(
                    initial_frames=deepcopy(initial_frames),
                    reserved_frames=deepcopy(reserved_frames),
                    controller=None,
                    run_id=run.run_id,
                    scenario=run.scenario,
                    mode_name="baseline",
                )
            )
            results.append(
                orchestrator.run(
                    initial_frames=deepcopy(initial_frames),
                    reserved_frames=deepcopy(reserved_frames),
                    controller=heuristic_controller,
                    run_id=run.run_id,
                    scenario=run.scenario,
                    mode_name="heuristic",
                )
            )
            results.append(
                orchestrator.run(
                    initial_frames=deepcopy(initial_frames),
                    reserved_frames=deepcopy(reserved_frames),
                    controller=agent_controller,
                    run_id=run.run_id,
                    scenario=run.scenario,
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
