"""Export live scan labels to a CSV that can be manually corrected before LoRA training."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _db_path() -> Path:
    _load_env_file(PROJECT_ROOT / ".env.local")
    db_path = Path(os.getenv("LS_DB_PATH", "data/processed/landfillsentry.db"))
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    return db_path


def _rows(limit: int) -> List[Dict[str, str]]:
    db_path = _db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"database not found: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        raw_rows = conn.execute(
            """
            SELECT
                s.scan_id,
                s.site_id,
                s.status,
                s.evidence_json,
                s.created_at,
                i.payload_json AS incident_json,
                site.payload_json AS site_json
            FROM scans s
            LEFT JOIN incidents i ON i.incident_id = s.incident_id
            LEFT JOIN sites site ON site.site_id = s.site_id
            ORDER BY s.created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()

    rows: List[Dict[str, str]] = []
    for row in raw_rows:
        evidence = json.loads(row["evidence_json"]) if row["evidence_json"] else {}
        metadata = evidence.get("metadata", {})
        if str(metadata.get("mode", "")).lower() != "live":
            continue
        incident = json.loads(row["incident_json"]) if row["incident_json"] else {}
        site = json.loads(row["site_json"]) if row["site_json"] else {}
        site_meta = site.get("metadata", {}) if isinstance(site, dict) else {}
        rows.append(
            {
                "scan_id": row["scan_id"],
                "site_id": row["site_id"],
                "site_name": site.get("name", row["site_id"]),
                "region": str(site_meta.get("region", "")),
                "country": site.get("country", ""),
                "created_at": row["created_at"],
                "split": str(site_meta.get("dataset_split", "")),
                "plume_likely": str(bool(incident.get("plume_likely", True))).lower(),
                "bbox_norm": json.dumps(incident.get("bbox_norm") or [0.2, 0.2, 0.5, 0.5]),
                "likely_source_zone": incident.get("likely_source_zone", "perimeter_or_unknown"),
                "priority_tier": incident.get("priority_tier", "medium"),
                "source_type": "manual" if incident.get("review_status") in {"published", "dismissed"} else "weak",
                "labeler": "operator_review" if incident.get("review_status") in {"published", "dismissed"} else "model_bootstrap",
                "notes": "Review bbox_norm/zone/priority, then copy corrected rows to data/labels/manual_label_corrections.csv.",
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Export live scan labels for manual review.")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "data/labels/manual_label_review_queue.csv"))
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    rows = _rows(limit=args.limit)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scan_id",
        "site_id",
        "site_name",
        "region",
        "country",
        "created_at",
        "split",
        "plume_likely",
        "bbox_norm",
        "likely_source_zone",
        "priority_tier",
        "source_type",
        "labeler",
        "notes",
    ]
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} live scan label rows for review: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
