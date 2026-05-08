"use client";

import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { db } from "@/lib/db";
import { useSyncStore } from "@/lib/stores/sync-store";
import { useSessionStore } from "@/lib/stores/session-store";
import { runSync } from "@/lib/sync/worker";
import { logger } from "@/lib/logger";

async function retryItem(id: string) {
  await db.sync_queue.update(id, { status: "PENDING", attempts: 0, last_error: undefined });
  runSync();
}

function exportLogs() {
  const blob = new Blob([logger.exportJson()], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `campo-logs-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function SyncPage() {
  const router = useRouter();
  const { status, isOnline, pendingCount, lastSyncAt, lastError } = useSyncStore();
  const { session } = useSessionStore();

  const failedItems = useLiveQuery(
    () => db.sync_queue.where("status").equals("FAILED").toArray(),
    []
  );

  const pendingItems = useLiveQuery(
    () => db.sync_queue.where("status").anyOf(["PENDING", "IN_FLIGHT"]).toArray(),
    []
  );

  const conflictTasks = useLiveQuery(
    () => db.tasks.filter((t) => !!t.sync_conflict).toArray(),
    []
  );

  return (
    <div className="flex flex-col gap-6 p-4 pb-8">
      {/* Header */}
      <div className="flex items-center gap-3 pt-2">
        <button onClick={() => router.back()} className="text-neutral-400">
          ←
        </button>
        <h1 className="text-lg font-bold">Sincronização</h1>
      </div>

      {/* Status Card */}
      <div className="bg-neutral-800 rounded-2xl p-5 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`size-2.5 rounded-full ${isOnline ? "bg-green-500" : "bg-neutral-500"}`} />
            <span className="font-semibold">{isOnline ? "Online" : "Offline"}</span>
          </div>
          <span
            className={`text-xs font-medium px-2.5 py-1 rounded-full ${
              status === "success"
                ? "bg-green-900 text-green-300"
                : status === "syncing"
                ? "bg-blue-900 text-blue-300"
                : status === "error"
                ? "bg-red-900 text-red-300"
                : "bg-neutral-700 text-neutral-300"
            }`}
          >
            {status === "success"
              ? "Sincronizado"
              : status === "syncing"
              ? "Sincronizando..."
              : status === "error"
              ? "Erro"
              : "Aguardando"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 text-center">
          <div className="bg-neutral-900 rounded-xl p-3">
            <p className="text-2xl font-bold text-amber-400">{pendingCount}</p>
            <p className="text-xs text-neutral-500 mt-0.5">Pendentes</p>
          </div>
          <div className="bg-neutral-900 rounded-xl p-3">
            <p className="text-2xl font-bold text-red-400">{failedItems?.length ?? 0}</p>
            <p className="text-xs text-neutral-500 mt-0.5">Com falha</p>
          </div>
        </div>

        {lastSyncAt && (
          <p className="text-xs text-neutral-500 text-center">
            Último sync: {new Date(lastSyncAt).toLocaleString("pt-BR")}
          </p>
        )}

        {lastError && (
          <div className="bg-red-950 border border-red-800 rounded-xl px-3 py-2 text-xs text-red-300">
            {lastError}
          </div>
        )}

        <button
          onClick={() => runSync()}
          disabled={!isOnline || status === "syncing"}
          className="bg-green-600 hover:bg-green-500 disabled:opacity-40 rounded-xl py-3 text-sm font-semibold transition-colors"
        >
          {status === "syncing" ? "Sincronizando..." : "Sincronizar Agora"}
        </button>
      </div>

      {/* Itens com falha */}
      {failedItems && failedItems.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-red-400 uppercase tracking-wide">
            Falhas ({failedItems.length})
          </h2>
          <div className="flex flex-col gap-2">
            {failedItems.map((item) => (
              <div key={item.id} className="bg-neutral-800 rounded-2xl p-4 flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium">{item.entity_type} — {item.operation}</p>
                    <p className="text-xs text-red-400 mt-1">{item.last_error}</p>
                    <p className="text-xs text-neutral-600 mt-0.5">
                      {item.attempts} tentativas • {new Date(item.created_at).toLocaleString("pt-BR")}
                    </p>
                  </div>
                  <button
                    onClick={() => retryItem(item.id)}
                    className="shrink-0 text-xs text-green-400 underline"
                  >
                    Tentar novamente
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Conflitos */}
      {conflictTasks && conflictTasks.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-amber-400 uppercase tracking-wide">
            Conflitos ({conflictTasks.length})
          </h2>
          <div className="flex flex-col gap-2">
            {conflictTasks.map((task) => (
              <div key={task.id} className="bg-neutral-800 rounded-2xl p-4 border border-amber-800/50">
                <p className="text-sm font-medium">{task.type}</p>
                <p className="text-xs text-amber-400 mt-1">{task.sync_conflict}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Info do dispositivo */}
      <section className="bg-neutral-800 rounded-2xl p-4 flex flex-col gap-1.5">
        <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-wide mb-1">
          Dispositivo
        </h2>
        <InfoRow label="ID" value={session?.device_id?.slice(0, 8) + "..."} />
        <InfoRow label="Usuário" value={session?.user_name ?? "—"} />
        <InfoRow label="Módulos" value={session?.modules?.join(", ") ?? "—"} />
      </section>

      {/* Diagnósticos */}
      <button
        onClick={exportLogs}
        className="w-full border border-neutral-700 rounded-2xl py-3 text-sm text-neutral-400"
      >
        Exportar logs de diagnóstico
      </button>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-neutral-500">{label}</span>
      <span className="text-neutral-200 font-mono text-xs">{value}</span>
    </div>
  );
}
