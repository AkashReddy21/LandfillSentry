import hashlib
from dataclasses import dataclass
from typing import Dict

from ..schemas import Candidate, ImageAsset, Site
from ..schemas.enums import LikelySourceZone


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


@dataclass
class CandidateResult:
    candidate: Candidate
    diagnostics: Dict


class CandidateService:
    def generate(self, site: Site, assets: Dict[str, ImageAsset], job_id: str) -> CandidateResult:
        fixture_class = str(site.metadata.get("fixture_class", "default")).lower()
        current_cloud = float(assets["current"].cloud_cover)
        historical_cloud = float(assets["historical"].cloud_cover)
        cloud_penalty = _clamp((current_cloud + historical_cloud) / 2.0)

        base_anomaly = self._base_anomaly_for_fixture(fixture_class)
        base_recurrence = self._base_recurrence_for_fixture(fixture_class)

        anomaly_intensity = _clamp(base_anomaly - (0.25 * cloud_penalty))
        temporal_recurrence = _clamp(base_recurrence * (1.0 - (0.5 * cloud_penalty)))
        candidate_score = _clamp(
            (0.55 * anomaly_intensity) + (0.35 * temporal_recurrence) + (0.10 * (1.0 - cloud_penalty))
        )

        likely_source_zone = self._zone_prior(site=site, candidate_score=candidate_score, anomaly=anomaly_intensity)
        bbox_norm = self._deterministic_bbox(site_id=site.site_id, job_id=job_id)

        candidate = Candidate(
            candidate_id=f"cand_{job_id}",
            site_id=site.site_id,
            job_id=job_id,
            bbox_norm=bbox_norm,
            candidate_score=candidate_score,
            temporal_recurrence=temporal_recurrence,
            cloud_penalty=cloud_penalty,
            likely_source_zone_prior=likely_source_zone,
        )

        diagnostics = {
            "fixture_class": fixture_class,
            "anomaly_intensity": anomaly_intensity,
            "temporal_recurrence_raw": base_recurrence,
            "current_cloud": current_cloud,
            "historical_cloud": historical_cloud,
            "cloud_penalty": cloud_penalty,
            "candidate_score_formula": "0.55*anomaly + 0.35*recurrence + 0.10*(1-cloud_penalty)",
            "zone_prior": likely_source_zone.value,
        }
        return CandidateResult(candidate=candidate, diagnostics=diagnostics)

    def _base_anomaly_for_fixture(self, fixture_class: str) -> float:
        mapping = {
            "positive": 0.82,
            "negative": 0.18,
            "cloudy": 0.42,
            "missing_data": 0.05,
            "default": 0.55,
        }
        return mapping.get(fixture_class, mapping["default"])

    def _base_recurrence_for_fixture(self, fixture_class: str) -> float:
        mapping = {
            "positive": 0.78,
            "negative": 0.12,
            "cloudy": 0.35,
            "missing_data": 0.05,
            "default": 0.50,
        }
        return mapping.get(fixture_class, mapping["default"])

    def _zone_prior(self, site: Site, candidate_score: float, anomaly: float) -> LikelySourceZone:
        preferred = str(site.metadata.get("preferred_zone", "")).lower().strip()
        if preferred == LikelySourceZone.ACTIVE_FACE.value:
            return LikelySourceZone.ACTIVE_FACE
        if preferred == LikelySourceZone.GAS_SYSTEM.value:
            return LikelySourceZone.GAS_SYSTEM
        if preferred == LikelySourceZone.PERIMETER_OR_UNKNOWN.value:
            return LikelySourceZone.PERIMETER_OR_UNKNOWN

        if candidate_score >= 0.70 and anomaly >= 0.60:
            return LikelySourceZone.ACTIVE_FACE
        if candidate_score >= 0.45:
            return LikelySourceZone.GAS_SYSTEM
        return LikelySourceZone.PERIMETER_OR_UNKNOWN

    def _deterministic_bbox(self, site_id: str, job_id: str):
        seed = int(hashlib.sha256(f"{site_id}:{job_id}".encode("utf-8")).hexdigest()[:8], 16)
        x1 = 0.10 + ((seed % 30) / 100.0)
        y1 = 0.10 + (((seed // 7) % 30) / 100.0)
        width = 0.18 + (((seed // 11) % 10) / 100.0)
        height = 0.15 + (((seed // 13) % 10) / 100.0)
        x2 = min(0.95, x1 + width)
        y2 = min(0.95, y1 + height)
        return [round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3)]
