"use client";

import { pullSync } from "./pull";
import { pushSync } from "./push";
import { useSyncStore } from "@/lib/stores/sync-store";
import { db } from "@/lib/db";
import { logger } from "@/lib/logger";

let _syncInProgress = false;
let _onlineListener: (() => void) | null = null;
let _offlineListener: (() => void) | null = null;

export async function runSync(): Promise<void> {
  if (_syncInProgress) {
    logger.debug("SyncWorker", "Sync já em andamento, ignorando");
    return;
  }
  if (!navigator.onLine) {
    useSyncStore.getState().setSyncStatus("idle");
    return;
  }

  _syncInProgress = true;
  useSyncStore.getState().setSyncStatus("syncing");
  const start = Date.now();
  logger.info("SyncWorker", "Iniciando sync");

  try {
    await pushSync();
    logger.info("SyncWorker", "Push concluído");

    await pullSync();
    logger.info("SyncWorker", "Pull concluído", { ms: Date.now() - start });

    const pending = await db.sync_queue.where("status").equals("PENDING").count();
    const failed = await db.sync_queue.where("status").equals("FAILED").count();

    useSyncStore.getState().setPendingCount(pending);
    useSyncStore.getState().setLastSyncAt(new Date().toISOString());
    useSyncStore.getState().setSyncStatus("success");

    if (failed > 0) {
      logger.warn("SyncWorker", `${failed} item(s) em quarentena (FAILED)`);
    }
    logger.info("SyncWorker", `Sync OK em ${Date.now() - start}ms`, { pending, failed });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Erro desconhecido";
    logger.error("SyncWorker", "Falha no sync", { msg, ms: Date.now() - start });
    useSyncStore.getState().setSyncStatus("error", msg);
  } finally {
    _syncInProgress = false;
  }
}

export function initSyncListeners(): () => void {
  const store = useSyncStore.getState();

  _onlineListener = () => {
    store.setOnline(true);
    logger.info("SyncWorker", "Conexão restaurada — disparando sync");
    runSync();
  };

  _offlineListener = () => {
    store.setOnline(false);
    store.setSyncStatus("idle");
    logger.info("SyncWorker", "Conexão perdida");
  };

  window.addEventListener("online", _onlineListener);
  window.addEventListener("offline", _offlineListener);

  // Sync inicial ao montar
  runSync();
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

// Reset IN_FLIGHT → PENDING ao inicializar (crash recovery)
export async function recoverInFlight(): Promise<void> {
  const stuck = await db.sync_queue.where("status").equals("IN_FLIGHT").toArray();
  if (stuck.length > 0) {
    logger.warn("SyncWorker", `Recuperando ${stuck.length} item(s) IN_FLIGHT`);
    await db.sync_queue.bulkUpdate(
      stuck.map((item) => ({ key: item.id, changes: { status: "PENDING" as const } }))
    );
  }
}
