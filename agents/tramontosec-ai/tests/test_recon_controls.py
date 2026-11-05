"""Controles informados não são tratados como comprovados."""
import unittest

from tramontosec.agents import analyze_recon


class ReconPriorityTest(unittest.TestCase):
    def evaluate(self, services, controls):
        return analyze_recon(None, [
            {'id': 'e1', 'kind': 'recon', 'payload': {'assets': [
                {'asset': 'lab.example.invalid', 'services': services, 'controls': controls}
            ]}}
        ], [])['hypotheses']

    def test_relevant_controls_reduce_one_level_without_changing_identity(self):
        cases = [
            ('database', 'network_acl', 'Alta', 'Média'),
            ('http', 'waf', 'Média', 'Baixa'),
            ('https', 'tls', 'Média', 'Baixa'),
            ('ssh', 'mfa', 'Baixa', 'Baixa'),
        ]
        for service, control, original, reduced in cases:
            with self.subTest(service=service):
                plain = self.evaluate([service], [])[0]
                guarded = self.evaluate([service], [control])[0]
                self.assertEqual(plain['severity'], original)
                self.assertEqual(guarded['severity'], reduced)
                self.assertEqual(plain['id'], guarded['id'])
                self.assertIn('não foram testados', guarded['uncertainty'])

    def test_irrelevant_controls_do_not_reduce_severity(self):
        result = self.evaluate(['database'], ['tls'])[0]
        self.assertEqual(result['severity'], 'Alta')
        self.assertIn('não foi testada', result['uncertainty'])


if __name__ == '__main__':
    unittest.main()
