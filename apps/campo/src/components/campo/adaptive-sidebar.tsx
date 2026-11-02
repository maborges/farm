"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChevronDown,
  ChevronRight,
  Laptop,
  PanelLeftClose,
  PanelLeftOpen,
  Smartphone,
  Tablet,
} from "lucide-react";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import {
  getContractedCampoModuleGroups,
  isCampoRouteActive,
  type CampoNavItem,
  type CampoNavModuleGroup,
} from "./nav-items";

function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

/**
 * Determina o estado inicial de expansão dos grupos de módulos na sidebar.
 *
 * Args:
 *   groups (CampoNavModuleGroup[]): Grupos disponíveis para os módulos contratados.
 *   pathname (string): Caminho atual da rota ativa.
 *
 * Return:
 *   Record<string, boolean>: Mapa indicando quais grupos estão expandidos.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function buildInitialExpandedState(
  groups: CampoNavModuleGroup[],
  pathname: string
): Record<string, boolean> {
  const map: Record<string, boolean> = {};
  for (const group of groups) {
    const hasActiveItem = group.items.some((item) => isCampoRouteActive(pathname, item.href));
    map[group.id] = group.id === "operacao-campo" || hasActiveItem;
  }
  return map;
}

/**
 * Sidebar retrátil adaptativa com o mesmo padrão visual do módulo Agro.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   JSX.Element: Barra lateral adaptativa com suporte a colapso e expansão por módulo.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function AdaptiveCampoSidebar() {
  const pathname = usePathname();
  const { layoutProfile, isSidebarCollapsed, toggleSidebar } = useDeviceContext();
  const { session } = useSessionStore();
  const { pendingCount } = useSyncStore();

  const moduleGroups = useMemo(
    () => getContractedCampoModuleGroups(session?.modules),
    [session?.modules]
  );

  const [expandedModules, setExpandedModules] = useState<Record<string, boolean>>(() =>
    buildInitialExpandedState(moduleGroups, pathname)
  );

  useEffect(() => {
    setExpandedModules((prev) => {
      const next = { ...prev };
      for (const group of moduleGroups) {
        if (group.items.some((item) => isCampoRouteActive(pathname, item.href))) {
          next[group.id] = true;
        } else if (next[group.id] === undefined) {
          next[group.id] = group.id === "operacao-campo";
        }
      }
      return next;
    });
  }, [moduleGroups, pathname]);

  const toggleGroup = (groupId: string) => {
    setExpandedModules((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  };

  const renderNavLink = (item: CampoNavItem) => {
    const Icon = item.icon;
    const isActive = isCampoRouteActive(pathname, item.href);
    const showSyncBadge = item.id === "sync" && pendingCount > 0;

    return (
      <Link
        key={item.id}
        href={item.href}
        title={`${item.label} — ${item.description}`}
        className={cn(
          "relative flex items-center rounded-sm transition-all min-h-[42px] px-2.5 py-2 text-xs font-medium group",
          isSidebarCollapsed ? "justify-center flex-col gap-1 px-1.5 py-2" : "gap-2.5",
          isActive
            ? "bg-primary text-primary-foreground font-semibold shadow-xs"
            : "text-muted-foreground hover:text-foreground hover:bg-muted/70"
        )}
      >
        <Icon
          className={cn(
            "w-4 h-4 shrink-0 transition-transform group-active:scale-95",
            isActive ? "text-primary-foreground" : "text-primary"
          )}
        />
        {isSidebarCollapsed ? (
          <span className="text-[10px] leading-none truncate max-w-[54px]">
            {item.shortLabel}
          </span>
        ) : (
          <div className="flex flex-col min-w-0 flex-1">
            <div className="flex items-center justify-between gap-1.5">
              <span className="truncate leading-tight">{item.label}</span>
              {showSyncBadge && (
                <span
                  className={cn(
                    "rounded-sm px-1.5 py-0.5 text-[10px] font-bold",
                    isActive
                      ? "bg-white/20 text-primary-foreground"
                      : "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                  )}
                >
                  {pendingCount}
                </span>
              )}
            </div>
            <span
              className={cn(
                "text-[10px] truncate leading-tight",
                isActive ? "text-primary-foreground/80" : "text-muted-foreground"
              )}
            >
              {item.description}
            </span>
          </div>
        )}
        {isSidebarCollapsed && showSyncBadge && (
          <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-amber-500" />
        )}
      </Link>
    );
  };

  const DeviceIcon =
    layoutProfile.deviceCategory === "tablet"
      ? Tablet
      : layoutProfile.deviceCategory === "mobile"
        ? Smartphone
        : Laptop;

  return (
    <aside
      aria-label="Menu lateral adaptativo"
      data-testid="adaptive-sidebar"
      data-collapsed={isSidebarCollapsed ? "true" : "false"}
      className={cn(
        "hidden md:flex flex-col shrink-0 border-r border-border bg-card/60 backdrop-blur-xs transition-all duration-200 sticky top-14 h-[calc(100dvh-3.5rem)] justify-between select-none",
        isSidebarCollapsed ? "w-[72px]" : "w-60"
      )}
    >
      <div className="p-2.5 space-y-3 overflow-y-auto flex-1">
        {/* Controle de Retração da Sidebar */}
        <div
          className={cn(
            "flex items-center",
            isSidebarCollapsed ? "justify-center" : "justify-between px-1"
          )}
        >
          {!isSidebarCollapsed && (
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Módulos Campo
            </span>
          )}
          <button
            type="button"
            onClick={toggleSidebar}
            aria-label={isSidebarCollapsed ? "Expandir menu lateral" : "Retrair menu lateral"}
            title={isSidebarCollapsed ? "Expandir menu lateral" : "Retrair menu lateral"}
            className="inline-flex h-7 w-7 items-center justify-center p-0 rounded-sm border border-border bg-background hover:bg-accent text-foreground transition-colors"
          >
            {isSidebarCollapsed ? (
              <PanelLeftOpen className="w-3.5 h-3.5" />
            ) : (
              <PanelLeftClose className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

        {/* Grupos de Módulos Contratados */}
        {moduleGroups.map((group, index) => {
          const isExpanded = expandedModules[group.id] ?? true;

          return (
            <div
              key={group.id}
              className={cn("space-y-1", index > 0 && "pt-2 border-t border-border/60")}
            >
              {!isSidebarCollapsed && (
                <button
                  type="button"
                  onClick={() => toggleGroup(group.id)}
                  className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-semibold text-foreground/80 hover:text-foreground rounded-sm transition-colors cursor-pointer"
                  aria-expanded={isExpanded}
                >
                  <span>{group.label}</span>
                  {isExpanded ? (
                    <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                  )}
                </button>
              )}
              {(isSidebarCollapsed || isExpanded) && (
                <div className="flex flex-col gap-1">
                  {group.items.map(renderNavLink)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Rodapé com Diagnóstico do Ambiente Detectado (mesmo padrão do Agro) */}
      <div className="p-2.5 border-t border-border/60 bg-muted/20">
        {isSidebarCollapsed ? (
          <div
            className="flex flex-col items-center gap-1 py-1 text-muted-foreground"
            title={`Ambiente: ${layoutProfile.deviceCategory === "tablet" ? "Tablet" : "Desktop"} (${layoutProfile.executionMode === "standalone" ? "PWA Instalado" : "Navegador"})`}
          >
            <DeviceIcon className="w-4 h-4 text-primary" />
            <span className="text-[9px] font-medium uppercase">
              {layoutProfile.deviceCategory === "tablet" ? "Tab" : "Web"}
            </span>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-2 px-1 py-0.5">
            <div className="flex items-center gap-2 min-w-0">
              <div className="p-1.5 rounded-sm bg-primary/10 text-primary">
                <DeviceIcon className="w-3.5 h-3.5" />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[11px] font-semibold text-foreground truncate">
                  {layoutProfile.deviceCategory === "tablet" ? "Modo Tablet" : "Modo Desktop"}
                </span>
                <span className="text-[10px] text-muted-foreground truncate">
                  {layoutProfile.executionMode === "standalone"
                    ? "PWA Instalado"
                    : "Acesso via Navegador"}
                </span>
              </div>
            </div>
            <span className="text-[9px] px-1.5 py-0.5 rounded-sm border border-border text-foreground font-semibold shrink-0">
              {layoutProfile.executionMode === "standalone" ? "App" : "Web"}
            </span>
          </div>
        )}
      </div>
    </aside>
  );
}
