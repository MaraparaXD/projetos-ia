"""Per-project SQLite storage layered over the recovered core; no shared evidence DB."""
from __future__ import annotations

import json
from pathlib import Path

from .contracts import STAGES, identifier, text
from .core import make_workspace, no_sync_roots, now, open_db, require_workspace


def project_root(workspace: Path, project: str) -> Path:
    identifier(project)
    no_sync_roots(workspace)
    base = workspace.resolve() / 'projects'
    root = base / project
    if base.is_symlink() or root.is_symlink() or root.resolve().parent != base:
        raise PermissionError('Diretório de projeto deve permanecer dentro do workspace.')
    if (root / 'audit.sqlite3').is_symlink():
        raise PermissionError('Banco de projeto não pode ser link simbólico.')
    return root


def init_runtime(root: Path) -> None:
    # Separate schema marker avoids downgrading the recovered core's schema 2.
    with open_db(root) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS runtime_meta(version INTEGER NOT NULL);
        INSERT INTO runtime_meta SELECT 1 WHERE NOT EXISTS(SELECT 1 FROM runtime_meta);
        CREATE TABLE IF NOT EXISTS project(
          id TEXT PRIMARY KEY, name TEXT NOT NULL, scope_json TEXT NOT NULL,
          objective TEXT NOT NULL, synthetic INTEGER NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS stages(
          name TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'pending',
          reviewer TEXT, reason TEXT, reviewed_at TEXT);
        CREATE TABLE IF NOT EXISTS evidence(
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, sha256 TEXT NOT NULL,
          payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks(
          id TEXT PRIMARY KEY, profile TEXT NOT NULL, status TEXT NOT NULL,
          input_json TEXT NOT NULL, output_json TEXT, created_at TEXT NOT NULL,
          finished_at TEXT, error TEXT);
        CREATE TABLE IF NOT EXISTS hypotheses(
          id TEXT PRIMARY KEY, title TEXT NOT NULL, severity TEXT NOT NULL,
          evidence_json TEXT NOT NULL, uncertainty TEXT NOT NULL,
          controls_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'candidate',
          profiles_json TEXT NOT NULL, reviewer TEXT, reason TEXT, reviewed_at TEXT);
        CREATE TABLE IF NOT EXISTS recommendations(
          id TEXT PRIMARY KEY, hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
          payload TEXT NOT NULL, task_id TEXT NOT NULL REFERENCES tasks(id));
        CREATE TABLE IF NOT EXISTS runtime_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,
          verb TEXT NOT NULL, details TEXT NOT NULL);
        ''')


def event(db, verb: str, details: dict) -> None:
    db.execute('INSERT INTO runtime_events(at,verb,details) VALUES(?,?,?)',
               (now(), verb, json.dumps(details, ensure_ascii=False)))


def create_project(workspace: Path, project: str, name: str, objective: str,
                   assets: list[str], repo: Path | None = None, synthetic: bool = False,
                   ack: bool = False) -> dict:
    if not ack:
        raise PermissionError('Confirme autorização do escopo e guarda local segura (--ack-authorized).')
    name, objective = text(name, 160), text(objective, 2000)
    if not isinstance(assets, list) or not assets or len(assets) > 100:
        raise ValueError('Informe de 1 a 100 ativos exatos no escopo.')
    import re
    for asset in assets:
        if not isinstance(asset, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', asset):
            raise ValueError('Use nomes exatos de ativos, sem URLs, portas ou curingas.')
        if synthetic and not asset.endswith('.invalid'):
            raise ValueError('Demonstrações sintéticas exigem ativos no domínio reservado .invalid.')
    repo_path = str(repo.resolve(strict=True)) if repo else None
    if repo and not repo.is_dir():
        raise ValueError('Repositório autorizado deve ser um diretório local.')
    root = project_root(workspace, project)
    # Case-insensitive identity on all OSes; do not merge projects on Windows.
    if root.parent.exists() and any(p.name.casefold() == project.casefold() for p in root.parent.iterdir()):
        raise ValueError('Já existe projeto com este identificador.')
    make_workspace(root)
    init_runtime(root)
    scope = {'assets': sorted(set(assets)), 'repo': repo_path, 'active_testing': False,
             'auto_remediation': False, 'external_providers': False}
    with open_db(root) as db:
        db.execute('INSERT INTO project VALUES(?,?,?,?,?,?)',
                   (project, name, json.dumps(scope), objective, int(synthetic), now()))
        db.executemany('INSERT INTO stages(name) VALUES(?)', [(s,) for s in STAGES])
        event(db, 'project_created', {'project': project, 'authorized': True, 'synthetic': synthetic})
    return get_project(workspace, project)


def get_project(workspace: Path, project: str) -> dict:
    root = project_root(workspace, project)
    require_workspace(root)
    with open_db(root) as db:
        row = db.execute('SELECT * FROM project WHERE id=?', (project,)).fetchone()
    if row is None:
        raise KeyError('Projeto não encontrado.')
    result = dict(row)
    result['scope'] = json.loads(result.pop('scope_json'))
    result['synthetic'] = bool(result['synthetic'])
    return result


def list_projects(workspace: Path) -> list[dict]:
    base = workspace.resolve() / 'projects'
    if base.is_symlink():
        raise PermissionError('Diretório de projetos não pode ser link simbólico.')
    if not base.is_dir():
        return []
    result = []
    for path in sorted(base.iterdir()):
        if path.is_symlink():
            continue
        if path.is_dir() and (path / 'audit.sqlite3').is_file():
            result.append(get_project(workspace, path.name))
    return result


def snapshot(workspace: Path, project: str) -> dict:
    info = get_project(workspace, project)
    with open_db(project_root(workspace, project)) as db:
        tables = {}
        for table in ('stages', 'evidence', 'tasks', 'hypotheses', 'recommendations', 'runtime_events'):
            tables[table] = [dict(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
    for item in tables['evidence']:
        item['payload'] = json.loads(item['payload'])
    for item in tables['tasks']:
        item['input'] = json.loads(item.pop('input_json'))
        output = item.pop('output_json')
        item['output'] = json.loads(output) if output else None
    for item in tables['hypotheses']:
        for key in ('evidence', 'controls', 'profiles'):
            item[key] = json.loads(item.pop(key + '_json'))
    for item in tables['recommendations']:
        item['payload'] = json.loads(item['payload'])
    for item in tables['runtime_events']:
        item['details'] = json.loads(item['details'])
    return {'project': info, **tables}
