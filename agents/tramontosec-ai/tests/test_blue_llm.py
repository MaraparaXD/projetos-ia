"""Blue usa memória isolada, sem recomendar rejeitadas nem aplicar mudanças."""
import unittest

from tramontosec.agents import Specialist
from tramontosec.contracts import Profile, TaskMessage
from tramontosec.policy import allowed_tools


class FakeProvider:
    def __init__(self, steps):
        self.steps = iter(steps)
    def agent_step(self, message, context):
        return next(self.steps)


class BlueLLMTest(unittest.TestCase):
    def setUp(self):
        self.msg = TaskMessage('t', 'lab', Profile.BLUE, 'Revisar controles fictícios',
                               'execucao', ('e1',), allowed_tools(Profile.BLUE))
        self.evidence = [{'id': 'e1', 'kind': 'recon', 'payload': {'assets': []}}]
        self.memory = [
            {'id': 'h1', 'status': 'candidate', 'title': 'Investigar superfície ssh',
             'severity': 'Alta', 'controls': ['Verificar ACL'], 'evidence': ['e1']},
            {'id': 'h2', 'status': 'rejected', 'title': 'Alerta falso',
             'severity': 'Média', 'controls': [], 'evidence': ['e1']},
        ]

    def test_recommendation_specific_and_unapplied(self):
        steps = [
            {'action': 'tool', 'tool': 'get_hypothesis', 'args': {'id': 'h1'}},
            {'action': 'final', 'hypotheses': [], 'recommendations': [
                {'hypothesis_id': 'h1', 'mitigation': 'Rever acesso administrativo com aprovação.',
                 'compensating_control': 'Monitorar acessos administrativos.',
                 'validation': 'Conferir autenticação em laboratório.',
                 'incident_response': 'Preservar logs e acionar equipe.'},
                {'hypothesis_id': 'h2', 'mitigation': 'Ignorar falso positivo.',
                 'compensating_control': 'Nenhum.', 'validation': 'Nenhuma.',
                 'incident_response': 'Nenhuma.'},
            ]},
        ]
        result = Specialist(Profile.BLUE).run(self.msg, self.evidence, self.memory, FakeProvider(steps))
        self.assertEqual(result.mode, 'local_llm_agent')
        self.assertEqual(len(result.recommendations), 1)
        rec = result.recommendations[0]
        self.assertEqual(rec['hypothesis_id'], 'h1')
        self.assertEqual(rec['origin'], 'llm')
        self.assertIs(rec['applied'], False)
        self.assertIs(rec['independent_confirmation'], False)

    def test_forged_hypothesis_falls_back(self):
        fake = FakeProvider([{'action': 'final', 'hypotheses': [], 'recommendations': [
            {'hypothesis_id': 'absent', 'mitigation': 'x', 'compensating_control': 'y',
             'validation': 'z', 'incident_response': 'w'}]}])
        result = Specialist(Profile.BLUE).run(self.msg, self.evidence, self.memory, fake)
        self.assertEqual(result.mode, 'deterministic_fallback')
        self.assertEqual(len(result.recommendations), 1)


if __name__ == '__main__':
    unittest.main()
