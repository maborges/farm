# CAMPO PWA-05 — Tarefas Programadas

**Branch:** `feature/campo-pwa-05-tarefas-programadas`  
**Data:** 2026-05-08

---

## Objetivo

Permitir que gestores programem tarefas no backoffice (apps/web) e operadores as recebam no PWA de campo (apps/campo), executem offline e sincronizem o resultado.

---

## Arquitetura

### Modelo unificado (Abordagem A)

`TarefaCampo` extendida com:

| Campo | Tipo | Descrição |
|---|---|---|
| `origem` | `MANUAL \| PROGRAMADA` | Diferencia criação offline vs backoffice |
| `status_execucao` | `PENDENTE \| EM_EXECUCAO \| CONCLUIDA \| CANCELADA` | Estado de execução pelo operador |
| `titulo` | String(200) nullable | Descrição legível (backoffice) |
| `data_programada` | Date nullable | Data alvo da execução |
| `prioridade` | `BAIXA \| NORMAL \| ALTA \| URGENTE` | Urgência da tarefa |
| `operador_id` | UUID nullable | Atribuição opcional a um operador |
| `iniciada_em` | DateTime nullable | Quando operador clicou "Iniciar" |
| `concluida_em` | DateTime nullable | Quando operador clicou "Concluir" |

### Regras de negócio

- `CONCLUIR` só é permitido se `status_execucao = EM_EXECUCAO`
- Tarefas manuais (criadas offline): `origem=MANUAL`, `status_execucao=CONCLUIDA` (retroativo)
- Tarefas programadas: criadas com `status_execucao=PENDENTE`
- `client_id`, `client_created_at`, `client_updated_at` são nullable para tarefas programadas

---

## Fluxo completo

```
Gestor (apps/web)
  └─ POST /api/v1/campo/tarefas
       └─ TarefaCampo(origem=PROGRAMADA, status_execucao=PENDENTE)

Operador (apps/campo)
  └─ /sync/pull → retorna tarefas data_programada <= hoje AND status_execucao IN (PENDENTE, EM_EXECUCAO)
       └─ IndexedDB via pull.ts
  └─ Home → seções: Em Execução / Atrasadas / Para Hoje
  └─ /campo/tarefa/[id] → "Iniciar" → status_execucao=EM_EXECUCAO
  └─ /campo/tarefa/[id] → "Concluir" + obs + foto + GPS → status_execucao=CONCLUIDA
  └─ /sync/push → payload com status_execucao
       └─ _aplicar_status_execucao() valida regras e atualiza no servidor

Backoffice (apps/web)
  └─ GET /api/v1/campo/tarefas → lista agrupada por status
```

---

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/campo/tarefas` | Cria tarefa programada (backoffice) |
| `GET` | `/api/v1/campo/tarefas` | Lista tarefas do tenant com filtros |
| `GET` | `/api/v1/campo/tarefas/{id}` | Detalhe de uma tarefa |
| `PATCH` | `/api/v1/campo/tarefas/{id}/execucao` | Atualiza execução (backoffice/API) |
| `DELETE` | `/api/v1/campo/tarefas/{id}` | Cancela tarefa |
| `GET` | `/api/v1/sync/pull` | Inclui tarefas programadas para o dispositivo |
| `POST` | `/api/v1/sync/push` | Aceita `status_execucao` no payload de UPDATE |

---

## Arquivos modificados

### Backend
- `campo/models.py` — novos campos em `TarefaCampo`
- `campo/schemas.py` — `TarefaProgramadaCreate`, `TarefaProgramadaResponse`, `ExecucaoUpdate`
- `campo/service.py` — `TarefaProgramadaService`, `_aplicar_status_execucao()`
- `campo/router.py` — endpoints de tarefas programadas
- `migrations/versions/20260508_campo_pwa_05.py` — migration additive

### Frontend PWA (apps/campo)
- `lib/db.ts` — v2 schema com índices + LocalTask novos campos
- `lib/sync/pull.ts` — popula tarefas programadas no IndexedDB
- `lib/task-factory.ts` — `executarTarefa()` para execução offline
- `app/(campo)/home/page.tsx` — 3 seções (Em Execução / Atrasadas / Para Hoje)
- `app/(campo)/campo/tarefa/[id]/page.tsx` — detalhe + Iniciar / Concluir / Cancelar

### Frontend Web (apps/web)
- `app/(dashboard)/dashboard/operacional/campo/tarefas/page.tsx` — lista backoffice
- `components/campo/tarefa-drawer.tsx` — drawer de criação

---

## Critérios de aceite

- [x] Gestor cria tarefa no apps/web → persiste com `origem=PROGRAMADA`
- [x] Tarefa aparece no PWA após sync/pull (data_programada <= hoje)
- [x] Operador inicia offline → `status_execucao=EM_EXECUCAO`, `iniciada_em` preenchido
- [x] Operador conclui offline → `status_execucao=CONCLUIDA`, obs/foto/GPS registrados
- [x] sync/push envia `status_execucao` corretamente para o servidor
- [x] Status atualizado no backoffice após sync
- [x] Tarefas manuais continuam funcionando sem quebra de compatibilidade
