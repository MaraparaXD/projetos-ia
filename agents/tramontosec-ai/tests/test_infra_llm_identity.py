"""Hipóteses do LLM devem preservar identidades definidas pelo Red de infraestrutura."""
import unittest

from tramontosec.agents import Specialist
from tramontosec.contracts import Profile, TaskMessage
from tramontosec.policy import allowed_tools
from tramontosec.red_team import normalize_infrastructure


class FakeProvider:
    def agent_step(self, message, context):
        return {'action': 'final', 'hypotheses': [
            {'asset_alias': 'asset-1', 'service': service,
             'evidence_ids': ['e1'], 'severity': 'Alta',
             'title': 'Verificar superficie ' + service,
             'uncertainty': 'Alcance externo não confirmado'}
            for service in ('dokploy', 'minio', 'buildkit')
        ], 'recommendations': []}


class InfraIdentityTest(unittest.TestCase):
    def test_rule_ids_unchanged_and_proposals_merged(self):
        raw = {'schema': 'tramontosec.infra.v1', 'synthetic': True, 'assets': [
            {'asset': 'lab.example.invalid', 'services': [
                {'name': 'dokploy', 'port': 3000, 'published': 'yes'},
                {'name': 'minio', 'port': 9000, 'published': 'yes'},
                {'name': 'buildkit', 'published': 'no', 'privileged': 'yes'}]}]}
        data = normalize_infrastructure(raw, {'lab.example.invalid'}, True)
        evidence = [{'id': 'e1', 'kind': 'infra', 'payload': data}]
        message = TaskMessage('t1', 'lab', Profile.RED, 'Auditoria fictícia', 'execucao',
                              ('e1',), allowed_tools(Profile.RED))
        baseline = Specialist(Profile.RED).run(message, evidence, [])
        assisted = Specialist(Profile.RED).run(message, evidence, [], FakeProvider())
        self.assertEqual(assisted.mode, 'local_llm_agent')
        self.assertEqual(len(assisted.hypotheses), len(baseline.hypotheses))
        self.assertEqual({h['id'] for h in assisted.hypotheses},
                         {h['id'] for h in baseline.hypotheses})
        self.assertTrue(all(h['origin'] == 'rule' for h in assisted.hypotheses))


if __name__ == '__main__':
    unittest.main()
