"""Academic demo: only locally generated synthetic files and a disposable Git repo."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import uuid

from .evidence import analyze_local, baseline, import_recon, import_scanner
from .git_readonly import inspect_repo
from .orchestrator import attest_stage, export_project, plan, review_hypothesis, run
from .store import create_project, snapshot


def run_demo(workspace: Path, project: str = 'aurora-demo', review: bool = False) -> dict:
    from .contracts import identifier
    from .core import no_sync_roots
    identifier(project)
    no_sync_roots(workspace)
    parent = workspace.resolve() / 'synthetic-inputs'
    if parent.is_symlink():
        raise PermissionError('Diretório de demonstração não pode ser link simbólico.')
    fixtures = parent / (project + '-' + uuid.uuid4().hex[:8])
    repo = fixtures / 'repo'
    (repo / 'src').mkdir(parents=True)
    (repo / 'src' / 'demo.py').write_text('def synthetic_review(value):\n    return eval(value)  # somente fixture AST, nunca executada\n', encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_TERMINAL_PROMPT': '0'})
    def git(*args):
        subprocess.run(['git', '-c', f'core.hooksPath={os.devnull}', '-c', 'core.fsmonitor=false',
                        '-C', str(repo), *args], check=True, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=15)
    git('init', '-q')
    git('add', 'src/demo.py')
    git('-c', 'user.name=Synthetic Demo', '-c', 'user.email=demo@example.invalid', 'commit', '-qm', 'synthetic fixture')
    head = inspect_repo(repo)['head']
    create_project(workspace, project, 'Laboratório Aurora', 'Avaliar evidências sintéticas de exposição e código.',
                   ['app.aurora.invalid'], repo, synthetic=True, ack=True)
    recon = fixtures / 'recon.json'
    recon.write_text(json.dumps({'synthetic': True, 'assets': [
        {'asset': 'app.aurora.invalid', 'services': ['http', 'ssh'], 'controls': ['logging']}]}), encoding='utf-8')
    scan = fixtures / 'semgrep.json'
    scan.write_text(json.dumps({'results': [{'check_id': 'python.dynamic-execution', 'path': 'src/demo.py',
                                             'start': {'line': 2}, 'extra': {'severity': 'WARNING'}}]}), encoding='utf-8')
    baseline(workspace, project, head)
    import_recon(workspace, project, recon, True)
    import_scanner(workspace, project, 'semgrep', scan, True, head)
    analyze_local(workspace, project, 'src/demo.py')
    for stage in ('adequacao', 'verificacao', 'preparacao'):
        attest_stage(workspace, project, stage, 'Demonstração sintética',
                     'Atestação fictícia para exercício local, sem efeito em auditoria real.', True)
    plan(workspace, project)
    outputs = run(workspace, project)
    if review:
        first = snapshot(workspace, project)['hypotheses'][0]
        review_hypothesis(workspace, project, first['id'], 'in_review', 'Auditor de demonstração',
                          'Decisão sintética solicitada pelo operador: investigar contraprovas antes de aceitar.')
    report = export_project(workspace, project)
    return {'project': project, 'synthetic': True, 'agents': [o['profile'] for o in outputs],
            'modes': [o['mode'] for o in outputs], 'report': str(report),
            'human_decision_recorded': review, 'completed_audit': False,
            'next': 'Revise as hipóteses pela CLI ou dashboard; Execução e Finalização continuam pendentes.'}
