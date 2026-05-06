---
library_name: peft
base_model: LiquidAI/LFM2.5-VL-450M
tags:
- peft
- lora
- vision-language
- satellite-imagery
- methane-monitoring
- landfill
license: apache-2.0
---

# LandfillSentry LFM2.5-VL Adapter Package

This Hugging Face model repository is reserved for the LandfillSentry
domain-adapted LFM2.5-VL adapter package.

## Current Status

The LandfillSentry application is deployed and verified with live LFM2.5-VL
inference, DPhi SimSat imagery, strict-live failure behavior, benchmark
artifacts, and a public PEFT LoRA adapter.

Adapter status:

- Public adapter repo: this repository
- Base model: `LiquidAI/LFM2.5-VL-450M`
- Inference engine: Hugging Face Transformers
- Adapter loader: PEFT
- Runtime adapter variable: `HF_ADAPTER_ID=akashreddy2103/landfill`
- Adapter files: `adapter_config.json`, `adapter_model.safetensors`
- Latest run id: `lora_run_20260504T181913Z`
- Training mode: `peft_lora_supervised`
- Completed optimizer steps: `24`
- Validation loss: `2.410613179206848` before, `1.3696070164442062` after

## Included Documentation

- `fine_tuning_methodology.md`
- `benchmark_summary_for_submission.md`
- `judge_deployment_runbook.md`
- `latest_live_smoke_proof.md`
- `latest_live_scan_artifact.md`
- `dataset_manifest_v1.json`
- `dataset_splits_v1.json`
- `phase7_evaluation_report.json`
- `tuned_checkpoint_v1.json`

## Methodology Summary

LandfillSentry builds domain-specific satellite evidence panels from DPhi
SimSat Sentinel imagery, historical Sentinel context, Mapbox context, generated
candidates, and review labels. Evaluation compares a base model path with a
domain-adapted path on a small fixture proxy and reports JSON validity,
incident F1, zone accuracy, bbox IoU, human usefulness, and null-scene false
positive behavior.

## Deployment

The verified judge deployment runs with:

```bash
docker compose --env-file .env.local -f docker-compose.landfillsentry.yml up --build
```

Verified live smoke:

- site: `LF_REAL_007`
- scan: `scan_083`
- incident: `inc_083`
- inference mode: `live`
- inference tooling: Hugging Face Transformers + PEFT

## Limitations

The current benchmark is a small domain-adaptation fixture proxy. The adapter
is real and loadable, but the dataset is still small and partly weak-labeled;
do not present it as a broad production-quality methane model.
