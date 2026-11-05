"""Three specialists with read-only tools and explicit limits on evidence."""
from __future__ import annotations

import hashlib
import json

from .contracts import AgentResult, Profile, TaskMessage
from .agent_loop import AgentLoopError, run_agent_loop
from .agent_validation import InvalidProposal, validate_model_proposals
from .policy import authorize, check_message
from .red_team import analyze_infra
from .providers import Provider, ProviderError, validate_assessment


def hypothesis(kind: str, identity: list, title: str, severity: str,
               evidence: str, controls: list[str], uncertainty: str) -> dict:
    key = hashlib.sha256(json.dumps([kind, identity], sort_keys=True).encode()).hexdigest()[:24]
    return {'id': key, 'title': title, 'severity': severity, 'evidence': [evidence],
            'controls': controls, 'uncertainty': uncertainty}


def analyze_recon(message: TaskMessage, evidence: list[dict], memory: list[dict]) -> dict:
    """Prioriza triagem, sem tratar controles declarados como controles comprovados."""
    candidates = []
    relevance = {
        'database': ('Alta', {'network_acl'}),
        'http': ('Média', {'waf', 'tls'}),
        'https': ('Média', {'waf', 'tls'}),
        'ssh': ('Baixa', {'mfa', 'network_acl'}),
    }
    previous_level = {'Crítica': 'Alta', 'Alta': 'Média', 'Média': 'Baixa', 'Baixa': 'Baixa'}
    for item in evidence:
        if item['kind'] != 'recon':
            continue
        for asset in item['payload']['assets']:
            controls = set(asset.get('controls', []))
            for service in asset['services']:
                if service not in relevance:
                    continue
                severity, relevant = relevance[service]
                matched = sorted(controls & relevant)
                if matched:
                    severity = previous_level[severity]
                caveat = 'Metadados passivos não demonstram exploração.'
                if matched:
                    caveat += (' Controles declarados (' + ', '.join(matched) +
                               ') reduziram a prioridade em um nível; não foram testados.')
                else:
                    caveat += ' A eficácia dos controles não foi testada.'
                candidates.append(hypothesis(
                    'exposure', [asset['asset'], service],
                    f'Investigar superfície {service} em {asset["asset"]}', severity, item['id'],
                    ['Verificar ACL e alcance real do serviço.',
                     'Conferir autenticação, TLS e registros defensivos.'],
                    caveat))
    return {'hypotheses': candidates, 'recommendations': []}


def analyze_static(message: TaskMessage, evidence: list[dict], memory: list[dict]) -> dict:
    candidates = []
    for item in evidence:
        if item['kind'] != 'scanner':
            continue
        data = item['payload']
        for alert in data['alerts']:
            # Same rule+location+commit correlates across reports without claiming independence.
            candidates.append(hypothesis(
                'static', [alert['rule_id'], alert['location'], alert['line'], alert['component'], data['commit']],
                f'Revisar {alert["rule_id"]} em {alert["location"]}:{alert["line"] or "?"}',
                {'CRITICAL': 'Crítica', 'HIGH': 'Alta', 'MEDIUM': 'Média', 'LOW': 'Baixa'}.get(alert['severity'].upper(), 'Indeterminada'),
                item['id'], ['Inspecionar caminho alcançável, autenticação e autorização.',
                             'Conferir versão implantada, sanitização e falso positivo.'],
                'Alerta de ferramenta não confirma vulnerabilidade. '
                + ('Commit informado exige conferência com a baseline.' if data['commit'] else 'Commit de origem não informado.')))
    return {'hypotheses': candidates, 'recommendations': []}


def review_controls(message: TaskMessage, evidence: list[dict], memory: list[dict]) -> dict:
    """Recomendações específicas sem aplicar mudanças nem validar incidentes."""
    recommendations = []
    for candidate in memory:
        if candidate.get('status') == 'rejected':
            continue
        title = candidate.get('title', '').lower()
        profiles = candidate.get('profiles', [])
        if 'static' in profiles or title.startswith('revisar '):
            mitigation = 'Revisar a regra e o contexto do alerta; corrigir a causa apenas após confirmar o caminho afetado.'
            validation = 'Conferir regra, versão, localização e executar novamente a análise estática no baseline aprovado.'
            incident = 'Se o alerta indicar incidente confirmado, preservar versão e registros; acionar resposta com o time de aplicação.'
            if 'secret' in title or 'password' in title:
                mitigation = 'Avaliar exposição real da credencial; planejar rotação autorizada sem divulgar seu valor.'
                validation = 'Confirmar escopo e revisar histórico sanitizado e controles de gestão de segredos.'
        elif 'ssh' in title or 'autenticação' in title:
            mitigation = 'Conferir acesso administrativo, origens autorizadas e autenticação, com plano de continuidade aprovado.'
            validation = 'Validar a configuração e o caminho de recuperação sem interromper sessões legítimas.'
            incident = 'Correlacionar logins aceitos com responsáveis e preservar registros antes de qualquer contenção.'
        elif 'database' in title or 'banco' in title:
            mitigation = 'Revisar ACL de banco, papéis e origem dos clientes autorizados antes de restringir acesso.'
            validation = 'Conferir alcance e autenticação com verificações previamente autorizadas e não destrutivas.'
            incident = 'Se houver acesso indevido comprovado, preservar trilhas do banco e escalar a resposta.'
        elif 'minio' in title or 's3' in title:
            mitigation = 'Revisar política de buckets, TLS e consumidores de objetos antes de limitar a API.'
            validation = 'Confirmar clientes internos/externos e URLs pré-assinadas sem ler dados sensíveis.'
            incident = 'Caso haja evidência de acesso não autorizado, preservar logs de objeto e notificar responsáveis.'
        else:
            mitigation = 'Revisar exposição do serviço e aplicar menor privilégio somente após validação e aprovação humana.'
            validation = 'Verificar alcance real, dependências e controles compensatórios após mudança autorizada.'
            incident = 'Caso surjam evidências independentes de intrusão, preservar logs e acionar triagem humana.'
        recommendations.append({
            'hypothesis_id': candidate['id'], 'priority': candidate['severity'],
            'controls_to_verify': candidate['controls'],
            'mitigation': mitigation,
            'validation': validation,
            'incident_response': incident,
            'applied': False, 'evidence': candidate['evidence'],
            'independent_confirmation': False,
        })
    return {'hypotheses': [], 'recommendations': recommendations}


