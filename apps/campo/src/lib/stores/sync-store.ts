import { create } from "zustand";

export type SyncStatus = "idle" | "syncing" | "success" | "error";

interface SyncState {
  status: SyncStatus;
  isOnline: boolean;
  pendingCount: number;
  lastSyncAt: string | null;
  lastError: string | null;
  setSyncStatus: (status: SyncStatus, error?: string) => void;
  setOnline: (online: boolean) => void;
  setPendingCount: (count: number) => void;
  setLastSyncAt: (ts: string) => void;
}

export const useSyncStore = create<SyncState>((set) => ({
  status: "idle",
  isOnline: typeof navigator !== "undefined" ? navigator.onLine : true,
  pendingCount: 0,
  lastSyncAt: null,
  lastError: null,

  setSyncStatus: (status, error) =>
    set({ status, lastError: error ?? null }),

  setOnline: (online) => set({ isOnline: online }),

  setPendingCount: (count) => set({ pendingCount: count }),

  setLastSyncAt: (ts) => set({ lastSyncAt: ts }),
}));
