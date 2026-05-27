"use client";

import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { db } from "@/lib/db";
import { useSyncStore } from "@/lib/stores/sync-store";
import { useSessionStore } from "@/lib/stores/session-store";
import { runSync } from "@/lib/sync/worker";
import { logger } from "@/lib/logger";
import { CampoButton, CampoMetric, CampoPill, CampoSectionTitle, CampoSurface } from "@/components/campo/ui";

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

  const conflictTasks = useLiveQuery(
    () => db.tasks.filter((t) => !!t.sync_conflict).toArray(),
    []
  );

  return (
    <div className="flex flex-col gap-5 pb-32">
      <CampoSurface className="p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <button
            onClick={() => router.back()}
            className="rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-white/80 transition-transform active:scale-[0.97]"
          >
            ←
          </button>
          <div className="flex-1">
            <CampoSectionTitle
              eyebrow="Sincronização"
              title="Sincronização do campo"
              description="Acompanhe o que já foi enviado e o que ainda aguarda conexão."
            />
          </div>
          <CampoPill
            className={`${isOnline ? "border-emerald-400/20 bg-emerald-400/12 text-emerald-100" : "border-white/10 bg-white/6 text-white/70"}`}
          >
            {isOnline ? "Online" : "Offline"}
          </CampoPill>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <CampoMetric label="Na fila" value={pendingCount} tone="amber" />
          <CampoMetric label="Com erro" value={failedItems?.length ?? 0} tone="rose" />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <CampoPill
            className={
              status === "syncing"
                ? "border-sky-400/20 bg-sky-400/12 text-sky-100"
                : "border-white/10 bg-white/6 text-white/70"
            }
          >
            {status === "syncing" ? "Sincronizando" : status === "error" ? "Erro" : "Pronto"}
          </CampoPill>
          {lastSyncAt && (
            <CampoPill className="border-white/10 bg-white/6 text-white/70">
              Última sincronização: {new Date(lastSyncAt).toLocaleString("pt-BR")}
            </CampoPill>
          )}
        </div>

        {lastError && (
          <div className="mt-4 rounded-2xl border border-rose-400/20 bg-rose-400/12 px-4 py-3 text-xs text-rose-100">
            {lastError}
          </div>
        )}

        <CampoButton
          onClick={() => runSync()}
          disabled={!isOnline || status === "syncing"}
          className="mt-5 w-full"
          size="lg"
        >
          {status === "syncing" ? "Sincronizando..." : "Sincronizar agora"}
        </CampoButton>
      </CampoSurface>

      <div className="grid gap-5 lg:grid-cols-2">
        {failedItems && failedItems.length > 0 ? (
          <section className="flex flex-col gap-2">
            <CampoSectionTitle
              eyebrow="Falhas"
              title={`Itens com erro (${failedItems.length})`}
              description="Revise e reenvie quando a conexão estiver estável."
            />
            <div className="flex flex-col gap-2">
              {failedItems.map((item) => (
                <div
                  key={item.id}
                  className="rounded-[24px] border border-white/10 bg-white/[0.04] p-4 shadow-[0_16px_40px_rgba(0,0,0,0.16)]"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-white">
                        {item.entity_type} — {item.operation}
                      </p>
                      <p className="mt-1 text-xs text-rose-200/80">{item.last_error}</p>
                      <p className="mt-0.5 text-xs text-white/35">
                        {item.attempts} tentativas • {new Date(item.created_at).toLocaleString("pt-BR")}
                      </p>
                    </div>
                    <button
                      onClick={() => retryItem(item.id)}
                      className="shrink-0 rounded-full border border-emerald-400/20 bg-emerald-400/12 px-3 py-1 text-xs font-semibold text-emerald-100 transition-transform active:scale-[0.97]"
                    >
                      Reenviar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : (
          <CampoSurface className="flex items-center gap-3 p-4 text-sm text-white/55">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-[18px] bg-emerald-400/12 text-emerald-100">
              <CheckCircle2 className="size-5" />
            </div>
            <div>
              <p className="font-medium text-white/85">Sem falhas pendentes</p>
              <p className="text-xs text-white/45">Os itens com erro aparecerão aqui para reprocessamento.</p>
            </div>
          </CampoSurface>
        )}

        {conflictTasks && conflictTasks.length > 0 ? (
          <section className="flex flex-col gap-2">
            <CampoSectionTitle
              eyebrow="Conflitos"
              title={`Itens em conflito (${conflictTasks.length})`}
              description="Há divergência entre o estado local e o servidor."
            />
            <div className="flex flex-col gap-2">
              {conflictTasks.map((task) => (
                <div key={task.id} className="rounded-[24px] border border-amber-400/20 bg-amber-400/12 p-4">
                  <p className="text-sm font-medium text-white">{task.type}</p>
                  <p className="mt-1 text-xs text-amber-100/80">{task.sync_conflict}</p>
                </div>
              ))}
            </div>
          </section>
        ) : (
          <CampoSurface className="flex items-center gap-3 p-4 text-sm text-white/55">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-[18px] bg-amber-400/12 text-amber-100">
              <AlertTriangle className="size-5" />
            </div>
            <div>
              <p className="font-medium text-white/85">Sem conflitos detectados</p>
              <p className="text-xs text-white/45">Se aparecerem, use esta área para revisar cada tarefa.</p>
            </div>
          </CampoSurface>
        )}
      </div>

      {/* Info do dispositivo */}
      <CampoSurface className="p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-white/45">
          Dispositivo
        </h2>
        <InfoRow label="ID" value={session?.device_id?.slice(0, 8) + "..."} />
        <InfoRow label="Usuário" value={session?.user_name ?? "—"} />
        <InfoRow label="Módulos" value={session?.modules?.join(", ") ?? "—"} />
      </CampoSurface>

      {/* Diagnósticos */}
      <button
        onClick={exportLogs}
        className="w-full rounded-[24px] border border-white/10 bg-white/[0.04] py-3 text-sm text-white/70 transition-all hover:bg-white/[0.06] active:scale-[0.99]"
      >
        Exportar diagnóstico
      </button>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2 text-sm last:border-0">
      <span className="text-white/45">{label}</span>
      <span className="truncate font-mono text-xs text-white/80">{value}</span>
    </div>
  );
}
