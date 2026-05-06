"""Judge readiness preflight for LandfillSentry."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env(name: str, env_file: Dict[str, str], default: str = "") -> str:
    return os.getenv(name, env_file.get(name, default)).strip()


def _http_ok(url: str, timeout: int = 8) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - local/user-provided preflight URL
            return 200 <= int(resp.status) < 500, f"HTTP {resp.status}"
    except Exception as exc:
        return False, str(exc)


def _hf_file_exists(repo_id: str, filename: str, token: str | None = None) -> tuple[bool, str]:
    if not repo_id:
        return False, "repo id missing"
    try:
        from huggingface_hub import hf_hub_download

        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            repo_type="model",
            token=token,
            local_files_only=False,
        )
        return True, f"{filename} found"
    except Exception as exc:
        return False, str(exc)


def _add(checks: List[Dict[str, Any]], name: str, ok: bool, detail: str, required: bool = True) -> None:
    checks.append({"name": name, "ok": ok, "required": required, "detail": detail})


def run(args: argparse.Namespace) -> Dict[str, Any]:
    env_file_path = PROJECT_ROOT / args.env_file
    env_file = _load_env_file(env_file_path)
    checks: List[Dict[str, Any]] = []

    required_files = [
        "Dockerfile",
        "docker-compose.landfillsentry.yml",
        "scripts/start_judge_mode.ps1",
        "scripts/live_smoke.py",
        "scripts/export_openapi.py",
        "docs/judge_deployment_runbook.md",
        "docs/benchmark_summary_for_submission.md",
        "data/manifests/dataset_manifest_v1.json",
        "data/manifests/phase7_evaluation_report.json",
    ]
    for rel_path in required_files:
        path = PROJECT_ROOT / rel_path
        _add(checks, f"file:{rel_path}", path.exists(), "present" if path.exists() else "missing")

    docker_available = shutil.which("docker") is not None
    _add(checks, "docker-cli", docker_available, "docker found" if docker_available else "docker not found")

    compose = PROJECT_ROOT / "docker-compose.landfillsentry.yml"
    if compose.exists():
        text = compose.read_text(encoding="utf-8")
        _add(checks, "compose:api-service", "landfillsentry-api" in text, "landfillsentry-api service declared")
        _add(checks, "compose:health-port", "8000:8000" in text, "port 8000 published")

    spec_path = PROJECT_ROOT / "openapi.json"
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        paths = set((spec.get("paths") or {}).keys())
        required_paths = {
            "/health",
            "/runtime/status",
            "/ops/summary",
            "/watchlist",
            "/sites/{site_id}/scan",
            "/incidents/{incident_id}/review",
            "/incidents/{incident_id}/export",
        }
        _add(checks, "openapi:current-version", spec.get("info", {}).get("version") == "0.8.0", str(spec.get("info", {})))
        _add(checks, "openapi:judge-paths", required_paths.issubset(paths), f"{len(paths)} paths exported")
        schemas = spec.get("components", {}).get("schemas", {})
        panel_required = schemas.get("EvidencePanel", {}).get("required", [])
        _add(
            checks,
            "openapi:mapbox-panel-contract",
            "mapbox_context_path" in panel_required,
            "EvidencePanel requires mapbox_context_path",
        )
    except Exception as exc:
        _add(checks, "openapi:parse", False, str(exc))

    strict_live = _env("REQUIRE_LIVE_RESULTS", env_file, "true").lower() == "true"
    fallback_disabled = _env("INFERENCE_ALLOW_FALLBACK", env_file, "false").lower() == "false"
    inference_live = _env("INFERENCE_MODE", env_file, "live").lower() == "live"
    _add(checks, "env:strict-live", strict_live, "REQUIRE_LIVE_RESULTS=true")
    _add(checks, "env:fallback-disabled", fallback_disabled, "INFERENCE_ALLOW_FALLBACK=false")
    _add(checks, "env:inference-live", inference_live, "INFERENCE_MODE=live")
    _add(checks, "inference:tooling", True, "Hugging Face Transformers + PEFT")

    mapbox_token = _env("MAPBOX_TOKEN", env_file) or _env("MAPBOX_ACCESS_TOKEN", env_file)
    hf_token = _env("HF_TOKEN", env_file) or _env("HUGGINGFACE_TOKEN", env_file)
    hf_adapter_id = _env("HF_ADAPTER_ID", env_file)
    _add(checks, "env:mapbox-token", bool(mapbox_token), "configured" if mapbox_token else "missing MAPBOX_TOKEN")
    _add(checks, "env:hf-token", bool(hf_token), "configured" if hf_token else "missing HF_TOKEN/HUGGINGFACE_TOKEN")
    _add(
        checks,
        "env:public-adapter-id",
        bool(hf_adapter_id),
        hf_adapter_id or "missing HF_ADAPTER_ID; fine-tuned public weights cannot be claimed",
        required=bool(args.strict_public_weights),
    )
    if hf_adapter_id:
        ok_config, detail_config = _hf_file_exists(hf_adapter_id, "adapter_config.json", token=hf_token or None)
        ok_weights, detail_weights = _hf_file_exists(hf_adapter_id, "adapter_model.safetensors", token=hf_token or None)
        _add(
            checks,
            "hf:adapter-config",
            ok_config,
            detail_config,
            required=bool(args.strict_public_weights),
        )
        _add(
            checks,
            "hf:adapter-weights",
            ok_weights,
            detail_weights,
            required=bool(args.strict_public_weights),
        )

    if args.check_running:
        ok, detail = _http_ok(args.api_base_url.rstrip("/") + "/health")
        _add(checks, "http:api-health", ok, detail)
        ok, detail = _http_ok(args.api_base_url.rstrip("/") + "/ops")
        _add(checks, "http:ops-ui", ok, detail)
        ok, detail = _http_ok(args.simsat_base_url.rstrip("/"))
        _add(checks, "http:simsat", ok, detail)

    blocking_failures = [check for check in checks if check["required"] and not check["ok"]]
    warnings = [check for check in checks if not check["required"] and not check["ok"]]
    return {
        "status": "pass" if not blocking_failures else "fail",
        "blocking_failure_count": len(blocking_failures),
        "warning_count": len(warnings),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run judge deployment readiness checks.")
    parser.add_argument("--env-file", default=".env.local")
    parser.add_argument("--check-running", action="store_true")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--simsat-base-url", default="http://127.0.0.1:9005")
    parser.add_argument("--strict-public-weights", action="store_true")
    args = parser.parse_args()

    report = run(args)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
