"""Red Team: interpretação passiva de metadados sanitizados, sem contato com alvos.

O agente formula hipóteses condicionais, nunca confirma exploração ou aplica regras.
"""
from __future__ import annotations

import hashlib
import json

SCHEMA = 'tramontosec.infra.v1'
YES_NO_UNKNOWN = frozenset({'yes', 'no', 'unknown'})
SERVICES = frozenset({'dokploy', 'minio', 'buildkit', 'ssh', 'http', 'https', 'database', 'other'})
SOCKET = frozenset({'rw', 'ro', 'none', 'unknown'})
REACHABILITY = YES_NO_UNKNOWN


def _object(value: object, allowed: set[str], required: set[str] = frozenset()) -> dict:
    if type(value) is not dict or not required <= value.keys() or not value.keys() <= allowed:
        raise ValueError('Campo de infraestrutura fora do esquema permitido.')
    return value


def _enum(value: object, choices: frozenset[str]) -> str:
    if type(value) is not str or value not in choices:
        raise ValueError('Valor de infraestrutura fora do vocabulário permitido.')
    return value


def _integer(value: object, lower: int, upper: int) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError('Contagem ou porta inválida.')
    return value


def normalize_infrastructure(data: object, scope_assets: set[str], synthetic: bool) -> dict:
    """Valida e normaliza apenas enums, números e aliases do escopo, sem texto livre."""
    root = _object(data, {'schema', 'synthetic', 'assets'}, {'schema', 'synthetic', 'assets'})
    if root['schema'] != SCHEMA or type(root['synthetic']) is not bool or root['synthetic'] != synthetic:
        raise ValueError('Esquema ou natureza sintética incompatível com o projeto.')
    rows = root['assets']
    if type(rows) is not list or not 1 <= len(rows) <= 50:
        raise ValueError('Informe de 1 a 50 ativos autorizados.')
    normalized, seen = [], set()
    for item in rows:
        a = _object(item, {'asset', 'network', 'services', 'auth', 'availability', 'access'}, {'asset'})
        name = a['asset']
        if type(name) is not str or name not in scope_assets or name in seen:
            raise PermissionError('Ativo não autorizado ou repetido na evidência.')
        seen.add(name)
        result = {'asset': name}
        if 'network' in a:
            v = _object(a['network'], {'host_input', 'edge_filter'})
            result['network'] = {
                'host_input': _enum(v.get('host_input', 'unknown'), frozenset({'accept', 'drop', 'unknown'})),
                'edge_filter': _enum(v.get('edge_filter', 'unknown'), frozenset({'enabled', 'disabled', 'unknown'})),
            }
        if 'auth' in a:
            v = _object(a['auth'], {'root_password_ssh'})
            result['auth'] = {'root_password_ssh': _enum(v.get('root_password_ssh', 'unknown'), YES_NO_UNKNOWN)}
        if 'availability' in a:
            v = _object(a['availability'], {'nodes', 'restore_tested'})
            result['availability'] = {
                'nodes': _integer(v['nodes'], 1, 10000) if 'nodes' in v else None,
                'restore_tested': _enum(v.get('restore_tested', 'unknown'), YES_NO_UNKNOWN),
            }
        if 'access' in a:
            v = _object(a['access'], {'failed_logins', 'unknown_accepted'})
            result['access'] = {
                'failed_logins': _integer(v['failed_logins'], 0, 10_000_000) if 'failed_logins' in v else None,
                'unknown_accepted': _enum(v.get('unknown_accepted', 'unknown'), YES_NO_UNKNOWN),
            }
        if 'services' in a:
            services = a['services']
            if type(services) is not list or len(services) > 25:
                raise ValueError('Quantidade de serviços excedida.')
            clean_services, service_keys = [], set()
            for entry in services:
                v = _object(entry, {'name', 'port', 'published', 'ipv4', 'ipv6',
                                    'reachable', 'socket', 'privileged'}, {'name'})
                service = {
                    'name': _enum(v['name'], SERVICES),
                    'port': None if v.get('port') is None else _integer(v['port'], 1, 65535),
                    'published': _enum(v.get('published', 'unknown'), YES_NO_UNKNOWN),
                    'ipv4': _enum(v.get('ipv4', 'unknown'), YES_NO_UNKNOWN),
                    'ipv6': _enum(v.get('ipv6', 'unknown'), YES_NO_UNKNOWN),
                    'reachable': _enum(v.get('reachable', 'unknown'), REACHABILITY),
                    'socket': _enum(v.get('socket', 'unknown'), SOCKET),
                    'privileged': _enum(v.get('privileged', 'unknown'), YES_NO_UNKNOWN),
                }
                if service['published'] == 'yes' and service['port'] is None:
                    raise ValueError('Publicação de serviço precisa informar a porta.')
                key = (service['name'], service['port'])
                if key in service_keys:
                    raise ValueError('Serviço/porta duplicado; consolide a observação.')
                service_keys.add(key)
                clean_services.append(service)
            result['services'] = sorted(clean_services, key=lambda s: (s['name'], s['port'] or 0))
        if len(result) == 1:
            raise ValueError('O ativo deve conter observações técnicas.')
        normalized.append(result)
    return {'schema': SCHEMA, 'synthetic': synthetic,
            'assets': sorted(normalized, key=lambda a: a['asset']),
            'review': 'human_required', 'collection': 'preexisting_sanitized_metadata_only'}


