# AUDIT-FIX-04.8: Classe C Discovery

## 1. Resumo Executivo
As Classes A e B foram migradas com pleno sucesso para o padrão React Server Components (RSC) + Client Components folha, eliminando dezenas de quedas de performance (waterfalls) em telas estáticas e de baixa-média interatividade.

A **Classe C** constitui os fluxos nevrálgicos de negócio do AgroSaaS:
- **Dashboards densos** e multifacetados (Gráficos via Recharts)
- **Tabelas infinitas/pesadas** e planilhas dinâmicas (AG Grid/MUI X)
- **Listagens complexas** dependentes de contexto cruzado (Múltiplas Queries locais)
- Telas que ultrapassam as 1.000 linhas e acoplam o estado de UI com a busca de dados primária.

**Objetivo desta etapa:** Propor uma estratégia cirúrgica (decomposição) antes de tentar a migração crua de `"use client"`, mapeando as frentes seguras e as "proibidas".

---

## 2. Inventário Classe C (Top 10 Páginas por Impacto)

Abaixo listamos as 10 páginas mais densas de todo o sistema na Classe C:

1. `apps/web/src/app/(dashboard)/dashboard/ia/performance/page.tsx`
   - **Linhas:** 2129
   - **Queries/Mutations:** ~4 useQueries
   - **Bibliotecas:** Recharts, Zustand
   - **Dependências de Browser:** LocalStorage (filtros persisitentes)
   - **Gráficos/Grids:** Múltiplos painéis gráficos complexos.

2. `apps/web/src/app/(dashboard)/dashboard/backoffice/crm/page.tsx`
   - **Linhas:** 1718
   - **Queries/Mutations:** ~7 useQueries, ~3 useMutations
   - **Gráficos/Grids:** Kanban, Grids ricos.
   - **Riscos:** Alto acoplamento de side-effects.

3. `apps/web/src/app/(dashboard)/suprimentos/estoque/page.tsx`
   - **Linhas:** 1651
   - **Queries/Mutations:** ~7 useQueries, ~5 useMutations
   - **Gráficos/Grids:** AG Grid pesado, abas de saldos.
   - **Riscos:** Fluxo sensível (movimentação de inventário real).

4. `apps/web/src/app/(dashboard)/dashboard/operacional/frota/[equipamentoId]/page.tsx`
   - **Linhas:** 1442
   - **Queries:** ~6 queries parciais

5. `apps/web/src/app/(dashboard)/dashboard/operacional/frota/page.tsx`
   - **Linhas:** 1377
   - **Queries:** ~6 queries de listagem

6. `apps/web/src/app/(dashboard)/agricola/safras/[id]/operacoes/page.tsx`
   - **Linhas:** 1175
   - **Queries:** ~9 queries cruzadas (operações, máquinas, tempo).

7. `apps/web/src/app/(dashboard)/agricola/safras/[id]/cenarios/page.tsx`
   - **Linhas:** 1074
   - **Queries:** ~2 grandes queries pesadas (Agregações matemáticas complexas em UI).

8. `apps/web/src/app/(dashboard)/dashboard/financeiro/dre/page.tsx`
   - **Linhas:** 1018
   - **Queries:** ~7 queries de DRE, fluxo e cenários.

9. `apps/web/src/app/(dashboard)/dashboard/agricola/prioridades/page.tsx`
   - **Linhas:** 889
   - **Queries:** ~4 queries (Kanban de Campo)

10. `apps/web/src/app/(dashboard)/agricola/safras/[id]/production-units/page.tsx`
    - **Linhas:** 886
    - **Queries:** ~5 queries.

*(Nota: Adicionamos as 4 páginas diferidas da Classe B à Classe C: `roles`, `team`, `produtos`, `imoveis`)*

---

## 3. Top 5 Páginas por Risco (Risco Crítico)

1. **`suprimentos/estoque/page.tsx`** - Risco financeiro real se quebrar inventário.
2. **`dashboard/financeiro/dre/page.tsx`** - Complexidade matemática front-side.
3. **`agricola/safras/[id]/operacoes/page.tsx`** - Acoplamento com apontamento diário e múltiplas sub-entidades (RH, Frota, Insumos).
4. **`dashboard/backoffice/crm/page.tsx`** - Fluxo central comercial e retenção da empresa.
5. **`dashboard/operacional/frota/[equipamentoId]/page.tsx`** - Possui micro-dashboards aninhados sobre tempo e vida útil.

