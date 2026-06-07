"use client";

import { useSyncStore } from "@/lib/stores/sync-store";
import { useRouter } from "next/navigation";
import { CampoPill } from "@/components/campo/ui";

export function SyncStatusBar() {
  const { isOnline, status, pendingCount } = useSyncStore();
  const router = useRouter();

  const bgClass =
    !isOnline
      ? "bg-muted text-muted-foreground"
      : status === "syncing"
      ? "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200"
      : status === "error"
      ? "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200"
      : "bg-card text-foreground";

  const label =
    !isOnline
      ? "Sem conexão — registros salvos no dispositivo"
      : status === "syncing"
      ? "Sincronizando registros..."
      : status === "error"
      ? "Erro na sincronização"
      : pendingCount > 0
      ? `${pendingCount} registro${pendingCount > 1 ? "s" : ""} aguardando envio`
      : "Tudo em dia";

  return (
    <button
      onClick={() => router.push("/sync")}
      className={`mx-auto w-full max-w-[520px] rounded-sm border border-border px-4 py-3 text-xs shadow-sm transition-colors ${bgClass}`}
    >
      <span className="flex items-center justify-between gap-3">
        <span
          className={`size-1.5 rounded-full ${
            !isOnline ? "bg-neutral-400" : status === "error" ? "bg-red-400" : "bg-green-500"
          }`}
        />
        <span className="flex-1 text-left">{label}</span>
        {pendingCount > 0 && <CampoPill className="border-border bg-muted">{pendingCount}</CampoPill>}
      </span>
    </button>
  );
}
