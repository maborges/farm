"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import {
  Check,
  ChevronDown,
  ChevronLeft,
  CircleAlert,
  CircleCheck,
  LogOut,
  MapPin,
  MapPinOff,
  MapPinned,
  Moon,
  RefreshCw,
  Signal,
  SignalHigh,
  Smartphone,
  Sun,
  Tablet,
  User,
  Warehouse,
} from "lucide-react";
import { BottomSheet } from "@/components/bottom-sheet";
import { useTheme } from "@/components/theme-provider";
import { db } from "@/lib/db";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { useSessionStore } from "@/lib/stores/session-store";
import {
  OPERACAO_ITEMS,
  isCampoRouteActive,
  resolveCampoRouteMeta,
} from "./nav-items";

function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

const TOP_NAV_ITEMS = OPERACAO_ITEMS.filter((item) => item.showInTopNav);

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
  const { layoutProfile } = useDeviceContext();
  const { theme, setTheme } = useTheme();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [avatarMenuOpen, setAvatarMenuOpen] = useState(false);

  const routeMeta = useMemo(() => resolveCampoRouteMeta(pathname), [pathname]);
  const ActiveIcon = routeMeta.icon;
  const isSubpage = !routeMeta.isRoot;
  const firstName = (session?.user_name ?? "Operador").split(" ")[0] || "Operador";

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
  const syncOk =
    isOnline && pendingCount === 0 && (syncStatus === "success" || syncStatus === "idle");

  return (
    <>
      <header
        data-testid="campo-app-header"
        data-device={layoutProfile.deviceCategory}
        data-execution-mode={layoutProfile.executionMode}
        className="sticky top-0 z-40 w-full border-b border-border/80 bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/85 safe-area-pt select-none"
      >
        <div className="max-w-7xl mx-auto px-3 sm:px-6 h-14 flex items-center justify-between gap-2 sm:gap-4">
          {/* Bloco Esquerdo: Identidade DeepFarms Campo ou App Bar Contextual no Mobile */}
          <div className="flex items-center gap-2 min-w-0">
            {isSubpage && (
              <Link
                href={routeMeta.backHref}
                aria-label="Voltar"
                title="Voltar"
                className="md:hidden inline-flex items-center justify-center w-9 h-9 -ml-1 rounded-sm text-foreground hover:bg-muted active:scale-95 transition-all shrink-0"
              >
                <ChevronLeft className="w-5 h-5 text-primary" />
              </Link>
            )}

            <Link
              href="/home"
              className={cn(
                "flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm group min-w-0",
                isSubpage && "hidden md:flex"
              )}
              title="Ir para página inicial do DeepFarms Campo"
            >
              <div className="relative w-7 h-7 shrink-0 rounded-sm bg-primary/10 p-0.5">
                <Image
                  src="/logos/deepfarms-mark.svg"
                  alt="DeepFarms Campo"
                  width={28}
                  height={28}
                  priority
                  className="w-full h-full object-contain"
                />
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5 leading-none">
                  <span className="font-bold tracking-tight text-foreground text-sm truncate">
                    DeepFarms
                  </span>
                  <span className="text-primary font-bold text-xs px-1.5 py-0.5 rounded-sm bg-primary/10">
                    Campo
                  </span>
                </div>
                <span className="text-[10px] text-muted-foreground hidden sm:inline truncate">
                  {layoutProfile.executionMode === "standalone"
                    ? "Aplicativo de Campo (PWA)"
                    : "Operação Rural Offline-First"}
                </span>
              </div>
            </Link>

            {/* Título Contextual de App Nativo quando em subpágina no Mobile */}
            {isSubpage && (
              <div className="flex md:hidden items-center gap-2 min-w-0">
                <div className="p-1.5 rounded-sm bg-primary/10 text-primary shrink-0">
                  <ActiveIcon className="w-4 h-4" />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-bold tracking-tight text-foreground text-sm leading-tight truncate">
                    {routeMeta.title}
                  </span>
                  <span className="text-[10px] text-muted-foreground leading-tight truncate">
                    {activeFazenda?.nome ?? routeMeta.subtitle}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Navegação Horizontal para Desktop (mesmo padrão visual de Agro) */}
          <nav
            className="hidden lg:flex items-center gap-1"
            aria-label="Navegação principal"
          >
            {TOP_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = isCampoRouteActive(pathname, item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground font-semibold"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Controles Direitos: Fazenda Ativa, Status, Dispositivo, Operador e Tema */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {/* Seletor de Fazenda Ativa (mesmo estilo da Localidade Ativa do Agro) */}
            <button
              type="button"
              onClick={() => {
                if (canSelectFazenda) setDialogOpen(true);
              }}
              disabled={!canSelectFazenda}
              title={
                canSelectFazenda
                  ? "Trocar unidade produtiva ativa"
                  : activeFazenda?.nome ?? "Unidade produtiva"
              }
              className={cn(
                "inline-flex items-center gap-1 px-2 py-1 rounded-sm bg-primary/10 text-primary text-[11px] font-medium max-w-[130px] sm:max-w-[180px] transition-colors",
                canSelectFazenda ? "hover:bg-primary/15 cursor-pointer" : "cursor-default"
              )}
            >
              <MapPin className="w-3 h-3 shrink-0" />
              <span className="truncate">
                {activeFazenda?.nome ?? "Unidade ativa"}
              </span>
              {canSelectFazenda && <ChevronDown className="w-3 h-3 shrink-0" />}
            </button>

            {/* Indicadores compactos de Rede, Sync e GPS */}
            <StatusBadge
              active={isOnline}
              icon={isOnline ? SignalHigh : Signal}
              label={isOnline ? "Online" : "Offline"}
            />
            <StatusBadge
              active={syncOk}
              icon={
                syncStatus === "syncing" ? RefreshCw : syncOk ? CircleCheck : CircleAlert
              }
              label={pendingCount > 0 ? `Sync (${pendingCount})` : "Sync"}
              spinning={syncStatus === "syncing"}
              onClick={() => router.push("/sync")}
            />
            <StatusBadge
              active={gpsStatus === "DISPONIVEL"}
              icon={gpsStatus === "DISPONIVEL" ? MapPinned : MapPinOff}
              label="GPS"
              hideOnTiny
            />

            {/* Indicador Adaptativo de Ambiente (Mobile / Tablet / Standalone) */}
            <span
              data-testid="header-device-badge"
              className="hidden sm:inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-sm border border-primary/25 text-muted-foreground font-semibold"
            >
              {layoutProfile.deviceCategory === "mobile" ? (
                <Smartphone className="w-3 h-3 text-primary" />
              ) : layoutProfile.deviceCategory === "tablet" ? (
                <Tablet className="w-3 h-3 text-primary" />
              ) : null}
              <span>
                {layoutProfile.executionMode === "standalone"
                  ? "PWA"
                  : layoutProfile.deviceCategory === "mobile"
                    ? "Mobile"
                    : layoutProfile.deviceCategory === "tablet"
                      ? "Tablet"
                      : "Web"}
              </span>
            </span>

            {/* Botão Conta do Operador (mesmo estilo do botão Minha Conta do Agro) */}
            <button
              type="button"
              onClick={() => setAvatarMenuOpen(true)}
              aria-label="Conta do Operador"
              title="Conta do Operador"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm text-xs font-medium border border-border bg-background hover:bg-accent text-foreground transition-colors min-h-[34px]"
            >
              <User className="w-3.5 h-3.5 text-primary" />
              <span className="hidden sm:inline">{firstName}</span>
            </button>

            {/* Alternador de Tema Claro/Escuro */}
            <button
              type="button"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label={theme === "dark" ? "Ativar modo claro" : "Ativar modo escuro"}
              title={theme === "dark" ? "Ativar modo claro" : "Ativar modo escuro"}
              className="inline-flex items-center justify-center h-8 w-8 rounded-sm border border-border bg-background hover:bg-accent text-foreground transition-colors shrink-0"
            >
              {theme === "dark" ? (
                <Sun className="w-3.5 h-3.5 text-amber-500" />
              ) : (
                <Moon className="w-3.5 h-3.5 text-foreground" />
              )}
            </button>
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
                {theme === "dark" ? (
                  <Sun className="size-4 text-amber-500" />
                ) : (
                  <Moon className="size-4" />
                )}
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

function StatusBadge({
  active,
  icon: Icon,
  label,
  spinning = false,
  hideOnTiny = false,
  onClick,
}: {
  active: boolean;
  icon: typeof Signal;
  label: string;
  spinning?: boolean;
  hideOnTiny?: boolean;
  onClick?: () => void;
}) {
  const classes = cn(
    "inline-flex shrink-0 items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[10px] font-semibold",
    hideOnTiny && "hidden sm:inline-flex",
    active
      ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
      : "border-amber-500/30 bg-amber-500/15 text-amber-700 dark:text-amber-400",
    onClick && "cursor-pointer hover:opacity-85 active:scale-95 transition-all"
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={classes}>
        <Icon className={cn("w-3 h-3", spinning && "animate-spin")} />
        <span className="hidden md:inline">{label}</span>
      </button>
    );
  }

  return (
    <span className={classes}>
      <Icon className={cn("w-3 h-3", spinning && "animate-spin")} />
      <span className="hidden md:inline">{label}</span>
    </span>
  );
}
