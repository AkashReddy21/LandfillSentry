# LandfillSentry Judge Demo Script (5 Minutes)

Date: May 5, 2026  
Audience: Hackathon judges

## 1) Problem Framing (30s)

Landfill teams do not need another generic map. They need a clear answer to: "Where do we inspect first, and why?"  
LandfillSentry turns satellite evidence into a reviewable incident object with operational follow-up guidance.

## 2) Live Scan Walkthrough (90s)

1. Open `http://127.0.0.1:8000/ops`.
2. Select one watchlist site.
3. Click `Scan Site` or `Scan Watchlist`.
4. Explain:
- `generation mode` shows `live`.
- imagery is fetched from DPhi SimSat coordinate endpoints for Sentinel current, Sentinel historical, and Mapbox context.
- current endpoints are `/data/current/image/sentinel` and `/data/current/image/mapbox`; historical Sentinel uses `/data/image/sentinel`.
- scan fails fast in judge mode if live dependencies are unavailable.

## 3) Evidence + Review Action (90s)

1. Show `Incident Summary`.
2. Show `Live Imagery Provenance`:
- DPhi SimSat provider and repository,
- `/data/current/image/sentinel`, `/data/image/sentinel`, and `/data/current/image/mapbox` endpoint usage,
- source chain,
- capture timestamps,
- live fetch status.
3. Review as operator:
- click `Publish`, `Dismiss`, or `Needs Review`.
4. Confirm state change in watchlist row.

## 4) Export + Dongle Corroboration (60s)

1. Click `Add Dongle Reading`.
2. Run scan again.
3. Show corroboration changing from `Satellite-only` to `Satellite + Dongle corroborated`.
4. Load markdown export and highlight:
- data source provenance,
- ground truth hint,
- recommended follow-up.

## 5) Architecture + Product Story (60s)

1. Satellite-first triage pipeline:
- SimSat imagery retrieval,
- candidate generation and evidence panel,
- LFM2.5-VL structured reasoning,
- operator review workflow.
2. Why this is productizable:
- clear workflow outcome, not just maps,
- audit-ready export object,
- extensible with field dongle ground truth loop.

## Demo Safety Notes

- Run `scripts/start_judge_mode.ps1` before demo.
- Keep `http://127.0.0.1:9005` DPhi SimSat running.
- If any live system fails, show deterministic error message (no fake live fallback).
- Smoke proof: `docs/latest_live_smoke_proof.md` shows scan `scan_083` passed judge-mode checks.
- Backup artifact: `docs/latest_live_scan_artifact.md` shows scan `scan_083` with strict-live DPhi SimSat provenance.
