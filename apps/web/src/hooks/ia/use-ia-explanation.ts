"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAExplanation {
    perfil: string;
    titulo: string;
    explicacao: string;
    metricas_usuario: {
        tempo_medio: string;
        taxa_execucao: string;
        curiosidade: string;
    };
    thresholds_referencia: Record<string, number>;
}

/**
 * Hook para obter a explicação amigável do perfil de IA.
 * Step UX-07.
 */
export const useIAExplanation = () => {
    return useQuery<IAExplanation>({
        queryKey: ["ia-explanation"],
        queryFn: () => apiFetch("/ia/ux/explicacao"),
        retry: false,
        staleTime: 5 * 60 * 1000,
        placeholderData: {
            perfil: "NEUTRO",
            titulo: "Perfil Neutro",
            explicacao: "A IA está aprendendo seu ritmo para ajustar a interface conforme suas necessidades.",
            metricas_usuario: {
                tempo_medio: "0,0s",
                taxa_execucao: "0%",
                curiosidade: "0% abertura detalhada",
            },
            thresholds_referencia: {},
        },
    });
};
