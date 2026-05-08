# Campo PWA-02 — Implementação Backend + Base Frontend

**Data:** 2026-05-08  
**Branch:** `feature/campo-pwa-02-backend-base`  
**Status:** COMPLETO ✅

---

## Commits

| Hash | Descrição |
|------|-----------|
| `503ea1c8` | feat(campo): add DispositivoCampo, TarefaCampo e SyncTombstone models |
| `5af7be7b` | feat(campo-app): setup Next.js PWA base com Dexie, Zustand e sync worker |
| `2221023e` | fix(campo-app): corrige pacote dexie-react-hooks |

---

## Backend — `services/api/campo/`

### Arquivos criados

| Arquivo | Descrição |
|---------|-----------|
| `campo/models.py` | `DispositivoCampo`, `TarefaCampo`, `SyncTombstone` |
| `campo/schemas.py` | Pydantic v2 para devices e sync (pull/push) |
| `campo/service.py` | `DispositivoService` + `SyncService` com lógica de conflito |
| `campo/router.py` | Endpoints `/campo/devices/*` e `/sync/pull`, `/sync/push` |
| `migrations/versions/20260508_campo_pwa.py` | Migration completa das 3 tabelas |

### Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/api/v1/campo/devices` | JWT normal | Cria dispositivo + gera activation_code (TTL 30min) |
| POST | `/api/v1/campo/devices/activate` | Público | Ativa dispositivo → retorna device_token JWT 30 dias |
| POST | `/api/v1/campo/devices/revoke` | JWT normal | Revoga dispositivo imediatamente |
| GET  | `/api/v1/campo/devices` | JWT normal | Lista dispositivos do tenant |
| GET  | `/api/v1/sync/pull` | device_token | Delta pull desde `last_sync_at` |
| POST | `/api/v1/sync/push` | device_token | Push de batch de operações da fila offline |

### Modelos de banco

```
campo_dispositivos       ← registro/ativação/revogação de devices
campo_tarefas            ← tarefas criadas offline (sync'd via push)
campo_sync_tombstones    ← rastreia deleções para tombstone pull
```

### Estratégia de conflito

| Entidade | Estratégia |
|----------|------------|
| CREATE task offline | Client-wins (sempre aceito) |
| UPDATE task APLICACAO* | Last-write-wins por `client_updated_at` |
| UPDATE task outros | Server-wins |
| DELETE | Soft-delete via status=CANCELADA |

---

## Frontend — `apps/campo/`

### Stack

```
Next.js 15 (App Router) + next-pwa
Dexie.js v4 + dexie-react-hooks
Zustand v5
TanStack Query v5
react-hook-form + zod
bcryptjs (hash PIN local)
Tailwind 4
```

### Estrutura de arquivos criados

```
apps/campo/
├─ package.json / tsconfig.json / next.config.ts
├─ public/manifest.json          ← PWA manifest
└─ src/
   ├─ app/
   │  ├─ layout.tsx              ← Root layout (PWA meta)
   │  ├─ page.tsx               ← Redirect → /home
   │  ├─ globals.css
   │  ├─ (auth)/
   │  │  ├─ activate/page.tsx   ← Ativação com código + criação de PIN
   │  │  └─ pin/page.tsx        ← Login por PIN (teclado numérico)
   │  └─ (campo)/
   │     ├─ layout.tsx          ← Guarda de sessão + init sync
   │     ├─ home/page.tsx       ← Hub de tarefas do dia
   │     └─ sync/page.tsx       ← Status de sincronização
   ├─ components/
   │  └─ sync-status-bar.tsx    ← Barra online/offline/pending
   └─ lib/
      ├─ db.ts                  ← Dexie schema (7 stores)
      ├─ stores/
      │  ├─ session-store.ts    ← Zustand: sessão local + PIN auth
      │  └─ sync-store.ts       ← Zustand: status online/offline/sync
      └─ sync/
         ├─ pull.ts             ← GET /sync/pull + atualiza IndexedDB
         ├─ push.ts             ← POST /sync/push + outbox pattern
         └─ worker.ts           ← Orquestrador: retry, listeners online/offline
```

### IndexedDB — 7 stores Dexie

| Store | Conteúdo |
|-------|----------|
| `session` | Sessão local singleton (device_token, pin_hash, módulos) |
| `tasks` | Tarefas de campo (offline-first) |
| `sync_queue` | Fila outbox — toda mutação passa aqui antes do HTTP |
| `fazendas` | Cache de unidades produtivas autorizadas |
| `talhoes` | Cache de talhões (AreaRural tipo=TALHAO) |
| `lotes` | Cache de lotes pecuários (pec_lotes) |
| `insumos` | Cache de produtos/insumos do tenant |

### Fluxo de sincronização

```
Abrir app / Recuperar conexão / Botão manual
         ↓
   worker.runSync()
         ↓
   pushSync() → POST /sync/push (itens PENDING em FIFO)
         ↓
   pullSync() → GET /sync/pull (delta desde last_sync_at)
         ↓
   IndexedDB atualizado (bulkPut + tombstones)
```

### Retry / Quarentena

- `IN_FLIGHT` → resetado para `PENDING` ao reabrir app (crash recovery)
- `attempts >= 5` → status `FAILED` (quarentena, não bloqueia outros)
- Background Sync API **não** implementado neste step (decisão PWA-01)

---

## Validações

| Check | Resultado |
|-------|-----------|
| `py_compile` campo/*.py | ✅ OK |
| `py_compile` migration | ✅ OK |
| `tsc --noEmit` apps/campo | ✅ 0 erros |
| Isolamento de tenant | ✅ Todos os queries filtram por `tenant_id` |
| Device token distinto de user JWT | ✅ `payload.type == "device"` validado |

---

## Como usar

### 1. Rodar migration

```bash
cd services/api
alembic upgrade head
```

### 2. Criar dispositivo (via API ou frontend web)

```bash
curl -X POST /api/v1/campo/devices \
  -H "Authorization: Bearer {user_token}" \
  -d '{"nome": "iPad João", "user_id": "...", "fazenda_ids": ["..."], "modulos": ["agricola"]}'
# Retorna: activation_code = "ABCD1234" (válido 30 min)
```

### 3. Ativar no dispositivo

```
Abrir apps/campo → /activate
Inserir código ABCD1234 + criar PIN
→ device_token salvo localmente no IndexedDB
```

### 4. Iniciar app campo

```bash
cd apps/campo
cp .env.local.example .env.local
pnpm dev   # porta 3002
```

---

## Próximo step: PWA-03

- Formulários de campo: aplicação, colheita, pesagem, vacinação
- Camera capture + GPS
- Integração do outbox com formulários
- Testes E2E offline/online
