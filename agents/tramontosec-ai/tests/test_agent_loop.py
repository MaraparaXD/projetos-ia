"""FakeProvider permite testes offline de loop consultivo."""
import unittest
from tramontosec.agent_loop import AgentLoopError, run_agent_loop
from tramontosec.contracts import Profile, TaskMessage
from tramontosec.policy import allowed_tools


class FakeProvider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.received = []

    def agent_step(self, message, context):
        self.received.append(context)
        return next(self.responses)


class AgentLoopTest(unittest.TestCase):
    def setUp(self):
        self.msg = TaskMessage('t', 'lab', Profile.RED, 'Revisar escopo fictício', 'execucao',
                               ('e1',), allowed_tools(Profile.RED))
        self.evidence = [{'id': 'e1', 'kind': 'recon', 'payload': {'assets': [
            {'asset': 'segredo-interno.example.invalid', 'services': ['https'], 'controls': ['tls']}
        ]}}]

    def test_readonly_tool_then_final(self):
        fake = FakeProvider([{'action': 'tool', 'tool': 'list_assets', 'args': {}},
                             {'action': 'final', 'hypotheses': [], 'recommendations': []}])
        output = run_agent_loop(fake, self.msg, self.evidence, [])
        self.assertEqual(len(output['reasoning_trace']), 1)
        self.assertEqual(output['reasoning_trace'][0]['tool'], 'list_assets')
        self.assertNotIn('segredo-interno', str(fake.received))
        self.assertIn('asset-1', str(fake.received[1]))

    def test_prohibited_tool_fails(self):
        fake = FakeProvider([{'action': 'tool', 'tool': 'execute_shell', 'args': {}}])
        with self.assertRaises(PermissionError):
            run_agent_loop(fake, self.msg, self.evidence, [])

    def test_no_final_before_limit_fails(self):
        fake = FakeProvider([{'action': 'tool', 'tool': 'list_assets', 'args': {}}] * 2)
        with self.assertRaises(AgentLoopError):
            run_agent_loop(fake, self.msg, self.evidence, [], max_steps=2)


if __name__ == '__main__':
    unittest.main()
