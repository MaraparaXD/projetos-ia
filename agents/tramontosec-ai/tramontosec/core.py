"""TramontoSec AI v0.2: audit evidence registry and human review gate.

Only Python stdlib; never executes target code, shell commands, or scanners.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
KINDS = {'external_assessment', 'whitebox_assessment', 'technical_note', 'scanner_report'}
CLASSIFICATIONS = {'VCE', 'VP', 'R', 'I', 'OBS'}
SEVERITIES = {'Crítica', 'Alta', 'Média', 'Baixa', 'Informativa', 'Indeterminada'}
STATUS = {'candidate', 'in_review', 'accepted', 'rejected'}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fd:
        for chunk in iter(lambda: fd.read(128 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def no_sync_roots(path: Path) -> None:
    forbidden = ('onedrive', 'dropbox', 'google drive', 'icloud drive', 'sharepoint')
    segments = (part.lower() for part in path.resolve(strict=False).parts)
    if any(part == 'box' or any(part.startswith(prefix) for prefix in forbidden)
           for part in segments):
        raise ValueError('Workspace inside a known sync root; use approved encrypted local storage.')


def make_workspace(root: Path) -> None:
    no_sync_roots(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / 'output').mkdir(exist_ok=True)
    # SQLite is internal and should inherit a private, secured directory ACL.
    with open_db(root) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS documents(
          doc_id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
          sha256 TEXT NOT NULL, imported_at TEXT NOT NULL, source_path TEXT NOT NULL,
          period TEXT NOT NULL, notes TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS findings(
          finding_key TEXT PRIMARY KEY, project TEXT NOT NULL, identifier TEXT NOT NULL,
          title TEXT NOT NULL, classification TEXT NOT NULL, severity TEXT NOT NULL,
          summary TEXT NOT NULL, uncertainty TEXT NOT NULL, source_doc TEXT NOT NULL,
          evidence_json TEXT NOT NULL, status TEXT NOT NULL,
          human_decision TEXT, reviewer TEXT, reviewed_at TEXT,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS report_catalog(
          doc_id TEXT PRIMARY KEY REFERENCES documents(doc_id),
          scope TEXT NOT NULL, format TEXT NOT NULL, ids_json TEXT NOT NULL,
          parsed_at TEXT NOT NULL, note TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scanner_runs(
          run_id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL,
          tool TEXT NOT NULL, sha256 TEXT NOT NULL, file_name TEXT NOT NULL,
          ingested_at TEXT NOT NULL, ingested_count INTEGER NOT NULL,
          UNIQUE(project,tool,sha256)
        );
        CREATE TABLE IF NOT EXISTS alerts(
          alert_id TEXT PRIMARY KEY, project TEXT NOT NULL, tool TEXT NOT NULL,
          rule_id TEXT NOT NULL, location TEXT NOT NULL, line INTEGER,
          component TEXT NOT NULL, severity TEXT NOT NULL,
          occurrences INTEGER NOT NULL DEFAULT 1, triage TEXT NOT NULL DEFAULT 'unreviewed',
          triage_note TEXT, reviewer TEXT, reviewed_at TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events(
          event_id INTEGER PRIMARY KEY AUTOINCREMENT, event_at TEXT NOT NULL,
          finding_key TEXT NOT NULL, verb TEXT NOT NULL, details TEXT NOT NULL
        );
        ''')
        db.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')


@contextmanager
def open_db(root: Path):
    """Commit/rollback and always close the SQLite handle (including on Windows)."""
    dbpath = root / 'audit.sqlite3'
    if not dbpath.exists() and not root.exists():
        raise FileNotFoundError('Workspace not found: run init first')
    connection = sqlite3.connect(dbpath)
    try:
        connection.row_factory = sqlite3.Row
        with closing(connection.execute('PRAGMA foreign_keys = ON')):
            pass
        with connection:
            yield connection
    finally:
        connection.close()


def require_workspace(root: Path) -> None:
    no_sync_roots(root)
    if not (root / 'audit.sqlite3').is_file():
        raise FileNotFoundError('Workspace database absent. Run `init` first.')


def record_document(root: Path, doc_id: str, path: Path, category: str,
                    period: str = '', notes: str = '') -> dict[str, str]:
    require_workspace(root)
    if category not in KINDS:
        raise ValueError('Unsupported document category')
    if not doc_id or len(doc_id) > 120 or not re.fullmatch(r'[A-Za-z0-9_.-]+', doc_id):
        raise ValueError('Document ID must be alphanumeric with ._- allowed')
    path = path.resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 30_000_000:
        raise ValueError('File must be a regular file under 30 MB')
    digest = hash_file(path)
    with open_db(root) as db:
        previous = db.execute('SELECT sha256 FROM documents WHERE doc_id=?', (doc_id,)).fetchone()
        if previous and previous['sha256'] != digest:
            raise ValueError('Document ID already exists with another SHA-256; use a new versioned doc ID')
        db.execute('''INSERT OR IGNORE INTO documents
           (doc_id,name,category,sha256,imported_at,source_path,period,notes)
           VALUES (?,?,?,?,?,?,?,?)''',
           (doc_id, path.name, category, digest, now(), str(path), period, notes))
    return {'id': doc_id, 'name': path.name, 'sha256': digest}


def import_findings(root: Path, seed_file: Path) -> tuple[int, int]:
    require_workspace(root)
    raw = json.loads(seed_file.read_text(encoding='utf-8'))
    if not isinstance(raw, list):
        raise ValueError('Input must be a JSON array')
    created, existing = 0, 0
    with open_db(root) as db:
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError('Every finding must be an object')
            project = str(item['project'])
            identifier = str(item['identifier'])
            key = project + ':' + identifier
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', project) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', identifier):
                raise ValueError('Invalid project or finding ID')
            classification = str(item['classification'])
            severity = str(item['severity'])
            if classification not in CLASSIFICATIONS or severity not in SEVERITIES:
                raise ValueError(f'Invalid classification or severity in {key}')
            evidence = item.get('evidence', [])
            if not isinstance(evidence, list):
                raise ValueError('Evidence must be an array')
            for e in evidence:
                if not isinstance(e, dict) or any(k not in e for k in ('repo', 'path', 'start', 'end', 'commit')):
                    raise ValueError(f'Missing repo/path/start/end/commit in {key}')
                if not all(isinstance(e[k], str) for k in ('repo', 'path', 'commit')):
                    raise ValueError('Invalid evidence fields')
                if not isinstance(e['start'], int) or not isinstance(e['end'], int) or not (1 <= e['start'] <= e['end'] <= 1_000_000):
                    raise ValueError('Invalid evidence line range')
            params = (key, project, identifier, str(item['title']), classification,
                      severity, str(item['summary']), str(item.get('uncertainty','')),
                      str(item['source_doc']), json.dumps(evidence, ensure_ascii=False),
                      'candidate', now())
            count = db.execute('''INSERT OR IGNORE INTO findings
                 (finding_key,project,identifier,title,classification,severity,summary,
                  uncertainty,source_doc,evidence_json,status,created_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', params).rowcount
            if count:
                created += 1
                db.execute('INSERT INTO events(event_at,finding_key,verb,details) VALUES(?,?,?,?)',
                           (now(), key, 'imported', f'source={item["source_doc"]}'))
            else:
                existing += 1
    return created, existing


def list_findings(root: Path) -> list[dict[str, Any]]:
    require_workspace(root)
    with open_db(root) as db:
        return [dict(r) for r in db.execute('''SELECT finding_key,title,classification,severity,status,source_doc
                                            FROM findings ORDER BY finding_key''')]


def _inside_repository(repo_root: Path, raw_path: str) -> Path:
    # No absolute paths, drive prefixes, dot traversal or paths through symlinks escaping the repo.
    normalized = raw_path.replace('\\', '/')
    if ('\x00' in normalized or normalized.startswith('/') or ':' in normalized
            or any(x in ('.', '..') for x in normalized.split('/'))):
        raise ValueError('Unsafe evidence path')
    if not normalized:
        raise ValueError('Empty evidence path')
    resolved_repo = repo_root.resolve(strict=True)
    result = (resolved_repo / normalized).resolve(strict=False)
    if not result.is_relative_to(resolved_repo):
        raise ValueError('Evidence path escapes repository')
    return result


def verify_one(e: dict[str, Any], repos: dict[str, Path]) -> dict[str, Any]:
    repo_name = e['repo']
    result: dict[str, Any] = {'repo': repo_name, 'path': e['path'], 'range': f'{e["start"]}-{e["end"]}', 'status': 'unverified'}
    if repo_name not in repos:
        result['reason'] = 'Repository path not provided'
        return result
    try:
        path = _inside_repository(repos[repo_name], e['path'])
        if not path.is_file():
            result['reason'] = 'File not present'
            return result
        with path.open('r', encoding='utf-8', errors='replace') as fd:
            lines = sum(1 for _ in fd)
        if e['end'] > lines:
            result['reason'] = f'Out of range: file has {lines} lines'
            return result
        result['status'] = 'located'
        result['reason'] = 'Path and lines exist; semantics NOT independently verified'
        return result
    except (OSError, ValueError) as exc:
        result['reason'] = str(exc)
        return result


def verify(root: Path, repos: dict[str, Path]) -> list[dict[str, Any]]:
    require_workspace(root)
    from .git_readonly import inspect_repo, compare_commit
    states = {name: inspect_repo(path) for name, path in repos.items()}
    checks: list[dict[str, Any]] = []
    with open_db(root) as db:
        rows = db.execute('SELECT finding_key,evidence_json FROM findings ORDER BY finding_key').fetchall()
    for row in rows:
        evidence = json.loads(row['evidence_json'])
        for e in evidence:
            check = {'finding_key': row['finding_key'], **verify_one(e, repos)}
            check['expected_commit'] = e['commit']
            state = states.get(e['repo'])
            check.update(compare_commit(e['commit'], state or {'git_valid': False}))
            check['worktree_clean'] = state.get('clean') if state else None
            check['head'] = state.get('head') if state else None
            check['semantics_verified'] = False  # Only a human can establish this.
            checks.append(check)
    return checks


def review(root: Path, key: str, decision: str, reviewer: str, reason: str,
           confirmed_code: bool) -> None:
    require_workspace(root)
    if decision not in ('accepted', 'in_review', 'rejected'):
        raise ValueError('Unsupported review decision')
    if not reviewer.strip() or not reason.strip():
        raise ValueError('Reviewer and written rationale required')
    if decision == 'accepted' and not confirmed_code:
        raise ValueError('Acceptance requires --ack-reviewed-code (human review)')
    with open_db(root) as db:
        r = db.execute('SELECT finding_key FROM findings WHERE finding_key=?', (key,)).fetchone()
        if not r:
            raise KeyError('Finding not found')
        db.execute('''UPDATE findings SET status=?,reviewer=?,human_decision=?,reviewed_at=?
                      WHERE finding_key=?''', (decision, reviewer, reason, now(), key))
        db.execute('INSERT INTO events(event_at,finding_key,verb,details) VALUES(?,?,?,?)',
                   (now(), key, decision, f'reviewer={reviewer}; reason={reason}'))


def export_report(root: Path, file_name: str = 'TRAMONTO_RASCUNHO.md') -> Path:
    require_workspace(root)
    out = root / 'output' / file_name
    if not out.resolve(strict=False).is_relative_to((root / 'output').resolve(strict=True)):
        raise ValueError('Unsafe output name')
    with open_db(root) as db:
        docs = db.execute('SELECT doc_id,name,sha256,period,category FROM documents ORDER BY doc_id').fetchall()
        rows = db.execute('SELECT * FROM findings ORDER BY identifier').fetchall()
        try:
            alerts = db.execute('''SELECT project,tool,triage,COUNT(*) AS qty FROM alerts
                                      GROUP BY project,tool,triage ORDER BY project,tool,triage''').fetchall()
            catalog = db.execute('SELECT doc_id,scope,ids_json FROM report_catalog ORDER BY doc_id').fetchall()
        except sqlite3.OperationalError:
            alerts, catalog = [], []
    sections = [
        '# TramontoSec AI — Relatório técnico preliminar',
        '',
        '> CONFIDENCIAL — MINUTA. Assistência automatizada. Revisão e autorização humana obrigatórias.',
        '> Nenhum teste dinâmico foi realizado por esta ferramenta. Confirmar versões reais, permissões e ambiente.',
        '', '## 1. Adequação', '',
        'Escopo e autorização ainda devem ser confirmados pelo auditor.',
        '', '## 2. Verificação', '',
        'Este programa não comprova automaticamente NDA, permissão de testes nem controles de guarda.',
        '', '## 3. Preparação — Documentos indexados', ''
    ]
    for d in docs:
        sections.append(f'- **{d["doc_id"]}**: `{d["name"]}` | {d["category"]} | período: {d["period"]} | SHA-256: `{d["sha256"]}`')
    if catalog:
        sections.extend(['', '### Catálogo de relatórios históricos', '',
                         'IDs aqui são históricos, não achados revalidados nem equivalentes entre relatórios.'])
        for c in catalog:
            ids = json.loads(c['ids_json'])
            sections.append(f'- `{c["doc_id"]}` ({c["scope"]}): {len(ids)} identificadores distintos')
    sections.extend(['', '## 4. Execução — Resultados da análise documental', '',
                     'As referências abaixo foram importadas de documentos anteriores. Não constituem nova validação de código.', ''])
    for row in rows:
        approved = 'REVISTO POR HUMANO' if row['status'] == 'accepted' else 'NÃO APROVADO'
        sections.extend([
            f'### {row["finding_key"]} — {row["title"]}', '',
            f'- **Origem:** {row["source_doc"]}',
            f'- **Classe histórica:** {row["classification"]}; **severidade:** {row["severity"]}',
            f'- **Revisão:** {row["status"]} — {approved}',
            f'- **Descrição documentada:** {row["summary"]}',
            f'- **Limitações:** {row["uncertainty"]}',
        ])
        for ev in json.loads(row['evidence_json']):
            sections.append(f'- **Referência a conferir:** `{ev["repo"]}/{ev["path"]}:{ev["start"]}-{ev["end"]}` no commit `{ev["commit"]}`')
        if row['human_decision']:
            sections.append(f'- **Nota de revisão:** {row["human_decision"]} (por {row["reviewer"]})')
        sections.append('')
    sections.extend(['', '### Triagem dos scanners (não são vulnerabilidades automaticamente confirmadas)', ''])
    for a in alerts:
        sections.append(f'- {a["project"]} / {a["tool"]} / {a["triage"]}: {a["qty"]} alertas distintos')
    sections.extend([
        '## 5. Finalização', '',
        'Conclusões técnicas e recomendações exigem validação independente das referências, controles compensatórios e versão implantada.',
        '', '### Histórico de classificação', '',
        'IDs de relatórios de reconhecimento externo e de inspeção White Box não são deduplicados automaticamente.',
        ''])
    out.write_text('\n'.join(sections), encoding='utf-8')
    return out
