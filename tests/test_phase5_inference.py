import os
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from apps.api.routes.api import (
    export_incidents,
    get_scan_evidence,
    register_site,
    review_incident,
    scan_site,
)
from apps.api.runtime import get_inference_service, reset_runtime_caches
from apps.api.schemas import ReviewAction, ScanRequest, Site
from apps.api.schemas.enums import FeedbackStatus, ReviewStatus
from apps.api.services.output_validation_service import OutputValidationService, ValidationContext


class Phase5InferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ls_phase5_"))
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
        os.environ["HF_ADAPTER_ID"] = ""
        os.environ["HF_ADAPTER_REVISION"] = "main"
        os.environ["HF_TOKEN"] = "hf_test_token_for_mock"
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

    def test_scan_records_inference_trace_in_mock_mode(self) -> None:
        register_site(self._site("LF_P5_MOCK_001"))
        scan = scan_site("LF_P5_MOCK_001", ScanRequest(force_refresh=False))
        evidence = get_scan_evidence(scan.scan_id)
        inference_meta = evidence["metadata"].get("inference", {})

        self.assertEqual(scan.status, "live")
        self.assertEqual(inference_meta.get("mode"), "mock")
        self.assertEqual(inference_meta.get("model_id"), "LiquidAI/LFM2.5-VL-450M")
        self.assertEqual(inference_meta.get("model_revision"), "main")
        self.assertEqual(inference_meta.get("model_ref"), "LiquidAI/LFM2.5-VL-450M@main")
        self.assertTrue(inference_meta.get("auth_configured"))

    def test_json_extraction_helper_handles_object_and_array(self) -> None:
        service = get_inference_service()
        obj = service._extract_json_payload("prefix {\"a\": 1, \"b\": 2} suffix")
        arr = service._extract_json_payload("prefix [{\"label\":\"x\"}] suffix")
        bad = service._extract_json_payload("no-json-here")

        self.assertEqual(obj, {"a": 1, "b": 2})
        self.assertEqual(arr, [{"label": "x"}])
        self.assertIsNone(bad)

    def test_priority_and_severity_logic_from_confidence_thresholds(self) -> None:
        svc = OutputValidationService()
        ctx = ValidationContext(
            incident_id="inc_p5_prio_001",
            site_id="LF_P5_PRIO_001",
            job_id="scan_p5_prio_001",
            model_version="LiquidAI/LFM2.5-VL-450M@main",
            fallback_bbox=[0.2, 0.2, 0.5, 0.5],
            fallback_confidence=0.3,
            fallback_recurrence=0.3,
            fallback_zone="gas_system",
            fallback_evidence_summary="summary",
        )
        urgent = svc.validate_with_retry([{"confidence": 0.90}], context=ctx).incident
        high = svc.validate_with_retry([{"confidence": 0.70}], context=ctx).incident
        medium = svc.validate_with_retry([{"confidence": 0.45}], context=ctx).incident

        self.assertEqual(urgent.priority_tier.value, "urgent")
        self.assertEqual(urgent.severity_tier.value, "high")
        self.assertEqual(high.priority_tier.value, "high")
        self.assertEqual(high.severity_tier.value, "medium")
        self.assertEqual(medium.priority_tier.value, "medium")
        self.assertEqual(medium.severity_tier.value, "low")

    def test_review_state_lifecycle_persists(self) -> None:
        register_site(self._site("LF_P5_REVIEW_001"))
        scan = scan_site("LF_P5_REVIEW_001", ScanRequest(force_refresh=False))
        incident_id = scan.incident_id

        published = review_incident(
            incident_id,
            ReviewAction(
                incident_id=incident_id,
                review_status=ReviewStatus.PUBLISHED,
                feedback_status=FeedbackStatus.CONFIRMED,
            ),
        )
        self.assertEqual(published.review_status.value, "published")
        self.assertEqual(published.feedback_status.value, "confirmed")

        dismissed = review_incident(
            incident_id,
            ReviewAction(
                incident_id=incident_id,
                review_status=ReviewStatus.DISMISSED,
            ),
        )
        self.assertEqual(dismissed.review_status.value, "dismissed")
        self.assertEqual(dismissed.feedback_status.value, "confirmed")

        export_payload = export_incidents(format="json")
        matched = [inc for inc in export_payload.incidents if inc.incident_id == incident_id]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].review_status.value, "dismissed")

    def test_validation_normalizes_bbox_dict_and_non_enum_status_values(self) -> None:
        svc = OutputValidationService()
        ctx = ValidationContext(
            incident_id="inc_p5_norm_001",
            site_id="LF_P5_NORM_001",
            job_id="scan_p5_norm_001",
            model_version="LiquidAI/LFM2.5-VL-450M@main",
            fallback_bbox=[0.1, 0.1, 0.2, 0.2],
            fallback_confidence=0.33,
            fallback_recurrence=0.21,
            fallback_zone="active_face",
            fallback_evidence_summary="fallback-summary",
        )
        raw = {
            "confidence": 0.85,
            "bbox_norm": {"left": 0.05, "top": 0.15, "right": 0.45, "bottom": 0.35},
            "likely_source_zone": "Active face",
            "priority_tier": "High",
            "severity_tier": "Medium",
            "review_status": "pending",
            "feedback_status": "received",
            "evidence_summary": "live-summary",
        }
        result = svc.validate_with_retry([raw], context=ctx).incident
        self.assertEqual(result.bbox_norm, [0.05, 0.15, 0.45, 0.35])
        self.assertEqual(result.likely_source_zone.value, "active_face")
        self.assertEqual(result.priority_tier.value, "high")
        self.assertEqual(result.severity_tier.value, "medium")
        self.assertEqual(result.review_status.value, "needs_review")
        self.assertEqual(result.feedback_status.value, "needs_review")
        self.assertEqual(result.confidence, 0.85)

    def test_require_live_results_blocks_non_live_runtime_modes(self) -> None:
        os.environ["REQUIRE_LIVE_RESULTS"] = "true"
        reset_runtime_caches()
        register_site(self._site("LF_P5_LIVE_REQUIRED_001"))
        with self.assertRaises(HTTPException) as ctx:
            scan_site("LF_P5_LIVE_REQUIRED_001", ScanRequest(force_refresh=False))
        self.assertEqual(ctx.exception.status_code, 412)
        detail = getattr(ctx.exception, "detail", {})
        self.assertEqual(detail.get("error"), "live_mode_required")


if __name__ == "__main__":
    unittest.main()
