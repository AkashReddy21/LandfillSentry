# LandfillSentry Ops: Decision Log and Answers to Open Questions

Version: 1.0  
Purpose: This document answers the full question list for LandfillSentry Ops and freezes the recommended operating assumptions for the hackathon build. It is intended to act as the single decision file that aligns product, engineering, data, evaluation, and delivery.

---

## How to read this document

These answers are written as **recommended defaults**, not abstract options.  
The goal is to remove ambiguity so the team can start building immediately.

Where relevant, each answer includes:

- **Decision**: the recommended choice
- **Why**: short justification
- **Implementation effect**: what changes in the build plan because of this choice

---

# 1. Scope and Outcome

### 1. Is the primary goal to win the hackathon, build a real MVP, or create a startup-grade product plan?
**Decision:** The primary goal is to **win the hackathon with a real MVP**, while laying a credible foundation for a startup-grade product later.

**Why:** A hackathon winner needs a working product, not only slides. At the same time, the idea should feel commercially serious enough that judges believe it can grow beyond the event.

**Implementation effect:**  
- Prioritize a working end to end system over feature breadth  
- Keep architecture production-aware, but do not overbuild enterprise features  
- Include a short post-hackathon roadmap, but do not let it dominate MVP scope

---

### 2. Should the final plan optimize for hackathon execution over the next 7 to 14 days, or for a 2 to 3 month build after the hackathon?
**Decision:** Optimize primarily for **7 to 14 day execution**, with a compact 2 to 3 month extension path.

**Why:** The fastest way to lose is to design a beautiful plan that cannot be implemented in time.

**Implementation effect:**  
- Choose tools with low integration friction  
- Prefer simple pipelines, cached assets, and deterministic demos  
- Defer advanced quantification, multi-tenant systems, and deep workflow automation

---

### 3. Is the product definitely operator-first, or do you want municipality and compliance users treated as equal priority?
**Decision:** The product is **definitely operator-first**.

**Why:** Operators have the clearest action after an alert: inspect and mitigate. Municipality and compliance users are important, but they are better treated as secondary audiences for the first version.

**Implementation effect:**  
- UI language should focus on inspection priority and site action  
- Incident object should emphasize source zone and follow-up recommendations  
- Compliance export remains future work, not the main workflow

---

### 4. Do you want the master plan to stay hackathon-scoped, or include a serious post-hackathon roadmap too?
**Decision:** Include both, but with clear separation: **hackathon MVP first, post-hackathon roadmap second**.

**Why:** Judges like believable growth, but they score what exists now.

**Implementation effect:**  
- Main body focuses on MVP  
- Final section includes phase 2 and phase 3 roadmap  
- No roadmap item should be required to validate MVP success

---

### 5. Should the plan sound like a product strategy document, an engineering build plan, or both equally?
**Decision:** **Both equally**, with engineering slightly dominant.

**Why:** The team needs something buildable, but the demo and judging also require a crisp product story.

**Implementation effect:**  
- Include product framing, user workflow, pricing logic, and competitors  
- Include APIs, schemas, architecture, tests, milestones, and evaluation

---

### 6. What is the single most important thing judges and users should remember about LandfillSentry?
**Decision:**  
**LandfillSentry turns satellite imagery into an explainable methane incident object that tells operators where to inspect first.**

**Why:** This is clearer and stronger than saying “we detect methane” or “we built a dashboard.”

**Implementation effect:**  
- Every demo screen and API output should reinforce this sentence  
- Avoid generic Earth observation storytelling

---

# 2. User and Workflow

### 7. Who exactly is the primary user in your head?
**Decision:** The primary user is a **landfill operations manager** or site operations lead.

**Why:** This role has direct responsibility, understands site zones, and can act quickly.

**Implementation effect:**  
- Design screens for operational triage, not policy reporting  
- Use plain operational wording rather than policy-heavy terminology

---

### 8. What is the intended user action after an alert?
**Decision:** The intended action is: **inspect a zone on site**, then optionally log or escalate if needed.

