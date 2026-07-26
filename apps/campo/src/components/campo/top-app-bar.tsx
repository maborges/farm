"use client";

import { useMemo, useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { Check, Signal, SignalHigh, RefreshCw, CircleCheck, CircleAlert, MapPinned, MapPinOff, Warehouse } from "lucide-react";
import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { BottomSheet } from "@/components/bottom-sheet";

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

/** Gera uma cor HSL determinística baseada na inicial do nome do usuário. */
function resolveAvatarColor(name: string): string {
  const code = (name.trim().charCodeAt(0) || 65) % 360;
  // Evitar hues muito próximos do vermelho (0°) para não parecer erro
  const hue = code < 20 ? code + 40 : code;
  return `hsl(${hue}, 55%, 42%)`;
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
  const avatarColor = resolveAvatarColor(session?.user_name ?? "O");

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
      <div className="sticky top-0 z-40" style={{ paddingTop: "env(safe-area-inset-top)" }}>
        <div className="border-b border-border/80 bg-card/95 px-4 py-2 sm:px-6 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/88">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                if (canSelectFazenda) setDialogOpen(true);
              }}
              disabled={!canSelectFazenda}
              className={cn(
                "inline-flex min-h-[48px] min-w-0 flex-1 items-center gap-2.5 rounded-2xl px-2 py-1 text-left transition-all",
                canSelectFazenda
                  ? "text-foreground active:scale-95 active:bg-black/5 dark:active:bg-white/10"
                  : "cursor-default text-foreground"
              )}
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-[var(--campo-pwa-agro-light)] dark:bg-[var(--campo-pwa-agro-bg)] text-[var(--campo-pwa-agro-dark-text)] dark:text-[var(--campo-pwa-agro)]">
                <Warehouse className="size-3.5" />
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

            <div
              className="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border shadow-sm text-[11px] font-semibold text-white"
              style={avatarSrc ? undefined : { background: avatarColor }}
            >
              {avatarSrc ? (
                <img src={avatarSrc} alt={session?.user_name ?? "Operador"} className="h-full w-full object-cover" />
              ) : (
                <span>{userInitial}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      <BottomSheet
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Selecionar unidade ativa"
        description="Escolha a unidade usada como contexto padrão dos registros no dispositivo."
      >
        <div className="flex flex-col px-3 pb-3">
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
                  "mt-1.5 flex min-h-[56px] w-full items-center justify-between gap-3 rounded-2xl px-4 py-3 text-left text-sm transition-all active:scale-95",
                  active
                    ? "bg-accent/80 text-accent-foreground"
                    : "bg-transparent text-foreground hover:bg-muted/70 active:bg-black/5 dark:active:bg-white/10"
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
                {active && <Check className="size-4 shrink-0 text-primary" />}
              </button>
            );
          })}
        </div>
      </BottomSheet>
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
