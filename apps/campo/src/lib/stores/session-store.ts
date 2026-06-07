import { create } from "zustand";
import { db, type LocalSession } from "@/lib/db";
import bcrypt from "bcryptjs";

const API_BASE = "/api/v1";

interface SessionState {
  session: LocalSession | null;
  isAuthenticated: boolean;
  loadSession: () => Promise<void>;
  loginWithPIN: (pin: string) => Promise<boolean>;
  logout: () => Promise<void>;
  clearSession: () => Promise<void>;
  saveSession: (session: LocalSession) => Promise<void>;
  updateLastSync: (timestamp: string) => Promise<void>;
  validateDeviceSession: () => Promise<boolean>;
  setActiveFazenda: (fazendaId: string) => Promise<void>;
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
        await db.session.delete(1);
        set({ session: null, isAuthenticated: false });
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
    await get().clearSession();
  },

  clearSession: async () => {
    await db.session.delete(1);
    set({ session: null, isAuthenticated: false });
  },

  saveSession: async (session: LocalSession) => {
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
