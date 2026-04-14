from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .config import CalibrationConfig
from .controllers import AgentController, HeuristicController
from .dataset_loader import DatasetLoader
from .evaluator import Evaluator
from .models import ExperimentRunResult
from .orchestrator import CalibrationOrchestrator
from .reporter import Reporter


class ExperimentRunner:
    def __init__(self, config: CalibrationConfig) -> None:
        self.config = config
        self.loader = DatasetLoader(config)
        self.orchestrator = CalibrationOrchestrator(config)
        self.heuristic_controller = HeuristicController(config.controller)
        self.agent_controller = AgentController(config.controller)
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

        results: list[ExperimentRunResult] = []
        for run in runs:
            initial_frames, reserved_frames = self.loader.split_initial_and_reserved(run.frames)

            results.append(
                self.orchestrator.run(
                    initial_frames=deepcopy(initial_frames),
                    reserved_frames=deepcopy(reserved_frames),
                    controller=None,
                    run_id=run.run_id,
                    scenario=run.scenario,
                    mode_name="baseline",
                )
            )
            results.append(
                self.orchestrator.run(
                    initial_frames=deepcopy(initial_frames),
                    reserved_frames=deepcopy(reserved_frames),
                    controller=self.heuristic_controller,
                    run_id=run.run_id,
                    scenario=run.scenario,
                    mode_name="heuristic",
                )
            )
            results.append(
                self.orchestrator.run(
                    initial_frames=deepcopy(initial_frames),
                    reserved_frames=deepcopy(reserved_frames),
                    controller=self.agent_controller,
                    run_id=run.run_id,
                    scenario=run.scenario,
                    mode_name="agent",
                )
            )

        summary = self.evaluator.summarize(results)
        self.reporter.write_results(output_dir, results, summary)
        return results
