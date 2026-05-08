# Campo PWA-01 — Arquitetura Offline-First

**Versão:** 1.0  
**Data:** 2026-05-08  
**Autor:** Borgus Software Ltda  
**Status:** RASCUNHO — Aguardando validação

---

## 1. Visão Geral

O **Campo PWA** é uma aplicação Progressive Web App (PWA) offline-first destinada a operadores de campo (tratoristas, auxiliares, veterinários, agrônomos) que trabalham em áreas rurais com conectividade instável ou inexistente.

### 1.1 Princípios de Design

| Princípio | Descrição |
|-----------|-----------|
| **Offline-first** | Toda operação funciona sem internet; a sincronização é eventual |
| **Device-bound** | Cada dispositivo é registrado e identificado; sem compartilhamento de tokens |
| **PIN-auth** | Operadores autenticam com PIN local de 4–6 dígitos (não exige senha de rede) |
| **Outbox pattern** | Mutações são gravadas na fila local antes de qualquer chamada HTTP |
| **Server-wins** | Conflitos de sincronização resolvidos pelo servidor por padrão |
| **Delta sync** | Pull traz apenas o diff desde o último sync (header `last_sync_at`) |

---

## 2. Stack Técnica

```
apps/campo/                     ← novo workspace pnpm
├─ Next.js 16 App Router (PWA)
├─ Dexie.js v4                  ← wrapper tipado para IndexedDB
├─ @dexie/react-hooks           ← liveQuery integrado com React
├─ Workbox (via next-pwa)        ← Service Worker + precaching
├─ Zustand                      ← estado de sessão local
├─ TanStack Query v5             ← cache de dados + retry automático
├─ react-hook-form + zod        ← formulários offline
└─ Tailwind 4 + shadcn/ui       ← UI consistente com web/backoffice
```

**Backend (novo módulo em `services/api/campo/`):**
```
FastAPI + SQLAlchemy 2.0 async
├─ /campo/devices        ← registro e revogação de dispositivos
├─ /sync/pull            ← delta pull por fazenda/dispositivo
└─ /sync/push            ← push de fila de sincronização
```

---

## 3. IndexedDB — Schema Dexie

```typescript
// apps/campo/src/lib/db.ts
import Dexie, { type Table } from "dexie";

export interface LocalSession {
  id: 1; // singleton
  user_id: string;
  tenant_id: string;
  device_id: string;
  device_token: string;        // JWT longo (30 dias)
  pin_hash: string;            // bcrypt do PIN local
  user_name: string;
  last_sync_at: string | null; // ISO timestamp
  modules: string[];           // ["agricola", "pecuaria"]
}

export interface LocalTask {
  id: string;                   // UUID gerado localmente (crypto.randomUUID)
  server_id?: string;           // UUID do servidor após sync confirmado
  type: TaskType;
  module: "agricola" | "pecuaria";
  fazenda_id: string;
  talhao_id?: string;           // agricola
  lote_id?: string;             // pecuaria
  operador_id: string;
  status: "PENDENTE" | "EM_ANDAMENTO" | "CONCLUIDA" | "CANCELADA";
  dados: Record<string, unknown>;
  fotos?: string[];             // base64 ou blob URL
  created_at: string;           // ISO
  updated_at: string;           // ISO
  synced: boolean;
  sync_conflict?: string;       // mensagem de conflito se houver
}

export interface SyncQueueItem {
  id: string;                   // UUID local
  operation: "CREATE" | "UPDATE" | "DELETE";
  entity_type: string;          // "task" | "pesagem" | "aplicacao" | etc
  entity_id: string;            // LocalTask.id
  server_id?: string;           // se já sincronizado antes
  payload: Record<string, unknown>;
  created_at: string;
  attempts: number;
  last_error?: string;
  status: "PENDING" | "IN_FLIGHT" | "DONE" | "FAILED";
}

// Entidades cacheadas do servidor (read-only local)
export interface CachedFazenda {
  id: string;
  nome: string;
  tenant_id: string;
}

export interface CachedTalhao {
  id: string;
  nome: string;
  area_ha: number;
  fazenda_id: string;
  cultivo_atual?: string;
}

export interface CachedLote {
  id: string;
  codigo: string;
  especie: string;
  quantidade: number;
  fazenda_id: string;
}

export interface CachedInsumo {
  id: string;
  nome: string;
  unidade: string;
  categoria: string;
}

export class CampoDatabase extends Dexie {
  session!: Table<LocalSession>;
  tasks!: Table<LocalTask>;
  sync_queue!: Table<SyncQueueItem>;
  fazendas!: Table<CachedFazenda>;
  talhoes!: Table<CachedTalhao>;
  lotes!: Table<CachedLote>;
  insumos!: Table<CachedInsumo>;

  constructor() {
    super("campo_db");
    this.version(1).stores({
      session:    "id",
      tasks:      "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      fazendas:   "id",
      talhoes:    "id, fazenda_id",
      lotes:      "id, fazenda_id",
      insumos:    "id, categoria",
    });
  }
}

export const db = new CampoDatabase();
```

