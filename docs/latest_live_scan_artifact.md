# Live Scan Artifact

Generated: 2026-05-05T06:09:08+00:00

## Runtime

- Imagery provider: DPhi SimSat
- Provider repository: https://github.com/DPhi-Space/SimSat
- SimSat reachable: True
- Live scan available: True
- Scan policy: strict_live
- SimSat base URL: http://localhost:9005
- Inference tooling: Hugging Face Transformers + PEFT

## Scan

- Site: LF_REAL_007
- Scan ID: scan_083
- Incident ID: inc_083
- Status: live
- Inference mode: live
- Model: LiquidAI/LFM2.5-VL-450M@main+adapter=akashreddy2103/landfill@main

## Incident

- Priority: high
- Confidence: 0.85
- Zone: perimeter_or_unknown
- Review status: published

The evidence panel indicates a potential landfill site with a high likelihood of contamination. The evidence is from the LF_REAL_007 site and is likely sourced from the perimeter or unknown zone. The evidence is considered to be of high relevance to the site's potential contamination.

## DPhi SimSat Provenance

- Provider: DPhi SimSat
- Repository: https://github.com/DPhi-Space/SimSat
- Fetch status: live
- Source chain: `['dphi_simsat_sentinel_current', 'dphi_simsat_sentinel_historical', 'dphi_simsat_mapbox_context']`

Endpoints:

- sentinel_current: `/data/current/image/sentinel`
- sentinel_historical: `/data/image/sentinel`
- mapbox_context: `/data/current/image/mapbox`

| Asset | Source | Captured | Cloud Cover | Local Path |
|---|---|---|---:|---|
| sentinel_current | dphi-simsat | 2026-05-03T10:36:59+00:00 | 0.8499029899999999 | data/cache/assets/f1/f1ca55cbc7ddef5551b5ac1cb0e7eb047aa7c1c7b08b69442526bdec18118f7a.img |
| sentinel_historical | dphi-simsat | 2026-04-26T10:46:55+00:00 | 0.07104859000000001 | data/cache/assets/8d/8ddb0342cfa026aa2591d799b226f23ade86d6e9de4a33a2ffbcfbc6ce4285a8.img |
| mapbox_context | mapbox | 2026-05-05T06:07:47+00:00 | 0.0 | data/cache/assets/e7/e75506537c03f2f240f03420891530f03a7cc359ea1e5e502981a3d4a46aa80d.img |
