"""Benchmark cobre todos os perfis, vazio, duplicatas e fallbacks estratificados."""
import unittest
from tramontosec.benchmark import compare_agent_synthetic
from tramontosec.providers import ProviderError
from fakes_v2 import FakeProvider, final


class BenchmarkFakeProvider(FakeProvider):
    def __init__(self, mode='valid'):
        super().__init__()
        self.mode = mode

    def agent_step(self, message, context):
        if self.mode == 'empty-fails' and all(
            e['asset_count'] == 0 and e['alert_count'] == 0 for e in context['evidence']
        ):
            return {'action': 'invalid'}
        if self.mode == 'static-duplicates-fail' and message.profile.value == 'static' and any(
            e['alert_count'] > 1 for e in context['evidence']
        ):
            raise ProviderError('PRIVATE MODEL TEXT')
        return final()


class BenchmarkProfilesTest(unittest.TestCase):
    def test_three_scenarios_per_profile_and_recommendation_coverage(self):
        result = compare_agent_synthetic(BenchmarkFakeProvider(), repetitions=2)
        self.assertEqual(result['samples'], 18)
        self.assertEqual(result['baseline']['runs'], 18)
        self.assertEqual(set(result['profiles']), {'red', 'static', 'blue'})
        for profile in result['profiles'].values():
            self.assertEqual(set(profile['scenarios']), {'empty', 'ordinary', 'duplicates'})
            for scenario in profile['scenarios'].values():
                self.assertEqual(scenario['agent']['runs'], 2)
                self.assertEqual(scenario['agent']['fallback_rate'], 0)
                time = scenario['agent']['elapsed_seconds']
                self.assertGreaterEqual(time['max'], time['median'])
                self.assertGreaterEqual(time['median'], 0)
            self.assertEqual(profile['scenarios']['empty']['agent']['hypotheses'], 0)
            self.assertEqual(profile['scenarios']['empty']['agent']['recommendations'], 0)
        blue = result['profiles']['blue']['scenarios']['ordinary']['agent']
        self.assertGreater(blue['recommendations'], 0)
        self.assertGreater(blue['coverage_evidence'], 0)
        self.assertFalse(result['vulnerability_detection_validated'])
        self.assertIsInstance(result['limitations'], list)

    def test_mixed_modes_keep_reasons_and_counts_separate(self):
        result = compare_agent_synthetic(BenchmarkFakeProvider('empty-fails'))
        self.assertAlmostEqual(result['agent']['fallback_rate'], 1 / 3)
        self.assertEqual(result['agent']['fallback_reasons'], {'AgentLoopError': 9})
        self.assertEqual(result['agent']['mode'], 'mixed')
        self.assertEqual(set(result['agent']['modes']), {'local_llm_agent', 'deterministic_fallback'})
        for profile in result['profiles'].values():
            self.assertEqual(profile['scenarios']['empty']['agent']['fallback_rate'], 1)
            self.assertEqual(profile['scenarios']['duplicates']['agent']['fallback_rate'], 0)

    def test_provider_failure_is_not_mislabeled_invalid_proposal(self):
        result = compare_agent_synthetic(BenchmarkFakeProvider('static-duplicates-fail'), repetitions=1)
        self.assertEqual(result['agent']['fallback_reasons'], {'ProviderError': 1})
        self.assertAlmostEqual(result['agent']['fallback_rate'], 1 / 9)
        self.assertNotIn('PRIVATE', str(result))

    def test_invalid_repetition_budget_is_rejected(self):
        for value in (0, 101, True, '3'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                compare_agent_synthetic(BenchmarkFakeProvider(), repetitions=value)
