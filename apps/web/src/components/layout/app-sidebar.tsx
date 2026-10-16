"use client";

import React, { useCallback, useDeferredValue, useMemo, useRef, useState } from "react";
import { useAppStore } from "@/lib/stores/app-store";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarMenuSub,
    SidebarMenuSubItem,
    SidebarMenuSubButton,
    useSidebar,
} from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    ChevronRight, ChevronDown, Sprout,
    LayoutDashboard,
    AlertCircle,
    Search, X,
    BookOpen,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useVisibleNavigation, canSeeTenantItem } from "@/hooks/use-visible-navigation";
import { ModuleGate } from "../shared/module-gate";
import { cn } from "@/lib/utils";
import { resolveAssetUrl } from "@/lib/runtime-config";
import { hasBackofficePermission, hasTenantPermission } from "@/lib/permissions";
import type { BackofficeRole, PlanTierId, TenantCustomPermissions, TenantRole, User } from "@/types/global";
import { tierAtLeast } from "@/lib/constants/planos";
import {
    CORE_CADASTROS,
    MODULOS_OPERACIONAIS,
    BACKOFFICE_SECTIONS,
} from "@/lib/sidebar-config";
import {
    getSidebarModuleFromPath,
    getActiveSectionFromPath,
    getActiveBackofficeSectionFromPath,
    isItemActive,
    resolveToggle,
    type SidebarModuleKey,
    type ToggleState,
} from "@/lib/sidebar-navigation";

type ModuleKey = SidebarModuleKey;

type SearchableItem = {
    href: string;
    icon: React.ElementType;
    label: string;
    tip?: string;
    group: string;
    section?: string;
    permission?: string;
    minimumTier?: PlanTierId;
    moduleId?: string;
    alertBadge?: boolean;
    activeClassName?: string;
    exact?: boolean;
};

