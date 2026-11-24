// lib/permissions.ts
// Constantes e utilitários de permissões para RBAC

import type { BackofficeRole, TenantRole, PermissionLevel, TenantCustomPermissions } from "@/types/global";

/* ─── Mapeamento de permissões por role do Backoffice ─── */

const BACKOFFICE_PERMISSIONS: Record<BackofficeRole, string[]> = {
    super_admin: [
        // Visão Geral
        "backoffice:dashboard:view",
        "backoffice:bi:view",
        // Comercial
        "backoffice:tenants:view", "backoffice:tenants:create", "backoffice:tenants:update", "backoffice:tenants:delete",
        "backoffice:plans:view", "backoffice:plans:create", "backoffice:plans:update",
        "backoffice:cupons:view", "backoffice:cupons:create", "backoffice:cupons:update", "backoffice:cupons:delete",
        "backoffice:crm:view", "backoffice:crm:create", "backoffice:crm:update", "backoffice:crm:delete",
        "backoffice:ia:view", "backoffice:ia:update",
        // Financeiro
        "backoffice:billing:view", "backoffice:billing:update",
        "backoffice:plan_changes:view", "backoffice:plan_changes:update",
        // Suporte
        "backoffice:support:view", "backoffice:support:update",
        "backoffice:kb:view", "backoffice:kb:create", "backoffice:kb:update", "backoffice:kb:delete",
        // Controle de Acesso
        "backoffice:users:view", "backoffice:users:update",
        "backoffice:admin_users:view", "backoffice:admin_users:create", "backoffice:admin_users:update", "backoffice:admin_users:delete",
        "backoffice:profiles:view", "backoffice:profiles:create", "backoffice:profiles:update", "backoffice:profiles:delete",
        // Sistema
        "backoffice:config:view", "backoffice:config:update",
        "backoffice:integrations:observe", "backoffice:integrations:support",
        "backoffice:tabelas:view", "backoffice:tabelas:create", "backoffice:tabelas:update", "backoffice:tabelas:delete",
        "backoffice:uom:view", "backoffice:uom:create", "backoffice:uom:update", "backoffice:uom:delete",
        "backoffice:audit:view",
        "backoffice:email_templates:view", "backoffice:email_templates:create", "backoffice:email_templates:update",
        "backoffice:sessions:view", "backoffice:sessions:delete",
        "backoffice:impersonate",
    ],
    admin: [
        // Visão Geral
        "backoffice:dashboard:view",
        "backoffice:bi:view",
        // Comercial
        "backoffice:tenants:view", "backoffice:tenants:create", "backoffice:tenants:update",
        "backoffice:plans:view",
        "backoffice:cupons:view",
        "backoffice:crm:view", "backoffice:crm:create", "backoffice:crm:update",
        "backoffice:ia:view", "backoffice:ia:update",
        // Financeiro
        "backoffice:billing:view",
        "backoffice:plan_changes:view",
        // Suporte
        "backoffice:support:view", "backoffice:support:update",
        "backoffice:kb:view", "backoffice:kb:create", "backoffice:kb:update",
        // Controle de Acesso
        "backoffice:users:view", "backoffice:users:update",
        "backoffice:admin_users:view", "backoffice:admin_users:create", "backoffice:admin_users:update",
        "backoffice:profiles:view", "backoffice:profiles:create", "backoffice:profiles:update",
        // Sistema (somente visualização)
        "backoffice:config:view",
        "backoffice:integrations:observe", "backoffice:integrations:support",
        "backoffice:tabelas:view",
        "backoffice:uom:view",
        "backoffice:audit:view",
    ],
    suporte: [
        // Visão Geral
        "backoffice:dashboard:view",
        // Comercial (somente visualização de assinantes)
        "backoffice:tenants:view",
        // Suporte
        "backoffice:support:view", "backoffice:support:update",
        "backoffice:integrations:observe", "backoffice:integrations:support",
        "backoffice:kb:view", "backoffice:kb:create", "backoffice:kb:update",
    ],
    financeiro: [
        // Visão Geral
        "backoffice:dashboard:view",
        "backoffice:bi:view",
        // Comercial (somente visualização)
        "backoffice:tenants:view",
        // Financeiro
        "backoffice:billing:view", "backoffice:billing:update",
        "backoffice:plan_changes:view", "backoffice:plan_changes:update",
        "backoffice:integrations:observe",
        // Controle de Acesso (somente visualização)
        "backoffice:users:view",
    ],
    comercial: [
        // Visão Geral
        "backoffice:dashboard:view",
        // Comercial
        "backoffice:tenants:view", "backoffice:tenants:create",
        "backoffice:plans:view", "backoffice:plans:create", "backoffice:plans:update",
        "backoffice:cupons:view", "backoffice:cupons:create", "backoffice:cupons:update",
        "backoffice:crm:view", "backoffice:crm:create", "backoffice:crm:update",
        "backoffice:ia:view", "backoffice:ia:update",
        // Suporte (solicitações de prorrogação demo)
        "backoffice:support:view", "backoffice:support:update",
    ],
};

/* ─── Mapeamento de permissões por role do Tenant ─── */

