# LandfillSentry Ops

Operator-first landfill methane incident triage copilot.

This repository now includes Phase 1 to Phase 7 implementation artifacts:

- frozen workflow and incident lifecycle
- frozen schema and enum contracts
- first-draft `openapi.json`
- demo-site selection rubric and template
- testing policy, fixture matrix, and integration checklist
- SQLite-backed site registry
- DPhi SimSat + Mapbox imagery adapters (live-first, strict mode supported)
- persistent cache-backed image retrieval paths
- DPhi SimSat API integration path (`/data/current/image/sentinel`, `/data/image/sentinel`, `/data/current/image/mapbox`)
- Phase 3 candidate generation with zone priors and temporal recurrence
- Phase 4 evidence panel builder, prompt contract metadata, and schema-validation loop scaffolding
- Phase 5 base model inference path with Hugging Face model loading and incident persistence/review integration
- Phase 6 dataset manifest freeze, annotation guidance, and Modal GPU PEFT LoRA fine-tuning artifacts
- Phase 7 evaluation harness, baseline comparison table, null-scene report, and reliability injection checks
- Phase 8 watchlist UI, site evidence drill-down, review controls, and incident export flow

## Quick Layout

- `docs/` planning contracts and governance docs
- `apps/api/` backend API scaffold and typed schemas
- `apps/web/` frontend placeholder structure
- `ml/` ML pipeline placeholders
- `data/` data, cache, labels, and manifests structure
- `tests/` schema and contract checks with fixture placeholders
- `assets/demo_sites/` demo-site rubric templates

## Current Status

- Phase 1 outputs are frozen as implementation baselines.
- Phase 2 foundation is implemented with registry, retrieval adapters, and cache flow.
- Phase 3 candidate generation and persistence are implemented.
- Phase 4 deterministic panel and contract-validation layer are implemented.
- Phase 5 base-model inference and incident lifecycle path are implemented.
- Phase 6 dataset build and Modal PEFT LoRA adapter training flow are implemented.
- Phase 7 evaluation and reliability hardening artifacts are implemented.
- Phase 8 watchlist/review/export operator UI and API workflows are implemented.
- Phase 8+ frontend is a production-style FastAPI-served ops console at `/ops`.

## Ops Console (Phase 8)

- Open the operator console at `GET /ops`
- Frontend source:
  - `apps/web/ops.html`
  - `apps/web/ops.css`
  - `apps/web/ops.js`
- The UI is served directly by FastAPI; no separate frontend build step is required for judging.
- Core API routes:
  - `GET /watchlist`
  - `GET /sites/{site_id}/detail`
  - `GET /runtime/status`
  - `GET /ops/summary`
  - `GET /overlays/plumes`
  - `GET /scan-progress/{progress_id}`
  - `POST /sites/{site_id}/dongle-readings`
  - `GET /sites/{site_id}/dongle-readings`
  - `POST /incidents/{incident_id}/review`
  - `GET /incidents/{incident_id}/export?format=markdown|json`

## Judge Quick Start (Strict Live)

Use this path for judging/demo runs where fallback should never be presented as live output.

Judge-facing brief: `docs/judge_submission_brief.md`
Deployment runbook: `docs/judge_deployment_runbook.md`
Fine-tuning methodology: `docs/fine_tuning_methodology.md`

1. Configure `.env.local` with real keys/tokens:
   - `SIMSAT_MODE=live`
   - `MAPBOX_MODE=live`
   - `INFERENCE_MODE=live`
   - `REQUIRE_LIVE_RESULTS=true`
   - `INFERENCE_ALLOW_FALLBACK=false`
   - `SIMSAT_BASE_URL=http://localhost:9005` (or hosted SimSat)
   - `MAPBOX_TOKEN=...`
   - `HF_TOKEN=...`
2. Start everything + run smoke checks:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_judge_mode.ps1
```
This command uses the project `.venv` when available, writes service logs under `data/logs/`, and saves smoke proof to:
  - `docs/latest_live_smoke_proof.md`
  - `data/processed/live_smoke_proof.json`
3. Open UI:
   - `http://127.0.0.1:8000/ops`
4. Validate live behavior:
   - `generation mode` must show `live`
   - `Live Imagery Provenance` panel must show DPhi SimSat Sentinel/Mapbox provenance
   - scans should fail fast with actionable errors if live dependencies are down

Smoke test script can also be run directly:

```bash
python scripts/live_smoke.py --api-base-url http://127.0.0.1:8000 --simsat-base-url http://127.0.0.1:9005
```

Archive the latest successful live scan:

```bash
python scripts/save_live_scan_artifact.py --api-base-url http://127.0.0.1:8000 --scan-id scan_083
```

Preflight the repository before handoff:

```bash
python scripts/export_openapi.py
python scripts/judge_preflight.py
```

Require a public adapter ID for final fine-tuned-weights claims:

```bash
python scripts/judge_preflight.py --strict-public-weights
```

## Docker Judge Deployment

Run the API/UI and SimSat API together:

```powershell
docker compose --env-file .env.local -f docker-compose.landfillsentry.yml up --build
```

Open:

- LandfillSentry: `http://127.0.0.1:8000/ops`
- SimSat API: `http://127.0.0.1:9005`

