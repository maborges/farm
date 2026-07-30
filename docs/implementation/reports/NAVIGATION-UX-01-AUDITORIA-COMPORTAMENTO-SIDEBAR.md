# NAVIGATION-UX-01 — Auditoria de Comportamento e Consistência do Sidebar

**Data:** 30/07/2026  
**Escopo:** `apps/web`, auditoria de comportamento; nenhuma alteração de implementação do sidebar nesta fase.

## 1. Resumo executivo

O sidebar tem uma boa separação entre configuração, autorização, gates de módulos e renderização. Porém, o comportamento de expansão não possui uma única fonte de verdade e não é uniforme entre Cadastros, módulos operacionais, seções internas e Backoffice.

Há três defeitos com impacto direto na previsibilidade:

1. **Seção ativa não pode ser fechada manualmente.** Ao fechar uma seção que contém a rota atual, o fallback por `pathname` a abre de novo no mesmo render.
2. **A identificação da seção ativa usa prefixos sem priorizar a rota mais específica.** Em Agricultura, qualquer rota `/agricola/...` resolve primeiro para “Safras e Contexto”, pois o item `/agricola` vem antes. O mesmo padrão afeta Estoque & Suprimento, Pecuária, Financeiro, Ambiental e IA.
3. **O drawer mobile não fecha após um link de navegação.** A evidência automatizada em Chromium confirmou a persistência do drawer após escolher “Painel Financeiro”.

O nó de módulo dos módulos operacionais e as seções do Backoffice têm uma proteção explícita para fechamento manual; Cadastros e as seções internas não têm. Assim, a regra UX “aberto + clique = fecha” não é satisfeita em todos os níveis.

**Veredicto: NO-GO** para o piloto sem a correção cirúrgica de autoexpansão/fechamento e do drawer mobile. O menu ainda permite navegar, mas seu estado muda de modo não previsível e pode ocultar o contexto correto da página ativa.

## 2. Arquitetura atual

| Camada | Arquivo | Responsabilidade observada |
| --- | --- | --- |
| Configuração | `apps/web/src/lib/sidebar-config.ts` | Define Cadastros, módulos, seções, links, permissões, tiers e `moduleId`. |
| Resolução de módulo | `apps/web/src/lib/sidebar-navigation.ts` | Mapeia prefixos de rota para a chave de módulo. |
| Renderização e estado | `apps/web/src/components/layout/app-sidebar.tsx` | Renderiza os nós, filtra permissões/tier e mantém estados de abertura. |
| Shell responsivo | `apps/web/src/components/ui/sidebar.tsx` | Controla sidebar expandido/recolhido, hover desktop, drawer mobile, tooltip e cookie de largura. |
| Gate de contratação | `apps/web/src/components/shared/module-gate.tsx` | Não renderiza conteúdo de módulo não contratado. |
| Permissões | `apps/web/src/lib/permissions.ts` | Resolve RBAC de tenant e Backoffice. |
| Bootstrap/layout | `apps/web/src/app/(dashboard)/layout.tsx` | Monta `SidebarProvider`, `AppSidebar`, topbar e `SidebarInset`. |

O sidebar não usa `Collapsible` para os nós da navegação. Os grupos são renderizados condicionalmente com `SidebarMenuSub`; portanto `defaultOpen`/`onOpenChange` de `collapsible.tsx` não causam o defeito investigado.

## 3. Fluxo do estado aberto/fechado

`AppSidebar` mantém quatro estados locais independentes:

| Estado | Uso | Fonte secundária que interfere |
| --- | --- | --- |
| `openModule` | Módulo operacional aberto | `activeModule` derivado da rota |
| `collapsedModules` | Exceção explícita para fechar o módulo ativo | efeito de mudança de módulo |
| `openSection` | Seção aberta por módulo | `getActiveSection()` derivado da rota |
| `openBackofficeSection` / `collapsedBackofficeSections` | Seção Backoffice aberta/fechada | `activeBackofficeSection` derivado da rota |

