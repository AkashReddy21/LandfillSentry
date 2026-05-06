from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .enums import (
    DataSplit,
    FeedbackStatus,
    LikelySourceZone,
    PriorityTier,
    ReviewStatus,
    SeverityTier,
)


class Site(BaseModel):
    site_id: str
    name: str
    lat: float
    lon: float
    country: str
    operator: str
    watchlist_enabled: bool = True
    polygon_geojson: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ImageAsset(BaseModel):
    asset_id: str
    site_id: str
    source: str
    timestamp_requested: datetime
    timestamp_captured: datetime
    cloud_cover: float = Field(ge=0.0, le=1.0)
    bands: List[str] = Field(default_factory=list)
    local_path: str
    cache_key: str


class Candidate(BaseModel):
    candidate_id: str
    site_id: str
    job_id: str
    bbox_norm: List[float] = Field(min_length=4, max_length=4)
    candidate_score: float = Field(ge=0.0, le=1.0)
    temporal_recurrence: float = Field(ge=0.0, le=1.0)
    cloud_penalty: float = Field(ge=0.0, le=1.0)
    likely_source_zone_prior: LikelySourceZone


class EvidencePanel(BaseModel):
    panel_id: str
    site_id: str
    candidate_id: str
    panel_version: str
    current_rgb_path: str
    spectral_composite_path: str
    temporal_diff_path: str
    mapbox_context_path: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class Incident(BaseModel):
    incident_id: str
    site_id: str
    job_id: str
    analysis_time: datetime
    plume_likely: bool
    confidence: float = Field(ge=0.0, le=1.0)
    bbox_norm: List[float] = Field(min_length=4, max_length=4)
    likely_source_zone: LikelySourceZone
    persistence_score: float = Field(ge=0.0, le=1.0)
    priority_tier: PriorityTier
    severity_tier: SeverityTier
    review_status: ReviewStatus
    feedback_status: FeedbackStatus
    evidence_summary: str
    recommended_followup: str
    model_version: str


class ReviewAction(BaseModel):
    incident_id: str
    review_status: ReviewStatus
    feedback_status: Optional[FeedbackStatus] = None
    review_comment: Optional[str] = None


class EvaluationRecord(BaseModel):
    eval_id: str
    split: DataSplit
    site_id: str
    baseline_model: str
    candidate_model: str
    json_valid_rate: float = Field(ge=0.0, le=1.0)
    incident_f1: float = Field(ge=0.0, le=1.0)
    zone_accuracy: float = Field(ge=0.0, le=1.0)
    bbox_iou: float = Field(ge=0.0, le=1.0)
    human_usefulness_score: float = Field(ge=0.0, le=1.0)


class ScanRequest(BaseModel):
    force_refresh: bool = False
    progress_id: Optional[str] = None


class ScanResult(BaseModel):
    scan_id: str
    site_id: str
    incident_id: str
    status: str


class WatchlistScanRequest(BaseModel):
    site_ids: Optional[List[str]] = None
    force_refresh: bool = False
    progress_id: Optional[str] = None


class ExportResponse(BaseModel):
    format: str
    generated_at: datetime
    incident_count: int
    incidents: List[Incident]


class DongleReadingCreate(BaseModel):
    methane_ppm: float = Field(ge=0.0)
    captured_at: Optional[datetime] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    device_id: str = "dongle-v1"
    source: str = "field_dongle"
    notes: Optional[str] = None
    incident_id: Optional[str] = None


class DongleReading(BaseModel):
    reading_id: str
    site_id: str
    incident_id: Optional[str] = None
    methane_ppm: float = Field(ge=0.0)
    captured_at: datetime
    lat: float
    lon: float
    device_id: str
    source: str
    notes: Optional[str] = None


class WatchlistSummary(BaseModel):
    sites_monitored: int
    high_priority_alerts: int
    needs_review: int
    published_count: int
    dismissed_count: int
    last_scan_success_rate: float = Field(ge=0.0, le=1.0)
    last_updated: Optional[datetime] = None


class WatchlistRow(BaseModel):
    site_id: str
    name: str
    country: str
    operator: str
    lat: float
    lon: float
    watchlist_enabled: bool
    scan_id: Optional[str] = None
    scan_status: Optional[str] = None
    scan_created_at: Optional[str] = None
    generation_mode: Optional[str] = None
    incident_id: Optional[str] = None
    priority_tier: str = "low"
    severity_tier: str = "low"
    review_status: str = "needs_review"
    feedback_status: str = "unresolved"
    confidence: float = 0.0
    likely_source_zone: Optional[str] = None
    evidence_summary: str = "No incidents yet."


