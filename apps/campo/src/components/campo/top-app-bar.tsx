"use client";

import { useMemo, useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { Check, Signal, SignalHigh, RefreshCw, CircleCheck, CircleAlert, MapPinned, MapPinOff, Warehouse } from "lucide-react";
import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

function resolveCampoAvatarUrl(url?: string) {
  if (!url) return undefined;
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:")) {
    return url;
  }
  return url;
}

export function CampoTopAppBar({
  pendingCount,
  isOnline,
  syncStatus,
  gpsStatus,
}: {
  pendingCount: number;
  isOnline: boolean;
  syncStatus: "idle" | "syncing" | "success" | "error";
  gpsStatus: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
}) {
  const { session, setActiveFazenda } = useSessionStore();
  const [dialogOpen, setDialogOpen] = useState(false);
  const avatarSrc = resolveCampoAvatarUrl(session?.user_avatar_url);
  const userInitial = (session?.user_name ?? "O").trim().charAt(0).toUpperCase();

  const fazendas = useLiveQuery(async () => {
    const ids = session?.fazenda_ids ?? [];
    if (ids.length === 0) return [];
    const rows = await db.fazendas.bulkGet(ids);
    return rows.filter(Boolean);
  }, [session?.fazenda_ids?.join("|")]);

  const activeFazenda = useMemo(
    () => (fazendas ?? []).find((fazenda) => fazenda?.id === session?.active_fazenda_id),
    [fazendas, session?.active_fazenda_id]
  );

  const canSelectFazenda = (fazendas?.length ?? 0) > 1;
  const syncOk = isOnline && pendingCount === 0 && (syncStatus === "success" || syncStatus === "idle");

  return (
    <>
      <div className="sticky top-0 z-40 px-4 sm:px-6">
        <div className="border-x border-b border-border/80 bg-card/95 px-3 py-2 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/88">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                if (canSelectFazenda) setDialogOpen(true);
              }}
              disabled={!canSelectFazenda}
              className={cn(
                "inline-flex min-w-0 flex-1 items-center gap-2.5 rounded-2xl px-1 py-1 text-left transition-colors",
                canSelectFazenda
                  ? "text-foreground active:scale-[0.99]"
                  : "cursor-default text-foreground"
              )}
            >
              <span className="flex size-7 shrink-0 items-center justify-center rounded-2xl bg-muted/75 text-muted-foreground">
                <Warehouse className="size-3.5 opacity-85" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold leading-4 text-foreground">
                  {activeFazenda?.nome ?? "Unidade produtiva"}
                </span>
              </span>
            </button>

            <StatusIndicator
              active={isOnline}
              icon={isOnline ? SignalHigh : Signal}
              label={isOnline ? "OnLine" : "OffLine"}
            />
            <StatusIndicator
              active={syncOk}
              icon={syncStatus === "syncing" ? RefreshCw : syncOk ? CircleCheck : CircleAlert}
              label="SYNC"
              spinning={syncStatus === "syncing"}
            />
            <StatusIndicator
              active={gpsStatus === "DISPONIVEL"}
              icon={gpsStatus === "DISPONIVEL" ? MapPinned : MapPinOff}
              label="GPS"
            />

            <div className="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-accent text-[11px] font-semibold text-accent-foreground shadow-sm">
              {avatarSrc ? (
                <img src={avatarSrc} alt={session?.user_name ?? "Operador"} className="h-full w-full object-cover" />
              ) : (
                <span>{userInitial}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {dialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 backdrop-blur-sm">
          <div className="w-full max-w-[380px] overflow-hidden rounded-[28px] border border-border/80 bg-card shadow-2xl">
            <div className="bg-[linear-gradient(180deg,rgba(255,255,255,0.06),transparent)] px-5 pb-4 pt-5">
              <div className="mb-4 mx-auto h-1.5 w-12 rounded-full bg-muted" />
              <div>
                <h2 className="text-base font-semibold text-foreground">
                  Selecionar unidade ativa
                </h2>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Escolha a unidade usada como contexto padrão dos registros no dispositivo.
                </p>
              </div>
            </div>

            <div className="flex max-h-[52dvh] flex-col overflow-y-auto px-3 pb-3">
              {(fazendas ?? []).map((fazenda) => {
                const active = fazenda?.id === session?.active_fazenda_id;
                if (!fazenda) return null;

                return (
                  <button
                    key={fazenda.id}
                    type="button"
                    onClick={() => {
                      void setActiveFazenda(fazenda.id);
                      setDialogOpen(false);
                    }}
                    className={cn(
                      "mt-1.5 flex w-full items-center justify-between gap-3 rounded-2xl px-3 py-3 text-left text-sm transition-colors active:scale-[0.99]",
                      active
                        ? "bg-accent/80 text-accent-foreground"
                        : "bg-transparent text-foreground hover:bg-muted/70"
                    )}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div
                        className={cn(
                          "flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-full border text-xs font-semibold shadow-sm",
                          active
                            ? "border-primary/20 bg-primary/12 text-primary"
                            : "border-border bg-card text-muted-foreground"
                        )}
                      >
                        <Warehouse className="size-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate font-medium">{fazenda.nome}</p>
                      </div>
                    </div>
                    {active && <Check className="size-4 shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function StatusIndicator({
  active,
  icon: Icon,
  label,
  spinning = false,
}: {
  active: boolean;
  icon: typeof Signal;
  label: string;
  spinning?: boolean;
}) {
  return (
    <div
      className={cn(
        "inline-flex shrink-0 items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.14em]",
        active ? "text-green-700 dark:text-green-300" : "text-rose-700 dark:text-rose-300"
      )}
    >
      <Icon className={cn("size-3.5", spinning && "animate-spin")} />
      {label}
    </div>
  );
}
