"""Ensaio operacional local sobre a demonstração sintética em diretório temporário."""
from pathlib import Path
import tempfile
from time import perf_counter

from .contracts import Profile
from .demo import run_demo
from .orchestrator import plan, run
from .providers import OllamaProvider, ProviderError


def fallback_reason(result):
    return next((item.split('=', 1)[1] for item in result['uncertainties']
                 if item.startswith('fallback_reason=')), None)


def run_agent_check(model, ack, provider_factory=None, repetitions=5):
    if not ack:
        raise PermissionError('agent-check exige --ack-local-model.')
    if type(repetitions) is not int or not 1 <= repetitions <= 100:
        raise ValueError('Repetições devem estar entre 1 e 100.')
    provider = (provider_factory or OllamaProvider)(model, ack)
    # A factory é injetável somente pela API Python para testes offline.
    try:
        provider.check_available()
    except (OSError, ValueError) as exc:
        raise ProviderError('Ollama ou modelo GGUF local indisponível; nenhum ensaio simulado.') from exc
    profiles = {profile.value: [] for profile in Profile}
    provider_failed = False
    with tempfile.TemporaryDirectory(prefix='tramontosec-agent-check-') as directory:
        workspace = Path(directory) / 'workspace'
        run_demo(workspace, 'agent-check')
        for repetition in range(1, repetitions + 1):
            for profile in Profile:
                plan(workspace, 'agent-check', [profile.value])
                start = perf_counter()
                result = run(workspace, 'agent-check', provider)[0]
                elapsed = perf_counter() - start
                reason = fallback_reason(result)
                provider_failed |= reason == 'ProviderError'
                profiles[profile.value].append({
                    'repetition': repetition, 'mode': result['mode'], 'fallback_reason': reason,
                    'steps_used': result['steps_used'],
                    'hypotheses': len(result['hypotheses']),
                    'recommendations': len(result['recommendations']),
                    'validated_model_hypotheses': result['validated_hypotheses'],
                    'validated_model_recommendations': result['validated_recommendations'],
                    'elapsed_seconds': round(elapsed, 6),
                })
    return {'synthetic_only': True, 'repetitions': repetitions, 'profiles': profiles,
            'available': not provider_failed, 'workspace_persisted': False,
            'vulnerability_detection_validated': False,
            'error': 'Ollama ou resposta do modelo indisponível/inválida durante o ensaio.' if provider_failed else None,
            'limitation': 'Propostas validadas pelo contrato continuam candidatas; não são decisões humanas.'}
