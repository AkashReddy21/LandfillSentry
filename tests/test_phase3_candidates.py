import os
import shutil
import tempfile
import unittest
from pathlib import Path

from apps.api.routes.api import get_scan_evidence, register_site, scan_site
from apps.api.runtime import (
    get_cache_service,
    get_candidate_service,
    get_imagery_service,
    reset_runtime_caches,
)
from apps.api.schemas import ScanRequest, Site
from apps.api.schemas.enums import LikelySourceZone


class Phase3CandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ls_phase3_"))
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

    def test_candidate_scoring_positive_vs_negative(self) -> None:
        imagery = get_imagery_service()
        candidate_service = get_candidate_service()
        get_cache_service()  # ensure cache path initialized for deterministic behavior

        positive_site = self._site("LF_POS_CAND_001", "positive")
        negative_site = self._site("LF_NEG_CAND_001", "negative")

        positive_assets, _ = imagery.fetch_site_bundle(site=positive_site, force_refresh=False)
        negative_assets, _ = imagery.fetch_site_bundle(site=negative_site, force_refresh=False)

        positive = candidate_service.generate(positive_site, positive_assets, job_id="scan_pos_001").candidate
        negative = candidate_service.generate(negative_site, negative_assets, job_id="scan_neg_001").candidate

        self.assertGreater(positive.candidate_score, negative.candidate_score)
        self.assertIn(positive.likely_source_zone_prior, [LikelySourceZone.ACTIVE_FACE, LikelySourceZone.GAS_SYSTEM])
        self.assertEqual(negative.likely_source_zone_prior, LikelySourceZone.PERIMETER_OR_UNKNOWN)

    def test_cloud_penalty_effect(self) -> None:
        imagery = get_imagery_service()
        candidate_service = get_candidate_service()

        cloudy_site = self._site("LF_CLOUD_001", "cloudy")
        assets, _ = imagery.fetch_site_bundle(site=cloudy_site, force_refresh=False)
        result = candidate_service.generate(cloudy_site, assets, job_id="scan_cloud_001").candidate

        self.assertGreaterEqual(result.cloud_penalty, 0.5)
        self.assertLess(result.candidate_score, 0.5)

    def test_scan_evidence_contains_candidate_contract(self) -> None:
        register_site(self._site("LF_SCAN_001", "positive"))
        scan = scan_site("LF_SCAN_001", ScanRequest(force_refresh=False))
        evidence = get_scan_evidence(scan.scan_id)

        candidate = evidence["metadata"].get("candidate")
        diagnostics = evidence["metadata"].get("candidate_diagnostics")

        self.assertIsNotNone(candidate)
        self.assertIsNotNone(diagnostics)
        self.assertIn("candidate_id", candidate)
        self.assertIn("bbox_norm", candidate)
        self.assertIn("candidate_score", candidate)
        self.assertIn("temporal_recurrence", candidate)
        self.assertIn("likely_source_zone_prior", candidate)
        self.assertGreaterEqual(float(candidate["candidate_score"]), 0.0)
        self.assertLessEqual(float(candidate["candidate_score"]), 1.0)

    def test_cached_and_live_paths_both_generate_candidates(self) -> None:
        register_site(self._site("LF_CACHE_CAND_001", "positive"))

        first = scan_site("LF_CACHE_CAND_001", ScanRequest(force_refresh=False))
        second = scan_site("LF_CACHE_CAND_001", ScanRequest(force_refresh=False))

        self.assertEqual(first.status, "live")
        self.assertEqual(second.status, "cached")

        evidence_1 = get_scan_evidence(first.scan_id)
        evidence_2 = get_scan_evidence(second.scan_id)
        self.assertIsNotNone(evidence_1["metadata"].get("candidate"))
        self.assertIsNotNone(evidence_2["metadata"].get("candidate"))


if __name__ == "__main__":
    unittest.main()