Para módulos operacionais, o fechamento manual grava a chave em `collapsedModules`; isso impede o fallback de reabrir o módulo ativo. Para Backoffice, o padrão equivalente é `collapsedBackofficeSections`.

Para uma seção interna, o cálculo é:

```ts
openSection[moduleKey] || (activeModule === moduleKey ? getActiveSection(moduleKey, pathname) : "")
```

Ao clicar numa seção ativa, `toggleSection` grava `""`. Como string vazia é falsy, a segunda metade da expressão a abre novamente. Esta é a causa-raiz do comportamento “fecha e reabre imediatamente”.

Cadastros não usa uma lista de colapsos manuais: ao zerar `openModule` na rota `/cadastros/...`, `resolvedOpenModule` volta a usar `activeModule`, reabrindo o nó.

### Respostas ao diagnóstico arquitetural obrigatório

1. **Quem controla aberto/fechado?** `AppSidebar`, com `SidebarProvider` controlando apenas a largura/drawer global.
2. **Há fonte única?** Não. Há estado local e fallback por rota em paralelo.
3. **É controlado?** Os nós são controlados manualmente por renderização condicional; não são `Collapsible` controlados.
4. **A rota força expansão?** Sim, por `activeModule`, `getActiveSection` e `getActiveBackofficeSection`.
5. **Usuário fecha nó com filho ativo?** Módulo operacional e Backoffice: sim. Cadastros e seção interna ativa: não de forma persistente.
6. **Reabre após fechar?** Sim, imediatamente em Cadastros/seção ativa; não no módulo operacional/Backoffice no mesmo pathname.
7. **Diferença entre módulos?** Sim, especialmente Cadastros versus módulos operacionais; e seções diretas versus seções aninhadas.
8. **Diferença desktop/mobile?** A lógica de nós é a mesma; no mobile há ainda drawer que não fecha após link.
9. **Nós com rota própria seguem padrão?** Não há título de módulo/seção que seja simultaneamente link e trigger; os títulos expansíveis são botões. Links são filhos.
10. **Estado após navegação?** O módulo do novo contexto abre; retornos reabrem o contexto pelo efeito de rota. Fechamentos manuais não são persistidos entre contextos.
11. **Refresh é adequado?** Módulo correspondente abre, mas a seção pode ser errada devido a prefixos amplos.
12. **Há grupos vazios?** A filtragem prévia evita módulos e seções vazios no menu normal. Não foi observado grupo vazio por gate.
13. **Acessibilidade tem problemas?** Sim: triggers não expõem `aria-expanded`/`aria-controls`; o rail não participa da tabulação.
14. **Há risco ao piloto?** Sim: alto para orientação e contexto, crítico em mobile por drawer persistente.
15. **Correção é cirúrgica?** Sim. Não exige nova arquitetura, mas exige unificar a precedência “fechamento manual > autoexpansão por rota” e ordenar a correspondência de rota.

## 4. Autoexpansão e rota ativa

### Implementação observada

- `getSidebarModuleFromPath()` usa o primeiro prefixo compatível de `MODULE_PATHS`.
- `getActiveSection()` e `getActiveBackofficeSection()` usam `pathname.startsWith(item.href)` na ordem da configuração.
- O item folha é ativo somente com igualdade exata (`pathname === item.href`).

### Inconsistências encontradas

