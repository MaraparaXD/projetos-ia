# Validação da recuperação

Data: 28/10/2026. Origem: `projetos-ia-tramontosec-recuperado.zip`, 23 arquivos,
78.659 bytes descompactados. Manifesto SHA-256 e ZIP original preservados fora
do repositório público, em `recovered-original/` e na pasta de trabalho.

Inspeção anterior à extração: rejeição de caminhos absolutos, drive Windows,
traversal, links simbólicos, entradas duplicadas, arquivos criptografados e
limites de tamanho. Todas as entradas permaneceram no destino de recuperação.

Base identificada pela documentação como **0.2.1**. Inconsistência encontrada:
`tramontosec/__init__.py` ainda declarava `0.2.0`. Não há pyproject ou requisitos
no ZIP. Núcleo e testes usam a biblioteca padrão. `pypdf` é opcional somente para
catalogar PDFs; não foi necessário instalá-lo na validação.

## Execução original, antes de desenvolvimento

- Windows, Python 3.13.14, ambiente virtual isolado.
- `python -m unittest discover -s tests -v`: **28 testes, OK**, 4,490 segundos.
- Testes SQLite confirmaram commit, rollback, fechamento após erro/interrupt,
  foreign keys, cursor e renomeação do banco no Windows sem handles retidos.
- Git desativa hooks/fsmonitor e não executa código do alvo.
- Scanners importam metadados e descartam mensagens, snippets e valores de segredos.
- Demonstração original é fictícia, com baseline de zeros explicitamente inválido.
- Sem agentes especialistas nem dashboard na base; benchmark mede somente
  localização e commit, sem provar eficácia na detecção de vulnerabilidades.
- Ollama é opcional e exige consentimento; não foi usado no teste original.

O primeiro commit da recuperação conserva fontes e 28 testes sem alterações.
Mudanças posteriores são incrementais. Nenhum sistema auditado foi acessado.
