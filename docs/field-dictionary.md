# Field Dictionary (Phase 1 Contract Freeze)

## Site

- `site_id`: unique stable site identifier
- `name`: human-readable site name
- `lat`: centroid latitude
- `lon`: centroid longitude
- `country`: country label
- `operator`: operator label
- `watchlist_enabled`: include site in watchlist scans
- `polygon_geojson`: optional polygon boundary
- `metadata`: extensible metadata object

## ImageAsset

- `asset_id`: unique asset identifier
- `site_id`: parent site
- `source`: imagery source (`dphi-simsat`, `dphi-simsat-sentinel`, `dphi-simsat-mapbox`, `mapbox`, `cache`, `other`)
- `timestamp_requested`: request time
- `timestamp_captured`: capture time
- `cloud_cover`: cloud metric in `[0,1]`
- `bands`: band list or channel descriptors
- `local_path`: cache path for asset
- `cache_key`: deterministic cache key

## Candidate

- `candidate_id`: candidate identifier
- `site_id`: parent site
- `job_id`: scan/job identifier
- `bbox_norm`: normalized bbox `[x1, y1, x2, y2]`
- `candidate_score`: candidate confidence score
- `temporal_recurrence`: recurrence feature score
- `cloud_penalty`: cloud penalty score
- `likely_source_zone_prior`: coarse zone prior enum

## EvidencePanel

- `panel_id`: evidence panel identifier
- `site_id`: parent site
- `candidate_id`: candidate link
- `panel_version`: panel composer version
- `current_rgb_path`: path to current RGB panel image
- `spectral_composite_path`: path to methane-sensitive composite
- `temporal_diff_path`: path to temporal difference panel
- `mapbox_context_path`: required map context image path
- `metadata_json`: serialized panel metadata

## Incident

- `incident_id`: incident identifier
- `site_id`: parent site
- `job_id`: scan/job identifier
- `analysis_time`: inference timestamp
- `plume_likely`: plume-likely classification
- `confidence`: confidence in `[0,1]`
- `bbox_norm`: normalized bbox `[x1, y1, x2, y2]`
- `likely_source_zone`: predicted zone enum
- `persistence_score`: persistence in `[0,1]`
- `priority_tier`: triage priority enum
- `severity_tier`: incident severity enum
- `review_status`: review lifecycle enum
- `feedback_status`: feedback enum
- `evidence_summary`: concise rationale text
- `recommended_followup`: next operational action
- `model_version`: model or adapter identifier

## ReviewAction

- `incident_id`: target incident
- `review_status`: requested review state transition
- `feedback_status`: optional operator feedback
- `review_comment`: optional human note

## EvaluationRecord

- `eval_id`: evaluation row identifier
- `split`: dataset split (`train`, `validation`, `test`, `demo`)
- `site_id`: evaluated site
- `baseline_model`: baseline model id
- `candidate_model`: model under evaluation
- `json_valid_rate`: valid JSON generation rate
- `incident_f1`: incident-level F1 metric
- `zone_accuracy`: source-zone accuracy
- `bbox_iou`: bbox IoU metric
- `human_usefulness_score`: reviewer usefulness score
