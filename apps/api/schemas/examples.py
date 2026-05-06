from datetime import datetime, timezone

from .enums import (
    FeedbackStatus,
    LikelySourceZone,
    PriorityTier,
    ReviewStatus,
    SeverityTier,
)
from .models import Candidate, Incident


def candidate_example() -> Candidate:
    return Candidate(
        candidate_id="cand_001",
        site_id="LF_DEMO_001",
        job_id="scan_001",
        bbox_norm=[0.25, 0.15, 0.47, 0.32],
        candidate_score=0.71,
        temporal_recurrence=0.64,
        cloud_penalty=0.12,
        likely_source_zone_prior=LikelySourceZone.ACTIVE_FACE,
    )


def incident_example(incident_id: str = "inc_001", site_id: str = "LF_DEMO_001") -> Incident:
    return Incident(
        incident_id=incident_id,
        site_id=site_id,
        job_id="scan_001",
        analysis_time=datetime(2026, 4, 19, 11, 15, 0, tzinfo=timezone.utc),
        plume_likely=True,
        confidence=0.84,
        bbox_norm=[0.32, 0.18, 0.56, 0.43],
        likely_source_zone=LikelySourceZone.ACTIVE_FACE,
        persistence_score=0.72,
        priority_tier=PriorityTier.HIGH,
        severity_tier=SeverityTier.MEDIUM,
        review_status=ReviewStatus.PROPOSED,
        feedback_status=FeedbackStatus.UNRESOLVED,
        evidence_summary=(
            "Recurring anomaly near the active working area across recent "
            "cloud-acceptable scenes."
        ),
        recommended_followup=(
            "Inspect active face cover integrity and nearby gas capture within 24 hours."
        ),
        model_version="lfm25vl450m-landfillsentry-lora-v1",
    )
