# AUDIT-FIX-04.1 — Frontend Migration Map

## 1. Inventário

- **Total de páginas (page.tsx):** 244
- **Pages com `"use client"`:** 199
- **Server Components (RSC):** 45
- **Páginas com React Query:** 164
- **Páginas sem React Query:** 80
- **Páginas com Waterfalls (múltiplos useQuery):** 103
- **Páginas com useEffect (possíveis side-effects no render):** 33

## 2. Classificação de Migração

### Classe A: Migração Fácil (46 páginas)
_Leitura simples, dashboards simples, listagens sem estados complexos locais._
- `apps/web/src/app/(dashboard)/dashboard/settings/sessoes/page.tsx` (290 linhas, 2 queries)
- `apps/web/src/app/integracoes/dominio/page.tsx` (290 linhas, 0 queries)
- `apps/web/src/app/(dashboard)/dashboard/ambiental/monitoramento/alertas/page.tsx` (289 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/dashboard/ambiental/outorgas/page.tsx` (286 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/dashboard/ambiental/car/lista/page.tsx` (268 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/dashboard/rh/esocial/page.tsx` (262 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/dashboard/rh/departamentos/page.tsx` (257 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/backoffice/tabelas/tipos-operacao/page.tsx` (254 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/dashboard/backoffice/ia-creditos/solicitacoes/kanban/page.tsx` (251 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/agricola/custos/page.tsx` (244 linhas, 2 queries)
- ... e outras 36 páginas.

### Classe B: Migração Moderada (15 páginas)
_Formulários, filtros de listagem e CRUD leve._
- `apps/web/src/app/(dashboard)/cadastros/pessoas/page.tsx` (212 linhas, 1 queries)
- `apps/web/src/app/(auth)/forgot-password/page.tsx` (205 linhas, 0 queries)
- `apps/web/src/app/(dashboard)/dashboard/operacional/manutencoes/page.tsx` (198 linhas, 2 queries)
- `apps/web/src/app/(dashboard)/dashboard/settings/smtp/page.tsx` (195 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/dashboard/rh/ponto/page.tsx` (168 linhas, 2 queries)
- `apps/web/src/app/(dashboard)/dashboard/rh/colaboradores/page.tsx` (153 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/dashboard/financeiro/contas-pagar/page.tsx` (153 linhas, 2 queries)
- `apps/web/src/app/(dashboard)/dashboard/financeiro/contas-bancarias/page.tsx` (129 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/dashboard/agricola/cadastros/culturas/page.tsx` (25 linhas, 0 queries)
- `apps/web/src/app/(dashboard)/dashboard/backoffice/cadastros-auxiliares/unidades-conversoes/page.tsx` (24 linhas, 0 queries)
- ... e outras 5 páginas.

### Classe C: Migração Complexa (105 páginas)
_Grids complexos, gráficos (Recharts), múltiplos useQuery (>3), páginas grandes (>300 linhas)._
- `apps/web/src/app/(dashboard)/dashboard/ia/performance/page.tsx` (2129 linhas, 4 queries)
- `apps/web/src/app/(dashboard)/dashboard/backoffice/crm/page.tsx` (1718 linhas, 7 queries)
- `apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx` (1651 linhas, 7 queries)
- `apps/web/src/app/(dashboard)/dashboard/operacional/frota/[equipamentoId]/page.tsx` (1442 linhas, 6 queries)
- `apps/web/src/app/(dashboard)/dashboard/operacional/frota/page.tsx` (1377 linhas, 6 queries)
- `apps/web/src/app/(dashboard)/agricola/safras/[id]/operacoes/page.tsx` (1175 linhas, 9 queries)
- `apps/web/src/app/(dashboard)/agricola/safras/[id]/cenarios/page.tsx` (1074 linhas, 2 queries)
- `apps/web/src/app/(dashboard)/dashboard/financeiro/dre/page.tsx` (1018 linhas, 7 queries)
- `apps/web/src/app/(dashboard)/dashboard/agricola/prioridades/page.tsx` (889 linhas, 4 queries)
- `apps/web/src/app/(dashboard)/agricola/safras/[id]/production-units/page.tsx` (886 linhas, 5 queries)
- ... e outras 95 páginas.

### Classe D: Não Migrar Agora (33 páginas)
_Uso pesado de Mapas (Leaflet/Google), bibliotecas altamente client-side ou recursos PWA/offline._
- `apps/web/src/app/(dashboard)/agricola/safras/[id]/dashboard/page.tsx` (1683 linhas, 4 queries)
- `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx` (868 linhas, 4 queries)
- `apps/web/src/app/(dashboard)/cadastros/propriedades/talhoes/page.tsx` (734 linhas, 2 queries)
- `apps/web/src/app/(dashboard)/cadastros/commodities/page.tsx` (731 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/dashboard/settings/roles/page.tsx` (729 linhas, 1 queries)
- `apps/web/src/app/(dashboard)/agricola/planejamento/page.tsx` (725 linhas, 5 queries)
- `apps/web/src/app/(dashboard)/dashboard/agricola/relatorios/page.tsx` (686 linhas, 4 queries)
- `apps/web/src/app/(dashboard)/cadastros/pessoas/[id]/page.tsx` (641 linhas, 2 queries)
- `apps/web/src/app/(dashboard)/dashboard/agricola/operacoes/page.tsx` (637 linhas, 7 queries)
- `apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx` (620 linhas, 2 queries)
- ... e outras 23 páginas.

## 3. Waterfalls e Gargalos Encontrados

- **Cascatas de useQuery**: Identificados 103 arquivos onde há mais de uma invocação de `useQuery`. Quando executados no mesmo Client Component sem suspense, bloqueiam a tela de forma assíncrona até a montagem completa.
- **useEffect no render**: 33 páginas dependem de `useEffect`, podendo disparar múltiplos layouts renders no React StrictMode e gerar requests duplicados.

## 4. Oportunidades de Suspense e Bundle

- **Falta de Suspense:** É imperativo a injeção de `<Suspense fallback={<Loading />}>` e `loading.tsx` para garantir que o _Time to First Byte_ apresente um HTML de esqueleto em vez de uma tela vazia.
- **Bundle Bloqueado:** Módulos que dependem de `recharts` ou pacotes externos pesados (Data grids) poderiam adotar `next/dynamic` ou serem servidos sob demanda em Client Components filhos.

## 5. Estratégia de Migração (Ondas)

### Onda 1 (Curto Prazo - Alto Impacto)
**Top Páginas Candidatas:** Foco nos maiores arquivos da Classe A.
**Estratégia:** Extração do data-fetching principal das listagens e painéis da Classe A para `await apiFetch()` direto dentro do `page.tsx` no formato de Server Component. 
**Ganhos:** Remoção do JS client do data fetch, SEO/First Paint otimizado.
**Riscos:** Possível quebra de responsividade caso falte cache adequado via revalidate.

### Onda 2 (Médio Prazo)
**Foco:** Classe B (Formulários e CRUD leve).
**Estratégia:** Manter `page.tsx` recebendo dados do servidor via props e transferir toda a parte interativa do form (como uso do `react-hook-form`) para um `[Modulo]FormClient.tsx`.
**Ganhos:** Bundle enxuto, estados centralizados.
**Riscos:** Props drilling entre RSC e Client Components.

### Onda 3 (Longo Prazo)
**Foco:** Classe C (Dashboards completos, listagens complexas).
**Estratégia:** Divisão micro-granular de Client Components; por exemplo, apenas o gráfico e filtros interativos serão `"use client"`. O grid de dados pode ter seu wrapper RSC.
