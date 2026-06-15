# AUDIT-FIX-04.16 — Discovery Frota UI

**Data:** 2026-06-09  
**Arquiteto:** Frontend Sênior AgroSaaS  
**Status:** ✅ Discovery Concluído — Aguardando aprovação para AUDIT-FIX-04.17

---

## 1. Inventário de Arquivos

| Arquivo | Linhas | `use client` | Tier | useMutation | Risco |
|---------|--------|-------------|------|-------------|-------|
| `frota/page.tsx` | **1.378** | ✅ | PROFISSIONAL + ENTERPRISE | ❌ | **ALTO** |
| `frota/[equipamentoId]/page.tsx` | **1.442** | ✅ | PROFISSIONAL + ENTERPRISE | ❌ | **ALTO** |
| `frota/jornadas/page.tsx` | **708** | ✅ | PROFISSIONAL | ✅ (3x) | **CRÍTICO** |
| `frota/manutencao-preventiva/page.tsx` | **403** | ✅ | PROFISSIONAL | ✅ (1x) | MÉDIO |
| `frota/consumo/page.tsx` | **362** | ✅ | PROFISSIONAL | ❌ | BAIXO |
| `frota/custos/page.tsx` | **373** | ✅ | PROFISSIONAL | ❌ | BAIXO |
| `frota/disponibilidade/page.tsx` | **379** | ✅ | PROFISSIONAL | ❌ | BAIXO |
| `frota/inteligencia/page.tsx` | **443** | ✅ | ENTERPRISE | ❌ | BAIXO |
| `frota/agricultura/page.tsx` | **410** | ✅ | ENTERPRISE | ❌ | BAIXO |
| `manutencoes/page.tsx` | **27** | ❌ (RSC ✅) | — | — | **JÁ MIGRADO** |

**Total de linhas ativas:** ~5.498  
**Já migrado:** `manutencoes/page.tsx` (RSC + ManutencoesClient)

---

## 2. Mapeamento de Estrutura — `frota/page.tsx` (1.378 linhas)

### Tipos/Interfaces (linhas 32–302)
- `FrotaResumo` — 18 campos de KPIs operacionais
- `FrotaEquipamento` — lista detalhada por máquina com custo/hora/km, riscos, OS
- `FrotaRankingItem` — top custos
- `FrotaAlerta` — alertas operacionais (5 tipos de risco)
- `FrotaUltimoAbastecimento` — últimos registros de combustível
- `FrotaJornadaDashboardItem` — jornadas operacionais abertas/recentes
- `FrotaDashboard` — agregador raiz (6 chaves)
- `FrotaConsumoDashboard`, `FrotaDisponibilidadeDashboard`, `FrotaCustoDashboard`
- `FrotaInteligenciaDashboard`, `FrotaAgriculturaDashboard`

### Constantes (linhas 304–317)
- `RISCO_LABELS` — 5 tipos de risco mapeados para labels
- `MANUTENCAO_LABELS` — 4 status de manutenção

### Componente Principal `FrotaPage` (linhas 319–1246)
- **1 estado**: nenhum `useState` local (apenas leitura)
- **6 useQuery independentes** com `enabled` condicional por tier:
  1. `queryKey: ["frota", "dashboard", activeFazendaId]` → `/frota/dashboard`
  2. `queryKey: ["frota", "consumo-dashboard", activeFazendaId]` → `/frota/consumo` *(PROFISSIONAL)*
  3. `queryKey: ["frota", "disponibilidade-dashboard", activeFazendaId]` → `/frota/disponibilidade` *(PROFISSIONAL)*
  4. `queryKey: ["frota", "custos-dashboard", activeFazendaId]` → `/frota/custos` *(PROFISSIONAL)*
  5. `queryKey: ["frota", "inteligencia-dashboard", activeFazendaId]` → `/frota/inteligencia` *(ENTERPRISE)*
  6. `queryKey: ["frota", "agricultura-dashboard", activeFazendaId]` → `/frota/agricultura/resumo` *(ENTERPRISE)*
- **0 useMutation** (página é puramente de leitura)
- **0 useEffect**
- **0 localStorage/window/document**

