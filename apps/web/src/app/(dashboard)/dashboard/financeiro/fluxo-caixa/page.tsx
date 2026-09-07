"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { TrendingUp, TrendingDown, DollarSign, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface FluxoCaixaPeriodo {
    periodo: string;
    receitas_realizadas: number;
    despesas_realizadas: number;
    saldo_realizado: number;
    receitas_previstas: number;
    despesas_previstas: number;
    saldo_previsto: number;
    saldo_acumulado: number;
}

interface FluxoCaixaTotais {
    total_receitas_realizadas: number;
    total_despesas_realizadas: number;
    total_saldo_realizado: number;
    total_receitas_previstas: number;
    total_despesas_previstas: number;
    total_saldo_previsto: number;
}

interface FluxoCaixa {
    data_inicio: string;
    data_fim: string;
    periodos: FluxoCaixaPeriodo[];
    totais: FluxoCaixaTotais;
}

function toLocaleBRL(v: number | undefined | null) {
    if (v === undefined || v === null) return "R$ 0,00";
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function FluxoCaixaPage() {
    const hoje = new Date();
    const [inicio, setInicio] = useState(new Date(hoje.getFullYear(), hoje.getMonth(), 1).toISOString().slice(0, 10));
    const [fim, setFim] = useState(new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0).toISOString().slice(0, 10));

    const { data: fluxo, isLoading } = useQuery<FluxoCaixa>({
        queryKey: ["financeiro", "fluxo-caixa", inicio, fim],
        queryFn: () => apiFetch(`/relatorios/fluxo-caixa?data_inicio=${inicio}&data_fim=${fim}`),
    });

    const kpis = fluxo ? [
        { label: "Receitas Real.", value: fluxo.totais.total_receitas_realizadas, borderColor: "border-l-emerald-500/80", titleColor: "text-emerald-700/70", valueColor: "text-emerald-700" },
        { label: "Despesas Real.", value: fluxo.totais.total_despesas_realizadas, borderColor: "border-l-red-500/80", titleColor: "text-red-700/70", valueColor: "text-red-700" },
        { 
            label: "Saldo do Período", 
            value: fluxo.totais.total_saldo_realizado, 
            borderColor: fluxo.totais.total_saldo_realizado >= 0 ? "border-l-blue-500/80" : "border-l-red-500/80", 
            titleColor: fluxo.totais.total_saldo_realizado >= 0 ? "text-blue-700/70" : "text-red-700/70", 
            valueColor: fluxo.totais.total_saldo_realizado >= 0 ? "text-blue-700" : "text-red-700" 
        },
        { label: "Saldo Previsto", value: fluxo.totais.total_saldo_previsto, borderColor: "border-l-amber-500/80", titleColor: "text-amber-800/70", valueColor: "text-amber-700" },
    ] : [];

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Fluxo de Caixa"
                description="Entradas, saídas e saldo por período"
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Fluxo de Caixa" },
                ]}
                icon={<TrendingUp className="text-primary" size={22} />}
                actions={
                    <div className="flex items-end gap-2">
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-bold text-muted-foreground uppercase">De</label>
                            <Input type="date" value={inicio} onChange={e => setInicio(e.target.value)} className="w-[150px]" />
                        </div>
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-bold text-muted-foreground uppercase">Até</label>
                            <Input type="date" value={fim} onChange={e => setFim(e.target.value)} className="w-[150px]" />
                        </div>
                    </div>
                }
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {isLoading
                    ? Array.from({ length: 4 }).map((_, i) => (
                        <Card key={i}>
                            <CardHeader className="pb-2">
                                <Skeleton className="h-3 w-24" />
                            </CardHeader>
                            <CardContent>
                                <Skeleton className="h-8 w-28" />
                            </CardContent>
                        </Card>
                    ))
                    : kpis.map(k => (
                        <Card key={k.label} className={`border-l-4 ${k.borderColor}`}>
                            <CardHeader className="pb-2">
                                <CardTitle className={`text-[10px] font-black uppercase tracking-[0.24em] ${k.titleColor}`}>
                                    {k.label}
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className={`text-3xl font-black ${k.valueColor}`}>
                                    {toLocaleBRL(k.value)}
                                </div>
                            </CardContent>
                        </Card>
                    ))
                }
            </div>

            {fluxo?.periodos && fluxo.periodos.length > 0 && (
                <Card>
                    <CardHeader className="flex flex-col gap-4 border-b border-border pb-4">
                        <div className="space-y-1">
                            <CardTitle className="text-sm font-semibold flex items-center gap-2">
                                <Calendar className="size-4 text-muted-foreground" />
                                Detalhamento Mensal
                            </CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-muted-foreground text-xs">
                                        <th className="text-left py-2 font-medium">Mês</th>
                                        <th className="text-right py-2 font-medium text-emerald-700/70">Entradas</th>
                                        <th className="text-right py-2 font-medium text-red-700/70">Saídas</th>
                                        <th className="text-right py-2 font-medium">Saldo</th>
                                        <th className="text-right py-2 font-medium">Acumulado</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {fluxo.periodos.map(m => (
                                        <tr key={m.periodo} className="border-b border-border/50 last:border-0 hover:bg-muted/30">
                                            <td className="py-2.5 font-medium">{new Date(m.periodo).toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</td>
                                            <td className="text-right py-2.5 text-emerald-700 font-medium">{toLocaleBRL(m.receitas_realizadas)}</td>
                                            <td className="text-right py-2.5 text-red-700 font-medium">{toLocaleBRL(m.despesas_realizadas)}</td>
                                            <td className={`text-right py-2.5 font-bold ${m.saldo_realizado >= 0 ? "text-blue-700" : "text-red-700"}`}>{toLocaleBRL(m.saldo_realizado)}</td>
                                            <td className={`text-right py-2.5 font-black ${m.saldo_acumulado >= 0 ? "text-blue-800" : "text-red-800"}`}>{toLocaleBRL(m.saldo_acumulado)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>
            )}

            {!isLoading && !fluxo && (
                <div className="text-center py-12 text-sm text-muted-foreground">Nenhum dado para o período selecionado.</div>
            )}
        </div>
    );
}
