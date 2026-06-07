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
    <div className="flex flex-col gap-4 pb-28">
      <CampoSurface className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <button
            onClick={() => router.back()}
            className="rounded-sm border border-border bg-card px-3 py-2 text-sm text-foreground transition-transform active:scale-[0.97]"
          >
            ←
          </button>
          <div className="flex-1">
            <CampoSectionTitle
              eyebrow="Sincronização"
              title="Sincronização do campo"
              description="Veja a fila local e reenvie itens com falha."
            />
          </div>
          <CampoPill
            className={`${isOnline ? "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200" : "border-border bg-muted text-muted-foreground"}`}
          >
            {isOnline ? "Online" : "Offline"}
          </CampoPill>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <CampoMetric label="Na fila" value={pendingCount} tone="amber" />
          <CampoMetric label="Com erro" value={failedItems?.length ?? 0} tone="rose" />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <CampoPill
            className={
              status === "syncing"
                ? "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200"
                : "border-border bg-muted text-muted-foreground"
            }
          >
            {status === "syncing" ? "Sincronizando" : status === "error" ? "Erro" : "Pronto"}
          </CampoPill>
          {lastSyncAt && (
            <CampoPill className="border-border bg-muted text-muted-foreground">
              Última sincronização: {new Date(lastSyncAt).toLocaleString("pt-BR")}
            </CampoPill>
          )}
        </div>

        {lastError && (
          <div className="mt-3 rounded-sm border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
            {lastError}
          </div>
        )}

        <CampoButton
          onClick={() => runSync()}
          disabled={!isOnline || status === "syncing"}
          className="mt-4 w-full"
          size="md"
        >
          {status === "syncing" ? "Sincronizando..." : "Sincronizar agora"}
        </CampoButton>
      </CampoSurface>

      <div className="grid gap-4 lg:grid-cols-2">
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
                  className="rounded-sm border border-border bg-card p-3 shadow-sm"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {item.entity_type} — {item.operation}
                      </p>
                      <p className="mt-1 text-xs text-rose-700 dark:text-rose-300">{item.last_error}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {item.attempts} tentativas • {new Date(item.created_at).toLocaleString("pt-BR")}
                      </p>
                    </div>
                    <button
                      onClick={() => retryItem(item.id)}
                      className="shrink-0 rounded-full border border-green-200 bg-green-50 px-2.5 py-1 text-[11px] font-semibold text-green-800 transition-transform active:scale-[0.97] dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200"
                    >
                      Reenviar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : (
          <CampoSurface className="flex items-center gap-3 p-3 text-sm text-muted-foreground">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200">
              <CheckCircle2 className="size-4.5" />
            </div>
            <div>
              <p className="font-medium text-foreground">Sem falhas pendentes</p>
              <p className="text-xs text-muted-foreground">Os itens com erro aparecerão aqui para reprocessamento.</p>
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
                <div key={task.id} className="rounded-sm border border-amber-200 bg-amber-50 p-3 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                  <p className="text-sm font-medium">{task.type}</p>
                  <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">{task.sync_conflict}</p>
                </div>
              ))}
            </div>
          </section>
        ) : (
          <CampoSurface className="flex items-center gap-3 p-3 text-sm text-muted-foreground">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              <AlertTriangle className="size-4.5" />
            </div>
            <div>
              <p className="font-medium text-foreground">Sem conflitos detectados</p>
              <p className="text-xs text-muted-foreground">Se aparecerem, use esta área para revisar cada tarefa.</p>
            </div>
          </CampoSurface>
        )}
      </div>

      {/* Info do dispositivo */}
      <CampoSurface className="p-3.5">
        <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          Dispositivo
        </h2>
        <InfoRow label="ID" value={session?.device_id?.slice(0, 8) + "..."} />
        <InfoRow label="Usuário" value={session?.user_name ?? "—"} />
        <InfoRow label="Módulos" value={session?.modules?.join(", ") ?? "—"} />
      </CampoSurface>

      {/* Diagnósticos */}
      <button
        onClick={exportLogs}
        className="w-full rounded-sm border border-border bg-card py-2.5 text-sm text-muted-foreground shadow-sm transition-all hover:bg-muted active:scale-[0.99]"
      >
        Exportar diagnóstico
      </button>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="truncate font-mono text-xs text-foreground">{value}</span>
    </div>
  );
}
