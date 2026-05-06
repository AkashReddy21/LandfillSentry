"""Safely upload a PEFT LoRA adapter folder to Hugging Face.

This script intentionally refuses to upload the project root. A model upload
should contain only publishable adapter artifacts and documentation, never
`.env.local`, caches, logs, databases, or source checkouts.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_ID = "akashreddy2103/landfill"
REQUIRED_ADAPTER_FILES = ("adapter_config.json", "adapter_model.safetensors")


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _token_configured() -> bool:
    return bool(os.getenv("HF_TOKEN", "").strip() or os.getenv("HUGGINGFACE_TOKEN", "").strip())


def _candidate_tokens() -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name in ("HUGGINGFACE_TOKEN", "HF_TOKEN"):
        value = os.getenv(name, "").strip()
        if value and value not in seen:
            tokens.append((name, value))
            seen.add(value)
    return tokens


def _validate_adapter_dir(adapter_dir: Path) -> None:
    resolved = adapter_dir.resolve()
    if resolved == PROJECT_ROOT.resolve():
        raise SystemExit("Refusing to upload the project root. Pass a folder containing only adapter files.")
    missing = [name for name in REQUIRED_ADAPTER_FILES if not (resolved / name).exists()]
    if missing:
        raise SystemExit(
            "Adapter folder is missing required files: "
            + ", ".join(missing)
            + f"\nExpected a PEFT adapter folder, got: {resolved}"
        )


def _ensure_model_card(adapter_dir: Path, repo_id: str) -> None:
    readme = adapter_dir / "README.md"
    if readme.exists():
        return
    readme.write_text(
        f"""---
library_name: peft
base_model: LiquidAI/LFM2.5-VL-450M
tags:
- peft
- lora
- vision-language
- satellite-imagery
- methane-monitoring
---

# LandfillSentry LFM2.5-VL LoRA Adapter

Repository: `{repo_id}`

This adapter is intended for LandfillSentry landfill methane/plume triage with
DPhi SimSat satellite imagery. See the project repository docs for dataset
construction, evaluation, and limitations:

- `docs/fine_tuning_methodology.md`
- `docs/benchmark_summary_for_submission.md`
- `data/manifests/dataset_manifest_v1.json`
- `data/manifests/phase7_evaluation_report.json`

Base model: `LiquidAI/LFM2.5-VL-450M`.
""",
        encoding="utf-8",
    )


def upload_adapter(adapter_dir: Path, repo_id: str) -> None:
    _load_env_file(PROJECT_ROOT / ".env.local")
    _validate_adapter_dir(adapter_dir)
    _ensure_model_card(adapter_dir, repo_id)

    try:
        from huggingface_hub import HfApi, upload_folder
    except Exception as exc:
        raise SystemExit(f"huggingface_hub is not installed or importable: {exc}") from exc

    tokens = _candidate_tokens()
    if not tokens:
        raise SystemExit("Missing HF_TOKEN or HUGGINGFACE_TOKEN in environment/.env.local")

    last_error: Exception | None = None
    for token_name, token in tokens:
        try:
            api = HfApi(token=token)
            api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
            upload_folder(
                folder_path=str(adapter_dir.resolve()),
                repo_id=repo_id,
                repo_type="model",
                token=token,
                ignore_patterns=[
                    ".env*",
                    "__pycache__/",
                    "*.pyc",
                    "*.db",
                    "*.log",
                    "data/cache/",
                    "data/logs/",
                    "data/tmp/",
                ],
            )
            print(f"Uploaded adapter folder to https://huggingface.co/{repo_id}")
            print(f"Token used: {token_name}")
            print(f"Set HF_ADAPTER_ID={repo_id}")
            return
        except Exception as exc:
            last_error = exc
            print(f"Upload attempt with {token_name} failed: {type(exc).__name__}")

    raise SystemExit(f"All configured Hugging Face tokens failed to upload. Last error: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload a PEFT adapter folder to Hugging Face.")
    parser.add_argument("--adapter-dir", required=True, help="Folder containing adapter_config.json and adapter_model.safetensors")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    args = parser.parse_args()

    if not _token_configured():
        _load_env_file(PROJECT_ROOT / ".env.local")
    upload_adapter(Path(args.adapter_dir), args.repo_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
