import React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, CheckCircle2, ShieldAlert, Truck, Info, Leaf } from "lucide-react";

interface Recommendation {
    tipo_operacao: string;
    status: string;
    severidade: string;
    motivo: string;
    dados_utilizados: Record<string, unknown>;
    fonte: string;
}

interface ApiError {
    status?: number;
    message?: string;
}

function getApiError(error: unknown): ApiError {
    return typeof error === "object" && error !== null ? error as ApiError : {};
}

function getRecommendationIcon(severity: string) {
    if (severity === "CRITICAL") return <AlertCircle className="size-5 text-red-500" />;
    if (severity === "WARNING") return <AlertCircle className="size-5 text-amber-500" />;
    return <CheckCircle2 className="size-5 text-green-500" />;
}

function getRecommendationBadge(severity: string) {
    if (severity === "CRITICAL") return <Badge variant="destructive" className="rounded-sm text-[10px]">Inviável</Badge>;
    if (severity === "WARNING") return <Badge variant="secondary" className="rounded-sm text-[10px] bg-amber-500 hover:bg-amber-600 text-white border-transparent">Atenção</Badge>;
    return <Badge variant="outline" className="rounded-sm text-[10px] border-green-500 text-green-600">Recomendado</Badge>;
}

function RecommendationItem({
    title,
    recommendation,
    icon,
}: {
    title: string;
    recommendation: Recommendation;
    icon: React.ReactNode;
}) {
    return (
        <div className="flex items-start gap-4 p-4 rounded-sm border bg-card">
            <div className="mt-1 flex-shrink-0">{getRecommendationIcon(recommendation.severidade)}</div>
            <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold flex items-center gap-2">
                        {title}
                        {icon}
                    </h4>
                    {getRecommendationBadge(recommendation.severidade)}
                </div>
                <p className="text-xs font-medium text-foreground">{recommendation.status}</p>
                <p className="text-xs text-muted-foreground">{recommendation.motivo}</p>
            </div>
        </div>
    );
}

export function RecomendacoesPecuaria() {
    const { activeFazendaId } = useAppStore();

    const { data: recomendacoes = [], isLoading, error } = useQuery<Recommendation[]>({
        queryKey: ["pecuaria", "climatico", "recomendacoes", activeFazendaId],
        queryFn: () => apiFetch(`/pecuaria/climatico/inteligencia/recomendacoes/${activeFazendaId}`, { suppressErrorLog: true }),
        enabled: !!activeFazendaId,
        retry: (failureCount, error: unknown) => {
            if (getApiError(error).status === 402) return false;
            return failureCount < 2;
        },
    });

    if (isLoading) {
        return <Skeleton className="h-48 w-full rounded-sm" />;
    }

    if (error || !recomendacoes) {
        const isUpgradeRequired = getApiError(error).status === 402;
        
        // Se requer upgrade, apenas oculta o componente em vez de exibir painel de upsell
        // para não poluir ou confundir a tela de Previsão Básica.
        if (isUpgradeRequired) {
            return null;
        }
        
        return (
            <Card className="border-dashed border-2 border-border/60 bg-muted/30">
                <CardContent className="p-8 flex flex-col items-center justify-center text-center space-y-4">
                    <ShieldAlert size={32} className="text-muted-foreground/50" />
                    <div>
                        <h3 className="text-sm font-bold">Motor de Recomendações Indisponível</h3>
                        <p className="text-xs text-muted-foreground max-w-sm">
                            Não foi possível carregar as recomendações operacionais da pecuária no momento.
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const byType = new Map(recomendacoes.map((rec) => [rec.tipo_operacao, rec]));

    return (
        <div className="space-y-4">
            <h2 className="text-lg font-bold flex items-center gap-2">
                <Info className="size-5 text-primary" />
                Recomendações Operacionais (Pecuária)
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {byType.get("TRANSPORTE") && (
                    <RecommendationItem
                        title="Transporte de Animais"
                        recommendation={byType.get("TRANSPORTE")!}
                        icon={<Truck className="size-5 text-slate-500" />}
                    />
                )}
                {byType.get("SUPLEMENTACAO") && (
                    <RecommendationItem
                        title="Suplementação a Pasto"
                        recommendation={byType.get("SUPLEMENTACAO")!}
                        icon={<Info className="size-5 text-amber-700" />}
                    />
                )}
                {byType.get("MANEJO_PASTO") && (
                    <RecommendationItem
                        title="Manejo de Pasto"
                        recommendation={byType.get("MANEJO_PASTO")!}
                        icon={<Leaf className="size-5 text-green-600" />}
                    />
                )}
            </div>

            {recomendacoes.filter((rec) => rec.tipo_operacao === "GERAL").length > 0 && (
                <Card className="vuexy-card border-0 rounded-sm mt-4 bg-muted/20">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Avisos Operacionais Gerais</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {recomendacoes.filter((rec) => rec.tipo_operacao === "GERAL").map((rec, index) => (
                            <div key={index} className="flex items-start gap-3 p-3 bg-background rounded-sm border shadow-sm">
                                {getRecommendationIcon(rec.severidade)}
                                <div>
                                    <h4 className="text-sm font-bold">{rec.status}</h4>
                                    <p className="text-xs text-muted-foreground">{rec.motivo}</p>
                                </div>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