### Seções Visuais
- `PageHeader` com navegação condicional por tier (botões diferentes por PROFISSIONAL/ENTERPRISE)
- **Bloco KPI Principal** — 6 cards (Equipamentos, Manutenção, Em uso, Em risco, Manutenções vencidas, Custo acumulado)
- **Bloco KPI Disponibilidade** — 5 cards *(PROFISSIONAL)* ou `TierUpgradeCard`
- **Bloco KPI Custos** — 4 cards *(PROFISSIONAL)* ou `TierUpgradeCard`
- **Grid principal** — Equipamentos da frota + sidebar (Ranking de Custo + Últimos Abastecimentos + Últimas Jornadas)
- **Alertas operacionais** — lista de alertas por equipamento
- **Alertas de consumo** *(PROFISSIONAL)*
- **Disponibilidade operacional** *(PROFISSIONAL)*
- **Resumo financeiro** *(PROFISSIONAL)* — custo por hectare, preventivo vs corretivo, ociosidade
- **Frota em risco** *(ENTERPRISE)* — ranking top 5 por score
- **Eficiência operacional** *(ENTERPRISE)* — ranking de consumo
- **Uso agrícola** *(ENTERPRISE)* — integração Frota × Agricultura

### Funções Auxiliares (linhas 1249–1377)
- `KpiCard` — componente local (pode virar subcomponente)
- `DashboardSkeleton` — skeleton de carregamento
- `formatCurrency`, `formatNumber`, `formatDateOrDash`, `formatDateTime`
- `getMaintenanceBadgeClass`, `getRiskClass`, `formatRiskLabel`

---

## 3. Mapeamento — `frota/[equipamentoId]/page.tsx` (1.442 linhas)

### Pattern
- Usa `useParams()` para ler `equipamentoId` — **dependência de Client-Side obrigatória** (ou migrar via RSC com `params` prop)
- **6 useQuery** por equipamento com período filtrado:
  1. `/frota/dashboard/equipamentos/:id` — dados gerais + custos + OS + abastecimentos
  2. `/frota/consumo/equipamentos/:id` *(PROFISSIONAL)*
  3. `/frota/disponibilidade/equipamentos/:id` *(PROFISSIONAL)*
  4. `/frota/custos/equipamentos/:id` com filtro de período *(PROFISSIONAL)*
  5. `/frota/inteligencia/equipamentos/:id` *(ENTERPRISE)*
  6. `/frota/agricultura/equipamentos/:id` *(ENTERPRISE)*
- **0 useMutation**
- **1 useState**: `[periodo, setPeriodo]` — filtro de período (30/90/180/all)
- Tabs implícitas via seções verticais

---

## 4. Mapeamento — `frota/jornadas/page.tsx` (708 linhas)

**Complexidade: CRÍTICA — possui forms + 3 mutations**

### States locais (4 useState)
- `selectedJornadaId` — jornada selecionada para finalizar/cancelar
- `form` — objeto de estado do formulário de criação de jornada (sem react-hook-form, form manual)
- `finalizacao` — leituras de finalização (horímetro, km)

### Queries (5 useQuery)
1. `["frota", "jornadas", activeFazendaId]` → `/frota/jornadas`
2. `["frota", "equipamentos-opcoes", activeFazendaId]` → `/frota`
3. `["frota", "operadores-opcoes"]` → `/cadastros/pessoas`
4. `["frota", "safras-opcoes"]` → `/safras`
5. `["frota", "talhoes-opcoes", activeFazendaId]` → `/cadastros/areas-rurais`

### Mutations (3 useMutation)
- `criarMutation` → `POST /frota/jornadas` — cria nova jornada operacional
- `finalizarMutation` → `POST /frota/jornadas/:id/finalizar` — finaliza jornada com leituras
- `cancelarMutation` → `POST /frota/jornadas/:id/cancelar`

### Invalidações após mutations
```ts
queryClient.invalidateQueries({ queryKey: ["frota", "jornadas"] });
queryClient.invalidateQueries({ queryKey: ["frota", "dashboard"] });
queryClient.invalidateQueries({ queryKey: ["frota", "disponibilidade"] });
```
⚠️ Invalida 3 query keys ao mesmo tempo — lógica sensível que afeta o painel principal.

---

## 5. Mapeamento — `frota/manutencao-preventiva/page.tsx` (403 linhas)

- **1 useQuery**: `/frota/manutencao-preventiva`
- **1 useMutation**: `gerarOsMutation` → `POST /frota/manutencao-preventiva/:planoId/gerar-os`
- Invalida `["frota", "manutencao-preventiva"]`, `["frota", "dashboard"]` e `["oficina"]`
- ⚠️ Cruzamento com `["oficina"]` — dependência com módulo de Manutenções/OS

