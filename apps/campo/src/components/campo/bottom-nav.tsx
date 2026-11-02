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
 * Barra de navegação inferior móvel com o mesmo padrão visual de abas do módulo Agro.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   JSX.Element | null: Dock móvel de 5 colunas com indicador superior e pílula ativa.
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
        aria-label="Navegação móvel"
        data-testid="mobile-bottom-dock"
        data-navigation-mode={layoutProfile.navigationMode}
        className={cn(
          "md:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border/80 bg-card/95 backdrop-blur-lg supports-[backdrop-filter]:bg-card/85 shadow-[0_-2px_12px_rgba(0,0,0,0.06)] safe-area-pb select-none",
          layoutProfile.executionMode === "standalone" && "pb-1"
        )}
      >
        <div className="grid grid-cols-5 items-center h-16 max-w-lg mx-auto px-1">
          {LEFT_ITEMS.map((item) => (
            <DockNavLink
              key={item.key}
              item={item}
              isActive={isCampoRouteActive(pathname, item.href)}
              onTap={handleTap}
            />
          ))}

          {/* Aba central de Novo Registro (mesmo padrão de aba do dock do Agro) */}
          <button
            type="button"
            onClick={() => {
              handleTap();
              setQuickSheetOpen(true);
            }}
            aria-label="Registrar nova atividade de campo"
            className="relative flex flex-col items-center justify-center h-full min-h-[48px] rounded-sm transition-all text-[11px] font-semibold text-primary active:scale-95"
          >
            <div className="px-3 py-1 rounded-full bg-primary text-primary-foreground shadow-2xs flex items-center justify-center">
              <Plus className="w-4 h-4" />
            </div>
            <span className="leading-tight mt-0.5 truncate max-w-[68px]">Novo</span>
          </button>

          {RIGHT_ITEMS.map((item) => (
            <DockNavLink
              key={item.key}
              item={item}
              isActive={isCampoRouteActive(pathname, item.href)}
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
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Módulo Agrícola
              </p>
              <div className="grid grid-cols-2 gap-2">
                <QuickLaunchButton
                  label="Caderno de Campo"
                  sublabel="Ocorrência / Foto"
                  icon={BookText}
                  tone="emerald"
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/caderno");
                  }}
                />
                <QuickLaunchButton
                  label="Aplicação"
                  sublabel="Defensivo / Insumo"
                  icon={Sprout}
                  tone="emerald"
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/aplicacao");
                  }}
                />
                <QuickLaunchButton
                  label="Colheita"
                  sublabel="Cargas e umidade"
                  icon={Wheat}
                  tone="amber"
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/colheita");
                  }}
                />
                <QuickLaunchButton
                  label="Entrega de EPI"
                  sublabel="Comprovante"
                  icon={ShieldHalf}
                  tone="blue"
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
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Módulo Pecuária
              </p>
              <div className="grid grid-cols-2 gap-2">
                <QuickLaunchButton
                  label="Pesagem"
                  sublabel="Animal ou lote"
                  icon={Scale}
                  tone="amber"
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/pesagem");
                  }}
                />
                <QuickLaunchButton
                  label="Vacinação"
                  sublabel="Manejo sanitário"
                  icon={Syringe}
                  tone="blue"
                  onClick={() => {
                    setQuickSheetOpen(false);
                    router.push("/campo/vacinacao");
                  }}
                />
                <QuickLaunchButton
                  label="Reprodução"
                  sublabel="Cobertura / Parto"
                  icon={Dna}
                  tone="purple"
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
  isActive,
  badge,
  isSyncing,
  onTap,
}: {
  item: NavItem;
  isActive: boolean;
  badge?: string;
  isSyncing?: boolean;
  onTap: () => void;
}) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      onClick={onTap}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "relative flex flex-col items-center justify-center h-full min-h-[48px] rounded-sm transition-all text-[11px] font-medium active:scale-95",
        isActive
          ? "text-primary font-semibold"
          : "text-muted-foreground hover:text-foreground"
      )}
    >
      {isActive && (
        <span
          className="absolute top-0 left-1/2 -translate-x-1/2 w-7 h-0.5 rounded-full bg-primary"
          aria-hidden="true"
        />
      )}

      <div
        className={cn(
          "px-3 py-1 rounded-full transition-colors flex items-center justify-center",
          isActive ? "bg-primary/15 text-primary" : "text-current"
        )}
      >
        <Icon className={cn("w-4 h-4", isSyncing && "animate-spin")} />
      </div>
      <span className="leading-tight mt-0.5 truncate max-w-[68px]">
        {item.label}
      </span>

      {badge && (
        <span className="absolute right-2 top-1.5 inline-flex min-w-[15px] items-center justify-center rounded-sm bg-amber-500 px-1 py-0.2 text-[9px] font-bold leading-tight text-white">
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
  tone,
  onClick,
}: {
  label: string;
  sublabel: string;
  icon: LucideIcon;
  tone: "emerald" | "amber" | "blue" | "purple";
  onClick: () => void;
}) {
  const toneClass = {
    emerald: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    amber: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    blue: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    purple: "bg-purple-500/10 text-purple-600 dark:text-purple-400",
  }[tone];

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2.5 rounded-sm border border-border bg-card p-3 text-left shadow-xs transition-all hover:border-primary/50 active:scale-95"
    >
      <div className={cn("p-2 rounded-sm shrink-0", toneClass)}>
        <Icon className="w-4 h-4" />
      </div>
      <span className="min-w-0">
        <span className="block truncate text-xs font-semibold text-foreground">{label}</span>
        <span className="block truncate text-[10px] text-muted-foreground">{sublabel}</span>
      </span>
    </button>
  );
}