| ID | Severidade | Evidência | Causa-raiz | Efeito |
| --- | --- | --- | --- | --- |
| NAV-01 | **CRÍTICO** | Em `/agricola/operacoes`, o navegador exibiu “Safras e Contexto” aberto, não “③ Execução”. | O primeiro item da seção é `/agricola`; `startsWith` captura toda a árvore antes da rota específica. | Seção errada autoabre em refresh/entrada direta. |
| NAV-02 | **ALTO** | Fechar a seção ativa grava `""`, e a expressão `openSection[...] || getActiveSection(...)` a reabre. | Falta de estado explícito de seção fechada manualmente. | Regra principal de clique é violada. |
| NAV-03 | **ALTO** | Cadastros deriva abertura do módulo ativo sem `collapsedModules`. | Não existe exceção explícita de fechamento para Cadastros. | Cadastros ativo não permanece fechado. |
| NAV-04 | **CRÍTICO** | Cenário Chromium mobile passou somente porque o drawer continuou visível após clicar “Painel Financeiro”. | Links não chamam `setOpenMobile(false)`. | Menu cobre a tela após navegar; fluxo mobile fica confuso. |
| NAV-05 | **MÉDIO** | `usePathname()` não inclui query string; há links `/agricola/safras?redirect=...`. | Item ativo compara pathname estritamente com `href` que contém query. | Planejamento/Orçamento não recebem destaque ativo. |
| NAV-06 | **MÉDIO** | Item folha usa igualdade exata; páginas dinâmicas não têm filho ativo correspondente. | Não há normalização de rota/segmento dinâmico para leaf active. | Painel da Safra e rotas filhas podem só destacar o pai. |
| NAV-07 | **MÉDIO** | Triggers de módulo/seção são botões sem `aria-expanded`/`aria-controls`. | Estado visual não é exposto semanticamente. | Leitores de tela não recebem o estado da hierarquia. |
| NAV-08 | **BAIXO** | `SidebarProvider` grava cookie `sidebar_state`, mas o layout sempre instancia `SidebarProvider` sem ler esse cookie. | Persistência somente de escrita. | Largura aberta/recolhida não restaura após refresh. |
| NAV-09 | **OBSERVAÇÃO** | `/cadastros/imoveis` ocorre em Visão Geral e Gestão; a duplicação é permitida pelo guardrail. | Dois links intencionais compartilham a mesma rota. | Dois contextos potenciais para a mesma página; reduz a precisão do destaque de seção. |

Prefixos amplos adicionais confirmados por leitura da configuração: `/suprimentos` captura toda a área de Suprimentos; `/dashboard/pecuaria`, `/dashboard/financeiro`, `/dashboard/ambiental` e `/dashboard/ia` capturam seus descendentes antes das seções específicas. Em Frota e RH, a incidência é menor pela composição atual de prefixos, mas o algoritmo permanece frágil.

## 5. Matriz dos nós expansíveis

Legenda: **Sim** = comportamento comprovado por implementação compartilhada; **Não** = exceção; **—** = nó de seção direta, sem expansão própria. “Rota” indica rota do título, não a dos filhos.

