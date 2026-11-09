# Changelog

## 0.5.0 — 09/11/2026 (em desenvolvimento, experimental)

- Agentes Red, Static e Blue com loop local consultivo, propostas tipadas e fallback explícito.
- Piso de severidade do scanner e registro de divergências sem rebaixar regras.
- Recomendações de regra e LLM preservadas separadamente, com origem e aviso na interface e relatório.
- Filtro explícito de texto; aliases rule-N para regras livres; get_alert_summary somente leitura.
- Static anexa equivalências como notas; agrupamentos adicionais exigem várias regras ou componentes.
- Trilha com motivo fixo e model_note opcional, breve e não verificada; why inválido é descartado.
- agent-check em workspace sintético temporário, cinco repetições por perfil e falhas sem simular inferência.
- Benchmark com três cenários por perfil, repetições, motivos de fallback e mediana/máximo de tempo.
- Testes offline de limites, transporte, leitores, CLI e DOM; cobertura mínima da CI em 91,52%.
- Versões, documentação e indicação de desenvolvimento alinhadas; sem licença ou contato inventados.
- Sem validação científica de detecção ou resultado real de modelo declarado.

## 0.4.0 — 04/11/2026 (Red Team, incremento experimental)

- Importação de metadados passivos de infraestrutura com esquema estrito e ativos previamente autorizados.
- Hipóteses sobre firewall, SSH, interfaces administrativas, S3, BuildKit, continuidade e tentativas de login.
- Evidência rastreável, incertezas explícitas e contraprovas; nenhum resultado é considerado exploração confirmada.
- Red Team integrado à allowlist, CLI, SQLite e orquestração existentes; teste sintético de ponta a ponta.
- Metadados de serviços normalizados antes de eventual avaliação por Ollama local; não envia nomes de ativos.
- Não inclui scanning ativo, ações na VPS ou remediação automática.

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