**Why:** “Inspect the site” is too broad. “Inspect a zone” is actionable.

**Implementation effect:**  
- The incident object must include a likely source zone and priority tier  
- Recommendations should be site-action oriented

---

### 9. Do you want the product to prioritize single-site deep analysis or multi-site watchlist triage as the first-class workflow?
**Decision:** **Multi-site watchlist triage** should be the first-class workflow, with drill-down into single-site analysis.

**Why:** It feels more like a real product and is stronger in demo form. It also matches how operators or municipalities would prioritize scarce field effort.

**Implementation effect:**  
- Home view should be a watchlist of monitored sites  
- Clicking a site opens the incident timeline and evidence details

---

### 10. Should the incident object include only recommendation text, or also a structured priority and severity tier?
**Decision:** Include **structured priority and severity tiers** in addition to recommendation text.

**Why:** Structured outputs are easier for downstream systems and better for judge evaluation.

**Implementation effect:**  
- Add fields such as `priority_tier`, `severity_tier`, and `recommended_followup`  
- Use controlled enums rather than free text only

---

### 11. Do you want operator feedback in v1, such as confirmed, dismissed, or needs review?
**Decision:** **Yes**, but keep it minimal.

**Why:** Feedback closes the loop, enables future learning, and makes the product feel more real.

**Implementation effect:**  
- Add a simple status field: `confirmed`, `dismissed`, `needs_review`  
- Store feedback in the incident table  
- Do not build active learning automation yet

---

### 12. Should there be a human review step before any incident becomes official in the UI?
**Decision:** **Yes**, at least in v1.

**Why:** This is the safest and most defensible framing. The system is a triage copilot, not final truth.

**Implementation effect:**  
- Incidents first appear as `proposed`  
- Human action promotes them to `published` or `dismissed`

---

# 3. Geography and Demo Sites

### 13. Are you already committed to a specific country or region for demo sites?
**Decision:** No hard commitment. Use a **globally framed product** with a small curated demo set from regions where imagery and site context look clean.

**Why:** This avoids unnecessary geographic narrowing and lets you pick visually strong examples.

**Implementation effect:**  
- Product copy remains global  
- Demo dataset can include 3 to 5 sites from different regions if useful

---

### 14. Do you already have 3 to 5 demo landfill coordinates or polygons selected?
**Decision:** Not yet, but you **should select them early and freeze them**.

**Why:** Demo stability depends on fixed sites.

**Implementation effect:**  
- Define a frozen demo site list in the first implementation phase  
- Cache assets and panels for those sites

---

### 15. Are your demo sites meant to be real known landfill sites, or semi-fictionalized demo locations?
**Decision:** Use **real known landfill sites**, but present them carefully as demonstrative case study sites.

**Why:** Real sites increase credibility and make the demo feel grounded.

**Implementation effect:**  
- Use publicly observable sites  
- Avoid making legal claims about actual emissions without proper qualification

---

### 16. Do you want the plan to assume site polygons are available, or only point coordinates?
**Decision:** Assume **point coordinates are always available** and **polygons are optional enhancements**.

**Why:** Coordinates are easier to obtain consistently. Polygons improve zoning, but should not block the MVP.

**Implementation effect:**  
- MVP works with center point plus fixed buffer  
- Polygon-aware workflows can be layered later

---

### 17. Should we include a path for facility-zone priors such as active face, gas infrastructure, cover system, perimeter from day one?
**Decision:** **Yes, include the path from day one**, but only implement the simplest version in MVP.

**Why:** Source-zone reasoning is one of the most differentiated parts of the idea.

**Implementation effect:**  
- Start with coarse zone categories: `active_face`, `gas_system`, `perimeter_or_unknown`  
- Expand the taxonomy later

---

### 18. Do you want India-specific examples in the final plan, or keep it globally framed?
**Decision:** Keep the product **globally framed**, with optional India-specific examples in a note or appendix if desired.

**Why:** Global framing is stronger for the hackathon.

