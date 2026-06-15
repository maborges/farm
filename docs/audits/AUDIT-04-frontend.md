# AUDIT-04: Performance e UX (Next.js/Frontend)

## Contexto e Escopo
Esta auditoria avalia o frontend do AgroSaaS (`apps/web`) em relação aos critérios de performance, UX e adoção correta do Next.js App Router, conforme diretrizes do projeto (**AGRO-03** e **AGRO-04**).

Nesta etapa, o objetivo é apenas **identificar e documentar riscos e desvios**, sem realizar modificações no código-fonte.

## 1. Avaliação de Renderização (Server vs Client Components)

**Achado Crítico (P0): Violação Massiva do Padrão RSC**
- A diretriz `AGRO-03` define que "Todo componente é Server Component por padrão" e que "`page.tsx` DEVE ser RSC".
- **Realidade:** Dos **244** arquivos `page.tsx` encontrados em `apps/web/src/app`, incríveis **190 arquivos** contêm a diretriz `"use client"`.
- **Impacto:** O frontend está operando essencialmente como uma SPA tradicional (Single Page Application). A página precisa baixar o bundle de JavaScript do cliente, fazer o parse, fazer o boot do React e, somente então, disparar o fetch de dados via `useQuery`. Isso elimina os benefícios do App Router (HTML streaming, redução de bundle, carregamento inicial rápido).
- **Evidência:** Arquivos centrais como `apps/web/src/app/(dashboard)/dashboard/financeiro/page.tsx` e `apps/web/src/app/(dashboard)/agricola/dashboard/page.tsx` são `"use client"` inteiramente.

## 2. Tratamento de Carregamento (Skeletons e Suspense)

**Achado (P1): Subutilização do Native Suspense (`loading.tsx`)**
- A diretriz exige: "Use `loading.tsx` para Suspense nativo em telas pesadas".
- **Realidade:** Existem **apenas 3 arquivos `loading.tsx`** em toda a aplicação (`agricola/analises-solo/loading.tsx`, `agricola/rat/loading.tsx`, `backoffice/tenants/loading.tsx`). Módulos massivos como Financeiro e Operacional não possuem arquivo de loading na rota.
- **Impacto:** O Next.js não consegue transmitir o layout e a interface de carregamento (HTML streaming). O usuário fica com a tela em branco até o React renderizar no cliente.
- **Evidência:** Em `financeiro/page.tsx`, Skeletons são renderizados via condicional (`if (isLoading) return <Skeleton />`) do client-side `useQuery`, atrasando o Time to First Byte (TTFB) percebido.

## 3. Waterfalls de Fetch de Dados no Cliente

**Achado (P1): Cascatas de chamadas API e Bloqueios Visuais**
- Como as páginas são Client Components, requisições paralelas (Dashboard KPIs, Fluxo de Caixa, Contas, Despesas) ocorrem apenas *depois* que a página carrega.
- Exemplo: `financeiro/page.tsx` faz 4 fetches separados via `useQuery`:
  - `/relatorios/dashboard`
  - `/relatorios/fluxo-caixa`
  - `/financeiro/despesas/`
  - `/financeiro/receitas/`
- **Risco:** Múltiplas conexões originadas do browser (latência alta) vs busca no servidor (RSC via `await fetch` ou conexão direta), o que é ineficiente.

## 4. Renderização de Data Grids (Tabelas Massivas)

**Achado (P2): Ausência de AG Grid para Grandes Volumes**
- A diretriz especifica: "AG Grid para planilhas com 10k+ linhas (Rebanho/Financeiro)".
- **Realidade:** A biblioteca `ag-grid` não está presente no `package.json`.
- **Risco:** Listagens como "Lançamentos Financeiros" ou "Estoque" provavelmente utilizam renderizações customizadas baseadas em tabelas simples, o que causará degradação de performance do browser caso haja muitos registros exibidos sem virtualização estrita no client.

## 5. Layout Shift (CLS)

**Achado (P2): Falta de Dimensões Estritas**
- O carregamento condicional dos gráficos em `dashboard/financeiro/page.tsx` não aplica uma altura ou largura 100% rígida desde a div raiz, podendo causar micro-pulos ao montar o canvas do Recharts após a carga dos dados (CLS - Cumulative Layout Shift). O layout tem um fallback `<div className="h-[260px] ... bg-muted">` o que mitiga parcialmente, mas o esqueleto primário sofre pop-in após carregar toda a aplicação react.

## 6. Gerenciamento de Estado (Sync State)

**Status OK:** O frontend obedece bem à separação de Server State e Client State.
- **TanStack Query** (v5) está sendo usado com sucesso para estado assíncrono (cache de APIs).
- **Zustand** (via `useAppStore`) está devidamente focado em controle leve de Client State (ex: `activeFazendaId`, `token`).

---

### Resumo das Próximas Ações Sugeridas (AUDIT-FIX-04)
1. **Refatoração para RSC (Core Pages):** Extrair o `useQuery` de dashboards principais (`financeiro/page.tsx`, `agricola/dashboard/page.tsx`) para Server Components passando `initialData` ou realizando o fetch direto antes de repassar ao `FinanceiroDashboardClient`.
2. **Implementar `loading.tsx`:** Inserir os arquivos de carregamento nos níveis de módulo (Financeiro, Agrícola, Operacional) injetando skeletons visuais antecipadamente pelo servidor.
3. **Avaliação AG Grid:** Incluir AG Grid nas tabelas que preveem volume massivo, protegendo a renderização.
