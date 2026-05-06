import base64
import asyncio
import json
import math
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, Response, StreamingResponse

from ..runtime import (
    get_candidate_service,
    get_inference_service,
    get_imagery_service,
    get_output_validation_service,
    get_panel_service,
    get_prompt_contract_service,
    get_repository,
    get_settings,
)
from ..schemas import (
    DongleReading,
    DongleReadingCreate,
    EvidencePackDetailResponse,
    EvidencePackListRow,
    EvidencePanel,
    ExportResponse,
    IncidentAssignRequest,
    IncidentAssignment,
    IncidentComment,
    IncidentCommentCreate,
    IncidentDetailResponse,
    IncidentHistoryEvent,
    IncidentListRow,
    Incident,
    ReviewQueueRow,
    ReviewAction,
    ScanRequest,
    ScanResult,
    Site,
    SiteDetailResponse,
    SiteWatchlistSettings,
    SiteWatchlistSettingsPatch,
    WatchlistSummary,
    WatchlistScanRequest,
)
from ..services.imagery_service import ImageryError
from ..services.inference_service import InferenceError
from ..services.output_validation_service import OutputValidationError, ValidationContext
from ..services.panel_service import PanelBuildError

router = APIRouter()

_SCAN_PROGRESS: Dict[str, Dict[str, Any]] = {}
_SIMSAT_REACHABILITY_CACHE: Dict[str, Any] = {}
_SIMSAT_REACHABILITY_TTL_SECONDS = 15
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DPHI_SIMSAT_REPOSITORY = "https://github.com/DPhi-Space/SimSat"
DPHI_SIMSAT_ENDPOINTS = [
    "/data/current/image/sentinel",
    "/data/image/sentinel",
    "/data/current/image/mapbox",
    "/data/image/mapbox",
]

_IMAGE_MAGIC_HEADERS = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIFF", "image/webp"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def _model_dump_jsonable(model):
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()  # type: ignore[attr-defined]


def _read_json_artifact(relative_path: str) -> Dict[str, Any]:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _dataset_manifest_summary() -> Dict[str, Any]:
    manifest = _read_json_artifact("data/manifests/dataset_manifest_v1.json")
    samples = manifest.get("samples") or []
    region_counts: Dict[str, int] = {}
    site_counts: Dict[str, int] = {}
    global_sites = set()
    for sample in samples:
        site_id = str(sample.get("site_id", ""))
        if site_id:
            site_counts[site_id] = site_counts.get(site_id, 0) + 1
        if site_id.startswith("LF_GLOBAL_"):
            global_sites.add(site_id)
        region = ((sample.get("provenance") or {}).get("region")) or "Europe/legacy"
        region_counts[str(region)] = region_counts.get(str(region), 0) + 1
    return {
        "sample_count": int(manifest.get("sample_count") or len(samples)),
        "unique_sites": len(site_counts),
        "global_unique_sites": len(global_sites),
        "split_counts": manifest.get("split_counts") or {},
        "region_counts": region_counts,
        "manifest_checksum": manifest.get("manifest_checksum"),
        "source_labels_path": manifest.get("source_labels_path"),
        "global_sites": sorted(global_sites),
    }


def _preview_data_url(local_path: str | None) -> str | None:
    if not local_path:
        return None
    path = Path(local_path)
    if not path.exists() or not path.is_file():
        return None
    raw = path.read_bytes()
    mime_type = None
    for signature, detected in _IMAGE_MAGIC_HEADERS:
        if raw.startswith(signature):
            mime_type = detected
            break
    if not mime_type:
        return None
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _progress(progress_id: str | None, stage: str, percent: int, message: str, **extra: Any) -> None:
    if not progress_id:
        return
    _SCAN_PROGRESS[progress_id] = {
        "progress_id": progress_id,
        "stage": stage,
        "percent": max(0, min(100, int(percent))),
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }


def _bbox_to_geojson(site: Site, bbox_norm: List[float] | None, scale_km: float = 2.4) -> Dict[str, Any] | None:
    if not bbox_norm or len(bbox_norm) != 4:
        return None
    x1, y1, x2, y2 = [float(v) for v in bbox_norm]
    x1, x2 = sorted((max(0.0, min(1.0, x1)), max(0.0, min(1.0, x2))))
    y1, y2 = sorted((max(0.0, min(1.0, y1)), max(0.0, min(1.0, y2))))
    lat_km = 111.32
    lon_km = max(1e-6, 111.32 * abs(math.cos(math.radians(site.lat))))
    lon_min = site.lon + ((x1 - 0.5) * scale_km / lon_km)
    lon_max = site.lon + ((x2 - 0.5) * scale_km / lon_km)
    lat_max = site.lat - ((y1 - 0.5) * scale_km / lat_km)
    lat_min = site.lat - ((y2 - 0.5) * scale_km / lat_km)
    coordinates = [[
        [lon_min, lat_min],
        [lon_max, lat_min],
        [lon_max, lat_max],
        [lon_min, lat_max],
        [lon_min, lat_min],
    ]]
    return {"type": "Polygon", "coordinates": coordinates}


def _incident_overlay_feature(repo, incident: Incident) -> Dict[str, Any] | None:
    site = repo.get_site(incident.site_id)
    if not site:
        return None
    geometry = _bbox_to_geojson(site, list(incident.bbox_norm), scale_km=3.0)
    if not geometry:
        return None
    scan = repo.get_scan_by_incident(incident.incident_id)
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "incident_id": incident.incident_id,
            "site_id": incident.site_id,
            "site_name": site.name,
            "scan_id": scan["scan_id"] if scan else None,
            "priority_tier": incident.priority_tier.value,
            "severity_tier": incident.severity_tier.value,
            "confidence": float(incident.confidence),
            "persistence_score": float(incident.persistence_score),
            "likely_source_zone": incident.likely_source_zone.value,
            "review_status": incident.review_status.value,
            "model_version": incident.model_version,
            "source": "model_bbox_norm",
        },
    }


def _priority_rank(value: str) -> int:
    ranks = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
    return ranks.get(str(value).lower(), 0)


def _inference_mode_from_scan(scan: Dict | None) -> str:
    if not scan:
        return ""
    metadata = (scan.get("evidence") or {}).get("metadata") or {}
    inference_mode = (metadata.get("inference") or {}).get("mode")
    if inference_mode:
        return str(inference_mode).lower()
    # Backward-compatible fallback for older scan records.
    return str(metadata.get("mode", "")).lower()


def _has_imagery_provenance(scan: Dict | None) -> bool:
    if not scan:
        return False
    metadata = (scan.get("evidence") or {}).get("metadata") or {}
    provenance = metadata.get("imagery_provenance") or {}
    source_chain = provenance.get("source_chain") or []
    return isinstance(source_chain, list) and len(source_chain) > 0


def _is_live_generated_scan(scan: Dict | None, incident: Incident | None) -> bool:
    if not scan or not incident:
        return False
    if str(scan.get("status", "")).lower() != "live":
        return False
    if _inference_mode_from_scan(scan) != "live":
        return False
    summary = str(incident.evidence_summary or "").strip().lower()
    if summary.startswith("fallback candidate output") or summary.startswith("phase 4 contract output"):
        return False
    return True


def _select_scan_and_incident(repo, site_id: str, require_live_results: bool) -> tuple[Dict | None, Incident | None]:
    scans = repo.list_scans_for_site(site_id=site_id, limit=50)
    if not scans:
        return None, None

    # Prefer high-confidence, fully-provenanced live records when available.
    for scan in scans:
        incident = repo.get_incident(scan["incident_id"]) if scan.get("incident_id") else None
        if _is_live_generated_scan(scan, incident) and _has_imagery_provenance(scan):
            return scan, incident

    if not require_live_results:
        first = scans[0]
        return first, repo.get_incident(first["incident_id"]) if first.get("incident_id") else None

    return None, None


