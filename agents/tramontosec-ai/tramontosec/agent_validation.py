"""Contratos estritos para sugestões LLM; nenhuma confirmação ou mudança automática."""
from __future__ import annotations

import hashlib
import json

from .contracts import Profile, text

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


def _check_text(value, limit):
    try:
        clean = text(value, limit)
    except (TypeError, ValueError) as exc:
        raise InvalidProposal('Texto LLM inválido.') from exc
    if any(c in clean for c in '<>' + chr(96)) or 'http://' in clean or 'https://' in clean:
        raise InvalidProposal('Marcação ou endereço não permitido.')
    return clean.replace('\\n', ' ')


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
            rule = proposal['rule']
            if type(rule) is not str or not 1 <= len(rule) <= 160:
                raise InvalidProposal('Regra inválida.')
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
