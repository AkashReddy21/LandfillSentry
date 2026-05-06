# Benchmark Summary For Submission

Date: May 5, 2026

## Goal

Show measurable improvement and reliability across:
- base model behavior,
- tuned/checkpoint path,
- strict live runtime behavior.

## Deployment And Inference Path

Recommended judge deployment:
- API/UI: Docker via `docker-compose.landfillsentry.yml`
- imagery: DPhi SimSat live API
- inference: Hugging Face Transformers + PEFT adapter (`akashreddy2103/landfill`)

Preflight:
```bash
python scripts/export_openapi.py
python scripts/judge_preflight.py
```

Public fine-tuned weight claim requires:
- `HF_ADAPTER_ID` set to a public Hugging Face PEFT adapter repo,
- `HF_ADAPTER_REVISION` set to the judged revision,
- model card documenting dataset, splits, methodology, and limitations.

Current public adapter:
- repo: `akashreddy2103/landfill`
- base: `LiquidAI/LFM2.5-VL-450M@main`
- run id: `lora_run_20260504T181913Z`
- training mode: `peft_lora_supervised`
- completed optimizer steps: `24`
- validation loss: `2.4106` before, `1.3696` after

## Reproducible Commands

1. Start live judge mode and run smoke checks:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_judge_mode.ps1 -RestartApi
```

2. Smoke validation only:
```bash
python scripts/live_smoke.py --api-base-url http://127.0.0.1:8000 --simsat-base-url http://127.0.0.1:9005
```

3. Probe/import/collect global live scans:
```bash
python scripts/collect_global_live_scans.py --probe-only
python scripts/collect_global_live_scans.py --target-samples 180 --repeats-per-site 8
```

4. Export labels for manual correction:
```bash
python scripts/export_label_review_queue.py
```

Copy reviewed rows to `data/labels/manual_label_corrections.csv`, then rebuild/train.

5. Save the latest successful live scan artifact:
```bash
python scripts/save_live_scan_artifact.py --api-base-url http://127.0.0.1:8000 --scan-id scan_083
```

6. Modal fine-tune:
```bash
python scripts/train_lora.py
```

7. Phase 7 benchmark harness:
```bash
python scripts/benchmark_models.py
```

## Latest Live Smoke Proof

Generated proof:
- `docs/latest_live_smoke_proof.md`
- `data/processed/live_smoke_proof.json`

Result from the latest run:
- status: `PASS`
- site: `LF_REAL_007`
- scan: `scan_083`
- incident: `inc_083`
- inference mode: `live`
- previews present: `current_rgb`, `spectral_composite`, `temporal_diff`, `mapbox_context`

The same scan is archived at:
- `docs/latest_live_scan_artifact.md`
- `data/processed/judge_live_artifacts/scan_083.json`

## Modal LoRA Run

`python scripts/train_lora.py` completed successfully on Modal after the global expansion:
- GPU smoke: CUDA available
- dataset source: `live_scans`
- sample count: `78`
- unique sites: `30`
- global non-Europe sites with successful live scans: `20`
- regions represented: Europe/legacy, North America, Latin America, Asia, Africa, Middle East
- site-based splits: train `49`, validation `20`, test `9`
- manifest checksum: `a6738e1af7d89f6fbd0d567c89759f6103beaa81553074a3ad520c6810988b01`
- run id: `lora_run_20260504T181913Z`
- adapter ref: `modal-volume://landfillsentry-model-artifacts/lora_run_20260504T181913Z/checkpoint-lora-v1`
- public adapter repo: `akashreddy2103/landfill`
- training mode: `peft_lora_supervised`
- completed optimizer steps: `24`
- LoRA rank/alpha/dropout: `8` / `16` / `0.05`
- validation loss before/after: `2.410613179206848` -> `1.3696070164442062`
- validation-loss delta: `+1.041006162762642`
- checkpoint record: `data/manifests/tuned_checkpoint_v1.json`

## Metrics Table

Populated from `data/manifests/phase7_evaluation_report.json`.

| Metric | Base Model | Tuned Path | Delta |
|---|---:|---:|---:|
| JSON valid rate | 1.00 | 1.00 | +0.00 |
| Incident F1 | 0.50 | 1.00 | +0.50 |
| Zone accuracy | 0.33 | 1.00 | +0.67 |
| BBox IoU | 0.1966 | 1.00 | +0.8034 |
| Human usefulness score | 0.7333 | 0.9733 | +0.2400 |
| Null-scene false positive rate (lower is better) | 1.00 | 0.00 | -1.00 |

Interpretation: this is a small, reproducible domain-adaptation fixture proxy. The base row is a schema-valid generic LFM2.5-VL projection without landfill-domain zone priors or null-scene caution. The tuned path uses the Phase 6 public adapter record, landfill-domain labels, source-zone priors, and strict output validation. The Modal training run also reports a direct validation-loss improvement on held-out LandfillSentry validation samples.

## Failure-Handling Table

| Failure Case | Expected Behavior | Verified By |
|---|---|---|
| SimSat unavailable | Fast fail with actionable error | `live_smoke.py` + `/sites/{id}/scan` |
| Invalid model JSON | Retry then fail if strict live mode | output validation + strict config |
| Fallback confusion | Do not present fallback as live | `REQUIRE_LIVE_RESULTS=true`, `INFERENCE_ALLOW_FALLBACK=false` |
| UI provenance ambiguity | Show source chain + timestamps | `/ops` Data Source panel |
| Smoke proof missing | Save proof automatically on smoke run | `docs/latest_live_smoke_proof.md` |

## Current Training Data Notes

- Primary labeled file: `data/labels/phase6_samples_live_v1.jsonl`
- Manual correction queue: `data/labels/manual_label_review_queue.csv`
- Optional manual corrections input: `data/labels/manual_label_corrections.csv`
- Global site seed list: `assets/demo_sites/global_sites.26rows.csv`
- Global API probe report: `docs/global_live_api_probe_report.md`
- Latest global collection batch report: `docs/global_live_scan_collection_report.md`
- Expanded dataset summary: `docs/global_live_dataset_summary.md`
- Frozen manifests:
  - `data/manifests/dataset_manifest_v1.json`
  - `data/manifests/dataset_splits_v1.json`
- Checkpoint metadata:
  - `data/manifests/tuned_checkpoint_v1.json`

## Known Limitations

- Metrics are a measured lift on a small domain-adaptation fixture proxy, not a broad production-quality public benchmark.
- Some live coordinates can intermittently return unusable SimSat imagery.
- Judge mode intentionally fails fast instead of silently degrading to cached/mock output.
