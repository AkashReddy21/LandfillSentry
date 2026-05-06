---
library_name: peft
base_model: LiquidAI/LFM2.5-VL-450M
tags:
- peft
- lora
- vision-language
- satellite-imagery
- landfill
license: apache-2.0
---

# LandfillSentry LFM2-VL LoRA Adapter

PEFT LoRA adapter trained on the frozen LandfillSentry satellite evidence-panel dataset.

- Base model: `LiquidAI/LFM2.5-VL-450M@main`
- Run id: `lora_run_20260504T181913Z`
- Training mode: `peft_lora_supervised`
- Completed optimizer steps: `24`
- LoRA rank/alpha/dropout: `8` / `16` / `0.05`
- Validation loss before: `2.410613179206848`
- Validation loss after: `1.3696070164442062`
- Dataset checksum: `a6738e1af7d89f6fbd0d567c89759f6103beaa81553074a3ad520c6810988b01`

This is a small, domain-specific adapter trained on live-scan-derived and weak/manual review labels. It is suitable for demonstrating the LandfillSentry training/deployment path, not as a broad production methane-detection benchmark.
