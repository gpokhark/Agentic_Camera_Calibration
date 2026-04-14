from __future__ import annotations

import json
from pathlib import Path

from .models import ExperimentRunResult, to_jsonable


class Reporter:
    def write_results(self, output_dir: str | Path, results: list[ExperimentRunResult], summary: dict) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "results.json").write_text(
            json.dumps([to_jsonable(result) for result in results], indent=2),
            encoding="utf-8",
        )
        (output_path / "summary.json").write_text(
            json.dumps(to_jsonable(summary), indent=2),
            encoding="utf-8",
        )
