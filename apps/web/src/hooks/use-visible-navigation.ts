import { useMemo, useCallback } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { useAppStore } from "@/lib/stores/app-store";
import { CORE_CADASTROS, MODULOS_OPERACIONAIS, BACKOFFICE_SECTIONS, ACCESS_ITEMS, SETTINGS_ITEMS, type SidebarMenuItem } from "@/lib/sidebar-config";
import { hasBackofficePermission, hasTenantPermission } from "@/lib/permissions";
import { tierAtLeast } from "@/lib/constants/planos";
import { getSidebarModuleFromPath, getActiveSectionFromPath, getActiveBackofficeSectionFromPath, isItemActive } from "@/lib/sidebar-navigation";
import type { User, BackofficeRole, TenantRole, TenantCustomPermissions } from "@/types/global";

// Reutilizamos a lógica isolada que estava no AppSidebar
export function canSeeTenantItem(user: User | null, permission?: string) {
    if (!permission) return true;
    if (!user?.tenant_role && !user?.custom_permissions && !user?.is_superuser) return false;
    if (user?.is_superuser) return true;
    return hasTenantPermission(
        user?.tenant_role as TenantRole | undefined,
        permission,
        user?.custom_permissions as TenantCustomPermissions | undefined
    );
}

export function canSeeBackofficeItem(user: User | null, permission?: string) {
    if (!user?.role && !user?.is_superuser) return false;
    if (!permission) return true;
    if (user?.is_superuser) return true;
    return hasBackofficePermission(user?.role as BackofficeRole | undefined, permission);
}

export function useVisibleNavigation() {
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const user = useAppStore((state) => state.user);
    const activePlanTier = useAppStore((state) => state.activePlanTier());
    const hasModule = useAppStore((state) => state.hasModule);
    const isReadOnlyDemo = Boolean(user?.is_demo_visitor || user?.is_read_only);

    // Módulos principais (Operacionais)
    const moduleGroups = useMemo(() => {
        return MODULOS_OPERACIONAIS.map((moduleGroup) => ({
            ...moduleGroup,
            sections: moduleGroup.sections
                .filter(section => !section.moduleId || hasModule(section.moduleId as any))
                .map(section => ({
                ...section,
                items: section.items
                    .filter((item) => !item.module || hasModule(item.module as any))
                    .filter((item) => !item.minimumTier || tierAtLeast(activePlanTier, item.minimumTier))
                    .filter((item) => canSeeTenantItem(user, item.permission))
            })).filter(section => section.items.length > 0)
        })).filter(group => {
            // Se o grupo tem ModuleGate, validar aqui
            if (group.moduleId && !hasModule(group.moduleId as any)) return false;
            return group.sections.length > 0;
        });
    }, [activePlanTier, user, hasModule]);

    // Core (Cadastros)
    const coreSections = useMemo(() => {
        return CORE_CADASTROS.map((section) => ({
            ...section,
            items: section.items
                .filter((item) => !item.module || hasModule(item.module as any))
                .filter((item) => !item.minimumTier || tierAtLeast(activePlanTier, item.minimumTier))
                .filter(
                    (item) =>
                        !isReadOnlyDemo ||
                        (item.href !== "/cadastros/pessoas" && !item.href.startsWith("/cadastros/pessoas/"))
                )
                .filter((item) => canSeeTenantItem(user, item.permission))
        })).filter(section => section.items.length > 0);
    }, [activePlanTier, user, hasModule, isReadOnlyDemo]);

    // Backoffice
    const backofficeSections = useMemo(() => {
        return BACKOFFICE_SECTIONS.map((section) => ({
            ...section,
            items: section.items.filter((item) => canSeeBackofficeItem(user, item.permission))
        })).filter(section => section.items.length > 0);
    }, [user]);

    // Itens de Acesso rápido e Configurações (footer do tenant — usado no sidebar e no mega menu)
    const accessItems = useMemo(
        () =>
            isReadOnlyDemo
                ? []
                : ACCESS_ITEMS.filter((item) => canSeeTenantItem(user, item.permission)),
        [isReadOnlyDemo, user]
    );
    const settingsItems = useMemo(
        () =>
            SETTINGS_ITEMS.filter((item) => {
                if (isReadOnlyDemo) {
                    return (
                        item.href === "/dashboard/settings/account" ||
                        item.href === "/dashboard/settings/kb" ||
                        item.href === "/dashboard/settings/support"
                    );
                }
                return canSeeTenantItem(user, item.permission);
            }),
        [isReadOnlyDemo, user]
    );

    const activeModule = getSidebarModuleFromPath(pathname);
    const activeSection = getActiveSectionFromPath(activeModule, pathname, new URLSearchParams(searchParams.toString()));
    const activeBackofficeSection = getActiveBackofficeSectionFromPath(pathname);

    return {
        moduleGroups,
        coreSections,
        backofficeSections,
        accessItems,
        settingsItems,
        activeModule,
        activeSection,
        activeBackofficeSection,
        pathname,
        searchParams,
        user
    };
}
