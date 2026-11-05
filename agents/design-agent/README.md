# Design Agent — protótipo v0.1

Agente independente que revisa **especificações estruturadas de telas** e sugere melhorias de UI/UX com regras explicáveis. Inspirado nas prioridades gerais de produtos digitais bem desenhados (como as apresentadas em [Hey Damir](https://heydamir.design/)), **sem copiar layout, código, marcas ou ativos** desse site.

Não é um navegador, criador automático de páginas, leitor de Figma ou auditor WCAG completo. Tudo o que verifica depende das propriedades fornecidas no JSON.

## Executar (Python 3.11+, somente biblioteca padrão)

```bash
cd agents/design-agent
python -m unittest discover -s tests -v
python -m designagent --input examples/screen.synthetic.json
```

## Modelo local opcional

```bash
ollama pull dolphin3
python -m designagent --input examples/screen.synthetic.json --model dolphin3 --ack-local-model
```

Você pode usar outro GGUF local. O modelo é **mais livre para propor soluções visuais**, mas não ganha acesso a navegador, arquivos privados, rede externa, alterações CSS nem revisão humana automática. O Ollama é acessado somente por 127.0.0.1, sem proxy ou redirecionamentos. Se falhar, a análise determinística continua.

## Formato de entrada

`schema: designagent.screen.v1`, `screen`: `name`, `platform` (`web`/`mobile`), `viewport` (width/height), `components` (até 200), cada um com `id`, `role` e propriedades opcionais:

- `foreground`, `background`: cores sólidas `#RRGGBB`;
- `large_text`: enquadramento declarado do texto grande;
- `width`, `height`: dimensões declaradas em px;
- `accessible_name`, `label`, `alt`, `responsive`, `feedback`: booleanos observados por quem preenche a ficha.

## O que mede

Contraste de texto com fórmula WCAG: meta 4,5:1 para texto normal e 3:1 para texto grande. Metas heurísticas de toque mobile de 44x44px; declaração explícita de rótulo, nome acessível, descrição alternativa, responsividade e feedback.

Ausência de campo opcional significa **não verificado**, não falha automática. Nenhum resultado é declaração de conformidade WCAG. Os findings são `candidate` e exigem testes visuais/funcionais feitos por humanos.

O modelo recebe apenas papéis, regras, severidades, IDs derivados e contagens. Não recebe nome da tela, textos, CSS, caminhos, capturas ou valores de cores. Só pode sugerir texto associado a **IDs existentes**, sem alterar nota, severidade ou estado dos achados.

## Próxima evolução

- Importador opcional de design tokens e resultados de axe/Lighthouse previamente exportados.
- Avaliação com capturas de tela autorizadas (requer motor visual, não presente).
- Geração de proposta de componentes com aceite humano, jamais deploy automático.
- Benchmark de acessibilidade e usabilidade com revisores independentes.