| Módulo/Seção | Nó | Nível | Rota própria | Inicia aberto | Fecha ao clicar | Reabre sozinho | Estado por rota | Mobile coerente | Problema |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| Cadastros | Cadastros | 1 | Não | Sim na rota `/cadastros` | **Não** na rota ativa | Sim | Sim | Não | NAV-03 |
| Imóveis | Imóveis Rurais | 1 | Não | Sim no contexto | Sim | Não no mesmo contexto | Sim | Não | — |
| Imóveis | Gestão | 2 | Não | Por rota | Não se ativa antes de Visão Geral em `/cadastros/imoveis` | Sim se ativa | Sim | Não | NAV-01/NAV-02/NAV-09 |
| Agricultura | Agricultura | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| Agricultura | Safras e Contexto | 2 | Não | Sim para **toda** `/agricola/*` | **Não** quando ativa | Sim | Sim, incorreto | Não | NAV-01/NAV-02 |
| Agricultura | ① Planejamento | 2 | Não | Por rota (nunca corretamente em subrota agrícola) | Sim se não ativa | Reabre quando ativa | Sim | Não | NAV-01/NAV-02/NAV-05 |
| Agricultura | ② Diagnóstico | 2 | Não | Idem | Idem | Idem | Sim | Não | NAV-01/NAV-02 |
| Agricultura | ③ Execução | 2 | Não | Idem | Idem | Idem | Sim | Não | NAV-01/NAV-02 |
| Agricultura | ④ Produção | 2 | Não | Idem | Idem | Idem | Sim | Não | NAV-01/NAV-02 |
| Agricultura | ⑤ Resultados | 2 | Não | Idem | Idem | Idem | Sim | Não | NAV-01/NAV-02 |
| Agricultura | ⑥ Suporte | 2 | Não | Idem | Idem | Idem | Sim | Não | NAV-01/NAV-02 |
| Suprimentos | Estoque & Suprimento | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| Suprimentos | ① Compras | 2 | Não | Não; Dashboard captura `/suprimentos/*` | Sim | Se ativa, sim | Sim, frágil | Não | NAV-01/NAV-02 |
| Suprimentos | ② Estoque | 2 | Não | Idem | Idem | Idem | Sim, frágil | Não | NAV-01/NAV-02 |
| Frota | Frota & Manutenção | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| Frota | ① Operação | 2 | Não | Sim em `/dashboard/operacional/frota/*` | **Não** quando ativa | Sim | Sim | Não | NAV-02 |
| Pecuária | Pecuária | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| Pecuária | ① Estrutura | 2 | Não | Dashboard captura a árvore | Sim | Se ativa, sim | Sim, incorreto | Não | NAV-01/NAV-02 |
| Pecuária | ② Rebanho | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| Pecuária | ③ Saúde & Nutrição | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| Pecuária | ④ Leite | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| Financeiro | Financeiro | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| Financeiro | ① Receitas & Vendas | 2 | Não | Dashboard captura a árvore | Sim | Se ativa, sim | Sim, incorreto | Não | NAV-01/NAV-02 |
| Financeiro | ② Despesas & Custos | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| Financeiro | ③ Bancário | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| Financeiro | ④ Gestão Financeira | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| Financeiro | ⑤ Hedging & Futuros | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| Financeiro | ⑤ Fiscal & Obrigações | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| RH | Recursos Humanos | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| RH | ① Estrutura | 2 | Não | Correto por prefixo | **Não** quando ativa | Sim | Sim | Não | NAV-02 |
| RH | ② Operação Diária | 2 | Não | Correto por prefixo | **Não** quando ativa | Sim | Sim | Não | NAV-02 |
| RH | ③ Obrigações | 2 | Não | Correto por prefixo | **Não** quando ativa | Sim | Sim | Não | NAV-02 |
| SST | Segurança do Trabalho | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| Ambiental | Ambiental | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| Ambiental | ① CAR & Áreas | 2 | Não | Dashboard captura a árvore | Sim | Se ativa, sim | Sim, incorreto | Não | NAV-01/NAV-02 |
| Ambiental | ② Monitoramento | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| IA | Copiloto IA | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| IA | ① Performance | 2 | Não | Dashboard captura `/dashboard/ia/*` | Sim | Se ativa, sim | Sim, incorreto | Não | NAV-01/NAV-02 |
| IA | ② Estratégia | 2 | Não | Idem | Idem | Idem | Sim, incorreto | Não | NAV-01/NAV-02 |
| Campo | Campo PWA | 1 | Não | Sim | Sim | Não no mesmo contexto | Sim | Não | — |
| Campo | Dispositivos | 2 | Não | Correto por prefixo | **Não** quando ativa | Sim | Sim | Não | NAV-02 |
| Backoffice | Visão Geral | 1 | Não | Por rota | Sim | Não no mesmo pathname | Sim | Não | Sem `aria-expanded` |
| Backoffice | Comercial | 1 | Não | Por rota | Sim | Não no mesmo pathname | Sim | Não | Sem `aria-expanded` |
| Backoffice | Suporte | 1 | Não | Por rota | Sim | Não no mesmo pathname | Sim | Não | Sem `aria-expanded` |
| Backoffice | Cadastros Auxiliares | 1 | Não | Por rota | Sim | Não no mesmo pathname | Sim | Não | Sem `aria-expanded` |
| Backoffice | Configuração | 1 | Não | Por rota | Sim | Não no mesmo pathname | Sim | Não | Sem `aria-expanded` |

Seções “Dashboard” e “Visão Geral” de Imóveis, Suprimentos, Frota, Pecuária, Financeiro, SST, Ambiental e IA são grupos diretos de links no renderizador e, por isso, não constituem nós expansíveis de nível 2.

## 6. Desktop, recolhido e mobile

### Desktop expandido

