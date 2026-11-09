# Relatório da revisão agentes IA v2 — 0.5.0 em desenvolvimento

Conclusão local: 09/11/2026. Repositório projetos-ia; escopo agents/tramontosec-ai.
Branch de correções: fix/agentes-ia-v2, derivada de feat/agentes-ia no commit `3534bfb6bd58c8703aea9c4216e1fe09e2e57c8e`.
Destino solicitado para publicação: main. A inspeção remota não encontrou main; a principal anterior
MaraparaXD/Projetos-pessoas é ancestral do trabalho. O histórico pode ser preservado sem force push.
Nenhum release estável foi publicado. Licença e contato de segurança continuam TODOs.

## Resultado medido

- Antes: 99 testes, 98 passaram e 1 ignorado por symlink no Windows; Ruff limpo.
- Depois: 172 testes, 171 passaram e o mesmo caso foi ignorado; 73 novos testes Python.
- Última medição com Coverage: 52,607 s; cobertura de linhas do runtime: 93,52%.
- Ruff: `All checks passed!`, código 0. CI: `coverage report --fail-under=91.52`.
- JavaScript: sintaxe válida e teste DOM aprovado; ambas as origens, legado e notas usam textContent.
- Ambiente: Windows, Python 3.13.17, Ruff 0.15.22, Coverage 7.17.2 e Git 2.56.0.windows.4.
- A configuração de cobertura considera somente tramontosec; não inclui os próprios testes.
- Não houve Ollama/modelo real, teste ativo, scanner executado contra alvo ou remediação.

## Entrega por item

### 1. Severidade

Ordem explícita e piso do scanner por regra/evidência; severidade da regra preservada e divergência registrada.

Arquivos tocados: `tests/fakes_v2.py`, `tests/test_severity_floor.py`, `tramontosec/agent_validation.py`, `tramontosec/agents.py`.

Testes: 6 novos testes com FakeProvider: rebaixamento, aumento, maior piso, nível desconhecido e ausência de baseline/regra.

Verificação após o item: 105 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 2. Blue lado a lado

Mantém regra e LLM separadamente, incluindo armazenamento, Markdown, dashboard e leitura de registros legados. A nova chave inclui origem.

Arquivos tocados: `tests/test_blue_llm.py`, `tests/test_blue_origins_v2.py`, `tramontosec/agents.py`, `tramontosec/orchestrator.py`, `tramontosec/reports.py`, `tramontosec/store.py`, `tramontosec/web/app.js`.

Testes: 1 novo teste integrado de duas origens, SQLite e relatório; teste Blue existente atualizado de uma para duas recomendações, com justificativa no commit.

Verificação após o item: 106 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 3. Filtro de texto

Lista explícita de comandos e instruções, URLs, controles Unicode e excesso de linhas; rejeição com InvalidProposal.

Arquivos tocados: `tests/test_model_text_v2.py`, `tramontosec/agent_validation.py`.

Testes: 3 novos testes com casos maliciosos e prosa legítima; campos de hipótese e recomendação cobertos com FakeProvider.

Verificação após o item: 109 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 4. Aliases de regra

Regex único, alias rule-N sem colisão e mapa inverso interno; contexto e modo consultivo não expõem regra livre nem severidade arbitrária.

Arquivos tocados: `tests/test_rule_aliases_v2.py`, `tramontosec/agent_loop.py`, `tramontosec/agent_validation.py`, `tramontosec/agents.py`, `tramontosec/scanners.py`.

Testes: 4 novos testes: contexto de FakeProvider após importação maliciosa, estabilidade/colisão, IDs válidos e filtros, provider consultivo.

Verificação após o item: 113 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 5. Resumo e equivalências Static

get_alert_summary somente Static/read_metadata; contagens sem nomes. Proposta equivalente vira nota; várias regras/componentes permitem candidato adicional.

Arquivos tocados: `tests/test_static_llm.py`, `tests/test_static_summary_v2.py`, `tramontosec/agent_loop.py`, `tramontosec/agent_validation.py`, `tramontosec/agents.py`, `tramontosec/orchestrator.py`, `tramontosec/policy.py`, `tramontosec/providers.py`.

Testes: 6 novos testes: contagem completa, ausência de dados sensíveis, autorização, equivalência, agrupamento e persistência. Expectativa antiga de duplicação foi corrigida e justificada.

Verificação após o item: 119 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 6. Nota breve do modelo

why opcional validado; reasoning_trace contém motivo fixo e model_note ou None. Nota inválida não descarta a consulta. Blue também aparece no relatório.

Arquivos tocados: `tests/test_model_note_v2.py`, `tramontosec/agent_loop.py`, `tramontosec/contracts.py`, `tramontosec/orchestrator.py`, `tramontosec/providers.py`, `tramontosec/reports.py`, `tramontosec/web/app.js`.

Testes: 4 novos testes de nota válida, ausente, maliciosa e persistência/apresentação com FakeProvider.

Verificação após o item: 123 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 7. agent-check

Preflight GGUF existente e cinco repetições por perfil em workspace temporário; causas estruturadas, passos, propostas validadas e tempo. Indisponibilidade sai com erro.

