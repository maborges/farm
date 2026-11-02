"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BookText,
  ClipboardList,
  Dna,
  House,
  Plus,
  RefreshCw,
  Scale,
  ShieldHalf,
  Sprout,
  Syringe,
  Wheat,
  type LucideIcon,
} from "lucide-react";
import { BottomSheet } from "@/components/bottom-sheet";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { isCampoRouteActive } from "./nav-items";

function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

type NavItem = {
  key: string;
  label: string;
  href: string;
  icon: LucideIcon;
};

const LEFT_ITEMS: NavItem[] = [
  { key: "home", label: "Início", href: "/home", icon: House },
  { key: "tarefas", label: "Tarefas", href: "/tarefas", icon: ClipboardList },
];

const RIGHT_ITEMS: NavItem[] = [
  { key: "caderno", label: "Caderno", href: "/caderno", icon: BookText },
  { key: "sync", label: "Sync", href: "/sync", icon: RefreshCw },
];

const SHOW_NAV_ROUTES = new Set([
  "/home",
  "/sync",
  "/caderno",
  "/agricultura",
  "/pecuaria",
  "/tarefas",
  "/recomendacoes",
]);

/**
 * Barra de navegação inferior nativa para dispositivos móveis (< 768px), oculta em tablets e desktops.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   JSX.Element | null: Dock inferior com atalho central de novo apontamento.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function CampoBottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { layoutProfile } = useDeviceContext();
  const { session } = useSessionStore();
  const { pendingCount, status } = useSyncStore();
  const [quickSheetOpen, setQuickSheetOpen] = useState(false);

  const shouldShow =
    SHOW_NAV_ROUTES.has(pathname) && layoutProfile.navigationMode === "bottom-nav";

  if (!shouldShow) {
    return null;
  }

  const handleTap = () => {
    if (typeof navigator !== "undefined" && "vibrate" in navigator) {
      navigator.vibrate(10);
    }
  };

  const modules = (session?.modules ?? []).map((m) => m.toLowerCase());
  const hasAll = modules.length === 0;
  const hasAgricola = hasAll || modules.includes("agricola") || modules.includes("agricultura");
  const hasPecuaria = hasAll || modules.includes("pecuaria");

  const syncBadge =
    status === "syncing" ? "Sync" : pendingCount > 0 ? `${pendingCount}` : "";

  return (
    <>
      <nav
        aria-label="Navegação principal mobile"
        data-navigation-mode={layoutProfile.navigationMode}
        className="fixed inset-x-0 bottom-0 z-40 md:hidden border-t border-border/80 bg-card/95 backdrop-blur-lg shadow-[0_-4px_20px_rgba(0,0,0,0.08)] select-none"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        <div className="mx-auto grid h-16 max-w-lg grid-cols-5 items-center gap-1 px-2">
          {LEFT_ITEMS.map((item) => (
            <DockNavLink
              key={item.key}
              item={item}
              active={isCampoRouteActive(pathname, item.href)}
              onTap={handleTap}
            />
          ))}

          {/* Botão Central de Novo Apontamento */}
          <div className="flex items-center justify-center">
            <button
              type="button"
              onClick={() => {
                handleTap();
                setQuickSheetOpen(true);
              }}
              aria-label="Registrar nova atividade de campo"
              className="flex size-11 flex-col items-center justify-center rounded-sm border border-primary bg-primary text-primary-foreground shadow-md transition-transform active:scale-90"
            >
              <Plus className="size-5 stroke-[2.25]" />
              <span className="text-[9px] font-bold uppercase tracking-wider leading-none mt-0.5">
                Novo
              </span>
            </button>
          </div>

          {RIGHT_ITEMS.map((item) => (
            <DockNavLink
              key={item.key}
              item={item}
              active={isCampoRouteActive(pathname, item.href)}
              badge={item.key === "sync" ? syncBadge : undefined}
              isSyncing={item.key === "sync" && status === "syncing"}
              onTap={handleTap}
            />
          ))}
        </div>
      </nav>

      {/* Bottom Sheet de Lançamento Rápido de Atividades */}
      <BottomSheet
        open={quickSheetOpen}
        onOpenChange={setQuickSheetOpen}
        title="Novo Apontamento de Campo"
        description="Selecione o registro que deseja iniciar agora mesmo sem conexão."
      >
        <div className="flex flex-col gap-3 p-4">
          {hasAgricola && (
            <div>
              <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Módulo Agrícola
              </p>
              <div className="grid grid-cols-2 gap-2">
                <QuickLaunchButton
                  label="Caderno de Campo"
                  sublabel="Ocorrência / Foto"
                  icon={BookText}
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/caderno");
                  }}
                />
                <QuickLaunchButton
                  label="Aplicação"
                  sublabel="Defensivo / Insumo"
                  icon={Sprout}
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/aplicacao");
                  }}
                />
                <QuickLaunchButton
                  label="Colheita"
                  sublabel="Cargas e umidade"
                  icon={Wheat}
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/colheita");
                  }}
                />
                <QuickLaunchButton
                  label="Entrega de EPI"
                  sublabel="Comprovante"
                  icon={ShieldHalf}
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/epi");
                  }}
                />
              </div>
            </div>
          )}

          {hasPecuaria && (
            <div>
              <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Módulo Pecuária
              </p>
              <div className="grid grid-cols-2 gap-2">
                <QuickLaunchButton
                  label="Pesagem"
                  sublabel="Animal ou lote"
                  icon={Scale}
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/pesagem");
                  }}
                />
                <QuickLaunchButton
                  label="Vacinação"
                  sublabel="Manejo sanitário"
                  icon={Syringe}
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/vacinacao");
                  }}
                />
                <QuickLaunchButton
                  label="Reprodução"
                  sublabel="Cobertura / Parto"
                  icon={Dna}
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/reproducao/cobertura");
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </BottomSheet>
    </>
  );
}

function DockNavLink({
  item,
  active,
  badge,
  isSyncing,
  onTap,
}: {
  item: NavItem;
  active: boolean;
  badge?: string;
  isSyncing?: boolean;
  onTap: () => void;
}) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      onClick={onTap}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative flex h-12 flex-col items-center justify-center gap-1 rounded-sm px-1 text-center transition-all duration-150 active:scale-95",
        active
          ? "bg-primary/12 text-primary font-semibold"
          : "text-muted-foreground hover:text-foreground"
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 h-0.5 w-6 rounded-full transition-all",
          active ? "bg-primary" : "bg-transparent"
        )}
      />
      <Icon
        className={cn(
          "size-4.5 transition-transform",
          active && "scale-105",
          isSyncing && "animate-spin"
        )}
      />
      <span className="max-w-full truncate text-[10px] leading-none">{item.label}</span>
      {badge && (
        <span className="absolute right-1.5 top-1 inline-flex min-w-[16px] items-center justify-center rounded-sm bg-amber-500 px-1 py-0.2 text-[9px] font-bold leading-tight text-white">
          {badge}
        </span>
      )}
    </Link>
  );
}

function QuickLaunchButton({
  label,
  sublabel,
  icon: Icon,
  onClick,
}: {
  label: string;
  sublabel: string;
  icon: LucideIcon;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2.5 rounded-sm border border-border bg-card p-3 text-left shadow-2xs transition-all hover:bg-muted/70 active:scale-95"
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary">
        <Icon className="size-4.5" />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-xs font-bold text-foreground">{label}</span>
        <span className="block truncate text-[10px] text-muted-foreground">{sublabel}</span>
      </span>
    </button>
  );
}
