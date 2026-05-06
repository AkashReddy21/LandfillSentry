from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_TOP_LEVEL = {"sample_id", "site_id", "split", "panel_artifact_path", "annotation", "provenance"}
REQUIRED_PROVENANCE = {"source_type", "source_ref", "labeler", "created_at"}
ALLOWED_SPLITS = {"train", "validation", "test", "demo"}


@dataclass
class DatasetBuildResult:
    manifest_path: Path
    split_path: Path
    sample_count: int
    manifest_checksum: str
    split_counts: Dict[str, int]


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"label file not found: {path}")
    rows: List[Dict[str, Any]] = []
    for index, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {index}: {exc}") from exc
        rows.append(row)
    return rows


def _validate_row(row: Dict[str, Any]) -> None:
    missing = REQUIRED_TOP_LEVEL.difference(row.keys())
    if missing:
        raise ValueError(f"sample {row.get('sample_id', '<unknown>')} missing fields: {sorted(missing)}")

    split = str(row.get("split", "")).strip().lower()
    if split not in ALLOWED_SPLITS:
        raise ValueError(f"sample {row['sample_id']} has unsupported split: {split}")

    annotation = row.get("annotation")
    if not isinstance(annotation, dict):
        raise ValueError(f"sample {row['sample_id']} annotation must be an object")
    bbox = annotation.get("bbox_norm")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError(f"sample {row['sample_id']} must include annotation.bbox_norm with 4 values")

    provenance = row.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError(f"sample {row['sample_id']} provenance must be an object")
    missing_prov = REQUIRED_PROVENANCE.difference(provenance.keys())
    if missing_prov:
        raise ValueError(f"sample {row['sample_id']} missing provenance fields: {sorted(missing_prov)}")


def _stable_checksum(samples: List[Dict[str, Any]]) -> str:
    canonical = json.dumps(samples, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_dataset_manifest_from_samples(
    samples: List[Dict[str, Any]],
    manifest_path: Path,
    split_path: Path,
    source_labels_path: str,
) -> DatasetBuildResult:
    seen = set()
    normalized: List[Dict[str, Any]] = []
    for row in samples:
        _validate_row(row)
        sample_id = str(row["sample_id"])
        if sample_id in seen:
            raise ValueError(f"duplicate sample_id: {sample_id}")
        seen.add(sample_id)
        normalized.append(
            {
                **row,
                "sample_id": sample_id,
                "split": str(row["split"]).strip().lower(),
            }
        )

    normalized.sort(key=lambda sample: sample["sample_id"])
    checksum = _stable_checksum(normalized)

    split_map: Dict[str, List[str]] = {name: [] for name in sorted(ALLOWED_SPLITS)}
    for sample in normalized:
        split_map[sample["split"]].append(sample["sample_id"])
    split_counts = {name: len(ids) for name, ids in split_map.items()}

    manifest = {
        "manifest_version": "phase6.dataset.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_labels_path": source_labels_path,
        "sample_count": len(normalized),
        "manifest_checksum": checksum,
        "split_counts": split_counts,
        "samples": normalized,
    }
    split_doc = {
        "split_version": "phase6.splits.v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "manifest_checksum": checksum,
        "splits": split_map,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    split_path.write_text(json.dumps(split_doc, indent=2, sort_keys=True), encoding="utf-8")

    return DatasetBuildResult(
        manifest_path=manifest_path,
        split_path=split_path,
        sample_count=len(normalized),
        manifest_checksum=checksum,
        split_counts=split_counts,
    )


def build_dataset_manifest(
    label_path: Path,
    manifest_path: Path,
    split_path: Path,
) -> DatasetBuildResult:
    samples = _load_jsonl(label_path)
    if not samples:
        raise ValueError("no label samples found")

    project_root = manifest_path.parents[2] if len(manifest_path.parents) >= 3 else manifest_path.parent
    try:
        source_labels_path = str(label_path.resolve().relative_to(project_root.resolve()))
    except Exception:
        source_labels_path = str(label_path)

    return build_dataset_manifest_from_samples(
        samples=samples,
        manifest_path=manifest_path,
        split_path=split_path,
        source_labels_path=source_labels_path,
    )
