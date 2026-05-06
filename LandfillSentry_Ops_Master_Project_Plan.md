# LandfillSentry Ops Master Project Plan

> Canonical execution document for building LandfillSentry Ops as a hackathon-winning MVP with a credible path to a startup-grade product.
>
> Planning basis:
> - Product and architecture source: `LandfillSentry_Ops_Detailed_Report.md`
> - Frozen defaults and scope decisions: `LandfillSentry_Ops_Answers_to_Open_Questions.md`
> - Planning structure reference: `UNIVERSAL_LLM_PROJECT_PLAN_TEMPLATE.md`

### Operating Mode

Use this document as a 2-layer system:

1. Master Plan: strategy, constraints, architecture, phases, testing rules, and acceptance logic.
2. Execution Cards: small, timeboxed tasks used during implementation.

Rules:
- Keep this file as the single source of truth.
- No phase is complete until it passes its integration checkpoint.
- Every major capability must support both a live path and a cached offline path.
- Every two phases must end with one full end-to-end scan.
- Prefer one stable implementation path over multiple half-working alternatives.

### Lean Usage Mode for This Project

Because LandfillSentry is both product-heavy and system-heavy, the following sections are mandatory for this plan:

- `0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 18, 19`

The following sections are included because they materially reduce execution risk:

- `13, 14, 15`

---

## 0) Project Identity

- **Project Name:** `LandfillSentry Ops`
- **Status:** `in progress`
- **Version:** `Master Plan v1.0 - Full Draft`
- **Primary Mode:** `Hackathon MVP first, product-grade foundation second`
- **Core Product Identity:** `Operator-first landfill methane incident triage copilot`
- **One-line Memory Hook:** `LandfillSentry turns satellite imagery into an explainable methane incident object that tells operators where to inspect first.`

### 0.1 Strategic Positioning

LandfillSentry Ops is not a generic remote sensing dashboard, and it is not a regulatory methane quantification system.

It is:
- a triage and prioritization product,
- built around landfill operations,
- using satellite imagery as the core evidence source,
- with a structured incident object as the product output,
- and a human review step before incidents become official.

### 0.2 Product Thesis

Existing methane monitoring ecosystems increasingly provide detections, maps, and broad emissions context. Landfill operators still lack a lightweight operational workflow that converts mixed satellite evidence into a facility-specific, explainable, inspectable incident recommendation.

LandfillSentry exists to close that gap.

---

## 1) Goal

### Primary Goal

Build a hackathon-winning MVP that scans a watchlist of landfill sites using SimSat imagery, generates methane-risk candidates, converts compact evidence panels into structured incident objects using Liquid's `LFM2.5-VL-450M`, and shows operators which zone to inspect first.

### Secondary Goals

- Demonstrate a credible fine-tuning story rather than a prompt-only demo.
- Prove operator usefulness through structured outputs, explainable evidence, and a clear action recommendation.
- Build the architecture so it can realistically evolve into a startup-grade product after the hackathon.
- Produce a polished demo that is robust to live failures through cached assets and offline-safe flows.

### 1.1 Definition of MVP Success

The MVP succeeds if it can do the following reliably for a small frozen demo set:

1. retrieve current and historical imagery for a selected site,
2. generate a plausible methane-risk candidate region,
3. build an evidence panel for model interpretation,
4. return valid structured incident JSON,
5. display the incident clearly in a watchlist-first UI,
6. allow human review before publication,
7. export a clean evidence summary,
8. and survive demo conditions using both live and cached execution paths.

---

## 2) Context & Problem Statement

### Current State

The waste sector is a large methane source, and landfill emissions are increasingly visible through remote sensing and public methane initiatives. Yet most available systems are designed for mapping, scientific interpretation, portfolio-level visibility, or policy action rather than day-to-day operational triage by landfill teams.

Existing tools can tell users that methane matters or that a site may be emitting. They often do not compress that evidence into a site-specific operational question:

`Where should my team inspect first, and why?`

### Problem

Landfill operators face three linked problems:

1. methane evidence arrives as raw or semi-processed imagery rather than operational guidance,
2. interpreting site structure, source zone, and urgency requires manual reasoning,
3. false positives or ambiguous alerts quickly destroy trust if outputs are not explainable and reviewable.

### Why It Matters Now

- Waste methane is gaining more policy and operational attention globally.
- Remote sensing is increasingly being used to guide waste-sector methane action.
- Landfill work-face and facility-zone attribution are becoming more important for mitigation prioritization.
- The hackathon stack creates an unusually strong fit: `SimSat` for imagery, `Liquid` for compact grounded multimodal reasoning, and open methane tooling such as Project Eucalyptus for domain bootstrapping.

### Who Is Impacted

- Primary: landfill operations managers and site operations leads
- Secondary: environmental compliance leads, consultants, municipalities, insurers, and climate program teams

### 2.1 Product Value Statement

LandfillSentry reduces operator cognitive load by turning imagery, temporal comparison, and contextual metadata into a compact incident object that can be reviewed, prioritized, and acted on quickly.

### 2.2 Explicit Non-Claims

LandfillSentry does not claim to provide:

- regulatory-grade methane quantification,
- legal attribution of emissions,
- continuous coverage,
- full atmospheric inversion,
- or autonomous final decision authority.

It is a triage copilot, not a final truth engine.

---

## 3) Constraints & Boundaries

### Tech Stack Constraints

- **Imagery sources for MVP:** `SimSat` and `Mapbox` are both required imagery/context inputs.
- **Backend:** `FastAPI`
- **Frontend:** `React`
- **Storage:** `SQLite` first
- **Primary inference path:** `Transformers`
- **Primary model:** `LiquidAI/LFM2.5-VL-450M`
- **Model registry and artifact source:** `Hugging Face` is required for model and adapter distribution.
- **Training method:** `LoRA` or similarly lightweight adapter tuning
- **Training infrastructure:** `Modal GPU` is required for training runs.
- **Execution model:** synchronous inference for MVP with caching

### Performance Constraints

- Demo flows must feel responsive enough for judge interaction.
- Live scan latency can be several seconds if clearly signaled, but cached demo paths should be near-instant.
- JSON validation and rendering must remain deterministic even if model latency varies.

### Security / Privacy / Licensing Constraints

- API tokens must never be hardcoded.
- SimSat, Mapbox, Hugging Face, and Modal credentials must be environment-driven.
- Model and dataset licenses must be reviewed and documented.
- Real sites may be used, but wording must avoid unvalidated legal or regulatory claims.
- Synthetic, weak, and manual labels must remain provenance-tracked.

### Data Constraints

- Manual labeled data is limited to approximately `80-200` usable examples.
- One primary labeler is assumed.
- Negative examples are first-class and must be budgeted intentionally.
- Validation and demo splits must be frozen early.

### Hackathon Constraints

- The system must run reliably under demo conditions.
- Fine-tuning is highly desirable, but the product needs a fallback path if the fine-tuned model underperforms.
- Architecture must support storytelling and judging clarity, not just technical completeness.

### Non-Goals

- Full compliance workflow
- Multi-tenant enterprise administration
- Full atmospheric modeling
- Advanced job orchestration infrastructure
- Complete automated active learning loop
- Production-scale global monitoring
- A generalized methane platform spanning all facility classes in MVP

### 3.1 Boundary Rule

If a feature does not directly improve one of the following, it is not MVP-critical:

- operator usefulness,
- valid incident generation,
- demo stability,
- fine-tuning credibility,
- or evaluation clarity.

---

## 4) Success Metrics (Measurable)

Directional metrics are preferred over overconfident hard claims at this stage. Final thresholds can be refined after the first end-to-end evaluation pass.

- [ ] **Metric 1: End-to-end Incident Reliability** - baseline: `not yet measured`, target: `stable valid JSON on >95% of frozen validation examples`, measurement: `schema validation pass rate across validation and golden fixtures`
- [ ] **Metric 2: Operator Usefulness** - baseline: `not yet measured`, target: `majority of reviewed incidents rated actionable by human rubric`, measurement: `manual scoring rubric on usefulness and explainability`
- [ ] **Metric 3: Null-Scene Trustworthiness** - baseline: `not yet measured`, target: `false positive rate below agreed threshold on negative split`, measurement: `negative-scene evaluation report`
- [ ] **Metric 4: Zone Guidance Quality** - baseline: `not yet measured`, target: `meaningful improvement over prompt-only baseline`, measurement: `source-zone accuracy / coarse zone agreement`
- [ ] **Metric 5: Demo Stability** - baseline: `not yet measured`, target: `100% success on frozen demo path`, measurement: `rehearsed runs on cached demo fixtures`
- [ ] **Metric 6: Model Improvement Story** - baseline: `base prompt-only model`, target: `fine-tuned model outperforms base on structured output reliability and human usefulness`, measurement: `baseline comparison table`

### 4.1 Prioritized Metric Hierarchy

Metrics are not equally important. The project should optimize in this order:

1. operator usefulness,
2. JSON validity,
3. null-scene trustworthiness,
4. source-zone accuracy,
5. bbox quality,
6. persistence scoring quality.

### 4.2 MVP Success Threshold Narrative

The MVP is considered strong if it can show:

- a believable operational workflow,
- high structured-output reliability,
- low embarrassing false positives on golden negatives,
- an understandable action recommendation,
- and a measurable improvement path from heuristics and base-model prompting to fine-tuned performance.

---

## 5) Architecture Snapshot