- O título de módulo é um `<button>` sem navegação acoplada; o padrão atual corresponde à alternativa A: título expande, filho navega.
- Módulos operacionais aceitam múltiplas seções configuradas, porém só uma por módulo pode ficar aberta em `openSection`.
- Apenas um módulo operacional pode estar aberto por vez (`openModule`). Backoffice também mantém uma seção aberta por vez.

### Desktop recolhido

- O modo `collapsible="icon"` reduz a barra a ícones e expande visualmente no hover.
- Há tooltip para `SidebarMenuButton` quando recolhido; ajuda a identificar o módulo.
- Não há submenu/popover próprio no ícone recolhido. O clique altera estado, mas subitens continuam ocultos até hover/expansão visual; a distinção link versus agrupador não é suficientemente explícita só pelo ícone.
- O rail de redimensionamento/alternância possui `tabIndex={-1}`; o controle de teclado disponível é o botão da topbar e o atalho Ctrl/Cmd+B.

### Mobile web

- `Sidebar` usa `Sheet`, com título e descrição disponíveis para leitor de tela.
- Os mesmos triggers e estado de nós são reutilizados, portanto NAV-01 e NAV-02 ocorrem conceitualmente também no drawer.
- Nenhum `<Link>` do `AppSidebar` chama `setOpenMobile(false)`. O cenário Playwright confirmou que, após selecionar “Painel Financeiro”, o drawer continuou visível.
- Há rolagem via `SidebarContent`; o menu é longo e não há compactação específica para mobile além do drawer.

## 7. Permissões, gates e tiers

O menu normal filtra itens por tier e permissão antes de renderizar o módulo/seção. Se todos os itens de uma seção forem bloqueados, ela retorna `null`; se todos os itens do módulo forem bloqueados, o módulo não é renderizado. Isto evita títulos vazios e chevrons sem filhos no fluxo comum.

`ModuleGate` envolve módulos e seções e remove o bloco para módulo não contratado. No modo de busca, o cabeçalho de grupo também fica dentro de `ModuleGate`, evitando cabeçalho órfão. Não foi identificada exposição de item sem permissão na leitura estática.

Risco a cobrir por teste de regressão: o módulo pai O1 usa `moduleId: O2_ESTOQUE` enquanto a seção Compras usa `O3_COMPRAS`; um tenant que tenha apenas Compras pode ser ocultado pelo gate do pai. Esta auditoria não altera a regra comercial; é uma **OBSERVAÇÃO** que precisa de cenário de matriz de contratação.

## 8. Acessibilidade

Aspectos positivos: triggers usam `<button type="button">`; links são `next/link`; há foco visível nos botões de sidebar; ícones dos links têm rótulo textual; a topbar possui botão com rótulo “Alternar sidebar”.

Lacunas:

- módulos, seções e Backoffice expansíveis não informam `aria-expanded`;
- não há `aria-controls` ligando trigger e submenu;
- a abertura não anuncia mudança de estado para tecnologias assistivas;
- o rail não é acessível por tabulação;
- não há teste de Enter/Espaço/ordem de foco dos nós expansíveis.

## 9. Evidências e testes executados

| Evidência | Resultado |
| --- | --- |
| `node apps/web/scripts/check-sidebar-guardrails.mjs` | **Passou**: 131 hrefs e 12 module gates. É teste de contrato estático; não testa interação. |
| Chromium autenticado com APIs mockadas, rota `/agricola/operacoes` | O snapshot mostrou Agricultura aberta, mas “Safras e Contexto” aberta e “③ Execução” fechada. Confirma NAV-01. |
| Chromium autenticado, viewport 390×844, rota `/dashboard/financeiro` | O cenário de clique em “Painel Financeiro” passou verificando que o drawer `[data-mobile=true]` permaneceu visível. Confirma NAV-04. |
| Leitura dos efeitos de rota e callbacks | Confirma NAV-02 e NAV-03 sem ambiguidade de temporização. |

