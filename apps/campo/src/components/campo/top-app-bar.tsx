"use client";

import { useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import {
  ArrowLeft,
  Check,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  Laptop,
  LogOut,
  MapPinOff,
  MapPinned,
  Moon,
  RefreshCw,
  Signal,
  SignalHigh,
  Smartphone,
  Sun,
  Tablet,
  Warehouse,
} from "lucide-react";
import { BottomSheet } from "@/components/bottom-sheet";
import { useTheme } from "@/components/theme-provider";
import { useCachedCampoImage } from "@/lib/campo-assets";
import { db } from "@/lib/db";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { useSessionStore } from "@/lib/stores/session-store";
import { resolveCampoRouteMeta } from "./nav-items";

function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

function resolveCampoAvatarUrl(url?: string): string | undefined {
  if (!url) return undefined;
  return url;
}

/**
 * Gera uma cor HSL determinística baseada na inicial do nome do operador.
 *
 * Args:
 *   name (string): Nome do operador autenticado.
 *
 * Return:
 *   string: String CSS HSL segura para uso em avatar.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function resolveAvatarColor(name: string): string {
  const code = (name.trim().charCodeAt(0) || 65) % 360;
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
  const pathname = usePathname();
  const router = useRouter();
  const { session, setActiveFazenda } = useSessionStore();
  const { layoutProfile, isHydrated } = useDeviceContext();
  const { theme, setTheme } = useTheme();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [avatarMenuOpen, setAvatarMenuOpen] = useState(false);

  const routeMeta = useMemo(() => resolveCampoRouteMeta(pathname), [pathname]);
  const isMobile = layoutProfile.deviceCategory === "mobile";

  const cachedAvatarSrc = useCachedCampoImage(
    "user_avatar",
    session?.user_id,
    session?.user_avatar_url
  );
  const avatarSrc = cachedAvatarSrc ?? resolveCampoAvatarUrl(session?.user_avatar_url);
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
  const cachedFazendaLogoSrc = useCachedCampoImage(
    "fazenda_logo",
    activeFazenda?.id,
    activeFazenda?.logo_url
  );

  const canSelectFazenda = (fazendas?.length ?? 0) > 1;
  const syncOk =
    isOnline && pendingCount === 0 && (syncStatus === "success" || syncStatus === "idle");

  return (
    <>
      <header
        data-device-category={layoutProfile.deviceCategory}
        data-execution-mode={layoutProfile.executionMode}
        className="sticky top-0 z-40 select-none"
        style={{ paddingTop: "env(safe-area-inset-top)" }}
      >
        <div className="glass-chrome border-b border-border/80 px-3 py-2 sm:px-5">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-2">
            {/* Esquerda: Botão voltar contextual no mobile em sub-rotas + Seletor de Fazenda */}
            <div className="flex min-w-0 flex-1 items-center gap-2">
              {!routeMeta.isRoot && isMobile && (
                <button
                  type="button"
                  onClick={() => router.push(routeMeta.backHref)}
                  aria-label="Voltar"
                  className="inline-flex size-8 shrink-0 items-center justify-center rounded-sm border border-border bg-card text-foreground shadow-2xs transition-transform active:scale-95"
                >
                  <ArrowLeft className="size-4" />
                </button>
              )}

              <button
                type="button"
                onClick={() => {
                  if (canSelectFazenda) setDialogOpen(true);
                }}
                disabled={!canSelectFazenda}
                className={cn(
                  "inline-flex min-h-[40px] min-w-0 items-center gap-2 rounded-sm px-2 py-1 text-left transition-all",
                  canSelectFazenda
                    ? "border border-border/70 bg-card/70 text-foreground hover:bg-muted/70 active:scale-95"
                    : "cursor-default text-foreground"
                )}
              >
                <span className="flex size-7 shrink-0 items-center justify-center overflow-hidden rounded-sm bg-[var(--campo-pwa-agro-light)] dark:bg-[var(--campo-pwa-agro-bg)] text-[var(--campo-pwa-agro-dark-text)] dark:text-[var(--campo-pwa-agro)]">
                  {cachedFazendaLogoSrc ? (
                    <img src={cachedFazendaLogoSrc} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <Warehouse className="size-3.5" />
                  )}
                </span>
                <span className="min-w-0 flex-1">
                  {!routeMeta.isRoot && isMobile ? (
                    <>
                      <span className="block truncate text-xs font-bold leading-tight text-foreground">
                        {routeMeta.title}
                      </span>
                      <span className="block truncate text-[10px] font-medium leading-tight text-muted-foreground">
                        {activeFazenda?.nome ?? "Unidade produtiva"}
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="block truncate text-xs sm:text-sm font-bold leading-tight text-foreground">
                        {activeFazenda?.nome ?? "Unidade produtiva"}
                      </span>
                      <span className="hidden sm:block truncate text-[10px] text-muted-foreground">
                        {routeMeta.title} • {routeMeta.subtitle}
                      </span>
                    </>
                  )}
                </span>
                {canSelectFazenda && (
                  <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
                )}
              </button>
            </div>

            {/* Direita: Indicadores operacionais + Badge de ambiente + Tema + Avatar */}
            <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
              {isHydrated && (
                <span
                  className="hidden sm:inline-flex items-center gap-1 rounded-sm border border-border bg-muted/60 px-2 py-1 text-[10px] font-semibold text-muted-foreground"
                  title={`Executando em modo ${layoutProfile.deviceCategory} (${layoutProfile.executionMode})`}
                >
                  {layoutProfile.deviceCategory === "mobile" ? (
                    <Smartphone className="size-3 text-primary" />
                  ) : layoutProfile.deviceCategory === "tablet" ? (
                    <Tablet className="size-3 text-primary" />
                  ) : (
                    <Laptop className="size-3 text-primary" />
                  )}
                  <span className="capitalize">{layoutProfile.deviceCategory}</span>
                </span>
              )}

              <StatusIndicator
                active={isOnline}
                icon={isOnline ? SignalHigh : Signal}
                label={isOnline ? "OnLine" : "OffLine"}
              />
              <StatusIndicator
                active={syncOk}
                icon={
                  syncStatus === "syncing" ? RefreshCw : syncOk ? CircleCheck : CircleAlert
                }
                label={pendingCount > 0 ? `SYNC (${pendingCount})` : "SYNC"}
                spinning={syncStatus === "syncing"}
                onClick={() => router.push("/sync")}
              />
              <StatusIndicator
                active={gpsStatus === "DISPONIVEL"}
                icon={gpsStatus === "DISPONIVEL" ? MapPinned : MapPinOff}
                label="GPS"
              />

              {/* Alternância rápida Dark/Light Mode (AGRO-03) */}
              <button
                type="button"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                aria-label="Alternar tema claro ou escuro"
                title={theme === "dark" ? "Mudar para modo claro" : "Mudar para modo escuro"}
                className="inline-flex size-8 items-center justify-center rounded-sm border border-border bg-card text-muted-foreground shadow-2xs transition-colors hover:bg-accent hover:text-foreground active:scale-95"
              >
                {theme === "dark" ? (
                  <Sun className="size-3.5 text-amber-400" />
                ) : (
                  <Moon className="size-3.5" />
                )}
              </button>

              <button
                type="button"
                onClick={() => setAvatarMenuOpen(true)}
                aria-label="Conta do operador"
                className="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-sm border border-border shadow-2xs text-[11px] font-bold text-white transition-all active:scale-95"
                style={avatarSrc ? undefined : { background: avatarColor }}
              >
                {avatarSrc ? (
                  <img
                    src={avatarSrc}
                    alt={session?.user_name ?? "Operador"}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <span>{userInitial}</span>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      <BottomSheet
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Selecionar unidade ativa"
        description="Escolha a unidade usada como contexto padrão dos registros no dispositivo."
      >
        <div className="flex flex-col gap-1.5 p-3">
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
                  "flex min-h-[52px] w-full items-center justify-between gap-3 rounded-sm border px-3.5 py-2.5 text-left text-sm transition-all active:scale-[0.99]",
                  active
                    ? "border-primary/30 bg-accent text-accent-foreground font-semibold"
                    : "border-border/60 bg-card text-foreground hover:bg-muted/70"
                )}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div
                    className={cn(
                      "flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-sm border text-xs font-semibold shadow-2xs",
                      active
                        ? "border-primary/25 bg-primary/12 text-primary"
                        : "border-border bg-muted text-muted-foreground"
                    )}
                  >
                    <Warehouse className="size-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-medium">{fazenda.nome}</p>
                    {(fazenda.municipio || fazenda.uf) && (
                      <p className="truncate text-xs text-muted-foreground">
                        {[fazenda.municipio, fazenda.uf].filter(Boolean).join(" · ")}
                      </p>
                    )}
                  </div>
                </div>
                {active && <Check className="size-4 shrink-0 text-primary" />}
              </button>
            );
          })}
        </div>
      </BottomSheet>

      <BottomSheet
        open={avatarMenuOpen}
        onOpenChange={setAvatarMenuOpen}
        title="Conta do Operador"
        description={
          session?.user_name
            ? `Operador conectado: ${session.user_name}`
            : "Gerencie sua sessão ou aparência."
        }
      >
        <div className="flex flex-col gap-2 p-3">
          <button
            type="button"
            onClick={() => {
              setTheme(theme === "dark" ? "light" : "dark");
              setAvatarMenuOpen(false);
            }}
            className="flex min-h-[52px] w-full items-center justify-between gap-3 rounded-sm border border-border bg-card px-3.5 py-2.5 text-left text-sm text-foreground transition-all hover:bg-muted/70 active:scale-[0.99]"
          >
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-sm border border-border bg-muted text-muted-foreground">
                {theme === "dark" ? <Sun className="size-4 text-amber-400" /> : <Moon className="size-4" />}
              </div>
              <div>
                <p className="font-semibold">Mudar Aparência</p>
                <p className="text-xs text-muted-foreground">
                  Alternar para tema {theme === "dark" ? "claro" : "escuro"}
                </p>
              </div>
            </div>
          </button>

          <button
            type="button"
            onClick={() => {
              setAvatarMenuOpen(false);
              router.push("/pin");
            }}
            className="flex min-h-[52px] w-full items-center justify-between gap-3 rounded-sm border border-border bg-card px-3.5 py-2.5 text-left text-sm text-foreground transition-all hover:bg-muted/70 active:scale-[0.99]"
          >
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-sm border border-border bg-muted text-muted-foreground">
                <LogOut className="size-4" />
              </div>
              <div>
                <p className="font-semibold">Bloquear Sessão</p>
                <p className="text-xs text-muted-foreground">Exigir PIN novamente</p>
              </div>
            </div>
          </button>
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
  onClick,
}: {
  active: boolean;
  icon: typeof Signal;
  label: string;
  spinning?: boolean;
  onClick?: () => void;
}) {
  const classes = cn(
    "inline-flex shrink-0 items-center gap-1 rounded-sm border px-1.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em]",
    active
      ? "border-green-200/80 bg-green-50/80 text-green-700 dark:border-green-900/50 dark:bg-green-950/30 dark:text-green-300"
      : "border-rose-200/80 bg-rose-50/80 text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300",
    onClick && "cursor-pointer active:scale-95 transition-transform"
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={classes}>
        <Icon className={cn("size-3", spinning && "animate-spin")} />
        <span className="hidden xs:inline sm:inline">{label}</span>
      </button>
    );
  }

  return (
    <div className={classes}>
      <Icon className={cn("size-3", spinning && "animate-spin")} />
      <span className="hidden xs:inline sm:inline">{label}</span>
    </div>
  );
}
