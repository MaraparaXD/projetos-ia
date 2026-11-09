"""Ramos de erro e orçamentos do loop, sempre com FakeProvider offline."""
import unittest
from tramontosec.agent_loop import AgentLoopError, run_agent_loop
from tramontosec.agent_validation import _check_text
from tramontosec.agents import Specialist
from tramontosec.contracts import Profile
from fakes_v2 import FakeProvider, message, scanner, final


class LoopErrorTest(unittest.TestCase):
    def test_invalid_step_budgets_never_call_provider(self):
        for budget in (0, 13, True, 1.5):
            fake = FakeProvider([final()])
            with self.subTest(budget=budget), self.assertRaises(AgentLoopError):
                run_agent_loop(fake, message(), scanner(), [], max_steps=budget)
            self.assertEqual(fake.contexts, [])

    def test_context_budget_blocks_before_inference(self):
        fake = FakeProvider([final()])
        memory = [{'id': 'x' * 18_001, 'severity': 'Alta'}]
        with self.assertRaises(AgentLoopError) as raised:
            run_agent_loop(fake, message(), scanner(), memory)
        self.assertEqual(raised.exception.steps_used, 0)
        self.assertEqual(fake.contexts, [])

    def test_malformed_actions_and_large_responses_preserve_baseline(self):
        cases = [[], 'raw text', {'action': []}, {**final(), 'decision': 'accepted'},
                 {**final(), 'hypotheses': {}}, {**final(), 'recommendations': {}},
                 {'action': 'tool', 'tool': 1, 'args': {}},
                 {'action': 'tool', 'tool': 'get_alerts', 'args': {}, 'extra': 1},
                 {**final(), 'extra': 'x' * 12_001}]
        for step in cases:
            result = Specialist(Profile.STATIC).run(message(), scanner(), [], FakeProvider([step]))
            self.assertEqual(result.mode, 'deterministic_fallback')
            self.assertEqual(result.steps_used, 1)
            self.assertTrue(all(h['origin'] == 'rule' for h in result.hypotheses))

    def test_tool_arguments_filters_and_identifiers_fail_closed(self):
        cases = [
            (Profile.RED, 'list_assets', {'unexpected': 1}),
            (Profile.STATIC, 'get_alerts', []), (Profile.STATIC, 'get_alerts', {'extra': 1}),
            (Profile.STATIC, 'get_alerts', {'severity': []}),
            (Profile.STATIC, 'get_alerts', {'severity': 'BOGUS'}),
            (Profile.STATIC, 'read_evidence', {}), (Profile.STATIC, 'read_evidence', {'id': 1}),
            (Profile.STATIC, 'read_evidence', {'id': 'outside'}),
            (Profile.BLUE, 'list_hypotheses', {'extra': 1}),
            (Profile.BLUE, 'list_hypotheses', {'status': 'confirmed'}),
            (Profile.BLUE, 'list_hypotheses', {'status': []}),
            (Profile.BLUE, 'get_hypothesis', {}), (Profile.BLUE, 'get_hypothesis', {'id': 1}),
            (Profile.BLUE, 'get_hypothesis', {'id': 'outside'}),
        ]
        for profile, tool, args in cases:
            with self.subTest(tool=tool, args=args), self.assertRaises(AgentLoopError):
                run_agent_loop(FakeProvider([{'action': 'tool', 'tool': tool, 'args': args}]),
                               message(profile), scanner(), [])

    def test_filtered_reads_and_metadata_only_evidence(self):
        data = scanner()
        data[0]['payload']['alerts'].append({**data[0]['payload']['alerts'][0], 'rule_id': 'other', 'severity': 'LOW'})
        steps = [{'action': 'tool', 'tool': 'get_alerts', 'args': {'rule': 'test.rule', 'severity': 'ERROR'}},
                 {'action': 'tool', 'tool': 'get_alerts', 'args': {'severity': 'LOW'}},
                 {'action': 'tool', 'tool': 'read_evidence', 'args': {'id': 'e1'}}, final()]
        fake = FakeProvider(steps)
        run_agent_loop(fake, message(), data, [])
        history = fake.contexts[-1]['history']
        self.assertEqual(len(history[0]['result']['alerts']), 1)
        self.assertEqual(history[1]['result']['alerts'][0]['rule'], 'other')
        self.assertEqual(history[2]['result'], {'id': 'e1', 'kind': 'scanner', 'asset_count': 0, 'alert_count': 2})
        self.assertNotIn('private.py', str(history))

    def test_status_filtered_memory_and_unknown_services_are_sanitized(self):
        memory = [{'id': 'h1', 'severity': 'Alta', 'status': 'rejected', 'evidence': ['e1']},
                  {'id': 'h2', 'severity': 'Baixa', 'status': 'candidate', 'evidence': ['e1']}]
        fake = FakeProvider([{'action': 'tool', 'tool': 'list_hypotheses', 'args': {'status': 'candidate'}}, final()])
        run_agent_loop(fake, message(Profile.BLUE), scanner(), memory)
        self.assertEqual(fake.contexts[-1]['history'][0]['result']['hypotheses'][0]['id'], 'h2')
        data = [{'id': 'e1', 'kind': 'infra', 'payload': {'assets': [
            {'asset': 'private.invalid', 'services': ['SECRET', {'name': 'SECRET'}, 42], 'controls': []}]}}]
        fake = FakeProvider([{'action': 'tool', 'tool': 'list_assets', 'args': {}}, final()])
        run_agent_loop(fake, message(Profile.RED), data, [])
        self.assertEqual(fake.contexts[-1]['history'][0]['result']['assets'][0]['services'], ['other'] * 3)

    def test_summary_truncation_and_rule_filtering_are_explicit(self):
        data = scanner()
        alert = data[0]['payload']['alerts'][0]
        data[0]['payload']['alerts'] = [{**alert, 'rule_id': f'rule.{i}'} for i in range(101)]
        fake = FakeProvider([{'action': 'tool', 'tool': 'get_alert_summary', 'args': {}},
                             {'action': 'tool', 'tool': 'get_alert_summary', 'args': {'rule': 'rule.1'}}, final()])
        run_agent_loop(fake, message(), data, [])
        history = fake.contexts[-1]['history']
        self.assertTrue(history[0]['result']['truncated'])
        self.assertEqual(history[0]['result']['rule_count'], 101)
        self.assertEqual(len(history[0]['result']['rules']), 100)
        self.assertEqual(history[1]['result']['rule_count'], 1)

    def test_provider_io_errors_are_wrapped_without_message_leak(self):
        for failure in (OSError('PRIVATE'), ValueError('PRIVATE'), TimeoutError('PRIVATE')):
            fake = FakeProvider([failure])
            with self.assertRaises(AgentLoopError) as raised:
                run_agent_loop(fake, message(), scanner(), [])
            self.assertEqual(raised.exception.steps_used, 1)
            self.assertNotIn('PRIVATE', str(raised.exception))

    def test_literal_newline_escape_normalization_is_preserved(self):
        self.assertEqual(_check_text('Revisar' + chr(92) + 'ncontrole', 160), 'Revisar controle')
