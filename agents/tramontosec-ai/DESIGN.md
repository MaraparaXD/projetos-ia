---
name: TramontoSec AI
description: Interface operacional monocromática, dinâmica e elegante para auditoria com revisão humana.
colors:
  black: "#000000"
  ink: "#111111"
  muted: "#595959"
  ground: "#fafafa"
  surface: "#ffffff"
  soft: "#f1f1f1"
  line: "#dedede"
  control-line: "#808080"
  nav-active: "#262626"
  nav-text: "#d8d8d8"
  inverse-muted: "#bdbdbd"
  inverse-line: "#414141"
  primary-hover: "#333333"
  selected-row: "#f6f6f6"
  review-line: "#8d8d8d"
  placeholder: "#6d6d6d"
  current-caption: "#d6d6d6"
typography:
  display:
    fontFamily: '"Segoe UI", Helvetica, Arial, sans-serif'
    fontSize: "clamp(2rem, 3.3vw, 3.3rem)"
    fontWeight: 650
    lineHeight: 1.12
    letterSpacing: "-0.035em"
  headline:
    fontFamily: '"Segoe UI", Helvetica, Arial, sans-serif'
    fontSize: "1.35rem"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  title:
    fontFamily: '"Segoe UI", Helvetica, Arial, sans-serif'
    fontSize: "1rem"
    fontWeight: 650
    lineHeight: 1.55
  body:
    fontFamily: '"Segoe UI", Helvetica, Arial, sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: '"Segoe UI", Helvetica, Arial, sans-serif'
    fontSize: "0.84rem"
    fontWeight: 500
    lineHeight: 1.55
  code:
    fontFamily: "Consolas, monospace"
    fontSize: "0.9em"
rounded:
  control: "4px"
  surface: "6px"
  badge: "20px"
  circle: "50%"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  mobile-panel: "18px"
  lg: "20px"
  panel: "22px"
  space: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.black}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-outline:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  button-outline-hover:
    backgroundColor: "{colors.soft}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
    width: "100%"
  navigation-item:
    backgroundColor: "transparent"
    textColor: "{colors.nav-text}"
    rounded: "{rounded.control}"
    padding: "14px"
  navigation-item-active:
    backgroundColor: "{colors.nav-active}"
    textColor: "{colors.surface}"
  badge:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.badge}"
    padding: "4px 9px"
  badge-review:
    backgroundColor: "{colors.surface}"
  badge-accepted:
    backgroundColor: "{colors.black}"
    textColor: "{colors.surface}"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "{spacing.panel}"
  stage-current:
    backgroundColor: "{colors.black}"
    textColor: "{colors.surface}"
    padding: "18px 12px"
---

# Design System: TramontoSec AI

## Overview

**Creative North Star: "Operação monocromática"**

O sistema traduz a direção preto e branco, dinâmica e elegante em uma interface de trabalho sóbria. Tipografia com presença, grandes áreas claras e navegação preta estabelecem hierarquia sem competir com evidências e decisões humanas. O contraste e a densidade organizam a leitura; não há cor de destaque cromática.

A sensação de movimento vem da troca de contexto, da inversão de tons nos estados e da revelação curta do detalhe. Painéis planos, contornos discretos e cantos levemente arredondados mantêm a interface precisa. A apresentação usa recursos locais, fontes do sistema e ícones SVG em linha, sem imagens raster, CDN ou fontes externas.

**Key Characteristics:**
- Monocromia com hierarquia por contraste, peso e espaço.
- Superfícies planas, contornos funcionais e arredondamento contido.
- Estados nomeados em português brasileiro e decisão humana explícita.
- Movimento breve, condicionado à preferência de movimento do usuário.

## Colors

A paleta usa preto, branco e cinzas neutros; os valores normativos estão no frontmatter.

### Primary
- **Preto operacional** (`black`): navegação, ação principal, etapa atual e estado aceito.
- **Carvão de interação** (`primary-hover`): resposta da ação principal ao ponteiro.

