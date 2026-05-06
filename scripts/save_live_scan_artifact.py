"""Run one strict-live scan and save judge-facing evidence artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _http_json(method: str, url: str, payload: Dict | None = None, timeout: int = 360) -> Tuple[int, Dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def _choose_site(watchlist: Dict, requested_site_id: str | None) -> str:
    if requested_site_id:
        return requested_site_id
    items = watchlist.get("items", [])
    if not items:
        raise RuntimeError("watchlist is empty")
    live_ready = [item for item in items if str(item.get("generation_mode", "")).lower() == "live"]
    return str((live_ready or items)[0]["site_id"])


def _artifact_markdown(payload: Dict) -> str:
    runtime = payload["runtime_status"]
    scan = payload["scan_result"]
    detail = payload["site_detail"]
    evidence = payload["evidence"]
    incident = detail.get("latest_incident") or {}
    metadata = evidence.get("metadata", {})
    provenance = metadata.get("imagery_provenance", {})
    inference = metadata.get("inference", {})
    assets = provenance.get("assets", {})
    endpoints = provenance.get("endpoints", {})

    rows = []
    for label, asset in assets.items():
        rows.append(
            "| "
            + " | ".join(
                [
                    label,
                    str(asset.get("source", "")),
                    str(asset.get("timestamp_captured", "")),
                    str(asset.get("cloud_cover", "")),
                    str(asset.get("local_path", "")),
                ]
            )
            + " |"
        )

    asset_table = "\n".join(rows) if rows else "| none | none | none | none | none |"
    endpoint_lines = "\n".join(f"- {label}: `{endpoint}`" for label, endpoint in endpoints.items())
    if not endpoint_lines:
        endpoint_lines = (
            "- Sentinel current: `/data/current/image/sentinel`\n"
            "- Sentinel historical: `/data/image/sentinel`\n"
            "- Mapbox context: `/data/current/image/mapbox`"
        )
    generated_at = payload["generated_at"]
    return f"""# Live Scan Artifact

Generated: {generated_at}

## Runtime

- Imagery provider: {runtime.get("imagery_provider")}
- Provider repository: {runtime.get("imagery_provider_repository")}
- SimSat reachable: {runtime.get("simsat_reachable")}
- Live scan available: {runtime.get("live_scan_available")}
- Scan policy: {runtime.get("scan_policy")}
- SimSat base URL: {runtime.get("simsat_base_url")}
- Inference tooling: {runtime.get("inference_tooling", "Hugging Face Transformers + PEFT")}

## Scan

- Site: {scan.get("site_id")}
- Scan ID: {scan.get("scan_id")}
- Incident ID: {scan.get("incident_id")}
- Status: {scan.get("status")}
- Inference mode: {inference.get("mode")}
- Model: {inference.get("model_ref") or inference.get("model_id")}

## Incident

- Priority: {incident.get("priority_tier")}
- Confidence: {incident.get("confidence")}
- Zone: {incident.get("likely_source_zone")}
- Review status: {incident.get("review_status")}

{incident.get("evidence_summary", "")}

## DPhi SimSat Provenance

- Provider: {provenance.get("provider", "DPhi SimSat")}
- Repository: {provenance.get("provider_repository", "https://github.com/DPhi-Space/SimSat")}
- Fetch status: {provenance.get("live_fetch_status")}
- Source chain: `{provenance.get("source_chain", [])}`

Endpoints:

{endpoint_lines}

| Asset | Source | Captured | Cloud Cover | Local Path |
|---|---|---|---:|---|
{asset_table}
"""


def _load_existing_scan(api_base_url: str, scan_id: str) -> Dict:
    _status, scan = _http_json("GET", f"{api_base_url}/scans/{scan_id}", timeout=60)
    _status, runtime = _http_json("GET", f"{api_base_url}/runtime/status", timeout=30)
    _status, evidence = _http_json("GET", f"{api_base_url}/scans/{scan_id}/evidence", timeout=60)
    _status, detail = _http_json("GET", f"{api_base_url}/sites/{scan['site_id']}/detail", timeout=60)
    _status, export = _http_json(
        "GET",
        f"{api_base_url}/incidents/{scan['incident_id']}/export?format=json",
        timeout=60,
    )
    return {
        "runtime_status": runtime,
        "scan_result": scan,
        "site_detail": detail,
        "evidence": evidence,
        "incident_export": export,
    }


def run(api_base_url: str, site_id: str | None, scan_id: str | None = None) -> Dict:
    if scan_id:
        payload = _load_existing_scan(api_base_url=api_base_url, scan_id=scan_id)
        metadata = payload["evidence"].get("metadata", {})
        provenance = metadata.get("imagery_provenance", {})
        inference = metadata.get("inference", {})
        if provenance.get("live_fetch_status") != "live":
            raise RuntimeError(f"expected live imagery fetch, got {provenance.get('live_fetch_status')}")
        if inference.get("mode") != "live":
            raise RuntimeError(f"expected live inference, got {inference.get('mode')}")
        return {
            "artifact_version": "judge.live_scan.v1",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            **payload,
        }

    _status, runtime = _http_json("GET", f"{api_base_url}/runtime/status", timeout=30)
    if not runtime.get("simsat_reachable") or not runtime.get("live_scan_available"):
        raise RuntimeError(f"strict live runtime is not ready: {runtime}")

    _status, watchlist = _http_json("GET", f"{api_base_url}/watchlist?include_summary=true&page_size=200", timeout=60)
    selected_site_id = _choose_site(watchlist, site_id)

    _status, scan = _http_json(
        "POST",
        f"{api_base_url}/sites/{selected_site_id}/scan",
        payload={"force_refresh": True},
        timeout=900,
    )
    scan_id = scan["scan_id"]

    _status, evidence = _http_json("GET", f"{api_base_url}/scans/{scan_id}/evidence", timeout=60)
    _status, detail = _http_json("GET", f"{api_base_url}/sites/{selected_site_id}/detail", timeout=60)
    _status, export = _http_json(
        "GET",
        f"{api_base_url}/incidents/{scan['incident_id']}/export?format=json",
        timeout=60,
    )

    metadata = evidence.get("metadata", {})
    provenance = metadata.get("imagery_provenance", {})
    inference = metadata.get("inference", {})
    if provenance.get("live_fetch_status") != "live":
        raise RuntimeError(f"expected live imagery fetch, got {provenance.get('live_fetch_status')}")
    if inference.get("mode") != "live":
        raise RuntimeError(f"expected live inference, got {inference.get('mode')}")

    return {
        "artifact_version": "judge.live_scan.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "runtime_status": runtime,
        "scan_result": scan,
        "site_detail": detail,
        "evidence": evidence,
        "incident_export": export,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Save one strict-live scan artifact for judging.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--site-id", default=None)
    parser.add_argument("--scan-id", default=None)
    args = parser.parse_args()

    try:
        payload = run(api_base_url=args.api_base_url.rstrip("/"), site_id=args.site_id, scan_id=args.scan_id)
    except Exception as exc:
        print(f"[live-artifact] FAIL: {exc}")
        return 1

    out_dir = PROJECT_ROOT / "data" / "processed" / "judge_live_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    scan_id = payload["scan_result"]["scan_id"]
    json_path = out_dir / f"{scan_id}.json"
    md_path = PROJECT_ROOT / "docs" / "latest_live_scan_artifact.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(_artifact_markdown(payload), encoding="utf-8")

    print("[live-artifact] PASS")
    print(f"- JSON: {json_path}")
    print(f"- Markdown: {md_path}")
    print(json.dumps({"scan_id": scan_id, "site_id": payload["scan_result"]["site_id"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
