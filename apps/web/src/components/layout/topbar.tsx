"use client";

import { useAppStore } from "@/lib/stores/app-store";
import { ContextSelector } from "./context-selector";
import { TenantSwitcher } from "./tenant-switcher";
import { NotificationBell } from "./notification-bell";
import { ToolbarWeatherWidget } from "./weather/toolbar-weather-widget";
import { AppWindow, Check, ChevronDown, ChevronRight, KeyRound, LayoutPanelLeft, Loader2, LogOut, Moon, Sprout, Sun, User } from "lucide-react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTheme } from "@/components/theme-provider";
import { resolveAssetUrl } from "@/lib/runtime-config";
import { SidebarTrigger } from "../ui/sidebar";
import { Button } from "../ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import {
    DropdownMenu,
    DropdownMenuTrigger,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
} from "../ui/dropdown-menu";
import { ChangePasswordDialog } from "./change-password-dialog";
import { AppMegaMenu } from "./mega-menu/app-mega-menu";
import { QuickAddMenu } from "./quick-add-menu";
import { useNavigationPreference } from "@/hooks/use-navigation-preference";

export function Topbar() {
    const { user, logout, tenant } = useAppStore();
    const { mode, setMode, isUpdating } = useNavigationPreference();
    const router = useRouter();
    const { resolvedTheme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    const [showChangePassword, setShowChangePassword] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    const displayName = user?.nickname?.trim() || user?.name || "Usuário";
    const userInitial = displayName.trim().charAt(0).toUpperCase() ?? "U";

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

    const tenantLogoSrc = (() => {
        return resolveAssetUrl(tenant?.branding?.logoUrl);
    })();

    const isDark = resolvedTheme === "dark";

    const changeNavigationMode = (nextMode: "sidebar" | "mega-menu") => {
        if (nextMode !== mode) {
            setMode(nextMode);
        }
    };

    return (
        <header className="glass-chrome !bg-sidebar/45 dark:!bg-sidebar/35 absolute inset-x-0 top-0 z-[var(--z-fixed)] w-full">
            <div className="flex h-14 w-full min-w-0 items-center justify-between gap-4 px-4">
                <div className="flex shrink-0 items-center gap-2">
                    {!mounted ? (
                        <div className="h-9 w-9" /> // placeholder para evitar layout shift
                    ) : mode === "mega-menu" ? (
                        <>
                            <AppMegaMenu />
                            <Link href="/dashboard" className="hidden sm:flex items-center gap-2.5 px-2 ml-2 outline-none">
                                <div className="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-md bg-primary/5 text-primary shadow-sm ring-1 ring-border/60">
                                    {tenantLogoSrc ? (
                                        <img
                                            src={tenantLogoSrc}
                                            alt={tenant?.nome ?? "Logo"}
                                            className="h-full w-full object-contain p-1.5"
                                        />
                                    ) : (
                                        <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-sm">
                                            <Sprout className="size-3.5" />
                                        </div>
                                    )}
                                </div>
                                <span className="font-black text-primary text-lg truncate">
                                    {tenant?.nome ?? "DeepFarms"}
                                </span>
                            </Link>
                        </>
                    ) : (
                        <SidebarTrigger
                            className="text-primary"
                            aria-label="Alternar sidebar"
                        />
                    )}
                </div>

                <div className="flex min-w-0 flex-1 items-center justify-end gap-3">
                    <div className="hidden min-w-0 flex-1 items-center justify-end gap-1.5 sm:flex">
                        <TenantSwitcher />
                        <ChevronRight size={12} className="text-primary/40 shrink-0" />
                        <ContextSelector />
                        <QuickAddMenu />
                        <ToolbarWeatherWidget />
                    </div>

                    <div className="flex shrink-0 items-center gap-2 border-l border-border pl-3">
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => setTheme(isDark ? "light" : "dark")}
                            className="relative overflow-hidden text-primary hover:text-foreground"
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
                                    variant="ghost"
                                    size="sm"
                                    aria-label="Abrir menu do perfil"
                                    className="min-w-0 gap-1.5 rounded-full px-1.5 hover:bg-muted/60 hover:text-foreground aria-expanded:bg-muted/70 aria-expanded:text-foreground focus-visible:ring-primary/20"
                                >
                                    <Avatar className="size-8 border border-border bg-muted">
                                        <AvatarImage
                                            src={avatarSrc}
                                            alt={displayName}
                                        />
                                        <AvatarFallback>{userInitial}</AvatarFallback>
                                    </Avatar>
                                    <span className="hidden max-w-[96px] text-left md:flex md:flex-col md:justify-center">
                                        <span className="line-clamp-2 text-[11px] font-medium leading-tight text-foreground break-words">
                                            {displayName}
                                        </span>
                                    </span>
                                    <ChevronDown className="hidden size-3.5 shrink-0 text-primary transition-transform duration-200 md:block group-aria-expanded/button:rotate-180" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" sideOffset={8} className="w-56">
                                <DropdownMenuLabel className="flex flex-col gap-1 px-3 py-2">
                                    <span className="text-sm font-semibold text-foreground leading-none">{displayName}</span>
                                    <span className="text-xs text-muted-foreground truncate max-w-48">{user?.email ?? ""}</span>
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
                                    {isUpdating && <Loader2 className="size-3 animate-spin" aria-label="Salvando preferência de navegação" />}
                                </DropdownMenuLabel>

                                <DropdownMenuItem
                                    className="gap-2 cursor-pointer"
                                    disabled={isUpdating || mode === "sidebar"}
                                    onClick={() => changeNavigationMode("sidebar")}
                                >
                                    <LayoutPanelLeft className="size-4 text-primary" />
                                    <span className="flex-1 text-primary">Usar barra lateral</span>
                                    {mode === "sidebar" && <Check className="size-4 text-primary" aria-label="Opção selecionada" />}
                                </DropdownMenuItem>

                                <DropdownMenuItem
                                    className="gap-2 cursor-pointer"
                                    disabled={isUpdating || mode === "mega-menu"}
                                    onClick={() => changeNavigationMode("mega-menu")}
                                >
                                    <AppWindow className="size-4 text-primary" />
                                    <span className="flex-1 text-primary">Usar Mega Menu</span>
                                    {mode === "mega-menu" && <Check className="size-4 text-primary" aria-label="Opção selecionada" />}
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
        </header>
    );
}
