"use client";

import * as React from "react";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  AppWindow,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  KeyRound,
  Laptop,
  LayoutDashboard,
  LayoutPanelLeft,
  Loader2,
  LogOut,
  Moon,
  Smartphone,
  Sun,
  Tablet,
  User,
} from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useTheme } from "@/components/theme-provider";
import { useNavigationPreference } from "@/hooks/use-navigation-preference";
import { useVisibleNavigation } from "@/hooks/use-visible-navigation";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { resolveAssetUrl } from "@/lib/runtime-config";
import { isItemActive } from "@/lib/sidebar-navigation";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";
import { ChangePasswordDialog } from "./change-password-dialog";
import { ContextSelector } from "./context-selector";
import { AppMegaMenu } from "./mega-menu/app-mega-menu";
import { NotificationBell } from "./notification-bell";
import { QuickAddMenu } from "./quick-add-menu";
import { TenantSwitcher } from "./tenant-switcher";
import { ToolbarWeatherWidget } from "./weather/toolbar-weather-widget";

interface MobileHeaderContext {
  title: string;
  subtitle: string;
  icon: React.ElementType;
}

export function Topbar(): React.ReactElement {
  const { user, logout, tenant, activeFazendaId, unidadesProdutivasAutorizadas } = useAppStore();
  const { mode, setMode, isUpdating } = useNavigationPreference();
  const { deviceCategory, executionMode, isHydrated } = useDeviceContext();
  const {
    moduleGroups,
    coreSections,
    backofficeSections,
    accessItems,
    settingsItems,
    searchParams,
  } = useVisibleNavigation();
  const pathname = usePathname();
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const [showChangePassword, setShowChangePassword] = useState(false);

  const displayName = user?.nickname?.trim() || user?.name || "Usuário";
  const userInitial = displayName.trim().charAt(0).toUpperCase() || "U";
  const fazendaAtiva = unidadesProdutivasAutorizadas.find((f) => f.id === activeFazendaId);
  const activeContextName =
    fazendaAtiva?.nome ??
    tenant?.nome ??
    (executionMode === "standalone" ? "Aplicativo de Gestão (PWA)" : "Gestão Integrada");

  const avatarSrc = (() => {
    const resolved = resolveAssetUrl(user?.foto_perfil_url);
    if (!resolved) {
      return undefined;
    }
    if (!user?.foto_perfil_cache_bust) {
      return resolved;
    }
    const base = resolved.split("?")[0];
    return `${base}?v=${encodeURIComponent(user.foto_perfil_cache_bust)}`;
  })();

  const tenantLogoSrc = resolveAssetUrl(tenant?.branding?.logoUrl);
  const isDark = resolvedTheme === "dark";
  const isSubpage = pathname !== "/dashboard";

  const mobileContext = ((): MobileHeaderContext => {
    for (const group of moduleGroups) {
      for (const section of group.sections) {
        const matched = section.items.find((item) =>
          isItemActive(item.href, pathname, searchParams, item.exact)
        );
        if (matched) {
          return {
            title: matched.label,
            subtitle: `${group.label} · ${section.label}`,
            icon: matched.icon ?? group.icon,
          };
        }
      }
    }

    for (const section of coreSections) {
      const matched = section.items.find((item) =>
        isItemActive(item.href, pathname, searchParams, item.exact)
      );
      if (matched) {
        return {
          title: matched.label,
          subtitle: `Cadastros · ${section.label}`,
          icon: matched.icon,
        };
      }
    }

    for (const section of backofficeSections) {
      const matched = section.items.find((item) =>
        isItemActive(item.href, pathname, searchParams, item.exact)
      );
      if (matched) {
        return {
          title: matched.label,
          subtitle: `Backoffice · ${section.label}`,
          icon: matched.icon,
        };
      }
    }

    const extraItem = [...accessItems, ...settingsItems].find((item) =>
      isItemActive(item.href, pathname, searchParams, item.exact)
    );
    if (extraItem) {
      return {
        title: extraItem.label,
        subtitle: activeContextName,
        icon: extraItem.icon,
      };
    }

    return {
      title: "Visão do Dia",
      subtitle: activeContextName,
      icon: LayoutDashboard,
    };
  })();

  const changeNavigationMode = (nextMode: "sidebar" | "mega-menu") => {
    if (nextMode !== mode) {
      setMode(nextMode);
    }
  };

  return (
    <header
      data-testid="web-app-header"
      data-device={deviceCategory}
      className="sticky top-0 inset-x-0 z-[var(--z-fixed)] w-full border-b border-border/80 bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/85 safe-area-pt select-none"
    >
      <div className="flex h-14 w-full min-w-0 items-center justify-between gap-2 sm:gap-4 px-3 sm:px-4">
        {/* Bloco Esquerdo: Gatilho de Navegação + Identidade / Título Contextual Mobile */}
        <div className="flex min-w-0 items-center gap-2">
          {!isHydrated ? (
            <div className="h-8 w-8" />
          ) : mode === "mega-menu" ? (
            <AppMegaMenu />
          ) : (
            <SidebarTrigger
              variant="outline"
              size="sm"
              className="h-8 w-8 p-0 rounded-sm border-border text-primary shrink-0"
              aria-label="Alternar sidebar"
            />
          )}

          {isSubpage && (
            <Link
              href="/dashboard"
              aria-label="Voltar para visão do dia"
              title="Voltar para visão do dia"
              className="md:hidden inline-flex items-center justify-center w-8 h-8 rounded-sm border border-border bg-background text-foreground hover:bg-muted active:scale-95 transition-all shrink-0"
            >
              <ChevronLeft className="w-4 h-4 text-primary" />
            </Link>
          )}

          {/* Identidade DeepFarms Gestão (Mobile Home ou Mega Menu Desktop) */}
          <Link
            href="/dashboard"
            className={cn(
              "flex items-center gap-2 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm min-w-0",
              isSubpage ? "hidden md:flex" : "flex",
              mode !== "mega-menu" && "md:hidden"
            )}
            title="Ir para Visão do Dia do DeepFarms"
          >
            <div className="relative w-7 h-7 shrink-0 rounded-sm bg-primary/10 p-0.5 flex items-center justify-center overflow-hidden">
              {tenantLogoSrc ? (
                <img
                  src={tenantLogoSrc}
                  alt={tenant?.nome ?? "DeepFarms"}
                  className="h-full w-full object-contain"
                />
              ) : (
                <Image
                  src="/logos/deepfarms-mark.svg"
                  alt="DeepFarms Gestão"
                  width={28}
                  height={28}
                  priority
                  className="w-full h-full object-contain"
                />
              )}
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1.5 leading-none">
                <span className="font-bold tracking-tight text-foreground text-sm truncate max-w-[130px] sm:max-w-[180px]">
                  {tenant?.nome ?? "DeepFarms"}
                </span>
                <span className="text-primary font-bold text-[10px] px-1.5 py-0.5 rounded-sm bg-primary/10 shrink-0">
                  Gestão
                </span>
              </div>
              <span className="text-[10px] text-muted-foreground truncate max-w-[150px] sm:max-w-[220px]">
                {activeContextName}
              </span>
            </div>
          </Link>

          {/* Título Contextual de App Nativo quando em subpágina no Mobile */}
          {isSubpage && (
            <div className="flex md:hidden items-center gap-2 min-w-0">
              <div className="p-1.5 rounded-sm bg-primary/10 text-primary shrink-0">
                {React.createElement(mobileContext.icon, { className: "w-4 h-4" })}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="font-bold tracking-tight text-foreground text-sm leading-tight truncate">
                  {mobileContext.title}
                </span>
                <span className="text-[10px] text-muted-foreground leading-tight truncate">
                  {mobileContext.subtitle}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Controles Direitos: Contexto Multiempresa, Indicador Adaptativo, Notificações, Tema e Conta */}
        <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 sm:gap-2.5">
          <div className="hidden min-w-0 flex-1 items-center justify-end gap-1.5 md:flex">
            <TenantSwitcher />
            <ChevronRight size={12} className="text-primary/40 shrink-0" />
            <ContextSelector />
            <QuickAddMenu />
            <ToolbarWeatherWidget />
          </div>

          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2 md:border-l md:border-border md:pl-3">
            {/* Atalho rápido de criação no mobile */}
            <div className="md:hidden">
              <QuickAddMenu />
            </div>

            {/* Indicador Adaptativo de Ambiente (Mobile / Tablet / Standalone / Web) */}
            <Badge
              variant="outline"
              data-testid="header-device-badge"
              className="hidden sm:inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-sm border-primary/25 text-muted-foreground"
            >
              {deviceCategory === "mobile" ? (
                <Smartphone className="w-3 h-3 text-primary" />
              ) : deviceCategory === "tablet" ? (
                <Tablet className="w-3 h-3 text-primary" />
              ) : (
                <Laptop className="w-3 h-3 text-primary" />
              )}
              <span>
                {executionMode === "standalone"
                  ? "PWA"
                  : deviceCategory === "mobile"
                    ? "Mobile"
                    : deviceCategory === "tablet"
                      ? "Tablet"
                      : "Web"}
              </span>
            </Badge>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setTheme(isDark ? "light" : "dark")}
              className="h-8 w-8 p-0 rounded-sm relative overflow-hidden text-primary hover:text-foreground"
              aria-label="Mudar o tema"
            >
              {isDark ? (
                <Sun className="size-4 shrink-0 transition-all duration-300" />
              ) : (
                <Moon className="size-4 shrink-0 transition-all duration-300" />
              )}
            </Button>

            <NotificationBell />

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  aria-label="Abrir menu do perfil"
                  className="h-8 min-w-0 gap-1.5 rounded-sm px-2 hover:bg-muted/60 hover:text-foreground aria-expanded:bg-muted/70 aria-expanded:text-foreground focus-visible:ring-primary/20"
                >
                  <Avatar className="h-5 w-5 size-5 border border-border/60 bg-muted rounded-sm">
                    <AvatarImage src={avatarSrc} alt={displayName} />
                    <AvatarFallback className="rounded-sm text-[10px] font-bold">
                      {userInitial}
                    </AvatarFallback>
                  </Avatar>
                  <span className="hidden max-w-[96px] text-left lg:flex lg:flex-col lg:justify-center">
                    <span className="truncate text-[11px] font-medium leading-tight text-foreground">
                      {displayName}
                    </span>
                  </span>
                  <ChevronDown className="hidden size-3.5 shrink-0 text-primary transition-transform duration-200 lg:block group-aria-expanded/button:rotate-180" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" sideOffset={8} className="w-56 rounded-sm">
                <DropdownMenuLabel className="flex flex-col gap-1 px-3 py-2">
                  <span className="text-sm font-semibold text-foreground leading-none">
                    {displayName}
                  </span>
                  <span className="text-xs text-muted-foreground truncate max-w-48">
                    {user?.email ?? ""}
                  </span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />

                <DropdownMenuItem
                  className="gap-2 cursor-pointer"
                  onClick={() => router.push("/dashboard/settings/account")}
                >
                  <User className="size-4 text-primary" />
                  <span className="text-primary">Meu Perfil</span>
                </DropdownMenuItem>

                <DropdownMenuItem
                  className="gap-2 cursor-pointer"
                  onClick={() => setShowChangePassword(true)}
                >
                  <KeyRound className="size-4 text-primary" />
                  <span className="text-primary">Alterar Senha</span>
                </DropdownMenuItem>

                <DropdownMenuSeparator />

                <DropdownMenuLabel className="flex items-center justify-between px-2 py-1.5 text-xs font-medium text-muted-foreground">
                  Navegação
                  {isUpdating && (
                    <Loader2
                      className="size-3 animate-spin"
                      aria-label="Salvando preferência de navegação"
                    />
                  )}
                </DropdownMenuLabel>

                <DropdownMenuItem
                  className="gap-2 cursor-pointer"
                  disabled={isUpdating || mode === "sidebar"}
                  onClick={() => changeNavigationMode("sidebar")}
                >
                  <LayoutPanelLeft className="size-4 text-primary" />
                  <span className="flex-1 text-primary">Usar barra lateral</span>
                  {mode === "sidebar" && (
                    <Check className="size-4 text-primary" aria-label="Opção selecionada" />
                  )}
                </DropdownMenuItem>

                <DropdownMenuItem
                  className="gap-2 cursor-pointer"
                  disabled={isUpdating || mode === "mega-menu"}
                  onClick={() => changeNavigationMode("mega-menu")}
                >
                  <AppWindow className="size-4 text-primary" />
                  <span className="flex-1 text-primary">Usar Mega Menu</span>
                  {mode === "mega-menu" && (
                    <Check className="size-4 text-primary" aria-label="Opção selecionada" />
                  )}
                </DropdownMenuItem>

                <DropdownMenuSeparator />

                <DropdownMenuItem
                  className="gap-2 cursor-pointer text-red-600 focus:text-red-600 focus:bg-red-50 dark:focus:bg-red-950/30 dark:focus:text-red-400"
                  onClick={logout}
                >
                  <LogOut className="size-4" />
                  <span>Sair</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Change Password Dialog */}
      <ChangePasswordDialog open={showChangePassword} onOpenChange={setShowChangePassword} />
    </header >
  );
}
