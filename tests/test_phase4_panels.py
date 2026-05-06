import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from apps.api.routes.api import get_scan_evidence, register_site, scan_site
from apps.api.runtime import reset_runtime_caches
from apps.api.schemas import ScanRequest, Site
from apps.api.services.output_validation_service import (
    OutputValidationService,
    ValidationContext,
)
from apps.api.services.prompt_contract_service import PromptContractService


class Phase4PanelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ls_phase4_"))
        self.db_path = self.tmpdir / "landfillsentry.db"
        self.cache_root = self.tmpdir / "cache"
        self.old_env = os.environ.copy()

        os.environ["LS_DB_PATH"] = str(self.db_path)
        os.environ["LS_CACHE_ROOT"] = str(self.cache_root)
        os.environ["SIMSAT_MODE"] = "mock"
        os.environ["MAPBOX_MODE"] = "mock"
        os.environ["INFERENCE_MODE"] = "mock"
        os.environ["REQUIRE_LIVE_RESULTS"] = "false"
        reset_runtime_caches()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)
        reset_runtime_caches()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _site(self, site_id: str, fixture_class: str) -> Site:
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

    def test_panel_renders_for_positive_and_negative_fixtures(self) -> None:
        for site in (self._site("LF_P4_POS_001", "positive"), self._site("LF_P4_NEG_001", "negative")):
            register_site(site)
            scan = scan_site(site.site_id, ScanRequest(force_refresh=False))
            evidence = get_scan_evidence(scan.scan_id)

            panel_path = Path(evidence["panel_paths"]["evidence_panel_path"])
            self.assertTrue(panel_path.exists())
            panel_doc = json.loads(panel_path.read_text(encoding="utf-8"))

            self.assertEqual(panel_doc["panel_version"], "phase4.panel.v1")
            self.assertEqual(panel_doc["layout_version"], "phase4.layout.2x2.v1")
            self.assertEqual(panel_doc["site_id"], site.site_id)
            self.assertTrue(panel_doc["metadata_text"])
            self.assertIn("mapbox_context", panel_doc["slots"])

    def test_every_panel_includes_required_mapbox_context_artifact(self) -> None:
        register_site(self._site("LF_P4_MAP_001", "positive"))
        scan = scan_site("LF_P4_MAP_001", ScanRequest(force_refresh=False))
        evidence = get_scan_evidence(scan.scan_id)

        panel_path = Path(evidence["panel_paths"]["evidence_panel_path"])
        panel_doc = json.loads(panel_path.read_text(encoding="utf-8"))

        self.assertTrue(evidence["panel_paths"]["mapbox_context_path"])
        self.assertEqual(panel_doc["slots"]["mapbox_context"], evidence["panel_paths"]["mapbox_context_path"])

    def test_prompt_contract_is_frozen_and_persisted_in_scan_metadata(self) -> None:
        register_site(self._site("LF_P4_PROMPT_001", "positive"))
        scan = scan_site("LF_P4_PROMPT_001", ScanRequest(force_refresh=False))
        evidence = get_scan_evidence(scan.scan_id)

        prompt_contract = evidence["metadata"]["prompt_contract"]
        self.assertEqual(prompt_contract["prompt_contract_version"], PromptContractService.PROMPT_CONTRACT_VERSION)
        self.assertEqual(prompt_contract["output_schema_version"], PromptContractService.OUTPUT_SCHEMA_VERSION)
        self.assertEqual(evidence["metadata"]["panel_version"], "phase4.panel.v1")
        self.assertTrue(evidence["metadata"]["metadata_text"])

    def test_output_schema_validation_loop_handles_canned_retry(self) -> None:
        service = OutputValidationService()
        context = ValidationContext(
            incident_id="inc_canned_001",
            site_id="LF_CANNED_001",
            job_id="scan_canned_001",
            model_version="lfm25vl450m-phase4-contract-preview",
            fallback_bbox=[0.2, 0.2, 0.5, 0.5],
            fallback_confidence=0.61,
            fallback_recurrence=0.52,
            fallback_zone="gas_system",
            fallback_evidence_summary="Canned fallback summary.",
        )

        invalid_output = "not-json"
        minimal_valid_output = {
            "confidence": 0.66,
            "bbox_norm": [0.2, 0.2, 0.5, 0.5],
            "likely_source_zone_prior": "gas_system",
            "temporal_recurrence": 0.51,
        }
        result = service.validate_with_retry([invalid_output, minimal_valid_output], context=context)

        self.assertEqual(result.attempts, 2)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.output_schema_version, "phase4.incident.v1")
        self.assertEqual(result.incident.site_id, "LF_CANNED_001")
        self.assertEqual(result.incident.job_id, "scan_canned_001")
        self.assertEqual(result.incident.likely_source_zone.value, "gas_system")

    def test_live_and_cached_panel_building_paths_both_work(self) -> None:
        register_site(self._site("LF_P4_CACHE_001", "positive"))
        first = scan_site("LF_P4_CACHE_001", ScanRequest(force_refresh=False))
        second = scan_site("LF_P4_CACHE_001", ScanRequest(force_refresh=False))

        self.assertEqual(first.status, "live")
        self.assertEqual(second.status, "cached")

        evidence_1 = get_scan_evidence(first.scan_id)
        evidence_2 = get_scan_evidence(second.scan_id)
        self.assertTrue(Path(evidence_1["panel_paths"]["evidence_panel_path"]).exists())
        self.assertTrue(Path(evidence_2["panel_paths"]["evidence_panel_path"]).exists())
        self.assertEqual(evidence_1["metadata"]["panel_version"], "phase4.panel.v1")
        self.assertEqual(evidence_2["metadata"]["panel_version"], "phase4.panel.v1")


if __name__ == "__main__":
    unittest.main()
