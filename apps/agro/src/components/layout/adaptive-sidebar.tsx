"use client";

import * as React from "react";
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
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { cn } from "@/lib/utils";
import { AGRO_NAV_ITEMS, type AgroNavItem } from "./nav-items";

export function AdaptiveSidebar(): React.ReactElement {
  const pathname = usePathname();
  const { deviceCategory, executionMode, sidebarCollapsed, toggleSidebar } = useDeviceContext();

  const [expandedGroups, setExpandedGroups] = React.useState<{
    operacional: boolean;
    identidade: boolean;
  }>({
    operacional: true,
    identidade: true,
  });

  // Garante que o grupo do item selecionado expanda automaticamente ao navegar
  React.useEffect(() => {
    const activeItem = AGRO_NAV_ITEMS.find((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href)
    );
    if (activeItem) {
      setExpandedGroups((prev) => ({
        ...prev,
        [activeItem.group]: true,
      }));
    }
  }, [pathname]);

  const toggleGroup = (group: "operacional" | "identidade") => {
    setExpandedGroups((prev) => ({
      ...prev,
      [group]: !prev[group],
    }));
  };

  const operacionais = AGRO_NAV_ITEMS.filter((item) => item.group === "operacional");
  const identidade = AGRO_NAV_ITEMS.filter((item) => item.group === "identidade");

  const renderNavLink = (item: AgroNavItem) => {
    const Icon = item.icon;
    const isActive =
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

    return (
      <Link
        key={item.href}
        href={item.href}
        title={`${item.label} — ${item.pageSubtitle}`}
        className={cn(
          "flex items-center rounded-sm transition-all min-h-[42px] px-2.5 py-2 text-xs font-medium group",
          sidebarCollapsed ? "justify-center flex-col gap-1 px-1.5 py-2" : "gap-2.5",
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
        {sidebarCollapsed ? (
          <span className="text-[10px] leading-none truncate max-w-[54px]">
            {item.shortLabel}
          </span>
        ) : (
          <div className="flex flex-col min-w-0 flex-1">
            <span className="truncate leading-tight">{item.label}</span>
            <span
              className={cn(
                "text-[10px] truncate leading-tight",
                isActive ? "text-primary-foreground/80" : "text-muted-foreground"
              )}
            >
              {item.pageSubtitle}
            </span>
          </div>
        )}
      </Link>
    );
  };

  const DeviceIcon =
    deviceCategory === "tablet"
      ? Tablet
      : deviceCategory === "mobile"
      ? Smartphone
      : Laptop;

  return (
    <aside
      aria-label="Menu lateral adaptativo"
      data-testid="adaptive-sidebar"
      data-collapsed={sidebarCollapsed ? "true" : "false"}
      className={cn(
        "hidden md:flex flex-col shrink-0 border-r border-border bg-card/60 backdrop-blur-xs transition-all duration-200 sticky top-14 h-[calc(100dvh-3.5rem)] justify-between select-none",
        sidebarCollapsed ? "w-[72px]" : "w-60"
      )}
    >
      <div className="p-2.5 space-y-3 overflow-y-auto flex-1">
        {/* Controle de Retração da Sidebar */}
        <div className={cn("flex items-center", sidebarCollapsed ? "justify-center" : "justify-between px-1")}>
          {!sidebarCollapsed && (
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Módulos Agro
            </span>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={toggleSidebar}
            aria-label={sidebarCollapsed ? "Expandir menu lateral" : "Retrair menu lateral"}
            title={sidebarCollapsed ? "Expandir menu lateral" : "Retrair menu lateral"}
            className="h-7 w-7 p-0 rounded-sm"
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen className="w-3.5 h-3.5" />
            ) : (
              <PanelLeftClose className="w-3.5 h-3.5" />
            )}
          </Button>
        </div>

        {/* Grupo 1: Ferramentas Operacionais */}
        <div className="space-y-1">
          {!sidebarCollapsed && (
            <button
              type="button"
              onClick={() => toggleGroup("operacional")}
              className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-semibold text-foreground/80 hover:text-foreground rounded-sm transition-colors cursor-pointer"
              aria-expanded={expandedGroups.operacional}
            >
              <span>Ferramentas de Campo</span>
              {expandedGroups.operacional ? (
                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
              )}
            </button>
          )}
          {(sidebarCollapsed || expandedGroups.operacional) && (
            <div className="flex flex-col gap-1">
              {operacionais.map(renderNavLink)}
            </div>
          )}
        </div>

        {/* Grupo 2: Rede & Identidade */}
        <div className="space-y-1 pt-2 border-t border-border/60">
          {!sidebarCollapsed && (
            <button
              type="button"
              onClick={() => toggleGroup("identidade")}
              className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-semibold text-foreground/80 hover:text-foreground rounded-sm transition-colors cursor-pointer"
              aria-expanded={expandedGroups.identidade}
            >
              <span>Comunidade & Conta</span>
              {expandedGroups.identidade ? (
                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
              )}
            </button>
          )}
          {(sidebarCollapsed || expandedGroups.identidade) && (
            <div className="flex flex-col gap-1">
              {identidade.map(renderNavLink)}
            </div>
          )}
        </div>
      </div>

      {/* Rodapé com Diagnóstico do Ambiente Detectado */}
      <div className="p-2.5 border-t border-border/60 bg-muted/20">
        {sidebarCollapsed ? (
          <div
            className="flex flex-col items-center gap-1 py-1 text-muted-foreground"
            title={`Ambiente: ${deviceCategory === "tablet" ? "Tablet" : "Desktop"} (${executionMode === "standalone" ? "PWA Instalado" : "Navegador"})`}
          >
            <DeviceIcon className="w-4 h-4 text-primary" />
            <span className="text-[9px] font-medium uppercase">
              {deviceCategory === "tablet" ? "Tab" : "Web"}
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
                  {deviceCategory === "tablet" ? "Modo Tablet" : "Modo Desktop"}
                </span>
                <span className="text-[10px] text-muted-foreground truncate">
                  {executionMode === "standalone" ? "PWA Instalado" : "Acesso via Navegador"}
                </span>
              </div>
            </div>
            <Badge variant="outline" className="text-[9px] px-1.5 py-0 rounded-sm shrink-0">
              {executionMode === "standalone" ? "App" : "Web"}
            </Badge>
          </div>
        )}
      </div>
    </aside>
  );
}

