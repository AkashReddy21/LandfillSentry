"""
Modal GPU LoRA trainer for LandfillSentry LFM2-VL domain adaptation.

Usage:
    modal run ml/training/modal_lora_train.py --config-json '{"epochs": 1, "max_steps": 24}'
"""

from __future__ import annotations

import base64
import io
import json
import os
import random
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import modal


def _gpu_from_env():
    gpu_name = os.getenv("MODAL_GPU", "L4").strip().upper()
    allowed = {"T4", "L4", "A10G", "A100"}
    return gpu_name if gpu_name in allowed else "L4"


APP_NAME = os.getenv("MODAL_APP_NAME", "landfillsentry-lora-train")
VOLUME_NAME = os.getenv("MODAL_ARTIFACT_VOLUME", "landfillsentry-model-artifacts")
ARTIFACT_ROOT = Path("/artifacts")
REMOTE_PROJECT_ROOT = Path("/workspace")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "accelerate>=1.0.0",
        "huggingface_hub>=1.0.0",
        "peft>=0.13.0",
        "pillow>=10.0.0",
        "safetensors>=0.4.0",
        "sentencepiece>=0.2.0",
        "torch>=2.0.0",
        "torchvision>=0.20.0",
        "transformers>=5.0.0",
    )
    .add_local_dir("apps", "/workspace/apps", copy=True)
    .add_local_dir("ml", "/workspace/ml", copy=True)
    .add_local_dir("data/cache/assets", "/workspace/data/cache/assets", copy=True)
    .add_local_dir("data/labels", "/workspace/data/labels", copy=True)
    .add_local_dir("data/manifests", "/workspace/data/manifests", copy=True)
)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
app = modal.App(APP_NAME)
_secret_values = {
    key: value
    for key in ("HF_TOKEN", "HUGGINGFACE_TOKEN")
    if (value := os.getenv(key, "").strip())
}
hf_secrets = [modal.Secret.from_dict(_secret_values)] if _secret_values else []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "model_id": str(config.get("model_id", "LiquidAI/LFM2.5-VL-450M")),
        "revision": str(config.get("revision", "main")),
        "epochs": int(config.get("epochs", 1)),
        "learning_rate": float(config.get("learning_rate", 2e-4)),
        "lora_r": int(config.get("lora_r", 8)),
        "lora_alpha": int(config.get("lora_alpha", 16)),
        "lora_dropout": float(config.get("lora_dropout", 0.05)),
        "max_steps": int(config.get("max_steps", 24)),
        "max_train_samples": int(config.get("max_train_samples", 49)),
        "max_eval_samples": int(config.get("max_eval_samples", 8)),
        "seed": int(config.get("seed", 2103)),
        "dataset_manifest_path": str(config.get("dataset_manifest_path", "data/manifests/dataset_manifest_v1.json")),
        "dataset_split_path": str(config.get("dataset_split_path", "data/manifests/dataset_splits_v1.json")),
        "hf_token": str(config.get("hf_token") or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or ""),
    }


