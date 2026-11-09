"""Transportes locais falsos: nenhuma conexão real é permitida pelos testes."""
import json


def encoded(value):
    return json.dumps(value).encode('utf-8')


def local_model():
    return {'details': {'format': 'gguf'}, 'model_info': {'general.architecture': 'synthetic'}}


class FakeResponse:
    def __init__(self, raw, status=200):
        self.raw = raw
        self.status = status
        self.limits = []

    def read(self, limit):
        self.limits.append(limit)
        return self.raw[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class FakeOpener:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def open(self, request, timeout):
        url = request if isinstance(request, str) else request.full_url
        if not url.startswith('http://127.0.0.1:11434/api/'):
            raise AssertionError('Teste tentou endpoint externo.')
        self.requests.append((request, timeout))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response
