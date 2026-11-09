"""Fluxos reais de CLI em processo para medir cobertura sem usar dados privados."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import runpy
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tramontosec.cli import main
from tramontosec.demo import run_demo
from tramontosec.store import snapshot
from tramontosec.scanners import list_alerts
from tramontosec.agent_check import run_agent_check
from test_agent_check_v2 import CheckFakeProvider
from transport_fakes_v2 import FakeOpener, FakeResponse, encoded, local_model


class CLIWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.ws = self.base / 'ws'

    def invoke(self, *args, expected=0, workspace=None):
        output, error = StringIO(), StringIO()
        argv = ['tramontosec', '--workspace', str(workspace or self.ws), *map(str, args)]
        code = 0
        with patch('sys.argv', argv), redirect_stdout(output), redirect_stderr(error):
            try:
                main()
            except SystemExit as exc:
                code = exc.code
        self.assertEqual(code, expected, error.getvalue())
        self.assertNotIn('Traceback', error.getvalue())
        return output.getvalue()

    def write_json(self, name, data):
        path = self.base / name
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_runtime_cli_roundtrip_preserves_gates_origins_and_review(self):
        self.invoke('demo', '--project', 'lab')
        view = snapshot(self.ws, 'lab')
        head = next(e['payload']['head'] for e in view['evidence'] if e['kind'] == 'baseline')
        self.invoke('baseline', '--project', 'lab', '--expected-commit', head)
        self.invoke('analyze-local', '--project', 'lab', '--path', 'src/demo.py')
        asset = view['project']['scope']['assets'][0]
        recon = self.write_json('recon.json', {'synthetic': True, 'assets': [
            {'asset': asset, 'services': ['http', 'ssh'], 'controls': ['tls']}]})
        infra = self.write_json('infra.json', {'schema': 'tramontosec.infra.v1', 'synthetic': True,
            'assets': [{'asset': asset, 'services': [{'name': 'dokploy', 'published': 'yes', 'port': 3000}]}]})
        scanner = self.write_json('scanner.json', {'results': [{'check_id': 'test.rule', 'path': 'src/demo.py',
            'start': {'line': 1}, 'extra': {'severity': 'ERROR'}}]})
        for tool, file in (('recon', recon), ('infra', infra), ('semgrep', scanner)):
            self.invoke('evidence-import', '--project', 'lab', '--tool', tool, '--file', file, '--ack-redacted-input')
        self.invoke('plan', '--project', 'lab')
        self.invoke('run', '--project', 'lab', expected=2)
        self.invoke('stage', '--project', 'lab', '--name', 'preparacao', '--reviewer', 'Auditor sintético',
                    '--reason', 'Evidências fictícias revistas', '--ack-human')
        with patch('tramontosec.providers.OllamaProvider', return_value=CheckFakeProvider()):
            results = json.loads(self.invoke('run', '--project', 'lab', '--model', 'synthetic', '--ack-local-model'))
        self.assertEqual([r['profile'] for r in results], ['red', 'static', 'blue'])
        self.assertTrue(all(r['mode'] == 'local_llm_agent' for r in results))
        self.assertTrue(all(r['origin'] == 'rule' for r in results[-1]['recommendations']))
        self.invoke('project-create', '--project', 'other', '--name', 'Outro', '--objective', 'Revisão sintética',
                    '--asset', 'lab.invalid', '--synthetic', '--ack-authorized')
        self.assertEqual(len(json.loads(self.invoke('projects'))), 2)
        self.assertEqual(len(json.loads(self.invoke('agents'))), 3)
        tags = {'models': [{'name': 'synthetic', 'size': 2_000_000}]}
        with patch('urllib.request.build_opener', return_value=FakeOpener([FakeResponse(encoded(tags))])):
            self.assertTrue(json.loads(self.invoke('models'))['available'])
        self.assertTrue(json.loads(self.invoke('history', '--project', 'lab')))
        self.assertEqual(json.loads(self.invoke('audit', '--project', 'lab'))['project']['id'], 'lab')
        report = json.loads(self.invoke('report', '--project', 'lab'))
        self.assertTrue(Path(report['report']).is_file())
        planned = json.loads(self.invoke('plan', '--project', 'lab', '--agent', 'red'))
        self.invoke('task-cancel', '--project', 'lab', '--id', planned[0]['task_id'],
                    '--reviewer', 'Auditor', '--reason', 'Plano sintético cancelado', '--ack-human')
        candidate = snapshot(self.ws, 'lab')['hypotheses'][0]
        args = ('finding-review', '--project', 'lab', '--id', candidate['id'],
                '--decision', 'accepted', '--reviewer', 'Auditor', '--reason', 'Conferência sintética')
        self.invoke(*args, expected=2)
        self.invoke(*args, '--ack-reviewed-evidence')
        self.assertEqual(snapshot(self.ws, 'lab')['hypotheses'][0]['status'], 'accepted')
        self.invoke('stage', '--project', 'lab', '--name', 'execucao', '--reviewer', 'Auditor',
                    '--reason', 'Ainda há outras candidatas', '--ack-human', expected=2)
        self.invoke('plan', '--project', 'lab', '--agent', 'red')
        deterministic = json.loads(self.invoke('run', '--project', 'lab'))
        self.assertTrue(all(r['mode'] == 'deterministic' for r in deterministic))

    def test_legacy_cli_roundtrip_requires_human_review_and_never_claims_semantics(self):
        self.invoke('init', '--ack-authorized-secure-storage')
        self.invoke('upgrade', '--ack-authorized-secure-storage')
        fixture_ws = self.base / 'fixture'
        run_demo(fixture_ws, 'lab')
        view = snapshot(fixture_ws, 'lab')
        repo = Path(view['project']['scope']['repo'])
        head = next(e['payload']['head'] for e in view['evidence'] if e['kind'] == 'baseline')
        finding = self.write_json('findings.json', [{'project': 'Lab', 'identifier': 'X-1', 'title': 'Sintético',
            'classification': 'I', 'severity': 'Indeterminada', 'summary': 'Exige revisão', 'source_doc': 'synthetic',
            'evidence': [{'repo': 'api', 'path': 'src/demo.py', 'start': 1, 'end': 1, 'commit': head}]}])
        doc = self.base / 'report.md'
        doc.write_text('VULN-01', encoding='utf-8')
        self.invoke('attach', '--id', 'doc', '--file', doc, '--kind', 'technical_note')
        self.invoke('catalog-report', '--id', 'catalog', '--file', doc, '--scope', 'external_assessment')
        self.invoke('seed', '--file', finding)
        self.assertIn('Lab:X-1', self.invoke('list'))
        self.assertTrue(json.loads(self.invoke('git-check', '--repo', repo, '--expected-commit', head))['baseline_valid'])
        scan = self.write_json('scan.json', {'results': [{'check_id': 'synthetic.rule', 'path': 'src/demo.py',
                                                       'start': {'line': 1}, 'extra': {'severity': 'WARNING'}}]})
        self.invoke('import-scan', '--project', 'Lab', '--tool', 'semgrep', '--file', scan, '--ack-redacted-input')
        alert = list_alerts(self.ws)[0]
        self.assertIn(alert['alert_id'][:14], self.invoke('alerts'))
        self.assertIn(alert['alert_id'], self.invoke('alerts', '--project', 'Lab', '--full-id'))
        self.invoke('triage', '--alert-id', alert['alert_id'], '--status', 'needs_context',
                    '--reviewer', 'Auditor', '--reason', 'Revisão sintética')
        self.assertEqual(list_alerts(self.ws)[0]['triage'], 'needs_context')
        self.assertTrue(json.loads(self.invoke('correlate', '--project', 'Lab')))
        manifest = self.base / 'manifest'
        manifest.mkdir()
        (manifest / 'requirements.txt').write_text('ollama>=1')
        self.assertFalse(json.loads(self.invoke('ai-inventory', '--repo', manifest))['ai_component_confirmed'])
        self.assertIn('semantic_review=HUMAN_REQUIRED', self.invoke('verify', '--api-repo', repo))
        self.invoke('review', '--key', 'Lab:X-1', '--decision', 'accepted', '--reviewer', 'Auditor',
                    '--reason', 'Revisão manual sintética', '--ack-reviewed-code')
        self.assertIn('Draft written', self.invoke('export'))
        answer = {'controles_a_conferir': [], 'duvidas': ['Conferir contexto'], 'possiveis_falsos_positivos': []}
        opener = FakeOpener([FakeResponse(encoded(local_model())), FakeResponse(encoded({'response': json.dumps(answer)}))])
        with patch('urllib.request.build_opener', return_value=opener):
            self.assertIn('suggestion_only', self.invoke('assist-local', '--key', 'Lab:X-1',
                                                       '--model', 'synthetic', '--ack-local-model'))
        self.assertEqual(json.loads(self.invoke('benchmark'))['fp'], 0)

    def test_cli_errors_do_not_leak_internal_database_or_git_details(self):
        for failure, code in ((sqlite3.OperationalError('PRIVATE'), 2),
                              (subprocess.TimeoutExpired('PRIVATE', 1), 2), (KeyboardInterrupt(), 130)):
            with self.subTest(failure=type(failure).__name__), patch('tramontosec.cli_v03.dispatch', side_effect=failure):
                self.invoke('projects', expected=code)

    def test_module_entry_point_and_dashboard_dispatch(self):
        output = StringIO()
        with patch('sys.argv', ['tramontosec', '--workspace', str(self.ws), 'agents']), redirect_stdout(output):
            runpy.run_module('tramontosec', run_name='__main__')
        self.assertEqual(len(json.loads(output.getvalue())), 3)
        with patch('tramontosec.dashboard.serve') as serve:
            self.invoke('dashboard', '--port', '9999')
        serve.assert_called_once_with(self.ws, 9999)

    def test_check_main_success_and_invalid_repetition_budget(self):
        output = StringIO()
        with patch('sys.argv', ['tramontosec', 'agent-check', '--model', 'synthetic', '--ack-local-model']), patch(
                'tramontosec.agent_check.OllamaProvider', return_value=CheckFakeProvider()), redirect_stdout(output):
            main()
        self.assertEqual(len(json.loads(output.getvalue())['profiles']['red']), 5)
        for value in (0, 101, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_agent_check('synthetic', True, repetitions=value)
