# Tramonto no TramontoSec AI

As cinco etapas fornecidas para o framework organizam a avaliação. A ferramenta
registra atestações e pendências; não comprova autorização nem eficácia por si só.
Classes VCE, VP, R, I e OBS são convenções do projeto, não categorias oficiais.

| Etapa | Implementação e gate |
|---|---|
| Adequação | Objetivo e escopo exato, atestados pelo auditor |
| Verificação | Auditor confirma autorização e guarda local |
| Preparação | Evidências, SHA-256, baseline Git atual se houver repo; atestação humana |
| Execução | Tarefas resolvidas, hipóteses decididas, baseline ainda válida |
| Finalização | Etapas anteriores completas, sem tarefas ou decisões pendentes |

`stage --name ETAPA --reviewer NOME --reason JUSTIFICATIVA --ack-human` registra
atestação. Nenhum agente chama esse serviço. Identidade e julgamento humano
não são autenticados por assinatura digital.

Novas evidências invalidam Preparação e etapas posteriores. Planos guardam
IDs exatos e rejeitam mudanças silenciosas. Baseline exige HEAD completo e
árvore limpa; commit correto não prova versão implantada. Sem repo no escopo,
relatório declara que baseline de código não foi avaliada.

Exportar relatório não encerra avaliação. A demonstração deixa Execução e
Finalização pendentes. Consenso de especialistas não é evidência independente.
Mapeamentos OWASP/NIST/CIS/CWE/MITRE ATLAS ficam para casos justificados futuros;
não há atribuição normativa automática ou declaração de conformidade.
