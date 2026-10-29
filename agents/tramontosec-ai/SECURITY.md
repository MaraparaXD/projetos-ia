# Segurança e fronteiras de confiança

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
