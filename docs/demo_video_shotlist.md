# Demo Video Shot List

Target length: 3-5 minutes.

## Pre-Record Checklist

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_judge_mode.ps1 -RestartApi
```

Verify these are ready:
- `http://127.0.0.1:8000/ops`
- `docs/latest_live_smoke_proof.md`
- `docs/latest_live_scan_artifact.md`
- `docs/benchmark_summary_for_submission.md`

## Recording Flow

1. Problem framing, 20s  
   Landfill operators need to know which site to inspect first and why, not just see another map.

2. Architecture, 35s  
   Show the flow: watchlist site -> DPhi SimSat Sentinel/Mapbox imagery -> candidate/evidence panel -> LFM2.5-VL incident JSON -> operator review/export.

3. Live proof, 45s  
   Show `docs/latest_live_smoke_proof.md`: status `PASS`, scan `scan_083`, inference mode `live`, all previews present.

4. Product walkthrough, 90s  
   Open `/ops`, select the scan/site, show evidence previews, provenance, source chain, timestamps, priority, confidence, and review status.

5. Reliability, 30s  
   Explain strict mode: if live imagery or inference is unavailable, the app fails with an actionable error instead of pretending cached/mock output is live.

6. Fine-tune and benchmark, 45s  
   Show `docs/benchmark_summary_for_submission.md`: Modal LoRA run `lora_run_20260504T181913Z`, 78 live-scan samples, public adapter `akashreddy2103/landfill`, validation-loss improvement, and the base-vs-tuned metric table.

7. Close, 20s  
   Emphasize the useful operator outcome: auditable, reviewable methane incident triage with live satellite provenance.

## Must-Say Lines

- "This is strict live mode: no fallback is presented as live."
- "DPhi SimSat is the primary imagery provider, with current Sentinel, historical Sentinel, and Mapbox context recorded in provenance."
- "The output is not just a caption; it becomes a persisted incident with review state and exportable evidence."
