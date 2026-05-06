from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path


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


def _extract_training_result(stdout: str) -> dict | None:
    marker = "TRAINING_RESULT_JSON:"
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line.startswith(marker):
            payload = line.split(marker, 1)[1].strip()
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return None

    match = re.search(r"Training scaffold result:\s*(\{.*\})", stdout)
    if not match:
        return None
    try:
        return ast.literal_eval(match.group(1))
    except Exception:
        return None


def _write_checkpoint_record(result: dict) -> Path:
    checkpoint_path = PROJECT_ROOT / "data" / "manifests" / "tuned_checkpoint_v1.json"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "record_version": "phase6.checkpoint.v1",
        "generated_by": "scripts/modal_gpu_check.py",
        "result": result,
    }
    checkpoint_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return checkpoint_path


def _print_stream(text: str, *, stderr: bool = False) -> None:
    if not text:
        return
    stream = sys.stderr if stderr else sys.stdout
    encoding = stream.encoding or "utf-8"
    safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    print(safe, end="", file=stream)


def main() -> None:
    _load_env_file(PROJECT_ROOT / ".env.local")

    token_id = os.getenv("MODAL_TOKEN_ID", "").strip()
    token_secret = os.getenv("MODAL_TOKEN_SECRET", "").strip()
    if not token_id or not token_secret:
        print("Modal credentials missing.")
        print("Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in .env.local")
        print("Get them by running: modal token new")
        sys.exit(1)

    config_payload = {
        "epochs": int(os.getenv("LORA_EPOCHS", "1")),
        "model_id": os.getenv("HF_MODEL_ID", "LiquidAI/LFM2.5-VL-450M"),
        "revision": os.getenv("HF_MODEL_REVISION", "main"),
        "dataset_manifest_path": "data/manifests/dataset_manifest_v1.json",
        "dataset_split_path": "data/manifests/dataset_splits_v1.json",
        "learning_rate": float(os.getenv("LORA_LEARNING_RATE", "0.0002")),
        "lora_alpha": int(os.getenv("LORA_ALPHA", "16")),
        "lora_dropout": float(os.getenv("LORA_DROPOUT", "0.05")),
        "lora_r": int(os.getenv("LORA_R", "8")),
        "max_eval_samples": int(os.getenv("LORA_MAX_EVAL_SAMPLES", "8")),
        "max_steps": int(os.getenv("LORA_MAX_STEPS", "24")),
        "max_train_samples": int(os.getenv("LORA_MAX_TRAIN_SAMPLES", "49")),
        "seed": int(os.getenv("LORA_SEED", "2103")),
    }
    output_dir = str(PROJECT_ROOT / "data" / "processed" / "hf_adapter_trained")

    cmd = [
        sys.executable,
        "-m",
        "modal",
        "run",
        "ml/training/modal_lora_train.py",
        "--config-json",
        json.dumps(config_payload, sort_keys=True),
        "--output-dir",
        output_dir,
    ]
    print("Running Modal LoRA training:")
    print(" ".join(cmd[:6] + ["<config-json>", "--output-dir", output_dir]))
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        errors="replace",
    )
    _print_stream(result.stdout)
    _print_stream(result.stderr, stderr=True)

    if result.returncode == 0:
        training_result = _extract_training_result(result.stdout)
        if training_result:
            record_path = _write_checkpoint_record(training_result)
            print(f"Saved Phase 6 checkpoint record: {record_path}")
        else:
            print("Warning: training completed but no structured result payload was found in stdout.")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
