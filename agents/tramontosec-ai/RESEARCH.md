# Proposta de pesquisa

Pesquisa em Sistemas de Informação na UFOPA: arquitetura Red Team-first com
análise estática especializada e apoio Blue Team sob o Tramonto.
Este documento não apresenta resultados experimentais de eficácia.

## Problema e objetivos

Como especialização Red/Static/Blue com evidências rastreáveis e revisão humana
afeta qualidade, tempo e justificabilidade de auditorias assistidas, comparada
a agente generalista e auditoria manual? Definir contratos e fronteiras de
confiança; medir hipóteses, contraprovas e interferência entre especialistas;
avaliar resistência a entradas maliciosas com protocolo reproduzível.

## Arquitetura e capacidades

Orquestrador sequencial, política independente do modelo, memória por projeto,
cinco etapas e decisões humanas. Implementado: quatro importadores de scanner,
reconhecimento por metadados, AST simples, baseline, correlação conservadora,
contraprovas, recomendações, CLI, relatório, dashboard e Ollama opcional.
Planejado: análise semântica ampla, avaliações reais de modelos, colaboração
distribuída, comparação controlada e referências normativas contextualizadas.
As descrições dos especialistas são mais amplas que as regras atuais; avaliar
essa diferença explicitamente. Nenhuma exploração ou remediação implementada.

## Experimento futuro e métricas

Comparar auditor manual, agente generalista com mesmas ferramentas e três
especialistas; incluir ablação sem LLM e sem memória. Equalizar modelo,
hardware, escopo, tempo, ferramentas e orçamento de tokens. Usar casos inéditos,
ordem aleatória, revisão cega independente, versões e prompts registrados.
Definir consentimento e avaliação ética aplicável sem publicar dados privados.

Medir precisão/recall por hipótese com ground truth, falsos positivos, cobertura
de controles, referências inventadas, tempo humano/total, custo/tokens,
duplicação, abstinência, concordância entre avaliadores, violações de política
e sucesso de prompt injection. Calcular variabilidade e intervalos de confiança.

## Limitações experimentais

Testes sintéticos funcionais não medem descoberta de vulnerabilidades.
Benchmark recuperado mede somente localização/commit. Não há evidência de
superioridade científica ou conformidade. Modelo local não disponível nesta
entrega; mocks validam protocolo, não inferência real. Dataset, tamanho amostral,
protocolo e revisores independentes ainda precisam ser definidos.