## SimSat Backend Setup

LandfillSentry uses the hackathon-provided DPhi SimSat API contract as the official live imagery backend:

- Repository: `https://github.com/DPhi-Space/SimSat`
- Expected local API: `http://localhost:9005`

1. Start SimSat locally from `DPhi-Space/SimSat`:
   - `cd external/SimSat`
   - `docker compose up --build`
2. Ensure SimSat API is reachable at `http://localhost:9005`.
3. Set required env values in this project:
   - `SIMSAT_MODE=live`
   - `MAPBOX_MODE=live`
   - `SIMSAT_BASE_URL=http://localhost:9005`
   - `SIMSAT_USE_FOR_MAPBOX=true`
4. In the SimSat project environment, set `MAPBOX_ACCESS_TOKEN` before startup so SimSat can serve Mapbox imagery.

If `SIMSAT_USE_FOR_MAPBOX=false`, this project falls back to direct Mapbox static API calls using `MAPBOX_TOKEN`.

### Endpoint Usage (Implemented)

- Sentinel historical data: `GET /data/image/sentinel`
- Sentinel current site-coordinate data: `GET /data/image/sentinel`
- Mapbox site-coordinate context data: `GET /data/image/mapbox`
- Runtime provenance: `GET /runtime/status` includes the DPhi SimSat repository and required endpoints.

## LFM2.5-VL Usage (Configured)

This project now includes a runnable script based on the official `LiquidAI/LFM2.5-VL-450M` examples:

- image question answering
- visual grounding (bbox JSON output)
- tool-use style response generation

Judge-mode inference tooling:
- inference engine: Hugging Face Transformers
- adapter loader: PEFT
- base model: `LiquidAI/LFM2.5-VL-450M`
- public adapter: `akashreddy2103/landfill`

Run:

```bash
python scripts/run_lfm25_examples.py
```

Notes:

- Set `HF_TOKEN` / `HUGGINGFACE_TOKEN` in `.env.local`.
- `INFERENCE_MODE=live` is the default runtime path.
- Use `INFERENCE_MODE=mock` only for offline/local test runs.
- `INFERENCE_ALLOW_FALLBACK=false` is recommended so failed live inference does not silently produce fallback-style incidents.
- `HF_LOCAL_FILES_ONLY=false` is recommended on a clean judge machine so the model can download; use `true` only when the model is already cached.
- The example script forces live model usage internally for demonstration.

## Modal GPU Setup (Configured)

The project is now wired for Modal GPU orchestration for Phase 6 LoRA runs.

1. Install dependencies:
```bash
python -m pip install -r requirements.txt
```
2. Create Modal token:
```bash
modal token new
```
3. Put credentials in `.env.local`:
```env
MODAL_TOKEN_ID=...
MODAL_TOKEN_SECRET=...
MODAL_GPU=T4
MODAL_APP_NAME=landfillsentry-lora-train
MODAL_ARTIFACT_VOLUME=landfillsentry-model-artifacts
HF_ADAPTER_ID=
HF_ADAPTER_REVISION=main
```
4. Run GPU check + LoRA train job:
```bash
python scripts/train_lora.py
```

Underlying Modal app:
- `ml/training/modal_lora_train.py`
- `scripts/modal_gpu_check.py`
- `ml/training/lora_artifacts.py`

Latest public adapter:

- Hugging Face repo: `akashreddy2103/landfill`
- Run id: `lora_run_20260504T181913Z`
- Training mode: `peft_lora_supervised`
- Completed optimizer steps: `24`
- Validation loss: `2.410613179206848` -> `1.3696070164442062`

Phase 6 dataset freeze inputs/outputs (live-first):

- Preferred labels source (auto-generated from real scans): `data/labels/phase6_samples_live_v1.jsonl`
- Seed fallback labels source (used only when no live scans exist): `data/labels/phase6_samples_v1.jsonl`
- Frozen manifest: `data/manifests/dataset_manifest_v1.json`
- Frozen splits: `data/manifests/dataset_splits_v1.json`
- Checkpoint record: `data/manifests/tuned_checkpoint_v1.json`

Generate dataset artifacts only:

```bash
python scripts/build_phase6_dataset.py
```

Global dataset expansion:

```bash
python scripts/collect_global_live_scans.py --probe-only
python scripts/collect_global_live_scans.py --target-samples 180 --repeats-per-site 8
python scripts/export_label_review_queue.py
python scripts/build_phase6_dataset.py
python scripts/train_lora.py
```

Current expanded dataset summary:
- `docs/global_live_dataset_summary.md`
- `assets/demo_sites/global_sites.26rows.csv`
- `docs/global_live_api_probe_report.md`
- `docs/global_live_scan_collection_report.md`

Current implementation behavior:

- Phase 2/3 scan flow uses current Sentinel + current Mapbox for inference context.
- The same scan flow also fetches Sentinel historical data to support temporal features and fine-tuning data collection.

Dataset roles (as provided by SimSat docs):

- Sentinel-2: high temporal revisit, multispectral, medium spatial resolution.
- Mapbox: high spatial resolution RGB context, static imagery (not time-dependent).