---

## 6. Endpoints Completos Mapeados

| Endpoint | Módulo | Tier | Tipo |
|----------|--------|------|------|
| `GET /frota/dashboard` | Dashboard | TODOS | Dashboard agregado |
| `GET /frota/consumo` | Consumo | PROFISSIONAL | Anomalias + ranking |
| `GET /frota/disponibilidade` | Disponibilidade | PROFISSIONAL | Status de frota |
| `GET /frota/custos` | Custos | PROFISSIONAL | Financeiro frota |
| `GET /frota/inteligencia` | Inteligência | ENTERPRISE | Score de risco |
| `GET /frota/agricultura/resumo` | Agricultura | ENTERPRISE | Apontamentos × safra |
| `GET /frota/dashboard/equipamentos/:id` | Detalhe | TODOS | KPIs por máquina |
| `GET /frota/consumo/equipamentos/:id` | Detalhe | PROFISSIONAL | Consumo individual |
| `GET /frota/disponibilidade/equipamentos/:id` | Detalhe | PROFISSIONAL | Status individual |
| `GET /frota/custos/equipamentos/:id` | Detalhe | PROFISSIONAL | Custo individual |
| `GET /frota/inteligencia/equipamentos/:id` | Detalhe | ENTERPRISE | Risco individual |
| `GET /frota/agricultura/equipamentos/:id` | Detalhe | ENTERPRISE | Apontamentos individuais |
| `GET /frota/jornadas` | Jornadas | PROFISSIONAL | Lista de jornadas |
| `POST /frota/jornadas` | Jornadas | PROFISSIONAL | Criar jornada |
| `POST /frota/jornadas/:id/finalizar` | Jornadas | PROFISSIONAL | Finalizar com leituras |
| `POST /frota/jornadas/:id/cancelar` | Jornadas | PROFISSIONAL | Cancelar jornada |
| `GET /frota` | Options | TODOS | Lista de equipamentos |
| `GET /frota/manutencao-preventiva` | Preventiva | PROFISSIONAL | Planos e vencimentos |
| `POST /frota/manutencao-preventiva/:id/gerar-os` | Preventiva | PROFISSIONAL | Gerar OS do plano |
| `GET /cadastros/pessoas` | Options | TODOS | Operadores |
| `GET /safras` | Options | TODOS | Safras |
| `GET /cadastros/areas-rurais` | Options | TODOS | Talhões |

---

## 7. Estados Críticos e Riscos Operacionais

### 7.1 Risco: Controle de Tier (ALTO)
A página principal usa `useHasTier("PROFISSIONAL")` e `useHasTier("ENTERPRISE")` para **habilitar/desabilitar queries** (`enabled: hasProfessionalTier`). 

**Problema na migração RSC:** O `apiFetchServer` no servidor não tem acesso ao tier do usuário da sessão atual de forma trivial. 

**Mitigação:** As queries condicionais por tier devem **permanecer no Client Component**. O RSC Shell só carregará os endpoints sem condicional de tier (apenas `frota/dashboard`).

### 7.2 Risco: Invalidação Cross-módulo (ALTO)
`jornadas` e `manutencao-preventiva` invalidam `["oficina"]` ao mutacionar. Qualquer componente que escute `["oficina"]` no mesmo layout ficará inconsistente se o cache não for compartilhado corretamente.

**Mitigação:** Preservar `invalidateQueries` exatamente como estão no Client Component, sem mover para Server Actions.

### 7.3 Risco: Filtro Temporal em `[equipamentoId]` (MÉDIO)
O componente de detalhe do equipamento possui filtro de período interativo (`periodo: "30" | "90" | "180" | "all"`). O `apiFetchServer` no RSC só pode buscar com um período default. O resto deve ser refetch no Client.

**Mitigação:** RSC carrega `periodo=90` como default. Client recarga ao trocar filtro.

### 7.4 Risco: Custo de Manutenção × Financeiro (MÉDIO)
`custo_manutencao` e `custo_abastecimento` aparecem em múltiplas views. Se cache do dashboard ficar stale após uma mutation de jornada/preventiva, o KPI de custo exibirá dados desatualizados.

**Mitigação:** `invalidateAll` após mutations já está correto. `initialData` no RSC serve apenas para hidratação SSR, não substitui o cache do Client.

