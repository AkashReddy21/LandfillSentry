import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..schemas import Incident


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


class OutputValidationError(Exception):
    pass


@dataclass
class ValidationContext:
    incident_id: str
    site_id: str
    job_id: str
    model_version: str
    fallback_bbox: List[float]
    fallback_confidence: float
    fallback_recurrence: float
    fallback_zone: str
    fallback_evidence_summary: str


@dataclass
class OutputValidationResult:
    incident: Incident
    attempts: int
    errors: List[Dict] = field(default_factory=list)
    output_schema_version: str = "phase4.incident.v1"

    def as_dict(self) -> Dict:
        return {
            "attempts": self.attempts,
            "errors": self.errors,
            "output_schema_version": self.output_schema_version,
        }


class OutputValidationService:
    OUTPUT_SCHEMA_VERSION = "phase4.incident.v1"

    def validate_with_retry(self, raw_outputs: List[Any], context: ValidationContext) -> OutputValidationResult:
        if not raw_outputs:
            raise OutputValidationError("no raw outputs provided for validation")

        errors: List[Dict] = []
        for attempt, raw in enumerate(raw_outputs, start=1):
            try:
                payload = self._parse_payload(raw)
                normalized = self._normalize_payload(payload, context=context)
                incident = Incident(**normalized)
                return OutputValidationResult(
                    incident=incident,
                    attempts=attempt,
                    errors=errors,
                    output_schema_version=self.OUTPUT_SCHEMA_VERSION,
                )
            except Exception as exc:
                errors.append({"attempt": attempt, "error": str(exc)})

        raise OutputValidationError(
            f"incident output validation failed after {len(raw_outputs)} attempts: {errors[-1]['error']}"
        )

    def _parse_payload(self, raw: Any) -> Dict:
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(raw, str):
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("parsed output is not a JSON object")
            return parsed
        raise ValueError(f"unsupported output type: {type(raw).__name__}")

    def _normalize_payload(self, payload: Dict, context: ValidationContext) -> Dict:
        result = dict(payload)
        confidence = _clamp(float(result.get("confidence", result.get("candidate_score", context.fallback_confidence))))
        persistence = _clamp(float(result.get("persistence_score", result.get("temporal_recurrence", context.fallback_recurrence))))

        likely_source_zone = (
            result.get("likely_source_zone")
            or result.get("likely_source_zone_prior")
            or context.fallback_zone
        )
        bbox_norm = self._normalize_bbox(result.get("bbox_norm"), context.fallback_bbox)
        review_status = self._normalize_review_status(result.get("review_status"))
        feedback_status = self._normalize_feedback_status(result.get("feedback_status"))

        likely_source_zone = self._normalize_zone(likely_source_zone, context.fallback_zone)
        priority_tier, severity_tier = self._priority_severity_from_confidence(confidence)
        priority_tier = self._normalize_priority(result.get("priority_tier"), default=priority_tier)
        severity_tier = self._normalize_severity(result.get("severity_tier"), default=severity_tier)
        followup = self._followup_for_zone(str(likely_source_zone))

        normalized = {
            "incident_id": context.incident_id,
            "site_id": context.site_id,
            "job_id": context.job_id,
            "analysis_time": result.get("analysis_time", self._now_iso()),
            "plume_likely": bool(result.get("plume_likely", confidence >= 0.50)),
            "confidence": confidence,
            "bbox_norm": bbox_norm,
            "likely_source_zone": likely_source_zone,
            "persistence_score": persistence,
            "priority_tier": priority_tier,
            "severity_tier": severity_tier,
            "review_status": review_status,
            "feedback_status": feedback_status,
            "evidence_summary": result.get("evidence_summary", context.fallback_evidence_summary),
            "recommended_followup": result.get("recommended_followup", followup),
            "model_version": context.model_version,
        }
        return normalized

    def _priority_severity_from_confidence(self, confidence: float) -> tuple[str, str]:
        if confidence >= 0.85:
            return "urgent", "high"
        if confidence >= 0.65:
            return "high", "medium"
        if confidence >= 0.40:
            return "medium", "low"
        return "low", "low"

    def _followup_for_zone(self, zone: str) -> str:
        if zone == "active_face":
            return "Inspect active-face cover, compaction quality, and short-loop gas collection today."
        if zone == "gas_system":
            return "Inspect nearby gas wells, manifolds, and vacuum balancing settings within 24 hours."
        return "Inspect perimeter and uncertain source corridors; collect confirmation imagery and field notes."

    def _normalize_bbox(self, raw_bbox: Any, fallback_bbox: List[float]) -> List[float]:
        if isinstance(raw_bbox, list) and len(raw_bbox) == 4:
            try:
                return [_clamp(float(v)) for v in raw_bbox]
            except Exception:
                return list(fallback_bbox)
        if isinstance(raw_bbox, dict):
            if {"left", "top", "right", "bottom"}.issubset(set(raw_bbox.keys())):
                try:
                    return [
                        _clamp(float(raw_bbox["left"])),
                        _clamp(float(raw_bbox["top"])),
                        _clamp(float(raw_bbox["right"])),
                        _clamp(float(raw_bbox["bottom"])),
                    ]
                except Exception:
                    return list(fallback_bbox)
            if {"x1", "y1", "x2", "y2"}.issubset(set(raw_bbox.keys())):
                try:
                    return [
                        _clamp(float(raw_bbox["x1"])),
                        _clamp(float(raw_bbox["y1"])),
                        _clamp(float(raw_bbox["x2"])),
                        _clamp(float(raw_bbox["y2"])),
                    ]
                except Exception:
                    return list(fallback_bbox)
        return list(fallback_bbox)

    def _normalize_review_status(self, raw_status: Any) -> str:
        value = str(raw_status or "").strip().lower()
        if value in {"proposed", "published", "dismissed", "needs_review"}:
            return value
        mapping = {
            "pending": "needs_review",
            "reviewed": "published",
            "confirmed": "published",
        }
        return mapping.get(value, "proposed")

    def _normalize_feedback_status(self, raw_status: Any) -> str:
        value = str(raw_status or "").strip().lower()
        if value in {"confirmed", "dismissed", "needs_review", "unresolved"}:
            return value
        mapping = {
            "pending": "unresolved",
            "received": "needs_review",
            "reviewed": "confirmed",
        }
        return mapping.get(value, "unresolved")

    def _normalize_zone(self, raw_zone: Any, fallback_zone: str) -> str:
        value = str(raw_zone or "").strip().lower().replace("-", "_").replace(" ", "_")
        mapping = {
            "activeface": "active_face",
            "active_face": "active_face",
            "gas_system": "gas_system",
            "gassystem": "gas_system",
            "perimeter_or_unknown": "perimeter_or_unknown",
            "perimeter_unknown": "perimeter_or_unknown",
            "perimeter": "perimeter_or_unknown",
            "unknown": "perimeter_or_unknown",
        }
        normalized = mapping.get(value)
        if normalized:
            return normalized
        fb = str(fallback_zone or "").strip().lower().replace("-", "_").replace(" ", "_")
        return mapping.get(fb, "perimeter_or_unknown")

    def _normalize_priority(self, raw_priority: Any, default: str) -> str:
        value = str(raw_priority or "").strip().lower()
        mapping = {
            "low": "low",
            "medium": "medium",
            "med": "medium",
            "high": "high",
            "urgent": "urgent",
            "critical": "urgent",
        }
        return mapping.get(value, default)

    def _normalize_severity(self, raw_severity: Any, default: str) -> str:
        value = str(raw_severity or "").strip().lower()
        mapping = {
            "low": "low",
            "medium": "medium",
            "med": "medium",
            "high": "high",
            "urgent": "high",
            "critical": "high",
        }
        return mapping.get(value, default)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
