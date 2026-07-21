import { create } from "zustand";
import { db, type LocalSession } from "@/lib/db";
import bcrypt from "bcryptjs";

const API_BASE = "/api/v1";

export type SessionClearReason =
  | "DEVICE_REVOKED"
  | "SESSION_INVALID"
  | "TENANT_CHANGED"
  | "USER_CHANGED"
  | "MANUAL_LOGOUT";

export interface LocalPendingSummary {
  syncQueue: number;
  tasks: number;
  cadernoEvents: number;
  cadernoDrafts: number;
  total: number;
}

export interface SessionClearNotice {
  reason: SessionClearReason;
  summary: LocalPendingSummary;
  clearedAt: string;
}

const SESSION_CLEAR_NOTICE_KEY = "campo:session-clear-notice";

// Caches HTTP (Workbox/next-pwa) conhecidos por poderem conter respostas
// autenticadas de API. Não inclui caches de assets estáticos (precache do SW).
const AUTHENTICATED_RUNTIME_CACHE_NAMES = ["campo-api-cache"];

interface SessionState {
  session: LocalSession | null;
  isAuthenticated: boolean;
  loadSession: () => Promise<void>;
  loginWithPIN: (pin: string) => Promise<boolean>;
  logout: () => Promise<void>;
  clearSession: (reason?: SessionClearReason) => Promise<void>;
  saveSession: (session: LocalSession) => Promise<void>;
  updateLastSync: (timestamp: string) => Promise<void>;
  validateDeviceSession: () => Promise<boolean>;
  setActiveFazenda: (fazendaId: string) => Promise<void>;
}

// INVARIANTE DE SEGURANÇA: `tasks` e `sync_queue` não armazenam `tenant_id`.
// O backend deduplica por `client_id` dentro do tenant do token atual, mas não
// tem como saber que um item `CREATE` enfileirado pertence ao contexto
// operacional de uma sessão/tenant anterior — um item órfão reenviado sob um
// token novo seria aceito como dado legítimo do tenant autenticado no momento
// do envio. Por isso, limpar todas as tabelas de cache/fila ANTES de trocar
// de sessão (tenant ou usuário) é obrigatório, não uma otimização. Esta
// função é o único ponto central dessa limpeza — não a remova, não a
// desloque para depois da gravação da nova sessão, e não a substitua por
// chamadas .clear() individuais espalhadas pelo código. Toda nova tabela
// local que carregue dados vinculados a um tenant/usuário deve ser incluída
// aqui.
async function clearCacheTables(): Promise<void> {
  await db.transaction(
    "rw",
    [
      db.tasks,
      db.sync_queue,
      db.caderno_events,
      db.caderno_server_events,
      db.caderno_drafts,
      db.fazendas,
      db.talhoes,
      db.lotes,
      db.animais,
      db.insumos,
      db.safras,
      db.colaboradores,
      db.recomendacoes_climaticas,
      db.recomendacoes_operacionais,
      db.pessoas_operacionais,
    ],
    async () => {
      await Promise.all([
        db.tasks.clear(),
        db.sync_queue.clear(),
        db.caderno_events.clear(),
        db.caderno_server_events.clear(),
        db.caderno_drafts.clear(),
        db.fazendas.clear(),
        db.talhoes.clear(),
        db.lotes.clear(),
        db.animais.clear(),
        db.insumos.clear(),
        db.safras.clear(),
        db.colaboradores.clear(),
        db.recomendacoes_climaticas.clear(),
        db.recomendacoes_operacionais.clear(),
        db.pessoas_operacionais.clear(),
      ]);
    }
  );
}

// Conta trabalho local que ainda não chegou a um estado terminal/sincronizado
// e seria destruído por clearCacheTables(). Usada só para informar o usuário
// — nunca para decidir se a limpeza acontece (a limpeza é sempre obrigatória).
export async function getLocalPendingSummary(): Promise<LocalPendingSummary> {
  const [syncQueue, tasks, cadernoEvents, cadernoDrafts] = await Promise.all([
    db.sync_queue.where("status").notEqual("DONE").count(),
    db.tasks.filter((task) => task.synced !== true).count(),
    db.caderno_events.where("sync_status").notEqual("SYNCED").count(),
    db.caderno_drafts.count(),
  ]);

  return {
    syncQueue,
    tasks,
    cadernoEvents,
    cadernoDrafts,
    total: syncQueue + tasks + cadernoEvents + cadernoDrafts,
  };
}

function writeSessionClearNotice(reason: SessionClearReason, summary: LocalPendingSummary): void {
  if (typeof sessionStorage === "undefined") return;
  try {
    const notice: SessionClearNotice = { reason, summary, clearedAt: new Date().toISOString() };
    sessionStorage.setItem(SESSION_CLEAR_NOTICE_KEY, JSON.stringify(notice));
  } catch {
    // sessionStorage indisponível/cheio não pode impedir a limpeza de segurança.
  }
}

