"""Build and freeze Phase 6 dataset manifest + split documents."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import csv
import hashlib
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.training.dataset_manifest import build_dataset_manifest, build_dataset_manifest_from_samples


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _site_split(site_id: str, site_metadata: Dict[str, Any]) -> str:
    configured = str(site_metadata.get("dataset_split", "")).strip().lower()
    if configured in {"train", "validation", "test", "demo"}:
        return configured
    bucket = int(hashlib.sha256(site_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket == 0:
        return "test"
    if bucket in {1, 2}:
        return "validation"
    return "train"


def _load_manual_corrections(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    corrections: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader, start=2):
            scan_id = str(row.get("scan_id", "")).strip()
            if not scan_id:
                continue
            parsed: Dict[str, Any] = {}
            if str(row.get("split", "")).strip():
                parsed["split"] = str(row["split"]).strip().lower()
            if str(row.get("plume_likely", "")).strip():
                parsed["plume_likely"] = str(row["plume_likely"]).strip().lower() in {"1", "true", "yes", "on"}
            if str(row.get("bbox_norm", "")).strip():
                try:
                    bbox = json.loads(str(row["bbox_norm"]).strip())
                    if not isinstance(bbox, list) or len(bbox) != 4:
                        raise ValueError("bbox_norm must be a JSON list of four numbers")
                    parsed["bbox_norm"] = bbox
                except Exception as exc:
                    raise ValueError(f"invalid bbox_norm in corrections row {idx}: {exc}") from exc
            for key in ("likely_source_zone", "priority_tier", "source_type", "labeler", "notes"):
                value = str(row.get(key, "")).strip()
                if value:
                    parsed[key] = value
            corrections[scan_id] = parsed
    return corrections


def _apply_manual_correction(sample: Dict[str, Any], correction: Dict[str, Any]) -> None:
    if not correction:
        return
    annotation = sample["annotation"]
    provenance = sample["provenance"]
    if "split" in correction:
        sample["split"] = correction["split"]
    for key in ("plume_likely", "bbox_norm", "likely_source_zone", "priority_tier"):
        if key in correction:
            annotation[key] = correction[key]
    for key in ("source_type", "labeler", "notes"):
        if key in correction:
            provenance[key] = correction[key]
    provenance["manual_correction_applied"] = True


def _collect_live_samples(db_path: Path, limit: int = 1000, corrections: Dict[str, Dict[str, Any]] | None = None) -> List[Dict]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
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
            ORDER BY s.created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    samples: List[Dict] = []
    for row in rows:
        evidence = json.loads(row["evidence_json"]) if row["evidence_json"] else {}
        metadata = evidence.get("metadata", {})
        panel_paths = evidence.get("panel_paths", {})
        mode = str(metadata.get("mode", "")).lower()
        if mode != "live":
            continue
        provenance = metadata.get("imagery_provenance", {})
        if provenance and provenance.get("live_fetch_status") != "live":
            continue
        panel_path = panel_paths.get("evidence_panel_path") or panel_paths.get("current_rgb_path")
        if not panel_path:
            continue
        incident = json.loads(row["incident_json"]) if row["incident_json"] else {}
        site_payload = json.loads(row["site_json"]) if row["site_json"] else {}
        site_metadata = site_payload.get("metadata", {}) if isinstance(site_payload, dict) else {}
        bbox = incident.get("bbox_norm") or metadata.get("candidate", {}).get("bbox_norm") or [0.2, 0.2, 0.5, 0.5]
        zone = incident.get("likely_source_zone") or metadata.get("candidate", {}).get("likely_source_zone_prior")
        if not zone:
            zone = "perimeter_or_unknown"
        priority = incident.get("priority_tier", "medium")
        review_status = incident.get("review_status", "needs_review")
        source_type = "manual" if review_status in {"published", "dismissed"} else "weak"
        labeler = "operator_review" if source_type == "manual" else "model_bootstrap"

        samples.append(
            {
                "sample_id": f"live_{row['scan_id']}",
                "site_id": row["site_id"],
                "split": _site_split(row["site_id"], site_metadata),
                "panel_artifact_path": str(panel_path),
                "annotation": {
                    "plume_likely": bool(incident.get("plume_likely", True)),
                    "bbox_norm": bbox,
                    "likely_source_zone": zone,
                    "priority_tier": priority,
                },
                "provenance": {
                    "source_type": source_type,
                    "source_ref": f"scan:{row['scan_id']}",
                    "labeler": labeler,
                    "created_at": row["created_at"],
                    "notes": f"captured from live scan pipeline; scan_status={row['status']}",
                    "region": site_metadata.get("region"),
                },
            }
        )

    samples.sort(key=lambda sample: sample["sample_id"])
    corrections = corrections or {}
    for sample in samples:
        scan_id = str(sample["provenance"]["source_ref"]).split("scan:", 1)[-1]
        _apply_manual_correction(sample, corrections.get(scan_id, {}))
    return samples


def _write_live_label_dump(path: Path, samples: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(sample, sort_keys=True) for sample in samples]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main() -> None:
    _load_env_file(PROJECT_ROOT / ".env.local")

    label_path = PROJECT_ROOT / "data" / "labels" / "phase6_samples_v1.jsonl"
    live_label_path = PROJECT_ROOT / "data" / "labels" / "phase6_samples_live_v1.jsonl"
    corrections_path = PROJECT_ROOT / "data" / "labels" / "manual_label_corrections.csv"
    manifest_path = PROJECT_ROOT / "data" / "manifests" / "dataset_manifest_v1.json"
    split_path = PROJECT_ROOT / "data" / "manifests" / "dataset_splits_v1.json"
    db_path = Path(os.getenv("LS_DB_PATH", "data/processed/landfillsentry.db"))
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path

    corrections = _load_manual_corrections(corrections_path)
    live_samples = _collect_live_samples(db_path=db_path, corrections=corrections)
    if live_samples:
        _write_live_label_dump(live_label_path, live_samples)
        result = build_dataset_manifest_from_samples(
            samples=live_samples,
            manifest_path=manifest_path,
            split_path=split_path,
            source_labels_path="data/labels/phase6_samples_live_v1.jsonl",
        )
        source = "live_scans"
    else:
        result = build_dataset_manifest(
            label_path=label_path,
            manifest_path=manifest_path,
            split_path=split_path,
        )
        source = "fallback_seed_labels"

    print(
        "Built Phase 6 dataset:",
        f"source={source}",
        f"samples={result.sample_count}",
        f"checksum={result.manifest_checksum}",
        f"manifest={result.manifest_path}",
        f"splits={result.split_path}",
    )


if __name__ == "__main__":
    main()