IMPLEMENTATIONS = {'analyze_recon': analyze_recon, 'analyze_infra': analyze_infra, 'analyze_static': analyze_static, 'review_controls': review_controls}


class Specialist:
    def __init__(self, profile: Profile):
        self.profile = profile

    def run(self, message: TaskMessage, evidence: list[dict], memory: list[dict],
            provider: Provider | None = None) -> AgentResult:
        check_message(message, message.project)
        if message.profile != self.profile or {e['id'] for e in evidence} != set(message.evidence_ids):
            raise PermissionError('Evidências ou perfil não correspondem ao contrato.')
        assessment, uncertainties = None, ['Concordância entre especialistas não constitui evidência independente.']
        model_hypotheses, model_recommendations, trace = [], [], ()
        mode = 'deterministic'
        selected = list(message.allowed_tools)
        if provider and self.profile in (Profile.RED, Profile.STATIC) and callable(getattr(provider, 'agent_step', None)):
            try:
                raw = run_agent_loop(provider, message, evidence, memory)
                parsed = validate_model_proposals(message, evidence, memory, raw)
                model_hypotheses, model_recommendations = parsed['hypotheses'], parsed['recommendations']
                trace = tuple(raw['reasoning_trace'])
                mode = 'local_llm_agent'
            except (AgentLoopError, InvalidProposal, PermissionError, ProviderError,
                    OSError, TimeoutError, TypeError, KeyError, RecursionError, StopIteration):
                uncertainties.append('Proposta LLM inválida ou bloqueada; regras determinísticas preservadas.')
                mode = 'deterministic_fallback'
        elif provider:
            # Omit objective text, asset identifiers, file paths and source. Only counts/IDs go to Ollama.
            meta = {'profile': self.profile.value, 'stage': message.stage,
                    'evidence': [{'id': e['id'], 'kind': e['kind'],
                                  'alert_count': len(e['payload'].get('alerts', [])),
                                  'rules': [{'rule': a['rule_id'], 'severity': a['severity']} for a in e['payload'].get('alerts', [])[:20]],
                                  'surfaces': [{'services': [v if isinstance(v, str) else v.get('name', 'other')
                                                               for v in a.get('services', [])[:30]],
                                                'declared_controls': a.get('controls', [])}
                                               for a in e['payload'].get('assets', [])[:20]],
                                  'asset_count': len(e['payload'].get('assets', []))} for e in evidence[:100]],
                    'candidate_count': len(memory), 'allowed_tools': selected}
            try:
                assessment = validate_assessment(provider.assess(message, meta), message)
                mode = 'local_llm_assisted'
                # Parecer consultivo: o modelo não determina o conjunto de regras executadas.
            except (ProviderError, OSError, TimeoutError):
                uncertainties.append('Provedor falhou ou retornou dados inválidos. Sem inferência utilizável; fallback determinístico.')
                mode = 'deterministic_fallback'
        else:
            uncertainties.append('Sem modelo habilitado: processamento determinístico, sem inferência de IA.')
        findings, recommendations = [], []
        for name in selected:
            authorize(self.profile, name)
            output = IMPLEMENTATIONS[name](message, evidence, memory)
            findings.extend(output['hypotheses'])
            recommendations.extend(output['recommendations'])
        # Identidades de regra são estáveis; correspondências LLM não sobrescrevem seu ID.
        known = {h['id']: h for h in findings}
        for candidate in findings:
            candidate.setdefault('origin', 'rule')
        for candidate in model_hypotheses:
            existing = known.get(candidate['id'])
            if existing:
                existing['uncertainty'] += ' O modelo propôs hipótese equivalente; sugestão não verificada.'
            else:
                findings.append(candidate)
                known[candidate['id']] = candidate
        recommendations.extend(model_recommendations)
        return AgentResult(message.task_id, self.profile, mode, tuple(findings), tuple(recommendations),
                           tuple(uncertainties), message.evidence_ids, assessment,
                           reasoning_trace=trace)
