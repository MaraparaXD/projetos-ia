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


def _agent_scenarios():
    """Três cenários independentes, sempre fictícios e sem arquivos do auditor."""
    from copy import deepcopy
    base_alert = {'rule_id': 'synthetic.rule', 'severity': 'ERROR',
                  'location': 'src/synthetic.py', 'line': 1, 'component': 'synthetic'}
    scenarios = []
    for name, services, alerts in (
        ('empty', [], []),
        ('ordinary', ['http', 'ssh'], [base_alert]),
        ('duplicates', ['http', 'http', 'ssh'], [base_alert, base_alert]),
    ):
        evidence = [
            {'id': 'synthetic-recon', 'kind': 'recon', 'payload': {'assets': [
                {'asset': 'lab.example.invalid', 'services': services, 'controls': ['tls']}
            ] if services else []}},
            {'id': 'synthetic-scanner', 'kind': 'scanner',
             'payload': {'alerts': deepcopy(alerts), 'commit': None}},
        ]
        scenarios.append((name, evidence))
    return scenarios


def compare_agent_synthetic(provider, repetitions=3) -> dict:
    """Pares baseline/agente: contratos e operação, nunca detecção de vulnerabilidades."""
    from collections import Counter
    from statistics import median
    from time import perf_counter
    from .agents import Specialist
    from .contracts import Profile, TaskMessage
    from .policy import allowed_tools

    if type(repetitions) is not int or not 1 <= repetitions <= 100:
        raise ValueError('Repetições devem estar entre 1 e 100.')

    def describe(out, elapsed, evidence):
        refs = {ref for item in (*out.hypotheses, *out.recommendations)
                for ref in item['evidence']}
        reason = next((u.split('=', 1)[1] for u in out.uncertainties
                       if u.startswith('fallback_reason=')), None)
        return {'mode': out.mode, 'hypotheses': len(out.hypotheses),
                'recommendations': len(out.recommendations),
                'hypotheses_by_origin': dict(Counter(h.get('origin', 'rule') for h in out.hypotheses)),
                'recommendations_by_origin': dict(Counter(r.get('origin', 'rule') for r in out.recommendations)),
                'coverage_evidence': len(refs) / len(evidence) if evidence else 0.0,
                'fallback_reason': reason, 'elapsed_seconds': elapsed}

    def aggregate(rows):
        modes = {}
        for mode in sorted({row['mode'] for row in rows}):
            selected = [row for row in rows if row['mode'] == mode]
            h_origins, r_origins = Counter(), Counter()
            for row in selected:
                h_origins.update(row['hypotheses_by_origin'])
                r_origins.update(row['recommendations_by_origin'])
            times = [row['elapsed_seconds'] for row in selected]
            modes[mode] = {
                'runs': len(selected),
                'hypotheses': sum(row['hypotheses'] for row in selected),
                'recommendations': sum(row['recommendations'] for row in selected),
                'hypotheses_by_origin': dict(h_origins),
                'recommendations_by_origin': dict(r_origins),
                'coverage_evidence': sum(row['coverage_evidence'] for row in selected) / len(selected),
                'elapsed_seconds': {'median': median(times), 'max': max(times)},
            }
        times = [row['elapsed_seconds'] for row in rows]
        reasons = Counter(row['fallback_reason'] for row in rows if row['fallback_reason'] is not None)
        return {'runs': len(rows), 'modes': modes,
                'mode': next(iter(modes)) if len(modes) == 1 else 'mixed',
                'hypotheses': sum(row['hypotheses'] for row in rows),
                'recommendations': sum(row['recommendations'] for row in rows),
                'coverage_evidence': sum(row['coverage_evidence'] for row in rows) / len(rows),
                'fallback_rate': sum(row['mode'] == 'deterministic_fallback' for row in rows) / len(rows),
                'fallback_reasons': dict(reasons),
                'elapsed_seconds': {'median': median(times), 'max': max(times)}}

    all_baseline, all_agent, profiles = [], [], {}
    for profile in Profile:
        baseline_rows, agent_rows, scenarios = [], [], {}
        for scenario, evidence in _agent_scenarios():
            ids = tuple(e['id'] for e in evidence)
            memory = []
            if profile == Profile.BLUE:
                # Memória fixa do baseline: não acumular sugestões entre repetições.
                known = {}
                for source in (Profile.RED, Profile.STATIC):
                    msg = TaskMessage('synthetic-memory', 'benchmark', source,
                                      'Evidências fictícias', 'execucao', ids, allowed_tools(source))
                    for h in Specialist(source).run(msg, evidence, []).hypotheses:
                        known[h['id']] = {**h, 'status': 'candidate', 'profiles': [source.value]}
                memory = list(known.values())
            msg = TaskMessage('synthetic-benchmark', 'benchmark', profile,
                              'Avaliar evidências fictícias', 'execucao', ids, allowed_tools(profile))
            scenario_baseline, scenario_agent = [], []
            for _ in range(repetitions):
                start = perf_counter()
                baseline = Specialist(profile).run(msg, evidence, memory)
                scenario_baseline.append(describe(baseline, perf_counter() - start, evidence))
                start = perf_counter()
                agent = Specialist(profile).run(msg, evidence, memory, provider)
                scenario_agent.append(describe(agent, perf_counter() - start, evidence))
            baseline_rows.extend(scenario_baseline)
            agent_rows.extend(scenario_agent)
            scenarios[scenario] = {'baseline': aggregate(scenario_baseline), 'agent': aggregate(scenario_agent)}
        all_baseline.extend(baseline_rows)
        all_agent.extend(agent_rows)
        profiles[profile.value] = {'scenarios': scenarios, 'baseline': aggregate(baseline_rows),
                                   'agent': aggregate(agent_rows)}
    return {'synthetic_only': True, 'vulnerability_detection_validated': False,
            'samples': len(all_agent), 'repetitions': repetitions, 'profiles': profiles,
            'baseline': aggregate(all_baseline), 'agent': aggregate(all_agent),
            'limitations': [
                'Somente fixtures sintéticas, sem ground truth de vulnerabilidades.',
                'Não mede precisão, recall ou segurança de um modelo real.',
                'Tempo depende de hardware, provedor e carga; mediana e máximo não são intervalos de confiança.',
                'Cobertura conta IDs de evidências referenciados, não qualidade da análise.',
                'Totais somam saídas por execução, incluindo duplicatas das regras e propostas ainda candidatas.',
                'Memória do Blue vem de regras fixas; repetições não simulam aprendizado.',
            ]}
