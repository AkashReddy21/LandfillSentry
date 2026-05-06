"""Export the current FastAPI OpenAPI spec with frozen judge contract schemas."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.api.main import app


def _json_schema_for_model(model_class):
    if hasattr(model_class, "model_json_schema"):
        return model_class.model_json_schema(ref_template="#/components/schemas/{model}")
    return model_class.schema(ref_template="#/components/schemas/{model}")  # type: ignore[attr-defined]


def _inject_frozen_contract_schemas(spec: dict) -> None:
    from apps.api.schemas.models import EvidencePanel

    schemas = spec.setdefault("components", {}).setdefault("schemas", {})
    schemas["EvidencePanel"] = _json_schema_for_model(EvidencePanel)

    panel_paths_schema = {
        "type": "object",
        "title": "EvidencePanelPaths",
        "required": [
            "current_rgb_path",
            "spectral_composite_path",
            "temporal_diff_path",
            "mapbox_context_path",
        ],
        "properties": {
            "current_rgb_path": {"type": "string"},
            "spectral_composite_path": {"type": "string"},
            "temporal_diff_path": {"type": "string"},
            "mapbox_context_path": {"type": "string"},
        },
    }
    schemas["EvidencePayload"] = {
        "type": "object",
        "title": "EvidencePayload",
        "required": ["assets", "candidate", "panel_paths", "metadata"],
        "properties": {
            "assets": {"type": "object", "additionalProperties": True},
            "candidate": {"type": "object", "additionalProperties": True},
            "panel_paths": panel_paths_schema,
            "metadata": {"type": "object", "additionalProperties": True},
        },
    }


def export_openapi(path: Path = PROJECT_ROOT / "openapi.json") -> Path:
    spec = app.openapi()
    _inject_frozen_contract_schemas(spec)
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path


def main() -> None:
    path = export_openapi()
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
