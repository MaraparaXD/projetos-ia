# Catálogo de agentes

Os projetos de IA ficam em subpastas independentes. Cada agente deve ter documentação, testes, exemplos sintéticos e limites de segurança explícitos.

## TramontoSec AI

Agente assistivo de auditoria baseado no Tramonto. O código está publicado em `agents/tramontosec-ai/`; os limites de segurança e as validações em andamento estão documentados nessa pasta.

## GraphIntel Agent

Análise de relações e impacto reverso a partir do `graph.json` gerado
pelo Graphify separadamente, sem executar código ou scanners.
[Documentação](graphintel-agent/README.md).

## Design Agent

Avaliação de especificações de tela com verificações de contraste,
acessibilidade e usabilidade declaradas, com parecer local opcional.
[Documentação](design-agent/README.md).
