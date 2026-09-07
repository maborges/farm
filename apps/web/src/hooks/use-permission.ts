// hooks/use-permission.ts
// Hook para verificar permissões do usuário logado

"use client";

import { useAppStore } from "@/lib/stores/app-store";
import { hasBackofficePermission, hasTenantPermission } from "@/lib/permissions";

/**
 * Hook que verifica se o usuário atual possui uma permissão.
 *
 * @param permission - String de permissão (ex: 'backoffice:admin_users:view')
 * @returns true se o usuário possui a permissão
 */
export function usePermission(permission: string): boolean {
    const { user } = useAppStore();

    if (!user) return false;

    // Superuser tem acesso total
    if (user.is_superuser) return true;

    // Permissões do Backoffice
    if (permission.startsWith("backoffice:")) {
        return hasBackofficePermission(user.role, permission);
    }

    // Permissões do Tenant
    if (permission.startsWith("tenant:") || !permission.startsWith("backoffice:")) {
        return hasTenantPermission(user.tenant_role, permission, user.custom_permissions);
    }

    return false;
}
