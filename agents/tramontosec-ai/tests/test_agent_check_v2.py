"""Comando de robustez injetável: sem rede e sem escrita no workspace do auditor."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tramontosec.agent_check import run_agent_check
from tramontosec.agents import Specialist
from tramontosec.cli import cli, main
from tramontosec.cli_v03 import dispatch
from tramontosec.contracts import Profile
from tramontosec.providers import ProviderError
from fakes_v2 import FakeProvider, message, scanner, final, proposal


class CheckFakeProvider:
    def check_available(self):
        pass

    def agent_step(self, msg, context):
        if not context['history']:
            tool = {'red': 'list_assets', 'static': 'get_alert_summary',
                    'blue': 'list_hypotheses'}[msg.profile.value]
            return {'action': 'tool', 'tool': tool, 'args': {}, 'why': 'Conferir metadados sintéticos.'}
        return final()


class AgentCheckTest(unittest.TestCase):
    def test_command_runs_five_times_each_profile_and_ignores_user_workspace(self):
        args = cli().parse_args(['agent-check', '--model', 'synthetic', '--ack-local-model'])
        with tempfile.TemporaryDirectory() as directory:
            untouched = Path(directory) / 'never-created'
            output = StringIO()
            with redirect_stdout(output):
                self.assertTrue(dispatch(args, untouched, provider_factory=lambda *_: CheckFakeProvider()))
            self.assertFalse(untouched.exists())
        result = json.loads(output.getvalue())
        self.assertFalse(result['workspace_persisted'])
        self.assertEqual(set(result['profiles']), {'red', 'static', 'blue'})
        for runs in result['profiles'].values():
            self.assertEqual(len(runs), 5)
            self.assertTrue(all(r['mode'] == 'local_llm_agent' and r['steps_used'] == 2 for r in runs))
            self.assertTrue(all(r['elapsed_seconds'] >= 0 and r['fallback_reason'] is None for r in runs))
        self.assertFalse(result['vulnerability_detection_validated'])

    def test_cli_unavailable_exits_nonzero_without_simulation(self):
        fake = CheckFakeProvider()
        fake.check_available = lambda: (_ for _ in ()).throw(ProviderError('PRIVATE ERROR'))
        output, error = StringIO(), StringIO()
        with patch('tramontosec.agent_check.OllamaProvider', return_value=fake), patch(
                'sys.argv', ['tramontosec', 'agent-check', '--model', 'synthetic', '--ack-local-model']):
            with redirect_stdout(output), redirect_stderr(error), self.assertRaises(SystemExit) as raised:
                main()
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(output.getvalue(), '')
        self.assertIn('indisponível', error.getvalue())
        self.assertNotIn('PRIVATE ERROR', error.getvalue())

    def test_ack_and_other_workspace_requirements_remain_mandatory(self):
        with self.assertRaises(PermissionError):
            run_agent_check('synthetic', False, lambda *_: CheckFakeProvider())
        with patch('sys.argv', ['tramontosec', 'projects']), redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main()
        self.assertEqual(raised.exception.code, 2)

    def test_fallback_reasons_and_steps_do_not_include_model_content(self):
        cases = [
            ([{'action': 'unknown'}], 'AgentLoopError', 1),
            ([final([proposal(rule='unknown')])], 'InvalidProposal', 1),
            ([ProviderError('PRIVATE MODEL OUTPUT')], 'ProviderError', 1),
            ([{'action': 'tool', 'tool': 'shell', 'args': {}}], 'PermissionError', 1),
            ([{'action': 'tool', 'tool': 'get_alerts', 'args': {}}] * 6, 'AgentLoopError', 6),
        ]
        for steps, reason, used in cases:
            with self.subTest(reason=reason, used=used):
                result = Specialist(Profile.STATIC).run(message(), scanner(), [], FakeProvider(steps))
                self.assertEqual(result.mode, 'deterministic_fallback')
                self.assertIn('fallback_reason=' + reason, result.uncertainties)
                self.assertEqual(result.steps_used, used)
                self.assertNotIn('PRIVATE', str(result.to_dict()))

    def test_validated_model_counts_are_not_human_acceptance(self):
        result = Specialist(Profile.STATIC).run(message(), scanner(), [],
                    FakeProvider([final([proposal()])]))
        self.assertEqual(result.validated_hypotheses, 1)
        self.assertEqual(result.validated_recommendations, 0)
        self.assertTrue(all(h.get('status', 'candidate') == 'candidate' for h in result.hypotheses))

    def test_inference_provider_failure_is_reported_and_cli_fails(self):
        class FailingFakeProvider(CheckFakeProvider):
            def agent_step(self, msg, context):
                raise ProviderError('PRIVATE')
        args = cli().parse_args(['agent-check', '--model', 'synthetic', '--ack-local-model'])
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(ProviderError):
            dispatch(args, None, lambda *_: FailingFakeProvider())
        result = json.loads(output.getvalue())
        self.assertFalse(result['available'])
        self.assertTrue(all(run['fallback_reason'] == 'ProviderError'
                            for runs in result['profiles'].values() for run in runs))
