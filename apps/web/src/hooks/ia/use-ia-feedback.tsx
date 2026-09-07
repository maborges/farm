"use client";

import React from "react";
import { toast } from "sonner";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useIAUserProfile } from "./use-ia-user-profile";
import { trackIAUXEvento } from "@/lib/ia/ux-telemetry";
import { BrainCircuit, TrendingUp, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface IAFeedbackOptions {
    impacto_valor?: number;
    tempo_decisao_ms?: number;
    tipo_ia?: string;
    origem?: string;
}

interface UXMetrics {
    resumo_geral: {
        tempo_medio_decisao_ms: number;
    };
    funil: {
        taxa_conversao_execucao: number;
    };
}

/**
 * Hook para gerenciar feedback imediato e reforço de decisão da IA.
 * Implementa o Step UX-04.
 */
export const useIAFeedback = () => {
    const fallbackMetrics: UXMetrics = {
        resumo_geral: {
            tempo_medio_decisao_ms: 0,
        },
        funil: {
            taxa_conversao_execucao: 0,
        },
    };

    // Busca métricas para comparação contextual
    const { data: metrics } = useQuery<UXMetrics>({
        queryKey: ["ia-ux-metricas"],
        queryFn: async () => {
            try {
                return await apiFetch<UXMetrics>("/ia/ux/metricas", {
                    suppressErrorLog: true,
                });
            } catch (error) {
                const message = error instanceof Error ? error.message : "";
                if (message.includes("Banco de dados indisponível") || message.includes("pool de conexões esgotado")) {
                    return fallbackMetrics;
                }

                console.error("Erro ao carregar métricas de UX:", error);
                return fallbackMetrics;
            }
        },
        retry: false,
        staleTime: 5 * 60 * 1000,
        placeholderData: fallbackMetrics,
    });

    const { data: userProfile } = useIAUserProfile();

    const fmt = (v: number) =>
        new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

    const showFeedback = React.useCallback((options: IAFeedbackOptions) => {
        const { impacto_valor, tempo_decisao_ms, tipo_ia, origem } = options;
        const profile = userProfile?.perfil || "NEUTRO";
        const tempoValido = typeof tempo_decisao_ms === "number" && tempo_decisao_ms >= 0
            ? tempo_decisao_ms
            : undefined;

        // 1. Determinar tipo de reforço base
        let reinforcementType = "consistência";
        let message = "Excelente consistência";
        let submessage = "Sua agilidade está otimizando a operação.";

        if (tempoValido !== undefined && metrics?.resumo_geral?.tempo_medio_decisao_ms) {
            const avg = metrics.resumo_geral.tempo_medio_decisao_ms;
            if (tempoValido < avg * 0.8) {
                reinforcementType = "velocidade";
                const diff = Math.round(((avg - tempoValido) / avg) * 100);
                message = "Decisão ágil";
                submessage = `Você agiu ${diff}% mais rápido que a média.`;
            }
        }

        if (impacto_valor && impacto_valor > 5000) {
            reinforcementType = "roi";
            message = "Alta eficiência";
            submessage = "Grande impacto na saúde financeira da safra.";
        }

        // 1.1 Adaptação de Comunicação (Step UX-09)
        // Sobrescreve mensagens base com tom específico do perfil
        if (profile === "CONFIANTE") {
            message = "Boa decisão";
            submessage = impacto_valor ? `Impacto estimado de ${fmt(impacto_valor)}` : "Ação executada com sucesso.";
        } else if (profile === "ANALÍTICO") {
            message = "Decisão Validada";
            submessage = "Os dados confirmam que este é o melhor caminho.";
        } else if (profile === "INSEGURO") {
            message = "Ação Segura";
            submessage = "Excelente escolha. Você está protegendo sua rentabilidade.";
        }

        // 2. Toast Premium
        toast.custom((t) => (
            <div className={cn(
                "flex flex-col gap-1 w-full max-w-[350px] p-4 rounded-sm border-l-4 shadow-2xl",
                "bg-white dark:bg-slate-900 border-l-emerald-500",
                "animate-in fade-in slide-in-from-right-4 duration-500"
            )}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-emerald-100 dark:bg-emerald-900/30 rounded-sm text-emerald-600">
                            <BrainCircuit className="h-4 w-4" />
                        </div>
                        <span className="text-[10px] font-black uppercase tracking-widest text-emerald-600">
                            IA: Feedback Positivo
                        </span>
                    </div>
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 opacity-50" />
                </div>

                <div className="mt-2">
                    <h4 className="text-sm font-black uppercase text-slate-900 dark:text-slate-100">
                        {message}
                    </h4>
                    <p className="text-xs font-medium text-muted-foreground leading-snug">
                        {submessage}
                    </p>
                </div>

                {impacto_valor !== undefined && (
                    <div className="mt-3 pt-2 border-t border-emerald-500/10 flex items-center justify-between">
                        <span className="text-[9px] font-black uppercase text-emerald-700/60 tracking-wider">
                            Impacto Estimado
                        </span>
                        <div className="flex items-center gap-1">
                            <TrendingUp className="h-3 w-3 text-emerald-500" />
                            <span className="text-xs font-black text-emerald-600">
                                {fmt(impacto_valor)}
                            </span>
                        </div>
                    </div>
                )}
            </div>
        ), {
            duration: 5000,
        });

        // 3. Registrar telemetria
        trackIAUXEvento({
            evento: "essential_action_executed",
            modo: "ESSENCIAL",
            metadados: {
                feedback_shown: true,
                feedback_type: reinforcementType,
                impacto_valor,
                time_to_action_ms: tempoValido,
                tipo_ia,
                origem
            }
        });
    }, [metrics, userProfile]);

    return { showFeedback };
};
