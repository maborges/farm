# AgroSaaS: Premium Orange Design System

Este documento define os padrões visuais e de interface (UI/UX) para a identidade **Premium Orange**, garantindo consistência e alta qualidade em toda a plataforma.

Este documento é a referência visual principal do `apps/web`. Alterações de componentes devem seguir estes tokens antes de introduzir valores locais.

## 🎨 Paleta de Cores (Brand Identity)

A cor principal do sistema é o **Premium Orange**, projetado para transmitir modernidade, energia e sofisticação no contexto agrícola.

- **Primary (Premium Orange):** `HSL(15 64% 59%)` / Hex: `#D97757`
- **Primary-Foreground light:** `#2B1B16` (texto escuro para contraste com o laranja)
- **Primary-Foreground dark:** `#2B1B16`
- **Accent:** Tons sutis de laranja para estados hover e backgrounds leves (`bg-primary/5` ou `bg-primary/10`).

### Cores semânticas

- **Sucesso:** verde, usado para confirmação e estados concluídos.
- **Alerta:** âmbar/laranja, usado para atenção e pendências.
- **Erro:** vermelho semântico, reservado para falhas e ações destrutivas.
- **Informação:** azul, usado para orientação e contexto.

As cores semânticas não devem substituir a cor primária em estados que não representem sua semântica.

## 🧱 Componentes Base

Todos os componentes devem seguir rigorosamente as medidas abaixo para manter o equilíbrio visual:

### Inputs (Campos de Entrada)
- **Altura (Desktop):** `h-8` (small standard)
- **Área de toque (mobile):** aproximadamente `48px`, mesmo quando o controle visual for menor
- **Borda:** `rounded-sm` (Bordas quadradas/suaves, não totalmente arredondadas)
- **Estilo Base:** `border-primary/10 bg-muted/10`
- **Foco (Focus):** `border-primary/40 ring-2 ring-primary/5`
- **Sombra:** `shadow-inner` para sensação de profundidade.

### Botões (Actions)
- **Variante Padrão:** `outline`
- **Tamanho Padrão:** `sm` (h-8)
- **Comportamento Tátil:** `active:scale-95` (Micro-animação de clique)
- **Tipografia:** `font-black`, `uppercase`, `tracking-widest` para ações principais.
- **Ícones:** Tamanho padronizado e alinhados com o texto.

### Cards e Containers
- **Borda:** `rounded-sm`
- **Aesthetic:** superfícies sólidas por padrão; glassmorphism somente em navegação, dialogs, sheets, popovers e overlays selecionados
- **Sombra Premium:** Layered shadows para profundidade (`shadow-premium`).

## 🖋️ Tipografia e Hierarquia

- **Sistema:** Inter para conteúdo, dados, formulários e navegação.
- **Branding:** Outfit pode ser usado em títulos institucionais e elementos de marca.
- **Títulos e Headers:** Hierarquia clara, sem exigir simultaneamente itálico, caixa alta e peso máximo.
- **Labels:** Preferencialmente `12px` ou maior; caixa alta e tracking ampliado somente quando não prejudicarem a leitura.
- **Contrastes:** Manter alto contraste entre `muted-foreground` e `foreground` para garantir legibilidade.

## 🌑 Modo Dark / Light

- O sistema deve suportar ambos os modos de forma nativa.
- Em modo Dark, as bordas e fundos devem ser ajustados para manter a transparência e o brilho do **Premium Orange** sem perder a legibilidade.
- O texto sobre superfícies primárias deve sempre usar o token de foreground correspondente ao tema.

## 🚀 Princípios de UX

1. **Micro-interações:** Transições suaves e discretas; escala não deve ser obrigatória em toda ação.
2. **Zero Layout Shift:** Containers com alturas fixas ou skeletons durante o carregamento.
3. **Feedback Visual:** Uso de `toast` para mensagens de sucesso/erro sempre na cor de marca ou semântica.
4. **Glassmorphism:** Aplicar blur de forma seletiva para preservar desempenho.
5. **Acessibilidade:** Estados de foco, teclado, contraste e áreas de toque devem ser preservados em todos os temas.

---
*Atualizado em: 12 de Setembro de 2026 — Fase 0*