// Lê e consome (remove) o aviso transitório de limpeza, se houver. Deve ser
// chamado uma única vez pela tela que recebe o usuário após a troca de
// sessão (ex.: activate ou home). Não contém payload de negócio — apenas
// contagens e o motivo da limpeza.
export function consumeSessionClearNotice(): SessionClearNotice | null {
  if (typeof sessionStorage === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SESSION_CLEAR_NOTICE_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(SESSION_CLEAR_NOTICE_KEY);
    return JSON.parse(raw) as SessionClearNotice;
  } catch {
    return null;
  }
}

// Remove caches HTTP autenticados criados pelo Service Worker (Workbox).
// Best-effort: nunca lança — uma falha aqui não pode impedir a limpeza do
// Dexie/sessão, que é a proteção primária.
async function clearAuthenticatedRuntimeCaches(): Promise<void> {
  if (typeof caches === "undefined") return;
  await Promise.all(
    AUTHENTICATED_RUNTIME_CACHE_NAMES.map((name) =>
      caches.delete(name).catch(() => {
        // Falha tolerada — não bloqueia logout/troca de sessão.
      })
    )
  );
}

function normalizeSession(session: LocalSession): LocalSession {
  const allowed = session.fazenda_ids ?? [];
  const active =
    session.active_fazenda_id && allowed.includes(session.active_fazenda_id)
      ? session.active_fazenda_id
      : allowed[0];

  return {
    ...session,
    active_fazenda_id: active,
  };
}

export const useSessionStore = create<SessionState>((set, get) => ({
  session: null,
  isAuthenticated: false,

  loadSession: async () => {
    const rawSession = await db.session.get(1);
    if (rawSession) {
      const session = normalizeSession(rawSession);
      if (session.active_fazenda_id !== rawSession.active_fazenda_id) {
        await db.session.put(session);
      }
      set({ session });
    } else {
      set({ session: null, isAuthenticated: false });
    }
  },

  validateDeviceSession: async () => {
    const rawSession = await db.session.get(1);
    if (!rawSession) return false;
    const session = normalizeSession(rawSession);

    // O app de campo precisa continuar utilizável offline.
    // Só descartamos a sessão local quando o backend confirma
    // que o dispositivo/token não é mais válido.
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      set({ session });
      return true;
    }

    try {
      const res = await fetch(`${API_BASE}/campo/devices/me?device_id=${session.device_id}`, {
        headers: {
          Authorization: `Bearer ${session.device_token}`,
        },
      });

      if (res.ok) {
        set({ session });
        return true;
      }

      if (res.status === 401 || res.status === 403 || res.status === 404) {
        await get().clearSession("DEVICE_REVOKED");
        return false;
      }

      set({ session });
      return true;
    } catch {
      set({ session });
      return true;
    }
  },

  loginWithPIN: async (pin: string) => {
    const rawSession = await db.session.get(1);
    if (!rawSession) return false;
    const session = normalizeSession(rawSession);

    const validDevice = await get().validateDeviceSession();
    if (!validDevice) return false;

    const valid = await bcrypt.compare(pin, session.pin_hash);
    if (valid) {
      set({ session, isAuthenticated: true });
    }
    return valid;
  },

  logout: async () => {
    await get().clearSession("MANUAL_LOGOUT");
  },

  clearSession: async (reason: SessionClearReason = "SESSION_INVALID") => {
    // 1. contar pendências (antes de qualquer limpeza)
    const summary = await getLocalPendingSummary();
    // 2. limpar Dexie em transação
    await clearCacheTables();
    // 3. remover sessão
    await db.session.delete(1);
    // 4. limpar caches HTTP autenticados (best-effort, não bloqueia o fluxo)
    await clearAuthenticatedRuntimeCaches();
    if (summary.total > 0) {
      writeSessionClearNotice(reason, summary);
    }
    // 5. resetar estado Zustand
    set({ session: null, isAuthenticated: false });
  },

  saveSession: async (session: LocalSession) => {
    const previous = await db.session.get(1);
    const tenantChanged = !!previous && previous.tenant_id !== session.tenant_id;
    const userChanged = !!previous && previous.user_id !== session.user_id;

    if (tenantChanged || userChanged) {
      const summary = await getLocalPendingSummary();
      await clearCacheTables();
      await clearAuthenticatedRuntimeCaches();
      if (summary.total > 0) {
        writeSessionClearNotice(tenantChanged ? "TENANT_CHANGED" : "USER_CHANGED", summary);
      }
    }

    const normalized = normalizeSession(session);
    await db.session.put(normalized);
    set({ session: normalized, isAuthenticated: true });
  },

  updateLastSync: async (timestamp: string) => {
    const session = get().session;
    if (!session) return;
    const updated = { ...session, last_sync_at: timestamp };
    await db.session.put(updated);
    set({ session: updated });
  },

  setActiveFazenda: async (fazendaId: string) => {
    const session = get().session;
    if (!session) return;
    if (!session.fazenda_ids.includes(fazendaId)) return;

    const updated = {
      ...session,
      active_fazenda_id: fazendaId,
    };
    await db.session.put(updated);
    set({ session: updated });
  },
}));