### 5.1 System Components

- **API Gateway / Orchestrator**
  - receives site scan requests,
  - coordinates imagery retrieval, candidate generation, panel building, inference, validation, and persistence.

- **Site Registry**
  - stores demo sites, watchlist metadata, coordinates, optional polygons, and status metadata.

- **Imagery Retrieval Service**
  - fetches current and historical imagery from `SimSat`,
  - retrieves required Mapbox context,
  - caches responses and normalized assets.

- **Preprocessing & Quality Control**
  - handles cloud filtering, band selection, temporal selection, normalization, and failure handling when imagery is weak or absent.

- **Candidate Generation Engine**
  - produces one or more suspicious methane-risk candidate regions using hybrid logic:
    - spectral heuristics,
    - temporal differencing,
    - optional ranking/refinement informed by methane-domain assets.

- **Evidence Panel Builder**
  - combines current crop, methane-sensitive spectral composite, temporal comparison crop, required Mapbox context, and compact metadata into a stable multimodal input.

- **VLM Inference Service**
  - runs `LFM2.5-VL-450M`,
  - initially in prompt-only mode,
  - then with a fine-tuned adapter path.

- **Incident Object Generator**
  - validates and normalizes model output,
  - computes priority and severity tiers,
  - assigns review state,
  - and stores structured records.

- **Results Store**
  - persists sites, assets, candidates, incidents, feedback, and evaluation records.

- **React UI**
  - watchlist-first workflow,
  - drill-down site detail,
  - evidence pack view,
  - review and publication actions.

### 5.2 Interfaces / Contracts

Core contract objects:

- `Site`
- `ImageAsset`
- `Candidate`
- `EvidencePanel`
- `Incident`
- `EvaluationRecord`
- `ReviewAction`

Contract rules:

- Incident outputs must always validate through typed schemas.
- Controlled enums should be used for fields like `priority_tier`, `severity_tier`, `review_status`, and `likely_source_zone`.
- API responses must be versionable and covered by `openapi.json`.
- Cached artifacts must be reusable across backend tests, UI smoke flows, and demo runs.

### 5.3 API Contract Artifact (`openapi.json`)

Artifact policy:

- Keep a committed `openapi.json` at repo root.
- Refresh it whenever API contracts change.
- Treat stale contract drift as a blocker for frontend work.
- Contract tests must cover the main endpoints:
  - health,
  - register site,
  - list sites,
  - scan site,
  - get result,
  - fetch evidence pack,
  - watchlist scan,
  - export incidents.

### 5.4 Data & State Strategy

- **Source of truth:** `SQLite` for MVP
- **Cache:** local filesystem + DB-linked asset metadata
- **Model artifacts:** stored separately and versioned by training run
- **Frozen artifacts:** demo panels, golden fixtures, evaluation manifests
- **Consistency model:** application-level consistency is acceptable for MVP; strict transactional complexity is unnecessary beyond core scan persistence

### 5.5 Key Risks in Architecture

- `SimSat` imagery inconsistency or missing scenes
- cloud-heavy scenes degrading candidate quality
- model outputs becoming invalid or verbose
- weak candidate generation overwhelming the VLM
- Mapbox dependency becoming a hard runtime dependency if credentials or quotas fail
- evaluation drift if splits and fixtures are not frozen early

### 5.6 Architectural Principle

The VLM should interpret evidence, not replace the full detection pipeline.

That means:

- candidate generation remains an explicit stage,
- evidence packing remains deterministic and inspectable,
- the VLM produces structured incident interpretation,
- and post-processing remains typed and auditable.

### 5.7 Differentiation Snapshot

LandfillSentry should be positioned as:

- not a global methane portal like `WasteMAP`,
- not a government-facing methane notification system like `UNEP MARS`,
- not a broad remote sensing emissions visibility platform like `Carbon Mapper`,
- but an operator-first triage copilot that converts imagery into an actionable incident object for landfill teams.

---

## 6) Phase Plan

This plan uses nine phases. The phases are intentionally integration-aware rather than function-siloed.

## Phase 1: Foundation Lock

### Objective

Freeze product scope, schemas, demo-site strategy, repo structure, contracts, and testing rules before implementation complexity grows.

### Deliverables

- [x] canonical master plan initialized
- [x] repo structure finalized
- [x] core schemas defined
- [x] `openapi.json` first draft generated
- [x] frozen demo-site selection process defined
- [x] testing and integration policy defined

### In-Scope / Out-of-Scope

- **In scope:** planning freeze, repo conventions, contract design, fixture planning
- **Out of scope:** full production implementation

### Dependencies

- **Requires:** detailed report, answers doc
- **Blocks:** all downstream implementation quality

### Parts in This Phase

- `1.1` Product and workflow lock
- `1.2` Data and schema contract lock
- `1.3` Testing and integration policy lock

### Phase Exit Criteria

- [x] Scope is frozen for MVP
- [x] JSON schema and API direction are frozen
- [x] Demo-site selection method is frozen
- [x] Golden fixture categories are defined
- [x] One integration checklist exists for future phases

---

## Phase 2: Site Registry, Imagery, and Cache

### Objective

Create the stable acquisition layer for sites, current imagery, historical imagery, required Mapbox context, and offline caching.

### Deliverables

- [x] site registry working
- [x] SimSat retrieval working for frozen demo sites
- [x] Mapbox retrieval working for frozen demo sites
- [x] caching layer working
- [x] basic cloud / missing-data handling working
- [x] live and cached retrieval path verified

### In-Scope / Out-of-Scope

- **In scope:** site metadata, image fetching, cache persistence, retrieval errors
- **Out of scope:** final methane interpretation quality

### Dependencies

- **Requires:** Phase 1 contracts
- **Blocks:** candidate generation, panel building, demo assets

### Parts in This Phase

- `2.1` Site registry and watchlist model
- `2.2` SimSat imagery adapters
- `2.3` Cache and image asset persistence

### Phase Exit Criteria

- [x] At least one positive and one negative demo site fetch cleanly
- [x] Mapbox context fetch and cache replay work for frozen demo sites
- [x] Cached replay works without live calls
- [x] Missing-data and cloud-heavy paths fail gracefully
- [x] API contract remains valid
- [x] Integration checkpoint with Phase 1 passes

---

## Phase 3: Candidate Generation and Zone Priors

### Objective

Build the hybrid candidate engine that proposes suspicious regions and coarse source-zone hypotheses, using Phase 2 imagery assets from live/cached SimSat Sentinel (current + historical) and required Mapbox context.

### Deliverables

- [x] heuristic candidate stage implemented
- [x] temporal differencing implemented
- [x] coarse source-zone prior logic implemented
- [x] candidate scoring contract finalized
- [x] positive, negative, cloudy, and missing-data fixtures supported
- [x] live candidate path verified against SimSat current Sentinel (`/data/current/image/sentinel`), historical Sentinel (`/data/image/sentinel`), and current Mapbox context (`/data/current/image/mapbox`)

### In-Scope / Out-of-Scope

- **In scope:** suspicious-region proposal, simple ranking, zone priors, and candidate operation on both live and cached imagery bundles
- **Out of scope:** final full incident interpretation

### Dependencies

- **Requires:** imagery and cache layer, SimSat live endpoint availability (or source bootstrap runner), and Mapbox token for live context retrieval
- **Blocks:** evidence panels and model inference

### Parts in This Phase

- `3.1` Heuristic anomaly generation
- `3.2` Temporal recurrence features
- `3.3` Zone prior and candidate scoring

### Phase Exit Criteria

- [x] Candidate object emits valid schema
- [x] Null-scene behavior is acceptable on golden negatives
- [x] Candidate outputs are inspectable in logs or notebook form
- [x] Cached and live candidate paths both run
- [x] Live Phase 3 scan path runs with SimSat current+historical Sentinel and required current Mapbox context
- [x] Integration checkpoint with Phases 1-2 passes

---

## Phase 4: Evidence Panels and Prompt Contract

### Objective

Build the deterministic evidence-packing layer and freeze the prompt / output contract used for base-model inference and later fine-tuning.

### Deliverables

- [x] evidence panel format frozen
- [x] panel builder implemented
- [x] required Mapbox panel input integrated
- [x] metadata text block finalized
- [x] prompt contract finalized
- [x] output schema validation loop implemented

### In-Scope / Out-of-Scope

- **In scope:** panel composition, prompt format, schema validation
- **Out of scope:** fine-tuned model quality gains

### Dependencies

- **Requires:** candidate outputs and imagery
- **Blocks:** base inference, training dataset format

### Parts in This Phase

- `4.1` Panel composition pipeline
- `4.2` Prompt and metadata contract
- `4.3` Output schema and retry policy

### Phase Exit Criteria

- [x] Panels render consistently for frozen fixtures
- [x] Every panel includes required Mapbox context artifact
- [x] Prompt contract is frozen for training
- [x] Incident schema validates on canned responses
- [x] Live and cached panel-building paths both work
- [x] First full end-to-end scan checkpoint passes across Phases 1-4

---

## Phase 5: Base Model Inference and Incident Pipeline

### Objective

Run the base `LFM2.5-VL-450M` model end to end with prompt-only structured output and complete the first fully functioning incident pipeline.

### Deliverables

- [x] base-model inference service working
- [x] Hugging Face model pull and auth path working
- [x] structured JSON validation working
- [x] incident object persistence working
- [x] review state lifecycle working
- [x] priority / severity logic working

