"""Synthetic evaluator for location/commit matching only; NOT vulnerability precision.

No project data, no LLM, no network and no scanner execution.
"""
from __future__ import annotations
import json
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
