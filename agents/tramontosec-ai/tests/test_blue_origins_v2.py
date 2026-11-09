"""Persistência e apresentação lado a lado sem perder recomendações anteriores."""
import json
from pathlib import Path
import tempfile
import unittest

from tramontosec.core import open_db
from tramontosec.demo import run_demo
from tramontosec.orchestrator import plan, run, report_markdown
from tramontosec.store import snapshot, project_root
from fakes_v2 import FakeProvider, final


class BlueOriginsTest(unittest.TestCase):
    def test_two_origins_survive_sqlite_report_and_legacy_rows(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / 'ws'
            run_demo(ws, 'lab')
            before = snapshot(ws, 'lab')
            candidate = before['hypotheses'][0]
            with open_db(project_root(ws, 'lab')) as db:
                for row in db.execute('SELECT id,payload FROM recommendations').fetchall():
                    payload = json.loads(row['payload'])
                    payload.pop('origin', None)
                    db.execute('UPDATE recommendations SET payload=? WHERE id=?',
                               (json.dumps(payload), row['id']))
            self.assertTrue(all(r['origin'] == 'rule' for r in snapshot(ws, 'lab')['recommendations']))
            plan(ws, 'lab', ['blue'])
            rec = {'hypothesis_id': candidate['id'], 'mitigation': 'Rever controle sintético.',
                   'compensating_control': 'Conferir ACL.', 'validation': 'Revisão independente.',
                   'incident_response': 'Preservar registros.'}
            result = run(ws, 'lab', FakeProvider([final(recommendations=[rec, rec])]))[0]
            matching = [r for r in result['recommendations'] if r['hypothesis_id'] == candidate['id']]
            self.assertEqual({r['origin'] for r in matching}, {'rule', 'llm'})
            self.assertEqual(len(matching), 2)
            self.assertTrue(all(r['applied'] is False and r['independent_confirmation'] is False
                                for r in matching))
            view = snapshot(ws, 'lab')
            self.assertEqual(len(view['recommendations']), len(before['recommendations']) + len(result['recommendations']))
            self.assertTrue(all(h['status'] == 'candidate' for h in view['hypotheses']))
            content = report_markdown(ws, 'lab')
            self.assertIn('Origem: rule', content)
            self.assertIn('Origem: llm', content)
            self.assertIn('sugestão de modelo não verificada', content)
            js = Path('tramontosec/web/app.js').read_text(encoding='utf-8')
            self.assertIn('adviceByOrigin.values()', js)
            self.assertIn('el.textContent = text', js)
            self.assertNotIn('innerHTML', js)
