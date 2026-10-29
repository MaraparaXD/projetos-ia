# Changelog

## 0.2.1 — recuperação e publicação sanitizada
- Recupera a base de código da versão 0.2 como um projeto dentro do monorepositório.
- Corrige fechamento de conexões SQLite para compatibilidade com Windows.
- Adiciona testes de regressão de ciclo de vida SQLite.
- Exclui relatórios, exemplos de achados e identificadores de projetos reais.
- Documenta arquitetura de agentes Red Team / Static Analysis / Blue Team como **plano**, não implementação existente.

## 0.2 — protótipo original
- Verificação de baseline Git e referências de arquivo/linha.
- Importação de metadados sanitizados de Semgrep, Trivy, Gitleaks e Zizmor.
- Catálogo de relatórios, correlação heurística, revisão humana e LLM local opcional.
