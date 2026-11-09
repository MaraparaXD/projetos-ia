# Validação executada — 29/10/2026

## Recuperação

ZIP original e 23 arquivos preservados fora do repositório público, com manifesto
SHA-256. ZIP: `fe2d1bda87ffb183b9753b102bdde7c27b986430faf04ecebc98f56dd619edb0`.
Antes de desenvolver: **28 testes originais, OK**, Windows/Python 3.13.14.
Consulte [RECOVERY.md](RECOVERY.md) para inspeção e inconsistência de versão.

## Suíte v0.3

Comando: `python -m unittest discover -s tests -v`.

| Ambiente | Resultado executado |
|---|---|
| Windows / Python 3.13.14 | 64 testes: 63 passaram, 1 skip por permissão para criar symlink; 30,255 s |
| WSL Ubuntu 22.04 / Python 3.11.17 | 64 passaram, sem skips; 27,822 s |
| WSL Ubuntu 22.04 / Python 3.13.16 | 64 passaram, sem skips; 34,954 s |

Inclui os 28 testes originais sem alterações, 30 novos testes de runtime e
segurança e 6 testes HTTP reais do dashboard. Cobertura: perfis e contratos,
persistência, gates, revisão, falhas, cancelamento, memória, importadores,
baseline, AST, idempotência, isolamento, SQLite Windows, path traversal,
symlinks (Linux), prompt injection, resposta/erro de provedor, cloud bloqueado,
CSRF, Host/Origin, sessão, relatório e dados sintéticos.

Falhas encontradas durante implementação (SQL de inserção, erro transitório de
sintaxe e consistência de plano) foram corrigidas antes destas execuções finais.
Um ensaio Linux foi afetado por edição simultânea; a suíte estável foi executada
novamente. Resultados acima correspondem a execuções completas bem-sucedidas.

## CLI, navegador e empacotamento

- Instalação editável em venv, `pip check`, CLI/ajuda, demonstração offline e
  wheel executados. Wheel inclui HTML/CSS/JS; nenhum dado operacional é empacotado.
- Playwright/Chromium real em 1440×1000 e 390×844. Capturas completas inspecionadas.
- Navegação de evidências/histórico, decisão sintética persistida, bloqueio de
  aceite sem confirmação e download Markdown exercitados.
- Mobile: documentElement.scrollWidth = 390, sem overflow horizontal do documento.
- Página final sem erros ou avisos de console. Somente requisições loopback.
- Detector visual mecânico: `[]`; revisão independente solicitou maior contraste
  nas bordas de campos. Corrigido mantendo os divisores estruturais discretos.
  O revisor confirmou a correção em desktop/mobile e retornou `ship` para esse
  ajuste, sem regressões introduzidas por ele. Foco em evidências e explicação
  de bloqueio após finalização também foram acrescentados.
- `node --check` validou JavaScript e compileall validou módulos Python.

## IA e limites

`models` consultou Ollama local: nenhum modelo disponível. **Não houve inferência
real de LLM nesta validação.** Mocks de transporte/resposta testam contrato,
fallback e restrições, não eficácia. Não foram executados scanners contra alvos,
testes ativos ou alterações em sistemas auditados. Scanners de revisão do
próprio código público rodaram somente no checkout desta entrega.

Não houve experimento científico comparativo. A CI configurada usa Windows e
Linux com Python 3.11/3.13; resultados de CI devem ser consultados na execução
do commit publicado, sem presumir sucesso antes de sua execução.

## Comparação sintética dos três perfis

compare_agent_synthetic(provider, repetitions=3) executa três cenários por perfil:
empty (sem achados), ordinary e duplicates (alerta e serviço repetidos). São
27 pares baseline/agente por padrão, 54 execuções ao todo. O provedor injetado
é reutilizado, com contexto novo por execução; testes usam FakeProvider offline.

O resultado separa perfil, cenário e modo, contagens de hipóteses/recomendações
por origem, cobertura de IDs de evidência (incluindo referências do Blue), taxa
e classe do fallback, mediana e máximo do tempo por execução. Os totais somam
as repetições, não representam achados únicos. No cenário vazio a cobertura é
zero; referências não demonstram qualidade. A memória do Blue é fixa e derivada
das regras, sem aprendizado ou acúmulo de notas entre repetições.

Mantém vulnerability_detection_validated=False e limitações explícitas. Mede
contratos, preservação do baseline, referências e comportamento operacional.
Não mede precisão, recall, exploração, segurança de modelo real, qualidade de
recomendações ou validade científica. Tempo de FakeProvider não estima latência
do Ollama. Mediana/máximo não substituem intervalos de confiança, ground truth,
cenários inéditos e revisão cega independente.

## Ensaio local de robustez dos agentes

Comando: python -m tramontosec agent-check --model NOME --ack-local-model

Executa cinco repetições por perfil, na ordem Red → Static → Blue, usando a
demonstração sintética em workspace temporário apagado ao terminar. Não usa o
workspace indicado pelo auditor. O preflight usa a mesma checagem de modelo GGUF
local do adaptador; indisponibilidade encerra com erro, sem simular inferência.

Cada repetição informa modo, classe do fallback (sem conteúdo do modelo), passos
de inferência tentados (incluindo o final), quantidades produzidas, propostas de
modelo validadas pelo contrato e tempo com orquestração. Proposta validada não é
hipótese aceita pelo auditor: todas continuam candidatas e não verificadas.
Erros do adaptador durante a execução também produzem saída não zero.

Esta entrega testa o comando com FakeProvider. O mantenedor ainda precisa
executá-lo com seu próprio modelo GGUF local; não há resultados reais de modelo
declarados aqui.
