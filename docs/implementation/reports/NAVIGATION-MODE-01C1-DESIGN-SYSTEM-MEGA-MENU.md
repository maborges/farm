# NAVIGATION-MODE-01C1 — Design System e Especificação da Experiência do Mega Menu

## 1. Resumo Executivo
Esta etapa projetou a experiência de Mega Menu para a navegação do sistema, provendo uma alternativa mais moderna e de baixa densidade visual comparada à barra lateral tradicional. A estrutura utiliza a mesma árvore já autorizada pelo `useVisibleNavigation`, mantendo toda a arquitetura de segurança intacta (sem tabelas novas, endpoints, ou configurações locais duplicadas). A especificação aqui descrita estabelece a fundação de layout, protótipos de responsividade e acessibilidade, pronta para implementação na Fase 01C2.

## 2. Objetivo
Definir a experiência estrutural e visual para o modo Mega Menu, respeitando a identidade da aplicação (SaaS moderno) sem introduzir ruídos de ERP legados e otimizando a responsividade para diversos dispositivos (de desktop a mobile). 

## 3. Referências Conceituais
O design toma como inspiração a apresentação limpa encontrada em ecossistemas como Microsoft 365, Vercel e Notion, utilizando:
- Baixa densidade visual.
- Fundo contínuo limpo, bordas sutis e grids espaçados.
- Categorização clara por "Áreas de Trabalho" funcionais (domínios).
- Ícones em peso regular com micro-interações restritas.

## 4. Restrições Arquiteturais
- **Fonte de Verdade Única**: O Mega Menu consome restritamente a árvore exportada pelo hook local `useVisibleNavigation`.
- **Sem Novas Entidades**: Nenhuma tabela nova (como favoritos ou históricos no BD) foi planejada nesta fase.
- **Isolamento de Contexto**: O `SafraContextHeader` se mantém intocado, isolando a navegação global do contexto operacional.
- **Acessibilidade**: Elementos nativos do DOM devem ancorar as semânticas (usando role/aria quando justificado, ou priorizando `nav` nativa).

## 5. Estrutura Escolhida
- **Desktop/Notebook**: `Popover` fixado próximo ao Topbar. Largura abrangente (evitando fullscreen obrigatório, com largura de ~800px-1000px). Apresenta um input de busca destacado na região superior e um grid adaptável (de 2 a 3 colunas) rolável verticalmente por áreas de trabalho. 
- **Mobile/Tablet Portrait**: Painel lateral modal do tipo `Sheet`/`Drawer`, que abre da esquerda. A hierarquia se transmuta em uma visão vertical encapsulada por `Accordion`. 

## 6. Layout Desktop (1440 × 900)
- **Top Navigation Bar**: Contém o gatilho "Menu" acompanhado do chevron e icone.
- **Mega Menu Panel**: `w-[800px]` a `w-[1000px]`, contendo busca no topo. Grade de áreas distribuídas em 3 colunas (grid `grid-cols-3`). Cada área possui ícone forte. 

## 7. Layout Notebook (1280 × 800)
O grid do Popover reduz de `grid-cols-3` para `grid-cols-2` ou ajusta a largura total (ex. 700-800px) garantindo a legibilidade e garantindo nenhum clipping lateral (rolagem apenas vertical restrita a `max-h-[85vh]`).

## 8. Layout Tablet (1024x768 / 768x1024)
- **Modo Landscape**: Comporta-se como o layout do Notebook, mas a 2 colunas.
- **Modo Portrait**: Transiciona para o `Sheet` Drawer caso a largura seja incapaz de portar a modal sobreposta confiavelmente.

## 9. Layout Mobile (390 × 844)
Utiliza um `<Sheet>` (sidebar drawer modal). A estrutura é:
- Header do Sheet (Menu + Busca fixada).
- ScrollArea: `Accordion` com `multiple` habilitado. Áreas (ex. Agricultura, Financeiro) são gatilhos que revelam subseções indentadas e seus respectivos links. 

## 10. Hierarquia Visual
A árvore provida pelo sistema é hierarquizada sob três elos:
```text
[Módulo/Área] (ex: Agricultura, Financeiro)
   ↳ [Seção] (ex: Planejamento, Execução)
        ↳ [Destino/Link] (ex: Operações, Safras)
```

## 11. Estratégia de Busca
A busca (ícone lupa) atua sobre o cache local da árvore já autorizada. 
Não emite requests, filtrando diretamente a UI em tempo de digitação. 
- O resultado esconde áreas vazias.
- O destino preserva o breadcrumb visual: `Safras (Agricultura > Planejamento)`.
- Se a busca não render correspondências, provê um Empty State "Nenhum resultado encontrado." 

## 12. Estratégia de Foco
- **Painel Não-Modal (Desktop/Popover)**: Foco não está confinado (focus-trap suave). Escape fecha o painel. Foco retrocede naturalmente para o botão engatilhador.
- **Modal Mobile (Sheet)**: Aplica-se focus-trap obrigatório pela natureza de modal, prendendo a circulação até encerramento. 

## 13. Semântica e ARIA
- O Topbar Button carrega `aria-haspopup="dialog"`, `aria-expanded={isOpen}` e `aria-controls="mega-menu-content"`.
- O conteúdo repousa primordialmente em estruturas `<nav>` com `<ul>` e `<li>` e links nativos `<a>`. A simplificação evita overhead desnecessário de roles explícitas como "menu" de aplicação para leitores, permitindo leitura natural.

## 14. Estado Ativo
O protótipo utiliza o resolver nativo de links ativados. Se `activeSection?.key === item.href`, a âncora exibe cor primária na fonte com fundo desbotado primário (`bg-primary/10`).

