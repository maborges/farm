"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { useAppStore } from "@/lib/stores/app-store";

/**
 * Componente invisível que detecta troca de tenant feita em outra aba do mesmo
 * navegador (localStorage é compartilhado entre abas do mesmo perfil) e avisa
 * o usuário, em vez de deixar a aba atual seguir com um tenant_id defasado —
 * causa raiz de 403 "Contexto de tenant ausente/inválido" e "Usuário fora do
 * tenant selecionado" quando o operador testa múltiplos tenants em abas
 * normais do mesmo navegador (ver PILOT-DRYRUN-03).
 */
export function TenantTabSyncWarning() {
    const currentTenantId = useAppStore((s) => s.tenant?.id ?? null);
    const tenantIdRef = useRef(currentTenantId);

    useEffect(() => {
        tenantIdRef.current = currentTenantId;
    }, [currentTenantId]);

    useEffect(() => {
        const handleStorage = (e: StorageEvent) => {
            if (e.key !== "agrosaas-auth-storage" || !e.newValue) return;

            let novoTenantId: string | null = null;
            try {
                novoTenantId = JSON.parse(e.newValue)?.state?.tenant?.id ?? null;
            } catch {
                return;
            }

            if (novoTenantId && tenantIdRef.current && novoTenantId !== tenantIdRef.current) {
                toast.warning("Tenant alterado em outra aba", {
                    description: "Esta aba ainda está no tenant anterior. Recarregue para evitar erros de acesso.",
                    duration: 15_000,
                    action: {
                        label: "Recarregar",
                        onClick: () => window.location.reload(),
                    },
                });
            }
        };

        window.addEventListener("storage", handleStorage);
        return () => window.removeEventListener("storage", handleStorage);
    }, []);

    return null;
}
