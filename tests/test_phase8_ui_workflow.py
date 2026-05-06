import os
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routes.api import (
    export_incident_evidence,
    get_site_detail,
    ingest_dongle_reading,
    list_dongle_readings,
    get_watchlist,
    register_site,
    review_incident,
    scan_site,
)
from apps.api.runtime import reset_runtime_caches
from apps.api.schemas import DongleReadingCreate, ReviewAction, ScanRequest, Site
from apps.api.schemas.enums import FeedbackStatus, ReviewStatus


class Phase8UIWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ls_phase8_"))
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
        reset_runtime_caches()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)
        reset_runtime_caches()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _site(self, site_id: str) -> Site:
        return Site(
            site_id=site_id,
            name=site_id,
            lat=22.5726,
            lon=88.3639,
            country="IN",
            operator="Demo Operator",
            watchlist_enabled=True,
            polygon_geojson=None,
            metadata={"fixture_class": "positive"},
        )

    def test_watchlist_and_site_detail_render_real_backend_payload(self) -> None:
        register_site(self._site("LF_P8_001"))
        scan = scan_site("LF_P8_001", ScanRequest(force_refresh=False))

        watchlist = get_watchlist()
        row = next(item for item in watchlist["items"] if item["site_id"] == "LF_P8_001")
        self.assertEqual(row["incident_id"], scan.incident_id)
        self.assertEqual(row["scan_status"], "live")
        self.assertEqual(row["generation_mode"], "mock")
        self.assertIn("priority_tier", row)

        detail = get_site_detail("LF_P8_001")
        self.assertEqual(detail["latest_scan"]["scan_id"], scan.scan_id)
        self.assertEqual(detail["latest_incident"]["incident_id"], scan.incident_id)
        self.assertIn("panel_previews", detail)
        self.assertIn("current_rgb", detail["panel_previews"])
        self.assertIn("mapbox_context_path", detail["evidence"]["panel_paths"])

    def test_review_action_reflects_in_watchlist_immediately(self) -> None:
        register_site(self._site("LF_P8_002"))
        scan = scan_site("LF_P8_002", ScanRequest(force_refresh=False))

        review_incident(
            scan.incident_id,
            ReviewAction(
                incident_id=scan.incident_id,
                review_status=ReviewStatus.PUBLISHED,
                feedback_status=FeedbackStatus.CONFIRMED,
            ),
        )

        watchlist = get_watchlist()
        row = next(item for item in watchlist["items"] if item["site_id"] == "LF_P8_002")
        self.assertEqual(row["review_status"], "published")
        self.assertEqual(row["feedback_status"], "confirmed")

    def test_incident_export_supports_markdown_and_json(self) -> None:
        register_site(self._site("LF_P8_003"))
        scan = scan_site("LF_P8_003", ScanRequest(force_refresh=False))

        markdown_resp = export_incident_evidence(scan.incident_id, format="markdown")
        markdown_text = markdown_resp.body.decode("utf-8")
        self.assertIn(scan.incident_id, markdown_text)
        self.assertIn("Evidence Panel Paths", markdown_text)

        json_resp = export_incident_evidence(scan.incident_id, format="json")
        self.assertEqual(json_resp["incident"]["incident_id"], scan.incident_id)
        self.assertIn("evidence", json_resp)

    def test_dongle_reading_is_attached_and_export_includes_ground_truth(self) -> None:
        site_id = "LF_P8_DONGLE_001"
        register_site(self._site(site_id))

        reading = ingest_dongle_reading(
            site_id,
            DongleReadingCreate(
                methane_ppm=2.75,
                device_id="dongle-test-v1",
                source="field_dongle",
                notes="test corroboration",
            ),
        )
        self.assertEqual(reading.site_id, site_id)
        self.assertIsNone(reading.incident_id)

        scan = scan_site(site_id, ScanRequest(force_refresh=False))
        detail = get_site_detail(site_id)
        hint = detail["evidence"]["metadata"]["ground_truth_hint"]
        self.assertEqual(hint["status"], "dongle_corroborated")
        self.assertIn("ppm", hint["message"])

        readings = list_dongle_readings(site_id, limit=10)
        self.assertTrue(any(r.incident_id == scan.incident_id for r in readings))

        markdown_resp = export_incident_evidence(scan.incident_id, format="markdown")
        markdown_text = markdown_resp.body.decode("utf-8")
        self.assertIn("Ground Truth Hint", markdown_text)
        self.assertIn("Data Source", markdown_text)

    def test_frontend_routes_smoke(self) -> None:
        with TestClient(app) as client:
            ops = client.get("/ops")
            self.assertEqual(ops.status_code, 200)
            self.assertIn("LandfillSentry Ops Console", ops.text)

            css = client.get("/ui/ops.css")
            self.assertEqual(css.status_code, 200)
            self.assertIn("--accent", css.text)


if __name__ == "__main__":
    unittest.main()