Arquivos tocados: `docs/VALIDATION.md`, `tests/test_agent_check_v2.py`, `tramontosec/agent_check.py`, `tramontosec/agent_loop.py`, `tramontosec/agents.py`, `tramontosec/cli.py`, `tramontosec/cli_v03.py`, `tramontosec/contracts.py`, `tramontosec/providers.py`.

Testes: 6 novos testes da CLI injetável, workspace intocado, consentimento, falhas e contadores; nenhuma inferência real foi simulada como resultado.

Verificação após o item: 129 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 8. Benchmark

Três cenários por perfil (empty, ordinary, duplicates), repetitions=3, resultados por modo/origem, cobertura de referências, motivos e mediana/máximo.

Arquivos tocados: `docs/VALIDATION.md`, `tests/test_agent_benchmark.py`, `tests/test_benchmark_profiles_v2.py`, `tramontosec/benchmark.py`.

Testes: 4 novos testes; os dois testes antigos passaram a esperar 27 pares e métricas ampliadas, com justificativa no commit. Mantém vulnerability_detection_validated=False.

Verificação após o item: 133 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 9. Cobertura e qualidade

Erros e limites de transporte, leitores e CLI; correção de resposta legada acima de 32 KB, componente desconhecido e ID histórico. CI com piso 91,52% e teste DOM.

Arquivos tocados: `.github/workflows/tramontosec-tests.yml`, `.coveragerc`, `tests/dashboard_rendering.cjs`, `tests/test_cli_workflows_v2.py`, `tests/test_loop_errors_v2.py`, `tests/test_model_text_v2.py`, `tests/test_read_boundaries_v2.py`, `tests/test_static_summary_v2.py`, `tests/test_transport_limits_v2.py`, `tests/transport_fakes_v2.py`, `tramontosec/agent_loop.py`, `tramontosec/agent_validation.py`, `tramontosec/local_ai.py`.

Testes: 38 novos testes Python nesta etapa, além de verificações JavaScript de DOM em memória. Transportes falsos, FakeProvider, limites, redirecionamento e cloud bloqueados; sem testes vazios.

Verificação após o item: 171 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 10. Documentação, versão e desenvolvimento

Metadados em 0.5.0; README, changelog, arquitetura, AGENTS, SECURITY e VALIDATION alinhados. Aviso de desenvolvimento no repositório e dashboard.

