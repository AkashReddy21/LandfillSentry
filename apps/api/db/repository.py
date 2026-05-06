import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from ..schemas import (
    Candidate,
    DongleReading,
    EvidencePanel,
    ImageAsset,
    Incident,
    IncidentAssignment,
    IncidentComment,
    IncidentHistoryEvent,
    Site,
    SiteWatchlistSettings,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.fromtimestamp(0, tz=timezone.utc)


def _model_dump(model) -> Dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()  # type: ignore[attr-defined]


def _model_dump_json(model) -> str:
    if hasattr(model, "model_dump_json"):
        return model.model_dump_json()
    return model.json()  # type: ignore[attr-defined]


class Repository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sites (
                    site_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS image_assets (
                    asset_id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp_requested TEXT NOT NULL,
                    timestamp_captured TEXT NOT NULL,
                    cloud_cover REAL NOT NULL,
                    bands_json TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    cache_key TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scans (
                    scan_id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    incident_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY,
                    scan_id TEXT NOT NULL,
                    site_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    diagnostics_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_panels (
                    panel_id TEXT PRIMARY KEY,
                    scan_id TEXT NOT NULL,
                    site_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    panel_version TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dongle_readings (
                    reading_id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    incident_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_comments (
                    comment_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    author_role TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_history (
                    history_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT,
                    actor TEXT NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_assignments (
                    incident_id TEXT PRIMARY KEY,
                    assignee_name TEXT NOT NULL,
                    assignee_role TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    sla_due_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS site_settings (
                    site_id TEXT PRIMARY KEY,
                    scan_cadence_hours INTEGER NOT NULL,
                    alert_threshold REAL NOT NULL,
                    change_detection_enabled INTEGER NOT NULL,
                    fallback_mode TEXT NOT NULL,
                    notes TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def register_site(self, site: Site) -> bool:
        payload = _model_dump_json(site)
        now = _now_iso()
        with self._connection() as conn:
            existing = conn.execute(
                "SELECT site_id FROM sites WHERE site_id = ?",
                (site.site_id,),
            ).fetchone()
            if existing:
                return False
            conn.execute(
                """
                INSERT INTO sites (site_id, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (site.site_id, payload, now, now),
            )
            return True

    def get_site(self, site_id: str) -> Optional[Site]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM sites WHERE site_id = ?",
                (site_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        return Site(**payload)

    def list_sites(self) -> List[Site]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM sites ORDER BY site_id ASC"
            ).fetchall()
        return [Site(**json.loads(row["payload_json"])) for row in rows]

    def list_watchlist_sites(self) -> List[Site]:
        return [site for site in self.list_sites() if site.watchlist_enabled]

    def save_image_asset(self, asset: ImageAsset) -> None:
        payload = _model_dump(asset)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO image_assets (
                    asset_id,
                    site_id,
                    source,
                    timestamp_requested,
                    timestamp_captured,
                    cloud_cover,
                    bands_json,
                    local_path,
                    cache_key,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["asset_id"],
                    payload["site_id"],
                    payload["source"],
                    payload["timestamp_requested"],
                    payload["timestamp_captured"],
                    payload["cloud_cover"],
                    json.dumps(payload["bands"]),
                    payload["local_path"],
                    payload["cache_key"],
                    _now_iso(),
                ),
            )

    def save_incident(self, incident: Incident) -> None:
        payload = _model_dump_json(incident)
        now = _now_iso()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO incidents (incident_id, site_id, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, COALESCE((SELECT created_at FROM incidents WHERE incident_id = ?), ?), ?)
                """,
                (incident.incident_id, incident.site_id, payload, incident.incident_id, now, now),
            )

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM incidents WHERE incident_id = ?",
                (incident_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        return Incident(**payload)

    def list_incidents(self) -> List[Incident]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM incidents ORDER BY incident_id ASC"
            ).fetchall()
        return [Incident(**json.loads(row["payload_json"])) for row in rows]

    def save_scan(
        self,
        scan_id: str,
        site_id: str,
        incident_id: str,
        status: str,
        evidence: Dict,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scans (scan_id, site_id, incident_id, status, evidence_json, created_at)
                VALUES (?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM scans WHERE scan_id = ?), ?))
                """,
                (
                    scan_id,
                    site_id,
                    incident_id,
                    status,
                    json.dumps(evidence),
                    scan_id,
                    _now_iso(),
                ),
            )

    def save_candidate(self, scan_id: str, candidate: Candidate, diagnostics: Dict) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO candidates (
                    candidate_id,
                    scan_id,
                    site_id,
                    payload_json,
                    diagnostics_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM candidates WHERE candidate_id = ?), ?))
                """,
                (
                    candidate.candidate_id,
                    scan_id,
                    candidate.site_id,
                    _model_dump_json(candidate),
                    json.dumps(diagnostics),
                    candidate.candidate_id,
                    _now_iso(),
                ),
            )

    def save_evidence_panel(self, scan_id: str, panel: EvidencePanel) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO evidence_panels (
                    panel_id,
                    scan_id,
                    site_id,
                    candidate_id,
                    panel_version,
                    payload_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM evidence_panels WHERE panel_id = ?), ?))
                """,
                (
                    panel.panel_id,
                    scan_id,
                    panel.site_id,
                    panel.candidate_id,
                    panel.panel_version,
                    _model_dump_json(panel),
                    panel.panel_id,
                    _now_iso(),
                ),
            )

    def list_evidence_panel_records(self) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT panel_id, scan_id, site_id, candidate_id, panel_version, payload_json, created_at
                FROM evidence_panels
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            {
                "panel_id": row["panel_id"],
                "scan_id": row["scan_id"],
                "site_id": row["site_id"],
                "candidate_id": row["candidate_id"],
                "panel_version": row["panel_version"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def get_evidence_panel_record(self, panel_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT panel_id, scan_id, site_id, candidate_id, panel_version, payload_json, created_at
                FROM evidence_panels
                WHERE panel_id = ?
                """,
                (panel_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "panel_id": row["panel_id"],
            "scan_id": row["scan_id"],
            "site_id": row["site_id"],
            "candidate_id": row["candidate_id"],
            "panel_version": row["panel_version"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }

    def save_dongle_reading(self, reading: DongleReading) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO dongle_readings (
                    reading_id,
                    site_id,
                    incident_id,
                    payload_json,
                    created_at
                ) VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM dongle_readings WHERE reading_id = ?), ?))
                """,
                (
                    reading.reading_id,
                    reading.site_id,
                    reading.incident_id,
                    _model_dump_json(reading),
                    reading.reading_id,
                    _now_iso(),
                ),
            )

    def list_dongle_readings_for_site(self, site_id: str, limit: int = 20) -> List[DongleReading]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM dongle_readings
                WHERE site_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (site_id, int(limit)),
            ).fetchall()
        return [DongleReading(**json.loads(row["payload_json"])) for row in rows]

    def list_dongle_readings_for_incident(self, incident_id: str) -> List[DongleReading]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM dongle_readings
                WHERE incident_id = ?
                ORDER BY created_at DESC
                """,
                (incident_id,),
            ).fetchall()
        return [DongleReading(**json.loads(row["payload_json"])) for row in rows]

    def get_latest_unlinked_dongle_for_site(self, site_id: str) -> Optional[DongleReading]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM dongle_readings
                WHERE site_id = ? AND (incident_id IS NULL OR incident_id = '')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (site_id,),
            ).fetchone()
        if not row:
            return None
        return DongleReading(**json.loads(row["payload_json"]))

    def attach_dongle_reading_to_incident(self, reading_id: str, incident_id: str) -> Optional[DongleReading]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM dongle_readings WHERE reading_id = ?",
                (reading_id,),
            ).fetchone()
            if not row:
                return None
            payload = json.loads(row["payload_json"])
            payload["incident_id"] = incident_id
            conn.execute(
                """
                UPDATE dongle_readings
                SET incident_id = ?, payload_json = ?
                WHERE reading_id = ?
                """,
                (incident_id, json.dumps(payload), reading_id),
            )
        return DongleReading(**payload)

    def save_incident_comment(self, comment: IncidentComment) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO incident_comments (
                    comment_id, incident_id, author_name, author_role, body, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    comment.comment_id,
                    comment.incident_id,
                    comment.author_name,
                    comment.author_role,
                    comment.body,
                    comment.created_at.isoformat(),
                ),
            )

    def list_incident_comments(self, incident_id: str) -> List[IncidentComment]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT comment_id, incident_id, author_name, author_role, body, created_at
                FROM incident_comments
                WHERE incident_id = ?
                ORDER BY created_at ASC
                """,
                (incident_id,),
            ).fetchall()
        return [
            IncidentComment(
                comment_id=row["comment_id"],
                incident_id=row["incident_id"],
                author_name=row["author_name"],
                author_role=row["author_role"],
                body=row["body"],
                created_at=_parse_dt(row["created_at"]),
            )
            for row in rows
        ]

    def count_incident_comments(self, incident_id: str) -> int:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM incident_comments WHERE incident_id = ?",
                (incident_id,),
            ).fetchone()
        return int(row["c"]) if row else 0

    def save_incident_history_event(self, event: IncidentHistoryEvent) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO incident_history (
                    history_id, incident_id, event_type, from_status, to_status, actor, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.history_id,
                    event.incident_id,
                    event.event_type,
                    event.from_status,
                    event.to_status,
                    event.actor,
                    event.note,
                    event.created_at.isoformat(),
                ),
            )

    def list_incident_history(self, incident_id: str, limit: int = 200) -> List[IncidentHistoryEvent]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT history_id, incident_id, event_type, from_status, to_status, actor, note, created_at
                FROM incident_history
                WHERE incident_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (incident_id, int(limit)),
            ).fetchall()
        return [
            IncidentHistoryEvent(
                history_id=row["history_id"],
                incident_id=row["incident_id"],
                event_type=row["event_type"],
                from_status=row["from_status"],
                to_status=row["to_status"],
                actor=row["actor"],
                note=row["note"],
                created_at=_parse_dt(row["created_at"]),
            )
            for row in rows
        ]

    def save_incident_assignment(self, assignment: IncidentAssignment) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO incident_assignments (
                    incident_id, assignee_name, assignee_role, assigned_at, sla_due_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    assignment.incident_id,
                    assignment.assignee_name,
                    assignment.assignee_role,
                    assignment.assigned_at.isoformat(),
                    assignment.sla_due_at.isoformat() if assignment.sla_due_at else None,
                ),
            )

    def get_incident_assignment(self, incident_id: str) -> Optional[IncidentAssignment]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT incident_id, assignee_name, assignee_role, assigned_at, sla_due_at
                FROM incident_assignments
                WHERE incident_id = ?
                """,
                (incident_id,),
            ).fetchone()
        if not row:
            return None
        return IncidentAssignment(
            incident_id=row["incident_id"],
            assignee_name=row["assignee_name"],
            assignee_role=row["assignee_role"],
            assigned_at=_parse_dt(row["assigned_at"]),
            sla_due_at=_parse_dt(row["sla_due_at"]) if row["sla_due_at"] else None,
        )

    def get_site_settings(self, site_id: str) -> SiteWatchlistSettings:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT site_id, scan_cadence_hours, alert_threshold, change_detection_enabled, fallback_mode, notes, updated_at
                FROM site_settings
                WHERE site_id = ?
                """,
                (site_id,),
            ).fetchone()
        if not row:
            return SiteWatchlistSettings(
                site_id=site_id,
                scan_cadence_hours=24,
                alert_threshold=0.7,
                change_detection_enabled=True,
                fallback_mode="strict_live",
                notes=None,
                updated_at=datetime.now(timezone.utc),
            )
        return SiteWatchlistSettings(
            site_id=row["site_id"],
            scan_cadence_hours=int(row["scan_cadence_hours"]),
            alert_threshold=float(row["alert_threshold"]),
            change_detection_enabled=bool(int(row["change_detection_enabled"])),
            fallback_mode=row["fallback_mode"],
            notes=row["notes"],
            updated_at=_parse_dt(row["updated_at"]),
        )

    def save_site_settings(self, settings: SiteWatchlistSettings) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO site_settings (
                    site_id, scan_cadence_hours, alert_threshold, change_detection_enabled, fallback_mode, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    settings.site_id,
                    int(settings.scan_cadence_hours),
                    float(settings.alert_threshold),
                    1 if settings.change_detection_enabled else 0,
                    settings.fallback_mode,
                    settings.notes,
                    settings.updated_at.isoformat(),
                ),
            )

    def get_evidence_panel_by_scan(self, scan_id: str) -> Optional[Dict]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM evidence_panels
                WHERE scan_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (scan_id,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

    def get_candidate_by_scan(self, scan_id: str) -> Optional[Dict]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT payload_json, diagnostics_json
                FROM candidates
                WHERE scan_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (scan_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "candidate": json.loads(row["payload_json"]),
            "diagnostics": json.loads(row["diagnostics_json"]),
        }

    def get_scan(self, scan_id: str) -> Optional[Dict]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT scan_id, site_id, incident_id, status, evidence_json, created_at
                FROM scans
                WHERE scan_id = ?
                """,
                (scan_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "scan_id": row["scan_id"],
            "site_id": row["site_id"],
            "incident_id": row["incident_id"],
            "status": row["status"],
            "evidence": json.loads(row["evidence_json"]),
            "created_at": row["created_at"],
        }

    def list_scans(self) -> List[Dict]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT scan_id, site_id, incident_id, status, evidence_json, created_at
                FROM scans
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            {
                "scan_id": row["scan_id"],
                "site_id": row["site_id"],
                "incident_id": row["incident_id"],
                "status": row["status"],
                "evidence": json.loads(row["evidence_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def get_latest_scan_for_site(self, site_id: str) -> Optional[Dict]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT scan_id, site_id, incident_id, status, evidence_json, created_at
                FROM scans
                WHERE site_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (site_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "scan_id": row["scan_id"],
            "site_id": row["site_id"],
            "incident_id": row["incident_id"],
            "status": row["status"],
            "evidence": json.loads(row["evidence_json"]),
            "created_at": row["created_at"],
        }

    def list_scans_for_site(self, site_id: str, limit: int = 50) -> List[Dict]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT scan_id, site_id, incident_id, status, evidence_json, created_at
                FROM scans
                WHERE site_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (site_id, int(limit)),
            ).fetchall()
        return [
            {
                "scan_id": row["scan_id"],
                "site_id": row["site_id"],
                "incident_id": row["incident_id"],
                "status": row["status"],
                "evidence": json.loads(row["evidence_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def get_scan_by_incident(self, incident_id: str) -> Optional[Dict]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT scan_id, site_id, incident_id, status, evidence_json, created_at
                FROM scans
                WHERE incident_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (incident_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "scan_id": row["scan_id"],
            "site_id": row["site_id"],
            "incident_id": row["incident_id"],
            "status": row["status"],
            "evidence": json.loads(row["evidence_json"]),
            "created_at": row["created_at"],
        }

    def get_latest_incident_for_site(self, site_id: str) -> Optional[Incident]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM incidents
                WHERE site_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (site_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        return Incident(**payload)

    def list_incident_rows(
        self,
        state: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        site_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        incidents = self.list_incidents()
        rows: List[Dict[str, Any]] = []
        for incident in incidents:
            if site_id and incident.site_id != site_id:
                continue
            if priority and incident.priority_tier.value != priority:
                continue
            state_filter = (state or status or "").strip()
            if state_filter and incident.review_status.value != state_filter:
                continue
            site = self.get_site(incident.site_id)
            scan = self.get_scan_by_incident(incident.incident_id)
            assignment = self.get_incident_assignment(incident.incident_id)
            comments = self.count_incident_comments(incident.incident_id)
            site_name = site.name if site else incident.site_id
            location = (
                f"{site.lat:.5f},{site.lon:.5f}" if site else "n/a"
            )
            rows.append(
                {
                    "incident_id": incident.incident_id,
                    "site_id": incident.site_id,
                    "site_name": site_name,
                    "location": location,
                    "detected_zone": incident.likely_source_zone.value,
                    "confidence": float(incident.confidence),
                    "priority_tier": incident.priority_tier.value,
                    "review_status": incident.review_status.value,
                    "feedback_status": incident.feedback_status.value,
                    "detected_time": incident.analysis_time,
                    "assignee": assignment.assignee_name if assignment else None,
                    "comment_count": comments,
                    "scan_id": scan["scan_id"] if scan else None,
                }
            )
        rows.sort(key=lambda r: r["detected_time"], reverse=True)
        total = len(rows)
        safe_page = max(1, int(page))
        safe_page_size = max(1, int(page_size))
        start = (safe_page - 1) * safe_page_size
        end = start + safe_page_size
        return rows[start:end], total

    def next_scan_index(self) -> int:
        with self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM scans").fetchone()
        return int(row["c"]) + 1
