---
library_name: peft
base_model: LiquidAI/LFM2.5-VL-450M
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

Base model: `LiquidAI/LFM2.5-VL-450M@main`
