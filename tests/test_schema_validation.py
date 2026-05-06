import unittest

try:
    from pydantic import ValidationError
except ImportError:  # pragma: no cover
    ValidationError = None  # type: ignore[assignment]

if ValidationError is not None:
    from apps.api.schemas.enums import FeedbackStatus, ReviewStatus
    from apps.api.schemas.examples import incident_example
    from apps.api.schemas.models import Incident


@unittest.skipIf(ValidationError is None, "pydantic not installed")
class SchemaValidationTests(unittest.TestCase):
    def test_incident_example_is_valid(self) -> None:
        incident = incident_example()
        self.assertIsInstance(incident, Incident)
        self.assertEqual(incident.review_status, ReviewStatus.PROPOSED)
        self.assertEqual(incident.feedback_status, FeedbackStatus.UNRESOLVED)

    def test_invalid_bbox_fails_validation(self) -> None:
        if hasattr(incident_example(), "model_dump"):
            payload = incident_example().model_dump()
        else:
            payload = incident_example().dict()  # type: ignore[attr-defined]
        payload["bbox_norm"] = [0.1, 0.2, 0.3]
        with self.assertRaises(ValidationError):
            Incident(**payload)


if __name__ == "__main__":
    unittest.main()