### In-Scope / Out-of-Scope

- **In scope:** prompt-only incident generation, post-processing, storage
- **Out of scope:** tuned model superiority

### Dependencies

- **Requires:** frozen evidence and output contract, Hugging Face credentials and model access
- **Blocks:** baseline benchmarking, UI truth wiring

### Parts in This Phase

- `5.1` Base inference runner
- `5.2` Incident normalization and review flow
- `5.3` Structured persistence and retrieval

### Phase Exit Criteria

- [x] Prompt-only pipeline works on frozen demo path
- [x] Inference path resolves model artifacts from Hugging Face with pinned revision
- [x] Invalid JSON path is handled gracefully
- [x] Review states work correctly
- [x] API retrieval endpoints function against real saved incidents
- [x] Integration checkpoint with prior phases passes

---

## Phase 6: Dataset Build and Fine-Tuning

### Objective

Assemble a compact, provenance-aware training set and train a useful LoRA adapter that improves structured incident quality.

### Deliverables

- [x] dataset manifest v1
- [x] annotation guidance v1
- [x] train / validation / demo split frozen
- [x] LoRA training script working
- [x] Modal GPU training job orchestration working
- [x] first tuned checkpoint produced

### In-Scope / Out-of-Scope

- **In scope:** label taxonomy, manifests, synthetic + manual + weak data separation, LoRA training
- **Out of scope:** large-scale research-grade dataset creation

### Dependencies

- **Requires:** frozen prompt and panel contract, Modal account access, Hugging Face artifact push/pull path
- **Blocks:** benchmark comparison and final demo quality story

### Parts in This Phase

- `6.1` Dataset assembly and provenance
- `6.2` Annotation rules and negative set
- `6.3` Fine-tuning run and checkpointing

### Phase Exit Criteria

- [x] Every sample has provenance metadata
- [x] Validation and demo splits are frozen and respected
- [x] Fine-tuned checkpoint can run in the same pipeline contract as the base model
- [x] At least one full fine-tuning run completes on Modal GPU
- [x] Training artifacts are saved and reproducible
- [x] Second full end-to-end scan checkpoint passes across Phases 5-6

---

## Phase 7: Evaluation and Reliability Hardening

### Objective

Compare heuristics, base model, and fine-tuned model while hardening the system against likely failures.

### Deliverables

- [x] evaluation harness working
- [x] baseline comparison table working
- [x] human actionability rubric working
- [x] null-scene report working
- [x] failure-injection tests working

### In-Scope / Out-of-Scope

- **In scope:** comparative evaluation, threshold tuning, reliability testing
- **Out of scope:** long-form scientific paper claims

### Dependencies

- **Requires:** stable base and fine-tuned inference paths
- **Blocks:** credible demo and submission narrative

### Parts in This Phase

- `7.1` Quantitative evaluation
- `7.2` Human usefulness and explainability review
- `7.3` Failure mode and threshold tuning

### Phase Exit Criteria

- [x] Heuristic, base, and fine-tuned comparisons are available
- [x] Null-scene performance is explicitly reported
- [x] Invalid JSON, empty candidates, Mapbox API failures, and slow inference are tested
- [x] Reliability results feed demo wording and claims
- [x] Integration checkpoint with prior phases passes

---

## Phase 8: Watchlist UI, Review Workflow, and Export

### Objective

Build the operator-facing React UI that makes the product feel real, operational, and demo-ready.

### Deliverables

- [x] watchlist screen
- [x] site detail screen
- [x] evidence panel view
- [x] review and publication controls
- [x] export flow for incident evidence

### In-Scope / Out-of-Scope

- **In scope:** core operator UX and demo flow
- **Out of scope:** full workflow automation or enterprise administration

### Dependencies

- **Requires:** stable backend and incident contracts
- **Blocks:** final demo polish

### Parts in This Phase

- `8.1` Watchlist-first triage experience
- `8.2` Site drill-down and evidence view
- `8.3` Review controls and evidence export

### Phase Exit Criteria

- [x] Critical screens render from real API responses
- [x] Manual smoke path works for frozen demo sites
- [x] Frontend smoke tests pass for key routes
- [x] Cached demo mode works
- [x] Third full end-to-end scan checkpoint passes across Phases 7-8

---

## Phase 9: Deployment, Demo Stability, and Submission Assets

### Objective

Package the system into a robust hackathon submission with stable runtime, polished story, and clear evidence of fine-tuning and product value.

### Deliverables

- [ ] deployment path finalized
- [ ] demo script finalized
- [ ] screenshots and fallback assets prepared
- [ ] architecture and benchmark slides prepared
- [ ] production secrets contract finalized for SimSat, Mapbox, Hugging Face, and Modal
- [ ] submission package finalized

### In-Scope / Out-of-Scope

- **In scope:** runtime stability, documentation, demo, and submission readiness
- **Out of scope:** broad product expansion

### Dependencies

- **Requires:** working system and evaluation outputs
- **Blocks:** final submission quality

### Parts in This Phase

- `9.1` Deployment and environment hardening
- `9.2` Demo preparation and fallback assets
- `9.3` Submission materials and final smoke checks

### Phase Exit Criteria

- [ ] Live demo path works
- [ ] Cached fallback demo path works
- [ ] SimSat, Mapbox, Hugging Face, and Modal secrets are validated in deployment profile
- [ ] Final smoke tests pass
- [ ] Submission claims match measured evidence
- [ ] No unresolved P1 defects remain

---

## 7) Detailed Part Breakdown

This section turns the phase map into implementation-grade parts. Each part is intentionally small enough to be decomposed into execution cards and large enough to represent a meaningful integration boundary.

### 7.1 Phase 1 Parts - Foundation Lock

| Part | Why | In Scope | Key Outputs | Verification | Integration Gate |
|---|---|---|---|---|---|
| `1.1` Product and workflow lock | Prevents scope drift before implementation starts | watchlist-first workflow, human review state, incident lifecycle, operator action definition | frozen workflow diagram, incident state model, MVP/non-goal list | manual walkthrough of primary user flow, incident-state schema test | Phase 1 cannot close unless all downstream contracts use the same workflow assumptions |
| `1.2` Data and schema contract lock | Prevents backend / ML / UI drift | `Site`, `ImageAsset`, `Candidate`, `EvidencePanel`, `Incident`, `ReviewAction`, enums | schema definitions, JSON examples, field dictionary, `openapi.json` draft | schema snapshot tests, example payload validation | All later phases must consume the same field names and enum values |
| `1.3` Testing and integration policy lock | Forces quality discipline early | test pyramid, golden fixture classes, live/cached policy, E2E cadence | testing charter, fixture matrix, phase-close checklist | checklist review, test scaffold placeholder | No later phase is marked done without adopting the policy |

### 7.2 Phase 2 Parts - Site Registry, Imagery, and Cache

| Part | Why | In Scope | Key Outputs | Verification | Integration Gate |
|---|---|---|---|---|---|
| `2.1` Site registry and watchlist model | All workflows begin at the site layer | site CRUD, watchlist listing, metadata storage, optional polygon support | site table, register/list endpoints, frozen demo-site manifest | API contract tests, DB schema tests | UI and scan logic must both read the same registry records |
| `2.2` SimSat and Mapbox imagery adapters | Makes the product actually dependent on DPhi imagery and required context inputs, not mock assets alone | current Sentinel retrieval, historical Sentinel retrieval, required Mapbox retrieval | adapter module, retrieval error handling, normalized responses | adapter tests against cached/live fixtures | Candidate pipeline must run off adapter outputs without ad hoc reshaping |
| `2.3` Cache and image asset persistence | Protects the demo and reduces repeated failures | local asset cache, image metadata persistence, replay mode | cache paths, asset records, cache invalidation rules | cached replay test, missing-data fallback test | One site scan must succeed with zero live calls after warm cache |

### 7.3 Phase 3 Parts - Candidate Generation and Zone Priors

| Part | Why | In Scope | Key Outputs | Verification | Integration Gate |
|---|---|---|---|---|---|
| `3.1` Heuristic anomaly generation | Gives the system a dependable first candidate stage | spectral anomaly rules, thresholding, bbox proposal from SimSat-fed assets | heuristic engine, score fields, candidate examples | candidate unit tests, golden positive/negative checks | Candidate object must be ingestible by panel builder without manual edits |
| `3.2` Temporal recurrence features | Helps distinguish transient noise from persistent suspicion | historical comparison, recurrence scoring, cloud penalties, and source provenance of current/historical imagery | temporal feature calculator, recurrence score, diagnostics metadata | recurrence tests on cached history, cloudy-scene regression tests | Candidate scoring must include historical context in stable field names |
| `3.3` Zone prior and candidate scoring | Makes the product operational rather than generic | coarse zones, facility heuristics, ranking, and required Mapbox-context dependency in scan path | `likely_source_zone_prior`, `candidate_score`, zone rationale | schema tests, manual review on demo sites, one live-path smoke scan | Incident model must consume candidate priors directly |

### 7.4 Phase 4 Parts - Evidence Panels and Prompt Contract

