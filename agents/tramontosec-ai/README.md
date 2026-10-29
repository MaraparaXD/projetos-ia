# TramontoSec AI v0.3 Multi-Agent

Auditoria local assistida pelo Tramonto, com três especialistas sequenciais,
políticas externas ao modelo, evidências persistentes e revisão humana.
Projeto acadêmico em Sistemas de Informação na UFOPA.

**Sem modelo habilitado, o processamento é determinístico e isso aparece nos resultados.**
Ollama local é opcional. Não há pentest ativo, execução de scanners nem remediação
automática. Testes funcionais não demonstram eficácia científica de detecção.

## Instalação no Windows

Requisitos: Python 3.11+ e Git no PATH. Runtime somente com biblioteca padrão;
setuptools é usado para empacotamento. PDF requer pypdf opcional.

```powershell
git clone https://github.com/MaraparaXD/projetos-ia.git
cd projetos-ia\agents\tramontosec-ai
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m tramontosec --help
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Também é possível executar diretamente `python -m tramontosec` na pasta do
agente sem instalação. O layout `tramontosec/` preserva compatibilidade com o
ZIP; não foi necessária migração para `src/`.

## Demonstração offline e dashboard

```powershell
$ws = Join-Path $env:LOCALAPPDATA 'TramontoSec-Demo'
.\.venv\Scripts\python.exe -m tramontosec --workspace "$ws" demo --ack-synthetic-review
.\.venv\Scripts\python.exe -m tramontosec --workspace "$ws" audit --project aurora-demo
.\.venv\Scripts\python.exe -m tramontosec --workspace "$ws" dashboard
```

Abra o link privado de sessão exibido pela CLI. O servidor escuta somente em
127.0.0.1; Ctrl+C encerra. Não exponha a porta. Para repetir a demonstração,
escolha outro `--project`. A CLI funciona sem navegador.

## Agentes e comandos

| Perfil | Ferramenta | Capacidade atual |
|---|---|---|
| red | analyze_recon | Hipóteses passivas de exposição HTTP, SSH e banco; contraprovas |
| static | analyze_static | Alertas por regra/arquivo/linha/commit; correlação conservadora |
| blue | review_controls | Prioridade proposta, controles, mitigação, resposta a incidentes e validação; nada aplicado |

Contratos versionados, ferramentas tipadas e memória por projeto implementam
os perfis. No modo assistido, Ollama interpreta metadados e propõe ferramentas
somente da allowlist. Nenhuma resposta do modelo vira decisão humana.

```text
project-create  projects        agents           audit
plan            run             history          stage
evidence-import baseline        analyze-local    finding-review
task-cancel     report          models           demo       dashboard
```

Use `--help` em cada comando. Antes de `run`, o auditor atesta `adequacao`,
`verificacao` e `preparacao`. Novas evidências invalidam Preparação e etapas
posteriores. Planos antigos não aceitam alterações silenciosas: cancele com
`task-cancel` e planeje novamente. [DEMO.md](DEMO.md) contém o fluxo completo.

## Ollama opcional

```powershell
python -m tramontosec --workspace "$ws" models
python -m tramontosec --workspace "$ws" plan --project aurora-demo --agent red
python -m tramontosec --workspace "$ws" run --project aurora-demo --model NOME_LOCAL --ack-local-model
```

Instale modelos separadamente. O adaptador exige modelo GGUF local e bloqueia
aliases cloud, proxies e redirects. Configure `OLLAMA_NO_CLOUD=1` **no servidor
Ollama** e reinicie-o; uma variável na CLI não altera servidor já iniciado.
Veja a [documentação oficial](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).
São enviados somente metadados limitados (regras, severidades, serviços,
controles, IDs e contagens), sem código, nomes de ativos, caminhos ou documentos.
Falhas viram `deterministic_fallback`. Nenhum provedor externo é implementado.

## Compatibilidade e limites

Os comandos recuperados continuam disponíveis para workspaces legados.
Não há migração automática de evidências antigas para projetos v0.3. Cada
projeto usa banco separado em `<workspace>/projects/<id>/`.
Guarde dados fora do Git e de pastas sincronizadas, com ACLs e volume protegido.
SQLite não é cifrado pelo programa. A confirmação humana não verifica BitLocker
nem autentica a identidade do auditor. Dashboard é apenas para um operador local.

Documentos: [arquitetura](ARCHITECTURE.md), [agentes](AGENTS.md),
[Tramonto](TRAMONTO.md), [segurança](SECURITY.md), [pesquisa](RESEARCH.md),
[roadmap](ROADMAP.md), [changelog](CHANGELOG.md),
[recuperação](docs/RECOVERY.md) e [validação](docs/VALIDATION.md).
