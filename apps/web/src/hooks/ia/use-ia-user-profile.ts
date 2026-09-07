"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export type IAUserProfileType = "CONFIANTE" | "ANALÍTICO" | "INSEGURO" | "NEUTRO";

interface IAUserProfile {
    perfil: IAUserProfileType;
    justificativa: string;
    metadados: {
        taxa_abertura: number;
        taxa_execucao: number;
        tempo_decisao_ms: number;
        total_visualizacoes: number;
    };
}

/**
 * Hook para obter o perfil comportamental do usuário em relação à IA.
 * Step UX-05.
 */
export const useIAUserProfile = () => {
    return useQuery<IAUserProfile>({
        queryKey: ["ia-user-profile"],
        queryFn: () => apiFetch("/ia/ux/perfil"),
        retry: false,
        staleTime: 30 * 60 * 1000, // Perfil muda raramente
        gcTime: 60 * 60 * 1000,
        placeholderData: {
            perfil: "NEUTRO",
            justificativa: "Dados insuficientes para classificar o perfil neste momento.",
            metadados: {
                taxa_abertura: 0,
                taxa_execucao: 0,
                tempo_decisao_ms: 0,
                total_visualizacoes: 0,
            },
        },
    });
};