| Part | Why | In Scope | Key Outputs | Verification | Integration Gate |
|---|---|---|---|---|---|
| `4.1` Panel composition pipeline | The VLM only works if evidence is consistently shaped | current crop, methane-sensitive composite, temporal difference, required Mapbox, metadata | panel builder, deterministic layout, saved panel assets | panel render regression tests, cached fixture panel snapshots | Same panel spec must be used for inference, training, and demo |
| `4.2` Prompt and metadata contract | Freeze the language interface before training | system prompt, user prompt, metadata block, task instructions | prompt templates, metadata serializer | prompt formatting tests, sample schema-validation runs | Fine-tuning cannot begin until this contract is frozen |
| `4.3` Output schema and retry policy | Keeps model behavior bounded | schema validator, retry logic, fallback normalization | typed output validator, retry rules, invalid-output handler | invalid JSON failure test, canned-response normalization test | Incident persistence must only accept validated outputs |

### 7.5 Phase 5 Parts - Base Model Inference and Incident Pipeline

| Part | Why | In Scope | Key Outputs | Verification | Integration Gate |
|---|---|---|---|---|---|
| `5.1` Base inference runner | Establishes the prompt-only baseline before tuning | Hugging Face model loading, inference invocation, deterministic config | base inference module, latency logging, model-revision config | smoke inference test, schema-valid output test | Must run on the exact same panel format as Phase 4 |
| `5.2` Incident normalization and review flow | Product value depends on usable incident objects | review states, priority tier, severity tier, recommended action, confidence normalization | incident assembler, state machine, follow-up rules | state-transition tests, enum validation tests | UI and export layers must read the same normalized object |
| `5.3` Structured persistence and retrieval | Makes the backend a real product surface | incident storage, result retrieval, evidence retrieval | incidents table, result endpoints, audit metadata | endpoint tests, persistence regression tests | Watchlist and site detail endpoints must render directly from saved incidents |

### 7.6 Phase 6 Parts - Dataset Build and Fine-Tuning

| Part | Why | In Scope | Key Outputs | Verification | Integration Gate |
|---|---|---|---|---|---|
| `6.1` Dataset assembly and provenance | Prevents training chaos and unverifiable claims | manifests, split membership, label source tracking, panel version tracking | dataset manifest v1, split files, provenance schema | manifest validation script, duplicate/leakage checks | Demo split and validation split must be frozen before training |
| `6.2` Annotation rules and negative set | Label consistency matters more than dataset size | annotation handbook, negative taxonomy, bbox guidance, plume-likely criteria | annotation guide, reviewer checklist, negative set targets | inter-pass consistency review, negative coverage audit | Training should not proceed until guidelines exist and are applied |
| `6.3` Fine-tuning run and checkpointing | Creates the quality-improvement story | LoRA config, Modal GPU training script, adapter artifacts, evaluation hooks | train script, adapter checkpoint, Modal run metadata | train smoke test, post-train inference smoke test | Fine-tuned model must drop into the same inference contract as the base model |

### 7.7 Phase 7 Parts - Evaluation and Reliability Hardening

| Part | Why | In Scope | Key Outputs | Verification | Integration Gate |
|---|---|---|---|---|---|
| `7.1` Quantitative evaluation | Gives objective evidence for judging and iteration | heuristics vs base vs tuned comparisons, held-out sites, held-out dates | benchmark table, metric reports, threshold sweep notes | evaluation harness tests, split integrity tests | Same fixture and split policy must be respected across all comparisons |
| `7.2` Human usefulness and explainability review | Product quality is not captured by one numeric metric | actionability rubric, explainability rubric, reviewer notes | human review form, scored examples, summary table | manual rubric completion on validation slice | Results must feed demo claims and not sit in isolation |
| `7.3` Failure mode and threshold tuning | Reliability wins hackathons | invalid JSON, empty candidates, Mapbox API failures, slow inference, null scenes | failure-injection suite, tuned confidence thresholds, degradation policy | targeted failure tests, null-scene report | UI and backend must handle all tested failures without collapsing |

### 7.8 Phase 8 Parts - Watchlist UI, Review Workflow, and Export

| Part | Why | In Scope | Key Outputs | Verification | Integration Gate |
|---|---|---|---|---|---|
| `8.1` Watchlist-first triage experience | This is the product's strongest narrative frame | multi-site list, incident status, priority ordering, quick glance metadata | watchlist screen, site ranking logic | manual watchlist walkthrough, frontend smoke test | Data must come from real API payloads, not static placeholders |
| `8.2` Site drill-down and evidence view | Needed to explain why an alert exists | imagery panels, bbox overlay, evidence summary, history slice | site detail screen, evidence pack UI | drill-down render test, overlay smoke test | Evidence panel fields must match backend payloads exactly |
| `8.3` Review controls and evidence export | Makes the system feel like an operations tool | confirm/dismiss/review state changes, export card or markdown/PDF | review actions UI, export endpoint, export template | review action test, export smoke test | Review state changes must persist and reflect in watchlist immediately |

### 7.9 Phase 9 Parts - Deployment, Demo Stability, and Submission Assets

| Part | Why | In Scope | Key Outputs | Verification | Integration Gate |
|---|---|---|---|---|---|
| `9.1` Deployment and environment hardening | Prevents demo-day surprises | env var handling, compose scripts, startup commands, model path config, mandatory SimSat/Mapbox/HuggingFace/Modal secrets wiring | `.env.example`, startup docs, deployment profile | startup smoke test, dependency checklist | Live and cached demo paths must both boot cleanly |
| `9.2` Demo preparation and fallback assets | Judges see stability first | frozen screenshots, cached outputs, architecture slides, script | demo script, fallback images, known-good JSON outputs | rehearsal checklist, timed dry run | Cached mode must fully support the demo narrative |
| `9.3` Submission materials and final smoke checks | The last mile matters | README polish, benchmark summary, fine-tuning notes, repo cleanup | submission pack, final smoke report, claim check | final full walkthrough, repo sanity check | No claim in the submission may exceed measured evidence |

### 7.10 Cross-Phase Integration Gates

The full build should pass these hard checkpoints:

1. **Checkpoint A (after Phase 2):** site registry + imagery + cache can fetch and replay one demo site.
2. **Checkpoint B (after Phase 4):** one site can produce a candidate and a renderable evidence panel (including Mapbox context) from live and cached assets.
3. **Checkpoint C (after Phase 6):** base and fine-tuned models can both consume the same panel and schema contract end to end.
4. **Checkpoint D (after Phase 8):** watchlist UI can render and review incidents from real backend data in cached mode.
5. **Checkpoint E (after Phase 9):** full demo succeeds in live mode and cached fallback mode.

---

## 8) Task Input Contract for LLM (Critical)

Use this contract for every implementation card.

- **Task ID:**
- **Objective (1 sentence):**
- **Context files/links:**
- **Allowed files to change:**
- **Do-not-touch files:**
- **Constraints:**
- **Expected output:**
- **Acceptance tests/checks:**
- **Definition of done:**

### Prompt Skeleton

`You are implementing Task <ID>.`

`Goal: <objective>.`

`Context: <key files and constraints>.`

`Make the smallest safe change.`

`Then run/describe verification: <tests/lint/typecheck/smoke path>.`

`Return: summary, files changed, why, and verification results.`

---

## 9) Execution Protocol (LLM + Human)

1. Work on the smallest task that moves the system forward.
2. Freeze contracts early; avoid changing schemas casually once training or UI wiring starts.
3. Build one canonical path before supporting alternatives.
4. Add a cached offline path whenever a live dependency is introduced.
5. Verify immediately after each task.
6. Close every phase with an integration checkpoint.
7. Run one full end-to-end scan after every two phases.
8. If a task exceeds 45 minutes, split it.
9. If a live dependency becomes unstable, preserve momentum through cached artifacts and keep moving.
10. Do not promote demo claims beyond measured evidence.

### 9.1 Integration Rule

No phase is marked done unless it satisfies:

- local functionality,
- previous-phase compatibility,
- one live path,
- one cached offline path,
- and documented verification.

---

## 10) Verification Matrix

| Category | Check | Tool/Method | Frequency | Pass/Fail |
|---|---|---|---|---|
| Functional | Site scan returns valid incident object | API + schema tests | Every relevant task |  |
| Quality | Lint / typecheck / formatting | Local CI commands | Every task touching code |  |
| Contract | API matches `openapi.json` | Contract tests + schema diff | Every API change |  |
| Data | Manifests, splits, provenance valid | Dataset validation script | Every dataset update |  |
| Candidate Reliability | Positive/negative fixture behavior | Golden fixture tests | Per candidate change |  |
| Model Output | JSON validity and enum correctness | Pydantic validation + retry tests | Every inference change |  |
| Integration | End-to-end scan across current stack | Live + cached scan test | Every phase / 2 phases |  |
| Frontend | Key screens render and bind data | Basic smoke tests + manual QA | Per UI milestone |  |
| Failure Handling | Mapbox API failures, empty candidates, slow model, invalid JSON | Failure-injection tests | Per major milestone |  |
| Demo Readiness | Frozen demo path completes reliably | Rehearsal checklist | Before submission |  |

### 10.1 Test Pyramid for This Project

- **Unit tests**
  - schema validators
  - bbox normalization
  - candidate scoring helpers
  - panel builder helpers
  - prompt formatting
  - review state transitions

- **Integration tests**
  - SimSat adapter + cache
  - candidate pipeline + panel builder
  - inference + schema validator
  - API endpoints + DB layer
  - UI fetch + render path against mocked or cached backend responses

- **End-to-end tests**
  - one positive-site live scan
  - one positive-site cached scan
  - one negative-site cached scan
  - one cloudy / missing-data graceful-degradation path