### Neutral
- **Tinta** (`ink`): texto principal e foco sobre superfícies claras.
- **Cinza de leitura** (`muted`): explicações, contagens e metadados.
- **Fundo claro** (`ground`): plano geral; **Branco de superfície** (`surface`): painéis e campos.
- **Cinza suave** (`soft`): cabeçalhos de tabela, evidências, avisos e hover secundário.
- **Linha estrutural** (`line`): separadores, painéis e limites não interativos.
- **Contorno de campo** (`control-line`): limites de input, select e textarea, distinguíveis do fundo branco.
- **Carvão ativo** (`nav-active`), **Texto de navegação** (`nav-text`), **Legenda inversa** (`inverse-muted`) e **Linha inversa** (`inverse-line`): hierarquia interna da navegação escura.
- **Seleção discreta** (`selected-row`): hipótese selecionada na tabela.
- **Linha de revisão** (`review-line`): selo em revisão; **Texto de exemplo** (`placeholder`): instrução dentro de campos vazios; **Legenda da etapa atual** (`current-caption`): texto secundário sobre preto.

**The Functional Boundary Rule.** Use `control-line` nos campos e `line` na estrutura. Uma linha estrutural suave não substitui o limite de um controle.

**The Named State Rule.** Identifique estados com texto e forma: aceito usa inversão, em revisão usa contorno e rejeitado usa texto riscado. Preserve a legenda; o tom sozinho não comunica a decisão.

## Typography

**Display Font:** Segoe UI, com Helvetica, Arial e sans-serif.
**Body Font:** a mesma família do sistema.
**Label/Mono Font:** Segoe UI para rótulos; Consolas e monospace para código e identificadores.

**Character:** tipografia direta, familiar e compacta. Títulos usam peso intermediário forte e tracking fechado; o corpo permanece regular, com entrelinha confortável. Nenhuma fonte é baixada.

### Hierarchy
- **Display:** título principal com escala fluida; no mobile passa a (2.1rem).
- **Headline:** títulos de seção; no mobile passam a (1.23rem).
- **Title:** subtítulos de evidência, modo e grupos internos.
- **Body:** base do documento; parágrafos limitados a (75ch), introdução do cabeçalho a (65ch). Textos auxiliares normalmente usam (0.9rem).
- **Label:** rótulos de formulário, em caixa natural. Botões usam peso (600).
- **Code:** código a (0.9em); digests a (0.76rem), com quebra para identificadores longos.

Contagens e datas usam algarismos tabulares. Os tamanhos exatos dos papéis estão no frontmatter; a implementação usa uma escala ajustada por função, sem razão modular única.

## Layout

A estrutura de desktop tem navegação fixa à esquerda (230px) e conteúdo com margem correspondente, largura máxima (1800px) e padding (26px 30px 18px). A composição operacional usa coluna principal e apoio na razão (2.1fr / 1fr), com mínimo (260px) na coluna de apoio e intervalo (24px). Painéis usam o token `panel`; formulários internos usam intervalos (16px).

A faixa de etapas distribui cinco itens iguais. O formulário de revisão tem introdução e campos em duas colunas; auditor e decisão dividem uma linha. Tabelas mantêm rolagem local quando necessário e quebram títulos longos; identificadores não alargam a página.

- A partir de (1500px), o conteúdo recebe padding (32px 42px), etapas (22px 18px) e intervalo principal (28px).
- Até (1200px), a navegação passa a (200px), conteúdo a padding (22px), área principal a uma coluna e especialistas a duas colunas. A revisão também vira uma coluna.
- Até (680px), a navegação entra no fluxo como cabeçalho preto com três abas; o conteúdo usa padding (20px 16px). Etapas, especialistas, formulário e histórico ficam em uma coluna. Painéis usam `mobile-panel`; a coluna Origem da tabela é ocultada, mantendo hipótese, estado e ação. O rodapé empilha seu conteúdo.

## Elevation & Depth

Não há sombras nem blur. Profundidade é expressa pela separação entre fundo, branco, cinza suave, contornos e inversão preta. A seleção de tabela é tonal; abrir evidências mantém o contexto na mesma página.

**The Flat Surface Rule.** Preserve a separação por tom e contorno ao estender painéis. Estados de interação não dependem de elevação ou brilho.

