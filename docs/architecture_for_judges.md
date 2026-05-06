# Architecture Brief For Judges

## End-to-End Flow

1. Site selected from watchlist (`/watchlist`).
2. Backend fetches imagery bundle:
- Sentinel current at selected landfill coordinates (`/data/current/image/sentinel` via DPhi SimSat),
- Sentinel historical (`/data/image/sentinel` via SimSat),
- Mapbox context at selected landfill coordinates (`/data/current/image/mapbox` via DPhi SimSat).
3. Candidate engine proposes likely methane-risk zone.
4. Evidence panel builder assembles current, spectral, temporal, and context views.
5. LFM2.5-VL (`LiquidAI/LFM2.5-VL-450M`) runs through Hugging Face Transformers with the PEFT LoRA adapter (`akashreddy2103/landfill`) and produces structured incident output.
6. Output validation enforces schema and normalization.
7. Incident + scan + evidence metadata are persisted.
8. Operator reviews and exports evidence.

## Live Reliability Controls

- `REQUIRE_LIVE_RESULTS=true` blocks non-live runtime modes.
- `INFERENCE_ALLOW_FALLBACK=false` prevents fallback from being shown as live.
- watchlist/site detail strict selector only surfaces live-generated incidents in judge mode.
- `scripts/live_smoke.py` verifies SimSat/API health, live scan success, previews, review persistence, and export.

## Provenance Contract

Every scan evidence payload stores:
- `imagery_provenance.source_chain`,
- per-asset timestamps and source metadata,
- `live_fetch_status`,
- `inference.mode`.

This is exposed in:
- `/sites/{site_id}/detail`,
- `/scans/{scan_id}/evidence`,
- `/incidents/{incident_id}/export`.

## Dongle Corroboration Loop

- API supports field methane ingestion:
  - `POST /sites/{site_id}/dongle-readings`
  - `GET /sites/{site_id}/dongle-readings`
- Latest unlinked dongle reading is attached to newly generated incident as `ground_truth_hint`.
- UI and export explicitly show `Satellite-only` vs `Satellite + Dongle corroborated`.

## Deployment Notes

- Backend: FastAPI + SQLite
- Frontend: FastAPI-served ops console at `/ops` (`apps/web/ops.html`, `ops.css`, `ops.js`)
- Live imagery: DPhi SimSat + Mapbox
- Inference tooling: Hugging Face Transformers + PEFT
- Model artifacts: Hugging Face base model + public PEFT adapter
- Fine-tuning compute: Modal GPU
