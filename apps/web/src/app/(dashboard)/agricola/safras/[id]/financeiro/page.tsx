"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FinanceiroKPIs } from "@/components/agricola/financeiro-kpis";
import { FinanceiroChart } from "@/components/agricola/financeiro-chart";
import { TransacaoTimeline } from "@/components/agricola/transacao-timeline";
import { LancamentosOrigemCard } from "@/components/financeiro/lancamentos-origem-card";
import { AgricolaDreKpis, type AgricolaDreKpisData } from "@/components/agricola/dre-kpis";
import { useAppStore } from "@/lib/stores/app-store";
import { getSafraLabel } from "@/lib/safra-label";
import { AlertCircle, DollarSign } from "lucide-react";

interface SafraResumoFinanceiro {
    id: string;
    cultura: string | null;
    ano_safra: string;
    status: string;
    financeiro: {
        total_operacoes: number;
        custo_operacoes_total: number;
        custo_por_ha: number;
        total_romaneios: number;
        total_sacas: number;
        produtividade_sc_ha: number | null;
        despesa_total: number;
        receita_total: number;
        lucro_bruto: number;
        roi_pct: number | null;
    };
}

interface DREAgricolaFinanceiroResumo {
    kpis?: AgricolaDreKpisData;
    warnings: Array<{
        codigo: string;
        severidade: string;
    }>;
}

export default function SafraFinanceiroPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const token = useAppStore((s) => s.token);
    const hasHydrated = useAppStore((s) => s._hasHydrated);
    const isReady = hasHydrated && !!token;

    const { data: safra, isLoading } = useQuery<SafraResumoFinanceiro>({
        queryKey: ["safra-financeiro", id],
        queryFn: () => apiFetch(`/agricola/dashboard/safras/${id}/resumo-financeiro`),
        enabled: isReady,
        retry: false,
    });

    const {
        data: dre,
        isLoading: isLoadingDre,
        isError: isErrorDre,
    } = useQuery<DREAgricolaFinanceiroResumo>({
        queryKey: ["safra-financeiro", "dre-v1", id],
        queryFn: () => apiFetch("/agricola/dre/v1", { params: { safra_id: id } }),
        enabled: isReady,
        retry: false,
    });

    if (!isReady || isLoading || !safra) {
        return (
            <div className="space-y-6 p-6">
                <Skeleton className="h-10 w-72" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }
    const safraLabel = getSafraLabel(safra);

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title={`Financeiro — ${safraLabel}`}
                icon={<DollarSign className="text-emerald-600" size={22} />}
                description="Resumo Financeiro Completo"
            />

            <section className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="rounded-sm">Fonte oficial</Badge>
                    <span className="text-xs text-muted-foreground">DRE agrícola v1</span>
                </div>

                {isLoadingDre ? (
                    <Card className="rounded-sm shadow-sm">
                        <CardContent className="grid gap-3 p-4">
                            <Skeleton className="h-5 w-64" />
                            <Skeleton className="h-24 w-full" />
                            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                                <Skeleton className="h-24 w-full rounded-lg" />
                                <Skeleton className="h-24 w-full rounded-lg" />
                                <Skeleton className="h-24 w-full rounded-lg" />
                                <Skeleton className="h-24 w-full rounded-lg" />
                            </div>
                        </CardContent>
                    </Card>
                ) : isErrorDre ? (
                    <Alert variant="destructive" className="rounded-sm">
                        <AlertCircle className="size-4" />
                        <AlertTitle>DRE agrícola v1 indisponível</AlertTitle>
                        <AlertDescription>
                            A página financeira segue disponível com o legado como referência secundária, mas os KPIs oficiais da DRE v1 não puderam ser carregados.
                        </AlertDescription>
                    </Alert>
                ) : dre?.kpis ? (
                    <AgricolaDreKpis kpis={dre.kpis} />
                ) : null}
            </section>

            <section className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                    <Badge variant="outline" className="rounded-sm">Referência secundária</Badge>
                    <span className="text-xs text-muted-foreground">Indicadores financeiros/operacionais legados</span>
                </div>
                <FinanceiroKPIs financeiro={safra.financeiro} />
            </section>

            {/* Gráfico Custo vs Receita */}
            <Card className="shadow-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Custo vs Receita</CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                    <FinanceiroChart financeiro={safra.financeiro} />
                </CardContent>
            </Card>

            {/* Timeline de Transações */}
            <Card className="shadow-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Rastreabilidade Financeira Legada</CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                    <TransacaoTimeline safraId={id} />
                </CardContent>
            </Card>

            {/* Lançamentos por origem */}
            <Card className="shadow-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Custos — Origem dos Lançamentos Legados</CardTitle>
                </CardHeader>
                <CardContent className="pt-2">
                    <LancamentosOrigemCard safraId={id} />
                </CardContent>
            </Card>
        </div>
    );
}
