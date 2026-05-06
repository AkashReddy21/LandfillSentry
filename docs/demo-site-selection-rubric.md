# Demo-Site Selection Rubric (Frozen in Phase 1)

## Goal

Select and freeze `3-5` landfill demo sites with reliable imagery access and clear storytelling value.

## Hard Filters (Must Pass)

- Site is a real landfill or operationally plausible landfill location.
- SimSat retrieval path is available for current and historical views.
- Site can support cached replay for demo fallback.
- Site metadata includes at least id, name, lat, lon, country.

## Scoring Rubric (100 Points)

- `30` Data availability and retrieval reliability
- `25` Visual signal separability (clear candidate-worthy regions)
- `15` Cloud resilience across recent history
- `15` Geographic diversity contribution
- `15` Demo narrative usefulness (operator actionability)

## Selection Process

1. Build shortlist of `8-12` candidate sites.
2. Score each site using the rubric in `assets/demo_sites/demo_site_selection_matrix.csv`.
3. Pick top `3-5` sites while preserving geographic diversity.
4. Freeze selected sites in `assets/demo_sites/frozen_demo_sites.template.json`.
5. Mark each frozen site as one of: `positive`, `negative`, `cloudy`, `missing_data`.

## Freeze Policy

- Frozen sites are not changed during a phase unless a blocker is logged.
- Any site replacement requires a documented reason in change log.
- Cached assets must be prepared for every frozen site.
