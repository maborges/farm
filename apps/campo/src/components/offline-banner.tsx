"use client";

import { useNetworkStatus } from "@/hooks/useNetworkStatus";
import { useSyncStore } from "@/lib/stores/sync-store";
import { runSync } from "@/lib/sync/worker";
import { useRouter } from "next/navigation";

export function OfflineBanner() {
  const { isOnline, justReconnected } = useNetworkStatus();
  const { pendingCount, status } = useSyncStore();
  const router = useRouter();

  if (justReconnected) {
    return (
      <div className="w-full bg-green-700 py-2 px-4 text-xs font-medium text-center animate-pulse">
        🟢 Conexão restaurada — sincronizando {pendingCount} registro{pendingCount !== 1 ? "s" : ""}...
      </div>
    );
  }

  if (!isOnline) {
    return (
      <div className="w-full bg-neutral-700 py-2 px-4 text-xs font-medium flex items-center justify-between">
        <span>📵 Offline — dados salvos localmente</span>
        {pendingCount > 0 && (
          <span className="bg-amber-500 text-black rounded-full px-2 py-0.5 text-xs font-bold">
            {pendingCount} pendente{pendingCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>
    );
  }

  if (pendingCount > 0 && status !== "syncing") {
    return (
      <button
        onClick={() => runSync()}
        className="w-full bg-amber-900/70 py-2 px-4 text-xs font-medium flex items-center justify-between"
      >
        <span>⏳ {pendingCount} registro{pendingCount !== 1 ? "s" : ""} pendente{pendingCount !== 1 ? "s" : ""} de sync</span>
        <span className="underline">Sincronizar →</span>
      </button>
    );
  }

  if (status === "syncing") {
    return (
      <div className="w-full bg-blue-900/70 py-2 px-4 text-xs font-medium text-center">
        ↻ Sincronizando...
      </div>
    );
  }

  if (status === "error") {
    return (
      <button
        onClick={() => router.push("/sync")}
        className="w-full bg-red-900/70 py-2 px-4 text-xs font-medium flex items-center justify-between"
      >
        <span>⚠️ Erro na sincronização</span>
        <span className="underline">Ver detalhes →</span>
      </button>
    );
  }

  return null;
}
