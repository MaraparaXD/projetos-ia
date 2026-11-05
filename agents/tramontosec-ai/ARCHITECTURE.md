# Arquitetura v0.3 com incremento Red Team v0.4

```text
CLI ──────────┐
Dashboard ────┴─> serviços do núcleo e gates Tramonto
                            │
                 orquestrador sequencial
                   Red → Static → Blue
                            │
              allowlist e ferramentas tipadas
                            │
               SQLite separado por projeto
                            │
                  Ollama local opcional
```

`contracts.py`: TaskMessage/AgentResult versionados. `policy.py`: ToolSpec e
allowlist imutável. `agents.py`: especialistas. `orchestrator.py`: planejamento,
gates, execução, correlação, revisão e relatórios. `store.py`: persistência.
O esquema original 2 é preservado; `runtime_meta` identifica a extensão v0.3.

Tarefas: planned → running → completed/failed. Uma execução interrompida vira
interrupted na próxima execução. Cancelamento humano justificado produz
cancelled. Lock do SO impede runtimes simultâneos e é liberado com o processo.
Mensagens, resultados e eventos persistem. Hipóteses correlacionam mesma
regra/localização/linha/componente/commit, sem presumir independência das fontes.
Novas fontes ligadas a uma hipótese invalidam sua aceitação anterior.

Importadores reutilizam os leitores sanitizados recuperados. AST Python só
reconhece chamadas diretas eval/exec: não executa alvo nem faz análise semântica
completa. Git consulta HEAD e árvore limpa sem hooks/fsmonitor/rede.

`Provider` é um Protocol desacoplado. Ollama opcional usa a API oficial
[generate](https://docs.ollama.com/api/generate), JSON, timeout e validação de
evidências/ferramentas. Falhas não impedem o núcleo determinístico. Nenhum
framework multiagente adicional é necessário: runtime pequeno, auditável,
offline, sem dependência/licença de framework para manter.

HTML/CSS/JS recebem snapshots do núcleo. Endpoints permitem listar projetos,
consultar snapshot, exportar Markdown e revisar hipóteses. Token efêmero,
cookie HttpOnly/SameSite, CSRF, Host/Origin e CSP protegem o acesso local.
O [http.server](https://docs.python.org/3.13/library/http.server.html) não é
servidor de produção completo; não publicar o dashboard na rede.


## Compatibilidade explícita: legado v0.2 e runtime v0.3

O módulo `cli.py` mantém a entrada única. Os seguintes comandos pertencem
à camada legada v0.2 e permanecem operacionais: `init`, `attach`, `seed`,
`list`, `upgrade`, `catalog-report`, `git-check`, `import-scan`,
`alerts`, `triage`, `ai-inventory`, `benchmark`, `correlate`,
`verify`, `review`, `export` e `assist-local`.

Suas tabelas originais, implementadas em `core.py`, são:
`documents`, `findings`, `report_catalog`, `scanner_runs`, `alerts`
e `events`. O `PRAGMA user_version = 2` é mantido. Não converter
automaticamente esses registros em hipóteses aceitas do runtime novo.

Os comandos adicionados em v0.3 por `cli_v03.py` são:
`project-create`, `projects`, `agents`, `models`, `audit`,
`history`, `report`, `plan`, `run`, `stage`, `evidence-import`,
`baseline`, `analyze-local`, `finding-review`, `task-cancel`,
`demo` e `dashboard`. A camada em `store.py` mantém
`runtime_meta`, `project`, `stages`, `evidence`, `tasks`,
`hypotheses`, `recommendations` e `runtime_events` no banco
**separado de cada projeto**. O runtime evoluiu incrementalmente para v0.4
com o importador `infra` e sem remover a camada v0.2.

Os arquivos SQLite v0.2 e v0.3 não são automaticamente migrados entre
escopos: a CLI legada consulta o workspace histórico e os projetos novos
utilizam `<workspace>/projects/<id>/`. Ambos podem coexistir no mesmo
workspace, mas evidências, gates e decisões de cada camada não se misturam.

## Especialização LLM experimental (branch feat/agentes-ia)

O `agent_loop.py` controla no máximo seis iterações com respostas JSON
`action=tool|final`. `policy.READ_TOOLS` limita consultas por perfil.
Os dados vêm de evidências importadas e memória em SQLite, exclusivamente
via representação sanitizada sem nomes de ativos, IPs, caminhos e código.
`agent_validation.py` rederiva IDs estáveis e valida referências, escopo,
severidade, tamanho, estados e lista de campos; nenhuma string do modelo
vira comando, autorização, decisão ou correção.

`OllamaProvider.agent_step` utiliza apenas o serviço
`127.0.0.1:11434`, sem proxy ou redirect, e verifica metadados GGUF locais
antes de cada consulta. O runtime executa a ordem Red → Static → Blue; cada
modelo pode falhar de forma recuperável, mantendo o baseline de regras e
registrando `deterministic_fallback`. Problemas de infraestrutura internos
continuam gerando falha de tarefa, sem ocultá-la.

Os `runtime_events` guardam o nome da ferramenta consultiva e um motivo
predefinido, sem prompt bruto nem cadeia de raciocínio. As saídas versionadas
guardam `reasoning_trace` curto e `origin=rule|llm`; snapshots e relatório
derivam a origem desses resultados, sem alteração destrutiva do esquema
legado. Hipóteses seguem `candidate`; somente o auditor pode aprovar.
A análise do benchmark sintético **não** atesta qualidade de detecção.
