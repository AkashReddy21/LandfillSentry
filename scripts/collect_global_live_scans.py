"""Import global landfill sites, probe live imagery, and collect live scan samples."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = PROJECT_ROOT / "assets/demo_sites/global_sites.26rows.csv"
DEFAULT_JSON_REPORT = PROJECT_ROOT / "data/processed/global_live_scan_collection_report.json"
DEFAULT_MD_REPORT = PROJECT_ROOT / "docs/global_live_scan_collection_report.md"


def _http_json(method: str, url: str, payload: Dict[str, Any] | None = None, timeout: int = 60) -> Tuple[int, Dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url=url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(detail) if detail else {}
        except Exception:
            return exc.code, {"detail": detail}
    except Exception as exc:
        return 0, {"detail": str(exc), "error_type": exc.__class__.__name__}


def _http_bytes(url: str, timeout: int = 60) -> Tuple[int, bytes, Dict[str, str]]:
    req = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), {k.lower(): v for k, v in exc.headers.items()}
    except Exception as exc:
        return 0, str(exc).encode("utf-8", errors="replace"), {}


def _parse_json_header(headers: Dict[str, str], name: str) -> Dict[str, Any]:
    raw = headers.get(name.lower(), "")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _load_sites(csv_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            metadata: Dict[str, Any] = {}
            raw_metadata = str(row.get("metadata_json", "")).strip()
            if raw_metadata:
                metadata.update(json.loads(raw_metadata))
            fixture_class = str(row.get("fixture_class", "")).strip()
            if fixture_class:
                metadata["fixture_class"] = fixture_class
            rows.append(
                {
                    "site_id": row["site_id"].strip(),
                    "name": row["name"].strip(),
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "country": row["country"].strip(),
                    "operator": row["operator"].strip(),
                    "watchlist_enabled": str(row.get("watchlist_enabled", "true")).strip().lower() not in {"0", "false", "no"},
                    "polygon_geojson": None,
                    "metadata": metadata,
                }
            )
    return rows


def _register_site(api_base_url: str, site: Dict[str, Any]) -> Dict[str, Any]:
    status, body = _http_json("POST", f"{api_base_url}/sites", payload=site, timeout=30)
    return {
        "status": status,
        "ok": status in {200, 201, 409},
        "message": "registered" if status in {200, 201} else ("already_exists" if status == 409 else body),
    }


def _probe_site(simsat_base_url: str, site: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    historical = now - timedelta(days=7)
    bands = [("spectral_bands", "red"), ("spectral_bands", "green"), ("spectral_bands", "blue")]
    common = [
        ("lon", str(site["lon"])),
        ("lat", str(site["lat"])),
        ("size_km", "5.0"),
        ("window_seconds", "864000"),
        ("return_type", "png"),
        *bands,
    ]
    endpoints = {
        "sentinel_current": (
            "/data/current/image/sentinel",
            [*common, ("timestamp", now.isoformat().replace("+00:00", "Z"))],
            "sentinel_metadata",
        ),
        "sentinel_historical": (
            "/data/image/sentinel",
            [*common, ("timestamp", historical.isoformat().replace("+00:00", "Z"))],
            "sentinel_metadata",
        ),
        "mapbox_context": (
            "/data/current/image/mapbox",
            [
                ("lon_target", str(site["lon"])),
                ("lat_target", str(site["lat"])),
                ("lon_satellite", str(site["lon"])),
                ("lat_satellite", str(site["lat"])),
                ("alt_satellite", "800.0"),
            ],
            "mapbox_metadata",
        ),
    }
    results: Dict[str, Any] = {}
    for label, (path, params, header_name) in endpoints.items():
        url = f"{simsat_base_url}{path}?{urllib.parse.urlencode(params)}"
        status, body, headers = _http_bytes(url, timeout=timeout)
        metadata = _parse_json_header(headers, header_name)
        image_available = bool(metadata.get("image_available", status == 200 and len(body) > 0))
        results[label] = {
            "status": status,
            "ok": status == 200 and image_available and len(body) > 0,
            "bytes": len(body),
            "metadata": metadata,
            "endpoint": path,
        }
    return {
        "ok": all(item["ok"] for item in results.values()),
        "endpoints": results,
    }


def _scan_site(api_base_url: str, site_id: str, timeout: int) -> Dict[str, Any]:
    status, body = _http_json(
        "POST",
        f"{api_base_url}/sites/{site_id}/scan",
        payload={"force_refresh": True},
        timeout=timeout,
    )
    result: Dict[str, Any] = {
        "status": status,
        "ok": status == 200,
        "response": body,
    }
    if status != 200:
        return result
    scan_id = body.get("scan_id")
    if scan_id:
        ev_status, evidence = _http_json("GET", f"{api_base_url}/scans/{scan_id}/evidence", timeout=60)
        metadata = evidence.get("metadata", {}) if ev_status == 200 else {}
        result.update(
            {
                "scan_id": scan_id,
                "incident_id": body.get("incident_id"),
                "evidence_status": ev_status,
                "inference_mode": (metadata.get("inference") or {}).get("mode"),
                "live_fetch_status": (metadata.get("imagery_provenance") or {}).get("live_fetch_status"),
            }
        )
    return result


def _write_report(report: Dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    rows = []
    for site in report["sites"]:
        rows.append(
            "| "
            + " | ".join(
                [
                    site["site_id"],
                    site["region"],
                    site["country"],
                    "yes" if site["probe_ok"] else "no",
                    str(site["success_count"]),
                    str(site["failure_count"]),
                ]
            )
            + " |"
        )
    table = "\n".join(rows)
    title = "Global Live API Probe Report" if report.get("probe_only") else "Global Live Scan Collection Report"
    markdown_path.write_text(
        f"""# {title}