def _project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return REMOTE_PROJECT_ROOT / candidate


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_samples(config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    manifest = _load_json(_project_path(config["dataset_manifest_path"]))
    by_id = {sample["sample_id"]: sample for sample in manifest.get("samples", [])}
    split_doc = _load_json(_project_path(config["dataset_split_path"]))
    split_ids = split_doc.get("splits", {})
    return {
        split: [by_id[sample_id] for sample_id in sample_ids if sample_id in by_id]
        for split, sample_ids in split_ids.items()
    }


def _panel_image_path(sample: Dict[str, Any]) -> Path:
    panel_path = _project_path(sample["panel_artifact_path"])
    panel = _load_json(panel_path)
    slots = panel.get("slots", {})
    image_ref = slots.get("current_rgb") or slots.get("spectral_composite") or slots.get("mapbox_context")
    if not image_ref:
        raise ValueError(f"panel has no usable image slot: {panel_path}")
    return _project_path(image_ref)


def _prompt_text(sample: Dict[str, Any]) -> tuple[str, str]:
    panel = _load_json(_project_path(sample["panel_artifact_path"]))
    metadata_block = panel.get("metadata_text") or (
        f"site_id={sample['site_id']}; sample_id={sample['sample_id']}; "
        f"source_ref={sample.get('provenance', {}).get('source_ref', 'unknown')}"
    )
    system_prompt = (
        "You are LandfillSentry Incident Assistant. Return JSON only. "
        "Do not include markdown or narrative. Use enum values exactly as specified."
    )
    user_prompt = (
        "Interpret the evidence panel and produce an incident object using this schema: "
        "{incident_id, site_id, job_id, analysis_time, plume_likely, confidence, bbox_norm, "
        "likely_source_zone, persistence_score, priority_tier, severity_tier, review_status, "
        "feedback_status, evidence_summary, recommended_followup, model_version}. "
        f"Metadata: {metadata_block}."
    )
    return system_prompt, user_prompt


def _target_json(sample: Dict[str, Any], model_id: str) -> str:
    annotation = sample["annotation"]
    priority = str(annotation.get("priority_tier", "medium"))
    severity = "critical" if priority == "urgent" else "high" if priority == "high" else "medium" if priority == "medium" else "low"
    payload = {
        "incident_id": f"train_{sample['sample_id']}",
        "site_id": sample["site_id"],
        "job_id": sample["sample_id"],
        "analysis_time": sample.get("provenance", {}).get("created_at", _utc_now()),
        "plume_likely": bool(annotation.get("plume_likely", True)),
        "confidence": 0.85 if annotation.get("plume_likely", True) else 0.35,
        "bbox_norm": annotation.get("bbox_norm", [0.2, 0.2, 0.5, 0.5]),
        "likely_source_zone": annotation.get("likely_source_zone", "perimeter_or_unknown"),
        "persistence_score": 0.74 if annotation.get("plume_likely", True) else 0.18,
        "priority_tier": priority,
        "severity_tier": severity,
        "review_status": "needs_review",
        "feedback_status": "unreviewed",
        "evidence_summary": f"Domain-labeled landfill sample {sample['sample_id']} indicates {priority} review priority.",
        "recommended_followup": "Review the evidence panel, confirm source zone, and compare with recent temporal context.",
        "model_version": model_id,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _conversation(sample: Dict[str, Any], image: Any, model_id: str, include_answer: bool) -> List[Dict[str, Any]]:
    system_prompt, user_prompt = _prompt_text(sample)
    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": user_prompt},
            ],
        },
    ]
    if include_answer:
        messages.append({"role": "assistant", "content": [{"type": "text", "text": _target_json(sample, model_id)}]})
    return messages


def _move_to_device(batch: Dict[str, Any], device: str) -> Dict[str, Any]:
    moved: Dict[str, Any] = {}
    for key, value in batch.items():
        moved[key] = value.to(device) if hasattr(value, "to") else value
    return moved


def _encode_sample(processor: Any, sample: Dict[str, Any], model_id: str) -> Dict[str, Any]:
    from PIL import Image

    image_path = _panel_image_path(sample)
    image = Image.open(image_path).convert("RGB")
    prompt_messages = _conversation(sample, image, model_id, include_answer=False)
    full_messages = _conversation(sample, image, model_id, include_answer=True)
    full = processor.apply_chat_template(
        full_messages,
        add_generation_prompt=False,
        return_tensors="pt",
        return_dict=True,
        tokenize=True,
    )
    prompt = processor.apply_chat_template(
        prompt_messages,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
        tokenize=True,
    )
    labels = full["input_ids"].clone()
    prompt_len = min(prompt["input_ids"].shape[1], labels.shape[1] - 1)
    labels[:, :prompt_len] = -100
    full["labels"] = labels
    return full


