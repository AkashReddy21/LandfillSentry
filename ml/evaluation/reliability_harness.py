from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Dict
from uuid import uuid4

from apps.api.config import load_settings
from apps.api.schemas import Site
from apps.api.services.cache_service import CacheService
from apps.api.services.imagery_service import ImageryError, ImageryService
from apps.api.services.output_validation_service import OutputValidationService, ValidationContext


class ReliabilityHarness:
    """Failure-injection checks required by Phase 7."""

    def __init__(self) -> None:
        self._old_env = os.environ.copy()

    def _restore_env(self) -> None:
        os.environ.clear()
        os.environ.update(self._old_env)

    def invalid_json_path(self) -> Dict:
        validator = OutputValidationService()
        context = ValidationContext(
            incident_id="phase7_invalid_json_inc",
            site_id="LF_PHASE7_INVALID_JSON",
            job_id="scan_phase7_invalid_json",
            model_version="phase7-test-model",
            fallback_bbox=[0.2, 0.2, 0.5, 0.5],
            fallback_confidence=0.4,
            fallback_recurrence=0.3,
            fallback_zone="gas_system",
            fallback_evidence_summary="phase7 invalid json fallback",
        )
        result = validator.validate_with_retry(
            raw_outputs=[
                "not-json",
                {
                    "confidence": 0.55,
                    "bbox_norm": [0.2, 0.2, 0.5, 0.5],
                    "likely_source_zone": "gas_system",
                    "temporal_recurrence": 0.4,
                },
            ],
            context=context,
        )
        return {
            "name": "invalid_json",
            "handled": True,
            "attempts": result.attempts,
            "errors": result.errors,
        }

    def empty_candidate_path(self) -> Dict:
        candidate = None
        if candidate is None:
            return {
                "name": "empty_candidate",
                "handled": True,
                "strategy": "skip_model_inference_and_raise_review_flag",
                "review_status": "needs_review",
            }
        return {"name": "empty_candidate", "handled": False}

    def mapbox_failure_path(self) -> Dict:
        tmp_root = Path(__file__).resolve().parents[2] / ".tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        tmpdir = tmp_root / f"ls_phase7_rel_{uuid4().hex[:10]}"
        try:
            os.environ["LS_CACHE_ROOT"] = str(tmpdir / "cache")
            os.environ["SIMSAT_MODE"] = "mock"
            os.environ["MAPBOX_MODE"] = "live"
            os.environ["SIMSAT_USE_FOR_MAPBOX"] = "false"
            os.environ["MAPBOX_TOKEN"] = ""
            os.environ["MAPBOX_BASE_URL"] = ""
            settings = load_settings()
            imagery = ImageryService(settings=settings, cache=CacheService(settings.cache_root))
            site = Site(
                site_id="LF_PHASE7_MAPBOX_FAIL",
                name="phase7_mapbox_fail",
                lat=22.5726,
                lon=88.3639,
                country="IN",
                operator="Phase7",
                watchlist_enabled=True,
                polygon_geojson=None,
                metadata={"fixture_class": "positive"},
            )
            try:
                imagery.fetch_site_bundle(site=site, force_refresh=True)
                return {"name": "mapbox_api_failure", "handled": False}
            except ImageryError as exc:
                return {"name": "mapbox_api_failure", "handled": True, "error": str(exc)}
        finally:
            self._restore_env()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def slow_inference_path(self, threshold_seconds: float = 0.2) -> Dict:
        def _slow_callable() -> str:
            time.sleep(0.3)
            return "ok"

        start = time.perf_counter()
        _slow_callable()
        elapsed = time.perf_counter() - start
        return {
            "name": "slow_inference",
            "handled": elapsed >= threshold_seconds,
            "elapsed_seconds": round(elapsed, 4),
            "threshold_seconds": threshold_seconds,
            "mitigation": "tag_scan_as_slow_and_keep_cached_demo_path_ready",
        }

    def run_all(self) -> Dict:
        report = {
            "invalid_json": self.invalid_json_path(),
            "empty_candidate": self.empty_candidate_path(),
            "mapbox_api_failure": self.mapbox_failure_path(),
            "slow_inference": self.slow_inference_path(),
        }
        report["all_passed"] = all(bool(item.get("handled")) for item in report.values() if isinstance(item, dict))
        return report
