# Metodologia do TramontoSec AI

O protótipo segue as cinco etapas do framework acadêmico **Tramonto**: Adequação, Verificação, Preparação, Execução e Finalização. A organização destas etapas não significa que testes ofensivos tenham sido executados.

| Etapa | Fluxo assistivo disponível | Limitação |
|---|---|---|
| Adequação | Identificação de avaliação e escopo | A equipe deve validar as regras de engajamento |
| Verificação | Confirmação explícita de workspace autorizado | Não valida automaticamente criptografia e permissões |
| Preparação | Git baseline, SHA-256, documentos | Commit não equivale a deploy |
| Execução | Importação de resultados sanitizados e verificação de localização | Não executa scanners nem confirma exploração |
| Finalização | Minutas e revisão humana | Exportação não concede autorização para divulgação |

As classes `VCE`, `VP`, `R`, `I` e `OBS` são convenções do projeto, **não categorias oficiais do Tramonto**.

## Objetivos futuros (não implementados)

- Agente Red Team: reconhecimento e planejamento de testes *autorizados*, com execução ativa bloqueada por padrão.
- Agente Static Analysis: inspeção semântica White Box, controles e contraprovas.
- Agente Blue Team: correlação defensiva, medidas de mitigação e validação posterior.
- Orquestrador: escopo, autorização, políticas, gestão de evidências e aprovação humana.
- AI Security: segurança de modelos, agentes, RAG e aplicações ML/LLM.

A validação científica futura requer casos sintéticos inéditos, revisão independente e métricas publicadas de qualidade de evidências, tempo, falsos positivos e concordância.
