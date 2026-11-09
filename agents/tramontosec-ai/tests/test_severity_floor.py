"""Severidade proposta não rebaixa regras nem evidências de scanner."""
import unittest
from tramontosec.agent_validation import validate_model_proposals
from tramontosec.agents import Specialist
from tramontosec.contracts import Profile
from fakes_v2 import FakeProvider, message, scanner, proposal, final


class SeverityFloorTest(unittest.TestCase):
    def test_scanner_floor_for_all_levels_and_unknown_model(self):
        for source, expected in [('CRITICAL', 'Crítica'), ('HIGH', 'Alta'), ('ERROR', 'Alta'),
                                 ('MEDIUM', 'Média'), ('WARNING', 'Média'), ('LOW', 'Baixa')]:
            for suggested in ('Informativa', 'Indeterminada'):
                with self.subTest(source=source, suggested=suggested):
                    data = scanner(severity=source)
                    fake = FakeProvider([final([proposal(severity=suggested)])])
                    result = Specialist(Profile.STATIC).run(message(), data, [], fake)
                    self.assertEqual(result.mode, 'local_llm_agent')
                    self.assertEqual(result.hypotheses[0]['severity'], expected)
                    self.assertTrue(any('modelo discorda do scanner' in h['uncertainty']
                                        for h in result.hypotheses))

    def test_highest_matching_scanner_level_only(self):
        data = scanner(severity='LOW')
        data[0]['payload']['alerts'] += [
            {**data[0]['payload']['alerts'][0], 'severity': 'CRITICAL'},
            {**data[0]['payload']['alerts'][0], 'rule_id': 'other.rule', 'severity': 'HIGH'}]
        parsed = validate_model_proposals(message(), data, [], final([proposal()]))
        self.assertEqual(parsed['hypotheses'][0]['severity'], 'Crítica')

    def test_model_can_raise_its_own_candidate(self):
        parsed = validate_model_proposals(message(), scanner(severity='WARNING'), [],
                                          final([proposal(severity='Alta')]))
        self.assertEqual(parsed['hypotheses'][0]['severity'], 'Alta')

    def test_unknown_scanner_severity_is_not_ordered(self):
        parsed = validate_model_proposals(message(), scanner(severity='UNKNOWN'), [],
                                          final([proposal(severity='Baixa')]))
        self.assertEqual(parsed['hypotheses'][0]['severity'], 'Baixa')

    def test_red_rule_severity_preserved_and_disagreement_recorded(self):
        data = [{'id': 'e1', 'kind': 'recon', 'payload': {'assets': [
            {'asset': 'lab.invalid', 'services': ['database'], 'controls': []}]}}]
        for severity in ('Informativa', 'Crítica'):
            suggested = {'asset_alias': 'asset-1', 'service': 'database', 'evidence_ids': ['e1'],
                         'severity': severity, 'title': 'Verificar banco', 'uncertainty': 'Conferência pendente'}
            result = Specialist(Profile.RED).run(message(Profile.RED), data, [],
                                                 FakeProvider([final([suggested])]))
            self.assertEqual(result.hypotheses[0]['severity'], 'Alta')
            self.assertIn('Modelo discordou', result.hypotheses[0]['uncertainty'])
            self.assertIn(severity, result.hypotheses[0]['uncertainty'])

    def test_absent_rule_falls_back_and_no_baseline_keeps_model_level(self):
        result = Specialist(Profile.STATIC).run(message(), scanner(), [],
                                                FakeProvider([final([proposal(rule='absent')])]))
        self.assertEqual(result.mode, 'deterministic_fallback')
        data = [{'id': 'e1', 'kind': 'recon', 'payload': {'assets': [
            {'asset': 'lab.invalid', 'services': ['minio'], 'controls': []}]}}]
        suggested = {'asset_alias': 'asset-1', 'service': 'minio', 'evidence_ids': ['e1'],
                     'severity': 'Baixa', 'title': 'Revisar objeto', 'uncertainty': 'Sem baseline'}
        result = Specialist(Profile.RED).run(message(Profile.RED), data, [], FakeProvider([final([suggested])]))
        self.assertEqual(result.hypotheses[0]['severity'], 'Baixa')
        self.assertEqual(result.hypotheses[0]['origin'], 'llm')