---

## 4. Modelo de Tarefas

### 4.1 Tipos de Tarefa

```typescript
export type TaskType =
  // Agricultura
  | "APLICACAO_DEFENSIVO"
  | "APLICACAO_FERTILIZANTE"
  | "COLHEITA_REGISTRO"
  | "PREPARO_SOLO"
  | "PLANTIO_REGISTRO"
  | "IRRIGACAO_EVENTO"
  | "MONITORAMENTO_PRAGA"
  | "AMOSTRAGEM_SOLO"
  // Pecuária
  | "PESAGEM_ANIMAL"
  | "VACINACAO_LOTE"
  | "MEDICACAO_ANIMAL"
  | "MOVIMENTACAO_LOTE"
  | "PARTO_REGISTRO"
  | "MORTE_REGISTRO"
  | "INSEMINACAO"
  // Geral
  | "ABASTECIMENTO_MAQUINA"
  | "MANUTENCAO_OCORRENCIA"
  | "CHECKLIST_CAMPO";
```

### 4.2 Payloads por Tipo (exemplos)

```typescript
// APLICACAO_DEFENSIVO
interface DadosAplicacao {
  insumo_id: string;
  dose_ha: number;
  unidade: string;
  area_aplicada_ha: number;
  equipamento?: string;
  operador_aplicador?: string;
  condicoes_clima?: "BOM" | "NUBLADO" | "VENTO_LEVE" | "VENTO_FORTE";
  obs?: string;
}

// PESAGEM_ANIMAL
interface DadosPesagem {
  animal_id?: string;           // pesagem individual
  lote_id?: string;             // pesagem de lote
  peso_kg: number;
  tipo: "INDIVIDUAL" | "AMOSTRA" | "LOTE_BALANCA";
  balanca_id?: string;
  obs?: string;
}

// COLHEITA_REGISTRO
interface DadosColheita {
  talhao_id: string;
  cultura: string;
  produtividade_sc_ha?: number;
  umidade_perc?: number;
  area_colhida_ha: number;
  maquina_id?: string;
  obs?: string;
}
```

---

## 5. Modelo de Fila de Sincronização (Outbox Pattern)

```
Operação Local              IndexedDB                    Backend
     │                          │                            │
     ├─ CREATE task ────────────►│                            │
     ├─ ADD to sync_queue ───────►│                            │
     │                          │                            │
     │         [conectividade disponível]                    │
     │                          │                            │
     │               SyncWorker.push() ──────────────────────►│
     │                          │         POST /sync/push    │
     │                          │◄──────────────────────────── result[]
     │               mark DONE ──►│                            │
     │               update server_id ─►│                    │
```

### 5.1 Regras da Fila

1. **Toda mutação** passa pela fila — sem exceções
2. Itens `FAILED` com `attempts >= 5` ficam em quarentena (não bloqueiam outros)
3. A fila é processada em ordem de `created_at` (FIFO)
4. Operações `DELETE` de entidades não-sincronizadas são resolvidas localmente (sem push)
5. `IN_FLIGHT` é resetado para `PENDING` no restart do app (evita travamento)

### 5.2 Resultado do Push