**Implementation effect:**  
- Do not anchor the entire pitch to India  
- Use India only if a selected demo site is visually strong or strategically relevant

---

# 4. Data and Labeling

### 19. How many labeled examples do you realistically think you can create before the deadline?
**Decision:** Plan for **80 to 200 usable labeled examples** total, depending on bandwidth.

**Why:** This is realistic for a hackathon-scale manual effort when combined with synthetic and weak labels.

**Implementation effect:**  
- Do not assume thousands of hand labels  
- Lean on candidate generation, synthetic overlays, and curated negatives

---

### 20. Will labels be created by you alone, or is there a team?
**Decision:** Assume **you are the primary labeler**, with optional support if teammates help.

**Why:** Planning around a team that may not deliver creates risk.

**Implementation effect:**  
- Annotation guidelines must be simple and fast  
- Labeling workflow should be optimized for one primary operator

---

### 21. Do you want synthetic plume data to be a major part of the training set, or just a bootstrap layer?
**Decision:** Synthetic plume data should be a **major bootstrap component**, but not the only component.

**Why:** Synthetic examples help coverage, especially early, but real examples and hard negatives are necessary for credibility.

**Implementation effect:**  
- Treat synthetic as a training accelerator  
- Keep validation and demo splits as real as possible

---

### 22. Do you want weak labels and manual labels tracked separately in the plan?
**Decision:** **Yes, absolutely.**

**Why:** Provenance matters for debugging and evaluation.

**Implementation effect:**  
- Every sample should have a `label_source` field  
- Allowed values: `manual`, `weak`, `synthetic`, `mixed`

---

### 23. Should negative examples be explicitly budgeted and tracked as a first-class dataset requirement?
**Decision:** **Yes.**

**Why:** Null scenes, false positives, and visually confusing negatives are crucial for this product.

**Implementation effect:**  
- Maintain a negative-example target in the dataset plan  
- Include clouds, smoke-like patterns, bright surfaces, and visually complex landfill scenes

---

### 24. Do you want a frozen validation split and a frozen demo split defined early?
**Decision:** **Yes.**

**Why:** Without frozen splits, the evaluation story becomes weak and the demo becomes unstable.

**Implementation effect:**  
- Define train, validation, and demo manifests early  
- Never fine-tune on the demo split

---

### 25. Should the plan include dataset versioning with manifests and provenance per sample?
**Decision:** **Yes.**

**Why:** This is worth the small setup cost.

**Implementation effect:**  
- Store manifest JSON or CSV files  
- Track site id, date, imagery source, label source, panel generator version, and split

---

### 26. Do you want annotation guidance written into the plan, including what counts as plume_likely and how bbox labels are set?
**Decision:** **Yes.**

**Why:** Consistency matters even with a small dataset.

**Implementation effect:**  
- Write a short annotation handbook  
- Include edge cases, confidence rules, and box placement guidance

---

# 5. Technical Choices

### 27. Is SimSat the only imagery path we should assume for MVP, or may the plan include fallback retrieval options?
**Decision:** **SimSat is the primary imagery path for MVP**, but the plan may mention fallback retrieval options as future or contingency paths.

**Why:** The hackathon explicitly centers SimSat and DPhi imagery.

**Implementation effect:**  
- All required MVP flows should work with SimSat only  
- Fallbacks should not be dependency blockers

---

### 28. Is Mapbox context mandatory for MVP, or optional if token and setup become painful?
**Decision:** Mapbox context is **strongly recommended but not mandatory**.

**Why:** It improves site grounding and demo quality, but the product should still run without it.

**Implementation effect:**  
- The pipeline must gracefully degrade if Mapbox is unavailable  
- Missing Mapbox becomes a tested failure mode, not a blocker

---

### 29. Do you want Project Eucalyptus integrated into MVP, or treated as a recommended enhancement or benchmark path?
**Decision:** Treat Project Eucalyptus as a **recommended benchmark and bootstrap path**, with selective integration where practical.

**Why:** It is valuable, but should not become an integration trap.

