# Testing Charter (Phase 1 Lock)

## Purpose

Define mandatory testing and integration behavior for all phases.

## Test Pyramid

### Unit

- schema validation
- bbox normalization utilities
- candidate scoring helpers
- prompt formatting
- review-state transition checks

### Integration

- SimSat adapter + cache behavior
- candidate -> panel pipeline compatibility
- inference output -> schema validator
- API routes + DB layer
- web UI fetch/render against cached payloads

### End-to-End

- one positive-site live scan
- one positive-site cached scan
- one negative-site cached scan
- one cloudy or missing-data graceful path

## Golden Fixture Matrix (Mandatory)

- `positive`: expected anomaly candidate path
- `negative`: null-scene trust path
- `cloudy`: cloud-heavy degradation path
- `missing_data`: retrieval failure degradation path

Fixture root: `tests/fixtures/`

## Live + Cached Policy

- Every major capability must support both live and cached execution.
- Cached mode is required for demo resilience.
- Integration tests should verify equivalent schema outputs between live and cached paths.

## Phase-Close Quality Gate

No phase is marked complete unless:

- part-level acceptance checks pass,
- integration checkpoint for the phase passes,
- required fixture classes are still supported,
- contract drift against `openapi.json` is resolved.
