# Phase Integration Checklist

Use this checklist before closing any phase.

- [ ] Previous-phase contracts remain unchanged or are explicitly versioned
- [ ] API contract still matches `openapi.json`
- [ ] Golden fixtures (`positive`, `negative`, `cloudy`, `missing_data`) still run
- [ ] Live execution path works for minimum smoke case
- [ ] Cached execution path works for minimum smoke case
- [ ] Failure behavior is user-readable and non-crashing
- [ ] Updated verification notes added to master-plan change log