### 10.2 Golden Fixtures (Mandatory)

Maintain at least:

- one positive site,
- one negative site,
- one cloudy site,
- one missing-data site.

These fixtures are shared across backend, evaluation, and demo validation.

---

## 11) Progress Tracker

Status legend: `TODO | WIP | BLOCKED | DONE`

- [x] ✅ Phase 1 - Foundation Lock
- [x] ✅ Phase 2 - Site Registry, Imagery, and Cache
- [x] ✅ Phase 3 - Candidate Generation and Zone Priors
- [x] ✅ Phase 4 - Evidence Panels and Prompt Contract
- [x] ✅ Phase 5 - Base Model Inference and Incident Pipeline
- [x] ✅ Phase 6 - Dataset Build and Fine-Tuning
- [x] ✅ Phase 7 - Evaluation and Reliability Hardening
- [x] âœ… Phase 8 - Watchlist UI, Review Workflow, and Export
- [ ] Phase 9 - Deployment, Demo Stability, and Submission Assets

---

## 12) Change Log

| Date | Task ID | Files Changed | Summary | Verification | Status |
|---|---|---|---|---|---|
| `2026-04-19` | `PLAN-CHUNK-01` | `LandfillSentry_Ops_Master_Project_Plan.md` | Initialized master plan with strategy, architecture, phase map, and verification framework | Manual review against frozen decisions and source reports | `done` |
| `2026-04-19` | `PLAN-FULL-DRAFT` | `LandfillSentry_Ops_Master_Project_Plan.md` | Expanded plan into full draft with detailed phase parts, operational deep dive, execution wave, data governance, API spec, evaluation plan, UX, deployment, GTM, and risk matrix | Manual structural review for completeness against detailed report and frozen answers | `done` |
| `2026-04-19` | `PHASE1-IMPLEMENTATION` | `README.md`, `openapi.json`, `docs/*`, `apps/api/*`, `tests/*`, `assets/demo_sites/*`, `scripts/*` | Implemented Phase 1 foundation lock artifacts: repo skeleton, schema and enum contracts, API scaffold, OpenAPI draft, demo-site selection rubric, golden fixture matrix, and integration checklist | `python -m unittest tests/test_api_contract.py`, `python -m unittest tests/test_schema_validation.py`, `python -m compileall apps scripts` | `done` |
| `2026-04-19` | `PLAN-MANDATORY-DEPENDENCIES` | `LandfillSentry_Ops_Master_Project_Plan.md` | Updated plan to make Mapbox, Hugging Face, and Modal GPU mandatory; aligned phase deliverables, part breakdowns, deployment/security requirements, and execution cards | Manual consistency review across sections 3, 6, 7, 16, and 17 | `done` |
| `2026-04-19` | `PHASE2-IMPLEMENTATION` | `apps/api/main.py`, `apps/api/routes/api.py`, `apps/api/runtime.py`, `apps/api/config.py`, `apps/api/db/*`, `apps/api/services/*`, `scripts/fetch_site_history.py`, `tests/test_phase2_integration.py`, `openapi.json`, `.env.example`, `README.md`, `LandfillSentry_Ops_Master_Project_Plan.md` | Implemented Phase 2: SQLite-backed site registry, SimSat+Mapbox adapters, cache/replay flow, and persisted scan evidence path | `python -m unittest tests/test_api_contract.py`, `python -m unittest tests/test_schema_validation.py`, `python -m unittest tests/test_phase2_integration.py`, `python -m compileall apps scripts tests` | `done` |
| `2026-04-19` | `PHASE2-SIMSAT-REPO-INTEGRATION` | `apps/api/config.py`, `apps/api/services/imagery_service.py`, `.env.example`, `README.md`, `tests/test_phase2_integration.py` | Aligned live imagery implementation to DPhi SimSat repository API contract using `/data/image/sentinel` and `/data/image/mapbox` endpoints and metadata headers | `python -m unittest tests/test_api_contract.py tests/test_schema_validation.py tests/test_phase2_integration.py`, `python -m compileall apps scripts tests` | `done` |
| `2026-04-20` | `PHASE3-IMPLEMENTATION` | `apps/api/services/candidate_service.py`, `apps/api/routes/api.py`, `apps/api/runtime.py`, `apps/api/db/repository.py`, `apps/api/services/__init__.py`, `tests/test_phase3_candidates.py`, `LandfillSentry_Ops_Master_Project_Plan.md` | Implemented Phase 3 hybrid candidate engine with heuristic anomaly scoring, temporal recurrence features, zone priors, candidate persistence, and scan/evidence integration | `python -m unittest tests/test_api_contract.py tests/test_schema_validation.py tests/test_phase2_integration.py tests/test_phase3_candidates.py`, `python -m compileall apps scripts tests` | `done` |
| `2026-04-20` | `SIMSAT-ENDPOINT-ALIGNMENT` | `apps/api/services/imagery_service.py`, `tests/test_phase2_integration.py`, `README.md` | Updated live endpoint usage to SimSat contract split: current inference (`/data/current/image/sentinel`, `/data/current/image/mapbox`) plus historical Sentinel retrieval (`/data/image/sentinel`) for temporal and fine-tuning workflows | `python -m unittest tests/test_api_contract.py tests/test_schema_validation.py tests/test_phase2_integration.py tests/test_phase3_candidates.py`, `python -m compileall apps scripts tests` | `done` |
| `2026-04-20` | `PHASE3-LIVE-DATA-ALIGNMENT` | `LandfillSentry_Ops_Master_Project_Plan.md` | Updated Phase 3 plan details to explicitly require and verify live candidate operation using SimSat current/historical Sentinel and required current Mapbox context, while retaining cached fallback behavior | Manual consistency review across sections 6, 7.3, 11, 12, and 17 (`3.1` card) | `done` |
| `2026-04-20` | `PHASE4-IMPLEMENTATION` | `apps/api/routes/api.py`, `apps/api/runtime.py`, `apps/api/db/repository.py`, `apps/api/services/panel_service.py`, `apps/api/services/prompt_contract_service.py`, `apps/api/services/output_validation_service.py`, `apps/api/services/__init__.py`, `tests/test_phase4_panels.py`, `LandfillSentry_Ops_Master_Project_Plan.md` | Implemented Phase 4 deterministic evidence panel builder, required Mapbox panel slot integration, frozen prompt/output contract metadata, and incident output schema validation loop with retry trace persisted in scan evidence | `python -m unittest tests/test_api_contract.py tests/test_schema_validation.py tests/test_phase2_integration.py tests/test_phase3_candidates.py tests/test_phase4_panels.py`; live scan smoke check via `scan_site` with SimSat backend | `done` |
| `2026-04-20` | `PHASE5-IMPLEMENTATION` | `apps/api/config.py`, `apps/api/runtime.py`, `apps/api/routes/api.py`, `apps/api/services/inference_service.py`, `apps/api/services/__init__.py`, `tests/test_phase5_inference.py`, `scripts/run_lfm25_examples.py`, `requirements.txt`, `.env.example`, `.env.local`, `README.md`, `LandfillSentry_Ops_Master_Project_Plan.md` | Implemented Phase 5 base-model inference pipeline with Hugging Face model loading (`LiquidAI/LFM2.5-VL-450M@main`), prompt-only image inference integration, structured output validation/fallback, persisted incident/review lifecycle support, and inference metadata trace in evidence payloads | `python -m unittest tests/test_api_contract.py tests/test_schema_validation.py tests/test_phase2_integration.py tests/test_phase3_candidates.py tests/test_phase4_panels.py tests/test_phase5_inference.py`; live end-to-end `scan_site` run with `INFERENCE_MODE=live`; `python scripts/run_lfm25_examples.py --max-new-tokens 24` | `done` |
| `2026-04-21` | `PHASE8-IMPLEMENTATION` | `apps/api/main.py`, `apps/api/db/repository.py`, `apps/api/routes/api.py`, `apps/web/public/ops.html`, `apps/web/public/ops.css`, `apps/web/public/ops-app.jsx`, `apps/web/README.md`, `tests/test_phase8_ui_workflow.py`, `README.md`, `LandfillSentry_Ops_Master_Project_Plan.md` | Implemented Phase 8 operator UX and workflow: watchlist API + screen, site drill-down evidence view, persisted review controls, incident export endpoint (markdown/json), and `/ops` console route with frontend smoke coverage | `python -m unittest tests/test_phase8_ui_workflow.py`; `python -m unittest tests/test_api_contract.py tests/test_schema_validation.py tests/test_phase2_integration.py tests/test_phase3_candidates.py tests/test_phase4_panels.py tests/test_phase5_inference.py tests/test_phase6_training.py tests/test_phase7_evaluation.py tests/test_phase7_reliability.py tests/test_phase8_ui_workflow.py`; `python -m compileall apps scripts tests` | `done` |

---

## 13) Blockers & Decisions Log

### Active Blockers

- Blocker: No active Phase 8 blockers
- Next action: begin Phase 9 (`9.1` deployment and environment hardening)
- ETA: `Phase 9`

### Key Decisions

- Decision: operator-first product
- Why chosen: clearest action loop and strongest demo fit
- Impact: watchlist triage and source-zone guidance become core UX

- Decision: synchronous inference for MVP
- Why chosen: simplest stable path under hackathon constraints
- Impact: caching and precomputation become essential

