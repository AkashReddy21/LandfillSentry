# Live Smoke Proof

Generated: 2026-05-05T06:09:00+00:00

## Command

```bash
python scripts/live_smoke.py --api-base-url http://127.0.0.1:8000 --simsat-base-url http://127.0.0.1:9005
```

## Result

- Status: PASS
- Site: LF_REAL_007
- Scan ID: scan_083
- Incident ID: inc_083
- Inference mode: live
- Inference tooling: Hugging Face Transformers + PEFT
- Panel preview keys: current_rgb, spectral_composite, temporal_diff, mapbox_context

## Checks

- SimSat health returned HTTP 200.
- API `/health` returned `status=ok`.
- Watchlist returned at least one site.
- Live scan completed.
- Evidence metadata reported `inference.mode=live`.
- Site detail returned panel previews.
- Review status persisted through export.
- Incident export returned evidence.
