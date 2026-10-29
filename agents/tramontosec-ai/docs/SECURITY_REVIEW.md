# Revisão pré-publicação — 29/10/2026

Escopo: checkout público deste monorepositório e código recuperado do ZIP.
Não incluiu qualquer sistema auditado, infraestrutura de terceiros, relatório
de cliente ou repositório proprietário.

## Verificações executadas

- Leitura dos fontes e testes originais, documentação e diff da migração.
- Inspeção da lista de arquivos versionados/candidatos: somente código,
  documentação, testes, exemplos sintéticos e configuração de CI/design.
- Verificação de ausência de bancos, ambientes, relatórios operacionais,
  credenciais, chaves, arquivos de clientes e identificadores confidenciais.
- Gitleaks **8.30.1**, modo diretório e histórico, com saída redigida: nenhum
  segredo detectado. Relatórios detalhados ficam fora do repositório.
- Zizmor offline com persona pedantic: nenhum achado após adicionar nome de
  job e limite de concorrência. Actions fixadas em SHA e contents:read;
  checkout não persiste credenciais.
- Busca de nomes confidenciais conhecidos, chaves privadas, padrões de tokens
  e endereços RFC1918: nenhum resultado nos arquivos públicos selecionados.
- Testes de importação descartam valores de segredos; nenhum alerta é
  automaticamente aceito. Fontes novas exigem nova decisão humana.
- Política e ferramentas não são alteráveis pelo modelo; comandos arbitrários,
  teste ativo, remediação e provedores externos não estão na allowlist.
- HTTP testa sessão, CSRF, rebinding por Host e origem externa. Browser renderiza
  conteúdo por textContent, sem interpretação de HTML vindo de evidências.
- .gitignore cobre dados locais, modelos/artefatos, builds, logs, caches, env e chaves.

## Riscos residuais e decisão técnica

Não se trata de certificação ou prova de ausência de vulnerabilidades. Parsers
e runtime não são sandbox contra um processo local com privilégios. SQLite
não é cifrado e eventos não são invioláveis. Modelo local adulterado pode mentir
sobre encaminhamento; mantenha cloud desabilitado no servidor ou use o núcleo
determinístico. Revisão humana é declaração do operador, sem autenticação forte.
Use apenas um operador e cópia estável de auditoria; não exponha o dashboard.

Código e dados sintéticos podem ser publicados após os testes e a revisão do
diff. Workspaces, relatórios, capturas de validação, ZIP e arquivos originais
de recuperação permanecem locais e fora do Git. A validação não autoriza
divulgação de qualquer dado real importado posteriormente.
