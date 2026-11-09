# Validação 0.5.0 — em desenvolvimento

Registro de execuções locais em 06/11/2026 e conclusão em 09/11/2026.
Sem avaliação científica de detecção ou inferência de modelo real declarada.

## Ambiente e linha de base

Windows, Python 3.13.17, Ruff 0.15.22 e Coverage 7.17.2. Git 2.56.0.windows.4.
Runtime sem dependências externas; Ruff/Coverage são ferramentas de desenvolvimento.
Os testes JavaScript usam Node 24 (localmente, o Node já incluído no VS Code).

Antes das correções, `python -m unittest discover -s tests` executou 99 casos:
98 passaram e um foi ignorado por falta de permissão de criação de symlink
no Windows, em 21,384 s. `ruff check .`: `All checks passed!`, código 0.

Execução final da etapa de documentação: 172 testes, 171 passaram e um foi
ignorado por symlink no Windows, em 52,607 s, sob Coverage.
`ruff check .`: `All checks passed!`, código 0. O relatório de cobertura
terminou em 93,52% e passou com `--fail-under=91.52`.

## Cobertura de linhas do código de produção

`coverage run --source=tramontosec -m unittest discover -s tests` na linha de
base; a configuração equivalente em `.coveragerc` passou a fixar a origem
`tramontosec`. Nenhum teste entra no denominador. Não é cobertura de ramos.

| Módulo | Antes | Depois |
|---|---:|---:|
| __init__.py | 100.00% | 100.00% |
| __main__.py | 0.00% | 100.00% |
| agent_check.py | — | 100.00% |
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

O piso da CI é `coverage report --fail-under=91.52`: cobertura medida de
93,52% menos dois pontos percentuais. A matriz Windows/Linux com Python
3.11/3.13 permanece; seu resultado deve ser consultado no GitHub Actions
do commit publicado. Execução configurada não significa execução remota aprovada.

## Verificações executadas

A suíte usa somente dados sintéticos, FakeProvider e transportes HTTP falsos;
os testes do dashboard fazem requisições reais apenas ao servidor loopback local.
São exercitados referências e perfis, gates, decisões humanas, persistência,
registros legados, aliasing, piso de severidade, agrupamentos e notas, limites de
loop/contexto/resposta, JSON malformado, cloud e redirecionamentos bloqueados,
manifestos inválidos, limites de relatório e fluxos de CLI temporários.

`node --check tramontosec/web/app.js` e `node tests/dashboard_rendering.cjs`
foram executados com sucesso. O segundo verifica ambas as origens do Blue,
registros legados e model_note usando DOM em memória; texto inesperado continua
literal e não executa HTML. Isso não é revisão visual de navegador real.
Não se repetem aqui alegações antigas de Playwright, wheel ou validação em WSL.

## Benchmark sintético dos três perfis

`compare_agent_synthetic(provider, repetitions=3)` cobre `empty`, `ordinary`
e `duplicates` por perfil. Há 27 pares baseline/agente (54 execuções).
O provedor é reutilizado com contexto novo a cada execução.

Os resultados separam perfil, cenário e modo, contagens por origem, cobertura
de IDs de evidência incluindo o Blue, fallback por classe, mediana e máximo de
tempo. Totais somam repetições; não representam achados únicos. Vazio tem
cobertura zero. A memória do Blue é fixa e vem de regras, sem aprendizado.

Mede contratos, referências e comportamento operacional. Não mede precisão,
recall, exploração, qualidade da decisão humana, segurança de modelo
real ou validade científica. Tempos de FakeProvider não estimam Ollama.
`vulnerability_detection_validated=False` e limitações são obrigatórios.
Ground truth independente, cenários inéditos e revisão cega continuam pendentes.


Execuções explícitas adicionais com FakeProvider (09/11/2026):

