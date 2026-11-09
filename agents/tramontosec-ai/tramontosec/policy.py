"""Small, immutable tool allowlist. No shell, scanner execution or remote provider."""
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from .contracts import Profile, TaskMessage


@dataclass(frozen=True)
class ToolSpec:
    name: str
    profiles: tuple[Profile, ...]
    effect: str = 'read_metadata'


class Tool(Protocol):
    def __call__(self, message: TaskMessage, evidence: list[dict], memory: list[dict]) -> dict: ...


TOOLS = MappingProxyType({
    'analyze_recon': ToolSpec('analyze_recon', (Profile.RED,)),
    'analyze_infra': ToolSpec('analyze_infra', (Profile.RED,)),
    'analyze_static': ToolSpec('analyze_static', (Profile.STATIC,)),
    'review_controls': ToolSpec('review_controls', (Profile.BLUE,)),
})


def allowed_tools(profile: Profile) -> tuple[str, ...]:
    return tuple(k for k, v in TOOLS.items() if profile in v.profiles)


def authorize(profile: Profile, name: str) -> ToolSpec:
    spec = TOOLS.get(name)
    if spec is None or profile not in spec.profiles:
        raise PermissionError('Ferramenta não autorizada para este agente.')
    return spec


def check_message(message: TaskMessage, project: str) -> None:
    if message.project != project or message.allowed_tools != allowed_tools(message.profile):
        raise PermissionError('Contrato fora do projeto ou da política de ferramentas.')
    for name in message.allowed_tools:
        authorize(message.profile, name)

# Ferramentas consultivas do loop LLM: somente leitura de metadados previamente importados.
READ_TOOLS = MappingProxyType({
    'list_assets': ToolSpec('list_assets', (Profile.RED,)),
    'get_alerts': ToolSpec('get_alerts', (Profile.STATIC,)),
    'get_alert_summary': ToolSpec('get_alert_summary', (Profile.STATIC,)),
    'read_evidence': ToolSpec('read_evidence', (Profile.RED, Profile.STATIC, Profile.BLUE)),
    'list_hypotheses': ToolSpec('list_hypotheses', (Profile.RED, Profile.STATIC, Profile.BLUE)),
    'get_hypothesis': ToolSpec('get_hypothesis', (Profile.BLUE,)),
})


def allowed_read_tools(profile: Profile) -> tuple[str, ...]:
    return tuple(name for name, spec in READ_TOOLS.items() if profile in spec.profiles)


def authorize_read_tool(profile: Profile, name: str) -> ToolSpec:
    spec = READ_TOOLS.get(name)
    if spec is None or profile not in spec.profiles or spec.effect != 'read_metadata':
        raise PermissionError('Ferramenta consultiva não autorizada para este perfil.')
    return spec
