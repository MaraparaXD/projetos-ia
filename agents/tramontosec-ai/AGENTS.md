# Instruções de engenharia e perfis

Somente TramontoSec neste diretório. Leia README, ARCHITECTURE, TRAMONTO,
SECURITY e testes antes de alterar o núcleo. Preserve os módulos e os testes
recuperados; mudanças incrementais. Interface em português brasileiro.

- Red: reconhecimento passivo importado, hipóteses e contraprovas; analyze_recon.
- Static: alertas sanitizados, rastreabilidade e correlação; analyze_static.
- Blue: memória das hipóteses, controles, mitigação, resposta a incidentes e
  procedimento de validação; review_controls. Não aplica correções.

TaskMessage/AgentResult são contratos versionados. Ordem Red → Static → Blue,
sequencial. Regras determinísticas não são inferência. Modelo só sugere.
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
