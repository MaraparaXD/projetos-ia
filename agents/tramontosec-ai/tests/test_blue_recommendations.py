"""Blue não recomenda itens rejeitados e distingue classes de risco."""
import unittest
from tramontosec.agents import review_controls


def candidate(key, title, status='candidate', profiles=None):
    return {'id': key, 'title': title, 'status': status, 'profiles': profiles or ['red'],
            'severity': 'Alta', 'controls': ['Confirmar acesso'], 'evidence': ['e1']}


class BlueRecommendationsTest(unittest.TestCase):
    def test_rejected_is_excluded(self):
        results = review_controls(None, [], [
            candidate('ok', 'Investigar superfície ssh'),
            candidate('no', 'Revisar regra', 'rejected', ['static']),
        ])['recommendations']
        self.assertEqual([r['hypothesis_id'] for r in results], ['ok'])

    def test_distinct_mitigations_and_no_false_applied(self):
        results = review_controls(None, [], [
            candidate('ssh', 'Investigar superfície ssh'),
            candidate('db', 'Investigar superfície database'),
            candidate('static', 'Revisar python.dynamic-execution', profiles=['static']),
        ])['recommendations']
        self.assertEqual(len({r['mitigation'] for r in results}), 3)
        self.assertEqual(len({r['validation'] for r in results}), 3)
        self.assertEqual(len({r['incident_response'] for r in results}), 3)
        self.assertTrue(all(r['applied'] is False and r['independent_confirmation'] is False for r in results))


if __name__ == '__main__':
    unittest.main()
