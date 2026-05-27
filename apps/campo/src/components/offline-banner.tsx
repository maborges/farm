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
      <div className="mx-auto w-full max-w-[520px] rounded-[24px] border border-emerald-400/20 bg-emerald-400/12 px-4 py-3 text-xs text-emerald-50 shadow-lg shadow-emerald-950/20">
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium">Conexão restabelecida. Sincronizando agora.</span>
          <CampoPill className="border-emerald-400/20 bg-emerald-400/10 text-emerald-100">
            {pendingCount} pendente{pendingCount !== 1 ? "s" : ""}
          </CampoPill>
        </div>
      </div>
    );
  }

  if (!isOnline) {
    return (
      <div className="mx-auto w-full max-w-[520px] rounded-[24px] border border-white/10 bg-white/[0.04] px-4 py-3 text-xs text-white/80 shadow-lg shadow-black/20 backdrop-blur-xl">
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium">Sem conexão. Os registros ficam salvos no dispositivo.</span>
          {pendingCount > 0 && (
            <CampoPill className="border-amber-400/20 bg-amber-400/12 text-amber-100">
              {pendingCount} pendente{pendingCount !== 1 ? "s" : ""}
            </CampoPill>
          )}
        </div>
      </div>
    );
  }

  if (pendingCount > 0 && status !== "syncing") {
    return (
      <div className="mx-auto w-full max-w-[520px] rounded-[24px] border border-amber-400/20 bg-amber-400/12 px-4 py-3 shadow-lg shadow-amber-950/20">
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-medium text-amber-50">
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
      <div className="mx-auto w-full max-w-[520px] rounded-[24px] border border-sky-400/20 bg-sky-400/12 px-4 py-3 text-center text-xs font-medium text-sky-50 shadow-lg shadow-sky-950/20">
        Sincronizando registros do campo...
      </div>
    );
  }

  if (status === "error") {
    return (
      <button
        onClick={() => router.push("/sync")}
      className="mx-auto flex w-full max-w-[520px] items-center justify-between rounded-[24px] border border-rose-400/20 bg-rose-400/12 px-4 py-3 text-left text-xs font-medium text-rose-50 shadow-lg shadow-rose-950/20"
    >
        <span>Houve um erro na sincronização. Toque para revisar.</span>
        <span className="text-rose-100/80">Ver detalhes →</span>
      </button>
    );
  }

  return null;
}