const TENANT_PERMISSIONS: Record<TenantRole, string[]> = {
    owner: [
        "tenant:users:view", "tenant:users:invite", "tenant:users:update", "tenant:users:delete",
        "tenant:permissions:view", "tenant:permissions:create", "tenant:permissions:update",
        "tenant:fazendas:view", "tenant:fazendas:create", "tenant:fazendas:update",
        "tenant:grupos:view", "tenant:grupos:create", "tenant:grupos:update", "tenant:grupos:delete",
        "tenant:settings:view", "tenant:settings:update",
        "tenant:billing:view",
        "tenant:audit:view",
        "integrations:view", "integrations:configure", "integrations:test", "integrations:sync", "integrations:logs:view",
        "estoque:implantacao_assistida:*",
    ],
    admin: [
        "tenant:users:view", "tenant:users:invite", "tenant:users:update",
        "tenant:permissions:view",
        "tenant:fazendas:view", "tenant:fazendas:create", "tenant:fazendas:update",
        "tenant:grupos:view", "tenant:grupos:create", "tenant:grupos:update",
        "tenant:settings:view", "tenant:settings:update",
        "tenant:billing:view",
        "tenant:audit:view",
        "integrations:view", "integrations:configure", "integrations:test", "integrations:sync", "integrations:logs:view",
        "estoque:implantacao_assistida:*",
    ],
    gerente: [
        "tenant:users:view",
        "tenant:permissions:view",
        "tenant:fazendas:view",
        "tenant:grupos:view",
        "tenant:settings:view",
        "integrations:view", "integrations:logs:view",
        "estoque:implantacao_assistida:view",
        "estoque:implantacao_assistida:list",
        "estoque:implantacao_assistida:create",
        "estoque:implantacao_assistida:edit",
    ],
    agronomo: [
        "tenant:fazendas:view",
        "integrations:view",
        "estoque:implantacao_assistida:view",
        "estoque:implantacao_assistida:list",
    ],
    veterinario: [
        "tenant:fazendas:view",
        "integrations:view",
        "estoque:implantacao_assistida:view",
        "estoque:implantacao_assistida:list",
    ],
    operador: [
        "tenant:fazendas:view",
        "estoque:implantacao_assistida:view",
        "estoque:implantacao_assistida:list",
    ],
    financeiro: [
        "tenant:fazendas:view",
        "tenant:billing:view",
        "integrations:view", "integrations:logs:view",
        "estoque:implantacao_assistida:view",
        "estoque:implantacao_assistida:list",
    ],
    visualizador: [
        "tenant:fazendas:view",
        "integrations:view",
        "estoque:implantacao_assistida:view",
        "estoque:implantacao_assistida:list",
    ],
    demonstracao: [
        "tenant:fazendas:view",
        "tenant:fazendas:list",
        "tenant:grupos:view",
    ],
};

/**
 * Verifica se uma role do Backoffice possui determinada permissão.
 *
 * @param role - Role do admin no backoffice
 * @param permission - String de permissão (ex: 'backoffice:admin_users:view')
 * @returns true se a role possui a permissão
 */
export function hasBackofficePermission(
    role: BackofficeRole | undefined,
    permission: string
): boolean {
    if (!role) return false;
    return BACKOFFICE_PERMISSIONS[role]?.includes(permission) ?? false;
}

/**
 * Verifica se uma role do Tenant possui determinada permissão.
 *
 * @param role - Role do membro no tenant
 * @param permission - String de permissão (ex: 'tenant:users:view')
 * @param customPermissions - Permissões customizadas do perfil
 * @returns true se a role possui a permissão
 */
export function hasTenantPermission(
    role: TenantRole | undefined,
    permission: string,
    customPermissions?: TenantCustomPermissions
): boolean {
    // A API autoriza o proprietário do tenant independentemente do JSON legado do perfil.
    if (role === "owner") return true;

    const granted = customPermissions?.granted ?? customPermissions?.permissions;

    // Formato novo: lista explícita de permissões concedidas.
    if (Array.isArray(granted)) {
        if (granted.includes("*") || granted.includes(permission)) return true;

        const parts = permission.split(":");
        for (let i = 1; i <= parts.length; i++) {
            if (granted.includes(`${parts.slice(0, i).join(":")}:*`)) {
                return true;
            }
        }

        return false;
    }

    // Formato legado: permissões por módulo em read/write/none.
    if (customPermissions) {
        const permissionScope = permission.split(":")[0];
        const level = customPermissions[permissionScope] as PermissionLevel | undefined;
        if (level === "write") return true;
        if (level === "read" && (permission.endsWith(":view") || permission.endsWith(":list") || permission.endsWith(":export"))) return true;
        if (level === "none") return false;
    }

    if (!role) return false;

    return TENANT_PERMISSIONS[role]?.includes(permission) ?? false;
}

/** Labels legíveis para roles do Backoffice */
export const BACKOFFICE_ROLE_LABELS: Record<BackofficeRole, string> = {
    super_admin: "Super Admin",
    admin: "Administrador",
    suporte: "Suporte",
    financeiro: "Financeiro",
    comercial: "Comercial",
};

/** Labels legíveis para roles do Tenant */
export const TENANT_ROLE_LABELS: Record<TenantRole, string> = {
    owner: "Proprietário",
    admin: "Administrador",
    gerente: "Gerente",
    agronomo: "Agrônomo",
    veterinario: "Veterinário",
    operador: "Operador",
    financeiro: "Financeiro",
    visualizador: "Visualizador",
    demonstracao: "Demonstração",
};
