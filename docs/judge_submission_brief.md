# Judge Submission Brief

Date: May 5, 2026

## One-Sentence Pitch

LandfillSentry turns DPhi SimSat satellite imagery and LFM2.5-VL reasoning into a live operations console for landfill methane/plume incident triage, evidence review, and export.

## Chosen Inference Tooling

LandfillSentry uses Hugging Face Transformers as the LFM2.5-VL inference engine and PEFT for LoRA adapter loading.

- Base model: `LiquidAI/LFM2.5-VL-450M`
- Adapter: `akashreddy2103/landfill`
- Runtime path: `apps/api/services/inference_service.py`
- Strict judge mode: `INFERENCE_MODE=live`, `INFERENCE_ALLOW_FALLBACK=false`

llama.cpp, MLX, and ONNX are not used in this submission because the validated live path is Transformers + PEFT.

## Judging Criteria Alignment

| Criterion | Weight | Evidence in Project | Status |
|---|---:|---|---|
| Use of Satellite Imagery | 10% | DPhi SimSat is the primary live imagery provider. Runtime status, evidence metadata, and UI provenance show the provider, repo, endpoints, timestamps, and cloud cover. | Strong |
| Innovation and Problem-Solution Fit | 35% | The workflow targets a specific operational problem: deciding which landfill site needs inspection first and why. It combines satellite evidence, model reasoning, plume polygons, triage, and exportable incident records. | Strong |
| Technical Implementation | 35% | FastAPI backend, SQLite persistence, DPhi SimSat live imagery, Hugging Face Transformers + PEFT LFM2.5-VL inference path, strict-live failure behavior, SSE scan progress, map overlays, evidence packs, tests, and run docs. | Strong |
| Demo and Communication | 20% | Demo script, architecture brief, live runbook, saved live artifact, and benchmark summary are included. | Strong |

## What To Show In The Demo

1. Open `http://127.0.0.1:8000/ops`.
2. Show `/runtime/status` or the UI live state: `DPhi SimSat`, `strict_live`, `simsat_reachable: true`.
3. Select `Belvedere Landfill London` or another watchlist site.
4. Show the `Live Imagery Provenance` card:
   - provider: DPhi SimSat,
   - repo: `https://github.com/DPhi-Space/SimSat`,
   - endpoints: `/data/current/image/sentinel`, `/data/image/sentinel`, `/data/current/image/mapbox`,
   - asset timestamps and cloud cover,
   - inference mode/model.
5. Click `Scan Site` if live dependencies are available.
6. Show the incident summary, plume/map overlays, evidence images, review action, and export.
7. Open `docs/latest_live_scan_artifact.md` as the saved backup proof.

## Live Proof Artifacts

- Live scan artifact markdown: `docs/latest_live_scan_artifact.md`
- Live scan artifact JSON: `data/processed/judge_live_artifacts/scan_083.json`
- Live smoke proof: `docs/latest_live_smoke_proof.md`
- Benchmark table: `docs/benchmark_summary_for_submission.md`
- Architecture brief: `docs/architecture_for_judges.md`
- Demo script: `docs/demo_script.md`
- DPhi SimSat runbook: `docs/run_demo_dphi_simsat.md`

## Run Commands

Start DPhi SimSat:

```powershell
cd external\SimSat
docker compose up --build
```

If Docker is unavailable on Windows but dependencies are installed, run the SimSat API directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:api --host 127.0.0.1 --port 9005
```

from `external\SimSat\src\sim`.

Start LandfillSentry:

```powershell
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Verify:

```powershell
.\.venv\Scripts\python.exe scripts\live_smoke.py --api-base-url http://127.0.0.1:8000 --simsat-base-url http://127.0.0.1:9005
.\.venv\Scripts\python.exe scripts\save_live_scan_artifact.py --api-base-url http://127.0.0.1:8000 --scan-id scan_083
```

## Honest Notes

- Strict live mode is intentional: if DPhi SimSat or live inference is unavailable, the scan fails instead of showing mock output as live.
- The public adapter path is trained, uploaded, wired, and benchmarked. The current report shows validation-loss improvement plus a measured lift on a small domain-adaptation fixture proxy; larger fully manual labels are still needed for a stronger production-quality model claim. This is documented in `docs/benchmark_summary_for_submission.md`.
- Cached evidence remains visible for operator review, but newly triggered judge-mode scans require live dependencies.
