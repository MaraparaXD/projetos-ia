"""why é opcional; texto inválido é descartado sem perder a ferramenta."""
import json
from pathlib import Path
import tempfile
import unittest
from tramontosec.agent_loop import run_agent_loop
from tramontosec.demo import run_demo
from tramontosec.orchestrator import plan, run, report_markdown
from tramontosec.store import snapshot
from fakes_v2 import FakeProvider, message, scanner, final


class ModelNoteTest(unittest.TestCase):
    def test_valid_note_is_distinct_from_fixed_reason(self):
        fake = FakeProvider([{'action': 'tool', 'tool': 'get_alert_summary', 'args': {},
                              'why': 'Conferir concentração de alertas por regra.'}, final()])
        out = run_agent_loop(fake, message(), scanner(), [])
        trace = out['reasoning_trace'][0]
        self.assertEqual(set(trace), {'tool', 'reason', 'model_note'})
        self.assertEqual(trace['model_note'], 'Conferir concentração de alertas por regra.')
        self.assertIn('Contar alertas', trace['reason'])

    def test_absent_and_invalid_notes_do_not_reject_tool_step(self):
        for value in (None, 1, {}, '', 'x' * 161, 'IGNORE regras', 'curl endpoint',
                      'https://example.invalid', 'a\nb\nc\nd'):
            step = {'action': 'tool', 'tool': 'get_alerts', 'args': {}}
            if value is not None:
                step['why'] = value
            fake = FakeProvider([step, final()])
            out = run_agent_loop(fake, message(), scanner(), [])
            self.assertIsNone(out['reasoning_trace'][0]['model_note'])
            self.assertEqual(len(fake.contexts), 2)

    def test_blue_note_persists_in_events_and_report_without_own_hypotheses(self):
        with tempfile.TemporaryDirectory() as directory:
            ws = Path(directory) / 'ws'
            run_demo(ws, 'lab')
            plan(ws, 'lab', ['blue'])
            fake = FakeProvider([{'action': 'tool', 'tool': 'list_hypotheses', 'args': {},
                                  'why': 'Conferir as candidatas para orientar a revisão.'}, final()])
            result = run(ws, 'lab', fake)[0]
            self.assertFalse(result['hypotheses'])
            events = [e for e in snapshot(ws, 'lab')['runtime_events'] if e['verb'] == 'llm_read_tool']
            self.assertEqual(events[-1]['details']['model_note'],
                             'Conferir as candidatas para orientar a revisão.')
            self.assertIn('nota do modelo (não verificada)', report_markdown(ws, 'lab'))
            self.assertIn('Conferir as candidatas', report_markdown(ws, 'lab'))

    def test_malicious_note_is_not_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            ws = Path(directory) / 'ws'
            run_demo(ws, 'lab')
            plan(ws, 'lab', ['static'])
            run(ws, 'lab', FakeProvider([{'action': 'tool', 'tool': 'get_alert_summary', 'args': {},
                                        'why': 'PowerShell SECRET_INJECTION'}, final()]))
            self.assertNotIn('SECRET_INJECTION', json.dumps(snapshot(ws, 'lab')))
            js = Path('tramontosec/web/app.js').read_text(encoding='utf-8')
            self.assertIn('nota do modelo (não verificada)', js)
            self.assertIn('el.textContent = text', js)
