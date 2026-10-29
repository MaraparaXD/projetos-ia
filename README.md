# Projetos IA

Monorepositório de projetos, ferramentas e agentes de Inteligência Artificial.

Cada agente tem sua pasta em `agents/`, com código, testes, documentação e dependências próprias.

## Agentes

| Agente | Finalidade | Estado |
|---|---|---|
| [TramontoSec AI](agents/tramontosec-ai/README.md) | Auditoria passiva pelo Tramonto: Red Team, análise estática e Blue Team | v0.3.0: runtime sequencial, CLI, dashboard local e LLM opcional |

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
