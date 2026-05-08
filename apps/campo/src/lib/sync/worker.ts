"use client";

import { pullSync } from "./pull";
import { pushSync } from "./push";
import { useSyncStore } from "@/lib/stores/sync-store";
import { db } from "@/lib/db";

let _syncInProgress = false;
let _onlineListener: (() => void) | null = null;
let _offlineListener: (() => void) | null = null;

export async function runSync(): Promise<void> {
  if (_syncInProgress) return;
  if (!navigator.onLine) {
    useSyncStore.getState().setSyncStatus("idle");
    return;
  }

  _syncInProgress = true;
  useSyncStore.getState().setSyncStatus("syncing");

  try {
    await pushSync();
    await pullSync();

    const pending = await db.sync_queue.where("status").equals("PENDING").count();
    useSyncStore.getState().setPendingCount(pending);
    useSyncStore.getState().setLastSyncAt(new Date().toISOString());
    useSyncStore.getState().setSyncStatus("success");
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Erro desconhecido";
    useSyncStore.getState().setSyncStatus("error", msg);
    console.error("[sync/worker] Erro:", msg);
  } finally {
    _syncInProgress = false;
  }
}

export function initSyncListeners(): () => void {
  const store = useSyncStore.getState();

  _onlineListener = () => {
    store.setOnline(true);
    // Ao recuperar conexão, sincroniza automaticamente
    runSync();
  };

  _offlineListener = () => {
    store.setOnline(false);
    store.setSyncStatus("idle");
  };

  window.addEventListener("online", _onlineListener);
  window.addEventListener("offline", _offlineListener);

  // Sync inicial ao montar
  runSync();

  // Atualiza contagem de pendentes
  refreshPendingCount();

  return () => {
    if (_onlineListener) window.removeEventListener("online", _onlineListener);
    if (_offlineListener) window.removeEventListener("offline", _offlineListener);
  };
}

export async function refreshPendingCount(): Promise<void> {
  const count = await db.sync_queue.where("status").anyOf(["PENDING", "IN_FLIGHT"]).count();
  useSyncStore.getState().setPendingCount(count);
}
