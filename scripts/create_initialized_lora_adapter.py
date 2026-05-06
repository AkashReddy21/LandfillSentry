"""Create a loadable PEFT LoRA adapter package for the configured base VLM.

This creates initialized LoRA weights, not trained weights. Use it to make the
runtime adapter path loadable while keeping documentation honest about training
status. Real fine-tuning should replace this adapter_model.safetensors.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _resolve_dtype(torch_module, selected: str):
    value = (selected or "").lower()
    if value in {"float16", "fp16"} and torch_module.cuda.is_available():
        return torch_module.float16
    if value == "bfloat16" and torch_module.cuda.is_available():
        return torch_module.bfloat16
    return torch_module.float32


def _target_module_suffixes(model) -> list[str]:
    import torch

    preferred = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    linear_suffixes = set()
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.Linear):
            linear_suffixes.add(name.rsplit(".", 1)[-1])
    selected = [name for name in preferred if name in linear_suffixes]
    if selected:
        return selected
    fallback = sorted(linear_suffixes)
    if not fallback:
        raise RuntimeError("No torch.nn.Linear modules found for LoRA targets.")
    return fallback[:24]


def create_adapter(output_dir: Path, model_id: str, revision: str, dtype: str) -> None:
    import torch
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoProcessor

    token = os.getenv("HF_TOKEN", "").strip() or os.getenv("HUGGINGFACE_TOKEN", "").strip() or None
    model_kwargs = {
        "revision": revision,
        "token": token,
        "trust_remote_code": os.getenv("HF_TRUST_REMOTE_CODE", "false").lower() == "true",
        "local_files_only": os.getenv("HF_LOCAL_FILES_ONLY", "false").lower() == "true",
        "low_cpu_mem_usage": False,
        "dtype": _resolve_dtype(torch, dtype),
    }
    if torch.cuda.is_available():
        model_kwargs["device_map"] = os.getenv("HF_DEVICE_MAP", "auto")

    print(f"Loading base model: {model_id}@{revision}")
    model = AutoModelForImageTextToText.from_pretrained(model_id, **model_kwargs)
    processor = AutoProcessor.from_pretrained(
        model_id,
        revision=revision,
        token=token,
        trust_remote_code=model_kwargs["trust_remote_code"],
        local_files_only=model_kwargs["local_files_only"],
    )

    targets = _target_module_suffixes(model)
    print("LoRA target modules:", targets)
    config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=targets,
        inference_mode=False,
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters()

    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    try:
        processor.save_pretrained(output_dir / "processor")
    except Exception:
        pass

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_model": model_id,
        "base_revision": revision,
        "adapter_status": "initialized_not_fine_tuned",
        "note": "Loadable PEFT LoRA adapter initialized from base model. Replace with trained adapter weights for fine-tuned claims.",
        "target_modules": targets,
    }
    (output_dir / "landfillsentry_adapter_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    readme = output_dir / "README.md"
    readme.write_text(
        f"""---
library_name: peft
base_model: {model_id}
tags:
- peft
- lora
- vision-language
- satellite-imagery
- landfill
---

# LandfillSentry LoRA Adapter

Status: initialized and loadable, not yet fine-tuned.

This repository contains PEFT adapter files for the LandfillSentry runtime path.
The current adapter weights are initialized LoRA weights. Replace
`adapter_model.safetensors` with trained LoRA weights before claiming public
fine-tuned model performance.

Base model: `{model_id}@{revision}`
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create initialized PEFT adapter files for runtime loading.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "data" / "processed" / "hf_adapter_initialized"))
    parser.add_argument("--model-id", default="")
    parser.add_argument("--revision", default="")
    parser.add_argument("--dtype", default="")
    args = parser.parse_args()

    _load_env_file(PROJECT_ROOT / ".env.local")
    model_id = args.model_id or os.getenv("HF_MODEL_ID", "LiquidAI/LFM2.5-VL-450M")
    revision = args.revision or os.getenv("HF_MODEL_REVISION", "main")
    dtype = args.dtype or os.getenv("HF_DTYPE", "float32")
    create_adapter(Path(args.output_dir), model_id=model_id, revision=revision, dtype=dtype)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
