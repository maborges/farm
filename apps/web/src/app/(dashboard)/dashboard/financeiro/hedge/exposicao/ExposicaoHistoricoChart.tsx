"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { ExposicaoHistoricoItem } from "../types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
    ComposedChart,
    Line,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend
} from "recharts";
import { Lock, TrendingUp } from "lucide-react";
import { format, parseISO } from "date-fns";

function fmtValue(val: number): string {
    return val.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}

type TooltipPoint = {
    payload?: ExposicaoHistoricoItem;
};

type CustomTooltipProps = {
    active?: boolean;
    payload?: TooltipPoint[];
};

type QueryErrorWithStatus = Error & {
    status?: number;
};

function hasStatus(value: unknown): value is QueryErrorWithStatus {
    return typeof value === "object" && value !== null && "status" in value;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        if (!data) return null;
        const dataFormatada = format(parseISO(data.data_referencia), "dd/MM/yyyy");
        return (
            <div className="bg-card border shadow-md rounded-sm p-3 text-sm">
                <p className="font-semibold mb-2">{dataFormatada}</p>
                <div className="space-y-1">
                    <p className="text-muted-foreground">
                        Exposição Física: <span className="font-medium text-foreground">{fmtValue(data.exposicao_fisica_sc)} sc</span>
                    </p>
                    <p className="text-emerald-600">
                        Proteção: <span className="font-medium">{fmtValue(data.protecao_financeira_sc)} sc</span>
                    </p>
                    <p className="text-red-500">
                        Exposição Aberta: <span className="font-medium">{fmtValue(data.exposicao_aberta_sc)} sc</span>
                    </p>
                    <p className="text-amber-600 mt-2 font-semibold border-t pt-1">
                        Hedge Ratio: {(data.hedge_ratio * 100).toFixed(1)}%
                    </p>
                </div>
            </div>
        );
    }
    return null;
}

export function ExposicaoHistoricoChart({
    safraId,
    commodityId,
}: {
    safraId?: string | null;
    commodityId?: string | null;
}) {
    const { data, isLoading, error } = useQuery<ExposicaoHistoricoItem[]>({
        queryKey: ["financeiro", "hedge", "exposicao", "historico", safraId, commodityId],
        queryFn: () => {
            const params = new URLSearchParams();
            if (safraId) params.append("safra_id", safraId);
            if (commodityId) params.append("commodity_id", commodityId);
            return apiFetch(`/financeiro/hedge/exposicao/historico?${params.toString()}`);
        },
        staleTime: 5 * 60 * 1000,
        retry: (failureCount, err: unknown) => {
            if (hasStatus(err) && err.status === 403) return false;
            return failureCount < 2;
        }
    });

    const isBlocked = hasStatus(error) && error.status === 403;

    return (
        <Card className="rounded-sm">
            <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Evolução Histórica da Exposição e Proteção
                </CardTitle>
                <CardDescription className="text-xs">
                    Histórico consolidado com base nos fechamentos diários (MtM) e posição física atual.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {isBlocked ? (
                    <div className="flex flex-col items-center justify-center py-12 px-4 text-center border rounded-sm bg-muted/20">
                        <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
                            <Lock className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <h4 className="text-sm font-semibold mb-1">Recurso Exclusivo ENTERPRISE</h4>
                        <p className="text-xs text-muted-foreground max-w-sm mb-4">
                            Acompanhe o histórico temporal do Hedge Ratio e da Exposição Aberta com o plano Enterprise.
                        </p>
                    </div>
                ) : isLoading ? (
                    <div className="h-[350px] w-full flex items-center justify-center">
                        <Skeleton className="h-full w-full rounded-sm" />
                    </div>
                ) : !data || data.length === 0 ? (
                    <div className="h-[350px] flex items-center justify-center text-sm text-muted-foreground border rounded-sm border-dashed">
                        Nenhum dado histórico registrado para o período ou filtros selecionados.
                    </div>
                ) : (
                    <div className="h-[350px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart
                                data={data}
                                margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted))" />
                                <XAxis 
                                    dataKey="data_referencia" 
                                    tickFormatter={(val) => format(parseISO(val), "dd/MM")}
                                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                                    tickMargin={10}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <YAxis 
                                    tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                                    axisLine={false}
                                    tickLine={false}
                                    width={50}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Legend wrapperStyle={{ fontSize: "12px" }} />
                                
                                <Area 
                                    type="monotone" 
                                    dataKey="exposicao_fisica_sc" 
                                    name="Exposição Física" 
                                    fill="hsl(var(--muted))" 
                                    stroke="hsl(var(--muted-foreground))" 
                                    fillOpacity={0.2}
                                />
                                <Area 
                                    type="monotone" 
                                    dataKey="protecao_financeira_sc" 
                                    name="Proteção (Hedge)" 
                                    fill="#10b981" 
                                    stroke="#059669" 
                                    fillOpacity={0.15}
                                />
                                <Line 
                                    type="monotone" 
                                    dataKey="exposicao_aberta_sc" 
                                    name="Exposição Aberta" 
                                    stroke="#ef4444" 
                                    strokeWidth={2}
                                    dot={false}
                                    activeDot={{ r: 4 }}
                                />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
