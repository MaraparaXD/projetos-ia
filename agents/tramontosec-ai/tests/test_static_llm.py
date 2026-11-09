"""Static agrupa alertas apenas com evidência e regra existentes."""
import unittest

from tramontosec.agents import Specialist
from tramontosec.contracts import Profile, TaskMessage
from tramontosec.policy import allowed_tools


class FakeProvider:
    def __init__(self, steps):
        self.steps = iter(steps)
    def agent_step(self, message, context):
        return next(self.steps)


class StaticLLMTest(unittest.TestCase):
    def setUp(self):
        self.msg = TaskMessage('t', 'lab', Profile.STATIC, 'Auditoria fictícia', 'execucao',
                               ('e1',), allowed_tools(Profile.STATIC))
        self.evidence = [{'id': 'e1', 'kind': 'scanner', 'payload': {
            'commit': None,
            'alerts': [{'rule_id': 'python.dynamic-execution', 'location': 'src/demo.py',
                        'line': 1, 'component': '', 'severity': 'WARNING'}]}}]

    def test_proposes_unverified_grouped_candidate(self):
        fake = FakeProvider([
            {'action': 'tool', 'tool': 'get_alerts', 'args': {'rule': 'python.dynamic-execution'}},
            {'action': 'final', 'hypotheses': [{
                'rule': 'python.dynamic-execution', 'evidence_ids': ['e1'],
                'title': 'Priorizar revisão do alerta sintético',
                'severity': 'Média', 'uncertainty': 'Possível falso positivo'}], 'recommendations': []},
        ])
        result = Specialist(Profile.STATIC).run(self.msg, self.evidence, [], fake)
        self.assertEqual(result.mode, 'local_llm_agent')
        self.assertEqual(len(result.hypotheses), 1)
        self.assertEqual(result.hypotheses[0]['origin'], 'rule')
        self.assertIn('Possível falso positivo', result.hypotheses[0]['uncertainty'])
        self.assertEqual(result.hypotheses[-1]['evidence'], ['e1'])

    def test_nonexistent_rule_falls_back(self):
        fake = FakeProvider([{'action': 'final', 'hypotheses': [{
            'rule': 'unseen.rule', 'evidence_ids': ['e1'], 'title': 'Alerta',
            'severity': 'Alta', 'uncertainty': 'Sem evidência'}], 'recommendations': []}])
        result = Specialist(Profile.STATIC).run(self.msg, self.evidence, [], fake)
        self.assertEqual(result.mode, 'deterministic_fallback')
        self.assertEqual(len(result.hypotheses), 1)


if __name__ == '__main__':
    unittest.main()
