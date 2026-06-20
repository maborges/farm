# BL-23 — F2_CUSTOS_ABC

**Módulo:** `F2_CUSTOS_ABC`  
**Status atual:** Implementado  
**Prioridade:** Alta  
**Dependências:** `CORE`, `F1_TESOURARIA`

## Contexto

Rateio, custos por safra/talhão/lote e visão gerencial de margem.

## Gaps observados

- Existe rota dedicada para `F2_CUSTOS_ABC`, com dashboard próprio e gate comercial separado de `F1_TESOURARIA`.
- O cálculo consolidado de centro de custos foi exposto para consumo operacional e gerencial.

## User Stories

### US-23.1 — Custo por atividade
**Como** gestor, **quero** apurar custo por atividade, **para** entender margem real.

**Critérios de aceite:**
- [x] Rateio automático
- [x] Centro de custos
- [x] Margem por safra/talhão/lote

### US-23.2 — Consolidado gerencial
**Como** gestor, **quero** consolidar custos, **para** comparar previsto vs realizado.

**Critérios de aceite:**
- [x] KPIs de custo
- [x] Consolidação mensal
- [x] Exportação analítica

## Tarefas técnicas

- [x] Extrair custo ABC para domínio próprio
- [x] Evitar duplicidade com custos agrícolas
- [x] Criar painel dedicado

## Evidências

- `services/api/financeiro/routers/custos.py`
- `services/api/financeiro/services/relatorio_service.py`
- `services/api/tests/unit/financeiro/test_custos_router.py`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/custos/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/custos/CustosClient.tsx`
- `apps/web/src/lib/sidebar-config.ts`
