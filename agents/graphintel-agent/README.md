# GraphIntel Agent — protótipo v0.1

Agente independente de inteligência arquitetural. Consome **somente** o `graph.json` do Graphify, em formato node-link com `nodes` e `links` (ou `edges`), e calcula dependências e **candidatos a impacto reverso**.

**Não é o Graphify oficial e não modifica, instala ou executa o Graphify.** O projeto Graphify-Labs/graphify tem sua própria licença (Apache-2.0); nenhum código dele foi copiado. A licença do nosso repositório continua pendente de escolha pelo mantenedor.

## Testar (Python 3.11+, biblioteca padrão)

```bash
cd agents/graphintel-agent
python -m unittest discover -s tests -v
python -m graphintel --graph examples/graph.synthetic.json --focus storage
```

No Windows CMD, substitua `python` pelo caminho do Python instalado se necessário. O protótipo não requer `pip install`.

## Usar com Graphify

Gere um `graph.json` **localmente**, pela CLI oficial do Graphify, em um repositório que você tenha autorização para analisar. Consulte [a documentação oficial](https://github.com/Graphify-Labs/graphify) para instalar e gerar `graphify-out/graph.json` com `--code-only`; não ative processamento remoto de documentos nem Graphify Cloud se os dados forem privados.

```bash
python -m graphintel --graph /caminho/para/graphify-out/graph.json --focus ID_EXATO
```

O ID pode ser identificado no próprio JSON. **Os caminhos, rótulos e IDs aparecem somente no relatório local.** O parecer LLM recebe contagens e aliases, não nomes, caminhos ou código.

## Modelo local opcional, com liberdade de alinhamento

```bash
ollama pull dolphin3
python -m graphintel --graph examples/graph.synthetic.json --focus storage --model dolphin3 --ack-local-model
```

Aceita outros modelos GGUF locais verificáveis no Ollama. Dolphin3 é um **candidato**, não garantia de disponibilidade de RAM/VRAM ou precisão. O agente não impõe filtros temáticos de estilo ao modelo, mas restringe **ferramentas, dados, rede e saída** para segurança. O cliente HTTP usa apenas 127.0.0.1, sem proxy e sem redirecionamentos. Falhas de modelo produzem `deterministic_fallback`.

## Limitações

- Relações `INFERRED` exigem contraprova, `EXTRACTED` não garante efeito em runtime.
- Direção de impacto é convencional para relações `calls`, `imports`, `depends_on` e similares. Confirme a semântica de seu grafo.
- Não há navegação no Git, leitura de código, execução de comandos ou integração direta com TramontoSec.
- O modelo sugere **somente observações gerais**; nunca reclassifica impacto nem confirma vulnerabilidades.
- O JSON deve ter no máximo 8 MB, 10 mil nós e 35 mil relações.