**Implementation effect:**  
- Reuse ideas, training assets, or post-processing patterns  
- Do not make MVP success depend on deep codebase coupling

---

### 30. Should candidate generation start heuristic-first, model-assisted-first, or hybrid from day one?
**Decision:** Use a **hybrid** approach from day one, but keep the heuristic layer simple and dependable.

**Why:** Pure heuristics may be brittle; pure model-first may be unstable. Hybrid is safer.

**Implementation effect:**  
- Start with spectral or temporal anomaly heuristics  
- Allow optional candidate ranking or refinement from learned components

---

### 31. Do you want FastAPI locked in as backend, or still open?
**Decision:** **Lock in FastAPI.**

**Why:** It is fast to build, easy to document, and good for typed JSON APIs.

**Implementation effect:**  
- Define API contracts early  
- Use FastAPI for both local and deployable backend modes

---

### 32. Do you want React for the web app, or would Streamlit be acceptable for the first shipping version?
**Decision:** **React for the primary web app**. Streamlit is acceptable only as an internal prototyping aid.

**Why:** Judges reward polished demos, and React gives better control.

**Implementation effect:**  
- Build a lightweight React app with a few strong screens  
- Keep Streamlit optional for internal analysis only

---

### 33. For storage, do you want SQLite first, or Postgres from the beginning?
**Decision:** Start with **SQLite**.

**Why:** It is enough for MVP and simpler to ship.

**Implementation effect:**  
- Use SQLModel or SQLAlchemy with migration-ready schema design  
- Keep schema compatible with later Postgres migration

---

### 34. Should inference be synchronous for MVP, or do you want background jobs and polling or websocket flow designed from the start?
**Decision:** Use **synchronous inference for MVP**, with small cached workflows. Background jobs can be a future upgrade.

**Why:** Synchronous flow is easier to reason about and demo.

**Implementation effect:**  
- API calls can block briefly during scan generation  
- Heavy jobs should be precomputed or cached

---

### 35. Do you want Transformers to be the only supported inference path in the first plan, or should we spec a fallback like ONNX or GGUF too?
**Decision:** Use **Transformers as the main path**, but mention ONNX and GGUF as deployment fallbacks.

**Why:** The first implementation needs one canonical path. Fallbacks are useful for later optimization and edge deployment narratives.

**Implementation effect:**  
- Build and test on one primary inference stack  
- Keep deployment abstraction thin so fallback export remains possible

---

# 6. Model and Evaluation

### 36. Is fine-tuning mandatory for success, or is prompt-only plus structured output acceptable as fallback?
**Decision:** Fine-tuning is **strongly preferred and should be treated as a major goal**, but prompt-only structured output is an acceptable fallback.

**Why:** The hackathon explicitly rewards domain fine-tuning. Still, a backup path is smart.

**Implementation effect:**  
- Build the system so base-model prompting works first  
- Add LoRA fine-tuning as the quality upgrade path

---

### 37. Which matters more for you: bbox quality, JSON validity, source-zone accuracy, persistence score quality, or operator usefulness?
**Decision:** The ranking should be:
1. **Operator usefulness**
2. **JSON validity**
3. **Source-zone accuracy**
4. **BBox quality**
5. **Persistence score quality**

**Why:** The product wins if the output is useful and reliable for action. A perfect score that nobody can act on is less valuable.

**Implementation effect:**  
- Evaluation should not be over-optimized on one visual metric  
- Human actionability scoring should be included

---

### 38. Do you want the plan to commit to numeric targets now, or keep some as provisional until we see real data?
**Decision:** Keep most targets **provisional**, with a few directional targets.

**Why:** Hard numeric claims made too early can backfire.

**Implementation effect:**  
- Use target ranges instead of rigid commitments  
- Example: JSON validity above 95 percent on validation set, null-scene false positive rate below a chosen threshold, but mark them as provisional

---

### 39. Should we evaluate on held-out sites, held-out dates, or both?
**Decision:** Evaluate on **both held-out sites and held-out dates**.

