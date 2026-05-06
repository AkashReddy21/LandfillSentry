# DPhi SimSat Live Demo Runbook

Use this path for the hackathon judging demo. It keeps the app on live DPhi SimSat imagery and live inference, with no mock/sample scan output presented as real.

## 1. Start DPhi SimSat

The hackathon-provided imagery backend is:

`https://github.com/DPhi-Space/SimSat`

This repository includes a local copy under `external/SimSat`.

```powershell
cd external\SimSat
docker compose up --build
```

Confirm the SimSat API is available on:

`http://localhost:9005`

Required API paths:

- `GET /data/current/image/sentinel`
- `GET /data/image/sentinel`
- `GET /data/current/image/mapbox`
- `GET /data/image/mapbox`

LandfillSentry scans watchlist sites through the coordinate-based DPhi SimSat endpoints, so the selected landfill coordinates are passed directly to `/data/current/image/sentinel`, `/data/image/sentinel`, and `/data/current/image/mapbox`.

## 2. Configure LandfillSentry

In `.env.local`, use live/strict settings:

```env
SIMSAT_MODE=live
MAPBOX_MODE=live
INFERENCE_MODE=live
REQUIRE_LIVE_RESULTS=true
INFERENCE_ALLOW_FALLBACK=false
SIMSAT_BASE_URL=http://localhost:9005
SIMSAT_USE_FOR_MAPBOX=true
```

Add the real tokens required by your local environment, for example `HF_TOKEN` and Mapbox credentials.

## 3. Start the app

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_judge_mode.ps1 -RestartApi
```

Open:

`http://127.0.0.1:8000/ops`

## 4. Judge Verification

These endpoints should all respond from the running app:

- `GET /runtime/status`
- `GET /ops/summary`
- `GET /overlays/plumes`

`/runtime/status` should show:

- `imagery_provider`: `DPhi SimSat`
- `imagery_provider_repository`: `https://github.com/DPhi-Space/SimSat`
- `simsat_required_endpoints`: the Sentinel and Mapbox endpoint list
- `scan_policy`: `strict_live`

If DPhi SimSat or live inference is unavailable, scans fail with an actionable error instead of silently substituting mock/sample data.

## 5. Saved Proof

The smoke command writes:

- `docs/latest_live_smoke_proof.md`
- `data/processed/live_smoke_proof.json`

The latest archived scan proof is:

- `docs/latest_live_scan_artifact.md`
- `data/processed/judge_live_artifacts/scan_083.json`
