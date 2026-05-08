import { create } from "zustand";
import { db, type LocalSession } from "@/lib/db";
import bcrypt from "bcryptjs";

interface SessionState {
  session: LocalSession | null;
  isAuthenticated: boolean;
  loadSession: () => Promise<void>;
  loginWithPIN: (pin: string) => Promise<boolean>;
  logout: () => Promise<void>;
  saveSession: (session: LocalSession) => Promise<void>;
  updateLastSync: (timestamp: string) => Promise<void>;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  session: null,
  isAuthenticated: false,

  loadSession: async () => {
    const session = await db.session.get(1);
    if (session) {
      set({ session });
    }
  },

  loginWithPIN: async (pin: string) => {
    const session = await db.session.get(1);
    if (!session) return false;
    const valid = await bcrypt.compare(pin, session.pin_hash);
    if (valid) {
      set({ session, isAuthenticated: true });
    }
    return valid;
  },

  logout: async () => {
    set({ isAuthenticated: false });
  },

  saveSession: async (session: LocalSession) => {
    await db.session.put(session);
    set({ session, isAuthenticated: true });
  },

  updateLastSync: async (timestamp: string) => {
    const session = get().session;
    if (!session) return;
    const updated = { ...session, last_sync_at: timestamp };
    await db.session.put(updated);
    set({ session: updated });
  },
}));
