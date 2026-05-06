# LandfillSentry Ops Architecture (Phase 1 Freeze)

## Frozen MVP Workflow

1. Operator opens watchlist and selects a site.
2. Backend retrieves current and historical imagery.
3. Candidate generator proposes suspicious regions.
4. Panel builder creates evidence artifacts.
5. VLM inference produces structured incident JSON.
6. Incident is stored with `review_status=proposed`.
7. UI shows evidence, recommendation, and review controls.
8. Human review sets final state (`published`, `dismissed`, or `needs_review`).

## Incident Lifecycle (Frozen)

```text
proposed -> published
proposed -> dismissed
proposed -> needs_review
needs_review -> published
needs_review -> dismissed
needs_review -> needs_review
```

## MVP Scope (Frozen)

- watchlist-first workflow
- single-incident object with explainable fields
- human review before incident publication
- live and cached execution paths
- synchronous scan path for MVP

## Explicit Non-Goals (Phase 1)

- regulatory-grade quantification
- autonomous enforcement decisions
- enterprise multi-tenant administration
- full atmospheric inversion
- global generalized methane platform in MVP
