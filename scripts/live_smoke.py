"""Deterministic live-mode smoke test for judge readiness."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROOF_JSON = PROJECT_ROOT / "data" / "processed" / "live_smoke_proof.json"
DEFAULT_PROOF_MD = PROJECT_ROOT / "docs" / "latest_live_smoke_proof.md"


def _http_json(method: str, url: str, payload: Dict | None = None, timeout: int = 120) -> Tuple[int, Dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            if body:
                return resp.status, json.loads(body)
            return resp.status, {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"{method} {url} failed: {exc}") from exc


def _http_status(url: str, timeout: int = 30) -> int:
    req = urllib.request.Request(url=url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status


def _choose_site(watchlist: Dict) -> str:
    items = watchlist.get("items", [])
    if not items:
        raise RuntimeError("watchlist is empty; register at least one site before smoke test")
    preferred = [i for i in items if not str(i.get("site_id", "")).startswith("LF_DEMO_")]
    target = preferred[0] if preferred else items[0]
    return str(target["site_id"])


def _proof_markdown(proof: Dict[str, Any]) -> str:
    result = proof.get("result", {})
    previews = ", ".join(result.get("preview_keys", [])) or "none"
    return f"""# Live Smoke Proof

Generated: {proof.get("generated_at")}

## Command

```bash
python scripts/live_smoke.py --api-base-url {proof.get("api_base_url")} --simsat-base-url {proof.get("simsat_base_url")}
```

## Result

- Status: {proof.get("status")}
- Site: {result.get("site_id")}
- Scan ID: {result.get("scan_id")}
- Incident ID: {result.get("incident_id")}
- Inference mode: {result.get("inference_mode")}
- Inference tooling: {result.get("inference_tooling")}
- Panel preview keys: {previews}

## Checks

- SimSat health returned HTTP 200.
- API `/health` returned `status=ok`.
- Watchlist returned at least one site.
- Live scan completed.
- Evidence metadata reported `inference.mode=live`.
- Site detail returned panel previews.
- Review status persisted through export.
- Incident export returned evidence.
"""


def _write_proof(proof: Dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(proof, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(_proof_markdown(proof), encoding="utf-8")
    print(f"[smoke] proof json: {json_path}")
    print(f"[smoke] proof markdown: {markdown_path}")


def run(api_base_url: str, simsat_base_url: str) -> Dict[str, Any]:
    print(f"[smoke] checking SimSat at {simsat_base_url}")
    simsat_status = _http_status(simsat_base_url, timeout=20)
    if simsat_status != 200:
        raise RuntimeError(f"SimSat not healthy: status={simsat_status}")
    print("[smoke] SimSat OK")

    print(f"[smoke] checking API at {api_base_url}/health")
    health_status, health = _http_json("GET", f"{api_base_url}/health", timeout=20)
    if health_status != 200 or health.get("status") != "ok":
        raise RuntimeError(f"API health check failed: {health_status} {health}")
    print("[smoke] API health OK")
    _status, runtime = _http_json("GET", f"{api_base_url}/runtime/status", timeout=30)

    print("[smoke] loading watchlist")
    _status, watchlist = _http_json("GET", f"{api_base_url}/watchlist", timeout=60)
    site_id = _choose_site(watchlist)
    print(f"[smoke] selected site: {site_id}")

    print("[smoke] running live scan")
    _status, scan = _http_json(
        "POST",
        f"{api_base_url}/sites/{site_id}/scan",
        payload={"force_refresh": True},
        timeout=360,
    )
    scan_id = scan["scan_id"]
    incident_id = scan["incident_id"]
    print(f"[smoke] scan complete: {scan_id}, incident: {incident_id}")

    print("[smoke] validating evidence payload")
    _status, evidence = _http_json("GET", f"{api_base_url}/scans/{scan_id}/evidence", timeout=60)
    inference_mode = evidence.get("metadata", {}).get("inference", {}).get("mode")
    if inference_mode != "live":
        raise RuntimeError(f"inference mode is not live: {inference_mode}")

    print("[smoke] validating site detail previews")
    _status, detail = _http_json("GET", f"{api_base_url}/sites/{site_id}/detail", timeout=60)
    previews = detail.get("panel_previews", {})
    missing = [k for k, v in previews.items() if not v]
    if missing:
        raise RuntimeError(f"missing panel previews: {missing}")

    print("[smoke] validating review persistence")
    _http_json(
        "POST",
        f"{api_base_url}/incidents/{incident_id}/review",
        payload={
            "incident_id": incident_id,
            "review_status": "published",
            "feedback_status": "confirmed",
            "review_comment": "live smoke check",
        },
        timeout=60,
    )
    _status, export_all = _http_json("GET", f"{api_base_url}/incidents/export?format=json", timeout=60)
    rows = export_all.get("incidents", [])
    matched = [r for r in rows if r.get("incident_id") == incident_id]
    if not matched or matched[0].get("review_status") != "published":
        raise RuntimeError("review state did not persist in export feed")

    print("[smoke] validating incident export endpoint")
    status, export_one = _http_json(
        "GET",
        f"{api_base_url}/incidents/{incident_id}/export?format=json",
        timeout=60,
    )
    if status != 200 or not export_one.get("evidence"):
        raise RuntimeError("incident export endpoint returned invalid payload")

    print("[smoke] PASS")
    result = {
        "site_id": site_id,
        "scan_id": scan_id,
        "incident_id": incident_id,
        "inference_mode": inference_mode,
        "inference_tooling": runtime.get("inference_tooling", "Hugging Face Transformers + PEFT"),
        "preview_keys": list(previews.keys()),
    }
    print(json.dumps(result, indent=2))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live smoke tests for judge-mode readiness.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--simsat-base-url", default="http://127.0.0.1:9005")
    parser.add_argument("--proof-json", default=str(DEFAULT_PROOF_JSON))
    parser.add_argument("--proof-md", default=str(DEFAULT_PROOF_MD))
    parser.add_argument("--no-save-proof", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_base_url = args.api_base_url.rstrip("/")
    simsat_base_url = args.simsat_base_url.rstrip("/")
    try:
        result = run(api_base_url=api_base_url, simsat_base_url=simsat_base_url)
        if not args.no_save_proof:
            proof = {
                "artifact_version": "judge.live_smoke.v1",
                "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "status": "PASS",
                "api_base_url": api_base_url,
                "simsat_base_url": simsat_base_url,
                "result": result,
            }
            _write_proof(proof, Path(args.proof_json), Path(args.proof_md))
        return 0
    except Exception as exc:
        print(f"[smoke] FAIL: {exc}")
        if not args.no_save_proof:
            proof = {
                "artifact_version": "judge.live_smoke.v1",
                "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "status": "FAIL",
                "api_base_url": api_base_url,
                "simsat_base_url": simsat_base_url,
                "error": str(exc),
            }
            _write_proof(proof, Path(args.proof_json), Path(args.proof_md))
        return 1


if __name__ == "__main__":
    sys.exit(main())
