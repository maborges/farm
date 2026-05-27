"use client";

import { useSyncStore } from "@/lib/stores/sync-store";
import { useRouter } from "next/navigation";
import { CampoPill } from "@/components/campo/ui";

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
      className={`mx-auto w-full max-w-[520px] rounded-[24px] border border-white/10 px-4 py-3 text-xs text-white/80 transition-colors ${bgClass}`}
    >
      <span className="flex items-center justify-between gap-3">
        <span
          className={`size-1.5 rounded-full ${
            !isOnline ? "bg-neutral-400" : status === "error" ? "bg-red-400" : "bg-green-500"
          }`}
        />
        <span className="flex-1 text-left">{label}</span>
        {pendingCount > 0 && <CampoPill className="border-white/10 bg-white/8">{pendingCount}</CampoPill>}
      </span>
    </button>
  );
}
