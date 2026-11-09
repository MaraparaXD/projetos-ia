"""Loop consultivo limitado: ferramentas tipadas em memória, sem I/O nem alvo remoto.

Respostas do modelo são dados não confiáveis, não decisões. Uma falha gera
AgentLoopError; o especialista deve preservar o baseline determinístico.
"""
from __future__ import annotations

import json

from .agent_validation import InvalidProposal, _check_text
from .policy import allowed_read_tools, authorize_read_tool
from .scanners import RuleAliases, model_alert_level
from .providers import ProviderError


MAX_STEPS = 6
MAX_CONTEXT_CHARS = 18000
MAX_RESPONSE_CHARS = 12000
REASONS = {
    'list_assets': 'Consultar serviços e controles declarados, com aliases.',
    'get_alerts': 'Consultar regras e severidades sem caminhos de código.',
    'get_alert_summary': 'Contar alertas, arquivos e componentes por regra, sem identificá-los.',
    'read_evidence': 'Conferir metadados da evidência autorizada.',
    'list_hypotheses': 'Consultar hipóteses registradas e estados humanos.',
    'get_hypothesis': 'Conferir referência de hipótese sem dados sensíveis.',
}


class AgentLoopError(ValueError):
    pass


def _service_name(value):
    if isinstance(value, str):
        return value if value in {'http', 'https', 'ssh', 'dns', 'database', 'unknown'} else 'other'
    if isinstance(value, dict):
        name = value.get('name')
        return name if name in {'dokploy', 'minio', 'buildkit', 'ssh', 'http', 'https', 'database', 'other'} else 'other'
    return 'other'


def _summary_evidence(record):
    payload = record['payload']
    return {
        'id': record['id'], 'kind': record['kind'],
        'asset_count': len(payload.get('assets', [])),
        'alert_count': len(payload.get('alerts', [])),
    }


