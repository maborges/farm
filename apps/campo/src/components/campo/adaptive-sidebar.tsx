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
  Sprout,
  Tablet,
} from "lucide-react";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import {
  getContractedCampoModuleGroups,
  isCampoRouteActive,
  type CampoNavModuleGroup,
} from "./nav-items";

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
 * Sidebar retrátil adaptativa para Tablet (Navigation Rail) e Desktop, separando itens por módulo contratado.
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

  const isTablet = layoutProfile.deviceCategory === "tablet";

  return (
    <aside
      aria-label="Menu de navegação por módulo do Campo"
      data-device-category={layoutProfile.deviceCategory}
      data-collapsed={isSidebarCollapsed}
      className={[
        "hidden md:flex flex-col shrink-0 border-r border-border bg-card/95 backdrop-blur-md transition-[width] duration-200 ease-out select-none",
        isSidebarCollapsed ? "w-16" : "w-64",
      ].join(" ")}
    >
      {/* Topo da Sidebar com Identidade AgroCampo e botão de retração */}
      <div className="flex h-14 items-center justify-between border-b border-border px-3">
        {!isSidebarCollapsed && (
          <Link href="/home" className="flex items-center gap-2.5 min-w-0">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-sm bg-primary text-primary-foreground shadow-xs">
              <Sprout className="size-4" />
            </span>
            <div className="truncate">
              <p className="text-sm font-bold leading-none tracking-tight text-foreground">
                AgroCampo
              </p>
              <p className="mt-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Operação Rural
              </p>
            </div>
          </Link>
        )}

        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={isSidebarCollapsed ? "Expandir menu lateral" : "Retrair menu lateral"}
          title={isSidebarCollapsed ? "Expandir menu lateral" : "Retrair menu lateral"}
          className={[
            "inline-flex size-8 items-center justify-center rounded-sm border border-border bg-background text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
            isSidebarCollapsed ? "mx-auto" : "",
          ].join(" ")}
        >
          {isSidebarCollapsed ? (
            <PanelLeftOpen className="size-4" />
          ) : (
            <PanelLeftClose className="size-4" />
          )}
        </button>
      </div>

      {/* Grupos de Módulos Contratados */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-3">
        {moduleGroups.map((group) => {
          const isExpanded = expandedModules[group.id] ?? true;

          return (
            <div key={group.id} className="space-y-1">
              {!isSidebarCollapsed ? (
                <button
                  type="button"
                  onClick={() => toggleGroup(group.id)}
                  className="flex w-full items-center justify-between rounded-sm px-2 py-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-colors"
                >
                  <span className="truncate">{group.label}</span>
                  {isExpanded ? (
                    <ChevronDown className="size-3.5 shrink-0" />
                  ) : (
                    <ChevronRight className="size-3.5 shrink-0" />
                  )}
                </button>
              ) : (
                <div className="mx-auto my-1 h-px w-8 bg-border" />
              )}

              {(isExpanded || isSidebarCollapsed) && (
                <ul className="space-y-1">
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const isActive = isCampoRouteActive(pathname, item.href);
                    const showSyncBadge = item.id === "sync" && pendingCount > 0;

                    return (
                      <li key={item.id}>
                        <Link
                          href={item.href}
                          title={isSidebarCollapsed ? `${item.label} — ${item.description}` : undefined}
                          className={[
                            "group relative flex items-center gap-3 rounded-sm px-2.5 py-2 text-xs font-medium transition-all",
                            isSidebarCollapsed ? "justify-center px-0 py-2.5" : "",
                            isActive
                              ? "bg-primary/12 text-primary font-semibold border border-primary/25 shadow-2xs"
                              : "text-muted-foreground hover:bg-muted/70 hover:text-foreground border border-transparent",
                          ].join(" ")}
                        >
                          <Icon
                            className={[
                              "size-4 shrink-0 transition-transform",
                              isActive
                                ? "text-primary scale-105"
                                : "text-muted-foreground group-hover:text-foreground",
                            ].join(" ")}
                          />
                          {!isSidebarCollapsed && (
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center justify-between gap-1.5">
                                <p className="truncate leading-tight">{item.label}</p>
                                {showSyncBadge && (
                                  <span className="rounded-sm bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-bold text-amber-700 dark:text-amber-300">
                                    {pendingCount}
                                  </span>
                                )}
                              </div>
                              <p className="truncate text-[10px] font-normal text-muted-foreground/80">
                                {item.description}
                              </p>
                            </div>
                          )}
                          {isSidebarCollapsed && showSyncBadge && (
                            <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-amber-500" />
                          )}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </nav>

      {/* Rodapé com indicador do ambiente detectado */}
      <div className="border-t border-border p-2.5">
        <div
          className={[
            "flex items-center gap-2 rounded-sm bg-muted/60 px-2.5 py-2 text-[11px] text-muted-foreground",
            isSidebarCollapsed ? "justify-center px-0" : "",
          ].join(" ")}
          title={`Ambiente detectado: ${isTablet ? "Tablet" : "Desktop"} (${layoutProfile.executionMode})`}
        >
          {isTablet ? (
            <Tablet className="size-3.5 shrink-0 text-primary" />
          ) : (
            <Laptop className="size-3.5 shrink-0 text-primary" />
          )}
          {!isSidebarCollapsed && (
            <div className="min-w-0 flex-1 truncate">
              <span className="font-semibold text-foreground">
                {isTablet ? "Modo Tablet" : "Modo Desktop"}
              </span>
              <span className="ml-1 text-[10px] uppercase text-muted-foreground">
                • {layoutProfile.executionMode === "standalone" ? "PWA" : "Web"}
              </span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

