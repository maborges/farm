"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    TrendingUp, Target, Users,
    Calendar, MousePointerClick,
    Activity, Tractor, BarChart3
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { formatCurrency } from "@/lib/utils";
import {
    Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer,
    BarChart, Line,
    ComposedChart, Legend
} from "recharts";

interface BIStats {
    churn_rate: number;
    ltv: number;
    cac_simulado: number;
    payback_meses: number;
    coortes: Array<{ periodo: string; tamanho: number; retencao: number }>;
    distribuicao_receita: Array<{ plano: string; clientes: number; receita: number }>;
    engajamento: {
        usuarios_ativos_dia: number;
        operacoes_por_dia: number;
        hectares_gerenciados: number;
    };
    periodo_analise: string;
}

/** Tooltip customizado reutilizável para os gráficos Recharts. */
const ChartTooltip = ({ active, payload, label, currency = false }: {
    active?: boolean;
    payload?: Array<{ color?: string; fill?: string; name: string; value: number; unit?: string }>;
    label?: string;
    currency?: boolean;
}) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-background/95 backdrop-blur-md border border-border p-3 rounded-sm shadow-2xl">
                <p className="text-[10px] font-bold text-muted-foreground uppercase mb-2">{label}</p>
                {payload.map((entry, index) => (
                    <div key={index} className="flex items-center gap-3 py-1">
                        <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color ?? entry.fill }} />
                        <span className="text-xs font-medium text-foreground">{entry.name}:</span>
                        <span className="text-xs font-black ml-auto">
                            {currency ? formatCurrency(entry.value) : entry.value.toLocaleString()}
                            {entry.unit ? ` ${entry.unit}` : ""}
                        </span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

export default function BackofficeBIPage() {
    const { data: bi, isLoading } = useQuery<BIStats>({
        queryKey: ["backoffice", "bi"],
        queryFn: () => apiFetch("/backoffice/bi/stats"),
    });

    if (isLoading) {
        return (
            <div className="p-8 space-y-8 w-full max-w-full">
                <Skeleton className="h-16 w-full" />
                <div className="grid gap-4 md:grid-cols-4">
                    {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)}
                </div>
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            {/* SVG Gradients para Recharts */}
            <svg style={{ height: 0, width: 0, position: "absolute" }}>
                <defs>
                    <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.8} />
                        <stop offset="100%" stopColor="#10b981" stopOpacity={0.4} />
                    </linearGradient>
                    <linearGradient id="cohortGradient" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.8} />
                        <stop offset="100%" stopColor="#60a5fa" stopOpacity={0.4} />
                    </linearGradient>
                </defs>
            </svg>

            <PageHeader
                title="Dashboard de BI"
                description="Análise profunda de unit economics e retenção do SaaS."
                icon={<BarChart3 className="text-primary" size={22} />}
                actions={
                    <div className="flex items-center gap-3">
                        <Badge variant="secondary">Alpha</Badge>
                        {bi?.periodo_analise && (
                            <div className="bg-muted/50 px-4 py-2 rounded-sm flex items-center gap-2 text-xs font-bold uppercase tracking-widest border border-border/50">
                                <Calendar size={13} className="text-primary" />
                                <span>Período: {bi.periodo_analise}</span>
                            </div>
                        )}
                    </div>
                }
            />

            {/* ── SaaS KPIs ── */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">
                            LTV (Lifetime Value)
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-primary">{formatCurrency(bi?.ltv ?? 0)}</div>
                        <p className="text-[10px] mt-2 text-muted-foreground">Estimativa de receita total por cliente</p>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">
                            Churn Rate
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-primary">{bi?.churn_rate}%</div>
                        <p className="text-[10px] mt-2 text-muted-foreground">Taxa de cancelamento mensal</p>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">
                            CAC (Cust. Acquisition)
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-primary">{formatCurrency(bi?.cac_simulado ?? 0)}</div>
                        <p className="text-[10px] mt-2 text-muted-foreground">Custo médio para adquirir um cliente</p>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">
                            Payback
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-primary">{bi?.payback_meses} Meses</div>
                        <p className="text-[10px] mt-2 text-muted-foreground">Tempo para recuperar o CAC</p>
                    </CardContent>
                </Card>
            </div>

            {/* ── Gráficos ── */}
            <div className="grid gap-6 md:grid-cols-12">
                <Card className="md:col-span-7">
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                            <Target className="size-4 text-primary" /> Receita x Volume por Plano
                        </CardTitle>
                        <CardDescription>Qual plano traz maior rentabilidade relativa.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[350px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart data={bi?.distribuicao_receita} barGap={12}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                                    <XAxis dataKey="plano" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                                    <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{ fontSize: 10 }} tickFormatter={(v) => `R$ ${v / 1000}k`} />
                                    <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{ fontSize: 10 }} />
                                    <Tooltip content={<ChartTooltip currency />} cursor={{ fill: "rgba(0,0,0,0.02)" }} />
                                    <Legend iconType="circle" />
                                    <Bar yAxisId="left" dataKey="receita" name="Receita Total" fill="url(#revenueGradient)" radius={[6, 6, 0, 0]} barSize={40} />
                                    <Line yAxisId="right" type="monotone" dataKey="clientes" name="Clientes Ativos" stroke="#ef4444" strokeWidth={4} dot={{ r: 5, fill: "#ef4444", strokeWidth: 2, stroke: "#fff" }} activeDot={{ r: 7 }} />
                                </ComposedChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>

                <Card className="md:col-span-5">
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                            <Activity className="size-4 text-blue-500" /> Retention Coortes (M1)
                        </CardTitle>
                        <CardDescription>Percentual de clientes retidos após 30 dias.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[350px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={bi?.coortes} layout="vertical" barSize={24}>
                                    <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.1} />
                                    <XAxis type="number" hide />
                                    <YAxis dataKey="periodo" type="category" axisLine={false} tickLine={false} width={80} tick={{ fontSize: 11 }} />
                                    <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(0,0,0,0.02)" }} />
                                    <Bar dataKey="retencao" name="Retenção" fill="url(#cohortGradient)" radius={[0, 6, 6, 0]} label={{ position: "right", formatter: ((v: unknown) => `${v}%`) as import("recharts/types/component/Label").LabelFormatter, fontSize: 10, fontWeight: "bold" }} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* ── Engagement ── */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="pt-6 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-sm bg-green-500/10 flex items-center justify-center text-green-600 shrink-0">
                            <Users size={24} />
                        </div>
                        <div>
                            <p className="text-2xl font-black">{bi?.engajamento.usuarios_ativos_dia}</p>
                            <p className="text-[10px] uppercase font-bold text-muted-foreground">DAU (Usuários Ativos Dia)</p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="pt-6 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-sm bg-blue-500/10 flex items-center justify-center text-blue-600 shrink-0">
                            <MousePointerClick size={24} />
                        </div>
                        <div>
                            <p className="text-2xl font-black">{bi?.engajamento.operacoes_por_dia}</p>
                            <p className="text-[10px] uppercase font-bold text-muted-foreground">Operações Agrícolas / Dia</p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="pt-6 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-sm bg-amber-500/10 flex items-center justify-center text-amber-600 shrink-0">
                            <Tractor size={24} />
                        </div>
                        <div>
                            <p className="text-2xl font-black">{bi?.engajamento.hectares_gerenciados.toLocaleString()}</p>
                            <p className="text-[10px] uppercase font-bold text-muted-foreground">Hectares Gerenciados</p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
