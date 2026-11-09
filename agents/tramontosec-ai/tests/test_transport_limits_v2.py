"""Transporte real do adaptador com respostas falsas: falha fechada e limites."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

from tramontosec.agents import Specialist
from tramontosec.contracts import Profile
from tramontosec.core import make_workspace, import_findings, list_findings
from tramontosec.local_ai import local_suggestion, _NoRedirect
from tramontosec.providers import OllamaProvider, ProviderError, local_models, validate_assessment
from fakes_v2 import FakeProvider, message, scanner, final, proposal
from transport_fakes_v2 import FakeOpener, FakeResponse, encoded, local_model


class ProviderTransportTest(unittest.TestCase):
    def test_full_loop_uses_loopback_no_proxy_and_checked_local_model_each_step(self):
        opener = FakeOpener([
            FakeResponse(encoded(local_model())),
            FakeResponse(encoded({'response': json.dumps({'action': 'tool', 'tool': 'get_alert_summary',
                                                         'args': {}, 'why': 'Conferir contagens.'})})),
            FakeResponse(encoded(local_model())),
            FakeResponse(encoded({'response': json.dumps(final([proposal()]))})),
        ])
        with patch('urllib.request.build_opener', return_value=opener) as factory:
            result = Specialist(Profile.STATIC).run(message(), scanner(), [], OllamaProvider('synthetic', True))
        self.assertEqual(result.mode, 'local_llm_agent')
        self.assertEqual(result.steps_used, 2)
        self.assertEqual(len(opener.requests), 4)
        for call in factory.call_args_list:
            self.assertEqual(call.args[0].proxies, {})
            self.assertIsInstance(call.args[1], _NoRedirect)
        for request, timeout in opener.requests:
            self.assertLessEqual(timeout, 25)
            if request.full_url.endswith('generate'):
                body = json.loads(request.data)
                self.assertIn('get_alert_summary', body['system'])
                self.assertIn('why', body['system'])
                self.assertNotIn('private.py', body['prompt'])

    def test_agent_rejects_status_oversize_and_malformed_envelopes(self):
        invalid = [FakeResponse(b'broken'), FakeResponse(encoded([])),
                   FakeResponse(encoded({'response': '[]'})), FakeResponse(encoded({'response': 'null'})),
                   FakeResponse(encoded({'response': '{bad'})), FakeResponse(encoded({'response': 42})),
                   FakeResponse(encoded({'missing': 'response'})), FakeResponse(b'\xff'),
                   FakeResponse(encoded({'response': '{}'}), 503),
                   FakeResponse(encoded({'response': '{}'}) + b' ' * 32_001)]
        for response in invalid:
            with self.subTest(raw=response.raw[:40]):
                opener = FakeOpener([FakeResponse(encoded(local_model())), response])
                with patch('urllib.request.build_opener', return_value=opener), self.assertRaises(ProviderError):
                    OllamaProvider('synthetic', True).agent_step(message(), {})
                self.assertEqual(response.limits, [32_001])

    def test_assessment_transport_limits_and_schema_errors(self):
        for response in (FakeResponse(b'bad'), FakeResponse(encoded({'response': '{}'})),
                         FakeResponse(encoded({}), 500), FakeResponse(b' ' * 64_001)):
            opener = FakeOpener([FakeResponse(encoded(local_model())), response])
            with patch('urllib.request.build_opener', return_value=opener), self.assertRaises(ProviderError):
                OllamaProvider('synthetic', True).assess(message(), {})

    def test_preflight_blocks_cloud_remote_bad_format_and_large_metadata(self):
        for model, raw in (
            ('synthetic:cloud', encoded(local_model())),
            ('synthetic', encoded({**local_model(), 'remote_model': 'remote'})),
            ('synthetic', encoded({'details': {'format': 'safetensors'}, 'model_info': {'general.architecture': 'x'}})),
            ('synthetic', b' ' * 1_000_001), ('synthetic', b'broken'),
        ):
            opener = FakeOpener([FakeResponse(raw)])
            with patch('urllib.request.build_opener', return_value=opener), self.assertRaises(ProviderError):
                OllamaProvider(model, True).check_available()
            self.assertTrue(all(not request.full_url.endswith('generate') for request, _ in opener.requests))
            if 'cloud' in model:
                self.assertEqual(opener.requests, [])

    def test_context_limit_blocks_before_transport_and_invalid_model_is_rejected(self):
        opener = FakeOpener([])
        with patch('urllib.request.build_opener', return_value=opener), self.assertRaises(ProviderError):
            OllamaProvider('synthetic', True).agent_step(message(), {'payload': 'x' * 18_001})
        self.assertEqual(opener.requests, [])
        with self.assertRaises(ValueError):
            OllamaProvider('invalid model', True)

    def test_model_listing_filters_cloud_and_handles_oversize_or_invalid_json(self):
        good = {'models': [{'name': 'local', 'size': 2_000_000}, {'name': 'x-cloud', 'size': 2_000_000},
                           {'name': 'tiny', 'size': 1}, {'name': 1, 'size': 2_000_000}, 'invalid']}
        with patch('urllib.request.build_opener', return_value=FakeOpener([FakeResponse(encoded(good))])):
            self.assertEqual(local_models()['models'], ['local'])
        for raw in (b' ' * 64_001, b'broken', encoded({'models': None}), encoded({})):
            with patch('urllib.request.build_opener', return_value=FakeOpener([FakeResponse(raw)])):
                self.assertFalse(local_models()['available'])

    def test_assessment_contract_requires_evidence_and_bounded_lists(self):
        valid = {'summary': 'Rever dados', 'uncertainties': [], 'evidence_ids': ['e1'], 'proposed_tools': []}
        for changes in ({'summary': ''}, {'uncertainties': ['x'] * 9}, {'uncertainties': [1]},
                        {'uncertainties': ['x' * 351]}, {'evidence_ids': []}, {'proposed_tools': 'tool'}):
            with self.subTest(changes=changes), self.assertRaises(ProviderError):
                validate_assessment({**valid, **changes}, message())

    def test_provider_runtime_failure_does_not_swallow_internal_bug(self):
        with self.assertRaises(RuntimeError):
            Specialist(Profile.STATIC).run(message(), scanner(), [], FakeProvider([RuntimeError('internal')]))


class LocalSuggestionTransportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.ws = self.base / 'ws'
        make_workspace(self.ws)
        path = self.base / 'findings.json'
        path.write_text(json.dumps([{'project': 'Lab', 'identifier': 'X-1', 'title': 'Sintético',
            'classification': 'I', 'severity': 'Indeterminada', 'summary': 'Requer revisão',
            'source_doc': 'synthetic', 'evidence': []}]), encoding='utf-8')
        import_findings(self.ws, path)
        self.answer = {'controles_a_conferir': ['Verificar controle'],
                       'duvidas': ['Conferência pendente'], 'possiveis_falsos_positivos': []}

    def invoke(self, answer=None, raw=None, status=200):
        response = FakeResponse(raw if raw is not None else encoded({'response': json.dumps(answer)}), status)
        opener = FakeOpener([FakeResponse(encoded(local_model())), response])
        with patch('urllib.request.build_opener', return_value=opener):
            result = local_suggestion(self.ws, 'Lab:X-1', 'synthetic', True)
        return result, response

    def test_success_remains_suggestion_without_changing_human_state(self):
        before = list_findings(self.ws)
        result, _ = self.invoke(self.answer)
        parsed = json.loads(result)
        self.assertEqual(parsed['status'], 'suggestion_only')
        self.assertEqual(parsed['review'], 'human_required')
        self.assertEqual(list_findings(self.ws), before)

    def test_bad_schema_types_limits_and_status_fail_closed(self):
        for answer in ([], {**self.answer, 'decision': 'accepted'},
                       {**self.answer, 'duvidas': 1}, {**self.answer, 'duvidas': ['x'] * 6},
                       {**self.answer, 'duvidas': ['x' * 251]}, {**self.answer, 'duvidas': [1]}):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                self.invoke(answer)
        for raw, status in ((encoded([]), 200), (encoded({'response': 42}), 200),
                            (b'broken', 200), (encoded({'response': '{}'}), 503)):
            with self.subTest(status=status, raw=raw), self.assertRaises(ValueError):
                self.invoke(raw=raw, status=status)

    def test_oversize_valid_json_with_padding_is_rejected(self):
        # Um prefixo JSON válido não pode esconder bytes além do orçamento.
        raw = encoded({'response': json.dumps(self.answer)}) + b' ' * 32_001
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            self.invoke(raw=raw)

    def test_missing_workspace_key_consent_and_model_fail_before_network(self):
        with patch('urllib.request.build_opener', side_effect=AssertionError('network')):
            for args, error in (
                ((self.ws, 'Lab:X-1', 'synthetic', False), ValueError),
                ((self.ws, 'Lab:X-1', 'bad model', True), ValueError),
                ((self.base / 'missing', 'Lab:X-1', 'synthetic', True), FileNotFoundError),
                ((self.ws, 'absent', 'synthetic', True), KeyError),
            ):
                with self.subTest(args=args), self.assertRaises(error):
                    local_suggestion(*args)

    def test_cloud_and_redirects_are_blocked_before_generation(self):
        opener = FakeOpener([])
        with patch('urllib.request.build_opener', return_value=opener), self.assertRaises(ProviderError):
            local_suggestion(self.ws, 'Lab:X-1', 'synthetic:cloud', True)
        self.assertEqual(opener.requests, [])
        request = urllib.request.Request('http://127.0.0.1:11434/api/generate')
        for url in ('http://external.invalid/', 'http://127.0.0.1:9999/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                _NoRedirect().redirect_request(request, None, 302, 'Found', {}, url)
