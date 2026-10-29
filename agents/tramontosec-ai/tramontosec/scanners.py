"""Import redacted scanner JSON as alerts, NEVER as confirmed vulnerabilities.

Intentional discard: source code snippets, secret values, messages, URLs, raw finding
payloads, command output, and all arbitrary scanner-provided descriptive text.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator
from .core import now, open_db, require_workspace, hash_file

TOOLS = {'semgrep', 'trivy', 'gitleaks', 'zizmor'}
TRIAGE = {'unreviewed', 'relevant', 'false_positive', 'needs_context', 'duplicate', 'informational'}
MAX_BYTES = 20_000_000
MAX_ALERTS = 12_000


def _s(value: Any, limit: int = 140) -> str:
    if not isinstance(value, str):
        return ''
    value = ''.join(ch if ch.isprintable() else ' ' for ch in value)
    # Never retain scanner messages or secret-bearing fields.
    value = re.sub(r'[A-Za-z0-9_-]{80,}', '[long-id]', value)
    return value[:limit]


def _path(value: Any) -> str:
    s = _s(value, 260).replace('\\', '/')
    # Do not retain absolute paths, drive/usernames, traversal, or unsafe strings.
    if s.startswith('/') or re.match(r'^[A-Za-z]:', s) or any(p in ('.', '..') for p in s.split('/')):
        return '[path-omitted]'
    return s or '[path-unavailable]'


def _line(value: Any) -> int | None:
    return value if type(value) is int and 1 <= value <= 2_000_000 else None


def _item(rule: Any, location: Any = '', line: Any = None,
          component: Any = '', severity: Any = '') -> dict[str, Any]:
    return {'rule_id': _s(rule, 160) or 'unspecified',
            'location': _path(location), 'line': _line(line),
            'component': _s(component, 140), 'severity': _s(severity, 30)}


def _semgrep(data: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get('results'), list):
        raise ValueError('Semgrep JSON must contain results[]')
    for x in data['results']:
        if isinstance(x, dict):
            extra = x.get('extra', {}) if isinstance(x.get('extra'), dict) else {}
            start = x.get('start', {}) if isinstance(x.get('start'), dict) else {}
            yield _item(x.get('check_id'), x.get('path'), start.get('line'),
                        severity=extra.get('severity'))


def _trivy(data: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get('Results'), list):
        raise ValueError('Trivy JSON must contain Results[]')
    for target in data['Results']:
        if not isinstance(target, dict):
            continue
        location = target.get('Target')
        for x in target.get('Vulnerabilities') or []:
            if isinstance(x, dict):
                yield _item(x.get('VulnerabilityID'), location, component=x.get('PkgName'), severity=x.get('Severity'))
        for x in target.get('Misconfigurations') or []:
            if isinstance(x, dict):
                yield _item(x.get('ID'), location, component=x.get('Type'), severity=x.get('Severity'))
        # Secrets excluded regardless of scanner configuration; secret values may
        # be embedded in other scanner fields, which we never store.


def _gitleaks(data: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError('Gitleaks JSON must be an array')
    for x in data:
        if isinstance(x, dict):
            # Do not store Match, Secret, Fingerprint, Description, or commit message.
            yield _item(x.get('RuleID'), x.get('File'), x.get('StartLine'),
                        severity='POTENTIAL_SECRET')


def _zizmor(data: Any) -> Iterator[dict[str, Any]]:
    if isinstance(data, dict):
        findings = data.get('findings', data.get('results', []))
    else:
        findings = data
    if not isinstance(findings, list):
        raise ValueError('Zizmor JSON needs findings[] or an array')
    for x in findings:
        if not isinstance(x, dict):
            continue
        loc = x.get('locations') or []
        first = loc[0] if isinstance(loc, list) and loc and isinstance(loc[0], dict) else {}
        concrete = first.get('concrete', {}) if isinstance(first.get('concrete'), dict) else {}
        file_path = first.get('path') or concrete.get('feature') or x.get('file')
        ln = first.get('line') or concrete.get('line')
        yield _item(x.get('ident', x.get('rule', x.get('audit'))), file_path, ln,
                    severity=x.get('severity'))


_READERS = {'semgrep': _semgrep, 'trivy': _trivy, 'gitleaks': _gitleaks, 'zizmor': _zizmor}


def parse_redacted(tool: str, path: Path) -> tuple[str, list[dict[str, Any]]]:
    if tool not in TOOLS:
        raise ValueError('Unsupported scanner')
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('Report absent or too large (limit 20 MB)')
    digest = hash_file(path)
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    results = []
    for x in _READERS[tool](data):
        results.append(x)
        if len(results) > MAX_ALERTS:
            raise ValueError('Too many scanner alerts')
    return digest, results


def _fingerprint(project: str, tool: str, x: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps([project, tool, x['rule_id'], x['location'],
                                       x['line'], x['component']], ensure_ascii=False).encode()).hexdigest()


def import_scan(root: Path, project: str, tool: str, path: Path,
                ack_redacted: bool) -> dict[str, Any]:
    if not ack_redacted:
        raise ValueError('Require explicit --ack-redacted-input; do not submit raw scans')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', project):
        raise ValueError('Invalid project ID')
    require_workspace(root)
    digest, parsed = parse_redacted(tool, path)
    # Do not store full source file paths; only basename + hash.
    added = existed = 0
    # Unique fingerprints within one scan; avoid double counting occurrences.
    unique = {_fingerprint(project, tool, x): x for x in parsed}
    with open_db(root) as db:
        old = db.execute('SELECT run_id FROM scanner_runs WHERE project=? AND tool=? AND sha256=?',
                         (project, tool, digest)).fetchone()
        if old:
            return {'project': project, 'tool': tool, 'raw_count': len(parsed),
                    'unique_count': len(unique), 'added': 0, 'existing': len(unique), 'already_imported': True}
        for key, x in unique.items():
            inserted = db.execute('''INSERT OR IGNORE INTO alerts(
                 alert_id,project,tool,rule_id,location,line,component,severity,created_at)
                 VALUES(?,?,?,?,?,?,?,?,?)''',
                 (key,project,tool,x['rule_id'],x['location'],x['line'],x['component'],
                  x['severity'],now())).rowcount
            added += inserted
            existed += not inserted
        db.execute('''INSERT INTO scanner_runs(project,tool,sha256,file_name,ingested_at,ingested_count)
                      VALUES(?,?,?,?,?,?)''', (project,tool,digest,path.name,now(),len(parsed)))
    return {'project': project, 'tool': tool, 'raw_count': len(parsed),
            'unique_count': len(unique), 'added': added, 'existing': existed, 'already_imported': False}


def list_alerts(root: Path, project: str | None = None) -> list[dict[str, Any]]:
    require_workspace(root)
    with open_db(root) as db:
        if project:
            result = db.execute('''SELECT * FROM alerts WHERE project=? ORDER BY tool,rule_id,location''', (project,))
        else:
            result = db.execute('SELECT * FROM alerts ORDER BY project,tool,rule_id,location')
        return [dict(r) for r in result]


def triage_alert(root: Path, alert_id: str, status: str, reviewer: str, note: str) -> None:
    require_workspace(root)
    if status not in TRIAGE - {'unreviewed'}:
        raise ValueError('Invalid triage status')
    if not reviewer.strip() or len(reviewer) > 120 or not note.strip() or len(note) > 1000:
        raise ValueError('Reviewer and brief rationale required')
    with open_db(root) as db:
        changed = db.execute('''UPDATE alerts SET triage=?,triage_note=?,reviewer=?,reviewed_at=?
                                WHERE alert_id=?''', (status,note,reviewer,now(),alert_id)).rowcount
        if not changed:
            raise KeyError('Alert not found')
        db.execute('INSERT INTO events(event_at,finding_key,verb,details) VALUES(?,?,?,?)',
                   (now(),f'alert:{alert_id[:14]}','triage',
                    f'status={status}; reviewer={reviewer}; rationale={note[:200]}'))
