# TramontoSec AI — agentes locais LLM experimentais (v0.5)

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


## Instalação no Linux e macOS

Requisitos: Python 3.11+ e Git. Em distribuições Linux, instale o pacote
`python3-venv` quando necessário.

```bash
git clone https://github.com/MaraparaXD/projetos-ia.git
cd projetos-ia/agents/tramontosec-ai
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m tramontosec --help
python -m unittest discover -s tests -v
```

## Papel da IA — agentes experimentais

Sem Ollama, Red, Static e Blue continuam **determinísticos** e independentes
do modelo. Com um modelo GGUF local explicitamente autorizado, o runtime
pode solicitar até seis turnos JSON por especialista, utilizar ferramentas
**exclusivamente consultivas** e receber propostas tipadas.

- **Red Team:** cenários passivos sobre serviços efetivamente observados e
  controles apenas declarados; hipóteses equivalentes às regras são fundidas
  mantendo identificador estável e revisão humana.
- **Static:** agrupa alertas de regras existentes para priorizar revisão de
  possíveis falsos positivos; não executa nem lê código-fonte do alvo.
- **Blue Team:** sugere mitigação, controle compensatório, validação e triagem
  para hipóteses não rejeitadas, sem aplicar qualquer mudança.

O loop autoriza `list_assets`, `get_alerts`, `read_evidence`,
`list_hypotheses` e `get_hypothesis` **por perfil**. Recebe apenas
metadados limitados com aliases; caminhos, código, nomes reais e segredos
não são enviados ao modelo. JSON inválido, ferramenta proibida, ID
inventado, limite de passos e indisponibilidade do modelo resultam em
`deterministic_fallback`. Toda sugestão continua `candidate`, não
confirmada. O relatório registra origem e trilha resumida de ferramentas,
não a cadeia privada de raciocínio do modelo.

**Status experimental:** FakeProvider comprova contratos e integração,
não a qualidade de um Ollama real; ainda faltam avaliações empíricas,
escolha do modelo, validação de limites e métricas científicas em
cenários inéditos. Os resultados de benchmark sintético não medem detecção.

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
| red | analyze_recon, analyze_infra | Hipóteses passivas de rede e infraestrutura, exposição e contraprovas |
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

O novo importador `evidence-import --tool infra` aceita somente metadados
estruturados e sanitizados; veja [RED_TEAM.md](RED_TEAM.md).

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

## Testes da branch experimental

```bash
git switch feat/agentes-ia
cd agents/tramontosec-ai
python -m unittest discover -s tests -v
python -c "from tramontosec.benchmark import compare_agent_synthetic; print('Use FakeProvider dos testes para repetir a comparação offline.')"
```

A API do Ollama só fica ativa mediante `--model` e
`--ack-local-model`. Sem um modelo GGUF local verificado, teste
somente a execução determinística e o FakeProvider.