class IncidentListRow(BaseModel):
    incident_id: str
    site_id: str
    site_name: str
    location: str
    detected_zone: str
    confidence: float
    priority_tier: str
    review_status: str
    feedback_status: str
    detected_time: datetime
    assignee: Optional[str] = None
    comment_count: int = 0
    scan_id: Optional[str] = None


class IncidentCommentCreate(BaseModel):
    author_name: str = "operator"
    author_role: str = "reviewer"
    body: str


class IncidentComment(BaseModel):
    comment_id: str
    incident_id: str
    author_name: str
    author_role: str
    body: str
    created_at: datetime


class IncidentHistoryEvent(BaseModel):
    history_id: str
    incident_id: str
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    actor: str = "system"
    note: Optional[str] = None
    created_at: datetime


class IncidentAssignRequest(BaseModel):
    assignee_name: str
    assignee_role: str = "reviewer"
    sla_due_at: Optional[datetime] = None


class IncidentAssignment(BaseModel):
    incident_id: str
    assignee_name: str
    assignee_role: str
    assigned_at: datetime
    sla_due_at: Optional[datetime] = None


class IncidentDetailResponse(BaseModel):
    incident: Incident
    site: Site
    scan: Optional[Dict[str, Any]] = None
    evidence_summary: str
    metadata_block: Dict[str, Any] = Field(default_factory=dict)
    detection_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    decision_history: List[IncidentHistoryEvent] = Field(default_factory=list)
    comments: List[IncidentComment] = Field(default_factory=list)
    panel_previews: Dict[str, Optional[str]] = Field(default_factory=dict)
    assignment: Optional[IncidentAssignment] = None


class EvidencePackListRow(BaseModel):
    panel_id: str
    site_id: str
    site_name: str
    scan_id: str
    incident_id: Optional[str] = None
    scan_time: Optional[datetime] = None
    confidence: float = 0.0
    zone: Optional[str] = None
    status: str = "unknown"
    thumbnail_preview: Optional[str] = None
    asset_readiness: str = "partial"


class EvidencePackDetailResponse(BaseModel):
    panel_metadata: Dict[str, Any] = Field(default_factory=dict)
    current_image_preview: Optional[str] = None
    temporal_comparison_preview: Optional[str] = None
    map_preview: Optional[str] = None
    metadata_panel: Dict[str, Any] = Field(default_factory=dict)
    linked_incident: Optional[Incident] = None
    linked_scan: Optional[Dict[str, Any]] = None
    export_options: Dict[str, Any] = Field(default_factory=dict)


class ReviewQueueRow(BaseModel):
    incident_id: str
    site_name: str
    location: str
    detected_time: datetime
    priority_tier: str
    review_status: str
    assignee: Optional[str] = None
    sla_status: str = "unassigned"
    queue_position: int
    confidence: float


class SiteWatchlistSettings(BaseModel):
    site_id: str
    scan_cadence_hours: int = 24
    alert_threshold: float = 0.7
    change_detection_enabled: bool = True
    fallback_mode: str = "strict_live"
    notes: Optional[str] = None
    updated_at: datetime


class SiteWatchlistSettingsPatch(BaseModel):
    scan_cadence_hours: Optional[int] = None
    alert_threshold: Optional[float] = None
    change_detection_enabled: Optional[bool] = None
    fallback_mode: Optional[str] = None
    notes: Optional[str] = None


class SiteDetailResponse(BaseModel):
    site: Dict[str, Any]
    latest_scan: Optional[Dict[str, Any]] = None
    latest_incident: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    panel_previews: Dict[str, Optional[str]] = Field(default_factory=dict)
    dongle_readings: List[Dict[str, Any]] = Field(default_factory=list)
    site_metrics: Dict[str, Any] = Field(default_factory=dict)
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)
    watchlist_settings: Optional[SiteWatchlistSettings] = None
    latest_dongle_summary: Dict[str, Any] = Field(default_factory=dict)
    incident_history_preview: List[IncidentHistoryEvent] = Field(default_factory=list)
    last_scan_at: Optional[str] = None
    scan_cadence_hours: Optional[int] = None
