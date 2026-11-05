# Projetos IA

Monorepositório de projetos, ferramentas e agentes de Inteligência Artificial.

Cada agente tem sua pasta em `agents/`, com código, testes, documentação e dependências próprias.

## Agentes

| Agente | Finalidade | Estado |
|---|---|---|
| [TramontoSec AI](agents/tramontosec-ai/README.md) | Auditoria passiva pelo Tramonto: Red Team, análise estática e Blue Team | Especialistas LLM experimentais e revisão humana |
| [GraphIntel Agent](agents/graphintel-agent/README.md) | Grafo de conhecimento e impacto de alterações | Protótipo v0.1 |
| [Design Agent](agents/design-agent/README.md) | Revisão de telas, acessibilidade e UI/UX | Protótipo v0.1 |

O catálogo aceita agentes de qualquer domínio. Projetos futuros não precisam ser ferramentas de segurança.

## Organização

```text
projetos-ia/
├── agents/
│   ├── tramontosec-ai/
│   ├── graphintel-agent/
│   └── design-agent/
├── docs/
├── .gitignore
└── README.md
```

**Privacidade:** não publicar código proprietário, evidências de auditoria, dados de clientes, logs, senhas ou chaves. O repositório é público.

Código de cada agente deve ser testado, documentado e desenvolvido de forma independente.

Consulte [a organização do monorepositório](docs/MONOREPO.md) e as instruções individuais dos agentes.

## Modelos locais e privacidade

Os três projetos podem funcionar **sem modelos**. Quando há suporte à IA,
o uso de modelos locais GGUF via Ollama é opcional, com consentimento.
Modelos mais flexíveis (como Dolphin3) são candidatos, mas nenhuma resposta
do modelo recebe poderes de executar comandos, alterar sistemas ou
aceitar automaticamente achados.

`ollama pull dolphin3` é opcional e depende do hardware. Não há
download nem execução automática de modelos. O Graphify e o TramontoSec
não estão integrados automaticamente: eventual interoperabilidade exigirá
sanitização e revisão de evidências.
