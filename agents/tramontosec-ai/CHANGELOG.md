# Changelog

## 0.3.0 — 29/10/2026

- Três especialistas, mensagens estruturadas e runtime sequencial com memória.
- Políticas independentes de LLM, isolamento SQLite e gates Tramonto humanos.
- CLI ampliada, importadores, baseline Git, AST local e cancelamento de tarefas.
- Ollama local com JSON validado, bloqueio cloud e fallback explícito.
- Demonstração offline, dashboard complementar e documentação acadêmica.
- Corrige versão interna divergente; preserva os 28 testes originais.

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