def _linear_target_modules(model: Any) -> List[str]:
    import torch

    preferred = {"q_proj", "k_proj", "v_proj", "o_proj"}
    found = set()
    fallback = set()
    for name, module in model.named_modules():
        if not isinstance(module, torch.nn.Linear):
            continue
        short = name.rsplit(".", 1)[-1]
        if short in preferred:
            found.add(short)
        elif len(fallback) < 8:
            fallback.add(short)
    return sorted(found or fallback)


def _average_loss(
    model: Any,
    processor: Any,
    samples: Iterable[Dict[str, Any]],
    model_id: str,
    device: str,
) -> float | None:
    import torch

    losses: List[float] = []
    model.eval()
    with torch.no_grad():
        for sample in samples:
            batch = _move_to_device(_encode_sample(processor, sample, model_id), device)
            loss = model(**batch).loss
            losses.append(float(loss.detach().cpu()))
    model.train()
    if not losses:
        return None
    return sum(losses) / len(losses)


def _archive_dir_b64(path: Path) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(path.rglob("*")):
            if item.is_file():
                zf.write(item, item.relative_to(path).as_posix())
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@app.function(image=image, gpu=_gpu_from_env(), timeout=60 * 10)
def gpu_smoke() -> Dict[str, Any]:
    import torch

    cuda_available = bool(torch.cuda.is_available())
    return {
        "cuda_available": cuda_available,
        "device_name": torch.cuda.get_device_name(0) if cuda_available else "cpu",
        "torch_version": torch.__version__,
    }


