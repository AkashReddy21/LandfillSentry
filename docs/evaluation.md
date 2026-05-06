# Phase 7 Evaluation Guide

This document defines the Phase 7 evaluation and reliability workflow.

## Scope

Phase 7 compares three model paths:

- `heuristic` (candidate-only projection)
- `base_model` (no adapter)
- `fine_tuned_model` (adapter-enabled contract path)

and validates reliability for known failure modes. The evaluator now runs repeated positive,
negative, and cloudy fixture cases so the report is no longer based on a single sample per class.

## Run Command

```bash
python scripts/benchmark_models.py
```

## Generated Artifacts

The command writes these files to `data/manifests/`:

- `phase7_evaluation_report.json`
- `phase7_baseline_comparison.md`
- `phase7_null_scene_report.json`
- `phase7_human_actionability_rubric_v1.json`
- `phase7_reliability_report.json`

## Metrics

Per model, the harness computes:

- `json_valid_rate`
- `incident_f1`
- `zone_accuracy`
- `bbox_iou`
- `human_usefulness_score`
- confusion matrix (`tp`, `fp`, `tn`, `fn`)
- per-fixture plume and zone accuracy
- Wilson confidence intervals for schema validity, plume accuracy, zone accuracy, and null-scene false positives

Null-scene trust is reported separately as:

- `false_positive_count`
- `false_positive_rate`
- confidence interval for `false_positive_rate`

## Quality Gates

The report includes pass/fail gates for the fine-tuned path:

- `json_valid_rate >= 1.00`
- `incident_f1 >= 0.80`
- `zone_accuracy >= 0.75`
- `bbox_iou >= 0.50`
- `human_usefulness_score >= 0.80`
- `null_false_positive_rate <= 0.25`

`validation_summary.validation_strength` is `moderate` only when the suite has at least
12 cases per model, the fine-tuned path passes all gates, and it shows meaningful deltas
over the base projection. Otherwise it remains `limited`.

## Human Actionability Rubric (v1)

Each incident is scored on:

- actionability
- clarity
- plausibility
- followup_quality
- trustworthiness

Each criterion is scored 1-5 and normalized to `[0,1]`.

## Failure Injection Coverage

The reliability harness explicitly tests:

- invalid JSON model output retry path
- empty candidate handling path
- Mapbox API configuration failure path
- slow inference detection path

These checks feed into `phase7_reliability_report.json`.