- Decision: phase completion requires integration
- Why chosen: reduces end-stage collapse risk
- Impact: more frequent checkpoints and fewer isolated branches

---

## 14) Release & Rollback Plan

- **Release strategy:** `single MVP release with cached demo fallback`
- **Pre-release checklist:**
  - [ ] Demo sites frozen
  - [ ] Golden fixtures frozen
  - [ ] Fine-tuned or fallback prompt-only path selected
  - [ ] Cached offline demo path validated
  - [ ] All required secrets documented in `.env.example`
- **Rollback criteria:**
  - Prompt-only model outperforms or stabilizes better than tuned model
  - Live dependency threatens demo reliability
  - UI instability exceeds acceptable demo risk
- **Rollback steps:**
  - Revert to cached incident outputs and panels
  - Switch to prompt-only model path if fine-tuned path is unstable
  - Reduce optional features before reducing the core scan-to-incident workflow
- **Post-release validation:**
  - final smoke scan,
  - final watchlist walkthrough,
  - final export path check.

---

## 15) Post-Phase Retro Template

- What went well:
- What broke or drifted:
- What integration issue appeared:
- What should be frozen more aggressively next phase:
- What can be simplified:

---

## 16) Operational Deep Dive

### 16.1 External Data Sources and Their Role

| Dependency | MVP Role | Why It Exists in the System | MVP Criticality |
|---|---|---|---|
| `SimSat Sentinel-2` | primary multispectral imagery source | current and historical imagery for anomaly generation and temporal comparison | Required |
| `SimSat Mapbox` | required high-resolution context | sharper facility interpretation, stronger zone context, and demo grounding | Required |
| `LFM2.5-VL-450M` | vision-language interpretation model | turns evidence panels into structured incident objects | Required |
| `Hugging Face` | model and adapter artifact registry | canonical source for model revisions and fine-tuned adapter versions | Required |
| `Modal GPU` | training execution platform | reproducible LoRA fine-tuning runs under hackathon timelines | Required |
| `Project Eucalyptus` | benchmark and bootstrap asset source | methane-domain priors, synthetic plume generation ideas, optional candidate improvements | Recommended |
| `METER` | watchlist enrichment source | landfill site discovery and metadata support | Recommended |
| weather / wind sources | contextual enhancement only | future persistence interpretation and synthetic realism | Optional |

### 16.2 Internal Service Design

The internal design should remain modular without becoming prematurely microservice-heavy.

- **API Gateway / Orchestrator**
  - validates incoming requests,
  - coordinates retrieval, candidate generation, panel building, inference, and persistence.

- **Site Registry Service**
  - manages site metadata,
  - stores frozen demo-site list,
  - supports watchlist and optional polygons.

- **Imagery Service**
  - wraps SimSat calls,
  - normalizes metadata,
  - stores assets to cache,
  - surfaces cloud or missing-data signals.

- **Candidate Generation Service**
  - computes anomaly candidates,
  - adds recurrence and zone priors,
  - emits ranked candidates.

- **Panel Builder Service**
  - assembles evidence packs consistently,
  - writes panel assets to cache,
  - stores panel generator version metadata.

- **VLM Inference Service**
  - loads base or fine-tuned model,
  - runs structured prompting,
  - validates and retries outputs.

- **Incident Service**
  - normalizes model outputs,
  - computes review state,
  - publishes incidents to API consumers.

- **UI Service**
  - watchlist-first workflow,
  - site drill-down,
  - review and export actions.

### 16.3 End-to-End Data Flow

1. User opens the watchlist or requests a scan for a site.
2. Backend loads site coordinates and optional polygon.
3. Imagery service fetches current Sentinel-2 imagery and historical scenes via SimSat.
4. Mapbox context is fetched as a required panel input.
5. Preprocessing filters weak scenes and normalizes imagery metadata.
6. Candidate generator proposes one or more suspicious regions.
7. Panel builder assembles multimodal evidence.
8. Base or fine-tuned `LFM2.5-VL-450M` receives panel plus prompt.
9. Output is validated and normalized into an incident object.
10. Incident is stored as `proposed`.
11. UI displays the result to the operator.
12. Human review promotes incident to `published`, `dismissed`, or keeps it in `needs_review`.

### 16.4 Candidate Generation Pipeline

**Recommended MVP mode:** hybrid candidate generation

The candidate engine should combine:

- simple spectral anomaly screening,
- temporal differencing against recent acceptable scenes,
- coarse zone priors,
- optional model-assisted ranking where practical.

Candidate scoring features should include:

- anomaly intensity,
- temporal recurrence,
- cloud penalty,
- facility-center proximity or heuristic zone prior,
- panel confidence support fields.

Candidate output contract:

```json
{
  "candidate_id": "cand_001",
  "site_id": "LF_DEMO_001",
  "bbox_norm": [0.25, 0.15, 0.47, 0.32],
  "candidate_score": 0.71,
  "temporal_recurrence": 0.64,
  "cloud_penalty": 0.12,
  "likely_source_zone_prior": "active_face"
}
```

### 16.5 Evidence Panel Specification

The panel format must be frozen before fine-tuning.

Required components:

1. current RGB crop,
2. methane-sensitive spectral composite crop,
3. temporal-difference crop,
4. Mapbox context crop,
5. metadata text block,
6. candidate bbox and score metadata.

Metadata text should include:

- site id,
- timestamp requested,
- timestamp captured,
- cloud score,
- candidate score,
- recurrence score,
- zone prior,
- Mapbox request metadata and retrieval timestamp.

### 16.6 Incident Object and Enum Contract

Minimum required fields:

```json
{
  "incident_id": "inc_001",
  "site_id": "LF_DEMO_001",
  "analysis_time": "2026-04-19T11:15:00Z",
  "plume_likely": true,
  "confidence": 0.84,
  "bbox_norm": [0.32, 0.18, 0.56, 0.43],
  "likely_source_zone": "active_face",
  "persistence_score": 0.72,
  "priority_tier": "high",
  "severity_tier": "medium",
  "review_status": "proposed",
  "evidence_summary": "Recurring anomaly near the active working area across recent cloud-acceptable scenes.",
  "recommended_followup": "Inspect active face cover integrity and nearby gas capture within 24 hours.",
  "model_version": "lfm25vl450m-landfillsentry-lora-v1"
}
```

Recommended controlled enums:

- `likely_source_zone`: `active_face | gas_system | perimeter_or_unknown`
- `priority_tier`: `low | medium | high | urgent`
- `severity_tier`: `low | medium | high`
- `review_status`: `proposed | published | dismissed | needs_review`
- `feedback_status`: `confirmed | dismissed | needs_review | unresolved`

### 16.7 Dataset and Annotation Governance

#### Dataset design goals

- small but high-signal,
- provenance-aware,
- strong negative coverage,
- frozen demo and validation sets,
- consistent panel format between training and inference.

#### Sample sources

- real historical/current site panels from SimSat,
- synthetic plume overlays or derived methane-domain examples,
- weak labels from heuristic or candidate-stage confidence,
- manual labels on selected panels.

#### Required dataset metadata per sample

- `sample_id`
- `site_id`
- `timestamp`
- `split`
- `label_source`
- `panel_version`
- `candidate_version`
- `imagery_sources_present`
- `annotator_id`
- `notes`

Allowed `label_source` values:

- `manual`
- `weak`
- `synthetic`
- `mixed`

#### Split policy

- **Train:** mixed real + synthetic + weak data
- **Validation:** frozen real-heavy set
- **Demo:** frozen set reserved for product demo only
- Never fine-tune on demo examples

#### Negative example policy

Negative examples must explicitly include:

- null scenes with no obvious anomaly,
- cloud-heavy scenes,
- bright or reflective surfaces,
- visually complex landfill scenes that should not trigger high confidence,
- suspicious but ultimately unconvincing candidates.

#### Annotation rules

- `plume_likely = true` only when the evidence pack supports a plausible, spatially localizable suspicious region.
- Bounding boxes should be tight enough to indicate the suspicious region without pretending scientific precision.
- If zone attribution is weak, label `perimeter_or_unknown` instead of forcing a precise class.
- Annotators should prefer consistency over ambition.

### 16.8 Fine-Tuning Strategy

Recommended approach:

- start with prompt-only pipeline,
- freeze panel and prompt contracts,
- build a narrow supervised dataset,
- fine-tune with LoRA,
- compare against the base model on the same validation slices.

Suggested stage order:

1. synthetic and weakly labeled SFT bootstrap,
2. manual correction and validation refinement,
3. optional instruction polishing if time remains.

Training artifacts to save:

- adapter weights,
- training config,
- dataset manifest,
- eval summary,
- sample outputs,
- panel format version,
- prompt contract version.

### 16.9 Prompting and Output Rules

Prompt design principles:

- be explicit about structured output,
- reinforce that the product is triage, not quantification,
- constrain zone taxonomy and enum values,
- ask for concise evidence summaries,
- forbid unsupported claims.

Core output rules:

- JSON only or clearly parseable structured response,
- no extra narrative outside contract unless debugging mode is enabled,
- bbox normalized to `[x1, y1, x2, y2]`,
- confidence in `[0,1]`,
- persistence score in `[0,1]`.

### 16.10 Evaluation Framework

#### Baselines

1. candidate-only heuristic path
2. base `LFM2.5-VL-450M` with prompt-only inference
3. fine-tuned `LFM2.5-VL-450M`

#### Core metrics

