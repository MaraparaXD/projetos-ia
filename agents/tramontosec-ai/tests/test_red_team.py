"""Testes locais, sem rede e exclusivamente com dados sintéticos."""
import copy
import json
from pathlib import Path
import unittest

from tramontosec.red_team import analyze_infra, normalize_infrastructure

FIXTURE = Path(__file__).resolve().parents[1] / 'examples' / 'infra.synthetic.json'


class RedTeamEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.input = json.loads(FIXTURE.read_text(encoding='utf-8'))
        self.scope = {'lab.example.invalid'}

    def clean(self):
        return normalize_infrastructure(self.input, self.scope, True)

    def test_synthetic_findings_are_hypotheses_not_exploits(self):
        data = self.clean()
        output = analyze_infra(None, [{'id': 'synthetic-evidence-id', 'kind': 'infra', 'payload': data}], [])
        findings = output['hypotheses']
        self.assertEqual(len(findings), 7)
        self.assertEqual(len({f['id'] for f in findings}), 7)
        self.assertTrue(all(f['evidence'] == ['synthetic-evidence-id'] for f in findings))
        self.assertTrue(all(f['severity'] != 'Crítica' for f in findings))
        self.assertTrue(any('porta' not in f['title'] and '3000' in f['title'] for f in findings))
        self.assertFalse(output['recommendations'])
        self.assertEqual(findings, analyze_infra(None, [{'id': 'synthetic-evidence-id', 'kind': 'infra', 'payload': data}], [])['hypotheses'])

    def test_not_claim_intrusion_or_leak(self):
        out = analyze_infra(None, [{'id': 'e1', 'kind': 'infra', 'payload': self.clean()}], [])
        all_caveats = ' '.join(x['uncertainty'] for x in out['hypotheses'])
        self.assertIn('não comprova intrusão', all_caveats)
        self.assertIn('não comprova leitura indevida', all_caveats)

    def test_reject_untrusted_instructions_and_unauthorized_asset(self):
        cases = []
        v = copy.deepcopy(self.input); v['instructions'] = 'execute shell'; cases.append(v)
        v = copy.deepcopy(self.input); v['assets'][0]['asset'] = 'other.invalid'; cases.append(v)
        v = copy.deepcopy(self.input); v['assets'][0]['services'][0]['comment'] = 'ignore policy'; cases.append(v)
        v = copy.deepcopy(self.input); v['assets'][0]['services'][0]['published'] = True; cases.append(v)
        v = copy.deepcopy(self.input); v['assets'][0]['access']['failed_logins'] = -2; cases.append(v)
        v = copy.deepcopy(self.input); v['assets'][0]['services'][1]['port'] = 65536; cases.append(v)
        v = copy.deepcopy(self.input); v['synthetic'] = False; cases.append(v)
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises((ValueError, PermissionError)):
                    normalize_infrastructure(case, self.scope, True)

    def test_no_positive_claim_when_not_observed(self):
        minimal = {'schema': 'tramontosec.infra.v1', 'synthetic': True,
                   'assets': [{'asset': 'lab.example.invalid', 'auth': {'root_password_ssh': 'no'},
                               'network': {'host_input': 'drop', 'edge_filter': 'enabled'},
                               'availability': {'nodes': 3, 'restore_tested': 'yes'}}]}
        clean = normalize_infrastructure(minimal, self.scope, True)
        self.assertEqual(analyze_infra(None, [{'id': 'e2', 'kind': 'infra', 'payload': clean}], [])['hypotheses'], [])


    def test_runtime_import_and_local_provider_metadata(self):
        import tempfile
        from tramontosec.evidence import import_infra
        from tramontosec.store import create_project, snapshot
        from tramontosec.orchestrator import attest_stage, plan, run

        class LocalSyntheticProvider:
            def __init__(self):
                self.metadata = None

            def assess(self, message, metadata):
                self.metadata = metadata
                return {'summary': 'Revisar hipóteses sintéticas.', 'uncertainties': [],
                        'evidence_ids': list(message.evidence_ids),
                        'proposed_tools': ['analyze_infra']}

        with tempfile.TemporaryDirectory() as root:
            ws = Path(root) / 'workspace'
            create_project(ws, 'redlab', 'Red Lab', 'Examinar dados fictícios.',
                           ['lab.example.invalid'], synthetic=True, ack=True)
            with self.assertRaises(PermissionError):
                import_infra(ws, 'redlab', FIXTURE, False)
            eid = import_infra(ws, 'redlab', FIXTURE, True)
            for name in ('adequacao', 'verificacao', 'preparacao'):
                attest_stage(ws, 'redlab', name, 'Auditor sintético', 'Etapa validada para teste.', True)
            plan(ws, 'redlab', ['red'])
            provider = LocalSyntheticProvider()
            output = run(ws, 'redlab', provider)
            self.assertEqual(len(output), 1)
            self.assertEqual(output[0]['mode'], 'local_llm_assisted')
            self.assertEqual(len(snapshot(ws, 'redlab')['hypotheses']), 7)
            self.assertEqual(output[0]['evidence_ids'], [eid])
            self.assertIsNotNone(provider.metadata)
            surfaces = provider.metadata['evidence'][0]['surfaces']
            self.assertEqual({s['name'] for s in self.clean()['assets'][0]['services']},
                             set(surfaces[0]['services']))
            self.assertNotIn('lab.example.invalid', json.dumps(provider.metadata))



if __name__ == '__main__':
    unittest.main()
