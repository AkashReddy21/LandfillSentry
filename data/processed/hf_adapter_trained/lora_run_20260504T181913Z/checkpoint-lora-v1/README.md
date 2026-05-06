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

# LandfillSentry LFM2.5-VL LoRA Adapter

This repository contains the PEFT LoRA adapter used by LandfillSentry Ops, a hackathon project for landfill methane/plume incident triage.

LandfillSentry combines DPhi SimSat satellite imagery, Mapbox context, and LFM2.5-VL reasoning to help operators decide which landfill site needs inspection first and why. The adapter is loaded on top of `LiquidAI/LFM2.5-VL-450M` inside the LandfillSentry FastAPI runtime.

## What It Is Used For

Use this adapter for the LandfillSentry incident-triage workflow:

- read a satellite evidence panel for a landfill site,
- reason over current Sentinel imagery, historical Sentinel context, and Mapbox context,
- produce structured incident evidence for methane/plume triage,
- support likely source-zone classification,
- support priority/severity scoring,
- support normalized plume or source bounding boxes,
- support operator review and exportable evidence packs.

This adapter is not a general-purpose methane detector. It is a small domain-adaptation adapter intended for the LandfillSentry demo/runtime path.

## Model Details

- Base model: `LiquidAI/LFM2.5-VL-450M`
- Adapter type: PEFT LoRA
- Public adapter repo: `akashreddy2103/landfill`
- Runtime adapter variable: `HF_ADAPTER_ID=akashreddy2103/landfill`
- Inference engine: Hugging Face Transformers
- Adapter loader: PEFT
- Latest run id: `lora_run_20260504T181913Z`

## Training Dataset Summary

This adapter was trained for the LandfillSentry hackathon submission using live-scan landfill samples.

- Dataset source: live_scans
- Samples: 78 live-scan samples
- Unique sites: 30
- Global non-Europe successful sites: 20
- Regions: Europe/legacy, North America, Latin America, Asia, Africa, Middle East
- Site-based split: train 49 / validation 20 / test 9
- Training platform: Modal GPU
- GPU: Tesla T4

## Runtime Integration

LandfillSentry loads this adapter with Hugging Face Transformers and PEFT.

- Runtime adapter variable: `HF_ADAPTER_ID=akashreddy2103/landfill`
- Runtime path: `apps/api/services/inference_service.py`
- Expected judge mode: `INFERENCE_MODE=live`
- Strict fallback policy: `INFERENCE_ALLOW_FALLBACK=false`

The app uses DPhi SimSat as the live imagery provider and records provenance for each evidence pack. In strict judge mode, unavailable live imagery or live inference fails clearly instead of presenting mock output as live.

## Expected Inputs

The adapter is intended to be used with the same prompt/evidence-panel contract produced by LandfillSentry:

- current Sentinel image from DPhi SimSat,
- historical Sentinel image from DPhi SimSat,
- Mapbox context image,
- site metadata and candidate priors,
- prompt contract requesting structured incident JSON.

## Expected Outputs

The application validates model output into the LandfillSentry incident contract, including fields such as:

- incident summary,
- confidence,
- priority tier,
- severity tier,
- likely source zone,
- persistence score,
- normalized bounding box,
- evidence notes and review metadata.

## Training Summary

- Run id: `lora_run_20260504T181913Z`
- Training mode: `peft_lora_supervised`
- Completed optimizer steps: `24`
- LoRA rank/alpha/dropout: `8` / `16` / `0.05`
- Validation loss before: `2.410613179206848`
- Validation loss after: `1.3696070164442062`
- Dataset checksum: `a6738e1af7d89f6fbd0d567c89759f6103beaa81553074a3ad520c6810988b01`

## Project And Documentation

- GitHub project: `https://github.com/AkashReddy21/LandfillSentry`
- Judge brief: `docs/judge_submission_brief.md`
- Deployment runbook: `docs/judge_deployment_runbook.md`
- Fine-tuning methodology: `docs/fine_tuning_methodology.md`
- Benchmark summary: `docs/benchmark_summary_for_submission.md`

## Limitations

- The dataset is small and partly weak-labeled from live scans plus review artifacts.
- The benchmark is a domain-adaptation fixture proxy, not a broad production methane benchmark.
- Use the adapter inside the LandfillSentry evidence-panel and validation pipeline for best results.
- Do not present this adapter as a standalone regulatory methane-monitoring system.
