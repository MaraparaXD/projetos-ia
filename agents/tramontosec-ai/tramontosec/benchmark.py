"""Synthetic evaluator for location/commit matching only; NOT vulnerability precision.

No project data, no LLM, no network and no scanner execution.
"""
from __future__ import annotations
import tempfile
import subprocess
import os
from pathlib import Path
from .core import verify_one
from .git_readonly import inspect_repo, compare_commit


def run_benchmark() -> dict:
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d) / 'synthetic'; repo.mkdir()
        src = repo / 'src'; src.mkdir()
        (src / 'safe.py').write_text('def check():\n    return True\n', encoding='utf-8')
        env = {**os.environ, 'GIT_CONFIG_NOSYSTEM':'1', 'GIT_CONFIG_GLOBAL':os.devnull}
        def git(*cmd):
            p = subprocess.run(['git', '-C', str(repo), *cmd], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                               env=env, check=True, timeout=8, text=True)
            return p.stdout.strip()
        git('init', '-q'); git('-c', 'user.name=Synthetic Test', '-c', 'user.email=test@example.invalid',
                               'add', 'src/safe.py')
        git('-c', 'user.name=Synthetic Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'synthetic')
        state = inspect_repo(repo)
        actual = state['head']
        cases = [
          (True, {'repo':'api', 'path':'src/safe.py', 'start':1,'end':2,'commit':actual}),
          (False, {'repo':'api', 'path':'src/safe.py', 'start':99,'end':100,'commit':actual}),
          (False, {'repo':'api', 'path':'../safe.py', 'start':1,'end':2,'commit':actual}),
          (False, {'repo':'api', 'path':'src/missing.py', 'start':1,'end':2,'commit':actual}),
          (False, {'repo':'api', 'path':'src/safe.py', 'start':1,'end':2,'commit':'0'*40}),
        ]
        tp=fp=tn=fn=0
        for expected, evidence in cases:
            x = verify_one(evidence, {'api': repo})
            commit = compare_commit(evidence['commit'],state)
            observed = x['status'] == 'located' and commit['baseline_valid']
            if expected and observed: tp += 1
            elif expected: fn += 1
            elif observed: fp += 1
            else: tn += 1
        return {'benchmark': 'synthetic location+commit association only',
                'cases': len(cases), 'tp':tp, 'tn':tn, 'fp':fp, 'fn':fn,
                'precision': tp/(tp+fp) if tp+fp else None,
                'recall':tp/(tp+fn) if tp+fn else None,
                'warning':'NOT measurement of vulnerability discovery or LLM security accuracy'}


def compare_agent_synthetic(provider) -> dict:
    """Experimento unitário sintético: não mede precisão real de vulnerabilidades."""
    from time import perf_counter
    from .agents import Specialist
    from .contracts import Profile, TaskMessage
    from .policy import allowed_tools

    msg = TaskMessage('synthetic-benchmark', 'benchmark', Profile.RED,
                      'Avaliar evidências fictícias', 'execucao',
                      ('synthetic-e1',), allowed_tools(Profile.RED))
    evidence = [{'id': 'synthetic-e1', 'kind': 'recon', 'payload': {'assets': [
        {'asset': 'lab.example.invalid', 'services': ['http', 'ssh'],
         'controls': ['tls']}
    ]}}]
    start = perf_counter()
    baseline = Specialist(Profile.RED).run(msg, evidence, [])
    baseline_time = perf_counter() - start
    start = perf_counter()
    agent = Specialist(Profile.RED).run(msg, evidence, [], provider)
    agent_time = perf_counter() - start

    def describe(out, elapsed):
        refs = {e for h in out.hypotheses for e in h['evidence']}
        return {'mode': out.mode, 'hypotheses': len(out.hypotheses),
                'coverage_evidence': len(refs) / len(evidence),
                'invalid_response_rate': 1.0 if out.mode == 'deterministic_fallback' else 0.0,
                'elapsed_seconds': round(elapsed, 6)}

    return {'synthetic_only': True, 'vulnerability_detection_validated': False,
            'samples': 1, 'baseline': describe(baseline, baseline_time),
            'agent': describe(agent, agent_time),
            'limitations': ('Uma fixture, sem ground truth de vulnerabilidades. '
                            'Tempo depende de hardware e provedor. '
                            'Sem precisão ou recall de detecção.')}
