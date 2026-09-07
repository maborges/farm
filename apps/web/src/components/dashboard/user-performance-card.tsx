"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Trophy, Target, TrendingUp, Star, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

interface PerformanceUsuario {
    total_decisoes: number;
    economia_total: number;
    melhor_decisao: {
        safra: string;
        ganho: number;
    };
    taxa_sucesso: number;
    ranking: string;
    nivel: string;
}

export function UserPerformanceCard() {
    const { data, isLoading } = useQuery<PerformanceUsuario>({
        queryKey: ["performance-usuario"],
        queryFn: () => apiFetch("/financeiro/lancamentos/performance-usuario"),
        staleTime: 300_000, // 5 minutos
    });

    if (isLoading) {
        return (
            <Card className="border-primary/10 bg-primary/5">
                <CardContent className="flex h-32 items-center justify-center">
                    <Loader2 className="size-6 animate-spin text-primary/40" />
                </CardContent>
            </Card>
        );
    }

    if (!data || data.total_decisoes === 0) return null;

    const getNivelColor = (nivel: string) => {
        switch (nivel) {
            case "LENDÁRIO": return "bg-purple-500/10 text-purple-600 border-purple-500/20";
            case "EXPERIENTE": return "bg-blue-500/10 text-blue-600 border-blue-500/20";
            case "PROFISSIONAL": return "bg-emerald-500/10 text-emerald-600 border-emerald-500/20";
            default: return "bg-slate-500/10 text-slate-600 border-slate-500/20";
        }
    };

    return (
        <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="rounded-full bg-primary/10 p-2 text-primary">
                            <Trophy size={18} />
                        </div>
                        <CardTitle className="text-sm font-bold uppercase tracking-wider">Seu Desempenho</CardTitle>
                    </div>
                    <Badge variant="outline" className={`${getNivelColor(data.nivel)} font-bold px-3`}>
                        {data.nivel}
                    </Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    <div className="space-y-1">
                        <p className="text-[10px] font-bold uppercase text-muted-foreground">Impacto Financeiro</p>
                        <p className="text-xl font-semibold text-emerald-600">
                            {data.economia_total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                        </p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] font-bold uppercase text-muted-foreground">Taxa de Sucesso</p>
                        <div className="flex items-center gap-2">
                            <p className="text-xl font-semibold">{data.taxa_sucesso}%</p>
                            <Target size={14} className="text-primary" />
                        </div>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] font-bold uppercase text-muted-foreground">Decisões Tomadas</p>
                        <p className="text-xl font-semibold">{data.total_decisoes}</p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] font-bold uppercase text-muted-foreground">Ranking Global</p>
                        <p className="text-xl font-semibold text-primary">{data.ranking}</p>
                    </div>
                </div>

                <div className="rounded-sm bg-background/50 p-4 border border-primary/10">
                    <div className="flex items-start gap-3">
                        <div className="mt-1 rounded-full bg-amber-500/10 p-2 text-amber-600">
                            <Star size={16} />
                        </div>
                        <div className="space-y-1">
                            <p className="text-xs font-bold text-muted-foreground uppercase">Destaque de Performance</p>
                            <p className="text-sm font-medium leading-relaxed">
                                Sua melhor decisão até agora foi em <span className="font-bold text-foreground">{data.melhor_decisao.safra}</span>, 
                                gerando um retorno projetado de <span className="font-bold text-emerald-600">{data.melhor_decisao.ganho.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span>.
                            </p>
                        </div>
                    </div>
                </div>

                <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] font-bold uppercase">
                        <span className="text-muted-foreground">Precisão das Projeções</span>
                        <span className="text-primary">{data.taxa_sucesso}%</span>
                    </div>
                    <Progress value={data.taxa_sucesso} className="h-1.5" />
                    <p className="text-[10px] text-muted-foreground italic">
                        Mantenha suas projeções próximas ao real para subir de nível e desbloquear novos insights.
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}