```typescript
// Resposta do servidor para cada item da fila
interface SyncPushResult {
  local_id: string;
  status: "CREATED" | "UPDATED" | "CONFLICT" | "ERROR";
  server_id?: string;
  server_data?: Record<string, unknown>; // dados com conflito resolvido
  error_message?: string;
}
```

---

## 6. Controle de Acesso — PIN + Device

### 6.1 Fluxo de Registro de Dispositivo

```
Gerente/Admin (web)              Backend                   Dispositivo Campo
       │                            │                              │
       ├─ POST /campo/devices ───────►│                              │
       │  { fazenda_ids, user_id,    │                              │
       │    expires_in: "30d" }      │                              │
       │◄─ { activation_code: "XYZW" }│                              │
       │                            │                              │
       │                            │◄── POST /campo/devices/activate
       │                            │    { activation_code, pin }  │
       │                            ├─────────────────────────────►│
       │                            │    { device_token, payload } │
       │                            │     (JWT 30 dias)            │
```

### 6.2 Autenticação Local com PIN

```typescript
// PIN nunca sai do dispositivo
async function loginWithPIN(pin: string): Promise<boolean> {
  const session = await db.session.get(1);
  if (!session) return false;
  
  // bcrypt local — sem chamada de rede
  const valid = await bcrypt.compare(pin, session.pin_hash);
  if (!valid) return false;
  
  // Carrega sessão em Zustand
  useSessionStore.getState().setSession(session);
  return true;
}

// Troca de PIN (requer conexão para audit log)
async function changePIN(old_pin: string, new_pin: string): Promise<void> {
  const valid = await loginWithPIN(old_pin);
  if (!valid) throw new Error("PIN incorreto");
  const hash = await bcrypt.hash(new_pin, 10);
  await db.session.update(1, { pin_hash: hash });
  // Registrar troca no servidor quando online
  enqueueSync("UPDATE", "device_pin", { pin_changed_at: new Date().toISOString() });
}
```

### 6.3 Modelo de Dados — Backend

```python
# services/api/campo/models.py

class DispositivoCampo(Base):
    __tablename__ = "dispositivos_campo"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    
    nome: Mapped[str] = mapped_column(String(100))           # "iPad do João"
    device_fingerprint: Mapped[str] = mapped_column(String(256), unique=True)
    activation_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="ATIVO")  # ATIVO | REVOGADO
    
    fazenda_ids: Mapped[list[str]] = mapped_column(ARRAY(UUID))  # fazendas acessíveis
    modulos: Mapped[list[str]] = mapped_column(ARRAY(String))    # ["agricola", "pecuaria"]
    
    last_sync_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)
    
    expires_at: Mapped[datetime] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_dispositivos_tenant_user", tenant_id, user_id),
        Index("ix_dispositivos_status", status),
    )
```

---

## 7. Endpoints de Sincronização

### 7.1 `GET /sync/pull`

Retorna o delta de todas as entidades acessíveis pelo dispositivo desde `last_sync_at`.

**Query params:**
```
device_id     UUID   obrigatório
last_sync_at  ISO    opcional (null = sync inicial completo)
fazenda_ids   UUID[] opcional (filtro adicional)
```

**Response:**
```json
{
  "sync_at": "2026-05-08T14:30:00Z",
  "fazendas": [...],
  "talhoes": [...],
  "lotes": [...],
  "insumos": [...],
  "tarefas_pendentes": [...],
  "tombstones": {
    "talhoes": ["uuid1", "uuid2"],
    "lotes": []
  }
}
```

**Regras:**
- Verifica `DispositivoCampo.status == "ATIVO"` e `expires_at > now()`
- Filtra apenas entidades das `fazenda_ids` do dispositivo
- Tombstones indicam registros deletados desde o último sync
- Tamanho máximo de payload: 5 MB por pull (paginação por `cursor` se necessário)

### 7.2 `POST /sync/push`

Recebe o batch de operações da fila local.

