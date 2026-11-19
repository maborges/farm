"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    AlertTriangle,
    BarChart,
    Calculator,
    DollarSign,
    PieChart,
    Wallet,
} from "lucide-react";
import { formatArea, formatCurrency } from "@farm/utils";

import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

import { apiFetch } from "@/lib/api";
import {
    resolveFonteResumoCustos,
    resolveSafraSelecionadaId,
    sortBreakdownCustos,
    type CampanhasResponse,
    type ResumoCustos,
    type SafraKPI,
} from "./custos-view-model";

function CustosSkeleton() {
    return (
        <div className="space-y-6 p-6">
            <Skeleton className="h-10 w-64 rounded-sm" />
            <Skeleton className="h-32 w-full rounded-sm" />
            <div className="flex gap-4">
                <Skeleton className="h-96 w-1/2 rounded-sm" />
                <Skeleton className="h-96 w-1/2 rounded-sm" />
            </div>
        </div>
    );
}

function CustosFeedbackCard({
    title,
    description,
    isError = false,
}: {
    title: string;
    description: string;
    isError?: boolean;
}) {
    return (
        <Card className={isError ? "rounded-sm border-destructive/40 shadow-sm" : "rounded-sm shadow-sm"}>
            <CardContent className="flex items-start gap-3 p-6">
                {isError ? (
                    <AlertTriangle className="mt-0.5 size-5 shrink-0 text-destructive" />
                ) : (
                    <Wallet className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
                )}
                <div className="space-y-1">
                    <p className="text-sm font-medium">{title}</p>
                    <p className="text-sm text-muted-foreground">{description}</p>
                </div>
            </CardContent>
        </Card>
    );
}