---

## 4. Classificação de Risco (Modelos)

**Das 105+ páginas da Classe C, categorizamos:**

* **C1 — Migrável com Baixo Risco (Estimativa: ~35 páginas)**
  * Listagem densa, porém em uma única tabela contida que só depende de *searchParams* estritos.
  * O `page.tsx` pode virar um wrapper RSC rapidamente chamando a tabela como folha.
* **C2 — Migrável com Decomposição Média (Estimativa: ~40 páginas)**
  * A página tem abas, modais diversos e gráficos misturados. Requer fatiamento prévio em micro-componentes antes de aplicar RSC no topo. (Ex: `cadastros/produtos/page.tsx`).
* **C3 — Exige Redesign Parcial / Refatoração Profunda (Estimativa: ~20 páginas)**
  * Alto acoplamento de estados (múltiplos `useQuery` injetando dados num chart). Requer migrar processamentos pesados pro Backend/Node ou virtualização total. (Ex: `suprimentos/estoque/page.tsx`, `financeiro/dre/page.tsx`).
* **C4 — Não Migrar Agora (Estimativa: ~10 páginas)**
  * Implantações assistidas massivas (Wizard), Mapas integrados e PWA Offline caching. 

---

## 5. Estratégia e Padrões de Decomposição

Para lidar com o código engessado nas classes C2/C3 sem quebrar nada:
1. **Shell RSC Limitado:**
   * O `page.tsx` passará apenas `initialData` do *miolo vital* ou passará *IDs*. Ele funcionará como uma "casca pre-renderizada" da página.
2. **Delegação a Componentes Dinâmicos (`next/dynamic`):**
   * Gráficos complexos (`Recharts`) não devem ser bloqueantes. Devem ser envelopados e carregados via *Dynamic Import* com `{ ssr: false }` ou embrulhados com `<Suspense fallback={<Skeleton />}>` para hidratação fragmentada.
3. **Prop Drilling Seguro vs Context API:**
   * Nas páginas grandes (1500+ linhas), transferir 8 arrays como props do RSC para o Client pode exceder o payload limite.
   * **Solução:** O RSC repassará apenas dados estáticos críticos (tenant, configs, permissão). O React Query fará o _stale-while-revalidate_ das listas de mais de 10.000 linhas paralelamente sob demanda ou paginação Server Side.

---

## 6. Candidatos Piloto Sugeridos

**Pilotos C1 (Migração Direta / Wrapper RSC):**
1. `apps/web/src/app/(dashboard)/cadastros/produtos/page.tsx` (Diferido da Classe B, ótimo case para testar props drilling).
2. `apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx` (Diferido da Classe B, focado na exibição de dados longos com abas).

**Pilotos C2 (Estudo de Decomposição):**
1. `apps/web/src/app/(dashboard)/dashboard/settings/roles/page.tsx` (Possui lista imensa de permissões matriz e check-boxes, exige fatiamento do forms e separação RSC/Client em abas).

**Páginas Proibidas nesta Fase (C3/C4):**
- *Qualquer fluxo PWA ou Offline.*
- *Estoque Central (`suprimentos/estoque/page.tsx`)*
- *Operações de Safra (`agricola/safras/[id]/operacoes/page.tsx`)*
- *Relatórios DRE e Cenários.*
- *Assistentes e Wizards.*

---

## 7. Recomendação para AUDIT-FIX-04.9

1. **Início dos Pilotos C1/C2:** Implementar os 3 pilotos selecionados (Produtos, Imóveis e Roles). Eles confirmarão se a estratégia de desmembramento sem quebra de `react-hook-form` e `payload limit` é sustentável antes de ir para telas maiores.
2. **Homologação Estrita:** Monitorar o comportamento de re-renderização (`useEffect`) para evitar refetches acidentais após o fatiamento das telas que chegam a 800+ linhas.