| Metric | Why It Matters | Target Style |
|---|---|---|
| JSON validity rate | system reliability | directional target, ideally >95% on validation |
| Operator usefulness | product value | majority of reviewed outputs considered actionable |
| Null-scene false positive rate | trust preservation | explicitly minimized and reported |
| Zone accuracy / agreement | operational focus | improve over base prompt-only baseline |
| BBox quality | localization utility | useful, not necessarily scientifically perfect |
| Human explainability score | demo and trust | clearly understandable evidence chain |

#### Evaluation slices

- held-out sites,
- held-out dates,
- frozen demo set,
- golden negative set.

#### Human review rubric

Each reviewed incident should be scored on:

- actionability,
- clarity,
- plausibility,
- usefulness of follow-up guidance,
- trustworthiness of explanation.

### 16.11 Product UX and Demo Flow

Core screens:

1. **Watchlist**
   - prioritized sites,
   - alert count,
   - review status,
   - latest scan snapshot.

2. **Site Detail**
   - current incident summary,
   - candidate zone,
   - confidence,
   - priority,
   - review actions.

3. **Evidence Pack**
   - imagery panel,
   - bbox overlay,
   - evidence summary,
   - recommended follow-up,
   - export action.

Recommended demo sequence:

1. open watchlist,
2. show prioritized site list,
3. select a flagged site,
4. show current vs historical imagery and candidate zone,
5. explain how evidence is assembled,
6. show structured incident object,
7. review and publish or dismiss,
8. export evidence pack,
9. mention cached fallback and fine-tuning result briefly.

### 16.12 Backend API Specification

| Endpoint | Method | Purpose | MVP Status |
|---|---|---|---|
| `/health` | `GET` | runtime health | Required |
| `/sites` | `POST` | register a site | Required |
| `/sites` | `GET` | list watchlist sites | Required |
| `/sites/{id}` | `GET` | get site metadata | Recommended |
| `/sites/{id}/scan` | `POST` | run synchronous scan | Required |
| `/scans/{id}` | `GET` | get scan result | Required |
| `/scans/{id}/evidence` | `GET` | get evidence pack | Required |
| `/watchlist/scan` | `POST` | batch scan or precompute watchlist | Recommended |
| `/incidents/{id}/review` | `POST` | confirm, dismiss, needs review | Required |
| `/incidents/export` | `GET` | export JSON / markdown / PDF-ready payload | Required |

OpenAPI policy:

- generate `openapi.json`,
- commit it,
- regenerate when route or schema changes,
- block frontend drift against stale contracts.

### 16.13 Data Models

#### Site

- `site_id`
- `name`
- `lat`
- `lon`
- `country`
- `operator`
- `watchlist_enabled`
- `polygon_geojson` optional
- `metadata`

#### ImageAsset

- `asset_id`
- `site_id`
- `source`
- `timestamp_requested`
- `timestamp_captured`
- `cloud_cover`
- `bands`
- `local_path`
- `cache_key`

#### Candidate

- `candidate_id`
- `site_id`
- `job_id`
- `bbox_norm`
- `candidate_score`
- `temporal_recurrence`
- `cloud_penalty`
- `likely_source_zone_prior`

#### EvidencePanel

- `panel_id`
- `site_id`
- `candidate_id`
- `panel_version`
- `current_rgb_path`
- `spectral_composite_path`
- `temporal_diff_path`
- `mapbox_context_path`
- `metadata_json`

#### Incident

- `incident_id`
- `site_id`
- `job_id`
- `plume_likely`
- `confidence`
- `bbox_norm`
- `likely_source_zone`
- `persistence_score`
- `priority_tier`
- `severity_tier`
- `review_status`
- `feedback_status`
- `evidence_summary`
- `recommended_followup`
- `model_version`

#### EvaluationRecord

- `eval_id`
- `split`
- `site_id`
- `baseline_model`
- `candidate_model`
- `json_valid_rate`
- `incident_f1`
- `zone_accuracy`
- `bbox_iou`
- `human_usefulness_score`

### 16.14 Repository Structure

```text
landfillsentry-ops/
├── README.md
├── openapi.json
├── docs/
│   ├── architecture.md
│   ├── evaluation.md
│   ├── annotation-guide.md
│   └── demo-script.md
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── db/
│   └── web/
│       ├── src/
│       └── public/
├── ml/
│   ├── candidate_generation/
│   ├── panel_builder/
│   ├── vlm/
│   ├── training/
│   └── evaluation/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── cache/
│   ├── labels/
│   └── manifests/
├── scripts/
│   ├── fetch_site_history.py
│   ├── build_panels.py
│   ├── run_inference.py
│   ├── train_lora.py
│   └── benchmark_models.py
├── tests/
│   ├── fixtures/
│   ├── test_api.py
│   ├── test_candidates.py
│   ├── test_panels.py
│   ├── test_schema_validation.py
│   ├── test_inference_smoke.py
│   └── test_frontend_smoke.md
└── assets/
    ├── demo_sites/
    ├── screenshots/
    └── diagrams/
```

### 16.15 Deployment, Infrastructure, and Training

Recommended MVP runtime:

1. SimSat
2. Mapbox
3. Hugging Face (model registry/auth)
4. FastAPI backend
5. React frontend
6. optional separate model-serving container

Recommended local setup:

- Docker Compose for local services
- SQLite file in local volume
- filesystem cache for panel assets
- local or remote GPU path for inference

Recommended hosted setup:

- frontend on Vercel / Netlify,
- backend on Railway / Render / Fly.io or similar,
- training on Modal GPU (mandatory),
- inference on a GPU instance or local GPU depending demo constraints.

Inference strategy:

- first path: `Transformers`
- future path: `ONNX` or `GGUF` fallback

### 16.16 Security, Secrets, Licensing, and Usage Risk

Must document:

- SimSat base URL and credentials,
- Mapbox token,
- Hugging Face token,
- Modal token / workspace config and GPU runtime settings,
- model license constraints,
- Project Eucalyptus non-commercial or usage conditions if reused,
- dataset provenance,
- wording guardrails for real-site claims.

Minimum security checklist:

- `.env.example` committed,
- secrets never committed,
- cached artifacts reviewed for sensitive metadata,
- export outputs avoid overclaiming or legal language.

### 16.17 Competitor Positioning and Buyer Wedge

| System | Primary Mode | What It Does Well | LandfillSentry Difference |
|---|---|---|---|
| `WasteMAP` | transparency and decision support platform | broad waste methane visibility, scenario planning | LandfillSentry is site-operator-first and incident-oriented |
| `UNEP MARS` | detect / attribute / notify ecosystem | large-event notification and public-interest action chain | LandfillSentry is not a global notification system; it is a facility triage workflow |
| `Carbon Mapper` | emissions visibility and attribution | high-quality emissions detection and data products | LandfillSentry focuses on turning evidence into a workflow-ready incident object for operators |

Light GTM framing:

- **initial buyer wedge:** landfill operator or operator-adjacent environmental compliance lead
- **near-term value:** inspection prioritization and reviewable incident workflow
- **future expansion:** municipality dashboards, evidence export, insurer workflows, portfolio scoring

### 16.18 Risk Matrix

| Risk | Probability | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| SimSat imagery unavailable | Medium | High | freeze demo sites early, cache assets | cached demo path |
| cloud cover too high | Medium | Medium | cloud filters and historical selection | use last acceptable scene |
| candidate engine too noisy | Medium | High | thresholds, recurrence score, negatives | simpler ranking and stricter cutoffs |
| invalid model JSON | Medium | High | schema prompts, retries, validation | normalization fallback or reject |
| fine-tuning underdelivers | Medium | Medium | keep prompt-only baseline strong | demo prompt-only path |
| Mapbox API outage or quota exhaustion | Medium | High | retries, quota monitoring, and warm cached Mapbox artifacts for frozen sites | cached Mapbox context for demo path |
| overclaiming science | Medium | High | strict wording guardrails | reset narrative to triage copilot |
| demo runtime instability | Medium | High | cached panels and results | full offline demo path |

### 16.19 Post-Hackathon Roadmap

#### Phase 2 Productization

- better facility polygons and zone maps,
- asynchronous scans and queueing,
- stronger export formats,
- operator feedback analytics,
- improved threshold calibration.

#### Phase 3 Product Expansion

- municipality and compliance workflows,
- audit trail and evidence lifecycle,
- broader landfill portfolio monitoring,
- richer weather and wind context,
- active learning loop from operator feedback.

---

## 17) Initial Execution Wave

### 17.1 Compressed 14-Day Build Plan

| Window | Focus | Required Output |
|---|---|---|
| Days 1-2 | Foundation lock | schemas, repo structure, demo-site shortlist, OpenAPI draft |
| Days 3-4 | Site registry + imagery + cache | working live and cached imagery retrieval |
| Days 5-6 | Candidate engine + panel builder | renderable evidence panels from frozen sites |
| Days 7-8 | Base model incident pipeline | valid incident JSON and persistence |
| Days 9-10 | Dataset prep + LoRA training | dataset manifest and first tuned checkpoint |
| Days 11-12 | Evaluation + reliability | baseline comparison and failure tests |
| Days 13-14 | React UI + demo hardening | watchlist workflow, export, final demo path |

### 17.2 Recommended Initial Execution Cards