## Shapes

Painéis e faixa de etapas usam cantos levemente arredondados pelo token `surface`; botões, campos e blocos de evidência usam `control`. Selos usam `badge`; os números das etapas usam círculos. Bordas são finas (1px). No mobile, as abas arredondam somente os cantos superiores. Ícones são SVG de traço, normalmente (21px), espessura (1.7), pontas e junções arredondadas.

## Components

### Buttons

Ações compactas, legíveis e com contraste firme. A ação principal usa preto com texto branco, contorno preto, padding definido no frontmatter e altura mínima (42px). O hover usa `primary-hover`. A ação de exportar usa branco e contorno preto; hover usa `soft`. A ação discreta usa fundo transparente, sem borda e altura mínima (36px). Botões desabilitados usam opacidade (0.5) e cursor padrão. Ações da tabela são sublinhadas, sem borda, com altura mínima (38px).

O foco visível é um contorno de tinta (2px) afastado (4px); na navegação escura, o contorno é branco. O link de salto torna-se visível ao receber foco. Não remova essas indicações ao adaptar componentes.

### Chips

Selos de estado são compactos e textuais. O padrão usa fundo suave; em revisão usa branco e contorno `review-line`; aceito usa preto e branco; rejeitado risca o texto. São indicadores, sem hover de ação. No mobile, tamanho de texto e padding diminuem para (0.67rem) e (3px 7px).

### Cards / Containers

Painéis brancos usam linha estrutural, cantos `surface` e padding `panel`, reduzido a `mobile-panel` no mobile. Avisos e blocos de evidência usam fundo suave. Mensagens de resultado aparecem somente com conteúdo e usam contorno de tinta; erros diferenciam o contorno com traço interrompido e uma explicação textual.

### Inputs / Fields

Campos brancos usam contorno `control-line`, cantos `control`, largura total e altura mínima (42px). Textarea tem altura mínima (90px), margem superior (6px) e redimensionamento vertical. Rótulos ficam acima dos campos; placeholder não substitui rótulo. O checkbox usa acento preto e dimensões (16px). O foco segue o padrão global; a interface usa validação nativa e mensagens textuais, sem inventar cores de erro. Decisões bloqueadas mantêm os campos desabilitados e uma explicação visível.

### Navigation

A navegação preta usa texto claro, SVG em linha, espaço entre itens (8px) e altura mínima (50px). Hover e item ativo compartilham fundo `nav-active` e texto branco; o item atual mantém `aria-current="page"`. No mobile, as abas ficam lado a lado e usam altura mínima (44px). As vistas preservam nomes em português brasileiro.

### Etapas e evidências

A faixa numerada torna o progresso legível sem depender de cor: etapa concluída tem círculo preto; etapa atual inverte todo o item e mantém `aria-current="step"`; cada etapa tem legenda de estado. No mobile, os cinco itens formam uma lista vertical.

Selecionar uma hipótese marca a linha, expõe o detalhe e move o foco para seu título. A ação mantém `aria-expanded` e `aria-controls`. Somente com movimento permitido, o detalhe revela seu recorte em (200ms), botões transitam o fundo em (150ms) e o deslocamento é suave. Com redução de movimento, essas animações e transições não são ativadas e a rolagem do detalhe é imediata.

## Do's and Don'ts

### Do:
- **Do** preservar a paleta monocromática e a hierarquia por contraste, tipografia e espaço.
- **Do** usar `control-line` nos campos e reservar `line` para estrutura.
- **Do** manter foco visível, rótulos persistentes e estados nomeados em português brasileiro.
- **Do** adaptar navegação, etapas e formulários nos breakpoints existentes.
- **Do** condicionar movimento à preferência do usuário e manter a leitura de evidências no contexto.

### Don't:
- **Don't** acrescentar acentos cromáticos para comunicar estados já definidos pela monocromia.
- **Don't** trocar contornos funcionais por divisores suaves ou remover o contorno de foco.
- **Don't** introduzir sombras, blur, imagens raster, fontes externas ou dependências de CDN nesta interface.
- **Don't** substituir rótulos de decisão por cor, ícone ou animação isolados.