function RelatorioCustosSection({
    relatorio,
    safras,
}: {
    relatorio: ResumoCustos;
    safras: readonly SafraKPI[];
}) {
    const breakdownOrdenado = useMemo(
        () => sortBreakdownCustos(relatorio.breakdown),
        [relatorio.breakdown],
    );

    const maxCustoHistorico = useMemo(
        () => Math.max(...safras.map((s) => s.custo_realizado_ha ?? 0), 1),
        [safras],
    );

    return (
        <>
            <div className="grid gap-4 md:grid-cols-2">
                <Card className="rounded-sm shadow-sm">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Custo Total (Realizado)
                        </CardTitle>
                        <DollarSign className="size-5 text-blue-500 opacity-40" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-blue-700 dark:text-blue-400">
                            {formatCurrency(relatorio.custo_total_realizado)}
                        </div>
                        <p className="mt-2 font-mono text-sm text-muted-foreground">
                            {formatCurrency(relatorio.custo_realizado_por_ha)} por hectare
                        </p>
                    </CardContent>
                </Card>

                <Card className="rounded-sm shadow-sm">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Orçamento Planejado
                        </CardTitle>
                        <Calculator className="size-5 text-amber-500 opacity-40" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-amber-700 dark:text-amber-400">
                            {relatorio.orcamento_previsto_total != null
                                ? formatCurrency(relatorio.orcamento_previsto_total)
                                : "—"}
                        </div>
                        {relatorio.desvio_orcamento_pct != null && (
                            <p
                                className={`mt-2 text-sm font-medium ${
                                    relatorio.desvio_orcamento_pct > 0
                                        ? "text-red-600 dark:text-red-400"
                                        : "text-emerald-600 dark:text-emerald-400"
                                }`}
                            >
                                {relatorio.desvio_orcamento_pct > 0 ? "+" : ""}
                                {relatorio.desvio_orcamento_pct}% do orçado
                            </p>
                        )}
                        <p className="mt-2 text-xs text-muted-foreground">
                            {relatorio.usou_fallback_orcamento
                                ? "Fonte: custo previsto da safra (fallback)"
                                : "Fonte: Orçamento de Safra"}
                        </p>
                    </CardContent>
                </Card>
            </div>

            <Card className="rounded-sm shadow-sm">
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-sm">
                        <PieChart className="size-4 text-muted-foreground" />
                        Distribuição por Categoria
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {breakdownOrdenado.length === 0 ? (
                        <p className="text-sm text-muted-foreground">Nenhum custo apropriado</p>
                    ) : (
                        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                            {breakdownOrdenado.map((c) => (
                                <div
                                    key={c.categoria}
                                    className="rounded-sm border bg-muted/40 p-3"
                                >
                                    <div className="mb-2 flex items-start justify-between">
                                        <span className="text-xs font-medium">{c.categoria}</span>
                                        <span className="text-xs text-muted-foreground">
                                            {c.percentual}%
                                        </span>
                                    </div>
                                    <div className="mb-2 h-1.5 overflow-hidden rounded-sm bg-muted">
                                        <div
                                            className="h-full bg-blue-600 dark:bg-blue-500"
                                            style={{ width: `${Math.min(Math.max(c.percentual, 0), 100)}%` }}
                                        />
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        <span className="font-mono">{formatCurrency(c.valor_total)}</span>
                                        <br />
                                        {formatCurrency(c.valor_por_ha)}/ha
                                    </p>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm">
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-sm">
                        <BarChart className="size-4 text-muted-foreground" />
                        Histórico de Custos
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {safras.length === 0 ? (
                        <p className="text-sm text-muted-foreground">Sem histórico</p>
                    ) : (
                        <div className="space-y-3">
                            {safras.map((s) => {
                                const realizado = s.custo_realizado_ha ?? 0;
                                const planejado = s.custo_previsto_ha ?? 0;
                                const larguraPct = Math.min((realizado / maxCustoHistorico) * 100, 100);
                                return (
                                    <div key={s.safra_id} className="text-sm">
                                        <div className="mb-1 flex justify-between">
                                            <span className="font-medium">
                                                {s.cultura} {s.ano_safra}
                                            </span>
                                            <span className="font-mono text-muted-foreground">
                                                {formatCurrency(realizado)}/ha
                                            </span>
                                        </div>
                                        <div className="h-2 overflow-hidden rounded-sm bg-muted">
                                            <div
                                                className={`h-full ${
                                                    realizado > planejado
                                                        ? "bg-red-500"
                                                        : "bg-emerald-500"
                                                }`}
                                                style={{ width: `${larguraPct}%` }}
                                            />
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>
        </>
    );
}

export function CustosClient() {
    const [selectedSafraId, setSelectedSafraId] = useState<string>("all");

    const {
        data: campanhas,
        isLoading: isLoadingCampanhas,
        isError: isErrorCampanhas,
    } = useQuery<CampanhasResponse>({
        queryKey: ["campanhas"],
        queryFn: () => apiFetch("/agricola/planejamento/campanhas"),
    });

    const safras = useMemo(() => campanhas?.safras ?? [], [campanhas?.safras]);
    const safraSelecionadaParam = useMemo(
        () => resolveSafraSelecionadaId(safras, selectedSafraId),
        [safras, selectedSafraId],
    );
    const safraAtualObj = useMemo(
        () => safras.find((s) => s.safra_id === safraSelecionadaParam),
        [safras, safraSelecionadaParam],
    );

    const {
        data: relatorio,
        isLoading: isLoadingRelatorio,
        isPending: isPendingRelatorio,
        isError: isErrorRelatorio,
    } = useQuery<ResumoCustos>({
        queryKey: ["custos", safraSelecionadaParam],
        queryFn: () => apiFetch(`/custos/safra/${safraSelecionadaParam}`),
        enabled: Boolean(safraSelecionadaParam),
    });

    const isAguardandoRelatorio =
        Boolean(safraSelecionadaParam) &&
        (isLoadingRelatorio || (isPendingRelatorio && !isErrorRelatorio));

    const fonteResumo = useMemo(() => resolveFonteResumoCustos(relatorio), [relatorio]);

    if (isLoadingCampanhas || isAguardandoRelatorio) {
        return <CustosSkeleton />;
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Custeio Agrícola"
                description="Custo de produção por safra com orçamento, apropriação econômica e histórico."
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Custeio Agrícola" }]}
                icon={<Wallet className="text-primary" size={22} />}
            />

            {isErrorCampanhas ? (
                <CustosFeedbackCard
                    isError
                    title="Não foi possível carregar as safras"
                    description="Verifique sua conexão ou tente recarregar a página para consultar o custeio agrícola."
                />
            ) : safras.length === 0 ? (
                <CustosFeedbackCard
                    title="Nenhuma safra cadastrada"
                    description="Cadastre uma safra no Planejamento Agrícola para visualizar o resumo de custos, orçamento e histórico."
                />
            ) : (
                <>
                    <Card className="rounded-sm shadow-sm">
                        <CardContent className="p-4">
                            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                                <div className="flex flex-col gap-1">
                                    <span className="text-xs uppercase tracking-wider text-muted-foreground">
                                        Qual Safra Analisar?
                                    </span>
                                    {safraAtualObj && (
                                        <p className="text-sm text-muted-foreground">
                                            {safraAtualObj.cultura} • Safra {safraAtualObj.ano_safra} •{" "}
                                            {formatArea(safraAtualObj.area_ha)}
                                        </p>
                                    )}
                                </div>
                                <Select value={selectedSafraId} onValueChange={setSelectedSafraId}>
                                    <SelectTrigger className="w-full rounded-sm md:w-[240px]">
                                        <SelectValue placeholder="Selecionar safra..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">Automático (Mais recente)</SelectItem>
                                        {safras.map((s) => (
                                            <SelectItem key={s.safra_id} value={s.safra_id}>
                                                {s.cultura} — {s.ano_safra}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            {fonteResumo && (
                                <div className="mt-4 flex flex-wrap items-center gap-2">
                                    <span className="text-xs uppercase tracking-wider text-muted-foreground">
                                        Fonte do resumo
                                    </span>
                                    <Badge variant={fonteResumo.variant}>{fonteResumo.label}</Badge>
                                    {fonteResumo.showFallbackHint && (
                                        <span className="text-xs text-muted-foreground">
                                            Não houve CostAllocation consolidada para esta safra; o
                                            resumo usa custo operacional como contingência.
                                        </span>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {isErrorRelatorio ? (
                        <CustosFeedbackCard
                            isError
                            title="Não foi possível carregar os custos da safra"
                            description="Ocorreu uma falha ao consultar a apropriação de custos desta safra. Tente novamente ou selecione outra safra."
                        />
                    ) : (
                        relatorio && <RelatorioCustosSection relatorio={relatorio} safras={safras} />
                    )}
                </>
            )}
        </div>
    );
}