**Body:**
```json
{
  "device_id": "uuid",
  "last_sync_at": "2026-05-08T12:00:00Z",
  "items": [
    {
      "local_id": "uuid-local",
      "operation": "CREATE",
      "entity_type": "task",
      "payload": { ... },
      "created_at": "2026-05-08T10:00:00Z",
      "client_updated_at": "2026-05-08T10:05:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "processed_at": "2026-05-08T14:30:05Z",
  "results": [
    { "local_id": "...", "status": "CREATED", "server_id": "..." },
    { "local_id": "...", "status": "CONFLICT", "server_data": { ... } }
  ]
}
```

---

## 8. Regras de Conflito

### 8.1 Estratégia Padrão: Server-Wins

Para a maioria das entidades, o servidor é autoritativo:

```
client_updated_at < server_updated_at  →  server_data sobrescreve local
client_updated_at >= server_updated_at →  client_data aceito (merge otimista)
```

### 8.2 Exceções por Tipo de Entidade

| Entidade | Estratégia | Motivo |
|----------|------------|--------|
| `task` (CREATE offline) | **Client-wins** | Registro de campo válido independente |
| `pesagem` | **Server-wins** | Dados históricos imutáveis após sync |
| `vacinacao` | **Server-wins** | Rastreabilidade sanitária |
| `aplicacao` | **Last-write-wins** por `updated_at` | Ajustes de dose são frequentes |
| Entidades de referência (talhão, lote) | **Server-wins** | Cadastro master controlado |

### 8.3 Tombstones

- Servidor mantém tabela `sync_tombstones(entity_type, entity_id, deleted_at, tenant_id)`
- Pull retorna tombstones desde `last_sync_at`
- Cliente remove entidades locais e cancela itens da fila para esse `entity_id`

### 8.4 Conflito Irresolvível

Quando o servidor detecta conflito sem estratégia clara:
1. Grava `status: "CONFLICT"` no resultado do push
2. Devolve `server_data` para o cliente
3. Cliente armazena em `LocalTask.sync_conflict`
4. UI apresenta badge "Conflito" com opção de revisão manual

---

## 9. Escopo do MVP

### 9.1 Funcionalidades Incluídas

**Autenticação & Dispositivo:**
- [ ] Registro de dispositivo via código de ativação (web)
- [ ] Login por PIN (4–6 dígitos)
- [ ] Troca de PIN offline (sync de audit quando online)
- [ ] Sessão persiste entre restarts do app

**Sincronização:**
- [ ] Pull inicial completo no primeiro login
- [ ] Delta pull (manual "Sincronizar agora" + automático quando online)
- [ ] Push da fila com retry automático (3 tentativas, backoff exponencial)
- [ ] Indicador de status de sync na UI (online/offline/pendente/sincronizado)

**Módulo Agrícola (MVP):**
- [ ] Registro de aplicação de defensivo/fertilizante
- [ ] Registro de colheita (parcial e final)
- [ ] Monitoramento de pragas/doenças (foto + descrição)
- [ ] Checklist de campo customizável

**Módulo Pecuário (MVP):**
- [ ] Registro de pesagem (individual e lote)
- [ ] Registro de vacinação por lote
- [ ] Registro de parto
- [ ] Movimentação de lote entre piquetes

**UI/UX:**
- [ ] PWA instalável (manifest + Service Worker)
- [ ] Interface touch-first (botões grandes, formulários simplificados)
- [ ] Modo noturno (operações em madrugada)
- [ ] Câmera integrada para fotos de campo
- [ ] GPS automático nos registros (lat/lon)

### 9.2 Fora do MVP (Backlog)

- Integração com balança eletrônica (Bluetooth/BLE)
- Sincronização em background (Background Sync API)
- Push notifications para tarefas pendentes
- Modo multi-usuário no mesmo dispositivo
- Assinatura digital de laudos
- Integração com maquinário (CAN Bus / telemetria)
- Suporte offline para módulos: financeiro, estoque, frota

---

## 10. Arquitetura de Componentes Frontend