def readonly_tool(message, name, args, evidence, memory, rule_aliases=None):
    """Executa exclusivamente transformação em memória: não aceita texto livre."""
    authorize_read_tool(message.profile, name)
    if type(args) is not dict:
        raise AgentLoopError('Argumentos devem ser objeto.')
    if name == 'list_assets':
        if args:
            raise AgentLoopError('list_assets não aceita argumentos.')
        assets = []
        for record in evidence:
            if record['kind'] not in {'recon', 'infra'}:
                continue
            for asset in record['payload'].get('assets', [])[:50]:
                services = asset.get('services', [])
                assets.append({
                    'alias': 'asset-' + str(len(assets) + 1),
                    'evidence_id': record['id'],
                    'services': [_service_name(s) for s in services[:25]],
                    'declared_controls': [
                        s for s in asset.get('controls', [])[:20]
                        if s in {'tls', 'mfa', 'network_acl', 'waf', 'logging', 'unknown'}
                    ],
                })
        return {'assets': assets[:50]}
    if name == 'get_alert_summary':
        if not set(args) <= {'rule'}:
            raise AgentLoopError('Filtro desconhecido.')
        rule_aliases = rule_aliases or RuleAliases(evidence)
        rule = args.get('rule')
        if rule is not None:
            try:
                rule = rule_aliases.resolve(rule)
            except ValueError as exc:
                raise AgentLoopError('Regra de filtro inválida.') from exc
        groups = {}
        for record in evidence:
            if record['kind'] != 'scanner':
                continue
            for alert in record['payload'].get('alerts', []):
                raw_rule = alert['rule_id']
                if rule is not None and rule != raw_rule:
                    continue
                group = groups.setdefault(raw_rule, {'count': 0, 'levels': set(),
                                                     'files': set(), 'components': set()})
                group['count'] += 1
                group['levels'].add(model_alert_level(alert['severity']))
                if alert.get('location') and not alert['location'].startswith('[path-'):
                    group['files'].add(alert['location'])
                if alert.get('component'):
                    group['components'].add(alert['component'])
        rows = [{'rule': rule_aliases.to_model(key), 'alert_count': value['count'],
                 'severities': sorted(value['levels']), 'file_count': len(value['files']),
                 'component_count': len(value['components'])} for key, value in groups.items()]
        rows.sort(key=lambda row: row['rule'])
        return {'rules': rows[:100], 'rule_count': len(rows), 'truncated': len(rows) > 100}
    if name == 'get_alerts':
        if not set(args) <= {'rule', 'severity'}:
            raise AgentLoopError('Filtro desconhecido.')
        rule = args.get('rule')
        severity = args.get('severity')
        rule_aliases = rule_aliases or RuleAliases(evidence)
        if rule is not None:
            try:
                rule = rule_aliases.resolve(rule)
            except ValueError as exc:
                raise AgentLoopError('Regra de filtro inválida.') from exc
        if severity is not None and (type(severity) is not str or severity not in {'ERROR', 'WARNING', 'INFO', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'}):
            raise AgentLoopError('Severidade de filtro inválida.')
        alerts = []
        for record in evidence:
            if record['kind'] != 'scanner':
                continue
            for alert in record['payload'].get('alerts', [])[:100]:
                if rule is not None and alert['rule_id'] != rule:
                    continue
                if severity is not None and model_alert_level(alert['severity']) != severity:
                    continue
                alerts.append({'evidence_id': record['id'], 'rule': rule_aliases.to_model(alert['rule_id']),
                               'severity': model_alert_level(alert['severity'])})
        return {'alerts': alerts[:100]}
    if name == 'read_evidence':
        if set(args) != {'id'} or type(args['id']) is not str:
            raise AgentLoopError('ID obrigatório para evidência.')
        match = next((e for e in evidence if e['id'] == args['id']), None)
        if match is None or args['id'] not in message.evidence_ids:
            raise AgentLoopError('Evidência fora do contrato.')
        return _summary_evidence(match)
    if name == 'list_hypotheses':
        if not set(args) <= {'status'}:
            raise AgentLoopError('Filtro inválido.')
        status = args.get('status')
        if status is not None and status not in {'candidate', 'in_review', 'accepted', 'rejected'}:
            raise AgentLoopError('Estado inválido.')
        return {'hypotheses': [
            {'id': h['id'], 'severity': h['severity'], 'status': h.get('status', 'candidate')}
            for h in memory[:100] if status is None or h.get('status', 'candidate') == status
        ]}
    if name == 'get_hypothesis':
        if set(args) != {'id'} or type(args['id']) is not str:
            raise AgentLoopError('ID obrigatório para hipótese.')
        match = next((h for h in memory if h['id'] == args['id']), None)
        if match is None:
            raise AgentLoopError('Hipótese fora da memória do projeto.')
        return {'id': match['id'], 'severity': match['severity'],
                'status': match.get('status', 'candidate'), 'evidence_ids': match['evidence']}
    raise AgentLoopError('Ferramenta proibida.')


def run_agent_loop(provider, message, evidence, memory, max_steps=MAX_STEPS):
    """Preserva contagem e trilha sanitizada também em falhas, sem texto bruto."""
    stats = {'steps_used': 0, 'trace': []}
    try:
        return _run_agent_loop(provider, message, evidence, memory, max_steps, stats)
    except Exception as exc:
        exc.steps_used = stats['steps_used']
        exc.reasoning_trace = tuple(stats['trace'])
        raise


def _run_agent_loop(provider, message, evidence, memory, max_steps, stats):
    """Executa até max_steps chamadas, devolvendo final e trilha resumida."""
    if type(max_steps) is not int or not 1 <= max_steps <= 12:
        raise AgentLoopError('Limite de passos inválido.')
    trace = stats['trace']
    rule_aliases = RuleAliases(evidence)
    context = {
        'schema': 'tramontosec.loop.v1', 'profile': message.profile.value,
        'scope': 'metadados_sanitizados_offline', 'max_steps': max_steps,
        'allowed_tools': list(allowed_read_tools(message.profile)),
        'evidence': [_summary_evidence(e) for e in evidence[:100]],
        'hypotheses': [{'id': h['id'], 'severity': h['severity'],
                        'status': h.get('status', 'candidate')} for h in memory[:100]],
        'history': [],
    }
    if rule_aliases.used:
        context['rule_alias_used'] = True
    for _ in range(max_steps):
        if len(json.dumps(context, ensure_ascii=False)) > MAX_CONTEXT_CHARS:
            raise AgentLoopError('Contexto do modelo ultrapassou o orçamento.')
        stats['steps_used'] += 1
        try:
            result = provider.agent_step(message, context)
        except ProviderError:
            raise
        except (OSError, ValueError, TimeoutError, TypeError, KeyError) as exc:
            raise AgentLoopError('Falha no provedor consultivo.') from exc
        if (type(result) is not dict or len(json.dumps(result, ensure_ascii=False)) > MAX_RESPONSE_CHARS
                or result.get('action') not in {'tool', 'final'}):
            raise AgentLoopError('Ação do modelo malformada.')
        if result['action'] == 'final':
            if set(result) != {'action', 'hypotheses', 'recommendations'}:
                raise AgentLoopError('Resposta final fora do contrato.')
            if type(result['hypotheses']) is not list or type(result['recommendations']) is not list:
                raise AgentLoopError('Listas finais inválidas.')
            return {'hypotheses': result['hypotheses'], 'recommendations': result['recommendations'],
                    'reasoning_trace': trace, 'steps_used': stats['steps_used']}
        fields = {'action', 'tool', 'args'}
        if set(result) not in (fields, fields | {'why'}) or type(result['tool']) is not str:
            raise AgentLoopError('Chamada de ferramenta fora do contrato.')
        tool = result['tool']
        response = readonly_tool(message, tool, result['args'], evidence, memory, rule_aliases)
        try:
            model_note = _check_text(result.get('why'), 160)
        except InvalidProposal:
            model_note = None
        trace.append({'tool': tool, 'reason': REASONS[tool], 'model_note': model_note})
        context['history'].append({'tool': tool, 'result': response})
    raise AgentLoopError('Limite de passos atingido sem resposta final.')