def _candidate(kind: str, identity: list, title: str, severity: str,
               source: str, caveat: str, checks: list[str]) -> dict:
    token = json.dumps([kind, identity], ensure_ascii=False, sort_keys=True)
    return {
        'id': hashlib.sha256(token.encode()).hexdigest()[:24],
        'title': title,
        'severity': severity,
        'evidence': [source],
        'controls': checks,
        'uncertainty': caveat,
    }


def analyze_infra(message, evidence: list[dict], memory: list[dict]) -> dict:
    """Usa somente evidências já importadas; nunca executa comandos nem acessa rede."""
    findings = []
    for record in evidence:
        if record.get('kind') != 'infra':
            continue
        source, data = record['id'], record['payload']
        if data.get('schema') != SCHEMA:
            raise ValueError('Evidência de infraestrutura com esquema desconhecido.')
        for item in data['assets']:
            asset = item['asset']
            network = item.get('network', {})
            if network.get('host_input') == 'accept' and network.get('edge_filter') != 'enabled':
                findings.append(_candidate(
                    'network-exposure', [asset], f'{asset}: revisar filtragem de entrada e proteção de borda',
                    'Média', source,
                    'Observação da política do host, não prova de ausência de firewall no provedor nem de alcance externo.',
                    ['Confirmar política efetiva IPv4/IPv6 e regras do provedor.',
                     'Inventariar serviços e conexões legítimas antes de aplicar restrições.']))
            if item.get('auth', {}).get('root_password_ssh') == 'yes':
                findings.append(_candidate(
                    'root-password', [asset], f'{asset}: autenticação administrativa root por senha',
                    'Alta', source,
                    'Configuração de risco; exploração, credencial comprometida ou login indevido não demonstrados.',
                    ['Verificar controles de acesso e origens permitidas; preservar logs.',
                     'Planejar migração com continuidade, autorização e acesso de recuperação.']))
            for svc in item.get('services', []):
                name, port = svc['name'], svc['port']
                exposed = svc['published'] == 'yes'
                if name == 'dokploy' and exposed:
                    findings.append(_candidate(
                        'management-surface', [asset, name, port],
                        f'{asset}: publicação administrativa de {name}/{port}', 'Alta', source,
                        'Porta publicada não confirma alcance externo nem falha de autenticação. '
                        'Socket Docker, quando montado, amplia o impacto de eventual comprometimento.',
                        ['Verificar alcance real em IPv4/IPv6 e controles HTTPS/MFA.',
                         'Identificar administradores e integrações antes de restringir a porta.',
                         'Verificar socket Docker, privilégios e rota alternativa de gestão.']))
                elif name == 'minio' and exposed:
                    findings.append(_candidate(
                        'object-storage-surface', [asset, name, port],
                        f'{asset}: exposição potencial da API S3/{port}', 'Alta', source,
                        'Publicação não comprova leitura indevida de objetos; políticas, TLS e consumidores são desconhecidos até validação.',
                        ['Identificar clientes internos/externos e URLs pré-assinadas.',
                         'Revisar TLS, política de bucket e operações autorizadas sem acessar dados reais.']))
                elif name == 'buildkit' and svc['privileged'] == 'yes':
                    findings.append(_candidate(
                        'privileged-build', [asset, name],
                        f'{asset}: executor de builds com privilégios elevados', 'Alta', source,
                        'Risco condicionado à possibilidade de submissão de build/contexto malicioso; escape do host não demonstrado.',
                        ['Verificar quem pode submeter builds e como os segredos são isolados.',
                         'Planejar executor substituto e ensaiar deploy sintético antes de migrar.']))
            availability = item.get('availability', {})
            if availability.get('nodes') == 1 and availability.get('restore_tested') != 'yes':
                findings.append(_candidate(
                    'resilience', [asset], f'{asset}: continuidade operacional sem redundância comprovada',
                    'Média', source,
                    'Risco de disponibilidade; existência de volumes ou arquivos candidatos não comprova backup restaurável.',
                    ['Confirmar cobertura, custódia e RPO/RTO.',
                     'Demonstrar recuperação em ambiente isolado, sem restaurar produção.']))
            access = item.get('access', {})
            if access.get('failed_logins') is not None and access['failed_logins'] >= 100:
                findings.append(_candidate(
                    'authentication-noise', [asset], f'{asset}: tentativas de autenticação a correlacionar',
                    'Média', source,
                    'Contagem de falhas não comprova intrusão nem identifica autoria; frequência isolada é indicador para triagem.',
                    ['Correlacionar período, fontes e logins aceitos nos registros retidos.',
                     'Validar eventos não reconhecidos com a equipe responsável.']))
    return {'hypotheses': findings, 'recommendations': []}
