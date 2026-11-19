"use client";

import { useMemo } from "react";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { HistoricoIth } from "@/lib/pecuaria/clima-api";

interface HistoricoIthChartProps {
    dados: HistoricoIth[];
}

export function HistoricoIthChart({ dados }: HistoricoIthChartProps) {
    const chartData = useMemo(() => dados.map((item) => ({
        ...item,
        labelData: format(parseISO(item.data), "dd/MM", { locale: ptBR }),
    })), [dados]);

    return (
        <Card className="rounded-sm border-border/40 shadow-sm bg-background/50 backdrop-blur-sm transition-all hover:shadow-md">
            <CardHeader className="px-6 pt-6 pb-2">
                <CardTitle className="text-lg font-bold tracking-tight">Histórico de Risco (ITH)</CardTitle>
                <CardDescription className="text-sm">Variação do índice de conforto térmico nos últimos 7 dias com base na temperatura e umidade.</CardDescription>
            </CardHeader>
            <CardContent>
                {chartData.length === 0 ? (
                    <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">Sem histórico climático disponível.</div>
                ) : (
                    <div className="h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData} margin={{ top: 12, right: 12, bottom: 8, left: -18 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                                <XAxis dataKey="labelData" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                                <YAxis domain={[60, 90]} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                                <Tooltip formatter={(value: number | undefined) => [value == null ? "Sem cálculo" : value.toFixed(1), "ITH"]} />
                                <Line type="monotone" dataKey="ith" name="ITH" stroke="#ef4444" strokeWidth={3} connectNulls={false} dot={{ r: 3 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
