"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, AlertTriangle, Info, ChevronRight, Loader2, Sparkles, Wand2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

const dashboardCardButtonClass = "h-8 rounded-sm px-3 text-xs font-semibold";

interface AlertaInteligente {
    id: string;
    tipo: string;
    gravidade: string;
    titulo: string;
    mensagem: string;
    impacto: string;
    recomendacao: string;
    acao?: string;
    parametros?: Record<string, any>;
    prioridade?: number; // Step 197
    motivo_prioridade?: string; // Step 197
    acao_sugerida?: {
        acao: "SIMULACAO" | "AJUSTE_CENARIO" | "ANALISE_DETALHADA";
        parametros: Record<string, any>;
        descricao: string;
    };
}

export function AlertasInteligentesCard({ safraId }: { safraId: string }) {
    const router = useRouter();
    const { data: alertas, isLoading } = useQuery<AlertaInteligente[]>({
        queryKey: ["alertas-inteligentes", safraId],
        queryFn: () => apiFetch(`/financeiro/lancamentos/alertas-inteligentes?safra_id=${safraId}`),
        enabled: !!safraId,
        staleTime: 300_000,
    });

    // Step 194: Track visualization — must be before any early returns (Rules of Hooks)
    useEffect(() => {
        if (alertas && alertas.length > 0) {
            alertas.forEach(alerta => {
                apiFetch(`/ia/alertas/${alerta.id}/visualizado`, { method: "PATCH" }).catch(() => {});
            });
        }
    }, [alertas]);

    if (isLoading) {
        return (
            <Card className="border-primary/10">
                <CardContent className="flex h-24 items-center justify-center">
                    <Loader2 className="size-5 animate-spin text-primary/30" />
                </CardContent>
            </Card>
        );
    }

    if (!alertas || alertas.length === 0) return null;

    const handleAcao = async (alerta: AlertaInteligente) => {
        // Step 194: Track execution
        apiFetch(`/ia/alertas/${alerta.id}/executado`, { method: "PATCH" }).catch(() => {});

        if (alerta.acao === "simular") {
            const params = new URLSearchParams();
            if (alerta.parametros?.receita_percentual !== undefined) params.set("receita", alerta.parametros.receita_percentual.toString());
            if (alerta.parametros?.custos_percentual !== undefined) params.set("custos", alerta.parametros.custos_percentual.toString());
            router.push(`/dashboard/financeiro/dre?safra_id=${safraId}&${params.toString()}`);
        } else if (alerta.acao === "comparar") {
            router.push(`/dashboard/financeiro/dre?safra_id=${safraId}&view=comparar`);
        }
    };

    const handleExecutarSugestao = async (sugestao: NonNullable<AlertaInteligente["acao_sugerida"]>, alertaId: string) => {
        // Step 201: Registrar ação assistida
        let actionId = "";
        try {
            const resp = await apiFetch("/ia/acoes-assistidas/registrar", {
                method: "POST",
                body: {
                    origem: "ALERTA_INTELIGENTE",
                    origem_id: alertaId,
                    tipo_acao: sugestao.acao,
                    parametros_json: sugestao.parametros
                }
            });
            actionId = (resp as any).id;
        } catch (e) {
            console.error("Erro ao registrar ação assistida:", e);
        }

        const actionParam = actionId ? `&action_id=${actionId}` : "";

        if (sugestao.acao === "SIMULACAO") {
            const params = new URLSearchParams();
            if (sugestao.parametros.receita_percentual !== undefined) params.set("receita", sugestao.parametros.receita_percentual.toString());
            if (sugestao.parametros.custos_percentual !== undefined) params.set("custos", sugestao.parametros.custos_percentual.toString());
            router.push(`/dashboard/financeiro/dre?safra_id=${safraId}&${params.toString()}&auto_simular=true${actionParam}`);
        } else if (sugestao.acao === "AJUSTE_CENARIO") {
            router.push(`/dashboard/agricola/safras/${safraId}/cenarios?ajuste_sugerido=true&cenario_id=${sugestao.parametros.cenario_id}${actionParam}`);
        }
    };

    const handleIgnorar = async (alertaId: string) => {
        try {
            await apiFetch(`/ia/alertas/${alertaId}/ignorado`, { method: "PATCH" });
        } catch (error) {
            console.error("Erro ao ignorar alerta:", error);
        }
    };

    const getGravidadeIcon = (gravidade: string) => {
        switch (gravidade) {
            case "alta": return <AlertCircle className="text-destructive" size={18} />;
            case "media": return <AlertTriangle className="text-amber-500" size={18} />;
            default: return <Info className="text-blue-500" size={18} />;
        }
    };

    const getGravidadeBadge = (gravidade: string) => {
        switch (gravidade) {
            case "alta": return <Badge variant="destructive" className="uppercase text-[9px] font-bold">Crítico</Badge>;
            case "media": return <Badge variant="outline" className="border-amber-500/50 text-amber-600 bg-amber-500/5 uppercase text-[9px] font-bold">Atenção</Badge>;
            default: return <Badge variant="outline" className="border-blue-500/50 text-blue-600 bg-blue-500/5 uppercase text-[9px] font-bold">Informativo</Badge>;
        }
    };

    const getPrioridadeBadge = (prioridade?: number) => {
        if (!prioridade) return null;
        if (prioridade >= 85) return <Badge variant="outline" className="border-primary text-primary bg-primary/5 uppercase text-[9px] font-semibold tracking-tighter">Prioridade Máxima</Badge>;
        if (prioridade >= 60) return <Badge variant="outline" className="border-primary/30 text-primary/70 bg-primary/5 uppercase text-[9px] font-bold">Importante</Badge>;
        return null;
    };

    return (
        <Card className="border-primary/20 shadow-sm overflow-hidden bg-gradient-to-r from-primary/[0.02] to-transparent">
            <CardHeader className="pb-3 border-b border-primary/10">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="bg-primary/10 p-1.5 rounded-full">
                            <Sparkles size={16} className="text-primary" />
                        </div>
                        <CardTitle className="text-sm font-bold uppercase tracking-tight">Copiloto: Prioridades de Ação</CardTitle>
                    </div>
                    <Badge variant="secondary" className="text-[10px]">{alertas.length} {alertas.length === 1 ? 'alerta' : 'alertas'}</Badge>
                </div>
            </CardHeader>
            <CardContent className="p-0 divide-y divide-primary/5">
                {alertas.map((alerta, index) => (
                    <div 
                        key={alerta.id} 
                        className={cn(
                            "p-5 flex flex-col gap-4 hover:bg-primary/[0.01] transition-colors relative",
                            index === 0 && "bg-primary/[0.03] border-l-4 border-l-primary"
                        )}
                    >
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex items-start gap-3">
                                <div className="mt-0.5">{getGravidadeIcon(alerta.gravidade)}</div>
                                <div className="space-y-1.5">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <h4 className="font-bold text-sm leading-none">{alerta.titulo}</h4>
                                        {getGravidadeBadge(alerta.gravidade)}
                                        {getPrioridadeBadge(alerta.prioridade)}
                                    </div>
                                    <p className="text-xs text-muted-foreground leading-relaxed">{alerta.mensagem}</p>
                                    
                                    {alerta.motivo_prioridade && (
                                        <div className="flex items-center gap-1.5 text-[10px] text-primary/70 font-bold bg-primary/5 py-1 px-2 rounded-sm w-fit">
                                            <Wand2 size={10} className="animate-pulse" />
                                            {alerta.motivo_prioridade}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-background/50 p-3 rounded-sm border border-primary/5">
                            <div className="space-y-1">
                                <span className="text-[10px] font-semibold uppercase text-muted-foreground/70">Impacto Esperado</span>
                                <p className="text-[11px] font-medium italic">{alerta.impacto}</p>
                            </div>
                            <div className="space-y-1">
                                <span className="text-[10px] font-semibold uppercase text-primary/70">Ação Recomendada</span>
                                <p className="text-[11px] font-bold text-primary">{alerta.recomendacao}</p>
                            </div>
                        </div>

                        <div className="flex justify-end gap-2">
                            <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => handleIgnorar(alerta.id)}
                                className={cn(dashboardCardButtonClass, "text-muted-foreground")}
                            >
                                Ignorar
                            </Button>
                            {alerta.acao_sugerida && (
                                <Button 
                                    variant="default" 
                                    size="sm" 
                                    onClick={() => handleExecutarSugestao(alerta.acao_sugerida!, alerta.id)}
                                    className={dashboardCardButtonClass}
                                >
                                    <Sparkles data-icon="inline-start" />
                                    Executar sugestão
                                </Button>
                            )}
                            {alerta.acao && !alerta.acao_sugerida && (
                                <Button 
                                    variant="default" 
                                    size="sm" 
                                    onClick={() => handleAcao(alerta)}
                                    className={dashboardCardButtonClass}
                                >
                                    <Wand2 data-icon="inline-start" />
                                    Ajustar agora
                                </Button>
                            )}
                            <Button variant="outline" size="sm" className={dashboardCardButtonClass}>
                                Analisar detalhes
                                <ChevronRight data-icon="inline-end" />
                            </Button>
                        </div>
                    </div>
                ))}
            </CardContent>
        </Card>
    );
}
