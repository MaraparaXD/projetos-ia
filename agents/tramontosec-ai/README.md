# TramontoSec AI — agentes locais LLM experimentais (v0.5.0)

> **EM DESENVOLVIMENTO — versão 0.5.0 experimental.** Sem avaliação científica de detecção ou validação com um modelo real nesta entrega.

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
git clone --branch main https://github.com/MaraparaXD/projetos-ia.git
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
git clone --branch main https://github.com/MaraparaXD/projetos-ia.git
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

O loop autoriza `list_assets`, `get_alerts`, `get_alert_summary`,
`read_evidence`, `list_hypotheses` e `get_hypothesis` por perfil.
Ativos usam aliases; os campos de caminho, mensagens e trechos de código
são omitidos do contexto. IDs sintaticamente válidos ainda exigem revisão
de privacidade antes da importação.

- Static consulta `get_alert_summary` para contar alertas, severidades,
  arquivos e componentes por regra, sem receber seus nomes.
- `rule_id` fora de `^[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}$` usa `rule-N`,
  sem enviar o mapa inverso ao modelo; o contexto informa `rule_alias_used`.
- A severidade de uma proposta Static respeita a maior severidade do scanner
  nas regras/evidências citadas. Regras existentes conservam sua severidade;
  discordâncias ficam registradas. `Indeterminada` não integra a ordem.
- Propostas equivalentes viram notas no `uncertainty` da regra. Um candidato
  Static novo exige agrupamento de várias regras ou componentes conhecidos.
- Blue preserva recomendações `origin="rule"` e `origin="llm"` lado a lado,
  sem aplicar mudanças. A sugestão LLM recebe aviso de modelo não verificado.
- O filtro explícito rejeita comandos, instruções de aprovação, URLs,
  controles Unicode e mais de duas quebras de linha. É uma heurística,
  não uma garantia contra toda injeção.
- `reasoning_trace` separa o motivo fixo da ferramenta do `model_note`:
  nota breve e não verificada derivada de `why`. Uma nota inválida é descartada
  sem invalidar a ferramenta. Não é a cadeia privada de raciocínio do modelo.

JSON inválido, ferramenta proibida, referências inexistentes, orçamento
excedido e indisponibilidade resultam em `deterministic_fallback`.
`fallback_reason=ClasseDoErro` registra a causa sem copiar a resposta.
Contadores de propostas validadas pelo contrato não representam aceite humano.

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
agent-check
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
No loop de agentes são enviados metadados limitados (regras, severidades, serviços,
controles, IDs e contagens). Campos de código, ativos, caminhos e documentos são omitidos;
identificadores de regra válidos sintaticamente ainda podem conter dados privados.
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

## Verificação da versão em desenvolvimento

```bash
git switch main
cd agents/tramontosec-ai
python -m unittest discover -s tests -v
python -c "from tramontosec.benchmark import compare_agent_synthetic; print('Use FakeProvider dos testes para repetir a comparação offline.')"
```

A inferência exige `--model` e `--ack-local-model`. O comando `models`
consulta somente disponibilidade e nomes de modelos locais, sem inferência. Sem um modelo GGUF local verificado, teste
somente a execução determinística e o FakeProvider.


## Ensaio com seu modelo local

```bash
python -m tramontosec agent-check --model NOME --ack-local-model
```

Faz cinco repetições por perfil sobre a demonstração sintética, em workspace
temporário removido ao terminar. Não exige `--workspace`; se informado, esse
workspace não é usado pelo ensaio. Exibe modo, motivo do fallback, passos,
quantidades, propostas validadas e tempo por perfil. Ollama/modelo indisponível
gera saída diferente de zero, sem simulação. A checagem GGUF original é usada.
**O mantenedor precisa executar esse comando com seu modelo: não houve
inferência real de LLM nesta validação.**

`compare_agent_synthetic(provider, repetitions=3)` cobre três cenários por perfil,
incluindo vazio e duplicatas, com mediana/máximo de tempo e fallback por motivo.
Mede contratos e operação; `vulnerability_detection_validated=False` permanece.

```bash
python -m unittest discover -s tests
ruff check .
coverage run -m unittest discover -s tests
coverage report --fail-under=91.52
node --check tramontosec/web/app.js
node tests/dashboard_rendering.cjs
```

Ruff/Coverage são ferramentas de desenvolvimento já declaradas. Node 24 é usado
somente no teste JavaScript e na CI; o runtime Python continua somente stdlib.
Consulte [VALIDATION](docs/VALIDATION.md) para números reais e limitações.

TODO do mantenedor: escolher licença, definir contato de segurança, escolher o
modelo GGUF do `agent-check` e confirmar o orçamento de passos (padrão atual: 6).

O comando legado `assist-local` envia metadados do achado (título, resumo,
classificação, severidade e incerteza). Revise a sanitização desses campos antes
usá-lo; nomes de campos não garantem ausência de informação privada.

Relatório completo por item: [revisão agentes IA v2](docs/AGENTES_IA_V2_REPORT.md).
