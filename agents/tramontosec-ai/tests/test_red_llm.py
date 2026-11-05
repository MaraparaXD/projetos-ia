"""Red Team LLM é limitado, reproduzível e mantém baseline de regras."""
import unittest

from tramontosec.agents import Specialist
from tramontosec.contracts import Profile, TaskMessage
from tramontosec.policy import allowed_tools


class FakeProvider:
    def __init__(self, responses):
        self.responses = iter(responses)
    def agent_step(self, message, context):
        return next(self.responses)


class RedLLMTest(unittest.TestCase):
    def setUp(self):
        self.msg = TaskMessage('t', 'lab', Profile.RED, 'Revisar serviços', 'execucao',
                               ('e1',), allowed_tools(Profile.RED))
        self.evidence = [{'id': 'e1', 'kind': 'recon', 'payload': {'assets': [
            {'asset': 'lab.example.invalid', 'services': ['http'], 'controls': []}
        ]}}]

    def test_same_identity_merges_and_records_trace(self):
        response = [
            {'action': 'tool', 'tool': 'list_assets', 'args': {}},
            {'action': 'final', 'hypotheses': [{
                'asset_alias': 'asset-1', 'service': 'http', 'evidence_ids': ['e1'],
                'severity': 'Média', 'title': 'Revisar HTTP',
                'uncertainty': 'Alcance real desconhecido'}], 'recommendations': []},
        ]
        original = Specialist(Profile.RED).run(self.msg, self.evidence, [])
        result = Specialist(Profile.RED).run(self.msg, self.evidence, [], FakeProvider(response))
        self.assertEqual(result.mode, 'local_llm_agent')
        self.assertEqual(len(result.reasoning_trace), 1)
        self.assertEqual(len(result.hypotheses), len(original.hypotheses))
        self.assertEqual(result.hypotheses[0]['id'], original.hypotheses[0]['id'])
        self.assertEqual(result.hypotheses[0]['origin'], 'rule')

    def test_invalid_model_response_fallback(self):
        result = Specialist(Profile.RED).run(self.msg, self.evidence, [],
                                              FakeProvider([{'action': 'final',
                                                             'hypotheses': [{'evidence_ids': ['forged']}],
                                                             'recommendations': []}]))
        self.assertEqual(result.mode, 'deterministic_fallback')
        self.assertEqual(len(result.hypotheses), 1)


if __name__ == '__main__':
    unittest.main()
