# LandfillSentry Ops

LandfillSentry is an operator-first landfill methane incident triage copilot. It combines live DPhi SimSat satellite imagery, Mapbox context, and LFM2.5-VL reasoning to help an operations team decide which landfill site needs inspection first, why it was flagged, and what evidence should be exported for review.

## Hackathon Submission

One-sentence pitch:

> LandfillSentry turns DPhi SimSat imagery and LFM2.5-VL reasoning into a live incident console for landfill methane/plume triage, evidence review, and export.

This repository is prepared for hackathon judging with:

- live DPhi SimSat imagery as the primary satellite source,
- visible imagery provenance in the API and UI,
- strict judge mode that fails clearly instead of presenting mock/fallback output as live,
- a FastAPI-served operator console at `/ops`,
- Hugging Face Transformers + PEFT inference using `LiquidAI/LFM2.5-VL-450M`,
- a public LoRA adapter path: `akashreddy2103/landfill`,
- reproducible smoke checks, live proof artifacts, and benchmark documentation.

## Latest Fine-Tuned Adapter

- Hugging Face adapter: https://huggingface.co/akashreddy2103/landfill
- Base model: `LiquidAI/LFM2.5-VL-450M`
- Training method: PEFT LoRA
- Dataset: 78 live-scan samples
- Unique sites: 30
- Global non-Europe successful sites: 20
- Site-based split: train 49 / validation 20 / test 9
- Modal GPU: Tesla T4
- Latest run ID: `lora_run_20260504T181913Z`
- Validation loss: 2.4106 -> 1.3696

## Judging Criteria Alignment

| Criterion | Evidence |
|---|---|
| Use of satellite imagery | DPhi SimSat is wired as the live imagery provider for Sentinel current, Sentinel historical, and Mapbox context endpoints. Runtime status and evidence metadata include provider, repository, endpoint, timestamp, and cloud-cover provenance. |
| Innovation and problem fit | The workflow focuses on a concrete operational decision: prioritize landfill sites for inspection using satellite evidence, model reasoning, plume overlays, review state, and exportable incident records. |
| Technical implementation | FastAPI backend, SQLite persistence, live imagery adapters, cache-backed evidence, LFM2.5-VL inference, PEFT adapter loading, SSE scan progress, review workflows, export APIs, tests, Docker support, and judge runbooks. |
| Demo and communication | Demo script, architecture brief, live smoke proof, benchmark summary, saved live artifact, and judge deployment runbook are included under `docs/`. |

## What The Demo Shows

1. Open the operator console at `http://127.0.0.1:8000/ops`.
2. Confirm runtime status shows live DPhi SimSat imagery and strict judge mode.
3. Select a watchlist landfill site.
4. Review live Sentinel/Mapbox provenance, evidence panels, model output, plume overlay, confidence, and priority.
5. Trigger a scan when live dependencies are available.
6. Review or assign the incident.
7. Export the evidence pack as Markdown or JSON.

Strict judge behavior is intentional: if DPhi SimSat, Mapbox, or live inference is unavailable, scans fail with actionable errors instead of silently substituting mock output.

## Repository Layout

```text
apps/api/       FastAPI routes, schemas, runtime wiring, services, SQLite repository
apps/web/       FastAPI-served operator console at /ops
assets/         Demo-site matrices and static supporting assets
data/           Labels, manifests, processed proof artifacts, and model artifacts
docs/           Judge brief, deployment runbook, architecture, demo script, benchmarks
external/SimSat DPhi SimSat submodule used as the live imagery backend
ml/             Evaluation and LoRA training helpers
scripts/        Smoke tests, preflight, dataset build, inference, training, upload helpers
tests/          Contract, integration, inference, training, UI workflow, and read API tests
```

## Clone

This repo uses DPhi SimSat as a submodule:

```bash
git clone --recurse-submodules https://github.com/AkashReddy21/LandfillSentry.git
cd LandfillSentry
```

If already cloned without submodules:

```bash
git submodule update --init --recursive
```

## Required Runtime Credentials

Create `.env.local` from `.env.example` and fill real credentials. Do not commit `.env.local`.

```env
SIMSAT_MODE=live
MAPBOX_MODE=live
SIMSAT_BASE_URL=http://localhost:9005
SIMSAT_USE_FOR_MAPBOX=true
MAPBOX_TOKEN=...

INFERENCE_MODE=live
REQUIRE_LIVE_RESULTS=true
INFERENCE_ALLOW_FALLBACK=false
HF_TOKEN=...
HF_MODEL_ID=LiquidAI/LFM2.5-VL-450M
HF_MODEL_REVISION=main
HF_ADAPTER_ID=akashreddy2103/landfill
HF_ADAPTER_REVISION=main
HF_LOCAL_FILES_ONLY=false
```

