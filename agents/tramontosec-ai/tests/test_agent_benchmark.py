"""Benchmark sintético: métricas operacionais não provam eficácia de detecção."""
import unittest
from tramontosec.benchmark import compare_agent_synthetic


class FakeProvider:
    def __init__(self, invalid=False):
        self.invalid = invalid
    def agent_step(self, message, context):
        if self.invalid:
            return {'action': 'unknown'}
        return {'action': 'final', 'hypotheses': [], 'recommendations': []}


class BenchmarkAgentTest(unittest.TestCase):
    def test_baseline_vs_agent_is_synthetic(self):
        result = compare_agent_synthetic(FakeProvider())
        self.assertFalse(result['vulnerability_detection_validated'])
        self.assertEqual(result['samples'], 1)
        self.assertEqual(result['baseline']['hypotheses'], result['agent']['hypotheses'])
        self.assertEqual(result['agent']['mode'], 'local_llm_agent')
        self.assertEqual(result['agent']['invalid_response_rate'], 0)
        self.assertGreaterEqual(result['baseline']['elapsed_seconds'], 0)

    def test_invalid_provider_counts_fallback(self):
        result = compare_agent_synthetic(FakeProvider(invalid=True))
        self.assertEqual(result['agent']['mode'], 'deterministic_fallback')
        self.assertEqual(result['agent']['invalid_response_rate'], 1)


if __name__ == '__main__':
    unittest.main()
