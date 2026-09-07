"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { formatCurrency } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Calculator } from "lucide-react";

export interface CentroCustoCategoria {
    plano_conta_nome: string;
    categoria_rfb: string | null;
    total_rateado: number;
    quantidade: number;
}

export interface CentroCusto {
    safra_id: string | null;
    safra_nome: string | null;
    talhao_id: string | null;
    talhao_nome: string | null;
    total_rateado: number;
    por_categoria: CentroCustoCategoria[];
}

export interface CentroCustoResponse {
    data_inicio: string;
    data_fim: string;
    unidade_produtiva_id: string | null;
    total_geral: number;
    centros: CentroCusto[];
}

interface CustosClientProps {
    initialCustos: CentroCustoResponse | null;
    initialDataInicio: string;
    initialDataFim: string;
    initialActiveFazendaId?: string;
}

export function CustosClient({ initialCustos, initialDataInicio, initialDataFim, initialActiveFazendaId }: CustosClientProps) {
    const { activeFazendaId, isVisaoGrupo, token, _hasHydrated } = useAppStore();
    const [dataInicio, setDataInicio] = useState(initialDataInicio);
    const [dataFim, setDataFim] = useState(initialDataFim);

    const canLoad = _hasHydrated && !!token && (isVisaoGrupo || !!activeFazendaId);
    const fqParam = activeFazendaId && !isVisaoGrupo ? `&unidade_produtiva_id=${activeFazendaId}` : "";

    const { data: custos, isLoading } = useQuery<CentroCustoResponse>({
        queryKey: ["financeiro", "custos-abc", activeFazendaId, dataInicio, dataFim],
        queryFn: () => apiFetch(`/financeiro/custos/centro-custos?data_inicio=${dataInicio}&data_fim=${dataFim}${fqParam}`),
        enabled: canLoad,
        initialData: activeFazendaId === initialActiveFazendaId && dataInicio === initialDataInicio && dataFim === initialDataFim
            ? initialCustos ?? undefined
            : undefined,
    });

    const centros = custos?.centros ?? [];
    const totalGeral = custos?.total_geral ?? 0;

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Custos ABC"
                description="Centro de custos por safra e talhão com rateio financeiro consolidado."
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Custos ABC" },
                ]}
                icon={<Calculator className="text-primary" size={22} />}
                actions={
                    <div className="flex items-end gap-2">
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-bold text-muted-foreground uppercase">De</label>
                            <Input
                                type="date"
                                value={dataInicio}
                                onChange={(e) => setDataInicio(e.target.value)}
                                className="w-[150px]"
                            />
                        </div>
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-bold text-muted-foreground uppercase">Até</label>
                            <Input
                                type="date"
                                value={dataFim}
                                onChange={(e) => setDataFim(e.target.value)}
                                className="w-[150px]"
                            />
                        </div>
                    </div>
                }
            />

            <div className="grid gap-4 md:grid-cols-3">
                <Card className="border-l-4 border-l-emerald-500/80">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-emerald-700/70 tracking-[0.24em]">Total Rateado</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? <Skeleton className="h-8 w-28" /> : <div className="text-3xl font-black text-emerald-700">{formatCurrency(totalGeral)}</div>}
                    </CardContent>
                </Card>

                <Card className="border-l-4 border-l-blue-500/80">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-blue-700/70 tracking-[0.24em]">Centros Ativos</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? <Skeleton className="h-8 w-20" /> : <div className="text-3xl font-black text-blue-700">{centros.length}</div>}
                    </CardContent>
                </Card>

                <Card className="border-l-4 border-l-amber-500/80">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-amber-800/70 tracking-[0.24em]">Período</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-sm font-medium text-foreground">
                            {dataInicio} até {dataFim}
                        </div>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
                {isLoading && (
                    <Card className="lg:col-span-3">
                        <CardContent className="py-10 text-center text-sm text-muted-foreground">
                            Carregando centros de custo...
                        </CardContent>
                    </Card>
                )}

                {!isLoading && centros.length === 0 && (
                    <Card className="lg:col-span-3">
                        <CardContent className="py-10 text-center text-sm text-muted-foreground">
                            Nenhum rateio encontrado para o período selecionado.
                        </CardContent>
                    </Card>
                )}

                {!isLoading && centros.map((centro, idx) => {
                    const share = totalGeral > 0 ? (centro.total_rateado / totalGeral) * 100 : 0;
                    return (
                        <Card key={`${centro.safra_id || "sem-safra"}-${centro.talhao_id || idx}`} className="lg:col-span-3 border border-border/70">
                            <CardHeader className="pb-3">
                                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                                    <div>
                                        <CardTitle className="text-base">
                                            {centro.safra_nome || "Sem safra"}{" "}
                                            <span className="text-muted-foreground font-normal">
                                                {centro.talhao_nome ? `• ${centro.talhao_nome}` : ""}
                                            </span>
                                        </CardTitle>
                                        <CardDescription className="mt-1">
                                            Centro de custo consolidado
                                        </CardDescription>
                                    </div>
                                    <div className="flex flex-col items-start md:items-end gap-1">
                                        <div className="text-2xl font-black text-foreground">{formatCurrency(centro.total_rateado)}</div>
                                        <Badge variant="outline" className="rounded-sm">
                                            {share.toFixed(1)}% do total
                                        </Badge>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid gap-3 md:grid-cols-3">
                                    {centro.por_categoria.map((cat) => (
                                        <div key={`${cat.plano_conta_nome}-${cat.total_rateado}`} className="rounded-sm border border-border/70 p-3">
                                            <div className="flex items-center justify-between gap-3">
                                                <div>
                                                    <div className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
                                                        {cat.categoria_rfb || "Sem categoria"}
                                                    </div>
                                                    <div className="mt-1 font-medium">{cat.plano_conta_nome}</div>
                                                </div>
                                                <Badge variant="secondary" className="rounded-sm">
                                                    x{cat.quantidade}
                                                </Badge>
                                            </div>
                                            <div className="mt-3 text-lg font-black">{formatCurrency(cat.total_rateado)}</div>
                                        </div>
                                    ))}
                                </div>
                                <div className="flex items-center justify-between rounded-sm bg-muted/40 px-3 py-2 text-sm">
                                    <span className="text-muted-foreground">Total por centro de custo</span>
                                    <span className="font-bold">{formatCurrency(centro.total_rateado)}</span>
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
}
