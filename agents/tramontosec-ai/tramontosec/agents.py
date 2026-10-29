"""Three specialists with read-only tools and explicit limits on evidence."""
from __future__ import annotations

import hashlib
import json

from .contracts import AgentResult, Profile, TaskMessage
from .policy import authorize, check_message
from .providers import Provider, ProviderError, validate_assessment


def hypothesis(kind: str, identity: list, title: str, severity: str,
               evidence: str, controls: list[str], uncertainty: str) -> dict:
    key = hashlib.sha256(json.dumps([kind, identity], sort_keys=True).encode()).hexdigest()[:24]
    return {'id': key, 'title': title, 'severity': severity, 'evidence': [evidence],
            'controls': controls, 'uncertainty': uncertainty}


def analyze_recon(message: TaskMessage, evidence: list[dict], memory: list[dict]) -> dict:
    candidates = []
    for item in evidence:
        if item['kind'] != 'recon':
            continue
        for asset in item['payload']['assets']:
            services = asset['services']
            for service, severity in (('http', 'Média'), ('database', 'Alta'), ('ssh', 'Baixa')):
                if service in services:
                    candidates.append(hypothesis(
                        'exposure', [asset['asset'], service],
                        f'Investigar superfície {service} em {asset["asset"]}', severity, item['id'],
                        ['Verificar ACL e alcance real do serviço.',
                         'Conferir autenticação, TLS e registros defensivos.'],
                        'Metadados passivos não demonstram exploração. Controles declarados não foram testados.'))
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
    recommendations = []
    for candidate in memory:
        recommendations.append({
            'hypothesis_id': candidate['id'], 'priority': candidate['severity'],
            'controls_to_verify': candidate['controls'],
            'mitigation': 'Revisar exposição e aplicar menor privilégio após validação e aprovação humana.',
            'validation': 'Auditor deve conferir contraprovas, revisar a correção e repetir a análise autorizada.',
            'incident_response': 'Se houver evidência independente de incidente, acionar o procedimento humano de triagem, preservação e contenção.',
            'applied': False, 'evidence': candidate['evidence'],
            'independent_confirmation': False,
        })
    return {'hypotheses': [], 'recommendations': recommendations}


IMPLEMENTATIONS = {'analyze_recon': analyze_recon, 'analyze_static': analyze_static, 'review_controls': review_controls}


class Specialist:
    def __init__(self, profile: Profile):
        self.profile = profile

    def run(self, message: TaskMessage, evidence: list[dict], memory: list[dict],
            provider: Provider | None = None) -> AgentResult:
        check_message(message, message.project)
        if message.profile != self.profile or {e['id'] for e in evidence} != set(message.evidence_ids):
            raise PermissionError('Evidências ou perfil não correspondem ao contrato.')
        assessment, uncertainties = None, ['Concordância entre especialistas não constitui evidência independente.']
        mode = 'deterministic'
        selected = list(message.allowed_tools)
        if provider:
            # Omit objective text, asset identifiers, file paths and source. Only counts/IDs go to Ollama.
            meta = {'profile': self.profile.value, 'stage': message.stage,
                    'evidence': [{'id': e['id'], 'kind': e['kind'],
                                  'alert_count': len(e['payload'].get('alerts', [])),
                                  'rules': [{'rule': a['rule_id'], 'severity': a['severity']} for a in e['payload'].get('alerts', [])[:20]],
                                  'surfaces': [{'services': a['services'], 'declared_controls': a['controls']}
                                               for a in e['payload'].get('assets', [])[:20]],
                                  'asset_count': len(e['payload'].get('assets', []))} for e in evidence[:100]],
                    'candidate_count': len(memory), 'allowed_tools': selected}
            try:
                assessment = validate_assessment(provider.assess(message, meta), message)
                mode = 'local_llm_assisted'
                # Controlled tool selection: model may select only allowlisted metadata tools.
                selected = assessment['proposed_tools'] or selected
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
        return AgentResult(message.task_id, self.profile, mode, tuple(findings), tuple(recommendations),
                           tuple(uncertainties), message.evidence_ids, assessment)
