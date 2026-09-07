"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Zap, AlertTriangle, TrendingDown, TrendingUp,
    FileText, ArrowRight, BrainCircuit,
    LayoutDashboard
} from "lucide-react";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/stores/app-store";
import {
    useIAFeedback,
    useIAUserProfile,
    useIAExplanation,
    useIAFriction,
    useIAProgresso,
} from "@/hooks";
import { IAUpgradeCTA } from "./ia-upgrade-cta";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info } from "lucide-react";

interface IAEssentialData {
    prioridade: string;
    tipo: string;
    cor: string;
    titulo: string;
    resumo: string;
    detalhe: string;
    impacto_financeiro: string;
    impacto_valor_num?: number;
    rota: string;
    acao_label: string;
}

interface IAEssentialCardProps {
    safraId: string | null;
    onExpand?: () => void;
}

export function IAEssentialCard({ safraId, onExpand }: IAEssentialCardProps) {
    const { data, isLoading } = useQuery<IAEssentialData>({
        queryKey: ["ia-essencial", safraId],
        queryFn: () => apiFetch(`/ia/essencial${safraId ? `?safra_id=${safraId}` : ""}`),
        enabled: true,
        refetchInterval: 60 * 1000,
    });

    const { data: profileData } = useIAUserProfile();
    const { data: explanationData } = useIAExplanation();
    const { data: frictionData } = useIAFriction(!isLoading && !!data);
    const { data: progressoData } = useIAProgresso();
    
    const profile = profileData?.perfil || "NEUTRO";
    const friction = frictionData?.friccao || "BAIXA";
    const nudge = frictionData?.nudge;
    const forceSimplify = frictionData?.acao === "simplificar_ui";

    React.useEffect(() => {
        if (nudge) {
            import("@/lib/ia/ux-telemetry").then(({ trackIAUXEvento }) => {
                trackIAUXEvento({
                    evento: "nudge_visualized",
                    modo: "ESSENCIAL",
                    metadados: {
                        nudge,
                        nivel_friccao: friction
                    }
                });
            });
        }
    }, [nudge, friction]);

    const { modoEssencial } = useAppStore();
    const { showFeedback } = useIAFeedback();
    
    const timer = React.useRef<{ startTime: number; getElapsedTime: () => number } | null>(null);

    React.useEffect(() => {
        if (!isLoading && data) {
            import("@/lib/ia/ux-telemetry").then(({ trackIAUXEvento }) => {
                const t = { 
                    startTime: performance.now(),
                    getElapsedTime: () => Math.round(performance.now() - t.startTime)
                };
                timer.current = t;

                trackIAUXEvento({
                    evento: "essential_view_loaded",
                    modo: "ESSENCIAL",
                    metadados: {
                        tipo_ia: data.tipo,
                        prioridade: data.prioridade,
                        perfil_detectado: profile
                    }
                });
            });
        }
    }, [isLoading, data, profile]);

    const handleActionClick = () => {
        const timeToDecision = timer.current?.getElapsedTime() || 0;
        
        import("@/lib/ia/ux-telemetry").then(({ trackIAUXEvento }) => {
            trackIAUXEvento({
                evento: "essential_cta_clicked",
                modo: "ESSENCIAL",
                metadados: {
                    tipo_ia: data?.tipo,
                    time_to_action_ms: timeToDecision,
                    perfil_detectado: profile
                }
            });

            showFeedback({
                impacto_valor: data?.impacto_valor_num,
                tempo_decisao_ms: timeToDecision,
                tipo_ia: data?.tipo,
                origem: "ESSENTIAL_CARD_CTA"
            });
        });
    };

    const handleExpandClick = () => {
        import("@/lib/ia/ux-telemetry").then(({ trackIAUXEvento }) => {
            trackIAUXEvento({
                evento: "advanced_mode_opened",
                modo: "ESSENCIAL",
                metadados: {
                    tipo_ia: data?.tipo,
                    perfil_detectado: profile
                }
            });
        });
        onExpand?.();
    };

    if (isLoading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-[140px] w-full rounded-sm" />
                <div className="flex justify-end">
                    <Skeleton className="h-8 w-32 rounded-sm" />
                </div>
            </div>
        );
    }

    if (!data) return null;

    const isOk = data.prioridade === "NORMAL" && data.tipo === "STATUS";
    const isConfiante = profile === "CONFIANTE";
    const isAnalitico = profile === "ANALÍTICO";
    const isInseguro = profile === "INSEGURO";

    const getIcon = () => {
        if (isOk) return <BrainCircuit className="text-white" />;
        switch (data.tipo) {
            case "PLANO_ACAO": return <Zap className="text-white" />;
            case "PREDICAO_RISCO": return <TrendingDown className="text-white" />;
            case "ALERTA": return <AlertTriangle className="text-white" />;
            default: return <FileText className="text-white" />;
        }
    };

    const getBgColor = () => {
        if (isOk) return "bg-slate-700";
        switch (data.cor) {
            case "red": return "bg-red-500";
            case "amber": return "bg-amber-500";
            case "emerald": return "bg-emerald-500";
            case "blue": return "bg-blue-500";
            default: return "bg-primary";
        }
    };

    const getBorderColor = () => {
        if (isOk) return "border-slate-200 dark:border-slate-800";
        switch (data.cor) {
            case "red": return "border-red-200 dark:border-red-900/30";
            case "amber": return "border-amber-200 dark:border-amber-900/30";
            case "emerald": return "border-emerald-200 dark:border-emerald-900/30";
            case "blue": return "border-blue-200 dark:border-blue-900/30";
            default: return "border-primary/20";
        }
    };

    return (
        <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-700">
            <Card className={cn(
                "overflow-hidden border-2 shadow-xl transition-all duration-500 relative", 
                getBorderColor(),
                (isConfiante || forceSimplify) ? "max-h-[220px]" : "max-h-[600px]",
                friction === "ALTA" ? "ring-2 ring-amber-500/30" : ""
            )}>
                {nudge && (
                    <div className="absolute top-0 right-0 z-10 animate-in slide-in-from-right-2 duration-500">
                        <div className="bg-amber-500 text-white text-[9px] font-black uppercase px-3 py-1 rounded-bl-sm shadow-sm flex items-center gap-2">
                            <BrainCircuit size={10} className="animate-pulse" />
                            {nudge}
                        </div>
                    </div>
                )}
                <CardContent className="p-0">
                    <div className="flex flex-col md:flex-row">
                        <div className={cn("md:w-20 flex items-center justify-center p-6 md:p-0 transition-colors duration-500", getBgColor())}>
                            {getIcon()}
                        </div>
                        <div className="flex-1 p-6 space-y-4">
                            <div className="flex items-center justify-between gap-4">
                                <div className="flex items-center gap-2">
                                    <Badge variant="outline" className={cn(
                                        "text-[10px] uppercase font-black tracking-wider rounded-sm px-2 py-0.5",
                                        isOk ? "border-slate-300 text-slate-600" : ""
                                    )}>
                                        IA: {data.prioridade}
                                    </Badge>
                                    {profile !== "NEUTRO" && (
                                        <TooltipProvider delay={300}>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Badge variant="outline" className="text-[10px] py-0 h-5 border-emerald-200 bg-emerald-50 text-emerald-700 cursor-help flex items-center gap-1 group">
                                                        Adaptado ao seu perfil
                                                        <Info className="w-3 h-3 text-emerald-500 group-hover:text-emerald-700 transition-colors" />
                                                    </Badge>
                                                </TooltipTrigger>
                                                <TooltipContent side="top" className="max-w-[280px] p-4 bg-white border-emerald-100 shadow-2xl rounded-sm">
                                                    <div className="space-y-2">
                                                        <div className="flex items-center gap-2 border-b border-emerald-50 pb-2">
                                                            <div className="size-2 rounded-full bg-emerald-500 animate-pulse" />
                                                            <p className="font-black text-[11px] text-emerald-900 uppercase tracking-tight">
                                                                {explanationData?.titulo || `Modo ${profile}`}
                                                            </p>
                                                        </div>
                                                        <p className="text-xs text-muted-foreground leading-relaxed">
                                                            {explanationData?.explicacao || "A IA está adaptando a densidade da informação com base no seu ritmo de decisão."}
                                                        </p>
                                                        <div className="pt-1 flex flex-wrap gap-2">
                                                            {explanationData?.metricas_usuario && (
                                                                <>
                                                                    <span className="text-[9px] font-bold px-1.5 py-0.5 bg-muted rounded-sm text-muted-foreground">
                                                                        Tempo: {explanationData.metricas_usuario.tempo_medio}
                                                                    </span>
                                                                    <span className="text-[9px] font-bold px-1.5 py-0.5 bg-muted rounded-sm text-muted-foreground">
                                                                        Execução: {explanationData.metricas_usuario.taxa_execucao}
                                                                    </span>
                                                                </>
                                                            )}
                                                        </div>
                                                    </div>
                                                </TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>
                                    )}
                                </div>
                                {!isOk && (
                                    <span className="text-[10px] font-black text-muted-foreground uppercase flex items-center gap-1.5 tracking-widest">
                                        <BrainCircuit size={14} className="text-primary animate-pulse" />
                                        {isConfiante ? "Sintonia Fina" : "Copiloto em Tempo Real"}
                                    </span>
                                )}
                            </div>

                            <div className="space-y-2">
                                <h3 className="text-xl font-black uppercase tracking-tight leading-tight text-foreground">
                                    {data.titulo}
                                </h3>
                                <p className="text-base font-bold text-foreground/90">
                                    {data.resumo}
                                </p>
                            </div>

                            {/* Detalhes adaptativos baseados no perfil e fricção */}
                            {!isOk && !isConfiante && !forceSimplify && (
                                <div className="p-4 bg-muted/40 rounded-sm border border-border/40 backdrop-blur-sm space-y-3">
                                    <p className="text-sm font-medium text-muted-foreground leading-relaxed italic">
                                        "{data.detalhe}"
                                    </p>
                                    
                                    {isAnalitico && profileData?.metadados && (
                                        <div className="flex items-center gap-2 text-[10px] font-bold text-blue-600 uppercase tracking-tighter">
                                            <Zap className="h-3 w-3 fill-current" />
                                            Baseado em {profileData.metadados.taxa_execucao.toFixed(0)}% de acerto histórico no seu perfil
                                        </div>
                                    )}

                                    {isInseguro && (
                                        <div className="flex items-center gap-2 p-2 bg-emerald-500/10 rounded-sm border border-emerald-500/20">
                                            <BrainCircuit className="h-4 w-4 text-emerald-600" />
                                            <p className="text-[10px] font-black text-emerald-700 uppercase tracking-tight">
                                                Decisão assistida: Nossa IA valida 127 pontos de controle antes de sugerir esta ação.
                                            </p>
                                        </div>
                                    )}

                                    <div className="mt-3 flex items-center gap-3">
                                        <div className="size-1.5 rounded-full bg-border" />
                                        <span className="text-[11px] font-black uppercase text-muted-foreground tracking-wider">Impacto:</span>
                                        <span className={cn(
                                            "text-sm font-black tracking-tight",
                                            data.cor === 'red' ? 'text-red-600' : 'text-emerald-600'
                                        )}>
                                            {data.impacto_financeiro}
                                        </span>
                                    </div>
                                </div>
                            )}

                            {(isConfiante || forceSimplify) && (
                                <div className="flex items-center justify-between p-2 bg-emerald-500/5 rounded-sm border border-emerald-500/10">
                                    <span className="text-[10px] font-black uppercase text-emerald-600 tracking-widest">
                                        {forceSimplify ? "Impacto Resumido" : "Impacto Estimado"}
                                    </span>
                                    <span className="text-sm font-black text-emerald-600">{data.impacto_financeiro}</span>
                                </div>
                            )}

                            <div className="flex items-center justify-between pt-2">
                                {isOk ? (
                                    <p className="text-xs font-bold text-muted-foreground italic">
                                        Tudo sob controle. Nenhuma ação pendente no momento.
                                    </p>
                                ) : (
                                    <div />
                                )}
                                <Button asChild size="sm" variant="outline" className={cn(
                                    "font-black uppercase text-[10px] rounded-sm h-8 px-6 shadow-sm transition-all active:scale-95",
                                    "border-primary/30 text-primary"
                                )}>
                                    <Link href={data.rota} onClick={handleActionClick}>
                                        {data.acao_label}
                                        <ArrowRight size={14} className="ml-1.5" />
                                    </Link>
                                </Button>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <IAUpgradeCTA contexto="acao" compact />

            {progressoData?.mensagem_destaque && (
                <div className="flex items-center gap-2 rounded-sm border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 animate-in fade-in duration-500">
                    <TrendingUp size={12} className="text-emerald-600 shrink-0" />
                    <p className="text-[10px] font-semibold text-emerald-700 leading-snug">
                        {progressoData.mensagem_destaque}
                    </p>
                </div>
            )}

            <div className="flex justify-center">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleExpandClick}
                    className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground hover:text-primary hover:bg-transparent transition-all group"
                >
                    Ver detalhes completos
                    <LayoutDashboard size={14} className="ml-2 opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0" />
                </Button>
            </div>
        </div>
    );
}
