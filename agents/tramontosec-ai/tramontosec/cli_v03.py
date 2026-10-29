"""Portuguese CLI additions; existing recovery commands remain compatible."""
from __future__ import annotations

import json
from pathlib import Path

from .contracts import STAGES


def add_commands(subs):
    create = subs.add_parser('project-create', help='Criar projeto com escopo local autorizado')
    create.add_argument('--project', required=True)
    create.add_argument('--name', required=True)
    create.add_argument('--objective', required=True)
    create.add_argument('--asset', action='append', required=True, dest='assets')
    create.add_argument('--repo', type=Path)
    create.add_argument('--synthetic', action='store_true')
    create.add_argument('--ack-authorized', action='store_true')
    subs.add_parser('projects', help='Listar projetos e escopos')
    subs.add_parser('agents', help='Consultar especialistas e ferramentas permitidas')
    subs.add_parser('models', help='Consultar disponibilidade do Ollama local, sem inferência')
    for name, help_text in (
        ('audit', 'Consultar estado, etapas, tarefas e hipóteses de um projeto'),
        ('history', 'Consultar histórico de decisões e atividades'),
        ('report', 'Exportar relatório Tramonto de um projeto'),
        ('plan', 'Planejar tarefas sequenciais para os especialistas'),
        ('run', 'Executar tarefas passivas com políticas verificadas'),
        ('stage', 'Atestar uma etapa do Tramonto como auditor humano'),
        ('evidence-import', 'Importar reconhecimento ou scanner sanitizado'),
        ('baseline', 'Registrar e verificar HEAD exato e árvore limpa'),
        ('analyze-local', 'Analisar AST Python sem executar código'),
        ('finding-review', 'Registrar decisão humana sobre hipótese'),
        ('task-cancel', 'Cancelar tarefa pendente ou interrompida com justificativa humana')):
        p = subs.add_parser(name, help=help_text)
        p.add_argument('--project', required=True)
        if name == 'plan':
            p.add_argument('--agent', choices=['red', 'static', 'blue'], action='append')
            p.add_argument('--objective')
        elif name == 'run':
            p.add_argument('--model', help='Modelo Ollama local opcional; sem modelo usa regras determinísticas')
            p.add_argument('--ack-local-model', action='store_true')
        elif name == 'stage':
            p.add_argument('--name', choices=STAGES, required=True)
            p.add_argument('--reviewer', required=True)
            p.add_argument('--reason', required=True)
            p.add_argument('--ack-human', action='store_true')
        elif name == 'evidence-import':
            p.add_argument('--tool', choices=['recon', 'semgrep', 'trivy', 'gitleaks', 'zizmor'], required=True)
            p.add_argument('--file', type=Path, required=True)
            p.add_argument('--commit')
            p.add_argument('--ack-redacted-input', action='store_true')
        elif name == 'baseline':
            p.add_argument('--expected-commit', required=True)
        elif name == 'analyze-local':
            p.add_argument('--path', required=True, help='Caminho Python relativo ao repositório autorizado')
        elif name == 'finding-review':
            p.add_argument('--id', required=True)
            p.add_argument('--decision', choices=['accepted', 'rejected', 'in_review'], required=True)
            p.add_argument('--reviewer', required=True)
            p.add_argument('--reason', required=True)
            p.add_argument('--ack-reviewed-evidence', action='store_true')
        elif name == 'task-cancel':
            p.add_argument('--id', required=True)
            p.add_argument('--reviewer', required=True)
            p.add_argument('--reason', required=True)
            p.add_argument('--ack-human', action='store_true')
    demo = subs.add_parser('demo', help='Executar demonstração acadêmica inteiramente fictícia e offline')
    demo.add_argument('--project', default='aurora-demo')
    demo.add_argument('--ack-synthetic-review', action='store_true',
                      help='Registrar em seu nome de demonstração uma decisão explicitamente sintética')
    dash = subs.add_parser('dashboard', help='Iniciar dashboard complementar em 127.0.0.1')
    dash.add_argument('--port', type=int, default=8765)


def dispatch(args, workspace: Path) -> bool:
    from . import evidence, orchestrator as rt, store
    from .contracts import Profile
    from .policy import allowed_tools
    from .providers import OllamaProvider, local_models
    command = args.command
    result = None
    if command == 'project-create':
        result = store.create_project(workspace, args.project, args.name, args.objective, args.assets,
                                      args.repo, args.synthetic, args.ack_authorized)
    elif command == 'projects':
        result = store.list_projects(workspace)
    elif command == 'agents':
        result = [{'profile': p.value, 'tools': allowed_tools(p), 'active_testing': False} for p in Profile]
    elif command == 'models':
        result = local_models()
    elif command == 'audit':
        result = store.snapshot(workspace, args.project)
    elif command == 'history':
        result = store.snapshot(workspace, args.project)['runtime_events']
    elif command == 'plan':
        result = rt.plan(workspace, args.project, args.agent, args.objective)
    elif command == 'run':
        provider = OllamaProvider(args.model, args.ack_local_model) if args.model else None
        result = rt.run(workspace, args.project, provider)
    elif command == 'stage':
        rt.attest_stage(workspace, args.project, args.name, args.reviewer, args.reason, args.ack_human)
        result = {'stage': args.name, 'status': 'completed', 'reviewer': args.reviewer}
    elif command == 'evidence-import':
        if args.tool == 'recon':
            key = evidence.import_recon(workspace, args.project, args.file, args.ack_redacted_input)
        else:
            key = evidence.import_scanner(workspace, args.project, args.tool, args.file, args.ack_redacted_input, args.commit)
        result = {'evidence_id': key, 'vulnerability_confirmed': False}
    elif command == 'baseline':
        result = evidence.baseline(workspace, args.project, args.expected_commit)
    elif command == 'analyze-local':
        result = {'evidence_id': evidence.analyze_local(workspace, args.project, args.path)}
    elif command == 'finding-review':
        rt.review_hypothesis(workspace, args.project, args.id, args.decision, args.reviewer, args.reason, args.ack_reviewed_evidence)
        result = {'hypothesis_id': args.id, 'decision': args.decision}
    elif command == 'task-cancel':
        rt.cancel_task(workspace, args.project, args.id, args.reviewer, args.reason, args.ack_human)
        result = {'task_id': args.id, 'status': 'cancelled'}
    elif command == 'report':
        result = {'report': str(rt.export_project(workspace, args.project))}
    elif command == 'demo':
        from .demo import run_demo
        result = run_demo(workspace, args.project, args.ack_synthetic_review)
    elif command == 'dashboard':
        from .dashboard import serve
        serve(workspace, args.port)
        return True
    else:
        return False
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return True
