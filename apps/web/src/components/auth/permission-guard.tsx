// components/auth/permission-guard.tsx
// Guard condicional que renderiza filhos apenas se o usuário possuir a permissão

"use client";

import type { ReactNode } from "react";
import { usePermission } from "@/hooks/use-permission";

interface PermissionGuardProps {
    /** String de permissão requerida (ex: 'tenant:users:view') */
    permission: string;
    /** Conteúdo protegido */
    children: ReactNode;
    /** Fallback renderizado quando a permissão é negada */
    fallback?: ReactNode;
}

/**
 * Componente guard que renderiza os filhos apenas se o
 * usuário possuir a permissão indicada.
 *
 * @param props - permission, children, fallback
 * @returns JSX.Element ou null
 */
export function PermissionGuard({ permission, children, fallback = null }: PermissionGuardProps) {
    const allowed = usePermission(permission);

    if (!allowed) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}