def _dongle_hint_payload(reading: DongleReading | None) -> Dict:
    if not reading:
        return {"status": "satellite_only", "message": "No dongle corroboration attached."}
    return {
        "status": "dongle_corroborated",
        "message": f"Dongle methane reading attached: {reading.methane_ppm:.2f} ppm.",
        "reading": _model_dump_jsonable(reading),
    }


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _paginate(items: List[Dict[str, Any]], page: int, page_size: int) -> tuple[List[Dict[str, Any]], int]:
    safe_page = max(1, int(page))
    safe_page_size = max(1, int(page_size))
    total = len(items)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size
    return items[start:end], total


def _asset_readiness_from_paths(panel_paths: Dict[str, Any]) -> str:
    keys = [
        "current_rgb_path",
        "spectral_composite_path",
        "temporal_diff_path",
        "mapbox_context_path",
    ]
    present = sum(1 for k in keys if panel_paths.get(k))
    if present == len(keys):
        return "ready"
    if present == 0:
        return "missing"
    return "partial"


def _sla_status(assignment: IncidentAssignment | None) -> str:
    if not assignment:
        return "unassigned"
    if not assignment.sla_due_at:
        return "on_track"
    now = datetime.now(timezone.utc)
    if assignment.sla_due_at < now:
        return "overdue"
    if assignment.sla_due_at <= now + timedelta(hours=6):
        return "due_soon"
    return "on_track"


def _check_simsat_reachable(base_url: str) -> tuple[bool, str | None]:
    if not base_url:
        return False, "SIMSAT_BASE_URL is not configured"
    now = datetime.now(timezone.utc)
    cached = _SIMSAT_REACHABILITY_CACHE.get(base_url)
    if cached:
        age_seconds = (now - cached["checked_at"]).total_seconds()
        if age_seconds < _SIMSAT_REACHABILITY_TTL_SECONDS:
            return bool(cached["reachable"]), cached.get("error")
    try:
        req = urllib.request.Request(base_url)
        with urllib.request.urlopen(req, timeout=2) as resp:  # nosec B310 - trusted configured endpoint
            result = (200 <= int(resp.status) < 500, None)
    except Exception as exc:  # pragma: no cover - environment-dependent network check
        result = (False, str(exc))
    _SIMSAT_REACHABILITY_CACHE[base_url] = {
        "checked_at": now,
        "reachable": result[0],
        "error": result[1],
    }
    return result


def _query_float(request: Request, name: str, default: float | None = None) -> float:
    raw = request.query_params.get(name)
    if raw is None:
        if default is None:
            raise HTTPException(status_code=422, detail=f"missing query parameter: {name}")
        return float(default)
    try:
        return float(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid float query parameter: {name}") from exc


def _query_datetime(request: Request, name: str, default: datetime | None = None) -> datetime:
    raw = request.query_params.get(name)
    if not raw:
        if default is None:
            raise HTTPException(status_code=422, detail=f"missing query parameter: {name}")
        return default
    try:
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid datetime query parameter: {name}") from exc


def _direct_site_from_request(request: Request, lon_name: str = "lon", lat_name: str = "lat") -> Site:
    lon_default = float(os.getenv("SIMSAT_BOOT_LON", "10.0"))
    lat_default = float(os.getenv("SIMSAT_BOOT_LAT", "50.0"))
    lon = _query_float(request, lon_name, default=lon_default)
    lat = _query_float(request, lat_name, default=lat_default)
    return Site(
        site_id="DIRECT_LIVE_PROXY",
        name="Direct Live Proxy Location",
        lat=lat,
        lon=lon,
        country="direct",
        operator="direct-live",
        watchlist_enabled=False,
        polygon_geojson=None,
        metadata={"source": "direct_proxy"},
    )


def _direct_live_image_response(path: str, request: Request) -> Response:
    imagery = get_imagery_service()
    now = datetime.now(timezone.utc)
    try:
        if path.endswith("/image/sentinel"):
            site = _direct_site_from_request(request)
            query_dt = _query_datetime(request, "timestamp", default=now)
            body, metadata = imagery.fetch_direct_sentinel_at(site=site, query_dt=query_dt)
            headers = {
                "sentinel_metadata": json.dumps(
                    {
                        "image_available": True,
                        "source": metadata.get("source", "direct-sentinel"),
                        "spectral_bands": metadata.get("bands", ["RGB"]),
                        "footprint": metadata.get("footprint", []),
                        "size_km": get_settings().simsat_size_km,
                        "cloud_cover": metadata.get("cloud_cover", 0.0),
                        "datetime": metadata.get("timestamp_captured"),
                        "timestamp": metadata.get("timestamp_requested"),
                        "direct_live_fallback": True,
                    }
                ),
                "Access-Control-Expose-Headers": "sentinel_metadata",
            }
            return Response(content=body, media_type="image/jpeg", headers=headers)

        if path.endswith("/image/mapbox"):
            if path == "/data/image/mapbox":
                site = _direct_site_from_request(request, lon_name="lon_target", lat_name="lat_target")
            else:
                site = _direct_site_from_request(request)
            body, metadata = imagery.fetch_direct_mapbox_for_site(site)
            headers = {
                "mapbox_metadata": json.dumps(
                    {
                        "target_visible": True,
                        "image_available": True,
                        "timestamp": metadata.get("timestamp_requested"),
                        "source": metadata.get("source", "mapbox-direct"),
                        "direct_live_fallback": True,
                    }
                ),
                "Access-Control-Expose-Headers": "mapbox_metadata",
            }
            return Response(content=body, media_type="image/png", headers=headers)
    except ImageryError as exc:
        raise HTTPException(status_code=503, detail=f"direct live imagery unavailable: {exc}") from exc

    raise HTTPException(status_code=404, detail="unsupported image endpoint")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "landfillsentry-api"}


@router.get("/runtime/status")
def runtime_status() -> dict:
    settings = get_settings()
    live_modes_ready = (
        settings.simsat_mode == "live"
        and settings.mapbox_mode == "live"
        and settings.inference_mode == "live"
    )
    simsat_reachable, simsat_error = _check_simsat_reachable(settings.simsat_base_url)
    direct_live_available = bool(settings.mapbox_token or settings.mapbox_base_url)
    primary_imagery_available = simsat_reachable if settings.require_live_results else (simsat_reachable or direct_live_available)
    return {
        "status": "ok",
        "imagery_provider": "DPhi SimSat",
        "imagery_provider_repository": DPHI_SIMSAT_REPOSITORY,
        "simsat_required_endpoints": DPHI_SIMSAT_ENDPOINTS,
        "require_live_results": settings.require_live_results,
        "live_modes_ready": live_modes_ready,
        "live_scan_available": live_modes_ready and primary_imagery_available,
        "scan_policy": "strict_live" if settings.require_live_results else "fallback_allowed",
        "primary_imagery_available": primary_imagery_available,
        "simsat_mode": settings.simsat_mode,
        "mapbox_mode": settings.mapbox_mode,
        "inference_mode": settings.inference_mode,
        "inference_tooling": "Hugging Face Transformers + PEFT",
        "inference_backend": "transformers_peft",
        "base_model_id": settings.hf_model_id,
        "base_model_revision": settings.hf_model_revision,
        "adapter_id": settings.hf_adapter_id,
        "adapter_revision": settings.hf_adapter_revision,
        "simsat_base_url": settings.simsat_base_url,
        "simsat_reachable": simsat_reachable,
        "simsat_error": simsat_error,
        "direct_live_available": direct_live_available,
        "inference_allow_fallback": settings.inference_allow_fallback,
    }


