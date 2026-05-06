# LandfillSentry Judge-Guideline Gap Closure Plan

Date: April 22, 2026  
Scope: Backend + Frontend + live-data reliability + demo readiness + fine-tuning evidence

## 1) Judge Criteria to Delivery Map

| Judge Criterion | Weight | Current Risk | Required State for Scoring |
|---|---:|---|---|
| Use of Satellite Imagery | 10% | Medium | DPhi/SimSat imagery is the primary source in every scan path, with visible provenance and timestamps in UI/API artifacts. |
| Innovation + Problem/Solution Fit | 35% | Medium-High | Clear domain narrative: satellite-first triage + LFM2-VL reasoning + optional field dongle verification loop. |
| Technical Implementation | 35% | High | One-command run, no judge debugging, stable live scan and review workflow, deterministic failure messaging. |
| Demo + Communication | 20% | Medium | End-to-end live demo script, architecture explanation, fallback policy explained without ambiguity. |

## 2) Current Gaps (Observed)

1. Live vs fallback confusion:
- older fallback/mock incidents may still exist in DB history
- users need explicit provenance and generation mode visibility

2. Frontend UX quality:
- engineering labels can leak into user-facing names
- operator intent must be clearer than raw backend fields

3. Runtime reliability:
- live scans can fail when SimSat/Mapbox/model output is unavailable or invalid
- judge mode must fail fast and clearly (never pretend fallback is live)

4. Demo readiness:
- judges need a repeatable one-command startup + smoke check flow

## 3) Required Changes by Criterion

## 3.1 Use of Satellite Imagery (10%)

### Must Have Status
- [x] Expose imagery provenance in every incident:
  - `source_chain`
  - per-asset capture timestamps
  - `live_fetch_status`
- [x] UI transparency:
  - `Live Imagery Provenance` section in site detail
  - `generation mode` visible in summary

### Files Updated
- `apps/api/routes/api.py`
- `apps/api/services/imagery_service.py`
- `apps/web/public/ops-app.jsx`

### Acceptance
- [x] For displayed incidents, UI shows provenance fields and generation mode.

---

## 3.2 Innovation + Problem/Solution Fit (35%)

### Must Have Status
- [x] Product story signals in-app:
  - why alert exists (incident summary text)
  - what to inspect first (recommended follow-up/export)
  - confidence visibility
- [x] Dongle integration path:
  - methane reading ingest endpoint
  - attach reading to incident as `ground_truth_hint`
  - UI badge: `Satellite-only` vs `Satellite + Dongle corroborated`
- [ ] OpenAPI artifact refreshed to include latest dongle routes

### Files Updated
- `apps/api/routes/api.py`
- `apps/api/db/repository.py`
- `apps/api/schemas/models.py`
- `apps/web/public/ops-app.jsx`
- `tests/test_phase8_ui_workflow.py`

### Acceptance
- [x] One incident can show satellite evidence + attached dongle reading in UI and export.

---

## 3.3 Technical Implementation (35%)

### Must Have Status
- [x] Strict live-only policy for judge mode:
  - `REQUIRE_LIVE_RESULTS=true` gating
  - strict scan selection for live-generated results in watchlist/detail
  - actionable fast-fail for non-live runtime mismatch
- [x] One-command run script:
  - `scripts/start_judge_mode.ps1`
- [x] Deterministic smoke tests:
  - `scripts/live_smoke.py` checks health, scan, live mode, previews, review persistence, export
- [x] Fallback ambiguity removed:
  - fallback only when explicitly enabled
  - strict mode rejects invalid live outputs

### Files Updated
- `scripts/start_judge_mode.ps1`
- `scripts/live_smoke.py`
- `apps/api/config.py`
- `apps/api/routes/api.py`
- `apps/api/services/inference_service.py`
- `README.md`
- `tests/test_phase5_inference.py`

### Acceptance
- [x] Fresh-machine style startup + smoke workflow exists and is documented.

---

## 3.4 Demo + Communication (20%)

### Must Have Status
- [x] 5-minute demo sequence documented
- [x] Architecture brief for judges documented
- [x] Benchmark summary template + reproducible commands documented
- [ ] Final architecture diagram image asset prepared
- [x] Final benchmark table populated with tuned vs base numeric deltas

### Files Added
- `docs/demo_script.md`
- `docs/architecture_for_judges.md`
- `docs/benchmark_summary_for_submission.md`

### Acceptance
- [x] Any teammate can follow the same demo sequence from documentation.

## 4) Priority Execution Plan (Order Matters)

1. Reliability first:
- [x] strict live-only path + judge-mode run script

2. UX second:
- [x] operator-first wording and provenance section

3. Dongle path third:
- [x] lightweight corroboration feature

4. Submission pack fourth:
- [x] docs scaffolds created
- [ ] final numeric benchmark fill-in
- [ ] final architecture diagram export

## 5) Concrete Sprint Backlog

## P0 (Blockers)
1. [x] Add `scripts/start_judge_mode.ps1` and `scripts/live_smoke.py`.
2. [x] Ensure watchlist/site detail only display strict live-generated incidents in judge mode.
3. [x] Add explicit live provenance block in UI and export payload.

## P1 (Score Multipliers)
1. [x] Add dongle ingestion endpoint + UI badge integration.
2. [x] Add benchmark delta table with final measured numbers.
3. [x] Finalize demo script and architecture brief docs.

## P2 (Polish)
1. [ ] Copywriting pass for operator persona language.
2. [ ] Responsive UI polish + empty/error states.
3. [ ] Screenshot pack generation for submission fallback/live comparison.

## 6) Done Definition Before Submission

Project is ready only if all are true:
1. [x] Judge can run using one command/script, no manual debugging path documented.
2. [x] UI displays live-generated incident with satellite provenance fields.
3. [x] Review + export flow succeeds end-to-end.
4. [x] Base vs tuned improvement table is filled with reproducible measured values.
5. [x] Demo narrative explains satellite + LFM2-VL + dongle loop.

## 7) Immediate Next Actions

1. [x] Implement `start_judge_mode.ps1` + `live_smoke.py`.
2. [x] Add `Live Imagery Provenance` panel in frontend.
3. [x] Add `dongle_readings` table + ingest API skeleton.
4. [ ] Re-run strict live screenshot pack for submission assets.
5. [ ] Refresh `openapi.json` to include latest dongle endpoints.
