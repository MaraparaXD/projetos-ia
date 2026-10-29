# Instruções de engenharia — TramontoSec AI

- Este diretório contém somente o agente TramontoSec, um dos projetos do monorepositório.
- Leia `README.md`, `docs/metodologia.md` e os testes antes de alterar o núcleo.
- Nunca acessar, varrer ou modificar infraestrutura de terceiros sem autorização verificável.
- Não incluir dados internos, segredos, identificadores de alvos reais, evidências privadas ou repositórios proprietários no Git público.
- A análise de código é somente leitura; scanner só pode importar relatórios previamente sanitizados.
- Ferramentas ativas e remediação automática não estão habilitadas na versão atual.
- Não interpretar resultados de scanner como vulnerabilidades confirmadas sem revisão humana e contexto.
- Ollama local é opcional; modelos e endpoints remotos não são habilitados automaticamente.
- Desenvolver com dados sintéticos, testes, documentação e controle de versões.