### 7.5 Risco: `useParams()` em `[equipamentoId]` (BAIXO)
O hook `useParams()` é Client-Only. Na migração para RSC Shell, `params.equipamentoId` virará `props.params.equipamentoId` no RSC, passado como `initialEquipamentoId` ao Client.

---

## 8. Classificação das Páginas

| Página | Classe | Critério |
|--------|--------|----------|
| `frota/page.tsx` | **C1** | Somente leitura, 0 mutations, grande volume de queries condicionais por tier |
| `frota/consumo/page.tsx` | **C1** | Somente leitura, 1 query simples |
| `frota/custos/page.tsx` | **C1** | Somente leitura, 1 query com filtro de período |
| `frota/disponibilidade/page.tsx` | **C1** | Somente leitura, 1 query |
| `frota/inteligencia/page.tsx` | **C1** | Somente leitura, ENTERPRISE |
| `frota/agricultura/page.tsx` | **C1** | Somente leitura, ENTERPRISE |
| `frota/[equipamentoId]/page.tsx` | **C2** | Somente leitura, mas 6 queries + filtro de período + useParams |
| `frota/manutencao-preventiva/page.tsx` | **C2** | 1 mutation, invalida módulo "oficina" |
| `frota/jornadas/page.tsx` | **C3** | 3 mutations, forms manuais, 5 queries, invalidação cross-módulo |
| `manutencoes/page.tsx` | ✅ DONE | RSC já implementado em AUDIT-FIX-04.7 |

---

## 9. Arquitetura Alvo

### 9.1 Grupo C1 — Leitura Pura (frota/page.tsx e subpáginas de leitura)

```
frota/page.tsx (RSC Shell)
├── apiFetchServer("/frota/dashboard")  ← sempre carregado
└── <FrotaClient initialData={...} />

FrotaClient.tsx ("use client")
├── useHasTier() — controla queries condicionais
├── useQuery(["frota", "consumo-dashboard"])  enabled=hasProfessionalTier
├── useQuery(["frota", "disponibilidade-dashboard"])  enabled=hasProfessionalTier
├── useQuery(["frota", "custos-dashboard"])  enabled=hasProfessionalTier
├── useQuery(["frota", "inteligencia-dashboard"])  enabled=hasEnterpriseTier
├── useQuery(["frota", "agricultura-dashboard"])  enabled=hasEnterpriseTier
└── JSX completo preservado
```

> ⚠️ **Decisão de design:** As queries condicionais por tier NÃO devem ir para o RSC Shell. O servidor não pode verificar o tier do usuário sem expor o token de sessão no `apiFetchServer`. Apenas o `frota/dashboard` vai para o servidor (é universal). As demais continuam no Client com `enabled` condicional.

### 9.2 Grupo C2 — `[equipamentoId]` e Preventiva

```
frota/[equipamentoId]/page.tsx (RSC Shell)
├── apiFetchServer(`/frota/dashboard/equipamentos/${params.equipamentoId}`)
└── <EquipamentoDetailClient
      equipamentoId={params.equipamentoId}
      initialData={...} />

EquipamentoDetailClient.tsx ("use client")
├── useState([periodo])
├── 6 useQuery com periodo como dep
└── JSX completo preservado
```

### 9.3 Grupo C3 — Jornadas (não migrar ainda)

```
frota/jornadas/page.tsx  → permanece Client Component por ora
```
Jornadas tem 3 mutations, forms manuais, 5 queries de opções e invalidação cross-módulo. Migrar para RSC traria risco desproporcionalmente alto sem benefício de performance significativo (o bottleneck é o form, não o carregamento inicial).

### 9.4 Subcomponentes Sugeridos para Decomposição

| Componente | Tipo | Extraído de |
|-----------|------|------------|
| `FrotaResumoCards.tsx` | Server/Client | Seção KPI do `frota/page.tsx` |
| `FrotaEquipamentosPanel.tsx` | Client | Grid de equipamentos + ranking |
| `FrotaAlertasPanel.tsx` | Client | Alertas operacionais + consumo |
| `FrotaDisponibilidadeResumoPainel.tsx` | Client | Bloco disponibilidade |
| `FrotaAgriculturaResumoPainel.tsx` | Client | Bloco uso agrícola |
| `FrotaInteligenciaRankingPainel.tsx` | Client | Bloco inteligência |
| `EquipamentoDetailClient.tsx` | Client | `[equipamentoId]/page.tsx` completo |
| `JornadasClient.tsx` | Client | `jornadas/page.tsx` (sem RSC) |
| `ManutencaoPreventivaPainel.tsx` | Client | Subcomponente da página preventiva |