Use `HF_LOCAL_FILES_ONLY=false` on a clean judge machine so the model can download. Use `true` only when the model is already cached.

## Quick Start For Judges

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the strict live judge path:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_judge_mode.ps1 -RestartApi
```

Open:

```text
http://127.0.0.1:8000/ops
```

The startup script uses the project `.venv` when available, starts/checks required services, writes logs under `data/logs/`, and saves smoke proof to:

- `docs/latest_live_smoke_proof.md`
- `data/processed/live_smoke_proof.json`

## Docker Judge Deployment

Run LandfillSentry and SimSat together:

```powershell
docker compose --env-file .env.local -f docker-compose.landfillsentry.yml up --build
```

Open:

- LandfillSentry API/UI: `http://127.0.0.1:8000/ops`
- SimSat API: `http://127.0.0.1:9005`

## SimSat Backend

LandfillSentry uses the hackathon-provided DPhi SimSat API contract as the official live imagery backend.

- SimSat repository: `https://github.com/DPhi-Space/SimSat`
- Local expected API: `http://localhost:9005`
- Included in this repo as submodule: `external/SimSat`

Start SimSat manually when needed:

```powershell
cd external\SimSat
docker compose up --build
```

Implemented imagery endpoints:

- Sentinel current: `GET /data/current/image/sentinel`
- Sentinel historical: `GET /data/image/sentinel`
- Mapbox context: `GET /data/current/image/mapbox`
- Runtime provenance: `GET /runtime/status`

## Core API Routes

- `GET /health`
- `GET /runtime/status`
- `GET /ops/summary`
- `GET /watchlist`
- `GET /watchlist/summary`
- `POST /watchlist/scan`
- `GET /sites/{site_id}/detail`
- `POST /sites/{site_id}/scan`
- `GET /scan-progress/{progress_id}`
- `GET /overlays/plumes`
- `GET /incidents`
- `GET /incidents/{incident_id}`
- `POST /incidents/{incident_id}/review`
- `POST /incidents/{incident_id}/assign`
- `GET /incidents/{incident_id}/export?format=markdown|json`
- `GET /evidence-packs`
- `GET /evidence-packs/{panel_id}`

## Inference And Fine-Tuning

Judge-mode inference tooling:

- Base model: `LiquidAI/LFM2.5-VL-450M`
- Inference engine: Hugging Face Transformers
- Adapter loader: PEFT
- Public adapter: `akashreddy2103/landfill`
- Runtime path: `apps/api/services/inference_service.py`

Latest adapter record:

- Run id: `lora_run_20260504T181913Z`
- Training mode: `peft_lora_supervised`
- Completed optimizer steps: `24`
- Validation loss: `2.410613179206848` to `1.3696070164442062`

Supporting docs:

- `docs/fine_tuning_methodology.md`
- `docs/benchmark_summary_for_submission.md`
- `docs/hf_model_card.md`

## Verification

Run all tests:

```bash
python -m pytest
```

Run live smoke check against running services:

```bash
python scripts/live_smoke.py --api-base-url http://127.0.0.1:8000 --simsat-base-url http://127.0.0.1:9005
```

Run repository preflight:

```bash
python scripts/export_openapi.py
python scripts/judge_preflight.py
python scripts/judge_preflight.py --strict-public-weights
```

## Submission Proof Artifacts

- Judge brief: `docs/judge_submission_brief.md`
- Deployment runbook: `docs/judge_deployment_runbook.md`
- Architecture brief: `docs/architecture_for_judges.md`
- Demo script: `docs/demo_script.md`
- Demo video shot list: `docs/demo_video_shotlist.md`
- Latest live smoke proof: `docs/latest_live_smoke_proof.md`
- Latest live scan artifact: `docs/latest_live_scan_artifact.md`
- Benchmark summary: `docs/benchmark_summary_for_submission.md`
- Saved live scan JSON: `data/processed/judge_live_artifacts/scan_083.json`

## Honest Notes

- Strict live mode is the judged path. Mock mode exists for local/offline tests only.
- Cached evidence can remain visible for operator review, but newly triggered judge-mode scans require live dependencies.
- The public adapter is wired and benchmarked, but larger manually verified labels would be needed before making production-grade model-performance claims.