@router.get("/scan-progress/{progress_id}")
async def stream_scan_progress(progress_id: str) -> StreamingResponse:
    async def events():
        last_payload = None
        for _ in range(900):
            payload = _SCAN_PROGRESS.get(progress_id) or {
                "progress_id": progress_id,
                "stage": "waiting",
                "percent": 0,
                "message": "Waiting for scan to start.",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            encoded = json.dumps(payload)
            if encoded != last_payload:
                yield f"data: {encoded}\n\n"
                last_payload = encoded
            if payload.get("stage") in {"complete", "failed"}:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/overlays/plumes")
def list_plume_overlays(
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
) -> dict:
    repo = get_repository()
    features = []
    for incident in repo.list_incidents():
        if status and incident.review_status.value != status:
            continue
        if priority and incident.priority_tier.value != priority:
            continue
        feature = _incident_overlay_feature(repo, incident)
        if feature:
            features.append(feature)
    return {
        "type": "FeatureCollection",
        "features": features,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "real_incident_model_bbox",
    }


@router.get("/incidents/{incident_id}/overlay")
def get_incident_overlay(incident_id: str) -> dict:
    repo = get_repository()
    incident = repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    feature = _incident_overlay_feature(repo, incident)
    if not feature:
        raise HTTPException(status_code=404, detail="overlay unavailable")
    return feature


@router.get("/ops/summary")
def ops_summary() -> dict:
    repo = get_repository()
    settings = get_settings()
    items = _build_watchlist_items(repo=repo, require_live_results=settings.require_live_results)
    incidents = repo.list_incidents()
    by_country: Dict[str, int] = {}
    by_operator: Dict[str, int] = {}
    for item in items:
        by_country[item["country"]] = by_country.get(item["country"], 0) + 1
        by_operator[item["operator"]] = by_operator.get(item["operator"], 0) + 1
    recent = sorted(
        [
            {
                "incident_id": inc.incident_id,
                "site_id": inc.site_id,
                "priority_tier": inc.priority_tier.value,
                "review_status": inc.review_status.value,
                "confidence": float(inc.confidence),
                "analysis_time": inc.analysis_time.isoformat(),
            }
            for inc in incidents
        ],
        key=lambda row: row["analysis_time"],
        reverse=True,
    )[:8]
    return {
        "summary": _model_dump_jsonable(_watchlist_summary(items)),
        "active_alerts": len([i for i in items if i.get("review_status") in {"proposed", "needs_review"}]),
        "published_incidents": len([i for i in incidents if i.review_status.value == "published"]),
        "dismissed_incidents": len([i for i in incidents if i.review_status.value == "dismissed"]),
        "top_countries": sorted(by_country.items(), key=lambda kv: kv[1], reverse=True)[:5],
        "top_operators": sorted(by_operator.items(), key=lambda kv: kv[1], reverse=True)[:5],
        "recent_incidents": recent,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ops/global-dataset")
def ops_global_dataset() -> dict:
    probe = _read_json_artifact("data/processed/global_live_api_probe_report.json")
    collection = _read_json_artifact("data/processed/global_live_scan_collection_report.json")
    checkpoint = _read_json_artifact("data/manifests/tuned_checkpoint_v1.json")
    checkpoint_result = checkpoint.get("result") or {}
    probe_sites = probe.get("sites") or []
    probe_ok = len([site for site in probe_sites if site.get("probe_ok")])
    collection_sites = collection.get("sites") or []
    collection_success_sites = len([site for site in collection_sites if int(site.get("success_count") or 0) > 0])
    return {
        "status": "ok",
        "dataset": _dataset_manifest_summary(),
        "api_probe": {
            "candidate_sites": len(probe_sites),
            "probe_ok_sites": probe_ok,
            "report_path": "docs/global_live_api_probe_report.md",
            "generated_at": probe.get("generated_at"),
        },
        "latest_collection_batch": {
            "success_count": int(collection.get("success_count") or 0),
            "failure_count": int(collection.get("failure_count") or 0),
            "unique_successful_sites": int(collection.get("unique_successful_sites") or collection_success_sites),
            "report_path": "docs/global_live_scan_collection_report.md",
            "generated_at": collection.get("generated_at"),
        },
        "training": {
            "run_id": checkpoint_result.get("run_id"),
            "adapter_artifact_ref": checkpoint_result.get("adapter_artifact_ref"),
            "training_mode": checkpoint_result.get("training_mode"),
            "status": checkpoint_result.get("status"),
            "checkpoint_record_path": "data/manifests/tuned_checkpoint_v1.json",
        },
        "manual_labeling": {
            "review_queue_path": "data/labels/manual_label_review_queue.csv",
            "corrections_path": "data/labels/manual_label_corrections.csv",
            "template_path": "data/labels/manual_label_corrections.template.csv",
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _proxy_simsat_image_endpoint(path: str, request: Request) -> Response:
    settings = get_settings()
    if not settings.simsat_base_url:
        raise HTTPException(status_code=503, detail="SIMSAT_BASE_URL is not configured")

    query = request.url.query
    url = f"{settings.simsat_base_url}{path}"
    if query:
        url = f"{url}?{query}"

    req = urllib.request.Request(url)
    if settings.simsat_api_key:
        req.add_header("Authorization", f"Bearer {settings.simsat_api_key}")

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:  # nosec B310 - trusted configured endpoint
            body = resp.read()
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
            passthrough_headers: Dict[str, str] = {}
            sentinel_meta = resp.headers.get("sentinel_metadata")
            mapbox_meta = resp.headers.get("mapbox_metadata")
            cache_control = resp.headers.get("Cache-Control")
            if sentinel_meta:
                passthrough_headers["sentinel_metadata"] = sentinel_meta
            if mapbox_meta:
                passthrough_headers["mapbox_metadata"] = mapbox_meta
            if cache_control:
                passthrough_headers["Cache-Control"] = cache_control
            return Response(content=body, media_type=content_type, headers=passthrough_headers)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network path
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            detail = ""
        message = detail[:240] if detail else str(exc.reason)
        try:
            return _direct_live_image_response(path, request)
        except HTTPException:
            raise HTTPException(status_code=exc.code, detail=f"simsat upstream error: {message}") from exc
    except Exception as exc:  # pragma: no cover - network path
        try:
            return _direct_live_image_response(path, request)
        except HTTPException as fallback_exc:
            raise HTTPException(
                status_code=503,
                detail=f"simsat upstream unavailable: {exc}; direct fallback failed: {fallback_exc.detail}",
            ) from exc


@router.get("/data/current/image/sentinel")
def proxy_data_current_image_sentinel(request: Request) -> Response:
    return _proxy_simsat_image_endpoint("/data/current/image/sentinel", request)


@router.get("/data/current/image/mapbox")
def proxy_data_current_image_mapbox(request: Request) -> Response:
    return _proxy_simsat_image_endpoint("/data/current/image/mapbox", request)


@router.get("/data/image/sentinel")
def proxy_data_image_sentinel(request: Request) -> Response:
    return _proxy_simsat_image_endpoint("/data/image/sentinel", request)


@router.get("/data/image/mapbox")
def proxy_data_image_mapbox(request: Request) -> Response:
    return _proxy_simsat_image_endpoint("/data/image/mapbox", request)


@router.post("/sites", response_model=Site)
def register_site(site: Site) -> Site:
    repo = get_repository()
    if not repo.register_site(site):
        raise HTTPException(status_code=409, detail="site already exists")
    return site


@router.get("/sites", response_model=List[Site])
def list_sites() -> List[Site]:
    repo = get_repository()
    return repo.list_sites()


def _build_watchlist_items(
    repo,
    require_live_results: bool,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for site in repo.list_watchlist_sites():
        latest_scan, latest_incident = _select_scan_and_incident(
            repo=repo,
            site_id=site.site_id,
            require_live_results=require_live_results,
        )
        item = {
            "site_id": site.site_id,
            "name": site.name,
            "country": site.country,
            "operator": site.operator,
            "lat": site.lat,
            "lon": site.lon,
            "watchlist_enabled": site.watchlist_enabled,
            "scan_id": latest_scan["scan_id"] if latest_scan else None,
            "scan_status": latest_scan["status"] if latest_scan else None,
            "scan_created_at": latest_scan["created_at"] if latest_scan else None,
            "generation_mode": _inference_mode_from_scan(latest_scan) if latest_scan else None,
            "incident_id": latest_incident.incident_id if latest_incident else None,
            "priority_tier": latest_incident.priority_tier.value if latest_incident else "low",
            "severity_tier": latest_incident.severity_tier.value if latest_incident else "low",
            "review_status": latest_incident.review_status.value if latest_incident else "needs_review",
            "feedback_status": latest_incident.feedback_status.value if latest_incident else "unresolved",
            "confidence": float(latest_incident.confidence) if latest_incident else 0.0,
            "likely_source_zone": latest_incident.likely_source_zone.value if latest_incident else None,
            "evidence_summary": latest_incident.evidence_summary if latest_incident else "No incidents yet.",
        }
        items.append(item)
    items.sort(
        key=lambda it: (
            _priority_rank(it["priority_tier"]),
            float(it["confidence"]),
            str(it["scan_created_at"] or ""),
        ),
        reverse=True,
    )
    return items


def _watchlist_summary(items: List[Dict[str, Any]]) -> WatchlistSummary:
    sites_monitored = len(items)
    high_priority_alerts = sum(1 for i in items if i.get("priority_tier") in {"high", "urgent"})
    needs_review = sum(1 for i in items if i.get("review_status") == "needs_review")
    published_count = sum(1 for i in items if i.get("review_status") == "published")
    dismissed_count = sum(1 for i in items if i.get("review_status") == "dismissed")
    scanned = [i for i in items if i.get("scan_id")]
    successful = [i for i in scanned if str(i.get("scan_status", "")).lower() == "live"]
    success_rate = float(len(successful) / len(scanned)) if scanned else 0.0
    timestamps = [_parse_iso_datetime(i.get("scan_created_at")) for i in items]
    timestamps = [ts for ts in timestamps if ts is not None]
    last_updated = max(timestamps) if timestamps else None
    return WatchlistSummary(
        sites_monitored=sites_monitored,
        high_priority_alerts=high_priority_alerts,
        needs_review=needs_review,
        published_count=published_count,
        dismissed_count=dismissed_count,
        last_scan_success_rate=success_rate,
        last_updated=last_updated,
    )


@router.get("/watchlist/summary", response_model=WatchlistSummary)
def get_watchlist_summary() -> WatchlistSummary:
    repo = get_repository()
    settings = get_settings()
    items = _build_watchlist_items(repo=repo, require_live_results=settings.require_live_results)
    return _watchlist_summary(items)


@router.get("/watchlist")
def get_watchlist(
    priority: Optional[str] = None,
    review_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "priority",
    selected_site_id: Optional[str] = None,
    include_summary: bool = False,
) -> dict:
    repo = get_repository()
    settings = get_settings()
    items = _build_watchlist_items(repo=repo, require_live_results=settings.require_live_results)

    if priority:
        items = [i for i in items if i.get("priority_tier") == priority]
    if review_status:
        items = [i for i in items if i.get("review_status") == review_status]

    if sort_by == "last_scan":
        items.sort(key=lambda i: str(i.get("scan_created_at") or ""), reverse=True)
    elif sort_by == "confidence":
        items.sort(key=lambda i: float(i.get("confidence") or 0.0), reverse=True)

    paged, total = _paginate(items, page=page, page_size=page_size)
    selected = None
    if selected_site_id:
        selected = next((it for it in items if it.get("site_id") == selected_site_id), None)

    payload: Dict[str, Any] = {
        "count": len(paged),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": paged,
    }
    if selected is not None:
        payload["selected"] = selected
    if include_summary:
        payload["summary"] = _model_dump_jsonable(_watchlist_summary(items))
    return payload


@router.get("/sites/{site_id}", response_model=Site)
def get_site(site_id: str) -> Site:
    repo = get_repository()
    site = repo.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")
    return site


@router.get("/sites/{site_id}/settings", response_model=SiteWatchlistSettings)
def get_site_settings(site_id: str) -> SiteWatchlistSettings:
    repo = get_repository()
    site = repo.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")
    return repo.get_site_settings(site_id)


@router.patch("/sites/{site_id}/settings", response_model=SiteWatchlistSettings)
def patch_site_settings(site_id: str, payload: SiteWatchlistSettingsPatch) -> SiteWatchlistSettings:
    repo = get_repository()
    site = repo.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")
    current = repo.get_site_settings(site_id)
    updates = payload.model_dump(exclude_none=True) if hasattr(payload, "model_dump") else payload.dict(exclude_none=True)
    base = current.model_dump() if hasattr(current, "model_dump") else current.dict()
    base.update(updates)
    base["updated_at"] = datetime.now(timezone.utc)
    merged = SiteWatchlistSettings(**base)
    repo.save_site_settings(merged)
    return merged


@router.post("/sites/{site_id}/dongle-readings", response_model=DongleReading)
def ingest_dongle_reading(site_id: str, payload: DongleReadingCreate) -> DongleReading:
    repo = get_repository()
    site = repo.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")
    reading = DongleReading(
        reading_id=f"dr_{uuid4().hex[:12]}",
        site_id=site_id,
        incident_id=payload.incident_id,
        methane_ppm=float(payload.methane_ppm),
        captured_at=payload.captured_at or datetime.now(timezone.utc),
        lat=float(payload.lat if payload.lat is not None else site.lat),
        lon=float(payload.lon if payload.lon is not None else site.lon),
        device_id=payload.device_id,
        source=payload.source,
        notes=payload.notes,
    )
    repo.save_dongle_reading(reading)
    return reading


@router.get("/sites/{site_id}/dongle-readings", response_model=List[DongleReading])
def list_dongle_readings(site_id: str, limit: int = Query(default=20, ge=1, le=200)) -> List[DongleReading]:
    repo = get_repository()
    if not repo.get_site(site_id):
        raise HTTPException(status_code=404, detail="site not found")
    return repo.list_dongle_readings_for_site(site_id=site_id, limit=limit)


@router.get("/sites/{site_id}/detail", response_model=SiteDetailResponse)
def get_site_detail(site_id: str) -> dict:
    repo = get_repository()
    settings = get_settings()
    site = repo.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")

    latest_scan, latest_incident = _select_scan_and_incident(
        repo=repo,
        site_id=site_id,
        require_live_results=settings.require_live_results,
    )
    site_scans = repo.list_scans_for_site(site_id=site_id, limit=200)
    site_incidents = [inc for inc in repo.list_incidents() if inc.site_id == site_id]
    total_scans = len(site_scans)
    live_scans = len([s for s in site_scans if str(s.get("status", "")).lower() == "live"])
    total_incidents = len(site_incidents)
    high_priority = len([i for i in site_incidents if i.priority_tier.value in {"high", "urgent"}])
    avg_confidence = float(sum(float(i.confidence) for i in site_incidents) / total_incidents) if total_incidents else 0.0
    watchlist_settings = repo.get_site_settings(site_id)
    recent_history: List[IncidentHistoryEvent] = []
    for incident in site_incidents:
        recent_history.extend(repo.list_incident_history(incident.incident_id, limit=5))
    recent_history.sort(key=lambda ev: ev.created_at, reverse=True)
    incident_history_preview = recent_history[:5]
    dongle_recent = repo.list_dongle_readings_for_site(site_id, limit=5)
    latest_dongle = dongle_recent[0] if dongle_recent else None

    if not latest_scan:
        payload = SiteDetailResponse(
            site=_model_dump_jsonable(site),
            latest_scan=None,
            latest_incident=_model_dump_jsonable(latest_incident) if latest_incident else None,
            evidence=None,
            panel_previews={},
            dongle_readings=[_model_dump_jsonable(r) for r in dongle_recent],
            site_metrics={
                "total_scans": total_scans,
                "live_scans": live_scans,
                "total_incidents": total_incidents,
                "high_priority_incidents": high_priority,
                "avg_confidence": avg_confidence,
            },
            recent_activity=[_model_dump_jsonable(ev) for ev in incident_history_preview],
            watchlist_settings=watchlist_settings,
            latest_dongle_summary=_model_dump_jsonable(latest_dongle) if latest_dongle else {},
            incident_history_preview=incident_history_preview,
            last_scan_at=None,
            scan_cadence_hours=watchlist_settings.scan_cadence_hours,
        )
        return _model_dump_jsonable(payload)

    evidence = latest_scan["evidence"]
    panel_paths = evidence.get("panel_paths", {})
    panel_previews = {
        "current_rgb": _preview_data_url(panel_paths.get("current_rgb_path")),
        "spectral_composite": _preview_data_url(panel_paths.get("spectral_composite_path")),
        "temporal_diff": _preview_data_url(panel_paths.get("temporal_diff_path")),
        "mapbox_context": _preview_data_url(panel_paths.get("mapbox_context_path")),
    }
    payload = SiteDetailResponse(
        site=_model_dump_jsonable(site),
        latest_scan=latest_scan,
        latest_incident=_model_dump_jsonable(latest_incident) if latest_incident else None,
        evidence=evidence,
        panel_previews=panel_previews,
        dongle_readings=[_model_dump_jsonable(r) for r in dongle_recent],
        site_metrics={
            "total_scans": total_scans,
            "live_scans": live_scans,
            "total_incidents": total_incidents,
            "high_priority_incidents": high_priority,
            "avg_confidence": avg_confidence,
        },
        recent_activity=[_model_dump_jsonable(ev) for ev in incident_history_preview],
        watchlist_settings=watchlist_settings,
        latest_dongle_summary=_model_dump_jsonable(latest_dongle) if latest_dongle else {},
        incident_history_preview=incident_history_preview,
        last_scan_at=latest_scan.get("created_at"),
        scan_cadence_hours=watchlist_settings.scan_cadence_hours,
    )
    return _model_dump_jsonable(payload)


def _build_evidence_payload(
    panel: EvidencePanel,
    mode: str,
    assets: Dict,
    candidate_payload: Dict,
    candidate_diagnostics: Dict,
    prompt_bundle: Dict,
    schema_validation_trace: Dict,
    inference_trace: Dict,
    ground_truth_hint: Dict,
) -> Dict:
    current = assets["current"]
    historical = assets["historical"]
    mapbox = assets["mapbox"]
    imagery_provenance = {
        "provider": "DPhi SimSat",
        "provider_repository": DPHI_SIMSAT_REPOSITORY,
        "api_base_url": get_settings().simsat_base_url,
        "source_chain": [
            "dphi_simsat_sentinel_current",
            "dphi_simsat_sentinel_historical",
            "dphi_simsat_mapbox_context",
        ],
        "endpoints": {
            "sentinel_current": "/data/current/image/sentinel",
            "sentinel_historical": "/data/image/sentinel",
            "mapbox_context": "/data/current/image/mapbox",
        },
        "live_fetch_status": mode,
        "assets": {
            "sentinel_current": {
                "source": current.source,
                "timestamp_captured": current.timestamp_captured.isoformat(),
                "cloud_cover": current.cloud_cover,
                "bands": list(current.bands),
                "local_path": current.local_path,
            },
            "sentinel_historical": {
                "source": historical.source,
                "timestamp_captured": historical.timestamp_captured.isoformat(),
                "cloud_cover": historical.cloud_cover,
                "bands": list(historical.bands),
                "local_path": historical.local_path,
            },
            "mapbox_context": {
                "source": mapbox.source,
                "timestamp_captured": mapbox.timestamp_captured.isoformat(),
                "cloud_cover": mapbox.cloud_cover,
                "bands": list(mapbox.bands),
                "local_path": mapbox.local_path,
                "note": "High-resolution context imagery; may be static/non-time-dependent.",
            },
        },
    }
    return {
        "panel_paths": {
            "current_rgb_path": panel.current_rgb_path,
            "spectral_composite_path": panel.spectral_composite_path,
            "temporal_diff_path": panel.temporal_diff_path,
            "mapbox_context_path": panel.mapbox_context_path,
            "evidence_panel_path": panel.metadata_json.get("panel_artifact_path"),
        },
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "panel_id": panel.panel_id,
            "panel_version": panel.panel_version,
            "layout_version": panel.metadata_json.get("layout_version"),
            "metadata_text": panel.metadata_json.get("metadata_text"),
            "cloud_cover_current": assets["current"].cloud_cover,
            "cloud_cover_historical": assets["historical"].cloud_cover,
            "candidate": candidate_payload,
            "candidate_diagnostics": candidate_diagnostics,
            "prompt_contract": {
                "prompt_contract_version": prompt_bundle.get("prompt_contract_version"),
                "output_schema_version": prompt_bundle.get("output_schema_version"),
            },
            "schema_validation": schema_validation_trace,
            "inference": inference_trace,
            "imagery_provenance": imagery_provenance,
            "ground_truth_hint": ground_truth_hint,
        },
    }


@router.post("/sites/{site_id}/scan", response_model=ScanResult)
def scan_site(site_id: str, request: ScanRequest) -> ScanResult:
    repo = get_repository()
    settings = get_settings()
    imagery_service = get_imagery_service()
    candidate_service = get_candidate_service()
    inference_service = get_inference_service()
    panel_service = get_panel_service()
    prompt_contract_service = get_prompt_contract_service()
    output_validation_service = get_output_validation_service()

    if settings.require_live_results:
        if settings.simsat_mode != "live" or settings.mapbox_mode != "live" or settings.inference_mode != "live":
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "live_mode_required",
                    "message": "REQUIRE_LIVE_RESULTS=true requires SIMSAT_MODE=live, MAPBOX_MODE=live, INFERENCE_MODE=live",
                },
            )

    site = repo.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")

    _progress(request.progress_id, "fetching_imagery", 12, "Fetching live satellite and context imagery.", site_id=site_id)
    try:
        assets, mode = imagery_service.fetch_site_bundle(site=site, force_refresh=request.force_refresh)
    except ImageryError as exc:
        _progress(request.progress_id, "failed", 100, str(exc), site_id=site_id)
        raise HTTPException(
            status_code=424,
            detail={
                "error": "imagery_unavailable",
                "message": str(exc),
                "site_id": site_id,
            },
        ) from exc
    if settings.require_live_results and mode != "live":
        _progress(request.progress_id, "failed", 100, "Strict live imagery unavailable.", site_id=site_id)
        raise HTTPException(
            status_code=424,
            detail={
                "error": "live_imagery_required",
                "message": (
                    "Strict live mode is enabled and live imagery was unavailable for this scan. "
                    "No fallback scan was created."
                ),
                "site_id": site_id,
                "live_fetch_status": mode,
            },
        )

    scan_index = repo.next_scan_index()
    scan_id = f"scan_{scan_index:03d}"
    incident_id = f"inc_{scan_index:03d}"

    for asset in assets.values():
        repo.save_image_asset(asset)

    _progress(request.progress_id, "candidate_generation", 30, "Generating candidate plume geometry.", site_id=site_id)
    candidate_result = candidate_service.generate(site=site, assets=assets, job_id=scan_id)
    repo.save_candidate(scan_id=scan_id, candidate=candidate_result.candidate, diagnostics=candidate_result.diagnostics)

    candidate_payload = (
        candidate_result.candidate.model_dump(mode="json")
        if hasattr(candidate_result.candidate, "model_dump")
        else candidate_result.candidate.dict()
    )
    try:
        _progress(request.progress_id, "panel_build", 45, "Building evidence panel previews.", site_id=site_id, scan_id=scan_id)
        panel_result = panel_service.build(
            site=site,
            assets=assets,
            candidate=candidate_result.candidate,
            mode=mode,
        )
    except PanelBuildError as exc:
        _progress(request.progress_id, "failed", 100, str(exc), site_id=site_id, scan_id=scan_id)
        raise HTTPException(
            status_code=500,
            detail={"error": "panel_build_failed", "message": str(exc), "site_id": site_id},
        ) from exc
    repo.save_evidence_panel(scan_id=scan_id, panel=panel_result.panel)

    prompt_bundle = prompt_contract_service.build_prompt_bundle(
        site=site,
        panel=panel_result.panel,
        candidate=candidate_result.candidate,
    ).as_dict()

    try:
        _progress(request.progress_id, "inference", 62, "Running live incident inference.", site_id=site_id, scan_id=scan_id)
        inference_result = inference_service.generate_incident_outputs(
            site=site,
            panel=panel_result.panel,
            prompt_bundle=prompt_bundle,
            candidate=candidate_result.candidate,
            incident_id=incident_id,
            scan_id=scan_id,
        )
    except InferenceError as exc:
        _progress(request.progress_id, "failed", 100, str(exc), site_id=site_id, scan_id=scan_id)
        raise HTTPException(
            status_code=424,
            detail={
                "error": "inference_live_failed",
                "message": str(exc),
                "site_id": site_id,
                "mode_required": "live",
            },
        ) from exc
    fallback_summary = (
        f"Candidate score {candidate_result.candidate.candidate_score:.2f} with "
        f"zone prior {candidate_result.candidate.likely_source_zone_prior.value}."
    )
    context = ValidationContext(
        incident_id=incident_id,
        site_id=site_id,
        job_id=scan_id,
        model_version=inference_result.model_ref,
        fallback_bbox=list(candidate_result.candidate.bbox_norm),
        fallback_confidence=float(candidate_result.candidate.candidate_score),
        fallback_recurrence=float(candidate_result.candidate.temporal_recurrence),
        fallback_zone=candidate_result.candidate.likely_source_zone_prior.value,
        fallback_evidence_summary=fallback_summary,
    )
    try:
        _progress(request.progress_id, "validation", 78, "Validating model output contract.", site_id=site_id, scan_id=scan_id)
        validation_result = output_validation_service.validate_with_retry(
            raw_outputs=inference_result.raw_outputs,
            context=context,
        )
    except OutputValidationError as exc:
        _progress(request.progress_id, "failed", 100, str(exc), site_id=site_id, scan_id=scan_id)
        raise HTTPException(
            status_code=424,
            detail={
                "error": "inference_output_invalid",
                "message": str(exc),
                "scan_id": scan_id,
                "mode_required": "live",
            },
        ) from exc

    latest_unlinked = repo.get_latest_unlinked_dongle_for_site(site_id=site_id)
    linked_reading = None
    if latest_unlinked:
        linked_reading = repo.attach_dongle_reading_to_incident(
            reading_id=latest_unlinked.reading_id,
            incident_id=validation_result.incident.incident_id,
        )
    if linked_reading is None:
        incident_readings = repo.list_dongle_readings_for_incident(validation_result.incident.incident_id)
        if incident_readings:
            linked_reading = incident_readings[0]

    repo.save_incident(validation_result.incident)
    repo.save_incident_history_event(
        IncidentHistoryEvent(
            history_id=f"hist_{uuid4().hex[:12]}",
            incident_id=validation_result.incident.incident_id,
            event_type="incident_created",
            from_status=None,
            to_status=validation_result.incident.review_status.value,
            actor="system",
            note=f"Incident generated from scan {scan_id}.",
            created_at=datetime.now(timezone.utc),
        )
    )

    evidence = _build_evidence_payload(
        panel=panel_result.panel,
        mode=mode,
        assets=assets,
        candidate_payload=candidate_payload,
        candidate_diagnostics=candidate_result.diagnostics,
        prompt_bundle=prompt_bundle,
        schema_validation_trace=validation_result.as_dict(),
        inference_trace={
            "mode": inference_result.mode,
            "model_id": inference_result.model_id,
            "model_revision": inference_result.model_revision,
            "model_ref": inference_result.model_ref,
            "auth_configured": inference_result.auth_configured,
        },
        ground_truth_hint=_dongle_hint_payload(linked_reading),
    )
    repo.save_scan(
        scan_id=scan_id,
        site_id=site_id,
        incident_id=incident_id,
        status=mode,
        evidence=evidence,
    )

    _progress(
        request.progress_id,
        "complete",
        100,
        "Scan complete. Incident, evidence, and plume overlays are available.",
        site_id=site_id,
        scan_id=scan_id,
        incident_id=incident_id,
    )
    return ScanResult(scan_id=scan_id, site_id=site_id, incident_id=incident_id, status=mode)


@router.get("/scans/{scan_id}", response_model=ScanResult)
def get_scan_result(scan_id: str) -> ScanResult:
    repo = get_repository()
    scan = repo.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="scan not found")
    return ScanResult(
        scan_id=scan["scan_id"],
        site_id=scan["site_id"],
        incident_id=scan["incident_id"],
        status=scan["status"],
    )


@router.get("/scans/{scan_id}/evidence")
def get_scan_evidence(scan_id: str) -> dict:
    repo = get_repository()
    scan = repo.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="scan not found")
    candidate_bundle = repo.get_candidate_by_scan(scan_id)
    panel_bundle = repo.get_evidence_panel_by_scan(scan_id)
    candidate_data = candidate_bundle["candidate"] if candidate_bundle else None
    candidate_diagnostics = candidate_bundle["diagnostics"] if candidate_bundle else None
    return {
        "scan_id": scan_id,
        "incident_id": scan["incident_id"],
        "panel_paths": scan["evidence"]["panel_paths"],
        "metadata": {
            **scan["evidence"]["metadata"],
            "status": scan["status"],
            "created_at": scan["created_at"],
            "candidate": candidate_data or scan["evidence"]["metadata"].get("candidate"),
            "candidate_diagnostics": candidate_diagnostics
            or scan["evidence"]["metadata"].get("candidate_diagnostics"),
            "panel": panel_bundle or scan["evidence"]["metadata"].get("panel"),
        },
    }