Generated: {report["generated_at"]}

- Target samples: {report["target_samples"]}
- Successes: {report["success_count"]}
- Failures: {report["failure_count"]}
- Unique successful sites: {report["unique_successful_sites"]}

| Site | Region | Country | Probe OK | Scan Successes | Scan Failures |
|---|---|---|---|---:|---:|
{table}
""",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> Dict[str, Any]:
    csv_path = Path(args.csv)
    sites = _load_sites(csv_path)
    if args.regions:
        wanted = {r.strip().lower() for r in args.regions.split(",") if r.strip()}
        sites = [s for s in sites if str(s["metadata"].get("region", "")).lower() in wanted]
    api_base_url = args.api_base_url.rstrip("/")
    simsat_base_url = args.simsat_base_url.rstrip("/")

    status, health = _http_json("GET", f"{api_base_url}/health", timeout=20)
    if status != 200 or health.get("status") != "ok":
        raise RuntimeError(f"API health failed: {status} {health}")

    report_sites: List[Dict[str, Any]] = []
    attempts: List[Dict[str, Any]] = []
    success_count = 0
    failure_count = 0
    successful_sites = set()

    for site in sites:
        registration = _register_site(api_base_url, site)
        probe = _probe_site(simsat_base_url, site, timeout=args.probe_timeout)
        site_report = {
            "site_id": site["site_id"],
            "name": site["name"],
            "region": str(site["metadata"].get("region", "")),
            "country": site["country"],
            "dataset_split": str(site["metadata"].get("dataset_split", "")),
            "registration": registration,
            "probe_ok": bool(probe["ok"]),
            "probe": probe,
            "success_count": 0,
            "failure_count": 0,
        }
        report_sites.append(site_report)
        _write_report(
            _summary(args, report_sites, attempts, success_count, failure_count, successful_sites),
            Path(args.output_json),
            Path(args.output_md),
        )

    if args.probe_only:
        return _summary(args, report_sites, attempts, success_count, failure_count, successful_sites)

    eligible = [site for site, site_report in zip(sites, report_sites) if site_report["registration"]["ok"] and site_report["probe_ok"]]
    for repeat in range(1, args.repeats_per_site + 1):
        for site in eligible:
            if success_count >= args.target_samples:
                return _summary(args, report_sites, attempts, success_count, failure_count, successful_sites)
            print(f"[collect] scan repeat={repeat} site={site['site_id']}")
            scan = _scan_site(api_base_url, site["site_id"], timeout=args.scan_timeout)
            ok = bool(scan.get("ok") and scan.get("inference_mode") == "live" and scan.get("live_fetch_status") == "live")
            site_report = next(r for r in report_sites if r["site_id"] == site["site_id"])
            if ok:
                success_count += 1
                successful_sites.add(site["site_id"])
                site_report["success_count"] += 1
            else:
                failure_count += 1
                site_report["failure_count"] += 1
            attempts.append(
                {
                    "site_id": site["site_id"],
                    "repeat": repeat,
                    "ok": ok,
                    "scan": scan,
                    "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                }
            )
            _write_report(
                _summary(args, report_sites, attempts, success_count, failure_count, successful_sites),
                Path(args.output_json),
                Path(args.output_md),
            )
            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
    return _summary(args, report_sites, attempts, success_count, failure_count, successful_sites)


def _summary(
    args: argparse.Namespace,
    sites: List[Dict[str, Any]],
    attempts: List[Dict[str, Any]],
    success_count: int,
    failure_count: int,
    successful_sites: set,
) -> Dict[str, Any]:
    return {
        "artifact_version": "global_live_collection.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "csv": str(args.csv),
        "api_base_url": args.api_base_url.rstrip("/"),
        "simsat_base_url": args.simsat_base_url.rstrip("/"),
        "target_samples": args.target_samples,
        "repeats_per_site": args.repeats_per_site,
        "probe_only": bool(args.probe_only),
        "success_count": success_count,
        "failure_count": failure_count,
        "unique_successful_sites": len(successful_sites),
        "sites": sites,
        "attempts": attempts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect live global scan samples for Phase 6 training.")
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--simsat-base-url", default="http://127.0.0.1:9005")
    parser.add_argument("--target-samples", type=int, default=180)
    parser.add_argument("--repeats-per-site", type=int, default=8)
    parser.add_argument("--regions", default="", help="Optional comma-separated region filter")
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--probe-timeout", type=int, default=90)
    parser.add_argument("--scan-timeout", type=int, default=420)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--output-json", default=str(DEFAULT_JSON_REPORT))
    parser.add_argument("--output-md", default=str(DEFAULT_MD_REPORT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
    except Exception as exc:
        print(f"[collect] FAIL: {exc}")
        return 1
    _write_report(report, Path(args.output_json), Path(args.output_md))
    print(json.dumps({k: report[k] for k in ("success_count", "failure_count", "unique_successful_sites")}, indent=2))
    print(f"[collect] report json: {args.output_json}")
    print(f"[collect] report markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
