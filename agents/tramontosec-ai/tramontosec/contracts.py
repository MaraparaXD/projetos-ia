"""Versioned messages. Evidence is data; it never grants permissions."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import re
from typing import Any


class Profile(str, Enum):
    RED = 'red'
    STATIC = 'static'
    BLUE = 'blue'


STAGES = ('adequacao', 'verificacao', 'preparacao', 'execucao', 'finalizacao')
STAGE_NAMES = ('Adequação', 'Verificação', 'Preparação', 'Execução', 'Finalização')


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value):
        raise ValueError('Identificador inválido: use até 64 letras, números, _ ou -.')
    if value.upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))}:
        raise ValueError('Identificador reservado pelo Windows.')
    return value


def text(value: Any, limit: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'Texto obrigatório, limitado a {limit} caracteres.')
    if any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError('Caracteres de controle não são permitidos.')
    return value.strip()


@dataclass(frozen=True)
class TaskMessage:
    task_id: str
    project: str
    profile: Profile
    objective: str
    stage: str
    evidence_ids: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    schema: str = 'tramontosec.task.v1'

    def __post_init__(self):
        identifier(self.project)
        text(self.objective, 2000)
        if not isinstance(self.profile, Profile) or self.stage != 'execucao':
            raise ValueError('Contrato de tarefa inválido.')
        if not isinstance(self.evidence_ids, tuple) or not isinstance(self.allowed_tools, tuple):
            raise ValueError('Evidências e ferramentas devem ser tuplas imutáveis.')

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AgentResult:
    task_id: str
    profile: Profile
    mode: str
    hypotheses: tuple[dict, ...]
    recommendations: tuple[dict, ...]
    uncertainties: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    model_assessment: dict | None = None
    schema: str = 'tramontosec.result.v1'

    def to_dict(self) -> dict:
        return asdict(self)
