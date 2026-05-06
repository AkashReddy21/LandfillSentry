# Fine-Tuning Methodology And Public Weights

## Current Status

LandfillSentry now has a real PEFT LoRA adapter trained on the frozen satellite evidence-panel dataset and published to Hugging Face.

Public adapter repo: `akashreddy2103/landfill`

Latest run:

- run id: `lora_run_20260504T181913Z`
- base model: `LiquidAI/LFM2.5-VL-450M@main`
- training mode: `peft_lora_supervised`
- completed optimizer steps: `24`
- LoRA rank/alpha/dropout: `8` / `16` / `0.05`
- target modules: `k_proj`, `q_proj`, `v_proj`
- validation loss before: `2.410613179206848`
- validation loss after: `1.3696070164442062`
- measured validation-loss delta: `+1.041006162762642`

## Implemented Artifacts

- Dataset builder: `scripts/build_phase6_dataset.py`
- Modal training entrypoint: `scripts/train_lora.py`
- Modal app: `ml/training/modal_lora_train.py`
- Adapter artifact helpers: `ml/training/lora_artifacts.py`
- Runtime adapter loading: `apps/api/services/inference_service.py`
- Evaluation harness: `scripts/benchmark_models.py`
- Dataset manifest: `data/manifests/dataset_manifest_v1.json`
- Split manifest: `data/manifests/dataset_splits_v1.json`
- Benchmark report: `data/manifests/phase7_evaluation_report.json`

## Dataset

The frozen dataset manifest contains 78 live-scan-derived samples with site-based splits:

- train: 49
- validation: 20
- test: 9

Inputs combine current Sentinel imagery, historical Sentinel context, Mapbox context, generated candidates, panel metadata, and operator-review labels/corrections where available.

Manifest checksum: `a6738e1af7d89f6fbd0d567c89759f6103beaa81553074a3ad520c6810988b01`

## Reproduce Training

1. Build/freeze the dataset:

```powershell
.\.venv\Scripts\python.exe scripts\build_phase6_dataset.py
```

2. Run Modal LoRA training:

```powershell
.\.venv\Scripts\python.exe scripts\train_lora.py
```

Default bounded config trains for up to 24 optimizer steps. Override with environment variables such as `LORA_MAX_STEPS`, `LORA_R`, `LORA_ALPHA`, and `LORA_LEARNING_RATE`.

3. Publish only the PEFT adapter folder:

```powershell
.\.venv\Scripts\python.exe scripts\upload_hf_adapter.py --adapter-dir data\processed\hf_adapter_trained\lora_run_20260504T181913Z\checkpoint-lora-v1 --repo-id akashreddy2103/landfill
```

Do not run `upload_folder(folder_path=".")`; that can leak `.env.local`, logs, caches, and non-model artifacts.
4. Set `.env.local`:

```env
HF_ADAPTER_ID=akashreddy2103/landfill
HF_ADAPTER_REVISION=main
HF_LOCAL_FILES_ONLY=false
```

5. Run:

```powershell
.\.venv\Scripts\python.exe scripts\judge_preflight.py --strict-public-weights
.\.venv\Scripts\python.exe scripts\benchmark_models.py
```

6. Update `docs/benchmark_summary_for_submission.md` with the public adapter ID and final base-vs-adapter metrics.

## Current Benchmark Interpretation

The current public adapter shows measured validation-loss improvement on the frozen LandfillSentry validation subset. The Phase 7 table remains a small domain-adaptation fixture proxy and should not be presented as a broad production-quality benchmark.
