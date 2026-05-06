import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "openapi.json"


class OpenAPIContractTests(unittest.TestCase):
    def test_openapi_exists(self) -> None:
        self.assertTrue(OPENAPI_PATH.exists(), "openapi.json is missing")

    def test_required_paths_are_present(self) -> None:
        spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
        required_paths = {
            "/health",
            "/sites",
            "/sites/{site_id}",
            "/sites/{site_id}/scan",
            "/scans/{scan_id}",
            "/scans/{scan_id}/evidence",
            "/watchlist/scan",
            "/incidents/{incident_id}/review",
            "/incidents/export",
        }
        self.assertTrue(required_paths.issubset(set(spec.get("paths", {}).keys())))

    def test_review_and_zone_enums_are_frozen(self) -> None:
        spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
        schemas = spec.get("components", {}).get("schemas", {})
        self.assertEqual(
            schemas["LikelySourceZone"]["enum"],
            ["active_face", "gas_system", "perimeter_or_unknown"],
        )
        self.assertEqual(
            schemas["ReviewStatus"]["enum"],
            ["proposed", "published", "dismissed", "needs_review"],
        )

    def test_mapbox_is_required_in_panel_contracts(self) -> None:
        spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
        schemas = spec.get("components", {}).get("schemas", {})

        evidence_panel_required = schemas["EvidencePanel"]["required"]
        self.assertIn("mapbox_context_path", evidence_panel_required)

        panel_paths = schemas["EvidencePayload"]["properties"]["panel_paths"]
        self.assertIn("mapbox_context_path", panel_paths["required"])


if __name__ == "__main__":
    unittest.main()
