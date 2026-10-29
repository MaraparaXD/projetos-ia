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