Arquivos tocados: `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `README.md`, `SECURITY.md`, `docs/VALIDATION.md`, `pyproject.toml`, `tests/test_dashboard.py`, `tests/test_release_docs_v2.py`, `tramontosec/__init__.py`, `tramontosec/cli.py`, `tramontosec/web/index.html`.

Testes: 1 novo teste de consistência de versão/status; teste HTTP existente passa a conferir o aviso e a versão sem reduzir verificações de segurança.

Verificação após o item: 172 casos, um ignorado no Windows; Ruff `All checks passed!`.

### 11. Relatório final

Este relatório reúne mudanças, arquivos, testes, cobertura, medições e decisões pendentes.
Arquivos: `docs/AGENTES_IA_V2_REPORT.md`, links em `README.md` e `docs/VALIDATION.md`.
Sem código de runtime ou novos testes nesta etapa documental. Confirmação pós-relatório: 172 testes em 50,707 s, 171 passaram e um foi ignorado; Ruff All checks passed!.

As mudanças de expectativa dos testes existentes ficaram documentadas nos commits dos itens 2, 5 e 8.
Nenhum teste foi removido; os controles humanos existentes não foram relaxados.

## Cobertura por módulo: antes e depois

| Módulo | Antes | Depois |
|---|---:|---:|
| __init__.py | 100.00% | 100.00% |
| __main__.py | 0.00% | 100.00% |
| agent_check.py | — (novo) | 100.00% |
| agent_loop.py | 71.84% | 99.36% |
| agent_validation.py | 86.36% | 90.08% |
| agents.py | 95.24% | 96.45% |
| benchmark.py | 100.00% | 100.00% |
| cli.py | 0.00% | 98.14% |
| cli_v03.py | 0.00% | 100.00% |
| contracts.py | 91.07% | 93.65% |
| core.py | 89.00% | 89.00% |
| correlation.py | 94.12% | 94.12% |
| dashboard.py | 83.22% | 83.22% |
| demo.py | 97.92% | 97.92% |
| evidence.py | 85.50% | 85.50% |
| git_readonly.py | 85.71% | 85.71% |
| inventory.py | 52.83% | 100.00% |
| local_ai.py | 58.54% | 100.00% |
| locking.py | 85.71% | 85.71% |
| orchestrator.py | 90.72% | 90.77% |
| policy.py | 100.00% | 100.00% |
| providers.py | 70.00% | 100.00% |
| red_team.py | 94.06% | 94.06% |
| reports.py | 54.76% | 100.00% |
| scanners.py | 85.12% | 88.74% |
| store.py | 91.18% | 91.35% |
| **TOTAL** | **74.25%** | **93.52%** |

O piso de 91,52% é a cobertura medida, arredondada a duas casas, menos dois pontos percentuais.
O escopo e o tipo de métrica são iguais nas duas medições: cobertura de linhas do código de produção,
sem excluir módulos nem contar testes. Cobertura de linhas não é cobertura de ramos ou eficácia científica.

## Benchmark executado com FakeProvider

Ambos os ensaios abaixo foram executados explicitamente, com três repetições e nove combinações
de perfil/cenário. Não são resultados de Ollama e os tempos não estimam sua latência.

| Provedor offline | Pares | Hipóteses | Recomendações | Fallback | Motivo | Mediana / máximo (s) |
|---|---:|---:|---:|---:|---|---|
| Respostas válidas | 27 | 24 | 18 | 0.00% | {} | 0.0000820 / 0.0001408 |
| Falha deliberada nos cenários vazios | 27 | 24 | 18 | 33.33% | {'AgentLoopError': 9} | 0.0000797 / 0.0001196 |

Totais somam todas as execuções e incluem saídas repetidas de regras; não são achados únicos.
Cobertura de evidências conta IDs referenciados por hipóteses e recomendações.
O cenário vazio tem zero achados e cobertura zero. A memória do Blue é fixa, derivada de regras.
`vulnerability_detection_validated=False` permanece. Não há precisão, recall, exploração comprovada
ou qualidade de um modelo real medida por esse experimento.

## Preservação das travas

Comparação por AST confirmou que TOOLS, authorize/check_message, gates humanos, cancelamento,
revisão, checagem GGUF require_downloaded_model e _NoRedirect permanecem iguais à base.
dashboard.py também é idêntico: CSRF, CSP, Host/Origin, sessão e limite de loopback não foram alterados.
A única extensão de política foi get_alert_summary no READ_TOOLS do Static, com read_metadata, como solicitado.
Nenhuma dependência nova de runtime. Node 24 é somente ferramenta de teste JavaScript/CI.
Recomendações mantêm applied=False e independent_confirmation=False; modelos não decidem aceitação humana.

## Pendências e decisões do mantenedor

1. **Licença:** escolher explicitamente; nenhum arquivo de licença foi inventado.
2. **Contato de segurança:** definir canal privado/endereço; não foi escolhido e-mail.
3. **Modelo local:** escolher GGUF e executar o comando abaixo. Ainda não há resultado real de modelo.
4. **Limite de passos:** confirmar o padrão de seis turnos com base no ensaio. A API aceita 1–12; a CLI não amplia o padrão.
5. **Avaliação empírica:** cenários inéditos, ground truth e revisão independente continuam pendentes.
6. **Matriz remota:** os resultados Windows/Linux Python 3.11/3.13 devem ser consultados no GitHub Actions da publicação.
7. **Navegador real:** houve teste HTTP e DOM em memória, sem nova revisão visual de desktop/mobile.
8. **Dados históricos:** registros antigos não são apagados nem automaticamente reclassificados; duplicatas históricas exigem revisão humana.

```bash
python -m tramontosec agent-check --model NOME --ack-local-model
```

O comando existe e foi testado com FakeProvider; **o mantenedor precisa rodá-lo com seu modelo**.
Usa workspace temporário e cinco repetições por perfil. Indisponibilidade falha sem simular resultados.
Propostas validadas pelo contrato continuam não verificadas e sujeitas a decisão humana.

## Repetição final e ocorrência de transporte local

Uma repetição executou 172 casos e encontrou ConnectionAbortedError/WinError 10053
no teste HTTP negativo de CSRF, em 51,117 s. A causa estrutural não foi estabelecida.
O caso isolado passou em 2,127 s; uma repetição completa passou em 50,707 s,
com 172 testes, um ignorado e Ruff limpo. Não houve mudança no teste para ocultar
a falha, nem redução de assertivas ou alteração dos controles de CSRF/CSP.
A ocorrência deve ser acompanhada na matriz Windows/Linux da CI.

## Riscos e limitações observados

- O filtro é heurístico: pode bloquear prosa útil e não detecta toda instrução maliciosa. O fallback preserva regras.
- IDs que passam no regex podem conter informação privada. Aliasing não dispensa sanitização antes da importação.
- Aliases rule-N são estáveis para o mesmo conjunto de evidências; novos conjuntos podem renumerá-los.
- Contagens e agrupamentos dependem dos metadados do scanner. Componentes ausentes não demonstram componentes adicionais.
- O piso de severidade preserva prioridade do scanner, sem comprovar vulnerabilidade ou validar sua classificação.
- Duas recomendações por hipótese aumentam informação para o auditor; origem e aviso devem permanecer visíveis.
- model_note é texto público não verificado, limitado e escapado; não deve ser tratado como prova ou cadeia privada de raciocínio.
- Um servidor Ollama local adulterado ainda pode mentir sobre metadados. A confiança no host e a revisão humana permanecem necessárias.
- Cobertura elevada e FakeProvider não demonstram utilidade, robustez estatística ou segurança de um modelo real.
- SQLite não é cifrado pelo programa e eventos não constituem um registro inviolável.

Detalhes reproduzíveis e números medidos: [VALIDATION.md](VALIDATION.md).
