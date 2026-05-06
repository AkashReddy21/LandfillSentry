"""Bulk import real sites from CSV into the LandfillSentry API."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Tuple


REQUIRED_COLUMNS = ["site_id", "name", "lat", "lon", "country", "operator"]


def _as_bool(value: str, default: bool = True) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _http_json(method: str, url: str, payload: Dict[str, Any], timeout: int) -> Tuple[int, Dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if body:
                return resp.status, json.loads(body)
            return resp.status, {}
    except urllib.error.HTTPError as exc:
        detail_text = exc.read().decode("utf-8", errors="replace")
        detail_payload: Dict[str, Any]
        try:
            detail_payload = json.loads(detail_text) if detail_text else {}
        except Exception:
            detail_payload = {"detail": detail_text}
        return exc.code, detail_payload


def _row_payload(row: Dict[str, str], row_number: int) -> Dict[str, Any]:
    missing = [key for key in REQUIRED_COLUMNS if not str(row.get(key, "")).strip()]
    if missing:
        raise ValueError(f"row {row_number}: missing required columns: {', '.join(missing)}")

    metadata: Dict[str, Any] = {"seeded_from": "csv_import"}
    metadata_raw = str(row.get("metadata_json", "")).strip()
    if metadata_raw:
        try:
            parsed = json.loads(metadata_raw)
            if isinstance(parsed, dict):
                metadata.update(parsed)
            else:
                raise ValueError("metadata_json must be a JSON object")
        except Exception as exc:
            raise ValueError(f"row {row_number}: invalid metadata_json: {exc}") from exc

    fixture_class = str(row.get("fixture_class", "")).strip()
    if fixture_class:
        metadata["fixture_class"] = fixture_class

    polygon_geojson = None
    polygon_raw = str(row.get("polygon_geojson", "")).strip()
    if polygon_raw:
        try:
            polygon_geojson = json.loads(polygon_raw)
        except Exception as exc:
            raise ValueError(f"row {row_number}: invalid polygon_geojson JSON: {exc}") from exc

    payload = {
        "site_id": str(row["site_id"]).strip(),
        "name": str(row["name"]).strip(),
        "lat": float(str(row["lat"]).strip()),
        "lon": float(str(row["lon"]).strip()),
        "country": str(row["country"]).strip(),
        "operator": str(row["operator"]).strip(),
        "watchlist_enabled": _as_bool(str(row.get("watchlist_enabled", "true")), default=True),
        "polygon_geojson": polygon_geojson,
        "metadata": metadata,
    }
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk import site registry rows from CSV.")
    parser.add_argument("--csv", required=True, help="Path to CSV file with site rows")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000", help="LandfillSentry API base URL")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    parser.add_argument("--dry-run", action="store_true", help="Validate CSV without POSTing to API")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}")
        return 2

    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            print("ERROR: CSV has no header row")
            return 2

        missing_headers = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing_headers:
            print(f"ERROR: CSV missing required headers: {', '.join(missing_headers)}")
            return 2

        created = 0
        skipped = 0
        failed = 0

        endpoint = args.api_base_url.rstrip("/") + "/sites"
        for idx, row in enumerate(reader, start=2):
            try:
                payload = _row_payload(row, idx)
            except Exception as exc:
                failed += 1
                print(f"FAIL line {idx}: {exc}")
                continue

            if args.dry_run:
                created += 1
                print(f"OK line {idx}: validated {payload['site_id']}")
                continue

            status, response = _http_json("POST", endpoint, payload, timeout=args.timeout)
            if status in {200, 201}:
                created += 1
                print(f"CREATED line {idx}: {payload['site_id']}")
            elif status == 409:
                skipped += 1
                detail = response.get("detail", "site already exists")
                print(f"SKIP line {idx}: {payload['site_id']} ({detail})")
            else:
                failed += 1
                print(f"FAIL line {idx}: {payload['site_id']} (status={status}, response={response})")

    print(
        json.dumps(
            {
                "csv": str(csv_path),
                "dry_run": bool(args.dry_run),
                "created_or_validated": created,
                "skipped_existing": skipped,
                "failed": failed,
            },
            indent=2,
        )
    )
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
