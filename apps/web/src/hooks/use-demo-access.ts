"use client";

import { useAppStore } from "@/lib/stores/app-store";

export interface DemoAccessState {
    isReadOnly: boolean;
    isDemoVisitor: boolean;
    isDemoExpired: boolean;
    validadeAcesso: string | null;
    diasRestantes: number | null;
    prorrogacoesCount: number;
}

/**
 * Hook utilitário para consultar estado do modo Demonstração (Somente Consulta) e vencimento.
 *
 * @returns Estado consolidado de leitura restrita e vigência da demonstração.
 */
export function useDemoAccess(): DemoAccessState {
    const user = useAppStore((state) => state.user);

    const isReadOnly = Boolean(user?.is_read_only);
    const isDemoVisitor = Boolean(user?.is_demo_visitor);
    const isDemoExpired = Boolean(user?.demo_expired);

    return {
        isReadOnly,
        isDemoVisitor,
        isDemoExpired,
        validadeAcesso: user?.demo_validade_acesso ?? null,
        diasRestantes: user?.demo_dias_restantes ?? null,
        prorrogacoesCount: user?.demo_prorrogacoes_count ?? 0,
    };
}
