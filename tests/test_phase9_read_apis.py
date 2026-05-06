import os
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routes.api import register_site, scan_site
from apps.api.runtime import reset_runtime_caches
from apps.api.schemas import ScanRequest, Site


class Phase9ReadApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ls_phase9_"))
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

        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        os.environ.clear()
        os.environ.update(self.old_env)
        reset_runtime_caches()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _site(self, site_id: str, name: str) -> Site:
        return Site(
            site_id=site_id,
            name=name,
            lat=22.5726,
            lon=88.3639,
            country="IN",
            operator="Demo Operator",
            watchlist_enabled=True,
            polygon_geojson=None,
            metadata={"fixture_class": "positive"},
        )

    def _seed(self) -> str:
        register_site(self._site("LF_P9_001", "Phase5 Live Site"))
        register_site(self._site("LF_P9_002", "All Phases E2E Site"))
        first = scan_site("LF_P9_001", ScanRequest(force_refresh=False))
        scan_site("LF_P9_002", ScanRequest(force_refresh=False))
        return first.incident_id

    def test_priority1_read_apis(self) -> None:
        incident_id = self._seed()

        watch_summary = self.client.get("/watchlist/summary")
        self.assertEqual(watch_summary.status_code, 200)
        payload = watch_summary.json()
        self.assertIn("sites_monitored", payload)
        self.assertIn("last_scan_success_rate", payload)

        incidents = self.client.get("/incidents?page=1&page_size=10")
        self.assertEqual(incidents.status_code, 200)
        incident_rows = incidents.json()["items"]
        self.assertGreaterEqual(len(incident_rows), 1)
        self.assertIn("site_name", incident_rows[0])
        self.assertIn("detected_time", incident_rows[0])

        incident_detail = self.client.get(f"/incidents/{incident_id}")
        self.assertEqual(incident_detail.status_code, 200)
        detail = incident_detail.json()
        self.assertIn("incident", detail)
        self.assertIn("decision_history", detail)
        self.assertIn("panel_previews", detail)

        packs = self.client.get("/evidence-packs?page=1&page_size=10")
        self.assertEqual(packs.status_code, 200)
        pack_rows = packs.json()["items"]
        self.assertGreaterEqual(len(pack_rows), 1)
        self.assertIn("panel_id", pack_rows[0])
        panel_id = pack_rows[0]["panel_id"]

        pack_detail = self.client.get(f"/evidence-packs/{panel_id}")
        self.assertEqual(pack_detail.status_code, 200)
        self.assertIn("panel_metadata", pack_detail.json())

        queue = self.client.get("/review-queue?page=1&page_size=10")
        self.assertEqual(queue.status_code, 200)
        q_payload = queue.json()
        self.assertIn("summary", q_payload)
        self.assertIn("items", q_payload)

    def test_priority2_workflow_tables(self) -> None:
        incident_id = self._seed()

        comment = self.client.post(
            f"/incidents/{incident_id}/comments",
            json={
                "author_name": "Akash",
                "author_role": "reviewer",
                "body": "Please verify this plume in next field visit.",
            },
        )
        self.assertEqual(comment.status_code, 200)

        comments = self.client.get(f"/incidents/{incident_id}/comments")
        self.assertEqual(comments.status_code, 200)
        self.assertGreaterEqual(len(comments.json()), 1)

        assignment = self.client.post(
            f"/incidents/{incident_id}/assign",
            json={"assignee_name": "Ops A", "assignee_role": "analyst"},
        )
        self.assertEqual(assignment.status_code, 200)
        self.assertEqual(assignment.json()["assignee_name"], "Ops A")

        site_settings = self.client.get("/sites/LF_P9_001/settings")
        self.assertEqual(site_settings.status_code, 200)
        self.assertIn("scan_cadence_hours", site_settings.json())

        patch = self.client.patch(
            "/sites/LF_P9_001/settings",
            json={"scan_cadence_hours": 12, "notes": "High-importance site"},
        )
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(patch.json()["scan_cadence_hours"], 12)

    def test_watchlist_enrichment(self) -> None:
        self._seed()
        resp = self.client.get(
            "/watchlist?page=1&page_size=1&include_summary=true&sort_by=confidence&selected_site_id=LF_P9_001"
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 1)
        self.assertIn("summary", payload)
        self.assertIn("selected", payload)
        self.assertEqual(len(payload["items"]), 1)


if __name__ == "__main__":
    unittest.main()
