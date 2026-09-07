"use client";

import { useQuery } from "@tanstack/react-query";
import {
    ResponsiveContainer,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
} from "recharts";
import { TrendingDown, TrendingUp } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface SerieTemporal {
    periodo: string;
    total: number;
}

function fmt(value: number) {
    return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function fmtPeriodo(periodo: string) {
    const [ano, mes] = periodo.split("-");
    const meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
    return `${meses[parseInt(mes) - 1]}/${ano.slice(2)}`;
}

interface Props {
    safraId: string;
}

export function CostTimelineChart({ safraId }: Props) {
    const { data, isLoading } = useQuery<SerieTemporal[]>({
        queryKey: ["lancamentos-serie-temporal", safraId],
        queryFn: () => apiFetch(`/financeiro/lancamentos/serie-temporal?safra_id=${safraId}`),
        staleTime: 30_000,
        enabled: !!safraId,
    });

    if (isLoading || !data || data.length === 0) return null;

    const chartData = data.map((d) => ({ ...d, label: fmtPeriodo(d.periodo) }));

    // Variação entre os dois últimos períodos
    let variacao: { pct: number; aumento: boolean } | null = null;
    if (data.length >= 2) {
        const ultimo = data[data.length - 1].total;
        const penultimo = data[data.length - 2].total;
        if (penultimo > 0) {
            const pct = ((ultimo - penultimo) / penultimo) * 100;
            variacao = { pct: Math.abs(pct), aumento: pct > 0 };
        }
    }

    return (
        <section className="rounded-sm border border-border bg-card p-5 shadow-sm space-y-4">
            <div className="flex items-start justify-between gap-4">
                <div className="space-y-0.5">
                    <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                        Evolução de Custos Mensais
                    </p>
                    {variacao && (
                        <p className={`text-sm font-semibold flex items-center gap-1.5 ${variacao.aumento ? "text-destructive" : "text-emerald-700 dark:text-emerald-400"}`}>
                            {variacao.aumento
                                ? <TrendingUp className="size-4" />
                                : <TrendingDown className="size-4" />}
                            Custos {variacao.aumento ? "aumentaram" : "reduziram"} {variacao.pct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% no último mês
                        </p>
                    )}
                </div>
            </div>

            <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-border" />
                    <XAxis
                        dataKey="label"
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        className="text-muted-foreground"
                    />
                    <YAxis
                        tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`}
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        width={52}
                        className="text-muted-foreground"
                    />
                    <Tooltip
                        formatter={(value: number) => [fmt(value), "Custos"]}
                        labelClassName="font-semibold"
                        contentStyle={{ fontSize: 12, borderRadius: 6 }}
                    />
                    <Bar dataKey="total" radius={[4, 4, 0, 0]} className="fill-primary" fill="hsl(var(--primary))" />
                </BarChart>
            </ResponsiveContainer>
        </section>
    );
}
