# Segurança e fronteiras de confiança — 0.5.0 em desenvolvimento

Ferramenta local assistida para escopo autorizado. Sem testes ativos,
scanners executados, comando de modelo, remediação ou provedor externo.

## Controles

- Allowlist por perfil e escopo persistido fora do controle do modelo.
- SQLite próprio por projeto; IDs restritos e bloqueio de traversal/links comuns.
- Reconhecimento com ativos exatos e vocabulário fechado; não contata alvos.
- JSON limitado, descarte de snippets/mensagens/valores de segredos; scanner não confirma vulnerabilidade.
- AST não executa alvo. Git verifica baseline antes/depois, sem hooks/fsmonitor.
- Evidência é entrada não confiável. Schema, IDs e ferramentas de modelo são
  validados. Defesa contra prompt injection está na restrição de capacidades,
  não apenas no prompt. Sugestões não viram decisões humanas.
- Ollama loopback opt-in, GGUF local, sem cloud/proxies/redirects.
- Dashboard: token efêmero no fragmento de URL, removido ao iniciar; cookie
  HttpOnly/SameSite=Strict, CSRF, Host/Origin exatos, CSP, textContent e sem CDN.
- Conexões SQLite fechadas em finally; lock de runtime do sistema operacional.

## Limites operacionais

Guarde workspaces fora do Git, com criptografia do volume, ACLs e retenção.
SQLite não é cifrado pelo programa. synthetic e ack-redacted-input são
declarações do operador, não prova de anonimização. IDs/caminhos também podem
conter informação privada: revise antes de importar e publicar.

Configure OLLAMA_NO_CLOUD=1 no servidor local e reinicie-o. Um servidor local
adulterado pode mentir sobre modelo/encaminhamento e não é autenticado pelo
adaptador. O modo determinístico evita essa dependência.

Dashboard para um operador local, sem TLS, RBAC ou identidade assinada; não
expor à rede. Um processo com permissão de alterar bancos/código não é isolado
pelo runtime. Eventos não são ledger inviolável. Use cópia estável do alvo:
há janela residual de alteração concorrente do filesystem e não há sandbox
de parser de SO. Não há garantia absoluta contra prompt injection.

Revisão desta entrega: [docs/SECURITY_REVIEW.md](docs/SECURITY_REVIEW.md).
Comunicar problemas ao mantenedor em canal privado previamente acordado;
não há endereço de divulgação de vulnerabilidades configurado.

## Ameaças específicas do loop LLM experimental

Entradas com prompt injection podem chegar por campos de evidência sanitizada.
O motor trata esses campos como **dados**, não como instruções; somente
serviços enumerados, aliases de ativos, IDs, regras e severidades limitadas
podem compor os resultados das ferramentas consultivas. Não encaminhar
nomes reais, código-fonte, credenciais, caminhos ou logs.

O modelo responde JSON não confiável. `agent_loop.py` limita passos e tamanho,
valida `action`, nome de ferramenta e argumentos; `policy.py` restringe
cada perfil. `agent_validation.py` valida referências existentes, schema
estrito, quantidade de propostas e severidade. Não confundir saída
`local_llm_agent` com decisão humana ou prova de exploração.

Falhas, injeções, IDs fabricados, ferramenta fora da allowlist, contexto
excessivo ou resposta inválida devem resultar em fallback determinístico
registrado; nunca em elevação de privilégio. O gateway Ollama é somente
loopback com GGUF local verificado, proxy desativado e redirects proibidos.
As decisões humanas, CSRF, CSP e controles de Host/Origin permanecem fora
do domínio de confiança do modelo.

Uma implementação real em máquina com Ollama exige revisão separada de
modelo, limites de tokens e política de metadados permitidos; ainda não
há avaliação científica em ambiente real nem direito de acesso a alvos.


## Controles incrementais 0.5.0

`rule_id` fora do regex `^[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}$` usa alias
`rule-N` com mapa inverso somente interno e `rule_alias_used` no contexto.
A sintaxe permitida não demonstra anonimização; um ID válido ainda pode revelar
informação privada. Revise entradas antes de qualquer inferência local.

`get_alert_summary` está restrito ao Static com efeito `read_metadata`. Conta
alertas, severidades, arquivos e componentes sem expor caminhos, mensagens,
trechos ou nomes. A contagem ajuda a triagem, sem provar alcance ou independência.

A severidade do scanner é piso para propostas Static. Hipóteses de regra não
são rebaixadas pelo modelo; discordâncias ficam explícitas. Equivalências são
notas, não novos achados. Blue mantém recomendações de regra e de LLM lado a
lado com `origin` e aviso de sugestão não verificada; nenhuma é aplicada e
nenhuma constitui confirmação independente.

O filtro explícito de `agent_validation.py` rejeita marcação, URLs, comandos,
instruções de aprovação, controles Unicode e excesso de linhas. Pode rejeitar
prosa legítima e não reconhece toda linguagem maliciosa. O baseline continua
disponível por fallback. A defesa decisiva segue nas capacidades restritas,
orçamentos e revisão humana.

O `why` opcional é público e limitado a 160 caracteres, filtrado pelo mesmo
validador. A trilha mantém motivo fixo e `model_note`, exibido como nota do
modelo não verificada. Valor inválido é descartado isoladamente. Dados são
escapados no Markdown e exibidos com `textContent`, inclusive se um banco
antigo contiver texto inesperado. Não é coleta de cadeia privada de raciocínio.

`agent-check` usa demonstração sintética e workspace temporário, com opt-in e
preflight GGUF inalterado. Indisponibilidade falha de forma explícita, sem
simulação. `fallback_reason=Classe` evita persistir detalhes da resposta em
diagnósticos. O ensaio e o benchmark não validam detecção de vulnerabilidades.
O limite de resposta do adaptador legado também rejeita bytes além de 32 KB.

TODO: definir contato privado de segurança. TODO: escolher licença.
Essas decisões pertencem ao mantenedor; nenhum endereço ou licença foi escolhido.
