"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Shield, TrendingUp, TrendingDown, Target, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { HedgeExposicao, HedgePosicao } from "../types";

type SafraOption = {
    id: string;
    ano_safra: string;
    cultura?: string;
};

export function PainelClient({ 
    initialExposicao, initialPosicao, safras, initialSafraId 
}: { 
    initialExposicao: HedgeExposicao | null, initialPosicao: HedgePosicao | null, safras: SafraOption[], initialSafraId: string 
}) {
    const router = useRouter();
    const [safraId, setSafraId] = useState(initialSafraId);

    const qs = safraId ? `?safra_id=${safraId}` : "";

    const { data: exposicao, isLoading: expLoading } = useQuery<HedgeExposicao>({
        queryKey: ["financeiro", "hedge", "exposicao", safraId],
        queryFn: () => apiFetch(`/financeiro/hedge/exposicao${qs}`),
        initialData: initialExposicao || undefined,
    });

    const { data: posicao, isLoading: posLoading } = useQuery<HedgePosicao>({
        queryKey: ["financeiro", "hedge", "posicao", safraId],
        queryFn: () => apiFetch(`/financeiro/hedge/posicao${qs}`),
        initialData: initialPosicao || undefined,
    });

    const handleSafraChange = (val: string) => {
        setSafraId(val === "all" ? "" : val);
        router.push(`/dashboard/financeiro/hedge/painel${val === "all" ? "" : `?safra_id=${val}`}`);
    };

    return (
        <div className="p-6 space-y-6 animate-in fade-in duration-500">
            <PageHeader
                title="Painel de Exposição"
                description="Visão executiva do risco de preço e cobertura"
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Hedge" },
                    { label: "Painel Geral" }
                ]}
                icon={<Shield className="text-primary" size={22} />}
                actions={
                    <div className="w-64">
                        <Select value={safraId || "all"} onValueChange={handleSafraChange}>
                            <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue placeholder="Filtrar por Safra" /></SelectTrigger>
                            <SelectContent className="rounded-sm">
                                <SelectItem value="all" className="text-sm">Todas as Safras</SelectItem>
                                {safras.map(s => <SelectItem key={s.id} value={s.id} className="text-sm">{s.cultura ? `${s.ano_safra} - ${s.cultura}` : s.ano_safra}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                }
            />

            <h3 className="text-lg font-semibold tracking-tight">Posição Consolidada</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="rounded-sm border-l-[3px] border-l-primary/60 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Contratos Abertos</CardTitle>
                        <Activity className="size-4 text-muted-foreground opacity-50" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black tabular-nums">
                            {posLoading ? <Skeleton className="h-8 w-16 rounded-sm" /> : posicao?.total_contratos_abertos || 0}
                        </div>
                    </CardContent>
                </Card>
                <Card className="rounded-sm border-l-[3px] border-l-primary/60 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Volume Total Hedgeado</CardTitle>
                        <Shield className="size-4 text-muted-foreground opacity-50" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black tabular-nums">
                            {posLoading ? <Skeleton className="h-8 w-24 rounded-sm" /> : `${posicao?.quantidade_total_hedgeada?.toLocaleString("pt-BR") || 0} sc`}
                        </div>
                    </CardContent>
                </Card>
                <Card className="rounded-sm border-l-[3px] border-l-primary/60 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Preço Médio Ponderado</CardTitle>
                        <Target className="size-4 text-muted-foreground opacity-50" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black tabular-nums">
                            {posLoading ? <Skeleton className="h-8 w-24 rounded-sm" /> : posicao?.preco_medio_ponderado ? posicao.preco_medio_ponderado.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—"}
                        </div>
                    </CardContent>
                </Card>
            </div>

            <h3 className="text-lg font-semibold tracking-tight mt-8">Exposição e Cobertura</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="rounded-sm border-l-[3px] border-l-neutral-400/50 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Produção Estimada</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black tabular-nums text-neutral-800 dark:text-neutral-200">
                            {expLoading ? <Skeleton className="h-8 w-full rounded-sm" /> : `${exposicao?.producao_estimada_sc?.toLocaleString("pt-BR") || 0} sc`}
                        </div>
                    </CardContent>
                </Card>
                <Card className="rounded-sm border-l-[3px] border-l-blue-500/60 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Já Vendido (Físico)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black tabular-nums text-blue-600 dark:text-blue-400">
                            {expLoading ? <Skeleton className="h-8 w-full rounded-sm" /> : `${exposicao?.ja_vendido_sc?.toLocaleString("pt-BR") || 0} sc`}
                        </div>
                    </CardContent>
                </Card>
                <Card className="rounded-sm border-l-[3px] border-l-emerald-500/60 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Já Hedgeado (Papel)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black tabular-nums text-emerald-600 dark:text-emerald-400">
                            {expLoading ? <Skeleton className="h-8 w-full rounded-sm" /> : `${exposicao?.ja_hedgeado_sc?.toLocaleString("pt-BR") || 0} sc`}
                        </div>
                    </CardContent>
                </Card>
                <Card className={`rounded-sm border-l-[3px] shadow-sm transition-all hover:shadow-md ${!exposicao || (exposicao.percentual_cobertura >= 20 && exposicao.percentual_cobertura <= 70) ? "border-l-primary/60" : exposicao.percentual_cobertura < 20 ? "border-l-red-500/60 border-red-200 bg-red-50 dark:bg-red-950/20" : "border-l-amber-500/60 border-amber-200 bg-amber-50 dark:bg-amber-950/20"}`}>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Exposição Líquida</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black tabular-nums">
                            {expLoading ? <Skeleton className="h-8 w-full rounded-sm" /> : `${exposicao?.exposicao_liquida_sc?.toLocaleString("pt-BR") || 0} sc`}
                        </div>
                        {exposicao && (
                            <p className="text-xs text-muted-foreground mt-1 flex items-center font-medium">
                                {exposicao.percentual_cobertura < 20 ? <TrendingDown className="size-3 mr-1 text-red-500" /> : <TrendingUp className="size-3 mr-1 text-emerald-500" />}
                                {exposicao.percentual_cobertura.toFixed(1)}% coberto
                            </p>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