@router.get("/incidents")
def list_incidents_api(
    state: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    site_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict:
    repo = get_repository()
    rows, total = repo.list_incident_rows(
        state=state,
        priority=priority,
        status=status,
        site_id=site_id,
        page=page,
        page_size=page_size,
    )
    typed = [IncidentListRow(**row) for row in rows]
    return {
        "count": len(typed),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_model_dump_jsonable(row) for row in typed],
    }


@router.get("/review-queue")
def get_review_queue(
    status: Optional[str] = Query(default=None),
    assignee: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict:
    repo = get_repository()
    rows, _total = repo.list_incident_rows(
        state=status,
        priority=priority,
        status=status,
        site_id=None,
        page=1,
        page_size=100000,
    )
    if assignee:
        rows = [r for r in rows if (r.get("assignee") or "").lower() == assignee.lower()]
    summary = {
        "new": len([r for r in rows if r.get("review_status") == "proposed"]),
        "in_review": len([r for r in rows if r.get("review_status") == "needs_review"]),
        "escalated": len(
            [
                r
                for r in rows
                if r.get("priority_tier") in {"high", "urgent"}
                and r.get("review_status") in {"proposed", "needs_review"}
            ]
        ),
        "ready_to_publish": len(
            [
                r
                for r in rows
                if r.get("feedback_status") == "confirmed"
                and r.get("review_status") in {"proposed", "needs_review"}
            ]
        ),
    }
    rows.sort(
        key=lambda r: (_priority_rank(str(r.get("priority_tier"))), r.get("detected_time")),
        reverse=True,
    )
    queue_rows: List[ReviewQueueRow] = []
    for idx, row in enumerate(rows, start=1):
        assignment = repo.get_incident_assignment(row["incident_id"])
        queue_rows.append(
            ReviewQueueRow(
                incident_id=row["incident_id"],
                site_name=row["site_name"],
                location=row["location"],
                detected_time=row["detected_time"],
                priority_tier=row["priority_tier"],
                review_status=row["review_status"],
                assignee=row.get("assignee"),
                sla_status=_sla_status(assignment),
                queue_position=idx,
                confidence=float(row.get("confidence", 0.0)),
            )
        )

    typed_rows = [_model_dump_jsonable(r) for r in queue_rows]
    paged, total = _paginate(typed_rows, page=page, page_size=page_size)
    return {
        "summary": summary,
        "count": len(paged),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": paged,
    }


@router.get("/evidence-packs")
def list_evidence_packs(
    status: Optional[str] = Query(default=None),
    quality: Optional[str] = Query(default=None),
    site_id: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict:
    repo = get_repository()
    from_dt = _parse_iso_datetime(from_date)
    to_dt = _parse_iso_datetime(to_date)
    records = repo.list_evidence_panel_records()
    rows: List[EvidencePackListRow] = []
    for rec in records:
        if site_id and rec["site_id"] != site_id:
            continue
        scan = repo.get_scan(rec["scan_id"])
        if not scan:
            continue
        incident = repo.get_incident(scan["incident_id"]) if scan.get("incident_id") else None
        site = repo.get_site(rec["site_id"])
        scan_dt = _parse_iso_datetime(scan.get("created_at"))
        if from_dt and scan_dt and scan_dt < from_dt:
            continue
        if to_dt and scan_dt and scan_dt > to_dt:
            continue
        panel_paths = (scan.get("evidence") or {}).get("panel_paths", {})
        readiness = _asset_readiness_from_paths(panel_paths)
        if quality and readiness != quality:
            continue
        row_status = incident.review_status.value if incident else scan.get("status", "unknown")
        if status and row_status != status:
            continue
        thumb = _preview_data_url(panel_paths.get("current_rgb_path"))
        rows.append(
            EvidencePackListRow(
                panel_id=rec["panel_id"],
                site_id=rec["site_id"],
                site_name=site.name if site else rec["site_id"],
                scan_id=rec["scan_id"],
                incident_id=scan.get("incident_id"),
                scan_time=scan_dt,
                confidence=float(incident.confidence) if incident else 0.0,
                zone=incident.likely_source_zone.value if incident else None,
                status=row_status,
                thumbnail_preview=thumb,
                asset_readiness=readiness,
            )
        )
    rows.sort(key=lambda r: r.scan_time or datetime.fromtimestamp(0, tz=timezone.utc), reverse=True)
    typed = [_model_dump_jsonable(r) for r in rows]
    paged, total = _paginate(typed, page=page, page_size=page_size)
    return {
        "count": len(paged),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": paged,
    }


@router.get("/evidence-packs/{panel_id}", response_model=EvidencePackDetailResponse)
def get_evidence_pack_detail(panel_id: str) -> EvidencePackDetailResponse:
    repo = get_repository()
    rec = repo.get_evidence_panel_record(panel_id)
    if not rec:
        raise HTTPException(status_code=404, detail="evidence panel not found")
    scan = repo.get_scan(rec["scan_id"])
    if not scan:
        raise HTTPException(status_code=404, detail="scan not found for panel")
    incident = repo.get_incident(scan["incident_id"]) if scan.get("incident_id") else None
    panel_paths = (scan.get("evidence") or {}).get("panel_paths", {})
    metadata = (scan.get("evidence") or {}).get("metadata", {})
    return EvidencePackDetailResponse(
        panel_metadata=rec,
        current_image_preview=_preview_data_url(panel_paths.get("current_rgb_path")),
        temporal_comparison_preview=_preview_data_url(panel_paths.get("temporal_diff_path")),
        map_preview=_preview_data_url(panel_paths.get("mapbox_context_path")),
        metadata_panel=metadata,
        linked_incident=incident,
        linked_scan=scan,
        export_options={
            "formats": ["json", "markdown"],
            "incident_export_url": f"/incidents/{scan.get('incident_id')}/export",
            "scan_evidence_url": f"/scans/{rec['scan_id']}/evidence",
        },
    )


@router.post("/watchlist/scan")
def scan_watchlist(request: WatchlistScanRequest) -> dict:
    repo = get_repository()
    if request.site_ids:
        target_sites = [site_id for site_id in request.site_ids if repo.get_site(site_id)]
    else:
        target_sites = [site.site_id for site in repo.list_watchlist_sites()]

    _progress(
        request.progress_id,
        "batch_start",
        5,
        f"Starting live scan for {len(target_sites)} watchlist sites.",
        total_sites=len(target_sites),
    )
    queued = []
    failures = []
    for idx, site_id in enumerate(target_sites, start=1):
        try:
            _progress(
                request.progress_id,
                "batch_site",
                5 + int((idx - 1) / max(len(target_sites), 1) * 90),
                f"Scanning {site_id} ({idx}/{len(target_sites)}).",
                site_id=site_id,
                total_sites=len(target_sites),
                completed_sites=idx - 1,
            )
            result = scan_site(
                site_id,
                ScanRequest(force_refresh=request.force_refresh, progress_id=f"{request.progress_id}:{site_id}" if request.progress_id else None),
            )
            queued.append(result.scan_id)
        except HTTPException as exc:
            failures.append(
                {
                    "site_id": site_id,
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                }
            )
            continue

    _progress(
        request.progress_id,
        "complete" if not failures else "failed",
        100,
        f"Batch scan finished: {len(queued)} complete, {len(failures)} failed.",
        total_sites=len(target_sites),
        completed_sites=len(queued),
        failed_count=len(failures),
    )
    return {
        "queued": queued,
        "count": len(queued),
        "requested_count": len(target_sites),
        "failed_count": len(failures),
        "failures": failures[:20],
    }


@router.post("/incidents/{incident_id}/review", response_model=Incident)
def review_incident(incident_id: str, action: ReviewAction) -> Incident:
    repo = get_repository()
    incident = repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    if action.incident_id != incident_id:
        raise HTTPException(status_code=400, detail="incident_id mismatch")

    updates = {
        "review_status": action.review_status,
        "feedback_status": action.feedback_status or incident.feedback_status,
    }
    if hasattr(incident, "model_copy"):
        updated = incident.model_copy(update=updates)
    else:
        updated = incident.copy(update=updates)
    repo.save_incident(updated)
    repo.save_incident_history_event(
        IncidentHistoryEvent(
            history_id=f"hist_{uuid4().hex[:12]}",
            incident_id=incident_id,
            event_type="review_status_changed",
            from_status=incident.review_status.value,
            to_status=updated.review_status.value,
            actor="reviewer",
            note=action.review_comment,
            created_at=datetime.now(timezone.utc),
        )
    )
    return updated


@router.get("/incidents/{incident_id}/comments", response_model=List[IncidentComment])
def get_incident_comments(incident_id: str) -> List[IncidentComment]:
    repo = get_repository()
    if not repo.get_incident(incident_id):
        raise HTTPException(status_code=404, detail="incident not found")
    return repo.list_incident_comments(incident_id)


@router.post("/incidents/{incident_id}/comments", response_model=IncidentComment)
def post_incident_comment(incident_id: str, payload: IncidentCommentCreate) -> IncidentComment:
    repo = get_repository()
    if not repo.get_incident(incident_id):
        raise HTTPException(status_code=404, detail="incident not found")
    comment = IncidentComment(
        comment_id=f"cmt_{uuid4().hex[:12]}",
        incident_id=incident_id,
        author_name=payload.author_name,
        author_role=payload.author_role,
        body=payload.body,
        created_at=datetime.now(timezone.utc),
    )
    repo.save_incident_comment(comment)
    repo.save_incident_history_event(
        IncidentHistoryEvent(
            history_id=f"hist_{uuid4().hex[:12]}",
            incident_id=incident_id,
            event_type="comment_added",
            from_status=None,
            to_status=None,
            actor=payload.author_name,
            note=payload.body[:240],
            created_at=datetime.now(timezone.utc),
        )
    )
    return comment


@router.post("/incidents/{incident_id}/assign", response_model=IncidentAssignment)
def assign_incident(incident_id: str, payload: IncidentAssignRequest) -> IncidentAssignment:
    repo = get_repository()
    if not repo.get_incident(incident_id):
        raise HTTPException(status_code=404, detail="incident not found")
    assignment = IncidentAssignment(
        incident_id=incident_id,
        assignee_name=payload.assignee_name,
        assignee_role=payload.assignee_role,
        assigned_at=datetime.now(timezone.utc),
        sla_due_at=payload.sla_due_at,
    )
    repo.save_incident_assignment(assignment)
    repo.save_incident_history_event(
        IncidentHistoryEvent(
            history_id=f"hist_{uuid4().hex[:12]}",
            incident_id=incident_id,
            event_type="assignment_updated",
            from_status=None,
            to_status=None,
            actor="dispatcher",
            note=f"Assigned to {payload.assignee_name} ({payload.assignee_role}).",
            created_at=datetime.now(timezone.utc),
        )
    )
    return assignment


@router.get("/incidents/export", response_model=ExportResponse)
def export_incidents(format: str = Query(default="json")) -> ExportResponse:
    repo = get_repository()
    incidents = repo.list_incidents()
    return ExportResponse(
        format=format,
        generated_at=datetime.now(timezone.utc),
        incident_count=len(incidents),
        incidents=incidents,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_incident_detail(incident_id: str) -> IncidentDetailResponse:
    repo = get_repository()
    incident = repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    site = repo.get_site(incident.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found for incident")
    scan = repo.get_scan_by_incident(incident_id)
    metadata_block = ((scan or {}).get("evidence") or {}).get("metadata", {})
    panel_paths = ((scan or {}).get("evidence") or {}).get("panel_paths", {})
    history = repo.list_incident_history(incident_id, limit=500)
    comments = repo.list_incident_comments(incident_id)
    assignment = repo.get_incident_assignment(incident_id)
    detection_timeline: List[Dict[str, Any]] = [
        {
            "event": "detection",
            "timestamp": incident.analysis_time.isoformat(),
            "message": "Incident detected from satellite evidence.",
        }
    ]
    if scan:
        detection_timeline.append(
            {
                "event": "scan_recorded",
                "timestamp": scan.get("created_at"),
                "scan_id": scan.get("scan_id"),
                "status": scan.get("status"),
            }
        )
    for ev in history:
        detection_timeline.append(
            {
                "event": ev.event_type,
                "timestamp": ev.created_at.isoformat(),
                "actor": ev.actor,
                "from_status": ev.from_status,
                "to_status": ev.to_status,
                "note": ev.note,
            }
        )
    return IncidentDetailResponse(
        incident=incident,
        site=site,
        scan=scan,
        evidence_summary=incident.evidence_summary,
        metadata_block=metadata_block,
        detection_timeline=detection_timeline,
        decision_history=history,
        comments=comments,
        panel_previews={
            "current_rgb": _preview_data_url(panel_paths.get("current_rgb_path")),
            "spectral_composite": _preview_data_url(panel_paths.get("spectral_composite_path")),
            "temporal_diff": _preview_data_url(panel_paths.get("temporal_diff_path")),
            "mapbox_context": _preview_data_url(panel_paths.get("mapbox_context_path")),
        },
        assignment=assignment,
    )


@router.get("/incidents/{incident_id}/export")
def export_incident_evidence(incident_id: str, format: str = Query(default="markdown")):
    repo = get_repository()
    incident = repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    scan = repo.get_scan_by_incident(incident_id)
    if not scan:
        raise HTTPException(status_code=404, detail="scan not found for incident")

    payload = {
        "incident": _model_dump_jsonable(incident),
        "scan": {
            "scan_id": scan["scan_id"],
            "status": scan["status"],
            "created_at": scan["created_at"],
        },
        "evidence": scan["evidence"],
    }
    if format.lower() == "json":
        return payload

    incident_data = payload["incident"]
    panel_paths = payload["evidence"].get("panel_paths", {})
    metadata = payload["evidence"].get("metadata", {})
    provenance = metadata.get("imagery_provenance", {})
    ground_truth_hint = metadata.get("ground_truth_hint", {})
    markdown = "\n".join(
        [
            f"# Incident Export - {incident_id}",
            "",
            f"- Site: `{incident_data['site_id']}`",
            f"- Scan: `{scan['scan_id']}`",
            f"- Analysis Time: `{incident_data['analysis_time']}`",
            f"- Priority: `{incident_data['priority_tier']}`",
            f"- Severity: `{incident_data['severity_tier']}`",
            f"- Review Status: `{incident_data['review_status']}`",
            f"- Confidence: `{incident_data['confidence']}`",
            f"- Zone: `{incident_data['likely_source_zone']}`",
            f"- Generation mode: `{metadata.get('inference', {}).get('mode', 'unknown')}`",
            "",
            "## Evidence Summary",
            "",
            incident_data["evidence_summary"],
            "",
            "## Data Source",
            "",
            f"- source_chain: `{provenance.get('source_chain', [])}`",
            f"- live_fetch_status: `{provenance.get('live_fetch_status', '')}`",
            f"- sentinel_current_captured_at: `{provenance.get('assets', {}).get('sentinel_current', {}).get('timestamp_captured', '')}`",
            f"- sentinel_historical_captured_at: `{provenance.get('assets', {}).get('sentinel_historical', {}).get('timestamp_captured', '')}`",
            f"- mapbox_context_captured_at: `{provenance.get('assets', {}).get('mapbox_context', {}).get('timestamp_captured', '')}`",
            "",
            "## Ground Truth Hint",
            "",
            f"- status: `{ground_truth_hint.get('status', 'satellite_only')}`",
            f"- message: `{ground_truth_hint.get('message', '')}`",
            "",
            "## Evidence Panel Paths",
            "",
            f"- current_rgb_path: `{panel_paths.get('current_rgb_path', '')}`",
            f"- spectral_composite_path: `{panel_paths.get('spectral_composite_path', '')}`",
            f"- temporal_diff_path: `{panel_paths.get('temporal_diff_path', '')}`",
            f"- mapbox_context_path: `{panel_paths.get('mapbox_context_path', '')}`",
            "",
            "## Recommended Follow-up",
            "",
            incident_data["recommended_followup"],
            "",
        ]
    )
    return PlainTextResponse(content=markdown, media_type="text/markdown")
