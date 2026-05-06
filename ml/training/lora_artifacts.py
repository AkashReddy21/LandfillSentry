from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def normalize_training_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "model_id": str(config.get("model_id", "LiquidAI/LFM2.5-VL-450M")),
        "revision": str(config.get("revision", "main")),
        "epochs": int(config.get("epochs", 1)),
        "learning_rate": float(config.get("learning_rate", 2e-4)),
        "lora_r": int(config.get("lora_r", 16)),
        "lora_alpha": int(config.get("lora_alpha", 32)),
        "lora_dropout": float(config.get("lora_dropout", 0.05)),
        "dataset_manifest_path": str(config.get("dataset_manifest_path", "data/manifests/dataset_manifest_v1.json")),
        "dataset_split_path": str(config.get("dataset_split_path", "data/manifests/dataset_splits_v1.json")),
    }


def _stable_hash(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def create_training_artifacts(
    artifact_root: Path,
    run_id: str,
    artifact_volume: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    normalized = normalize_training_config(config)
    run_dir = artifact_root / run_id
    checkpoint_dir = run_dir / "checkpoint-lora-v1"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    adapter_config = {
        "base_model_name_or_path": normalized["model_id"],
        "peft_type": "LORA",
        "r": normalized["lora_r"],
        "lora_alpha": normalized["lora_alpha"],
        "lora_dropout": normalized["lora_dropout"],
        "inference_mode": False,
        "task_type": "CAUSAL_LM",
        "note": "Phase 6 scaffold checkpoint artifact.",
    }
    _write_json(checkpoint_dir / "adapter_config.json", adapter_config)

    # Scaffold artifact to anchor downstream wiring before full trainer loop.
    (checkpoint_dir / "adapter_model.safetensors").write_bytes(
        json.dumps(
            {
                "artifact_type": "phase6.scaffold.weights",
                "note": "Placeholder adapter blob. Replace in full LoRA trainer.",
            },
            sort_keys=True,
        ).encode("utf-8")
    )
    _write_json(
        checkpoint_dir / "training_args.json",
        {
            "epochs": normalized["epochs"],
            "learning_rate": normalized["learning_rate"],
            "dataset_manifest_path": normalized["dataset_manifest_path"],
            "dataset_split_path": normalized["dataset_split_path"],
        },
    )

    reproducibility = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config_hash": _stable_hash(normalized),
        "config": normalized,
    }
    _write_json(run_dir / "reproducibility.json", reproducibility)

    run_manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_volume": artifact_volume,
        "model_id": normalized["model_id"],
        "revision": normalized["revision"],
        "checkpoint_dir": str(checkpoint_dir),
        "adapter_artifact_ref": f"modal-volume://{artifact_volume}/{run_id}/checkpoint-lora-v1",
        "dataset_manifest_path": normalized["dataset_manifest_path"],
        "dataset_split_path": normalized["dataset_split_path"],
        "config_hash": reproducibility["config_hash"],
        "training_mode": "phase6_scaffold",
    }
    manifest_path = run_dir / "run_manifest.json"
    _write_json(manifest_path, run_manifest)

    return {
        "status": "ok",
        "run_id": run_id,
        "manifest_path": str(manifest_path),
        "checkpoint_dir": str(checkpoint_dir),
        "adapter_artifact_ref": run_manifest["adapter_artifact_ref"],
        "artifact_volume": artifact_volume,
        "config_hash": reproducibility["config_hash"],
        "training_mode": "phase6_scaffold",
    }

