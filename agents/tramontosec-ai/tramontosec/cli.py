"""Command-line interface for TramontoSec AI."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
from pathlib import Path
from .core import make_workspace, record_document, import_findings, list_findings, verify, review, export_report, no_sync_roots


def cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='tramontosec', description='TramontoSec AI v0.3 — auditoria passiva, especialistas e revisão humana')
    from . import __version__
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--workspace', type=Path, required=True, help='Pasta local autorizada, privada e fora de sincronização')
    subs = parser.add_subparsers(dest='command', required=True)
    ini = subs.add_parser('init', help='Inicializar workspace legado')
    ini.add_argument('--ack-authorized-secure-storage', action='store_true', required=True,
                     help='Confirme criptografia, ACLs e autorização do projeto')
    attach = subs.add_parser('attach', help='Indexar documento legado: somente hash e metadados')
    attach.add_argument('--id', required=True)
    attach.add_argument('--file', type=Path, required=True)
    attach.add_argument('--kind', choices=['external_assessment','whitebox_assessment','technical_note','scanner_report'], required=True)
    attach.add_argument('--period', default='')
    attach.add_argument('--note', default='')
    ingest = subs.add_parser('seed', help='Importar metadados JSON de achados legados')
    ingest.add_argument('--file', type=Path, required=True)
    subs.add_parser('list', help='Listar achados históricos e estados de revisão')
    up = subs.add_parser('upgrade', help='Atualizar esquema de workspace legado')
    up.add_argument('--ack-authorized-secure-storage', action='store_true', required=True)
    cat = subs.add_parser('catalog-report', help='Extrair IDs históricos de PDF/Markdown; não confirma vulnerabilidades')
    cat.add_argument('--id', required=True)
    cat.add_argument('--file', type=Path, required=True)
    cat.add_argument('--scope', choices=['external_assessment','whitebox_assessment'], required=True)
    cat.add_argument('--period', default='')
    gg = subs.add_parser('git-check', help='Consultar HEAD e árvore Git sem alterar repositório')
    gg.add_argument('--repo', type=Path, required=True)
    gg.add_argument('--expected-commit', default=None)
    scan = subs.add_parser('import-scan', help='Importar scanner sanitizado para workspace legado')
    scan.add_argument('--project', required=True)
    scan.add_argument('--tool', choices=['semgrep','trivy','gitleaks','zizmor'], required=True)
    scan.add_argument('--file', type=Path, required=True)
    scan.add_argument('--ack-redacted-input', action='store_true')
    al = subs.add_parser('alerts', help='Listar alertas sanitizados ainda não confirmados')
    al.add_argument('--project', default=None)
    al.add_argument('--full-id', action='store_true', help='Exibir SHA-256 completo para triagem')
    tr = subs.add_parser('triage', help='Registrar triagem humana de alerta legado')
    tr.add_argument('--alert-id', required=True)
    tr.add_argument('--status', choices=['relevant','false_positive','needs_context','duplicate','informational'], required=True)
    tr.add_argument('--reviewer', required=True)
    tr.add_argument('--reason', required=True)
    invent = subs.add_parser('ai-inventory', help='Consultar indícios de bibliotecas IA nos manifestos da raiz')
    invent.add_argument('--repo', type=Path, required=True)
    subs.add_parser('benchmark', help='Executar benchmark sintético de localização e commit')
    corr = subs.add_parser('correlate', help='Sugerir associação arquivo/linha sem veredicto automático')
    corr.add_argument('--project', required=True)
    corr.add_argument('--line-slack', type=int, default=3)
    v = subs.add_parser('verify', help='Localizar linhas referenciadas; não prova comportamento')
    v.add_argument('--web-repo', type=Path)
    v.add_argument('--api-repo', type=Path)
    v.add_argument('--mobile-repo', type=Path)
    rv = subs.add_parser('review', help='Decidir sobre achado legado como auditor humano')
    rv.add_argument('--key', required=True)
    rv.add_argument('--decision', required=True, choices=['accepted', 'in_review', 'rejected'])
    rv.add_argument('--reviewer', required=True)
    rv.add_argument('--reason', required=True)
    rv.add_argument('--ack-reviewed-code', action='store_true')
    subs.add_parser('export', help='Exportar minuta confidencial de workspace legado')
    ai = subs.add_parser('assist-local', help='Solicitar sugestão Ollama local para achado legado')
    ai.add_argument('--key', required=True)
    ai.add_argument('--model', required=True)
    ai.add_argument('--ack-local-model', action='store_true')
    from .cli_v03 import add_commands
    add_commands(subs)
    return parser


def main() -> None:
    import sys
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    args = cli().parse_args()
    workspace = args.workspace.expanduser()
    try:
        from .cli_v03 import dispatch
        if dispatch(args, workspace):
            return
        if args.command == 'init':
            if not args.ack_authorized_secure_storage:
                raise ValueError('Explicit confirmation of encrypted, private and authorized storage is required')
            make_workspace(workspace)
            print('Workspace initialized:', workspace)
        elif args.command == 'upgrade':
            from .core import require_workspace
            if not args.ack_authorized_secure_storage:
                raise ValueError('Explicit authorized-storage confirmation required')
            require_workspace(workspace)
            make_workspace(workspace)
            print('Workspace upgraded in place; existing findings preserved')
        elif args.command == 'catalog-report':
            from .reports import catalog_report
            result = catalog_report(workspace, args.id, args.file, args.scope, args.period)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == 'git-check':
            from .git_readonly import inspect_repo, compare_commit
            result = inspect_repo(args.repo)
            if args.expected_commit:
                result.update(compare_commit(args.expected_commit, result))
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == 'import-scan':
            from .scanners import import_scan
            result = import_scan(workspace, args.project, args.tool, args.file, args.ack_redacted_input)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == 'alerts':
            from .scanners import list_alerts
            result = list_alerts(workspace, args.project)
            for item in result:
                print(f'{item["alert_id"] if args.full_id else item["alert_id"][:14]} {item["project"]:<15} {item["tool"]:<8} {item["triage"]:<16} {item["rule_id"][:50]}')
        elif args.command == 'triage':
            from .scanners import triage_alert
            triage_alert(workspace, args.alert_id, args.status, args.reviewer, args.reason)
            print('Human triage recorded; no finding was automatically approved')
        elif args.command == 'ai-inventory':
            from .inventory import scan_manifests
            print(json.dumps(scan_manifests(args.repo), ensure_ascii=False, indent=2))
        elif args.command == 'correlate':
            from .correlation import correlate_candidates
            print(json.dumps(correlate_candidates(workspace,args.project,args.line_slack),
                             ensure_ascii=False, indent=2))
        elif args.command == 'benchmark':
            from .benchmark import run_benchmark
            print(json.dumps(run_benchmark(), ensure_ascii=False, indent=2))
        elif args.command == 'attach':
            info = record_document(workspace, args.id, args.file, args.kind, args.period, args.note)
            print(json.dumps(info, ensure_ascii=False, indent=2))
        elif args.command == 'seed':
            created, existed = import_findings(workspace, args.file)
            print(f'Imported {created}, already existing {existed}; no code inspected')
        elif args.command == 'list':
            for item in list_findings(workspace):
                print(f'{item["finding_key"]:<24} {item["classification"]:<4} {item["severity"]:<13} {item["status"]:<12} {item["title"]}')
        elif args.command == 'verify':
            repos = {k:p for k,p in [('web',args.web_repo),('api',args.api_repo),('mobile',args.mobile_repo)] if p}
            for result in verify(workspace, repos):
                print(f'{result["finding_key"]}: {result["repo"]}/{result["path"]}:{result["range"]} =>'
                      f' {result["status"]}; commit={result["commit_verified"]};'
                      f' clean={result["worktree_clean"]}; baseline={result["baseline_valid"]};'
                      ' semantic_review=HUMAN_REQUIRED')
        elif args.command == 'review':
            review(workspace, args.key, args.decision, args.reviewer, args.reason, args.ack_reviewed_code)
            print('Review recorded; report requires human judgment on each finding')
        elif args.command == 'export':
            print('Draft written:', export_report(workspace))
        elif args.command == 'assist-local':
            from .core import require_workspace
            require_workspace(workspace)
            from .local_ai import local_suggestion
            print('LOCAL AI SUGGESTION ONLY — NOT AUDIT EVIDENCE OR HUMAN APPROVAL\n')
            print(local_suggestion(workspace, args.key, args.model, args.ack_local_model))
    except (ValueError, FileNotFoundError, KeyError, OSError) as error:
        cli().exit(2, f'Erro: {error}\n')
    except (sqlite3.Error, subprocess.SubprocessError):
        cli().exit(2, 'Erro: falha ao acessar banco local ou Git. Confira o workspace e os requisitos.\n')
    except KeyboardInterrupt:
        cli().exit(130, 'Operação interrompida pelo auditor.\n')


if __name__ == '__main__':
    main()
