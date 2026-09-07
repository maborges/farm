"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle, Info, ShieldAlert, Sparkles, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSearchParams, useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

interface RecomendacaoComercial {
    id_regra: string;
    titulo: string;
    mensagem: string;
    prioridade: "CRITICA" | "ALTA" | "MEDIA" | "BAIXA";
    acao_sugerida: string;
}

export function RecomendacoesInteligentes() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const safraId = searchParams.get("safra_id") || "";
    const commodity = searchParams.get("commodity") || "";
    
    const queryParams = new URLSearchParams();
    if (safraId) queryParams.append("safra_id", safraId);
    if (commodity) queryParams.append("commodity", commodity);
    
    const { data: recomendacoes, isLoading, error } = useQuery<RecomendacaoComercial[]>({
        queryKey: ["financeiro", "hedge", "exposicao", "recomendacoes", safraId, commodity],
        queryFn: () => apiFetch(`/financeiro/hedge/exposicao/recomendacoes?${queryParams.toString()}`),
        refetchOnWindowFocus: false,
    });

    if (isLoading) {
        return (
            <div className="space-y-3">
                <Skeleton className="h-24 w-full rounded-sm" />
            </div>
        );
    }

    if (error || !recomendacoes || recomendacoes.length === 0) {
        return null;
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-500" />
                <h3 className="text-sm font-semibold text-foreground">Recomendações Inteligentes</h3>
            </div>
            
            <div className="grid gap-3">
                {recomendacoes.map((rec) => {
                    let variant: "default" | "destructive" = "default";
                    let Icon = Info;
                    let colorClass = "text-muted-foreground";
                    let bgClass = "bg-background";
                    let borderClass = "border-border";

                    if (rec.prioridade === "CRITICA") {
                        variant = "destructive";
                        Icon = ShieldAlert;
                        bgClass = "bg-red-50 dark:bg-red-950/20";
                        borderClass = "border-red-200 dark:border-red-900";
                    } else if (rec.prioridade === "ALTA") {
                        Icon = AlertTriangle;
                        colorClass = "text-orange-600 dark:text-orange-400";
                        bgClass = "bg-orange-50 dark:bg-orange-950/20";
                        borderClass = "border-orange-200 dark:border-orange-900";
                    } else if (rec.prioridade === "MEDIA") {
                        Icon = Info;
                        colorClass = "text-blue-600 dark:text-blue-400";
                        bgClass = "bg-blue-50 dark:bg-blue-950/20";
                        borderClass = "border-blue-200 dark:border-blue-900";
                    }

                    return (
                        <Alert 
                            key={rec.id_regra} 
                            variant={variant} 
                            className={`rounded-sm ${bgClass} ${borderClass} transition-colors`}
                        >
                            <Icon className={`h-4 w-4 ${colorClass}`} />
                            <AlertTitle className={`text-sm font-semibold flex items-center gap-2 ${colorClass}`}>
                                {rec.titulo}
                            </AlertTitle>
                            <AlertDescription className="mt-2 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <span className="text-muted-foreground leading-relaxed">
                                    {rec.mensagem}
                                </span>
                                <Button 
                                    size="sm" 
                                    variant="outline" 
                                    className="shrink-0"
                                    onClick={() => {
                                        if (rec.acao_sugerida.toLowerCase().includes("contrato")) {
                                            router.push("/dashboard/financeiro/hedge/contratos");
                                        } else {
                                            router.push("/dashboard/financeiro/comercializacoes");
                                        }
                                    }}
                                >
                                    {rec.acao_sugerida}
                                    <ChevronRight className="h-4 w-4 ml-1.5" />
                                </Button>
                            </AlertDescription>
                        </Alert>
                    );
                })}
            </div>
        </div>
    );
}