O ambiente permitiu o navegador apenas fora do sandbox. O servidor local em `:3000` foi usado com autenticação/API simuladas. A tentativa inicial com outra porta não alcançou o namespace do navegador e foi descartada. Não há evidência E2E existente que cubra toggle, autoexpansão, fechamento manual ou drawer mobile do sidebar.

## 10. Cobertura automatizada existente e testes ausentes

Existe `apps/web/scripts/check-sidebar-guardrails.mjs`, que valida rotas configuradas, permissões, tiers, gates e alguns mapeamentos de autoexpansão. Não há teste de componente/E2E dedicado ao `AppSidebar`.

Testes a criar na fase de implementação:

1. clique alterna cada módulo operacional aberto/fechado;
2. Cadastros ativo fecha e permanece fechado no mesmo pathname;
3. seção ativa fecha e permanece fechada no mesmo pathname;
4. refresh/entrada direta abre somente o módulo e a seção da rota mais específica;
5. mudança de módulo autoabre o novo contexto sem reabrir o anterior automaticamente;
6. query de Planejamento/Orçamento preserva destaque ativo correto;
7. rota dinâmica de Safra mantém pai e leaf/contexto adequadamente ativos;
8. itens removidos por RBAC/tier/gate não deixam módulos ou seções vazios;
9. mobile fecha o `Sheet` após navegação;
10. `aria-expanded` acompanha o estado visual e Enter/Espaço alternam os nós.

## 11. Proposta de correção cirúrgica

Não implementar nesta fase. A próxima execução deve:

1. criar um resolvedor de rota único, que normalize pathname/query e escolha a correspondência mais específica (segmento ou maior `href` sem query), em vez do primeiro `startsWith`;
2. modelar o fechamento manual como estado explícito por módulo e por seção; a precedência deve ser `fechado manualmente > aberto manualmente > auto por rota`;
3. aplicar a mesma abstração a Cadastros, módulos operacionais e Backoffice, preservando a decisão de produto de um nó aberto por nível;
4. fechar o drawer mobile ao navegar por link, sem fechar quando o clique for somente trigger;
5. adicionar `aria-expanded` e `aria-controls` a todos os triggers;
6. ler o cookie `sidebar_state` no provider/layout se persistência de recolhimento continuar sendo requisito;
7. criar testes Playwright/componentes para os dez casos acima.

### Arquivos potencialmente afetados

- `apps/web/src/components/layout/app-sidebar.tsx`
- `apps/web/src/lib/sidebar-navigation.ts` (ou novo helper de matching de rota)
- `apps/web/src/components/ui/sidebar.tsx`
- `apps/web/src/app/(dashboard)/layout.tsx` (somente se restaurar o cookie)
- `apps/web/tests/e2e/...` e/ou testes unitários de navegação

## 12. Recomendação de modelo de expansão

**Recomendação: C — modelo híbrido por seção.**

- Um módulo operacional aberto por vez, como já ocorre, limita poluição visual em um ERP grande.
- Uma seção aberta por módulo, como já ocorre, preserva foco na jornada.
- O fechamento manual deve sempre ter precedência até mudança real de contexto.
- Backoffice pode manter uma seção aberta por vez pelo mesmo motivo.

Não se recomenda trocar título por link/chevron nesta fase: o padrão atual de título exclusivamente expansível e filho “Painel/Visão Geral” navegável é consistente nos módulos configurados. A prioridade é tornar esse padrão previsível.

## 13. Impacto no piloto e veredicto final

O usuário não será bloqueado de todas as páginas, mas verá grupos/seções indevidos abertos, não conseguirá fechar certas áreas ativas e, em mobile, precisará fechar o drawer manualmente após navegar. Para um público com pouca familiaridade com ERP, isso reduz confiança e pode causar navegação repetitiva.

**Veredicto final: NO-GO.**

Condição para reavaliar como GO COM RESSALVAS: corrigir NAV-01, NAV-02, NAV-03 e NAV-04; adicionar ao menos os testes de toggle, fechamento manual, rota específica e fechamento mobile. NAV-05 a NAV-09 podem ser concluídos na mesma execução de correção, mas não exigem nova arquitetura.
