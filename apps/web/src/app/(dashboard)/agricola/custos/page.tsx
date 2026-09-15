"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { 
    Calculator,
    PieChart,
    BarChart,
    Wallet,
    DollarSign
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { formatCurrency, formatArea } from "@farm/utils";

interface CustoBreakdown {
    categoria: string;
    valor_total: number;
    valor_por_ha: number;
    percentual: number;
}

interface ResumoCustos {
    safra_id: string;
    area_total_ha: number;
    custo_total_realizado: number;
    custo_realizado_por_ha: number;
    orcamento_previsto_total: number | null;
    desvio_orcamento_pct: number | null;
    fonte_orcamento_previsto: string;
    usou_fallback_orcamento: boolean;
    fonte_apuracao: string;
    usou_fallback_operacional: boolean;
    breakdown: CustoBreakdown[];
}

interface SafraKPI {
    safra_id: string;
    cultura: string;
    ano_safra: string;
    area_ha: number;
    custo_previsto_ha: number | null;
    custo_realizado_ha: number | null;
}

interface CampanhasResponse {
    safras: SafraKPI[];
}

export default function CustosPage() {
    const [selectedSafraId, setSelectedSafraId] = useState<string>("all");

    // Fetch safras active (from Campanhas, which gives everything we need)
    const { data: campanhas, isLoading: isLoadingCampanhas } = useQuery<CampanhasResponse>({
        queryKey: ["campanhas"],
        queryFn: () => apiFetch("/agricola/planejamento/campanhas"),
    });

    const safras = campanhas?.safras ?? [];
    const safraSelecionadaParam = selectedSafraId === "all" ? (safras[0]?.safra_id || null) : selectedSafraId;
    const safraAtualObj = safras.find(s => s.safra_id === safraSelecionadaParam);

    // Fetch Resumo do Custo da safra selecionada
    const { data: relatorio, isLoading: isLoadingRelatorio } = useQuery<ResumoCustos>({
        queryKey: ["custos", safraSelecionadaParam],
        queryFn: () => apiFetch(`/custos/safra/${safraSelecionadaParam}`),
        enabled: !!safraSelecionadaParam,
    });

    if (isLoadingCampanhas || isLoadingRelatorio) {
        return (
            <div className="space-y-6 p-6">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-32 w-full" />
                <div className="flex gap-4">
                    <Skeleton className="h-96 w-1/2" />
                    <Skeleton className="h-96 w-1/2" />
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Custeio Agrícola"
                description="Custo de produção por safra com orçamento, apropriação econômica e histórico."
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Custeio Agrícola" }]}
                icon={<Wallet className="text-primary" size={22} />}
            />

            {/* Seletor de Safra */}
            <Card className="shadow-sm">
                <CardContent className="p-4">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div className="flex flex-col gap-1">
                            <span className="text-xs text-muted-foreground uppercase tracking-wider">Qual Safra Analisar?</span>
                            {safraAtualObj && (
                                <p className="text-sm text-muted-foreground">
                                    {safraAtualObj.cultura} • Safra {safraAtualObj.ano_safra} • {formatArea(safraAtualObj.area_ha)}
                                </p>
                            )}
                        </div>
                        <Select value={selectedSafraId} onValueChange={setSelectedSafraId}>
                            <SelectTrigger className="w-full md:w-[240px]">
                                <SelectValue placeholder="Selecionar safra..." />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Automático (Mais recente)</SelectItem>
                                {safras.map(s => (
                                    <SelectItem key={s.safra_id} value={s.safra_id}>{s.cultura} — {s.ano_safra}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                        <span className="text-xs uppercase tracking-wider text-muted-foreground">Fonte do resumo</span>
                        <Badge variant={relatorio.fonte_apuracao === "COST_ALLOCATION" ? "success" : "warning"}>
                            {relatorio.usou_fallback_operacional ? "Fallback operacional" : "Apropriação econômica oficial"}
                        </Badge>
                        {relatorio.usou_fallback_operacional && (
                            <span className="text-xs text-muted-foreground">
                                Não houve CostAllocation consolidada para esta safra; o resumo usa custo operacional como contingência.
                            </span>
                        )}
                    </div>
                </CardContent>
            </Card>

            {relatorio && (
                <>
                    {/* KPIs principais */}
                    <div className="grid gap-4 md:grid-cols-2">
                        <Card className="shadow-sm">
                            <CardHeader className="pb-2 flex flex-row items-center justify-between">
                                <CardTitle className="text-sm font-medium text-muted-foreground">Custo Total (Realizado)</CardTitle>
                                <DollarSign className="size-5 text-blue-500 opacity-40" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold text-blue-700">{formatCurrency(relatorio.custo_total_realizado)}</div>
                                <p className="text-sm text-muted-foreground mt-2 font-mono">
                                    {formatCurrency(relatorio.custo_realizado_por_ha)} por hectare
                                </p>
                            </CardContent>
                        </Card>

                        <Card className="shadow-sm">
                            <CardHeader className="pb-2 flex flex-row items-center justify-between">
                                <CardTitle className="text-sm font-medium text-muted-foreground">Orçamento Planejado</CardTitle>
                                <Calculator className="size-5 text-amber-500 opacity-40" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold text-amber-700">
                                    {relatorio.orcamento_previsto_total ? formatCurrency(relatorio.orcamento_previsto_total) : "—"}
                                </div>
                                {relatorio.desvio_orcamento_pct !== null && (
                                    <p className={`text-sm mt-2 font-medium ${relatorio.desvio_orcamento_pct > 0 ? "text-red-600" : "text-emerald-600"}`}>
                                        {relatorio.desvio_orcamento_pct > 0 ? "+" : ""}{relatorio.desvio_orcamento_pct}% do orçado
                                    </p>
                                )}
                                <p className="text-xs text-muted-foreground mt-2">
                                    {relatorio.usou_fallback_orcamento
                                        ? "Fonte: custo previsto da safra (fallback)"
                                        : "Fonte: Orçamento de Safra"}
                                </p>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Distribuição por Categoria */}
                    <Card className="shadow-sm">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <PieChart className="size-4 text-muted-foreground" />
                                Distribuição por Categoria
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {!relatorio.breakdown?.length ? (
                                <p className="text-sm text-muted-foreground">Nenhum custo apropriado</p>
                            ) : (
                                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                    {relatorio.breakdown.sort((a,b) => b.valor_total - a.valor_total).map(c => (
                                        <div key={c.categoria} className="p-3 bg-slate-50 rounded-sm border">
                                            <div className="flex justify-between items-start mb-2">
                                                <span className="font-medium text-xs">{c.categoria}</span>
                                                <span className="text-xs text-muted-foreground">{c.percentual}%</span>
                                            </div>
                                            <div className="h-1.5 bg-slate-200 rounded-full mb-2 overflow-hidden">
                                                <div className="h-full bg-blue-600" style={{ width: `${c.percentual}%` }} />
                                            </div>
                                            <p className="text-xs text-muted-foreground">
                                                <span className="font-mono">{formatCurrency(c.valor_total)}</span><br/>
                                                {formatCurrency(c.valor_por_ha)}/ha
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Histórico de Safras */}
                    <Card className="shadow-sm">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <BarChart className="size-4 text-muted-foreground" />
                                Histórico de Custos
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {!safras.length ? (
                                <p className="text-sm text-muted-foreground">Sem histórico</p>
                            ) : (
                                <div className="space-y-3">
                                    {safras.map(s => {
                                        const realizado = s.custo_realizado_ha ?? 0;
                                        const planejado = s.custo_previsto_ha ?? 0;
                                        const maxRef = Math.max(...safras.map(x => x.custo_realizado_ha || 0), 1);
                                        return (
                                            <div key={s.safra_id} className="text-sm">
                                                <div className="flex justify-between mb-1">
                                                    <span className="font-medium">{s.cultura} {s.ano_safra}</span>
                                                    <span className="text-muted-foreground font-mono">{formatCurrency(realizado)}/ha</span>
                                                </div>
                                                <div className="h-2 bg-slate-100 rounded overflow-hidden">
                                                    <div className={`h-full ${realizado > (planejado || 0) ? 'bg-red-500' : 'bg-emerald-500'}`} style={{ width: `${(realizado / maxRef) * 100}%` }} />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
}
