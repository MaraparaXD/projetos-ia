"""Provedor offline com snapshots independentes para regressões de segurança."""
from copy import deepcopy
from tramontosec.contracts import Profile, TaskMessage
from tramontosec.policy import allowed_tools


class FakeProvider:
    def __init__(self, steps=()):
        self.steps = iter(steps)
        self.contexts = []

    def agent_step(self, message, context):
        self.contexts.append(deepcopy(context))
        step = next(self.steps)
        if isinstance(step, Exception):
            raise step
        return deepcopy(step)


def message(profile=Profile.STATIC, refs=('e1',)):
    return TaskMessage('t', 'lab', profile, 'Revisão sintética', 'execucao', refs, allowed_tools(profile))


def scanner(rule='test.rule', severity='ERROR'):
    return [{'id': 'e1', 'kind': 'scanner', 'payload': {'commit': None, 'alerts': [
        {'rule_id': rule, 'severity': severity, 'location': 'src/private.py', 'line': 1, 'component': 'internal'}]}}]


def proposal(**changes):
    return {'rule': 'test.rule', 'severity': 'Informativa', 'evidence_ids': ['e1'],
            'title': 'Revisar alerta sintético', 'uncertainty': 'Exige conferência', **changes}


def final(hypotheses=(), recommendations=()):
    return {'action': 'final', 'hypotheses': list(hypotheses), 'recommendations': list(recommendations)}
