"""Sequential runtime; scope, stage gates and human decisions live outside the LLM."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import uuid

from .agents import Specialist
from .contracts import Profile, STAGES, STAGE_NAMES, TaskMessage, text
from .core import now, open_db
from .git_readonly import compare_commit, inspect_repo
from .policy import allowed_tools, check_message
from .providers import Provider
from .store import event, get_project, project_root, snapshot


def plan(workspace: Path, project: str, profiles: list[str] | None = None, objective: str | None = None) -> list[dict]:
    info = get_project(workspace, project)
    requested = [Profile(p) for p in profiles] if profiles else list(Profile)
    if not requested or len(requested) != len(set(requested)):
        raise ValueError('Selecione perfis distintos: red, static, blue.')
    # Always Red Team first, Blue Team after technical evidence; preserve deterministic ordering.
    requested = [p for p in Profile if p in requested]
    data = snapshot(workspace, project)
    if data['stages'][-1]['status'] == 'completed':
        raise PermissionError('Avaliação já finalizada.')
    messages = [TaskMessage(uuid.uuid4().hex, project, p, text(objective or info['objective'], 2000),
                            'execucao', tuple(e['id'] for e in data['evidence']), allowed_tools(p)) for p in requested]
    with open_db(project_root(workspace, project)) as db:
        for msg in messages:
            db.execute('INSERT INTO tasks(id,profile,status,input_json,created_at) VALUES(?,?,?,?,?)',
                       (msg.task_id, msg.profile.value, 'planned', json.dumps(msg.to_dict(), ensure_ascii=False), now()))
        event(db, 'plan_created', {'task_ids': [m.task_id for m in messages], 'profiles': [p.value for p in requested]})
    return [m.to_dict() for m in messages]


def _baseline_current(data: dict) -> bool:
    repo = data['project']['scope']['repo']
    if not repo:
        return True  # Passive-only scope: no claim about a code baseline.
    state = inspect_repo(Path(repo))
    return any(e['kind'] == 'baseline' and compare_commit(e['payload']['expected_commit'], state)['baseline_valid']
               for e in data['evidence'])


def attest_stage(workspace: Path, project: str, stage: str, reviewer: str, reason: str, ack: bool) -> None:
    if stage not in STAGES or not ack:
        raise PermissionError('Etapa inválida ou confirmação humana ausente (--ack-human).')
    reviewer, reason = text(reviewer, 120), text(reason, 1000)
    data = snapshot(workspace, project)
    index = STAGES.index(stage)
    states = {s['name']: s['status'] for s in data['stages']}
    if any(states[s] != 'completed' for s in STAGES[:index]):
        raise PermissionError('Conclua as etapas anteriores do Tramonto com revisão humana.')
    if stage == 'preparacao' and (not data['evidence'] or not _baseline_current(data)):
        raise PermissionError('Preparação exige evidências e baseline atual para repositório autorizado.')
    if stage in ('execucao', 'finalizacao'):
        if (not any(t['status'] == 'completed' for t in data['tasks'])
                or any(t['status'] not in ('completed', 'cancelled') for t in data['tasks'])):
            raise PermissionError('Há tarefas pendentes, interrompidas ou falhas.')
        if any(h['status'] not in ('accepted', 'rejected') for h in data['hypotheses']):
            raise PermissionError('Há hipóteses sem decisão humana final.')
        if not _baseline_current(data):
            raise PermissionError('Baseline alterada; não conclua esta avaliação.')
    with open_db(project_root(workspace, project)) as db:
        db.execute("UPDATE stages SET status='completed',reviewer=?,reason=?,reviewed_at=? WHERE name=?",
                   (reviewer, reason, now(), stage))
        event(db, 'stage_attested', {'stage': stage, 'reviewer': reviewer, 'reason': reason})


def run(workspace: Path, project: str, provider: Provider | None = None) -> list[dict]:
    from .locking import execution_lock
    get_project(workspace, project)
    with execution_lock(project_root(workspace, project)):
        return _run(workspace, project, provider)


def _run(workspace: Path, project: str, provider: Provider | None = None) -> list[dict]:
    data = snapshot(workspace, project)
    states = {s['name']: s['status'] for s in data['stages']}
    if states['finalizacao'] == 'completed' or any(states[s] != 'completed' for s in STAGES[:3]):
        raise PermissionError('Execução requer Adequação, Verificação e Preparação revisadas; avaliação aberta.')
    if not _baseline_current(data):
        raise PermissionError('Baseline Git mudou; execução bloqueada.')
    root, outputs = project_root(workspace, project), []
    with open_db(root) as db:
        # A crashed process never silently replays a task. Operator must plan another execution.
        interrupted = db.execute("UPDATE tasks SET status='interrupted',error='Processo interrompido',finished_at=? "
                                 "WHERE status='running'", (now(),)).rowcount
        if interrupted:
            event(db, 'interrupted_tasks_detected', {'count': interrupted})
    for task in data['tasks']:
        if task['status'] != 'planned':
            continue
        raw = task['input']
        msg = TaskMessage(raw['task_id'], raw['project'], Profile(raw['profile']), raw['objective'],
                          raw['stage'], tuple(raw['evidence_ids']), tuple(raw['allowed_tools']))
        check_message(msg, project)
        current = snapshot(workspace, project)
        if set(msg.evidence_ids) != {e['id'] for e in current['evidence']}:
            raise PermissionError('Evidências mudaram depois do planejamento; crie um novo plano.')
        with open_db(root) as db:
            claimed = db.execute("UPDATE tasks SET status='running' WHERE id=? AND status='planned'", (msg.task_id,)).rowcount
            if not claimed:
                raise PermissionError('Tarefa já assumida por outra execução.')
            db.execute("UPDATE stages SET status='pending' WHERE name IN ('execucao','finalizacao')")
            event(db, 'task_started', {'task_id': msg.task_id, 'profile': msg.profile.value})
        try:
            output = Specialist(msg.profile).run(msg, current['evidence'], current['hypotheses'], provider).to_dict()
            with open_db(root) as db:
                for h in output['hypotheses']:
                    if not set(h['evidence']) <= set(msg.evidence_ids):
                        raise PermissionError('Hipótese cita evidência fora do escopo.')
                    previous = db.execute('SELECT * FROM hypotheses WHERE id=?', (h['id'],)).fetchone()
                    if previous:
                        references = sorted(set(json.loads(previous['evidence_json']) + h['evidence']))
                        profiles = sorted(set(json.loads(previous['profiles_json']) + [msg.profile.value]))
                        changed = references != sorted(json.loads(previous['evidence_json']))
                        db.execute('UPDATE hypotheses SET evidence_json=?,profiles_json=? WHERE id=?',
                                   (json.dumps(references), json.dumps(profiles), h['id']))
                        if changed:
                            db.execute("UPDATE hypotheses SET status='candidate',reviewer=NULL,reason=NULL,reviewed_at=NULL WHERE id=?", (h['id'],))
                    else:
                        db.execute('''INSERT INTO hypotheses(id,title,severity,evidence_json,uncertainty,controls_json,profiles_json)
                                      VALUES(?,?,?,?,?,?,?)''', (h['id'], h['title'], h['severity'], json.dumps(h['evidence']),
                                                h['uncertainty'], json.dumps(h['controls']), json.dumps([msg.profile.value])))
                for rec in output['recommendations']:
                    key = hashlib.sha256((msg.task_id + rec['hypothesis_id']).encode()).hexdigest()[:24]
                    db.execute('INSERT INTO recommendations VALUES(?,?,?,?)',
                               (key, rec['hypothesis_id'], json.dumps(rec, ensure_ascii=False), msg.task_id))
                db.execute("UPDATE tasks SET status='completed',output_json=?,finished_at=? WHERE id=?",
                           (json.dumps(output, ensure_ascii=False), now(), msg.task_id))
                event(db, 'human_review_requested', {'task_id': msg.task_id, 'mode': output['mode']})
            outputs.append(output)
        except Exception as exc:
            with open_db(root) as db:
                db.execute("UPDATE tasks SET status='failed',error=?,finished_at=? WHERE id=?",
                           (type(exc).__name__, now(), msg.task_id))
                event(db, 'task_failed', {'task_id': msg.task_id, 'error_type': type(exc).__name__})
            raise
    return outputs


def cancel_task(workspace: Path, project: str, task_id: str, reviewer: str, reason: str, ack: bool) -> None:
    from .locking import execution_lock
    if not ack:
        raise PermissionError('Cancelamento exige confirmação humana.')
    reviewer, reason = text(reviewer, 120), text(reason, 1000)
    get_project(workspace, project)
    root = project_root(workspace, project)
    with execution_lock(root), open_db(root) as db:
        if db.execute("SELECT status FROM stages WHERE name='finalizacao'").fetchone()[0] == 'completed':
            raise PermissionError('Avaliação finalizada.')
        changed = db.execute("UPDATE tasks SET status='cancelled',finished_at=? "
                             "WHERE id=? AND status IN ('planned','failed','interrupted','running')", (now(), task_id)).rowcount
        if not changed:
            raise ValueError('Tarefa não pode ser cancelada ou não pertence ao projeto.')
        event(db, 'task_cancelled', {'task_id': task_id, 'reviewer': reviewer, 'reason': reason})


def review_hypothesis(workspace: Path, project: str, key: str, decision: str,
                      reviewer: str, reason: str, ack: bool = False) -> None:
    if decision not in ('accepted', 'rejected', 'in_review'):
        raise ValueError('Decisão inválida.')
    if decision == 'accepted' and not ack:
        raise PermissionError('Aceitação exige conferência independente e --ack-reviewed-evidence.')
    reviewer, reason = text(reviewer, 120), text(reason, 1000)
    get_project(workspace, project)
    with open_db(project_root(workspace, project)) as db:
        if db.execute("SELECT status FROM stages WHERE name='finalizacao'").fetchone()[0] == 'completed':
            raise PermissionError('Avaliação finalizada: decisões estão fechadas.')
        changed = db.execute('UPDATE hypotheses SET status=?,reviewer=?,reason=?,reviewed_at=? WHERE id=?',
                             (decision, reviewer, reason, now(), key)).rowcount
        if not changed:
            raise KeyError('Hipótese não encontrada neste projeto.')
        db.execute("UPDATE stages SET status='pending',reviewer=NULL,reason=NULL,reviewed_at=NULL "
                   "WHERE name IN ('execucao','finalizacao')")
        event(db, 'human_decision', {'hypothesis_id': key, 'decision': decision, 'reviewer': reviewer, 'reason': reason})


def report_markdown(workspace: Path, project: str) -> str:
    from html import escape
    def safe(value):
        return escape(str(value)).replace('\n', ' ').replace('`', '&#96;').replace('[', '&#91;').replace(']', '&#93;')
    data = snapshot(workspace, project)
    p = data['project']
    complete = all(s['status'] == 'completed' for s in data['stages']) and _baseline_current(data)
    lines = [f'# TramontoSec AI — {safe(p["name"])}', '',
             '> DEMONSTRAÇÃO SINTÉTICA — sem sistemas reais.' if p['synthetic'] else '> CONFIDENCIAL — uso local autorizado.',
             '', '**Relatório preliminar**' if not complete else '**Etapas atestadas pelo auditor humano**',
             'A concordância entre agentes não substitui evidência independente.',
             'Nenhum teste ativo ou alteração de sistema foi realizado.',
             '', f'Objetivo: {safe(p["objective"])}',
             f'Escopo passivo: {safe(", ".join(p["scope"]["assets"]))}', '']
    for stage, label in zip(STAGES, STAGE_NAMES):
        s = next(s for s in data['stages'] if s['name'] == stage)
        lines += [f'## {STAGES.index(stage)+1}. {label}', '', f'Estado: {s["status"]}.',
                  f'Revisão: {safe(s["reviewer"] or "pendente")}; {safe(s["reason"] or "sem atestação")}.', '']
        if stage == 'preparacao':
            lines += [f'- Evidência `{e["id"]}`: {e["kind"]}; SHA-256 `{e["sha256"]}`.' for e in data['evidence']]
            if not p['scope']['repo']:
                lines.append('Sem repositório autorizado: baseline de código não avaliada neste escopo.')
        if stage == 'execucao':
            for t in data['tasks']:
                out = t['output'] or {}
                lines += [f'- Agente {t["profile"]}: {t["status"]}; modo: {out.get("mode", "sem resultado")}.']
                lines += [f'  - Limitação: {safe(u)}' for u in out.get('uncertainties', [])]
                if out.get('model_assessment'):
                    a = out['model_assessment']
                    lines += [f'  - Sugestão não confiável do modelo local: {safe(a["summary"])}',
                              f'  - Evidências citadas pelo modelo: {safe(", ".join(a["evidence_ids"]))}.']
            for h in data['hypotheses']:
                lines += ['', f'### {safe(h["title"])}', f'- ID: `{h["id"]}`; severidade proposta: {h["severity"]}; decisão: {h["status"]}.',
                          f'- Evidências: {", ".join(h["evidence"])}.', f'- Incerteza: {safe(h["uncertainty"])}.',
                          f'- Auditor: {safe(h["reviewer"] or "pendente")}; justificativa: {safe(h["reason"] or "pendente")}.']
                lines += [f'- Contraprova: {safe(c)}' for c in h['controls']]
            for rec in data['recommendations']:
                r = rec['payload']
                lines += ['', f'- Recomendação para `{r["hypothesis_id"]}`: {safe(r["mitigation"])}',
                          f'- Validação: {safe(r["validation"])}; aplicada: não.',
                          f'- Resposta a incidente: {safe(r["incident_response"])}']
    if not complete:
        lines += ['', 'Há etapas ou revisões pendentes. A avaliação não foi concluída.']
    return '\n'.join(lines) + '\n'


def export_project(workspace: Path, project: str) -> Path:
    content = report_markdown(workspace, project)
    output = project_root(workspace, project) / 'output'
    if output.is_symlink():
        raise PermissionError('Destino de relatório não pode ser link simbólico.')
    out = output / 'TRAMONTO_PRELIMINAR.md'
    if out.is_symlink():
        raise PermissionError('Arquivo de relatório não pode ser link simbólico.')
    out.write_text(content, encoding='utf-8')
    with open_db(project_root(workspace, project)) as db:
        event(db, 'report_exported', {'format': 'markdown', 'preliminary': 'Relatório preliminar' in content})
    return out
