"use client";

import { useQuery } from "@tanstack/react-query";
import { BrainCircuit, ChevronRight, Lightbulb, TriangleAlert, Sparkles, Bot, Lock, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ResumoConsultivo {
    titulo: string;
    resumo: string;
    recomendacoes: string[];
    pontos_atencao: string[];
    nivel_confianca: string;
    fonte: string;
    ia_disponivel: boolean;
    limite_atingido: boolean;
}

interface Props {
    safraId: string;
}

function trackEvent(event: string, props?: Record<string, string>) {
    if (typeof window === "undefined") return;
    try {
        // Envia evento simples via beacon para não bloquear UI
        const payload = JSON.stringify({ event, ...props, ts: Date.now() });
        navigator.sendBeacon?.("/api/analytics", payload);
    } catch {
        // Analytics must never block the dashboard.
    }
}

export function AssistenteSafraCard({ safraId }: Props) {
    const { data } = useQuery<ResumoConsultivo>({
        queryKey: ["resumo-consultivo", safraId],
        queryFn: async () => {
            const result = await apiFetch<ResumoConsultivo>(`/financeiro/lancamentos/resumo-consultivo?safra_id=${safraId}`);
            if (!result.ia_disponivel) {
                trackEvent("monetization_blocked", { feature: "ia_resumo", surface: "assistente_safra_card" });
            }
            return result;
        },
        staleTime: 60_000,
        enabled: !!safraId,
    });

    if (!data) return null;

    const isIA = data.fonte === "IA";

    return (
        <section className="rounded-sm border border-border bg-card shadow-sm overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-border bg-muted/30">
                <span className="size-8 rounded-sm bg-primary/10 border border-primary/15 flex items-center justify-center shrink-0">
                    <BrainCircuit className="size-4 text-primary" />
                </span>
                <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                        Assistente da Safra
                    </p>
                    <p className="text-sm font-semibold text-foreground leading-tight">
                        {data.titulo}
                    </p>
                </div>
                {/* IA Badge */}
                {isIA && (
                  <Badge
                    variant="outline"
                    className="shrink-0 text-[10px] gap-1 px-2 h-5 border-primary/30 text-primary bg-primary/5"
                  >
                    <span className="mr-1">✨</span> Análise com IA
                  </Badge>
                )}
            </div>

            <div className="p-5 space-y-5">
                {/* Resumo executivo */}
                <p className="text-sm text-foreground leading-relaxed">
                    {data.resumo}
                </p>

                <div className="grid gap-4 sm:grid-cols-2">
                    {/* Pontos de atenção */}
                    {data.pontos_atencao.length > 0 && (
                        <div className="space-y-2">
                            <p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                <TriangleAlert className="size-3" />
                                Pontos de atenção
                            </p>
                            <ul className="space-y-1.5">
                                {data.pontos_atencao.map((p, i) => (
                                    <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground leading-snug">
                                        <span className="size-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                        {p}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Recomendações */}
                    {data.recomendacoes.length > 0 && (
                        <div className="space-y-2">
                            <p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                <Lightbulb className="size-3" />
                                Próximas ações
                            </p>
                            <ul className="space-y-1.5">
                                {data.recomendacoes.map((a, i) => (
                                    <li key={i} className="flex items-start gap-2 text-xs text-foreground leading-snug">
                                        <ChevronRight className="size-3.5 text-primary mt-0.5 shrink-0" />
                                        {a}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>

                {/* Aviso de limite mensal atingido */}
                {data.ia_disponivel && data.limite_atingido && (
                    <div className="flex items-center gap-3 rounded-sm border border-amber-500/20 bg-amber-500/5 px-4 py-3">
                        <AlertCircle className="size-4 text-amber-500 shrink-0" />
                        <p className="text-xs text-muted-foreground leading-snug">
                            Você atingiu o limite mensal de análises com IA. O resumo abaixo é automático.
                        </p>
                    </div>
                )}

                {/* CTA upgrade — apenas quando IA não disponível no plano */}
                {!data.ia_disponivel && (
                    <div className="flex items-center gap-3 rounded-sm border border-primary/15 bg-primary/5 px-4 py-3">
                        <Lock className="size-4 text-primary/60 shrink-0" />
                        <p className="flex-1 text-xs text-muted-foreground leading-snug">
                            Desbloqueie análise inteligente com IA no plano{" "}
                            <span className="font-semibold text-foreground">Profissional</span>
                        </p>
                        <Button
                            size="sm"
                            variant="outline"
                            className="h-8 rounded-sm px-3 text-xs font-semibold shrink-0"
                            onClick={() => {
                                trackEvent("monetization_cta_clicked", {
                                    feature: "ia_resumo",
                                    surface: "assistente_safra_card",
                                    target_tier: "PROFISSIONAL",
                                });
                                window.location.href = "/dashboard/configuracoes/plano";
                            }}
                        >
                            Ver planos
                        </Button>
                    </div>
                )}
            </div>
        </section>
    );
}
