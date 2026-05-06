import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from apps.api.routes.api import get_scan_evidence, register_site, scan_site
from apps.api.runtime import reset_runtime_caches
from apps.api.schemas import ScanRequest, Site
from ml.training.dataset_manifest import build_dataset_manifest
from ml.training.lora_artifacts import create_training_artifacts


class Phase6TrainingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ls_phase6_"))
        self.db_path = self.tmpdir / "landfillsentry.db"
        self.cache_root = self.tmpdir / "cache"
        self.old_env = os.environ.copy()

        os.environ["LS_DB_PATH"] = str(self.db_path)
        os.environ["LS_CACHE_ROOT"] = str(self.cache_root)
        os.environ["SIMSAT_MODE"] = "mock"
        os.environ["MAPBOX_MODE"] = "mock"
        os.environ["INFERENCE_MODE"] = "mock"
        os.environ["REQUIRE_LIVE_RESULTS"] = "false"
        os.environ["HF_MODEL_ID"] = "LiquidAI/LFM2.5-VL-450M"
        os.environ["HF_MODEL_REVISION"] = "main"
        os.environ["HF_ADAPTER_ID"] = "landfillsentry/lfm25vl450m-lora-v1"
        os.environ["HF_ADAPTER_REVISION"] = "main"
        reset_runtime_caches()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)
        reset_runtime_caches()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _site(self, site_id: str, fixture_class: str = "positive") -> Site:
        return Site(
            site_id=site_id,
            name=site_id,
            lat=22.5726,
            lon=88.3639,
            country="IN",
            operator="Demo Operator",
            watchlist_enabled=True,
            polygon_geojson=None,
            metadata={"fixture_class": fixture_class},
        )

    def test_dataset_manifest_build_includes_provenance_and_frozen_splits(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        labels = project_root / "data" / "labels" / "phase6_samples_v1.jsonl"
        manifest_path = self.tmpdir / "dataset_manifest_v1.json"
        split_path = self.tmpdir / "dataset_splits_v1.json"

        result = build_dataset_manifest(labels, manifest_path, split_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        splits = json.loads(split_path.read_text(encoding="utf-8"))

        self.assertEqual(result.sample_count, 10)
        self.assertEqual(manifest["manifest_version"], "phase6.dataset.v1")
        self.assertIn("manifest_checksum", manifest)
        self.assertEqual(splits["manifest_checksum"], manifest["manifest_checksum"])
        self.assertGreaterEqual(len(splits["splits"]["train"]), 1)
        self.assertGreaterEqual(len(splits["splits"]["validation"]), 1)
        self.assertGreaterEqual(len(splits["splits"]["demo"]), 1)

        for sample in manifest["samples"]:
            provenance = sample.get("provenance", {})
            self.assertIn("source_type", provenance)
            self.assertIn("source_ref", provenance)
            self.assertIn("labeler", provenance)
            self.assertIn("created_at", provenance)

    def test_training_artifacts_include_checkpoint_and_manifest(self) -> None:
        result = create_training_artifacts(
            artifact_root=self.tmpdir,
            run_id="lora_run_test_001",
            artifact_volume="landfillsentry-model-artifacts",
            config={
                "epochs": 1,
                "model_id": "LiquidAI/LFM2.5-VL-450M",
                "revision": "main",
            },
        )
        manifest_path = Path(result["manifest_path"])
        checkpoint_dir = Path(result["checkpoint_dir"])

        self.assertTrue(manifest_path.exists())
        self.assertTrue((checkpoint_dir / "adapter_config.json").exists())
        self.assertTrue((checkpoint_dir / "adapter_model.safetensors").exists())
        self.assertTrue((checkpoint_dir / "training_args.json").exists())
        self.assertIn("adapter_artifact_ref", result)
        self.assertEqual(result["training_mode"], "phase6_scaffold")

    def test_inference_trace_supports_adapter_model_ref_contract(self) -> None:
        register_site(self._site("LF_P6_SCAN_001"))
        scan = scan_site("LF_P6_SCAN_001", ScanRequest(force_refresh=False))
        evidence = get_scan_evidence(scan.scan_id)
        inference_meta = evidence["metadata"]["inference"]

        self.assertEqual(inference_meta["mode"], "mock")
        self.assertIn("+adapter=", inference_meta["model_ref"])
        self.assertIn("landfillsentry/lfm25vl450m-lora-v1@main", inference_meta["model_ref"])


if __name__ == "__main__":
    unittest.main()

