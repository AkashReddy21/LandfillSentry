"""Upload a sanitized LandfillSentry submission package to Hugging Face."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_ID = "akashreddy2103/landfill"

ALLOWLIST = {
    "docs/hf_model_card.md": "README.md",
    "docs/architecture_for_judges.md": "architecture_for_judges.md",
    "docs/fine_tuning_methodology.md": "fine_tuning_methodology.md",
    "docs/benchmark_summary_for_submission.md": "benchmark_summary_for_submission.md",
    "docs/judge_deployment_runbook.md": "judge_deployment_runbook.md",
    "docs/judge_submission_brief.md": "judge_submission_brief.md",
    "docs/latest_live_smoke_proof.md": "latest_live_smoke_proof.md",
    "docs/latest_live_scan_artifact.md": "latest_live_scan_artifact.md",
    "data/manifests/dataset_manifest_v1.json": "dataset_manifest_v1.json",
    "data/manifests/dataset_splits_v1.json": "dataset_splits_v1.json",
    "data/manifests/phase7_evaluation_report.json": "phase7_evaluation_report.json",
    "data/manifests/tuned_checkpoint_v1.json": "tuned_checkpoint_v1.json",
    "scripts/build_phase6_dataset.py": "training_code/build_phase6_dataset.py",
    "scripts/benchmark_models.py": "training_code/benchmark_models.py",
    "scripts/upload_hf_adapter.py": "training_code/upload_hf_adapter.py",
    "ml/training/dataset_manifest.py": "training_code/ml/training/dataset_manifest.py",
    "ml/training/lora_artifacts.py": "training_code/ml/training/lora_artifacts.py",
    "ml/training/modal_lora_train.py": "training_code/ml/training/modal_lora_train.py",
    "ml/evaluation/phase7_harness.py": "training_code/ml/evaluation/phase7_harness.py",
}


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def build_package(out_dir: Path) -> Path:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for src_rel, dest_rel in ALLOWLIST.items():
        src = PROJECT_ROOT / src_rel
        if not src.exists():
            raise SystemExit(f"Missing allowlisted file: {src_rel}")
        dest = out_dir / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return out_dir


def _candidate_tokens() -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name in ("HUGGINGFACE_TOKEN", "HF_TOKEN"):
        value = os.getenv(name, "").strip()
        if value and value not in seen:
            tokens.append((name, value))
            seen.add(value)
    return tokens


def upload_package(package_dir: Path, repo_id: str, create_pr: bool = False) -> None:
    _load_env_file(PROJECT_ROOT / ".env.local")
    tokens = _candidate_tokens()
    if not tokens:
        raise SystemExit("Missing HF_TOKEN or HUGGINGFACE_TOKEN in environment/.env.local")

    try:
        from huggingface_hub import HfApi, upload_folder
    except Exception as exc:
        raise SystemExit(f"huggingface_hub is not installed or importable: {exc}") from exc

    last_error: Exception | None = None
    for token_name, token in tokens:
        try:
            api = HfApi(token=token)
            api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
            info = upload_folder(
                folder_path=str(package_dir.resolve()),
                repo_id=repo_id,
                repo_type="model",
                token=token,
                create_pr=create_pr,
            )
            print(f"Uploaded sanitized submission package to https://huggingface.co/{repo_id}")
            print(f"Token used: {token_name}")
            print(info)
            return
        except Exception as exc:
            last_error = exc
            print(f"Upload attempt with {token_name} failed: {type(exc).__name__}")

    raise SystemExit(f"All configured Hugging Face tokens failed to upload. Last error: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload sanitized LandfillSentry docs/artifacts to Hugging Face.")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--package-dir", default=str(PROJECT_ROOT / ".tmp" / "hf_landfill_publish"))
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--create-pr", action="store_true", help="Upload as a Hugging Face pull request.")
    args = parser.parse_args()

    package_dir = build_package(Path(args.package_dir))
    print(f"Built package: {package_dir}")
    if not args.build_only:
        upload_package(package_dir, args.repo_id, create_pr=args.create_pr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
