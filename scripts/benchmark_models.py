"""Run Phase 7 evaluation harness and reliability checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.evaluation.phase7_harness import Phase7EvaluationHarness
from ml.evaluation.reliability_harness import ReliabilityHarness


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    import os

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    _load_env_file(PROJECT_ROOT / ".env.local")

    output_dir = PROJECT_ROOT / "data" / "manifests"
    evaluation_report_path = output_dir / "phase7_evaluation_report.json"
    null_scene_report_path = output_dir / "phase7_null_scene_report.json"
    reliability_report_path = output_dir / "phase7_reliability_report.json"
    rubric_path = output_dir / "phase7_human_actionability_rubric_v1.json"
    comparison_table_path = output_dir / "phase7_baseline_comparison.md"

    evaluator = Phase7EvaluationHarness(project_root=PROJECT_ROOT)
    evaluation_report = evaluator.run()
    reliability_report = ReliabilityHarness().run_all()

    null_scene_report = {
        "report_version": "phase7.null_scene.v2",
        "generated_at": evaluation_report["generated_at"],
        "models": evaluation_report["null_scene_report"],
        "confidence_intervals": {
            model_key: diagnostics["confidence_intervals"]["null_false_positive_rate"]
            for model_key, diagnostics in evaluation_report["model_diagnostics"].items()
        },
    }
    rubric_doc = {
        "rubric_version": "phase7.human_actionability.v1",
        "generated_at": evaluation_report["generated_at"],
        "criteria": evaluation_report["human_rubric"]["criteria"],
        "model_rows": evaluation_report["human_rubric"]["model_rows"],
    }

    _write_json(evaluation_report_path, evaluation_report)
    _write_json(null_scene_report_path, null_scene_report)
    _write_json(reliability_report_path, reliability_report)
    _write_json(rubric_path, rubric_doc)
    comparison_table_path.write_text(evaluation_report["comparison_table_markdown"], encoding="utf-8")

    print("Phase 7 evaluation complete:")
    print(f"- Evaluation report: {evaluation_report_path}")
    print(f"- Baseline comparison table: {comparison_table_path}")
    print(f"- Null-scene report: {null_scene_report_path}")
    print(f"- Human rubric: {rubric_path}")
    print(f"- Reliability report: {reliability_report_path}")


if __name__ == "__main__":
    main()
