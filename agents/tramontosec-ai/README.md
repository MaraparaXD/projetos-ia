# TramontoSec AI — v0.2.1 (protótipo recuperado)

Ferramenta **local, assistiva e em Python** para organização de auditorias de segurança pelo framework acadêmico Tramonto. É um projeto no monorepositório `projetos-ia`.

> **Estado atual:** CLI e motor de evidências; **não** é ainda um sistema multiagente autônomo. Não faz pentest ativo, não dispara scanners automaticamente e não corrige infraestrutura.

## Funcionalidades existentes

- Catálogo de documentos e preservação de SHA-256 / períodos de avaliações.
- Verificação referencial de caminhos, linhas e baselines Git em modo somente leitura.
- Importação de metadados *sanitizados* de Semgrep, Trivy, Gitleaks e Zizmor; triagem humana.
- Correlação conservadora de alertas com evidências por localização.
- Registro de decisões humanas e geração de minuta Markdown.
- Inventário preliminar de dependências relacionadas a IA (indícios, não diagnósticos).
- Sugestões opcionais via **Ollama local**, apenas com metadados curtos, sem aceitar achados.

## Instalação / execução (Python 3.11+)

```bash
cd agents/tramontosec-ai
python -m unittest discover -s tests -v
python -m tramontosec --help
```

Crie o workspace **fora de pastas sincronizadas**, em volume criptografado e com permissões adequadas, confirmados pelo auditor:

```powershell
$ws = Join-Path $env:LOCALAPPDATA 'TramontoSec-Auditorias'
python -m tramontosec --workspace "$ws" init --ack-authorized-secure-storage
python -m tramontosec --workspace "$ws" seed --file .\examples\demo_findings.json
python -m tramontosec --workspace "$ws" list
```

Os dados demonstrativos são totalmente **fictícios**, não evidências de um sistema real.

## Segurança e limites

A opção de confirmação **não** verifica por si mesma BitLocker/EFS ou ACLs. Não inclua no Git público workspaces, bancos de auditoria, relatórios reais, logs, segredos ou conteúdos privados. O módulo de IA local precisa de consentimento explícito e não pode aprovar resultados.

Use `docs/metodologia.md` para o Tramonto e `docs/ROADMAP.md` para o desenvolvimento dos futuros agentes Red Team, Static Analysis e Blue Team.

**Pesquisa científica:** apenas testes funcionais e fixtures sintéticas até o momento; não há métricas de eficácia de detecção de vulnerabilidades em produção.
