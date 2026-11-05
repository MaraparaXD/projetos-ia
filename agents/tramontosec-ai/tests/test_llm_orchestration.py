"""Orquestrador persiste o uso de ferramentas e preserva sequência por perfil."""
from pathlib import Path
import tempfile
import unittest

from tramontosec.demo import run_demo
from tramontosec.orchestrator import plan, run
from tramontosec.store import snapshot


class FakeProvider:
    def agent_step(self, message, context):
        if not context['history']:
            tool = {'red': 'list_assets', 'static': 'get_alerts',
                    'blue': 'list_hypotheses'}[message.profile.value]
            return {'action': 'tool', 'tool': tool, 'args': {}}
        return {'action': 'final', 'hypotheses': [], 'recommendations': []}


class OrchestrationTest(unittest.TestCase):
    def test_runtime_events_are_isolated_and_modes_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / 'workspace'
            run_demo(workspace, 'synthetic')
            plan(workspace, 'synthetic', ['blue', 'red', 'static'])
            results = run(workspace, 'synthetic', FakeProvider())
            self.assertEqual([r['profile'] for r in results], ['red', 'static', 'blue'])
            self.assertTrue(all(r['mode'] == 'local_llm_agent' for r in results))
            view = snapshot(workspace, 'synthetic')
            events = [e for e in view['runtime_events'] if e['verb'] == 'llm_read_tool']
            self.assertEqual(len(events), 3)
            self.assertEqual({e['details']['profile'] for e in events}, {'red', 'static', 'blue'})
            self.assertTrue(all(h['origin'] in ('rule', 'llm') for h in view['hypotheses']))


if __name__ == '__main__':
    unittest.main()
