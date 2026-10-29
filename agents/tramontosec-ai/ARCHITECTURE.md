# Arquitetura v0.3

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
