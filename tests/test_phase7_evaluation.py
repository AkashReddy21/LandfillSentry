import os
import shutil
import tempfile
import unittest
from pathlib import Path

from ml.evaluation.phase7_harness import Phase7EvaluationHarness


class Phase7EvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ls_phase7_eval_test_"))
        self.old_env = os.environ.copy()
        os.environ["HF_ADAPTER_ID"] = "landfillsentry/lfm25vl450m-lora-v1"

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_evaluation_harness_outputs_three_model_comparison(self) -> None:
        harness = Phase7EvaluationHarness(project_root=Path(__file__).resolve().parents[1])
        report = harness.run()

        self.assertEqual(report["report_version"], "phase7.evaluation.v2")
        self.assertEqual(
            report["models_compared"],
            ["heuristic", "base_model", "fine_tuned_model"],
        )
        self.assertEqual(len(report["records"]), 3)
        self.assertIn("comparison_table_markdown", report)
        self.assertIn("| Model | JSON Valid |", report["comparison_table_markdown"])

        null_scene = report["null_scene_report"]
        self.assertIn("heuristic", null_scene)
        self.assertIn("base_model", null_scene)
        self.assertIn("fine_tuned_model", null_scene)

        rubric = report["human_rubric"]
        self.assertIn("criteria", rubric)
        self.assertIn("model_rows", rubric)

        summary = report["validation_summary"]
        self.assertEqual(summary["sample_count_per_model"], 12)
        self.assertEqual(summary["fixture_repeats_per_class"], 4)
        self.assertEqual(summary["validation_strength"], "moderate")
        self.assertTrue(summary["fine_tuned_passes_quality_gates"])
        self.assertGreaterEqual(summary["deltas_vs_base_model"]["incident_f1"], 0.1)

        diagnostics = report["model_diagnostics"]
        self.assertEqual(diagnostics["fine_tuned_model"]["sample_count"], 12)
        self.assertIn("confusion_matrix", diagnostics["base_model"])
        self.assertIn("confidence_intervals", diagnostics["base_model"])
        self.assertIn("quality_gates", diagnostics["fine_tuned_model"])
        self.assertTrue(diagnostics["fine_tuned_model"]["quality_gates"]["passed"])


if __name__ == "__main__":
    unittest.main()
