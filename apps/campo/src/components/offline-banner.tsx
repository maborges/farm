"use client";

import { useNetworkStatus } from "@/hooks/useNetworkStatus";
import { useSyncStore } from "@/lib/stores/sync-store";
import { runSync } from "@/lib/sync/worker";
import { useRouter } from "next/navigation";
import { CampoButton, CampoPill } from "@/components/campo/ui";

export function OfflineBanner() {
  const { isOnline, justReconnected } = useNetworkStatus();
  const { pendingCount, status } = useSyncStore();
  const router = useRouter();

  if (justReconnected) {
    return (
      <div className="w-full rounded-sm border border-green-200 bg-green-50 px-3 py-2 text-[11px] text-green-800 shadow-sm dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200">
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium">Conexão restabelecida. Sincronizando agora.</span>
          <CampoPill className="border-green-200 bg-green-100 text-green-800 dark:border-green-900/60 dark:bg-green-950/40 dark:text-green-200">
            {pendingCount} pendente{pendingCount !== 1 ? "s" : ""}
          </CampoPill>
        </div>
      </div>
    );
  }

  if (!isOnline) {
    return (
      <div className="w-full rounded-sm border border-border bg-card px-3 py-2 text-[11px] text-foreground shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium">Sem conexão. Os registros ficam salvos no dispositivo.</span>
          {pendingCount > 0 && (
            <CampoPill className="border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              {pendingCount} pendente{pendingCount !== 1 ? "s" : ""}
            </CampoPill>
          )}
        </div>
      </div>
    );
  }

  if (pendingCount > 0 && status !== "syncing") {
    return (
      <div className="w-full rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800 shadow-sm dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[11px] font-medium">
            {pendingCount} registro{pendingCount !== 1 ? "s" : ""} aguardando envio
          </span>
          <CampoButton size="sm" variant="secondary" onClick={() => runSync()}>
            Enviar agora
          </CampoButton>
        </div>
      </div>
    );
  }

  if (status === "syncing") {
    return (
      <div className="w-full rounded-sm border border-sky-200 bg-sky-50 px-3 py-2 text-center text-[11px] font-medium text-sky-800 shadow-sm dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">
        Sincronizando registros do campo...
      </div>
    );
  }

  if (status === "error") {
    return (
      <button
        onClick={() => router.push("/sync")}
      className="flex w-full items-center justify-between rounded-sm border border-rose-200 bg-rose-50 px-3 py-2 text-left text-[11px] font-medium text-rose-800 shadow-sm dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200"
    >
        <span>Houve um erro na sincronização. Toque para revisar.</span>
        <span className="opacity-80">Ver detalhes →</span>
      </button>
    );
  }

  return null;
}
