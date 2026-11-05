"""Relatório local exibe a origem e trilha sem alterar revisões humanas."""
from pathlib import Path
import tempfile
import unittest

from tramontosec.demo import run_demo
from tramontosec.orchestrator import plan, report_markdown, run


class FakeProvider:
    def agent_step(self, message, context):
        if context['history']:
            return {'action': 'final', 'hypotheses': [], 'recommendations': []}
        return {'action': 'tool', 'tool': 'list_assets', 'args': {}}


class ReportOriginTest(unittest.TestCase):
    def test_report_displays_rule_origin_and_read_tool_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            ws = Path(directory) / 'ws'
            run_demo(ws, 'case')
            plan(ws, 'case', ['red'])
            run(ws, 'case', FakeProvider())
            content = report_markdown(ws, 'case')
            self.assertIn('Origem: rule', content)
            self.assertIn('Trilha resumida: ferramenta list_assets', content)
            self.assertIn('Relatório preliminar', content)


if __name__ == '__main__':
    unittest.main()