| Card ID | Title | Phase | Outcome |
|---|---|---|---|
| `EC-1-1-01` | Freeze incident schema and enums | `1.2` | stable contract for backend, ML, and UI |
| `EC-1-1-02` | Freeze review-state workflow | `1.1` | proposed / published / dismissed / needs_review lifecycle |
| `EC-1-2-01` | Draft and commit `openapi.json` | `1.2` | API contract baseline |
| `EC-1-3-01` | Define golden fixture matrix | `1.3` | positive / negative / cloudy / missing-data fixtures |
| `EC-1-3-02` | Select and freeze demo-site shortlist rubric | `1.1` | repeatable site-selection method |
| `EC-2-1-01` | Implement site registry table and routes | `2.1` | list/register/get sites |
| `EC-2-2-01` | Implement SimSat Sentinel retrieval adapter | `2.2` | current + historical Sentinel fetch |
| `EC-2-2-02` | Implement required Mapbox retrieval adapter | `2.2` | mandatory context path for every scan |
| `EC-2-3-01` | Implement image asset cache and replay | `2.3` | live/cached imagery modes |
| `EC-3-1-01` | Build first heuristic candidate scorer | `3.1` | candidate bbox and score |
| `EC-4-1-01` | Build evidence panel composer | `4.1` | stable panel output |
| `EC-5-1-01` | Run prompt-only base model end to end | `5.1` | first valid incident object |
| `EC-5-1-02` | Wire Hugging Face model auth and pinned revision load | `5.1` | reproducible model load path |
| `EC-6-3-02` | Run first LoRA training job on Modal GPU | `6.3` | mandatory training-platform proof |

### 17.3 Active Execution Cards (Recommended Starting Set)

### `1.2` Contract Freeze

### Card Identity

- **Card ID:** `EC-1-1-01`
- **Title:** `Freeze Incident Schema And Enums`
- **Phase/Part:** `1.2`
- **Status:** `DONE`

### Objective (1 sentence)

Define and freeze the `Incident` contract, enum values, and sample payloads so backend, ML, and frontend work from the same object.

### Scope Guardrails

- **In scope:** schema fields, enums, sample JSON, validation rules
- **Out of scope:** model inference implementation
- **Do not change:** product scope or phase structure

### Inputs

- Files/docs to read first: detailed report, answers doc, master plan sections `1-5`
- Assumptions: operator-first triage and review flow are frozen
- Dependencies/preconditions: none beyond planning baseline

### Allowed File Changes

- `docs/architecture.md`
- `apps/api/schemas/*`
- `openapi.json`

### Planned Output

- Expected code/artifact result: typed schema and example incident payload
- User-visible behavior/result: downstream features all speak the same language

### Verification

- Required checks: schema validation tests, example payload parse
- Acceptance criteria:
  - [x] Incident schema validates sample payloads
  - [x] Enums are explicitly frozen and documented
  - [x] Review-state fields exist

### Integration Check

- Previous phase dependency verified: `yes`
- Live path verified: `n/a`
- Cached path verified: `n/a`

### Timebox & Control

- **Hard stop at (+45 min):** `split card`

### `1.3` Testing Policy

### Card Identity

- **Card ID:** `EC-1-3-01`
- **Title:** `Define Golden Fixture Matrix`
- **Phase/Part:** `1.3`
- **Status:** `DONE`

### Objective (1 sentence)

Freeze the minimum fixture classes that all later tests and demo hardening will use.

### Scope Guardrails

- **In scope:** fixture taxonomy, storage convention, naming policy
- **Out of scope:** full fixture creation
- **Do not change:** core product thesis

### Verification

- Acceptance criteria:
  - [x] Positive fixture defined
  - [x] Negative fixture defined
  - [x] Cloudy fixture defined
  - [x] Missing-data fixture defined

### `2.1` Site Registry

### Card Identity

- **Card ID:** `EC-2-1-01`
- **Title:** `Implement Site Registry Endpoints`
- **Phase/Part:** `2.1`
- **Status:** `DONE`

### Objective (1 sentence)

Create site storage and API routes so the watchlist and scan pipeline have a stable source of truth for demo sites.

### Scope Guardrails

- **In scope:** register, list, get site
- **Out of scope:** complex auth, multi-tenant management
- **Do not change:** SQLite-first storage choice

### Verification

- Acceptance criteria:
  - [x] Site create endpoint works
  - [x] Site list endpoint works
  - [x] Site read endpoint works
  - [x] Contracts align with `openapi.json`

### `2.2` Imagery Adapter

### Card Identity

- **Card ID:** `EC-2-2-01`
- **Title:** `Implement SimSat Sentinel Adapter`
- **Phase/Part:** `2.2`
- **Status:** `DONE`

### Objective (1 sentence)

Fetch current and historical Sentinel-2 imagery from SimSat and normalize the response for downstream services.

### Scope Guardrails

- **In scope:** adapter, request params, response normalization, error handling
- **Out of scope:** candidate scoring
- **Do not change:** SimSat-first MVP assumption

### Verification

- Acceptance criteria:
  - [x] Current imagery fetch works for one demo site
  - [x] Historical imagery fetch works for one demo site
  - [x] Missing-data path is handled cleanly

### `2.3` Cache Layer

### Card Identity

- **Card ID:** `EC-2-3-01`
- **Title:** `Implement Image Cache And Replay`
- **Phase/Part:** `2.3`
- **Status:** `DONE`

### Objective (1 sentence)

Persist fetched imagery and metadata so scans can replay without live dependency calls.

### Scope Guardrails

- **In scope:** cache directory layout, DB asset metadata, replay mode
- **Out of scope:** distributed caching
- **Do not change:** local-first MVP architecture

### Verification

- Acceptance criteria:
  - [x] Asset metadata persists
  - [x] Cached replay succeeds with live calls disabled
  - [x] Cache path integrates with fixture strategy

### `3.1` Candidate Heuristics

### Card Identity

- **Card ID:** `EC-3-1-01`
- **Title:** `Build First Candidate Scorer`
- **Phase/Part:** `3.1`
- **Status:** `DONE`

### Objective (1 sentence)

Produce at least one ranked candidate bbox and score from cached imagery using a simple stable heuristic path.

### Scope Guardrails

- **In scope:** simple anomaly rule, bbox proposal, score field
- **Out of scope:** learned ranking model
- **Do not change:** candidate object contract

### Verification

- Acceptance criteria:
  - [x] Candidate object validates
  - [x] Positive fixture produces a nontrivial candidate
  - [x] Negative fixture does not trigger high-confidence output
  - [x] Live scan path for candidate stage works with SimSat current/historical Sentinel plus required current Mapbox context

### `4.1` Evidence Panels

### Card Identity

- **Card ID:** `EC-4-1-01`
- **Title:** `Build Evidence Panel Composer`
- **Phase/Part:** `4.1`
- **Status:** `DONE`

### Objective (1 sentence)

Generate a deterministic evidence panel from imagery, candidate, and metadata that can be reused for both inference and training.

### Scope Guardrails

- **In scope:** image panel layout, metadata block, panel file output
- **Out of scope:** model inference
- **Do not change:** frozen panel contract once accepted

### Verification

- Acceptance criteria:
  - [x] Panel renders for one positive fixture
  - [x] Panel renders for one negative fixture
  - [x] Panel metadata includes required fields

### 17.4 Immediate Planning-to-Build Handoff

The very first implementation wave should stop only after this mini-checklist is true:

- `Incident` schema frozen
- golden fixture matrix frozen
- demo-site selection rubric frozen
- site registry running
- live and cached SimSat retrieval working
- first candidate object emitted
- first evidence panel rendered

At that point the plan has successfully crossed from architecture into working software.

---

## 18) Execution Card Template (Embedded)

### Card Identity

- **Card ID:** `EC-<phase>-<part>-<task>`
- **Title:** `<short action title>`
- **Phase/Part:** `<e.g., 2.2>`
- **Status:** `TODO | WIP | BLOCKED | DONE`

### Objective (1 sentence)

Describe exactly what must be true when this card is done.

### Scope Guardrails

- **In scope:**
- **Out of scope:**
- **Do not change:**

### Inputs

- Files/docs to read first:
- Assumptions:
- Dependencies/preconditions:

### Allowed File Changes

- `path/to/file1`
- `path/to/file2`

### Planned Output

- Expected code/artifact result:
- User-visible behavior/result:

### Verification

- Required checks (tests/lint/typecheck/run path):
- Acceptance criteria:
  - [ ] Criteria 1
  - [ ] Criteria 2

### Integration Check

- Previous phase dependency verified:
- Live path verified:
- Cached path verified:

### Timebox & Control

- **Started at:**
- **Checkpoint at (+25 min):**
- **Hard stop at (+45 min):**
- **If not done by hard stop:** `split card | mark blocked`

### Execution Log

- **Attempt 1:**
  - Summary:
  - Files changed:
  - Verification result:
  - Outcome: `continue | done | blocked`

### Completion

- **Ended at:**
- **Elapsed (minutes):**
- **Final status:** `DONE | BLOCKED | SPLIT`

---

## 19) Final Usage Pattern (Single File)

1. Use this file as the canonical planning artifact.
2. Treat sections `0-17` as the strategy-and-execution baseline.
3. Use section `17` to start work immediately.
4. Add more execution cards under section `18` as implementation expands.
5. Update the progress tracker after each completed phase or major card.
6. Update the change log after every meaningful planning or implementation milestone.
7. Treat integration checkpoints as hard gates, not advisory notes.
