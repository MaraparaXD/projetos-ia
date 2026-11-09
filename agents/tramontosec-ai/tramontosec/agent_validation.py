"""Contratos estritos para sugestões LLM; nenhuma confirmação ou mudança automática."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

from .contracts import Profile, text
from .scanners import RuleAliases

SEVERITIES = frozenset({'Crítica', 'Alta', 'Média', 'Baixa', 'Informativa', 'Indeterminada'})
# Indeterminada não participa da ordem; scanner conhecido fornece um piso.
SEVERITY_ORDER = {name: level for level, name in enumerate(
    ('Informativa', 'Baixa', 'Média', 'Alta', 'Crítica'))}
SCANNER_SEVERITIES = {
    'CRITICAL': 'Crítica', 'HIGH': 'Alta', 'ERROR': 'Alta',
    'MEDIUM': 'Média', 'WARNING': 'Média', 'LOW': 'Baixa',
}


def scanner_severity(value):
    return SCANNER_SEVERITIES.get(value.upper(), 'Indeterminada')


SERVICES = frozenset({'http', 'https', 'ssh', 'database', 'dokploy', 'minio', 'buildkit'})


class InvalidProposal(ValueError):
    pass


# Filtro heurístico explícito para propostas, não um interpretador nem uma
# garantia linguística. Limites de capacidade e revisão humana continuam obrigatórios.
# Fronteiras de palavra evitam bloquear "execução", "aproveitar" ou
# ponto e vírgula seguido de prosa comum.
COMMAND_PATTERNS = (
    r'\brm\s+-', r'\bsudo\s+', r'\bcurl\s+', r'\bwget\s+', r'\bchmod\s+',
    r'\bbash\s+-c\b', r'\bpowershell\b', r'\bInvoke-[A-Za-z]',
    r'\beval\s*\(', r'\bexec\s*\(', r'\|\s*sh\b', r'&&', r'\$\(',
    r';\s*(?:rm|sudo|curl|wget|chmod|bash|sh|powershell|pwsh|cmd|python3?|node|'
    r'echo|printf|cat|cd|cp|mv|del|start|mkdir|touch|whoami|id)\b',
    r';\s*[A-Za-z_][A-Za-z0-9_.-]*\s*\(',
)
INSTRUCTION_PATTERNS = (
    r'\b(?:ignore|ignorem|ignorar|disregard|override|bypass)\b',
    r'\bdesconsidere\s+(?:as\s+)?regras\b', r'\baceite\s+tudo\b',
    r'\b(?:aprove|aprovar|approve)\b', r'\baccept\s+(?:all|everything)\b',
    r'\bmark\s+as\s+accepted\b',
)
FORBIDDEN_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE)
                           for pattern in (*COMMAND_PATTERNS, *INSTRUCTION_PATTERNS))
URL_PATTERN = re.compile(r'\b[a-z][a-z0-9+.-]*://|www\.', re.IGNORECASE)


def _check_text(value, limit):
    if (type(value) is not str or value.count('\n') > 2
            or any(unicodedata.category(c) in {'Cc', 'Cf', 'Cs'} and c != '\n' for c in value)):
        raise InvalidProposal('Texto LLM contém controles ou quebras excessivas.')
    try:
        clean = text(value, limit)
    except (TypeError, ValueError) as exc:
        raise InvalidProposal('Texto LLM inválido.') from exc
    if (any(c in clean for c in '<>' + chr(96)) or URL_PATTERN.search(clean)
            or any(pattern.search(clean) for pattern in FORBIDDEN_PATTERNS)):
        raise InvalidProposal('Marcação, endereço, comando ou instrução não permitido.')
    return clean.replace('\\\\n', ' ')


def _digest(kind, identity):
    return hashlib.sha256(json.dumps([kind, identity], sort_keys=True).encode()).hexdigest()[:24]


def validate_model_proposals(message, evidence, memory, output):
    hypotheses = output.get('hypotheses')
    recommendations = output.get('recommendations')
    if (type(hypotheses) is not list or type(recommendations) is not list
            or len(hypotheses) > 10 or len(recommendations) > 50):
        raise InvalidProposal('Limite de propostas inválido.')
    known = {e['id']: e for e in evidence}
    memory_by_id = {h['id']: h for h in memory}
    aliases = {}
    n = 0
    for e in evidence:
        if e['kind'] not in {'infra', 'recon'}:
            continue
        for asset in e['payload'].get('assets', [])[:50]:
            n += 1
            aliases['asset-' + str(n)] = (asset, e['id'])
    out_h, out_r = [], []
    for proposal in hypotheses:
        if type(proposal) is not dict or message.profile == Profile.BLUE:
            raise InvalidProposal('Hipótese inválida para perfil.')
        refs = proposal.get('evidence_ids')
        if (type(refs) is not list or not 1 <= len(refs) <= 10 or
                any(type(x) is not str for x in refs) or
                not set(refs) <= set(message.evidence_ids) or
                not set(refs) <= set(known)):
            raise InvalidProposal('Referência a evidência inexistente ou fora do contrato.')
        sev = proposal.get('severity')
        if type(sev) is not str or sev not in SEVERITIES:
            raise InvalidProposal('Severidade inválida.')
        title = _check_text(proposal.get('title'), 160)
        caveat = _check_text(proposal.get('uncertainty'), 500)
        refs = sorted(set(refs))
        if message.profile == Profile.RED:
            if set(proposal) != {'asset_alias', 'service', 'evidence_ids', 'severity', 'title', 'uncertainty'}:
                raise InvalidProposal('Contrato Red inválido.')
            alias, service = proposal['asset_alias'], proposal['service']
            if type(alias) is not str or alias not in aliases or type(service) is not str or service not in SERVICES:
                raise InvalidProposal('Ativo ou serviço desconhecido.')
            asset, source = aliases[alias]
            observed = [v if isinstance(v, str) else v.get('name') for v in asset.get('services', [])]
            if source not in refs or service not in observed:
                raise InvalidProposal('Serviço não foi observado na evidência citada.')
            # O hash das regras de infraestrutura usa o tipo e a porta;
            # conservar a identidade original para evitar duplicatas com LLM.
            observed_service = next((
                v for v in asset.get('services', [])
                if (v if isinstance(v, str) else v.get('name')) == service
            ), None)
            if isinstance(observed_service, dict) and observed_service.get('published') == 'yes' and service == 'dokploy':
                key = _digest('management-surface', [asset['asset'], service, observed_service.get('port')])
            elif isinstance(observed_service, dict) and observed_service.get('published') == 'yes' and service == 'minio':
                key = _digest('object-storage-surface', [asset['asset'], service, observed_service.get('port')])
            elif isinstance(observed_service, dict) and observed_service.get('privileged') == 'yes' and service == 'buildkit':
                key = _digest('privileged-build', [asset['asset'], service])
            else:
                key = _digest('exposure', [asset['asset'], service])
        elif message.profile == Profile.STATIC:
            if set(proposal) != {'rule', 'evidence_ids', 'severity', 'title', 'uncertainty'}:
                raise InvalidProposal('Contrato Static inválido.')
            try:
                rule = RuleAliases(evidence).resolve(proposal['rule'])
            except ValueError as exc:
                raise InvalidProposal('Regra inválida.') from exc
            if not any(known[r]['kind'] == 'scanner' and
                       any(a['rule_id'] == rule for a in known[r]['payload'].get('alerts', []))
                       for r in refs):
                raise InvalidProposal('Regra sem evidência correspondente.')
            floors = [scanner_severity(a['severity']) for r in refs
                      if known[r]['kind'] == 'scanner'
                      for a in known[r]['payload'].get('alerts', []) if a['rule_id'] == rule]
            floor = max(floors, key=lambda v: SEVERITY_ORDER.get(v, -1))
            if SEVERITY_ORDER.get(sev, -1) < SEVERITY_ORDER.get(floor, -1):
                caveat += (' modelo discorda do scanner; manter severidade do scanner como piso'
                           f' (modelo: {sev}; piso: {floor}).')
                sev = floor
            key = _digest('static-llm-group', [rule, refs])
        else:
            raise InvalidProposal('Perfil não aceita hipótese.')
        out_h.append({'id': key, 'title': title, 'severity': sev, 'evidence': refs,
                      'controls': ['Conferir hipótese com evidência independente.'],
                      'uncertainty': caveat + ' Sugestão de modelo não verificada.',
                      'origin': 'llm'})
    if message.profile != Profile.BLUE and recommendations:
        raise InvalidProposal('Recomendações pertencem ao Blue.')
    for rec in recommendations:
        if type(rec) is not dict or set(rec) != {
            'hypothesis_id', 'mitigation', 'compensating_control', 'validation', 'incident_response'
        }:
            raise InvalidProposal('Contrato Blue inválido.')
        key = rec['hypothesis_id']
        if type(key) is not str or key not in memory_by_id:
            raise InvalidProposal('Referência a hipótese inexistente.')
        candidate = memory_by_id[key]
        if candidate.get('status') == 'rejected':
            continue
        out_r.append({
            'hypothesis_id': key, 'priority': candidate['severity'],
            'controls_to_verify': candidate['controls'] + [_check_text(rec['compensating_control'], 500)],
            'mitigation': _check_text(rec['mitigation'], 500),
            'validation': _check_text(rec['validation'], 500),
            'incident_response': _check_text(rec['incident_response'], 500),
            'evidence': candidate['evidence'], 'origin': 'llm',
            'applied': False, 'independent_confirmation': False,
        })
    return {'hypotheses': out_h, 'recommendations': out_r}
