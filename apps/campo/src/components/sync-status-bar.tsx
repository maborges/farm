"use client";

import { useSyncStore } from "@/lib/stores/sync-store";
import { useRouter } from "next/navigation";

export function SyncStatusBar() {
  const { isOnline, status, pendingCount } = useSyncStore();
  const router = useRouter();

  const bgClass =
    !isOnline
      ? "bg-neutral-700"
      : status === "syncing"
      ? "bg-blue-900"
      : status === "error"
      ? "bg-red-900"
      : "bg-neutral-900";

  const label =
    !isOnline
      ? "Offline — dados salvos localmente"
      : status === "syncing"
      ? "Sincronizando..."
      : status === "error"
      ? "Erro na sincronização"
      : pendingCount > 0
      ? `${pendingCount} registro${pendingCount > 1 ? "s" : ""} pendente${pendingCount > 1 ? "s" : ""}`
      : "Sincronizado";

  return (
    <button
      onClick={() => router.push("/sync")}
      className={`w-full py-2 px-4 text-xs text-center font-medium transition-colors ${bgClass}`}
    >
      <span className="flex items-center justify-center gap-1.5">
        <span
          className={`size-1.5 rounded-full ${
            !isOnline ? "bg-neutral-400" : status === "error" ? "bg-red-400" : "bg-green-500"
          }`}
        />
        {label}
      </span>
    </button>
  );
}