function normalizeSearchValue(value: string) {
    return value
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

function itemMatchesSearch(item: SearchableItem, query: string) {
    const haystack = normalizeSearchValue([
        item.label,
        item.tip,
        item.group,
        item.section,
        item.href,
    ].filter(Boolean).join(" "));
    return haystack.includes(query);
}

// Active button style per module
const activeMenuClass =
    "relative data-[active=true]:bg-primary/5 data-[active=true]:text-primary data-[active=true]:font-semibold before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[2px] before:bg-primary before:rounded-full before:opacity-0 data-[active=true]:before:opacity-100 transition-all";

const moduleActive: Record<string, string> = {
    A1: activeMenuClass,
    P1: activeMenuClass,
    F1: activeMenuClass,
    O1: activeMenuClass,
    RH: activeMenuClass,
    RH2: activeMenuClass,
    AM1: activeMenuClass,
};

const backofficeActive = activeMenuClass;

// Get active style for a section header based on the module key
function getSectionActiveStyle(moduleKey: string) {
    const activeClass = moduleActive[moduleKey] || "data-[active=true]:bg-primary/5 data-[active=true]:text-primary";
    return cn(
        "w-full px-1.5 py-0.5 text-xs font-semibold text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        activeClass
    );
}

function BackofficeNav({
    pathname,
    searchParams,
    user,
    backofficeToggle,
    setBackofficeToggle,
    onNavigate,
}: {
    pathname: string;
    searchParams: URLSearchParams;
    user: User | null;
    backofficeToggle: Record<string, ToggleState>;
    setBackofficeToggle: React.Dispatch<React.SetStateAction<Record<string, ToggleState>>>;
    onNavigate: () => void;
}) {
    const role = user?.role as BackofficeRole | undefined;
    const isSuperuser = user?.is_superuser;

    // Só mostra se o usuário tem role de backoffice ou é superuser
    if (!role && !isSuperuser) return null;

    const canSee = (permission?: string) => {
        if (!permission) return true;
        if (isSuperuser) return true;
        return hasBackofficePermission(role, permission);
    };

    // Filtra seções: só mostra se pelo menos 1 item for visível
    const visibleSections = BACKOFFICE_SECTIONS.map((section) => ({
        ...section,
        items: section.items.filter((item) => canSee(item.permission)),
    })).filter((section) => section.items.length > 0);

    if (visibleSections.length === 0) return null;

    // Determina qual seção deve estar aberta
    const activeSectionKey = getActiveBackofficeSectionFromPath(pathname);

    return (
        <SidebarGroup>
            <SidebarGroupLabel>Administração SaaS</SidebarGroupLabel>
            <SidebarGroupContent>
                <SidebarMenu>
                    {visibleSections.map((section) => {
                        const sectionActive = section.items.some((item) =>
                            isItemActive(item.href, pathname, searchParams, item.exact)
                        );

                        // Se a seção tem apenas 1 item, renderiza direto (sem Collapsible)
                        if (section.items.length === 1) {
                            const item = section.items[0];
                            const Icon = item.icon;
                            return (
                                <SidebarMenuItem key={item.href}>
                                    <SidebarMenuButton
                                        render={<Link href={item.href} onClick={onNavigate} />}
                                        isActive={isItemActive(item.href, pathname, searchParams, item.exact)}
                                        tooltip={item.tip}
                                        className={backofficeActive}
                                    >
                                        <Icon className="size-3.5 flex-shrink-0 text-primary" />
                                        <span className="truncate">{item.label}</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            );
                        }

                        // Seção com múltiplos itens
                        const SectionIcon = section.icon;
                        const isActiveByRoute = activeSectionKey === section.key;
                        const isOpen = resolveToggle(backofficeToggle[section.key], isActiveByRoute);
                        const submenuId = `sidebar-backoffice-${section.key}`;

                        return (
                            <SidebarMenuItem key={section.key}>
                                <SidebarMenuButton
                                    onClick={() => {
                                        setBackofficeToggle((prev) => ({
                                            ...prev,
                                            [section.key]: isOpen ? "closed" : "open",
                                        }));
                                    }}
                                    isActive={sectionActive}
                                    tooltip={section.label}
                                    className={backofficeActive}
                                    aria-expanded={isOpen}
                                    aria-controls={submenuId}
                                >
                                    <SectionIcon className="size-3.5 text-primary" />
                                    <span className="font-semibold">{section.label}</span>
                                    {isOpen ? <ChevronDown className="ml-auto size-3.5 " /> : <ChevronRight className="ml-auto size-3.5 " />}
                                </SidebarMenuButton>
                                {isOpen && (
                                    <SidebarMenuSub id={submenuId}>
                                        {section.items.map(({ href, icon: Icon, label, tip }) => (
                                            <SidebarMenuSubItem key={href}>
                                                <SidebarMenuSubButton title={tip} isActive={isItemActive(href, pathname, searchParams, section.items.find(i => i.href === href)?.exact)} render={<Link href={href} onClick={onNavigate} />}>
                                                    <Icon className="size-3.5 text-primary" />
                                                    {label}
                                                </SidebarMenuSubButton>
                                            </SidebarMenuSubItem>
                                        ))}
                                    </SidebarMenuSub>
                                )}
                            </SidebarMenuItem>
                        );
                    })}
                </SidebarMenu>
            </SidebarGroupContent>
        </SidebarGroup>
    );
}

export function AppSidebar() {
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const { isMobile, setOpenMobile } = useSidebar();
    const tenant = useAppStore((state) => state.tenant);
    const user = useAppStore((state) => state.user);
    const activePlanTier = useAppStore((state) => state.activePlanTier());

    const { moduleGroups, coreSections, backofficeSections, accessItems, settingsItems, activeModule, activeBackofficeSection } = useVisibleNavigation();

    // ── Unified toggle state ───────────────────────────────────────────────
    // Each key maps to "auto" | "open" | "closed"
    const [moduleToggle, setModuleToggle] = useState<Record<string, ToggleState>>({});
    const [backofficeToggle, setBackofficeToggle] = useState<Record<string, ToggleState>>({});
    const [searchQuery, setSearchQuery] = useState("");
    const deferredSearchQuery = useDeferredValue(searchQuery);

    // Track the previous active module to reset manual toggles on context change
    const prevActiveModuleRef = useRef<ModuleKey>("");



    // ── Navigation effect: reset manual toggles on context change ──────────
    React.useEffect(() => {
        const prevModule = prevActiveModuleRef.current;
        prevActiveModuleRef.current = activeModule;

        if (prevModule && prevModule !== activeModule) {
            // Module changed: reset the old module's toggles to auto
            setModuleToggle((prev) => {
                const next = { ...prev };
                delete next[prevModule];
                return next;
            });
        }
    }, [activeModule]);

    // ── Close mobile drawer on navigation ──────────────────────────────────
    const handleNavigation = useCallback(() => {
        if (isMobile) {
            setOpenMobile(false);
        }
    }, [isMobile, setOpenMobile]);

    // ── Query de alertas de caderno desatualizado ──────────────────────────
    const { data: cadernoAlertas = [] } = useQuery<Array<{ safra_id: string; mensagem: string }>>({
        queryKey: ["caderno-alertas"],
        queryFn: async () => {
            try {
                return await apiFetch("/caderno/alertas", { suppressErrorLog: true });
            } catch (error: unknown) {
                // Módulo não contratado (402) ou outros erros esperados - retornar vazio silenciosamente
                return [];
            }
        },
        retry: false,
        refetchInterval: 5 * 60 * 1000, // Verifica a cada 5 min
    });
    const hasCadernoAlerta = cadernoAlertas.length > 0;

    const normalizedSearchQuery = normalizeSearchValue(deferredSearchQuery);
    const isSearching = normalizedSearchQuery.length > 0;

    // ── Module toggle handler ──────────────────────────────────────────────
    const handleModuleToggle = useCallback((key: ModuleKey) => {
        setModuleToggle((prev) => {
            const currentState = prev[key] ?? "auto";
            const isCurrentlyOpen = resolveToggle(currentState, activeModule === key);
            return {
                ...prev,
                [key]: isCurrentlyOpen ? "closed" : "open",
            };
        });
    }, [activeModule]);

    // ── Resolve whether a module is open ───────────────────────────────────
    const isModuleOpen = useCallback((key: string): boolean => {
        return resolveToggle(moduleToggle[key], activeModule === key);
    }, [moduleToggle, activeModule]);

    const tenantLogoSrc = (() => {
        return resolveAssetUrl(tenant?.branding?.logoUrl);
    })();

        const searchGroups = useMemo(() => {
        const coreItems = coreSections.flatMap((section) =>
            section.items.map((item) => ({
                ...item,
                group: "Cadastros",
                section: section.label,
            }))
        );

        const modGroups = moduleGroups.map((moduleGroup) => ({
            moduleId: moduleGroup.moduleId,
            key: moduleGroup.key,
            label: moduleGroup.label,
            items: moduleGroup.sections.flatMap((section) =>
                section.items.map((item) => ({
                    ...item,
                    group: moduleGroup.label,
                    section: section.label,
                    moduleId: section.moduleId ?? moduleGroup.moduleId,
                    activeClassName: moduleActive[moduleGroup.key as keyof typeof moduleActive],
                }))
            ),
        }));

        const backofficeItems = backofficeSections.flatMap((section) =>
            section.items.map((item) => ({
                ...item,
                group: "Administração SaaS",
                section: section.label,
                activeClassName: backofficeActive,
            }))
        );

        return {
            coreItems,
            moduleGroups: modGroups,
            backofficeItems,
            accessItems: accessItems.map((item) => ({
                ...item,
                group: "Gestão de Acessos",
            })) satisfies SearchableItem[],
            settingsItems: settingsItems.map((item) => ({
                ...item,
                group: "Configurações",
            })) satisfies SearchableItem[],
        };
    }, [coreSections, moduleGroups, backofficeSections, accessItems, settingsItems]);

    const filteredSearchGroups = useMemo(() => {
        if (!normalizedSearchQuery) {
            return {
                coreItems: [],
                moduleGroups: [],
                backofficeItems: [],
                accessItems: [],
                settingsItems: [],
                total: 0,
            };
        }

        const coreItems = searchGroups.coreItems.filter((item) => itemMatchesSearch(item, normalizedSearchQuery));
        const moduleGroups = searchGroups.moduleGroups
            .map((group) => ({
                ...group,
                items: group.items.filter((item) => itemMatchesSearch(item, normalizedSearchQuery)),
            }))
            .filter((group) => group.items.length > 0);
        const backofficeItems = searchGroups.backofficeItems.filter((item) => itemMatchesSearch(item, normalizedSearchQuery));
        const accessSearchItems = searchGroups.accessItems.filter((item) => itemMatchesSearch(item, normalizedSearchQuery));
        const settingsSearchItems = searchGroups.settingsItems.filter((item) => itemMatchesSearch(item, normalizedSearchQuery));

        return {
            coreItems,
            moduleGroups,
            backofficeItems,
            accessItems: accessSearchItems,
            settingsItems: settingsSearchItems,
            total:
                coreItems.length +
                moduleGroups.reduce((sum, group) => sum + group.items.length, 0) +
                backofficeItems.length +
                accessSearchItems.length +
                settingsSearchItems.length,
        };
    }, [normalizedSearchQuery, searchGroups]);

    const renderSearchItems = (items: SearchableItem[]) => items.map((item) => {
        const Icon = item.icon;
        return (
            <SidebarMenuItem key={`${item.group}-${item.href}`}>
                <SidebarMenuButton
                    render={<Link href={item.href} onClick={() => { setSearchQuery(""); handleNavigation(); }} />}
                    isActive={isItemActive(item.href, pathname, searchParams, item.exact)}
                    tooltip={item.tip ?? item.label}
                    className={cn(
                        "h-auto py-2",
                        item.activeClassName || "relative data-[active=true]:bg-primary/5 data-[active=true]:text-primary data-[active=true]:font-bold before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[2px] before:bg-primary before:rounded-full before:opacity-0 data-[active=true]:before:opacity-100 transition-all"
                    )}
                >
                    <Icon className="size-3.5 shrink-0 text-primary" />
                    <span className="flex min-w-0 flex-col gap-0.5">
                        <span className="truncate">{item.label}</span>
                        <span className="truncate text-[10px] font-normal text-muted-foreground">
                            {item.group}{item.section ? ` > ${item.section}` : ""}
                        </span>
                    </span>
                    {item.alertBadge && hasCadernoAlerta && (
                        <Badge variant="destructive" className="ml-auto">
                            <AlertCircle className="size-3" />
                        </Badge>
                    )}
                </SidebarMenuButton>
            </SidebarMenuItem>
        );
    });

    // ── Resolved module/section state for Cadastros ────────────────────────
    const isCadastrosOpen = isModuleOpen("CADASTROS");
    const cadastrosSubmenuId = "sidebar-module-CADASTROS";

    return (
        <Sidebar collapsible="icon">
            <SidebarHeader className="border-b border-border/50 h-14 flex items-center justify-center p-0 overflow-hidden">
                <Link href="/dashboard" className="flex items-center justify-center w-full h-full outline-none" onClick={handleNavigation}>
                    {/* Collapsed */}
                    <div className="hidden group-data-[collapsible=icon]:flex w-full items-center justify-center">
                        <div className="flex size-8 items-center justify-center rounded-sm bg-primary text-primary-foreground shadow-sm">
                            <Sprout className="size-3.5" />
                        </div>
                    </div>
                    {/* Expanded */}
                    <div className="group-data-[collapsible=icon]:hidden flex items-center gap-2.5 px-3 w-full">
                        <div className="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-md bg-primary/5 text-primary shadow-sm ring-1 ring-border/60">
                            {tenantLogoSrc ? (
                                <img
                                    src={tenantLogoSrc}
                                    alt={tenant?.nome ?? "Logo"}
                                    className="h-full w-full object-contain p-1.5"
                                />
                            ) : (
                                <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-sm">
                                    <Sprout className="size-3.5" />
                                </div>
                            )}
                        </div>
                        <span className="font-black text-primary text-lg truncate">
                            {tenant?.nome ?? "DeepFarms"}
                        </span>
                    </div>
                </Link>
            </SidebarHeader>

            {tenant && (
                <div className="group-data-[collapsible=icon]:hidden border-b border-border/50 px-3 py-2">
                    <div className="flex items-center gap-1.5">
                        <div className="relative min-w-0 flex-1">
                            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                value={searchQuery}
                                onChange={(event) => setSearchQuery(event.target.value)}
                                placeholder="Pesquisar menu..."
                                aria-label="Pesquisar itens do menu"
                                className="h-8 rounded-sm bg-sidebar-accent/40 pl-8 text-xs"
                            />
                        </div>
                        {searchQuery && (
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="size-8 shrink-0"
                                aria-label="Limpar pesquisa do menu"
                                onClick={() => setSearchQuery("")}
                            >
                                <X data-icon="icon" />
                            </Button>
                        )}
                    </div>
                </div>
            )}

            <SidebarContent>
                {isSearching ? (
                    <SidebarGroup>
                        <SidebarGroupLabel>
                            {filteredSearchGroups.total === 1
                                ? "1 item encontrado"
                                : `${filteredSearchGroups.total} itens encontrados`}
                        </SidebarGroupLabel>
                        <SidebarGroupContent>
                            {filteredSearchGroups.total === 0 ? (
                                <div className="px-2 py-6 text-center text-xs text-muted-foreground">
                                    Nenhum item encontrado para &quot;{deferredSearchQuery}&quot;.
                                </div>
                            ) : (
                                <SidebarMenu>
                                    {filteredSearchGroups.coreItems.length > 0 && (
                                        <>
                                            <SidebarMenuSubItem>
                                                <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground/60">
                                                    Cadastros
                                                </div>
                                            </SidebarMenuSubItem>
                                            {renderSearchItems(filteredSearchGroups.coreItems)}
                                        </>
                                    )}

                                    {filteredSearchGroups.moduleGroups.map((moduleGroup) => (
                                        <ModuleGate key={moduleGroup.key} moduleId={moduleGroup.moduleId}>
                                            <SidebarMenuSubItem>
                                                <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground/60">
                                                    {moduleGroup.label}
                                                </div>
                                            </SidebarMenuSubItem>
                                            {renderSearchItems(moduleGroup.items)}
                                        </ModuleGate>
                                    ))}

                                    {filteredSearchGroups.backofficeItems.length > 0 && (
                                        <>
                                            <SidebarMenuSubItem>
                                                <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground/60">
                                                    Administração SaaS
                                                </div>
                                            </SidebarMenuSubItem>
                                            {renderSearchItems(filteredSearchGroups.backofficeItems)}
                                        </>
                                    )}

                                    {filteredSearchGroups.accessItems.length > 0 && (
                                        <>
                                            <SidebarMenuSubItem>
                                                <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground/60">
                                                    Gestão de Acessos
                                                </div>
                                            </SidebarMenuSubItem>
                                            {renderSearchItems(filteredSearchGroups.accessItems)}
                                        </>
                                    )}

                                    {filteredSearchGroups.settingsItems.length > 0 && (
                                        <>
                                            <SidebarMenuSubItem>
                                                <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground/60">
                                                    Configurações
                                                </div>
                                            </SidebarMenuSubItem>
                                            {renderSearchItems(filteredSearchGroups.settingsItems)}
                                        </>
                                    )}
                                </SidebarMenu>
                            )}
                        </SidebarGroupContent>
                    </SidebarGroup>
                ) : (
                    <>
                        {/* ── Geral ─────────────────────────────────── */}
                        {tenant && (
                            <SidebarGroup>
                                <SidebarGroupLabel>Geral</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton
                                                render={<Link href="/dashboard" onClick={handleNavigation} />}
                                                isActive={pathname === "/dashboard"}
                                                tooltip="Dashboard"
                                                className="relative data-[active=true]:bg-primary/5 data-[active=true]:text-primary data-[active=true]:font-bold before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[2px] before:bg-primary before:rounded-full before:opacity-0 data-[active=true]:before:opacity-100 transition-all"
                                            >
                                                <LayoutDashboard className="size-3.5 flex-shrink-0 text-primary" />
                                                <span className="truncate">Dashboard</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton
                                                render={<Link href="/manual" onClick={handleNavigation} />}
                                                isActive={pathname === "/manual" || pathname.startsWith("/manual/")}
                                                tooltip="Manual do Usuário & Ajuda"
                                                className="relative data-[active=true]:bg-primary/5 data-[active=true]:text-primary data-[active=true]:font-bold before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[2px] before:bg-primary before:rounded-full before:opacity-0 data-[active=true]:before:opacity-100 transition-all"
                                            >
                                                <BookOpen className="size-3.5 flex-shrink-0 text-primary" />
                                                <span className="truncate">Manual do Usuário</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        )}

                        {/* ── Módulos ───────────────────────────────── */}
                        {tenant && (
                            <SidebarGroup>
                                <SidebarGroupLabel>Módulos</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>

                                        {/* CORE — Cadastros e Tabelas Compartilhadas */}
                                        {coreSections.length > 0 && (
                                        <SidebarMenuItem>
                                            <SidebarMenuButton
                                                onClick={() => handleModuleToggle("CADASTROS")}
                                                isActive={pathname.startsWith("/cadastros")}
                                                tooltip="Cadastros.."
                                                aria-expanded={isCadastrosOpen}
                                                aria-controls={cadastrosSubmenuId}
                                            >
                                                {CORE_CADASTROS[0]?.icon && (() => {
                                                    const Icon = CORE_CADASTROS[0].icon;
                                                    return <Icon className="size-3.5 text-primary" />;
                                                })()}
                                                <span className="font-semibold">Cadastros</span>
                                                {isCadastrosOpen ? <ChevronDown className="ml-auto size-3.5 " /> : <ChevronRight className="ml-auto size-3.5 " />}
                                            </SidebarMenuButton>
                                            {isCadastrosOpen && (
                                                <SidebarMenuSub id={cadastrosSubmenuId}>
                                                    {coreSections.map((section) => (
                                                        <React.Fragment key={section.key}>
                                                            {/* Seção de label */}
                                                            <SidebarMenuSubItem>
                                                                <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground/60">
                                                                    {section.label}
                                                                </div>
                                                            </SidebarMenuSubItem>

                                                            {/* Items dessa seção */}
                                                            {section.items.map((item) => (
                                                                    <SidebarMenuSubItem key={`${item.href}-${item.label}`}>
                                                                        <SidebarMenuSubButton title={item.tip} isActive={isItemActive(item.href, pathname, searchParams, item.exact)} render={<Link href={item.href} onClick={handleNavigation} />}>
                                                                            <item.icon className="size-3.5 flex-shrink-0 text-primary" />
                                                                            <span>{item.label}</span>
                                                                        </SidebarMenuSubButton>
                                                                    </SidebarMenuSubItem>
                                                                ))}
                                                        </React.Fragment>
                                                    ))}
                                                </SidebarMenuSub>
                                            )}
                                        </SidebarMenuItem>
                                        )}

                                        {/* Módulos Operacionais */}
                                        {moduleGroups.map((moduleGroup) => {
                                            const moduleKey = moduleGroup.key as ModuleKey;
                                            const moduleIsOpen = isModuleOpen(moduleKey);
                                            const moduleSubmenuId = `sidebar-module-${moduleGroup.key}`;
                                            const moduleIsActive = moduleGroup.sections.some((section) =>
                                                section.items.some((item) => isItemActive(item.href, pathname, searchParams, item.exact))
                                            );

                                            return (
                                            <ModuleGate key={moduleGroup.key} moduleId={moduleGroup.moduleId}>
                                                <SidebarMenuItem>
                                                <SidebarMenuButton
                                                        onClick={() => handleModuleToggle(moduleKey)}
                                                        isActive={moduleIsActive}
                                                        tooltip={moduleGroup.label}
                                                        className={cn(moduleActive[moduleGroup.key as keyof typeof moduleActive] || "data-[active=true]:bg-primary/10 data-[active=true]:text-primary")}
                                                        aria-expanded={moduleIsOpen}
                                                        aria-controls={moduleSubmenuId}
                                                    >
                                                        <moduleGroup.icon className="size-3.5 text-primary" />
                                                        <span className="font-semibold">{moduleGroup.label}</span>
                                                        {moduleIsOpen ? <ChevronDown className="ml-auto size-3.5 " /> : <ChevronRight className="ml-auto size-3.5 " />}
                                                    </SidebarMenuButton>

                                                    {moduleIsOpen && (
                                                        <SidebarMenuSub id={moduleSubmenuId}>
                                                            {moduleGroup.sections.map((section) => {
                                                                const visibleItems = section.items.filter(
                                                                    (item) =>
                                                                        (!item.minimumTier || tierAtLeast(activePlanTier, item.minimumTier)) &&
                                                                        canSeeTenantItem(user, item.permission)
                                                                );
                                                                if (visibleItems.length === 0) {
                                                                    return null;
                                                                }
                                                                const isDirectGroup = section.label === "Dashboard" || section.label === "Visão Geral";

                                                                const sectionModuleId = section.moduleId ?? moduleGroup.moduleId;

                                                                if (isDirectGroup) {
                                                                    return (
                                                                        <ModuleGate key={section.key} moduleId={sectionModuleId}>
                                                                            {visibleItems.map((item) => (
                                                                                <SidebarMenuSubItem key={`${item.href}-${item.label}`} className="mb-1">
                                                                                    <SidebarMenuSubButton title={item.tip} isActive={isItemActive(item.href, pathname, searchParams, item.exact)} render={<Link href={item.href} onClick={handleNavigation} />} className="font-semibold text-primary">
                                                                                        <item.icon className="size-3.5 flex-shrink-0" />
                                                                                        <span className="truncate">{item.label}</span>
                                                                                        {item.alertBadge && hasCadernoAlerta && (
                                                                                            <Badge variant="destructive" className="ml-auto">
                                                                                                <AlertCircle className="size-3" />
                                                                                            </Badge>
                                                                                        )}
                                                                                    </SidebarMenuSubButton>
                                                                                </SidebarMenuSubItem>
                                                                            ))}
                                                                        </ModuleGate>
                                                                    );
                                                                }

                                                                return (
                                                                    <ModuleGate key={section.key} moduleId={sectionModuleId}>
                                                                    <React.Fragment>
                                                                        <SidebarMenuSubItem>
                                                                            <div className={cn(
                                                                                "px-1.5 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/70",
                                                                                getSectionActiveStyle(moduleGroup.key)
                                                                            )}>
                                                                                {section.label}
                                                                            </div>
                                                                        </SidebarMenuSubItem>
                                                                        {visibleItems.map((item) => (
                                                                            <SidebarMenuSubItem key={`${item.href}-${item.label}`}>
                                                                                <SidebarMenuSubButton title={item.tip} isActive={isItemActive(item.href, pathname, searchParams, item.exact)} render={<Link href={item.href} onClick={handleNavigation} />}>
                                                                                    <item.icon className="size-3.5 flex-shrink-0 text-primary" />
                                                                                    <span className="truncate">{item.label}</span>
                                                                                    {item.alertBadge && hasCadernoAlerta && (
                                                                                        <Badge variant="destructive" className="ml-auto">
                                                                                            <AlertCircle className="size-3" />
                                                                                        </Badge>
                                                                                    )}
                                                                                </SidebarMenuSubButton>
                                                                            </SidebarMenuSubItem>
                                                                        ))}
                                                                    </React.Fragment>
                                                                    </ModuleGate>
                                                                );
                                                            })}
                                                        </SidebarMenuSub>
                                                    )}
                                                </SidebarMenuItem>
                                            </ModuleGate>
                                        );
                                        })}


                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        )}

                        {/* ── Administração SaaS (6 seções agrupadas por domínio) ── */}
                        <BackofficeNav
                            pathname={pathname}
                            searchParams={searchParams}
                            user={user}
                            backofficeToggle={backofficeToggle}
                            setBackofficeToggle={setBackofficeToggle}
                            onNavigate={handleNavigation}
                        />

                        {/* ── Gestão de Acessos ─────────────────────── */}
                        {tenant && accessItems.length > 0 && (
                            <SidebarGroup>
                                <SidebarGroupLabel>Gestão de Acessos</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        {accessItems.map(({ href, icon: Icon, label, tip, exact }) => (
                                            <SidebarMenuItem key={href}>
                                                <SidebarMenuButton
                                                    isActive={isItemActive(href, pathname, searchParams, exact)}
                                                    tooltip={tip}
                                                    className="relative data-[active=true]:bg-primary/5 data-[active=true]:text-primary data-[active=true]:font-bold before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[2px] before:bg-primary before:rounded-full before:opacity-0 data-[active=true]:before:opacity-100 transition-all"
                                                    render={<Link href={href} onClick={handleNavigation} />}
                                                >
                                                    <Icon className="size-3.5 shrink-0 text-primary" />
                                                    <span className="truncate">{label}</span>
                                                </SidebarMenuButton>
                                            </SidebarMenuItem>
                                        ))}
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        )}

                        {/* ── Configurações ─────────────────────────── */}
                        {tenant && settingsItems.length > 0 && <SidebarGroup>
                            <SidebarGroupLabel>Configurações</SidebarGroupLabel>
                            <SidebarGroupContent>
                                <SidebarMenu>
                                    {settingsItems.map(({ href, icon: Icon, label, tip, exact }) => (
                                        <SidebarMenuItem key={href}>
                                            <SidebarMenuButton
                                                isActive={isItemActive(href, pathname, searchParams, exact)}
                                                tooltip={tip}
                                                className="relative data-[active=true]:bg-primary/5 data-[active=true]:text-primary data-[active=true]:font-bold before:absolute before:left-0 before:top-1 before:bottom-1 before:w-[2px] before:bg-primary before:rounded-full before:opacity-0 data-[active=true]:before:opacity-100 transition-all font-medium text-sidebar-foreground/80"
                                                render={<Link href={href} onClick={handleNavigation} />}
                                            >
                                                <Icon className="size-3.5 shrink-0 text-primary" />
                                                <span className="truncate">{label}</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    ))}
                                </SidebarMenu>
                            </SidebarGroupContent>
                        </SidebarGroup>}
                    </>
                )}
            </SidebarContent>
        </Sidebar>
    );
}
