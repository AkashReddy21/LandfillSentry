# Judge Deployment Runbook

## Recommended Choice

Use Docker for the LandfillSentry API/UI package and keep inference on the existing Hugging Face Transformers + PEFT path.

This is the selected inference tooling for the submission:

- Inference engine: Hugging Face Transformers
- Adapter loader: PEFT
- Base model: `LiquidAI/LFM2.5-VL-450M`
- Public adapter: `akashreddy2103/landfill`

Why this is the safest choice for judging:

- The app already supports `LiquidAI/LFM2.5-VL-450M` through Transformers.
- LoRA adapter loading is already wired through `HF_ADAPTER_ID` and `HF_ADAPTER_REVISION`.
- The strict judge path already rejects mock/fallback output when `REQUIRE_LIVE_RESULTS=true` and `INFERENCE_ALLOW_FALLBACK=false`.
- Docker makes the API/UI reproducible without asking judges to debug local Python paths.

Do not switch to llama.cpp, MLX, or ONNX for the judging build unless exported model artifacts are already validated. MLX is Apple-only, llama.cpp needs a compatible GGUF vision model path, and ONNX needs an export/validation step that is not currently implemented in this repo.

## What Is Implemented Now

- FastAPI app and `/ops` UI.
- Strict live judge mode.
- DPhi SimSat imagery integration and provenance.
- Hugging Face Transformers inference path.
- PEFT adapter loading with `HF_ADAPTER_ID=akashreddy2103/landfill`.
- Modal training scaffold and checkpoint record.
- Benchmark/evaluation artifacts for a small domain-adaptation fixture proxy.

## Credentials Needed At Runtime

For the final judged run, provide:

- `HF_ADAPTER_ID=akashreddy2103/landfill`
- `HF_TOKEN`: a token that can read the base model and adapter during judging.
- `MAPBOX_TOKEN`: needed by SimSat Mapbox imagery.
- The public Hugging Face model card already includes the dataset, methodology, benchmark, proof artifacts, and training code package.

## Local Judge Mode

This remains the fastest path on the current Windows machine:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_judge_mode.ps1 -RestartApi
```

Open:

```text
http://127.0.0.1:8000/ops
```

The script starts SimSat if needed, starts the API if needed, checks `/health` and `/ops`, then runs `scripts/live_smoke.py`.

## Docker API/UI Mode

From the repo root:

```powershell
docker compose --env-file .env.local -f docker-compose.landfillsentry.yml up --build
```

Open:

```text
http://127.0.0.1:8000/ops
```

The same Compose stack exposes:

- LandfillSentry API/UI: `http://127.0.0.1:8000`
- SimSat API: `http://127.0.0.1:9005`

Verify:

```powershell
.\.venv\Scripts\python.exe scripts\live_smoke.py --api-base-url http://127.0.0.1:8000 --simsat-base-url http://127.0.0.1:9005
```

Run preflight:

```powershell
.\.venv\Scripts\python.exe scripts\export_openapi.py
.\.venv\Scripts\python.exe scripts\judge_preflight.py --check-running
```

For a final submission that claims public fine-tuned adapter weights:

```powershell
.\.venv\Scripts\python.exe scripts\judge_preflight.py --strict-public-weights
```

## Required `.env.local` Values

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

Use `HF_LOCAL_FILES_ONLY=false` for a clean judge machine so the model can be downloaded. Use `true` only when the model is already cached.

## Final Submission Checklist

- `docker compose --env-file .env.local -f docker-compose.landfillsentry.yml up --build` starts the API.
- `/ops` loads without a frontend build step.
- `/runtime/status` shows live mode and SimSat provenance.
- `scripts/live_smoke.py` passes.
- `docs/latest_live_smoke_proof.md` is regenerated after the final run.
- `docs/benchmark_summary_for_submission.md` includes the public adapter ID, methodology, and measured base-vs-tuned delta.
- `/runtime/status` reports `inference_tooling=Hugging Face Transformers + PEFT`.
