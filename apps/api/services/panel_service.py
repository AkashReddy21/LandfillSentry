import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict

from ..schemas import Candidate, EvidencePanel, ImageAsset, Site
from .cache_service import CacheService


class PanelBuildError(Exception):
    pass


@dataclass
class PanelBuildResult:
    panel: EvidencePanel
    panel_document: Dict


class PanelService:
    PANEL_VERSION = "phase4.panel.v1"
    LAYOUT_VERSION = "phase4.layout.2x2.v1"

    def __init__(self, cache: CacheService) -> None:
        self.cache = cache

    def build(
        self,
        site: Site,
        assets: Dict[str, ImageAsset],
        candidate: Candidate,
        mode: str,
    ) -> PanelBuildResult:
        current = assets.get("current")
        historical = assets.get("historical")
        mapbox = assets.get("mapbox")
        if not current or not historical or not mapbox:
            raise PanelBuildError("current, historical, and mapbox assets are all required to build a panel")
        if not mapbox.local_path:
            raise PanelBuildError("mapbox context path is required for panel build")

        metadata_text = self._metadata_text(site=site, candidate=candidate, current=current, historical=historical)
        panel_doc = {
            "panel_version": self.PANEL_VERSION,
            "layout_version": self.LAYOUT_VERSION,
            "site_id": site.site_id,
            "candidate_id": candidate.candidate_id,
            "metadata_text": metadata_text,
            "slots": {
                "current_rgb": current.local_path,
                "spectral_composite": historical.local_path,
                "temporal_diff": historical.local_path,
                "mapbox_context": mapbox.local_path,
            },
            "metrics": {
                "candidate_score": candidate.candidate_score,
                "temporal_recurrence": candidate.temporal_recurrence,
                "cloud_penalty": candidate.cloud_penalty,
                "cloud_cover_current": current.cloud_cover,
                "cloud_cover_historical": historical.cloud_cover,
            },
        }

        cache_key = self.cache.make_cache_key(
            namespace="panel:phase4",
            payload={
                "site_id": site.site_id,
                "candidate_id": candidate.candidate_id,
                "current_cache_key": current.cache_key,
                "historical_cache_key": historical.cache_key,
                "mapbox_cache_key": mapbox.cache_key,
                "panel_version": self.PANEL_VERSION,
            },
        )
        cached_meta = self.cache.write(
            cache_key=cache_key,
            blob=json.dumps(panel_doc, sort_keys=True, indent=2).encode("utf-8"),
            metadata={
                "timestamp_requested": self._now_iso(),
                "timestamp_captured": self._now_iso(),
                "cloud_cover": 0.0,
                "bands": ["panel"],
            },
            ext=".panel.json",
        )

        panel = EvidencePanel(
            panel_id=f"panel_{cache_key[:12]}",
            site_id=site.site_id,
            candidate_id=candidate.candidate_id,
            panel_version=self.PANEL_VERSION,
            current_rgb_path=current.local_path,
            spectral_composite_path=historical.local_path,
            temporal_diff_path=historical.local_path,
            mapbox_context_path=mapbox.local_path,
            metadata_json={
                "layout_version": self.LAYOUT_VERSION,
                "metadata_text": metadata_text,
                "panel_artifact_path": cached_meta["path"],
                "source_mode": mode,
            },
        )
        return PanelBuildResult(panel=panel, panel_document=panel_doc)

    def _metadata_text(self, site: Site, candidate: Candidate, current: ImageAsset, historical: ImageAsset) -> str:
        return (
            f"Site {site.site_id} ({site.name}) candidate {candidate.candidate_id}: "
            f"score={candidate.candidate_score:.2f}, recurrence={candidate.temporal_recurrence:.2f}, "
            f"zone_prior={candidate.likely_source_zone_prior.value}, "
            f"cloud_current={current.cloud_cover:.2f}, cloud_historical={historical.cloud_cover:.2f}."
        )

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