---

## 10. Plano Incremental

### AUDIT-FIX-04.17 — Decomposição Visual Frota (sem RSC)
**Objetivo:** Extrair subcomponentes do `frota/page.tsx` para `_components/`  
**Escopo:**
- `_components/FrotaEquipamentosPanel.tsx` — lista de equipamentos
- `_components/FrotaAlertasPanel.tsx` — alertas operacionais + consumo
- `_components/FrotaKpiCard.tsx` — KpiCard extraído
- `_components/FrotaDashboardSkeleton.tsx` — skeleton
- Manter `page.tsx` como Client Component
- Validar `tsc --noEmit` após cada extração

**Risco:** BAIXO. Apenas movimentação de JSX sem alterar lógica.

### AUDIT-FIX-04.18 — RSC Shell Frota
**Objetivo:** Converter `frota/page.tsx` para RSC  
**Escopo:**
- `page.tsx` → RSC, busca apenas `/frota/dashboard` com `apiFetchServer`
- `FrotaClient.tsx` → Client coordenador com `initialData`
- Queries condicionais (consumo/disponibilidade/custos/inteligencia/agricultura) permanecem no Client com `enabled: useHasTier(...)`
- Mesma abordagem para `frota/consumo`, `custos`, `disponibilidade`, `inteligencia`, `agricultura` (C1 simples)
- Validar `tsc + eslint`

**Risco:** MÉDIO. Cuidado com as queries condicionais por tier.

### AUDIT-FIX-04.19 — RSC Shell `[equipamentoId]`
**Objetivo:** Converter página de detalhe do equipamento para RSC  
**Escopo:**
- `page.tsx` → RSC, busca `/frota/dashboard/equipamentos/:id` com `apiFetchServer`
- `EquipamentoDetailClient.tsx` → Client com `useState(periodo)` + 5 queries extras condicionais
- `params.equipamentoId` passado via props
- Validar `tsc + eslint`

**Risco:** MÉDIO. Dependência de `useParams()` eliminada corretamente via props.

### AUDIT-FIX-04.20 — Validação UI/E2E Frota
**Objetivo:** Validar navegação, KPIs, tier gates e detail page  
**Escopo:**
- Teste Playwright: carregamento do dashboard, cards KPI, link para detalhe, navegação entre subpáginas
- Verificar que `TierUpgradeCard` aparece para usuários sem PROFISSIONAL
- Verificar que `frota/jornadas` continua funcional como Client puro

---

## 11. Recomendação de Fase

```
PRÓXIMO PASSO RECOMENDADO:
AUDIT-FIX-04.17 — Decomposição Visual Frota
```

**Motivo:** O `frota/page.tsx` com 1.378 linhas, assim como o Estoque, deve ter seus painéis secundários extraídos antes da conversão RSC. A decomposição visual reduz o risco de erros de import durante a criação do `FrotaClient.tsx` e torna o AUDIT-FIX-04.18 cirúrgico e seguro.

**NÃO migrar `jornadas/page.tsx` para RSC** neste ciclo — risco desproporcionalmente alto pelas 3 mutations cross-módulo.

---

## 12. Riscos Finais Classificados

| # | Risco | Severidade | Mitigação |
|---|-------|-----------|-----------|
| R1 | Queries condicionais por tier no RSC Shell | 🔴 CRÍTICO | Manter `enabled: useHasTier()` no Client, RSC busca apenas dashboard base |
| R2 | Invalidação cross-módulo em jornadas | 🟠 ALTO | Não migrar jornadas para RSC neste ciclo |
| R3 | `useParams()` em `[equipamentoId]` | 🟡 MÉDIO | Passar `equipamentoId` como prop do RSC para o Client |
| R4 | Filtro de período reativo | 🟡 MÉDIO | RSC fornece `periodo=90` default, Client recarga no filtro |
| R5 | Cache stale após mutation de manutenção | 🟢 BAIXO | `invalidateAll` no Client já trata corretamente |
| R6 | Cruzamento `["oficina"]` com preventiva | 🟡 MÉDIO | Preservar mutation sem alteração no Client |