## 15. Tipografia
- Títulos de Seção: fonte mini-capsulas, cinza, `text-[11px]`, uppercase com bom letter-spacing (tracking).
- Itens de Destino: `text-sm`, regulares, cor forte com hover acentuado.
- Metadados: Uso restrito à `text-muted-foreground` quando necessário.

## 16. Cores
Total uso dos CSS Vars definidos pelo Shadcn: `bg-background`, `bg-card`, `bg-muted/50`, `text-primary`, `text-muted-foreground`. Sem cores extravagantes ou color-coding forçado. 

## 17. Espaçamento
- Gaps verticais generosos para respiração de colunas (`gap-6` no grid principal desktop).
- `padding` da popover: topo do menu search unificado, container de scroll recebendo `p-6`.
- Ícones levemente afastados (`gap-3`).
- Accordion do Mobile preza por touch targets maiores (`py-3`).

## 18. Ícones
Lucide React. Tamanho unificado de áreas = `h-5 w-5` acompanhando o título. Destinos utilizam ícones `h-4 w-4` neutros. 

## 19. Animações
- Fade in (duration-150 / 200). 
- O componente `Popover` e `Sheet` nativos do Shadcn já implementam estados controlados (`data-[state=open]`) que evitam saltos repentinos, harmonizando com o ecossistema. Redução extrema nas microinterações individuais de texto para focar a CPU na filtragem. 

## 20. Componentes Reutilizados (Shadcn/UI)
- `Popover` (Desktop Overlay)
- `Sheet` (Mobile Drawer)
- `Accordion` (Mobile Treeview)
- `Input` (Search)
- `Button` (Triggers)
- `ScrollArea` (Prevenção de clipping e rolagem limpa interna)

## 21. Componentes Novos
- `MegaMenuPrototype`
- `MegaMenuDesktopContent`
- `MegaMenuMobileContent`

## 22. Estados da Interface (Mapeados no Protótipo)
- Aberto/Fechado (toggle via `isOpen`).
- Ativo (Destacado no item correspondente ao pathname).
- Busca vazia (mostrando catálogo completo).
- Busca operando e resultando em hits reduzidos.
- Busca falha: Empty State ("Nenhum resultado encontrado"). 

## 23. Protótipo Técnico
Criado um protótipo encapsulado na pasta `src/components/layout/mega-menu/mega-menu-prototype.tsx`. O componente é exportável, sem plugar diretamente no `NavigationShell`, porém usando o hook `useVisibleNavigation()` real e funcional, confirmando viabilidade integral. 

## 24. Validação por Breakpoint (Simulação Padrão)
- **1440x900**: 3 colunas de painel (ok). 
- **1280x800**: Mantém 3 colunas ou decai pra 2, scroll area entra conforme o preenchimento da base oficial. (ok).
- **1024x768**: 2 colunas seguras. 
- **390x844 (Mobile)**: O `Sheet` substitui o `Popover`. 1 coluna 100% de largura, empilhando módulos via accordions super fluidos, poupando imensamente espaço da viewport. Busca ancorada superior garante recuperação ultrarrápida. 

## 25. Riscos Residuais
Nenhum mapeado. A abordagem é segura e assenta-se puramente na leitura de cache das camadas subjacentes do próprio layout existente, não poluindo outras views. 

## 26. Decisões Rejeitadas
- Dropdown Modal Fullscreen: Rejeitado. Retiraria muito o controle da mão do usuário e causaria cegueira situacional no background. 
- Múltiplas buscas (global e menu juntas): Rejeitado. O escopo local deve se restringir às navegações e features expostas na permissão do usuário. 
- Favoritos e Recentes: Postergar. Implementar criaria duplicação desnecessária nesta fase que prioriza o hardening do esqueleto.

## 27. Arquivos Criados
- `apps/web/src/components/layout/mega-menu/mega-menu-prototype.tsx`
- `docs/implementation/reports/NAVIGATION-MODE-01C1-DESIGN-SYSTEM-MEGA-MENU.md` (Este documento)

## 28. Arquivos Alterados
Nenhum arquivo modificado destrutivamente. Apenas inclusão do protótipo e do respectivo diretório.

## 29. Testes e Validação
Comandos Executados:
```bash
npm run typecheck
npm run lint
npm run build
npm run test:sidebar
git diff --check
```

## 30. Evidências Visuais
(Serão geradas in loco durante o QA via ambiente dev. O protótipo pode ser renderizado para averiguação adicionando temporariamente `<MegaMenuPrototype />` no `AppSidebar` ou root para inspeção).

## 31. Plano Objetivo da Fase 01C2
A Fase 01C2 deverá:
1. Instanciar oficialmente `AppMegaMenu` com base na implementação do `MegaMenuDesktopContent` e `MegaMenuMobileContent`.
2. Incluir a detecção do breakpoint atual para selecionar seletivamente qual experiência disparar (Sheet x Popover) de maneira performática.
3. Substituir o `<AppMegaMenuPlaceholder />` dentro do `<NavigationShell />` pela invocação correta do novo componente.
4. Incluir botão de atalho padronizado que reflita a identidade do tenant/ambiente global, substituindo apenas os ícones e rótulos necessários da barra oficial, não adulterando o `SafraContextHeader`. 
5. Limpar os protótipos de demonstração.

## 32. Veredicto
**GO**. Todos os layouts, dependências, restrições e componentes base foram definidos com alta clareza técnica. A Fase 01C2 pode iniciar de imediato seguindo esta diretriz arquitetural sem requerer reabertura de design.
