"""Bounded import of passive recon, sanitized scanner metadata and Git baselines."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .core import now, open_db
from .git_readonly import compare_commit, inspect_repo
from .scanners import MAX_ALERTS, _READERS
from .store import event, get_project, project_root

MAX_INPUT = 20_000_000


def bounded_json(path: Path):
    if not path.is_file() or path.stat().st_size > MAX_INPUT:
        raise ValueError('Entrada ausente ou acima de 20 MB.')
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT:
        raise ValueError('Entrada excedeu o limite de tamanho.')
    try:
        return hashlib.sha256(raw).hexdigest(), json.loads(raw.decode('utf-8-sig'))
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('JSON inválido ou excessivamente aninhado.') from exc


def save_evidence(workspace: Path, project: str, kind: str, digest: str, payload: dict) -> str:
    get_project(workspace, project)
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    key = hashlib.sha256((kind + digest + body).encode()).hexdigest()
    with open_db(project_root(workspace, project)) as db:
        if db.execute("SELECT status FROM stages WHERE name='finalizacao'").fetchone()[0] == 'completed':
            raise PermissionError('Avaliação finalizada; crie outra avaliação para novas evidências.')
        added = db.execute('INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?)',
                          (key, kind, digest, body, now())).rowcount
        if added:
            # New evidence invalidates preparation and subsequent human sign-offs.
            db.execute("UPDATE stages SET status='pending', reviewer=NULL,reason=NULL,reviewed_at=NULL "
                       "WHERE name IN ('preparacao','execucao','finalizacao')")
            event(db, 'evidence_imported', {'id': key, 'kind': kind, 'sha256': digest})
    return key


def import_recon(workspace: Path, project: str, path: Path, ack: bool) -> str:
    info = get_project(workspace, project)
    if not ack:
        raise PermissionError('Confirme sanitização e coleta previamente autorizada (--ack-redacted-input).')
    digest, data = bounded_json(path)
    if not isinstance(data, dict) or set(data) != {'synthetic', 'assets'} or type(data['synthetic']) is not bool:
        raise ValueError('Reconhecimento exige synthetic:boolean e assets:[].')
    if data['synthetic'] != info['synthetic']:
        raise ValueError('Origem sintética incompatível com o projeto.')
    assets = data['assets']
    if not isinstance(assets, list) or not assets or len(assets) > 100:
        raise ValueError('Reconhecimento deve conter de 1 a 100 ativos.')
    cleaned = []
    for item in assets:
        if not isinstance(item, dict) or set(item) != {'asset', 'services', 'controls'}:
            raise ValueError('Ativo exige somente asset, services e controls.')
        if item['asset'] not in info['scope']['assets']:
            raise PermissionError('Ativo fora do escopo autorizado.')
        services, controls = item['services'], item['controls']
        if (not isinstance(services, list) or len(services) > 30
                or any(s not in ('http', 'https', 'ssh', 'dns', 'database', 'unknown') for s in services)
                or not isinstance(controls, list) or len(controls) > 20
                or any(c not in ('tls', 'mfa', 'network_acl', 'waf', 'logging', 'unknown') for c in controls)):
            raise ValueError('Serviços ou controles fora do vocabulário permitido.')
        cleaned.append({'asset': item['asset'], 'services': sorted(set(services)), 'controls': sorted(set(controls))})
    return save_evidence(workspace, project, 'recon', digest,
                         {'synthetic': data['synthetic'], 'assets': cleaned})


def import_scanner(workspace: Path, project: str, tool: str, path: Path,
                   ack: bool, commit: str | None = None) -> str:
    info = get_project(workspace, project)
    if not ack:
        raise PermissionError('Importe apenas resultados sanitizados (--ack-redacted-input).')
    # Validate before the legacy parser; no secret-bearing arbitrary strings in new storage.
    digest, data = bounded_json(path)
    if tool not in _READERS:
        raise ValueError('Scanner não suportado.')
    try:
        alerts = []
        for alert in _READERS[tool](data):
            alerts.append(alert)
            if len(alerts) > MAX_ALERTS:
                raise ValueError('Número de alertas acima do limite.')
    except (TypeError, AttributeError, RecursionError) as exc:
        raise ValueError('Estrutura de scanner inválida.') from exc
    if commit is not None and not re.fullmatch(r'[a-fA-F0-9]{40}', commit):
        raise ValueError('Commit deve ser SHA-1 completo; não use branch ou expressão Git.')
    for alert in alerts:
        for field in ('rule_id', 'component'):
            value = alert[field]
            if value and not re.fullmatch(r'[A-Za-z0-9_.:/@+-]{1,160}', value):
                raise ValueError('Metadado de scanner contém texto não sanitizado.')
        if not re.fullmatch(r'[A-Za-z0-9_./@+\[\]-]{1,260}', alert['location']):
            raise ValueError('Localização de scanner não sanitizada.')
        if alert['severity'].upper() not in ('ERROR', 'WARNING', 'INFO', 'CRITICAL', 'HIGH',
                                           'MEDIUM', 'LOW', 'UNKNOWN', 'POTENTIAL_SECRET', ''):
            raise ValueError('Severidade de scanner desconhecida.')
    unique = {json.dumps(a, sort_keys=True): a for a in alerts}
    return save_evidence(workspace, project, 'scanner', digest,
                         {'tool': tool, 'alerts': list(unique.values()), 'commit': commit,
                          'synthetic': info['synthetic'], 'review': 'human_required'})


def baseline(workspace: Path, project: str, expected: str) -> dict:
    info = get_project(workspace, project)
    repo = info['scope']['repo']
    if not repo:
        raise PermissionError('Nenhum repositório local foi autorizado neste projeto.')
    state = inspect_repo(Path(repo))
    result = {**state, **compare_commit(expected, state), 'expected_commit': expected.lower()}
    if not result['baseline_valid']:
        raise ValueError('Baseline inválida: exija HEAD exato e árvore de trabalho limpa.')
    result['evidence_id'] = save_evidence(workspace, project, 'baseline',
                                         hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest(), result)
    return result


def analyze_local(workspace: Path, project: str, relative: str) -> str:
    """Parse Python AST only. No imports, exec, network, scanners or writes to target."""
    import ast
    from .core import _inside_repository
    info = get_project(workspace, project)
    if not info['scope']['repo']:
        raise PermissionError('Autorize um repositório local ao criar o projeto.')
    repo = Path(info['scope']['repo'])
    with open_db(project_root(workspace, project)) as db:
        rows = db.execute("SELECT payload FROM evidence WHERE kind='baseline'").fetchall()
    state = inspect_repo(repo)
    if not any(compare_commit(json.loads(r[0])['expected_commit'], state)['baseline_valid'] for r in rows):
        raise PermissionError('Análise local exige baseline Git previamente registrada e ainda válida.')
    path = _inside_repository(repo, relative)
    if path.suffix != '.py' or not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError('Análise AST aceita somente arquivo Python de até 1 MB.')
    source = path.read_bytes()
    if len(source) > 1_000_000:
        raise ValueError('Arquivo excedeu 1 MB.')
    try:
        tree = ast.parse(source, filename='authorized-source.py')
    except (SyntaxError, RecursionError) as exc:
        raise ValueError('Arquivo Python não pôde ser analisado por AST.') from exc
    alerts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('eval', 'exec'):
            alerts.append({'rule_id': 'python.dynamic-execution', 'location': relative.replace('\\', '/'),
                           'line': node.lineno, 'component': '', 'severity': 'WARNING'})
    if not compare_commit(state['head'], inspect_repo(repo))['baseline_valid']:
        raise PermissionError('Baseline alterada durante a análise; resultado descartado.')
    return save_evidence(workspace, project, 'scanner', hashlib.sha256(source).hexdigest(),
                         {'tool': 'python-ast', 'alerts': alerts, 'commit': state['head'],
                          'synthetic': info['synthetic'], 'review': 'human_required'})
