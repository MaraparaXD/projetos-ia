"""Conservative scanner/finding path association. Does not establish causality.

Only matches sanitized metadata; never uses code snippets or promotes alerts to findings.
"""
from __future__ import annotations
import json
from pathlib import Path
from .core import open_db, require_workspace


def _same_file(source: str, target: str) -> bool:
    # Remova apenas prefixos de diretório relativos; arquivos ocultos não são prefixos.
    def relative_prefix(value: str) -> str:
        value = value.replace('\\', '/')
        while value.startswith('./'):
            value = value[2:]
        return value

    a = relative_prefix(source)
    b = relative_prefix(target)
    if a.startswith('[') or b.startswith('[') or not a or not b:
        return False
    # Anchored suffix with path separator; prevents foo.ts ~ notfoo.ts.
    return a == b or a.endswith('/' + b) or b.endswith('/' + a)


def correlate_candidates(root: Path, project: str, line_slack: int = 3) -> list[dict]:
    require_workspace(root)
    if not 0 <= line_slack <= 10:
        raise ValueError('line_slack must be 0..10')
    out=[]
    with open_db(root) as db:
        findings=db.execute('SELECT finding_key,evidence_json FROM findings WHERE project=?', (project,)).fetchall()
        alerts=db.execute('''SELECT alert_id,tool,rule_id,location,line,triage FROM alerts
                             WHERE project=? AND triage IN ('unreviewed','relevant','needs_context')''', (project,)).fetchall()
    for f in findings:
        evs=json.loads(f['evidence_json'])
        for ev in evs:
            for a in alerts:
                if not _same_file(a['location'], ev['path']):
                    continue
                line=a['line']
                if line is not None and not ev['start']-line_slack <= line <= ev['end']+line_slack:
                    continue
                out.append({'finding_key':f['finding_key'], 'alert_id':a['alert_id'][:16],
                            'tool':a['tool'], 'rule_id':a['rule_id'],
                            'evidence_path':ev['path'], 'scanner_path':a['location'],
                            'line_proximity': line is not None,
                            'interpretation':'candidate association ONLY — human verification required'})
    return out