**Why:** Generalization matters across geography and time.

**Implementation effect:**  
- Create separate evaluation views  
- Report both temporal generalization and cross-site transfer

---

### 40. Do you want baseline comparison against base LFM2.5-VL-450M, candidate-only heuristics, and fine-tuned model all three?
**Decision:** **Yes, compare all three.**

**Why:** This creates a stronger scientific and product story.

**Implementation effect:**  
- Baseline A: heuristic or candidate-only  
- Baseline B: base LFM2.5-VL  
- Final: fine-tuned LFM2.5-VL

---

### 41. Should the plan include human scoring of actionability and explainability?
**Decision:** **Yes.**

**Why:** These are central to the product and often missed by purely technical metrics.

**Implementation effect:**  
- Add a small rubric for human review  
- Score whether the incident object is understandable and useful for follow-up

---

### 42. Do you want calibration or confidence-threshold tuning explicitly included?
**Decision:** **Yes, lightly.**

**Why:** Thresholds matter for operational usefulness.

**Implementation effect:**  
- Include simple threshold sweeps  
- Do not overcomplicate with heavy calibration research in MVP

---

### 43. Should no anomaly or null-scene performance be a major metric?
**Decision:** **Yes, it should be a major metric.**

**Why:** False positives will destroy trust quickly.

**Implementation effect:**  
- Track null-scene precision or false positive rate explicitly  
- Build a robust negative set

---

# 7. Testing and Integration

### 44. Do you want a formal rule that no phase is marked done until it passes an integration checkpoint with previous phases?
**Decision:** **Yes.**

**Why:** Integration failures kill hackathon projects.

**Implementation effect:**  
- Each phase closes only after a working end-to-end checkpoint

---

### 45. Should every phase end with one live path and one cached offline path?
**Decision:** **Yes.**

**Why:** Cached offline paths protect the demo and speed debugging.

**Implementation effect:**  
- Every major flow should have reproducible cached artifacts  
- Live and offline modes should both be supported

---

### 46. Do you want unit, integration, and end-to-end tests all explicitly planned in every phase?
**Decision:** **Yes**, but keep the scope pragmatic.

**Why:** This gives quality without going overboard.

**Implementation effect:**  
- Unit tests for helpers and parsers  
- Integration tests for API and inference contracts  
- At least one end-to-end scan test

---

### 47. Should we define golden fixtures for at least one positive site, one negative site, one cloudy site, and one missing-data site?
**Decision:** **Yes.**

**Why:** These become the backbone of reliability testing.

**Implementation effect:**  
- Freeze fixture data early  
- Use them across backend and UI tests

---

### 48. Do you want frontend smoke tests in the plan, or keep frontend verification manual for MVP?
**Decision:** Include **basic frontend smoke tests**, but keep most UI verification manual.

**Why:** A few smoke tests are worth it, full automation is not necessary for MVP.

**Implementation effect:**  
- Test critical render and API-wiring paths  
- Validate most styling and interactions manually

---

### 49. Should we include API contract tests and a committed openapi.json as part of the plan?
**Decision:** **Yes.**

**Why:** Strong APIs are part of the product thesis.

**Implementation effect:**  
- Generate and commit OpenAPI schema  
- Write contract tests for main endpoints

---

### 50. Do you want failure-injection tests for invalid JSON, empty candidates, missing Mapbox, and slow inference?
**Decision:** **Yes.**

**Why:** These are highly likely failures in the real build.

**Implementation effect:**  
- Add specific tests for each failure mode  
- UI must degrade gracefully

---

### 51. Should we require one full end-to-end scan after every 2 phases before advancing?
**Decision:** **Yes.**

**Why:** This keeps momentum aligned around a real working system.

**Implementation effect:**  
- Insert hard demo checkpoints throughout the build plan  
- No long isolated implementation branches

---

# 8. Delivery and Business Framing

### 52. Do you want the plan to include pricing, GTM, and buyer wedge in detail, or keep it mostly technical?
**Decision:** Include **light but serious GTM and buyer wedge detail**, while keeping the document mostly technical.

