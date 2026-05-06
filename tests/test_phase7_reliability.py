import unittest

from ml.evaluation.reliability_harness import ReliabilityHarness


class Phase7ReliabilityTests(unittest.TestCase):
    def test_reliability_harness_covers_required_failure_modes(self) -> None:
        harness = ReliabilityHarness()
        report = harness.run_all()

        self.assertTrue(report["invalid_json"]["handled"])
        self.assertTrue(report["empty_candidate"]["handled"])
        self.assertTrue(report["mapbox_api_failure"]["handled"])
        self.assertTrue(report["slow_inference"]["handled"])
        self.assertTrue(report["all_passed"])


if __name__ == "__main__":
    unittest.main()