| Ensaio offline | Pares | Hipóteses | Recomendações | Fallback | Motivos | Mediana / máximo (s) |
|---|---:|---:|---:|---:|---|---|
| Respostas válidas | 27 | 24 | 18 | 0.00% | {} | 0.0000820 / 0.0001408 |
| Falha deliberada nos cenários vazios | 27 | 24 | 18 | 33.33% | {'AgentLoopError': 9} | 0.0000797 / 0.0001196 |

Esses tempos descrevem somente este FakeProvider nesta máquina, sem inferência.

## Ensaio com o modelo do mantenedor

```bash
python -m tramontosec agent-check --model NOME --ack-local-model
```

Cinco repetições por perfil, na ordem Red → Static → Blue, com demonstração
sintética em workspace temporário removido ao terminar. Não grava em projeto
do auditor, nem utiliza um `--workspace` informado. O preflight e cada consulta
usam a checagem GGUF existente, sem cloud/proxy/redirects.

Cada tentativa informa modo, classe do fallback sem texto do modelo, passos
(incluindo final), quantidades produzidas, propostas de modelo validadas pelo
contrato e tempo com orquestração. Proposta validada não é aceite humano.
Indisponibilidade inicial falha sem simular; erro do adaptador durante o ensaio
também resulta em saída não zero.

O comando foi testado com FakeProvider. **O mantenedor precisa executá-lo com
seu modelo GGUF local; nenhum resultado de modelo real foi inventado.**

## Pendências e limites

Escolher licença, contato de segurança e modelo local. Confirmar limite de
passos: padrão seis turnos; API Python aceita de 1 a 12, e a CLI não o amplia.
Revisar privacidade de identificadores, falsos positivos do filtro e utilidade
de propostas sem reduzir os gates. Dados históricos não são apagados nem
retroativamente aceitos. Cobertura elevada não demonstra ausência de defeitos.

Relatório completo por item: [revisão agentes IA v2](AGENTES_IA_V2_REPORT.md).

Repetição pós-relatório: 172 casos em 50,707 s, 171 passaram e um foi ignorado;
Ruff All checks passed!. Uma execução anterior dessa repetição teve WinError
10053 no teste HTTP negativo de CSRF. O caso isolado passou em 2,127 s e a
repetição completa acima passou, sem relaxar assertivas ou modificar CSRF/CSP.
A causa estrutural do reset local não foi estabelecida.

## Validação da integração em main — GitHub Actions

O workflow [TramontoSec tests](https://github.com/MaraparaXD/projetos-ia/actions/runs/42632284320) foi concluído com sucesso em
09/11/2026 para o commit 2cae2934dc0ed5d746ec329f5d1754c49ae4a523,
presente na main e na fix/agentes-ia-v2. Foram sete jobs aprovados:

| Ambiente | Resultado real | Tempo da suíte |
|---|---|---:|
| Ubuntu / Python 3.11 | 172 testes, OK, sem skips | 7,079 s |
| Ubuntu / Python 3.13 | 172 testes, OK, sem skips | 5,352 s |
| Windows / Python 3.11 | 172 testes, OK, sem skips | 71,657 s |
| Windows / Python 3.13 | 172 testes, OK, sem skips | 91,948 s |

O job Coverage/Ubuntu Python 3.13 executou 172 testes em 8,070 s e mediu
93,57% (2378 linhas executáveis, 153 não cobertas), passando com piso 91,52%.
O valor local de 93,52% acima permanece como medição Windows comparável à base.
Os jobs de Ruff/JavaScript e demonstração sintética também passaram.
Não houve inferência real de LLM nesses jobs.

Esta atualização registra a integração solicitada em main após os 11 commits
da revisão. Altera somente documentação; os módulos de produção são os mesmos
que passaram na matriz acima. A branch principal anterior não foi apagada.

Verificação local desta atualização documental: 172 testes em 50,105 s,
171 passaram e um foi ignorado por symlink; Ruff All checks passed!.