**Why:** The hackathon entry should sound commercially credible, but not become a sales deck.

**Implementation effect:**  
- Include buyer, pricing logic, and wedge narrative  
- Keep most pages focused on implementation and product design

---

### 53. Should the final plan explicitly position LandfillSentry relative to WasteMAP, UNEP MARS, and Carbon Mapper, or only lightly reference them?
**Decision:** **Explicitly position it relative to them.**

**Why:** Judges and future users will care about differentiation.

**Implementation effect:**  
- Add a concise competitor positioning section  
- Explain that LandfillSentry is an operator-first triage copilot, not a global methane data platform

---

### 54. Do you want the final plan to include security, secrets, licensing, and model and data usage risks?
**Decision:** **Yes.**

**Why:** These are practical startup and deployment concerns and make the document stronger.

**Implementation effect:**  
- Add a short security and risk section  
- Cover API tokens, model licenses, data licensing, and disclosure risks

---

### 55. Should we include a roadmap for compliance evidence export and regulator-facing workflows, or leave that as future work?
**Decision:** Include it as **future work on the roadmap**, not as MVP.

**Why:** It is valuable, but not necessary to win the hackathon.

**Implementation effect:**  
- Mention evidence export templates, audit trails, and regulator workflows in phase 2 or phase 3  
- Do not let them expand MVP scope

---

### 56. Do you want the final document to remain single-file like AdaptOpt, with appended execution cards and change log?
**Decision:** **Yes.**

**Why:** A single-file master document is easier to manage during a fast build.

**Implementation effect:**  
- Keep one canonical Markdown file  
- Append execution cards, assumptions, change log, and milestone updates at the end

---

# Recommended frozen defaults summary

This section compresses the decisions into one quick-reference view.

## Product
- Goal: Win the hackathon with a real MVP
- Product type: Operator-first methane incident triage copilot
- Core memory line: Turn satellite imagery into an explainable incident object telling operators where to inspect first

## User
- Primary user: Landfill operations manager
- Primary action: Inspect a likely source zone
- First-class workflow: Multi-site watchlist triage with single-site drill-down
- Human review: Required before incident is official
- Feedback loop: Minimal v1 support

## Geography
- Global framing
- Freeze 3 to 5 demo sites early
- Use real sites with careful wording
- Coordinates required, polygons optional

## Data
- 80 to 200 usable labeled examples target
- One primary labeler assumption
- Synthetic plumes: major bootstrap layer
- Weak and manual labels tracked separately
- Negative examples first-class
- Frozen validation and demo splits
- Dataset manifests and provenance required
- Annotation guidelines required

## Tech
- SimSat-first
- Mapbox recommended but optional
- FastAPI backend
- React frontend
- SQLite for MVP
- Synchronous inference first
- Transformers primary inference path
- ONNX or GGUF mentioned as future fallback

## Model
- Fine-tuning preferred, prompt-only fallback allowed
- Prioritize usefulness, valid JSON, and zone accuracy
- Numeric targets provisional
- Evaluate on held-out sites and dates
- Compare heuristics, base model, and fine-tuned model
- Include actionability and explainability review
- Include threshold tuning
- Track null-scene performance

## Testing
- Integration gate per phase
- Live plus cached path per phase
- Unit, integration, and end-to-end tests
- Golden fixtures required
- Basic frontend smoke tests
- OpenAPI contract committed
- Failure injection required
- Full end-to-end scan after every 2 phases

## Business and delivery
- Mostly technical document with light GTM
- Explicit competitor positioning
- Security, licensing, and secrets included
- Compliance export kept for roadmap
- Single-file canonical plan

---

# Suggested next action

The next document should convert these frozen answers into a **master execution plan** with:
1. phased milestones,
2. repo structure,
3. dataset schema,
4. API definitions,
5. evaluation table,
6. demo script,
7. execution cards,
8. change log.

This document is now the source of truth for those choices.
