# Projetos IA

> **EM DESENVOLVIMENTO.** Projetos experimentais; sem versão estável ou eficácia de detecção demonstrada.

Monorepositório de projetos, ferramentas e agentes de Inteligência Artificial.

Cada agente tem sua pasta em `agents/`, com código, testes, documentação e dependências próprias.

## Agentes

| Agente | Finalidade | Estado |
|---|---|---|
| [TramontoSec AI](agents/tramontosec-ai/README.md) | Auditoria passiva pelo Tramonto: Red Team, análise estática e Blue Team | **v0.5.0 — em desenvolvimento:** agentes LLM locais experimentais, fallback e revisão humana |

O catálogo aceita agentes de qualquer domínio. Projetos futuros não precisam ser ferramentas de segurança.

## Organização

```text
projetos-ia/
├── agents/
│   ├── tramontosec-ai/
│   └── outros-agentes-no-futuro/
├── docs/
├── .gitignore
└── README.md
```

**Privacidade:** não publicar código proprietário, evidências de auditoria, dados de clientes, logs, senhas ou chaves. O repositório é público.

Código de cada agente deve ser testado, documentado e desenvolvido de forma independente.

Consulte [a organização do monorepositório](docs/MONOREPO.md) e as instruções individuais dos agentes.

Validação atual do TramontoSec: [execuções e limites](agents/tramontosec-ai/docs/VALIDATION.md). Licença e contato de segurança continuam pendentes de definição pelo mantenedor.
