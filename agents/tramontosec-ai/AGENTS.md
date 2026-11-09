# Instruções de engenharia e perfis

Somente TramontoSec neste diretório. Leia README, ARCHITECTURE, TRAMONTO,
SECURITY e testes antes de alterar o núcleo. Preserve os módulos e os testes
recuperados; mudanças incrementais. Interface em português brasileiro.

- Red: reconhecimento passivo e metadados de infraestrutura previamente coletados; analyze_recon e analyze_infra. Nenhum scan ativo.
- Static: alertas sanitizados, rastreabilidade e correlação; analyze_static.
- Blue: memória das hipóteses, controles, mitigação, resposta a incidentes e
  procedimento de validação; review_controls. Não aplica correções.

TaskMessage/AgentResult são contratos versionados. Ordem Red → Static → Blue,
sequencial. Sem modelo as regras são determinísticas. Com Ollama GGUF local, o loop limitado pode propor hipóteses e recomendações validadas, sempre candidatas; jamais decide.
Não conceder a agentes/modelos acesso a decisão humana, escopo ou política.

Não acessar, varrer ou modificar infraestrutura de terceiros. Não executar
scanners, código auditado, comandos de modelo ou remediação. Não publicar
dados privados, segredos, evidências, bancos ou código proprietário.
Não enviar dados para provedores externos. Ollama local exige consentimento
e verificação de modelo GGUF local; sem cloud/proxy/redirects.
Scanner, arquivo/linha ou consenso não confirmam vulnerabilidade.
Conservar etapas Tramonto e pendências, sem concluir automaticamente auditoria.

Validar com `python -m unittest discover -s tests -v`, somente dados sintéticos.
Revisar diff e arquivos versionados antes de publicar. Runtime stdlib;
dependências extras exigem justificativa. CLI independe do navegador.


## Contratos 0.5.0 em desenvolvimento

- Manter `get_alert_summary` somente no Static/READ_TOOLS, com `read_metadata`:
  contagens por regra, severidades e quantidades de arquivos/componentes sem nomes.
- Encaminhar regras livres apenas por `RuleAliases`/`rule-N` e indicar
  `rule_alias_used`; nunca enviar o mapa inverso ou campos de caminho ao provider.
- Preservar o piso de severidade do scanner nas propostas Static, tratando
  `Indeterminada` à parte. Regras existentes conservam a severidade; divergências
  e equivalências são notas no `uncertainty`, sem confirmação automática.
- Preservar ambas as recomendações `origin="rule"` e `origin="llm"`, com aviso
  de sugestão de modelo não verificada. Rejeitadas não recebem novas recomendações.
  `applied` e `independent_confirmation` continuam False.
- Aplicar o filtro explícito de texto a propostas e `why`. A nota breve validada
  aparece como `model_note` não verificado; valor inválido vira None, sem perder
  a ferramenta. Interface usa `textContent`; não persistir prompt ou resposta bruta.
- Validar `agent-check` offline com FakeProvider e workspace temporário.
  Resultado com modelo real só pode ser declarado após execução real do mantenedor.
- O orçamento atual permanece em seis turnos por especialista; a API aceita de
  1 a 12. Alterar o padrão depende da avaliação operacional do mantenedor.
- Licença e contato de segurança são TODOs do mantenedor; não inventá-los.