@app.function(
    image=image,
    gpu=_gpu_from_env(),
    timeout=60 * 120,
    volumes={str(ARTIFACT_ROOT): volume},
    secrets=hf_secrets,
)
def run_lora_training(config: Dict[str, Any]) -> Dict[str, Any]:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoProcessor

    cfg = _normalize_config(config)
    random.seed(cfg["seed"])
    torch.manual_seed(cfg["seed"])
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(cfg["seed"])

    samples_by_split = _load_samples(cfg)
    train_samples = list(samples_by_split.get("train", []))[: cfg["max_train_samples"]]
    eval_samples = (list(samples_by_split.get("validation", [])) or list(samples_by_split.get("test", [])))[: cfg["max_eval_samples"]]
    if not train_samples:
        raise RuntimeError("no train samples found in frozen split manifest")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    token = cfg["hf_token"] or None
    load_kwargs: Dict[str, Any] = {
        "revision": cfg["revision"],
        "trust_remote_code": True,
        "dtype": dtype,
    }
    processor_kwargs: Dict[str, Any] = {"revision": cfg["revision"], "trust_remote_code": True}
    if token:
        load_kwargs["token"] = token
        processor_kwargs["token"] = token

    processor = AutoProcessor.from_pretrained(cfg["model_id"], **processor_kwargs)
    model = AutoModelForImageTextToText.from_pretrained(cfg["model_id"], **load_kwargs)
    model.to(device)
    model.config.use_cache = False

    target_modules = _linear_target_modules(model)
    peft_config = LoraConfig(
        r=cfg["lora_r"],
        lora_alpha=cfg["lora_alpha"],
        target_modules=target_modules,
        lora_dropout=cfg["lora_dropout"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, peft_config)
    model.train()

    eval_loss_before = _average_loss(model, processor, eval_samples, cfg["model_id"], device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"])
    train_losses: List[float] = []
    completed_steps = 0

    for _epoch in range(cfg["epochs"]):
        for sample in train_samples:
            if cfg["max_steps"] > 0 and completed_steps >= cfg["max_steps"]:
                break
            optimizer.zero_grad(set_to_none=True)
            batch = _move_to_device(_encode_sample(processor, sample, cfg["model_id"]), device)
            loss = model(**batch).loss
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.detach().cpu()))
            completed_steps += 1
        if cfg["max_steps"] > 0 and completed_steps >= cfg["max_steps"]:
            break

    eval_loss_after = _average_loss(model, processor, eval_samples, cfg["model_id"], device)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"lora_run_{timestamp}"
    run_dir = ARTIFACT_ROOT / run_id
    checkpoint_dir = run_dir / "checkpoint-lora-v1"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(checkpoint_dir)
    processor.save_pretrained(checkpoint_dir / "processor")

    manifest = _load_json(_project_path(cfg["dataset_manifest_path"]))
    metadata = {
        "adapter_status": "fine_tuned",
        "base_model": cfg["model_id"],
        "base_revision": cfg["revision"],
        "completed_steps": completed_steps,
        "created_at": _utc_now(),
        "dataset_manifest_checksum": manifest.get("manifest_checksum"),
        "dataset_sample_count": manifest.get("sample_count"),
        "eval_loss_after": eval_loss_after,
        "eval_loss_before": eval_loss_before,
        "eval_loss_delta": None
        if eval_loss_before is None or eval_loss_after is None
        else eval_loss_before - eval_loss_after,
        "lora_alpha": cfg["lora_alpha"],
        "lora_dropout": cfg["lora_dropout"],
        "lora_r": cfg["lora_r"],
        "max_steps": cfg["max_steps"],
        "target_modules": target_modules,
        "train_loss_mean": None if not train_losses else sum(train_losses) / len(train_losses),
        "train_sample_count_used": len(train_samples),
        "validation_sample_count_used": len(eval_samples),
    }
    (checkpoint_dir / "landfillsentry_adapter_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (checkpoint_dir / "README.md").write_text(
        "# LandfillSentry LFM2-VL LoRA Adapter\n\n"
        "PEFT LoRA adapter trained on the frozen LandfillSentry satellite evidence-panel dataset.\n\n"
        f"- Base model: `{cfg['model_id']}@{cfg['revision']}`\n"
        f"- Completed optimizer steps: `{completed_steps}`\n"
        f"- Validation loss before: `{eval_loss_before}`\n"
        f"- Validation loss after: `{eval_loss_after}`\n"
        f"- Dataset checksum: `{manifest.get('manifest_checksum')}`\n",
        encoding="utf-8",
    )

    run_manifest = {
        "adapter_artifact_ref": f"modal-volume://{VOLUME_NAME}/{run_id}/checkpoint-lora-v1",
        "artifact_volume": VOLUME_NAME,
        "checkpoint_dir": str(checkpoint_dir),
        "config": {k: v for k, v in cfg.items() if k != "hf_token"},
        "created_at": _utc_now(),
        "manifest_path": str(run_dir / "run_manifest.json"),
        "metrics": metadata,
        "model_id": cfg["model_id"],
        "revision": cfg["revision"],
        "run_id": run_id,
        "status": "ok",
        "training_mode": "peft_lora_supervised",
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True), encoding="utf-8")
    volume.commit()

    return {
        **run_manifest,
        "adapter_archive_b64": _archive_dir_b64(checkpoint_dir),
    }


def _extract_adapter_archive(result: Dict[str, Any], output_root: Path) -> Path | None:
    archive_b64 = result.pop("adapter_archive_b64", None)
    if not archive_b64:
        return None
    run_id = str(result.get("run_id", "lora_run_latest"))
    out_dir = output_root / run_id / "checkpoint-lora-v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(archive_b64.encode("ascii"))
    with zipfile.ZipFile(io.BytesIO(data), mode="r") as zf:
        zf.extractall(out_dir)
    return out_dir


@app.local_entrypoint()
def main(config_json: str = "", output_dir: str = "data/processed/hf_adapter_trained") -> None:
    config = json.loads(config_json) if config_json else {}
    smoke = gpu_smoke.remote()
    print("GPU smoke:", smoke)
    result = run_lora_training.remote(config)
    local_adapter_dir = _extract_adapter_archive(result, Path(output_dir))
    if local_adapter_dir is not None:
        result["local_adapter_dir"] = str(local_adapter_dir)
        print("LOCAL_ADAPTER_DIR:", local_adapter_dir)
    print("Training result:", result)
    print("TRAINING_RESULT_JSON:", json.dumps(result, sort_keys=True))
