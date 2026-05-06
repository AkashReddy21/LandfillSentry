# Global Live Dataset Summary

Date: April 28, 2026

## What Changed

The Phase 6 training dataset is no longer Europe-only. A global site seed file was added at:

- `assets/demo_sites/global_sites.26rows.csv`

The collection script probes DPhi SimSat first, then only scans sites whose current Sentinel, historical Sentinel, and Mapbox context endpoints are reachable:

```bash
python scripts/collect_global_live_scans.py --probe-only
python scripts/collect_global_live_scans.py --target-samples 180 --repeats-per-site 8
```

Latest all-site probe result:

- `26 / 26` global candidate sites passed the DPhi SimSat endpoint probe.
- Report: `docs/global_live_api_probe_report.md`

## Current Expanded Dataset

After the first two global collection batches:

- total live-scan samples: `78`
- total unique sites: `30`
- global non-Europe successful sites: `20`
- split counts:
  - train: `49`
  - validation: `20`
  - test: `9`

Regions represented:

| Region | Samples |
|---|---:|
| Europe/legacy | 58 |
| North America | 5 |
| Latin America | 5 |
| Asia | 6 |
| Africa | 3 |
| Middle East | 1 |

The larger target remains `150-300+` live scans. The pipeline is now ready for that run; at the current live scan speed it should be treated as a longer overnight collection job.

## Manual Label Correction

Export review queue:

```bash
python scripts/export_label_review_queue.py
```

Then copy corrected rows into:

- `data/labels/manual_label_corrections.csv`

Template:

- `data/labels/manual_label_corrections.template.csv`

When `scripts/build_phase6_dataset.py` runs, it applies those manual corrections before writing:

- `data/labels/phase6_samples_live_v1.jsonl`
- `data/manifests/dataset_manifest_v1.json`
- `data/manifests/dataset_splits_v1.json`

## Latest Modal Run

- run id: `lora_run_20260428T165129Z`
- adapter ref: `modal-volume://landfillsentry-model-artifacts/lora_run_20260428T165129Z/checkpoint-lora-v1`
- checkpoint record: `data/manifests/tuned_checkpoint_v1.json`