```
apps/campo/src/
├─ app/
│  ├─ (auth)/
│  │  ├─ activate/page.tsx        ← código de ativação
│  │  └─ pin/page.tsx             ← login por PIN
│  ├─ (campo)/
│  │  ├─ layout.tsx               ← verifica sessão local
│  │  ├─ home/page.tsx            ← hub de tarefas do dia
│  │  ├─ agricola/
│  │  │  ├─ aplicacao/page.tsx
│  │  │  ├─ colheita/page.tsx
│  │  │  └─ monitoramento/page.tsx
│  │  ├─ pecuaria/
│  │  │  ├─ pesagem/page.tsx
│  │  │  ├─ vacinacao/page.tsx
│  │  │  └─ parto/page.tsx
│  │  └─ sync/page.tsx            ← status e histórico de sync
├─ lib/
│  ├─ db.ts                       ← Dexie schema (seção 3)
│  ├─ sync/
│  │  ├─ pull.ts                  ← GET /sync/pull
│  │  ├─ push.ts                  ← POST /sync/push
│  │  └─ worker.ts                ← orquestrador de sync
│  └─ stores/
│     ├─ session-store.ts         ← Zustand: sessão local
│     └─ sync-store.ts            ← Zustand: status de sync
├─ components/
│  ├─ sync-status-bar.tsx         ← barra online/offline/pending
│  ├─ task-card.tsx               ← card de tarefa pendente
│  ├─ camera-capture.tsx          ← captura de foto
│  └─ gps-field.tsx               ← captura automática de coordenadas
└─ hooks/
   ├─ useSync.ts                  ← trigger manual + status
   ├─ useOfflineTasks.ts          ← liveQuery Dexie
   └─ useNetworkStatus.ts         ← navigator.onLine + event listeners
```

---

## 11. Backend — Estrutura de Arquivos

```
services/api/campo/
├─ __init__.py
├─ models.py              ← DispositivoCampo, SyncTombstone
├─ schemas.py             ← DeviceCreate, SyncPullResponse, SyncPushRequest
├─ service.py             ← DispositivoService, SyncService
└─ router.py              ← /campo/devices, /sync/pull, /sync/push

migrations/versions/
└─ XXX_campo_devices_sync.py
```

---

## 12. Plano de Implementação

### Fase 1 — Backend (Estimativa: 8h)
1. `campo/models.py` — DispositivoCampo + SyncTombstone + migration
2. `campo/service.py` — registro, ativação, revogação de dispositivos
3. `sync/service.py` — lógica de pull delta + push com conflict resolution
4. `campo/router.py` — endpoints `/campo/devices/*` e `/sync/*`
5. Registrar routers em `main.py`
6. Testes de isolamento de tenant para sync

### Fase 2 — Frontend base (Estimativa: 12h)
1. Criar workspace `apps/campo` com next-pwa + Dexie
2. Schema IndexedDB completo (`db.ts`)
3. Fluxo de ativação de dispositivo
4. Tela de PIN login
5. `sync/worker.ts` — pull + push com retry
6. `sync-status-bar` + `useNetworkStatus`

### Fase 3 — Tarefas Agrícolas MVP (Estimativa: 10h)
1. Formulários de aplicação, colheita, monitoramento
2. Home hub com tarefas do dia
3. Camera + GPS nos formulários
4. Outbox pattern integrado a cada formulário

### Fase 4 — Tarefas Pecuárias MVP (Estimativa: 8h)
1. Formulários de pesagem, vacinação, parto
2. Seleção de lote offline (cached)
3. Integração com outbox

**Total estimado MVP:** ~38h

---

## 13. Perguntas em Aberto

1. **Tamanho do payload de fotos:** limitar a 2 fotos por tarefa no MVP? Ou usar upload separado via presigned URL quando online?
2. **Expiração do device_token:** 30 dias está alinhado com a política de segurança?
3. **Módulos habilitados por dispositivo:** o gerente configura quais módulos cada dispositivo acessa, ou segue o plano do tenant?
4. **Sync automático em background:** priorizar Background Sync API (Service Worker) ou apenas sync manual + ao abrir o app?
5. **GPS obrigatório:** bloquear registro se GPS indisponível, ou permitir sem coordenadas?

---

*Próximo documento: `CAMPO_PWA_02_IMPLEMENTACAO_BACKEND.md`*
