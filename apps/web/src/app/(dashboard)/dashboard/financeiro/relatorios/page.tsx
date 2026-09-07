"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
    FileText, Download, Activity,
    ArrowUpCircle, ArrowDownCircle, Landmark,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Legend,
    PieChart, Pie, Cell,
} from "recharts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface FluxoPeriodo {
    periodo: string;
    receitas_realizadas: number;
    despesas_realizadas: number;
    saldo_realizado: number;
    saldo_acumulado: number;
}

interface FluxoData {
    periodos: FluxoPeriodo[];
    totais: {
        total_receitas_realizadas: number;
        total_despesas_realizadas: number;
        total_saldo_realizado: number;
    };
}

interface DREData {
    receita_bruta: number;
    total_custeio: number;
    total_investimento: number;
    total_nao_dedutivel: number;
    resultado_atividade_rural: number;
    outras_receitas: number;
    resultado_liquido: number;
}

interface TopCategoria {
    plano_conta_nome: string;
    total: number;
}

interface DashData {
    top_despesas: TopCategoria[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function mesLabel(periodoIso: string) {
    const d = new Date(periodoIso + "T00:00:00");
    return d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
}

const PIE_COLORS = ["#ef4444", "#3b82f6", "#f59e0b", "#8b5cf6", "#10b981"];

const ChartTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-background/95 backdrop-blur-md border border-border p-3 rounded-sm shadow-2xl">
            <p className="text-[10px] font-bold text-muted-foreground uppercase mb-2 tracking-wider">{label}</p>
            {payload.map((entry: any, index: number) => (
                <div key={index} className="flex items-center gap-3 py-1">
                    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color || entry.fill }} />
                    <span className="text-xs font-medium">{entry.name}:</span>
                    <span className="text-xs font-black ml-auto">{formatCurrency(entry.value)}</span>
                </div>
            ))}
        </div>
    );
};

// ── Page ─────────────────────────────────────────────────────────────────────

export default function FinanceiroRelatoriosPage() {
    const { activeFazendaId, isVisaoGrupo, token, _hasHydrated } = useAppStore();

    const defaultInicio = (() => {
        const d = new Date();
        d.setMonth(d.getMonth() - 5);
        d.setDate(1);
        return d.toISOString().split("T")[0];
    })();
    const defaultFim = new Date().toISOString().split("T")[0];

    const [dataInicio, setDataInicio] = useState(defaultInicio);
    const [dataFim, setDataFim] = useState(defaultFim);

    const fqParam = activeFazendaId && !isVisaoGrupo ? `&unidade_produtiva_id=${activeFazendaId}` : "";
    const canLoadReports = _hasHydrated && !!token && (isVisaoGrupo || !!activeFazendaId);

    const { data: fluxo, isLoading: loadingFluxo } = useQuery<FluxoData>({
        queryKey: ["relat-fluxo", activeFazendaId, isVisaoGrupo, dataInicio, dataFim],
        queryFn: () =>
            apiFetch(`/relatorios/fluxo-caixa?data_inicio=${dataInicio}&data_fim=${dataFim}${fqParam}`),
        enabled: canLoadReports,
    });

    const { data: dre, isLoading: loadingDRE } = useQuery<DREData>({
        queryKey: ["relat-dre", activeFazendaId, isVisaoGrupo, dataInicio, dataFim],
        queryFn: () =>
            apiFetch(`/relatorios/dre?data_inicio=${dataInicio}&data_fim=${dataFim}${fqParam}`),
        enabled: canLoadReports,
    });

    const { data: dash } = useQuery<DashData>({
        queryKey: ["fin-dashboard-cat", activeFazendaId, isVisaoGrupo],
        queryFn: () => apiFetch(`/relatorios/dashboard${activeFazendaId && !isVisaoGrupo ? `?unidade_produtiva_id=${activeFazendaId}` : ""}`),
        enabled: canLoadReports,
    });

    const chartData = (fluxo?.periodos ?? []).map(p => ({
        mes: mesLabel(p.periodo),
        Receitas: p.receitas_realizadas,
        Despesas: p.despesas_realizadas,
    }));

    const pieData = (dash?.top_despesas ?? []).slice(0, 5).map(c => ({
        name: c.plano_conta_nome,
        value: c.total,
    }));

    const totais = fluxo?.totais;
    const margem = dre && dre.receita_bruta > 0
        ? ((dre.resultado_liquido / dre.receita_bruta) * 100).toFixed(1)
        : "—";

    return (
        <div className="p-8 space-y-8 w-full max-w-7xl mx-auto">
            <PageHeader
                title="Relatórios Financeiros"
                description="Análise de rentabilidade, fluxo de caixa e demonstrativos."
                icon={<FileText className="h-8 w-8 text-primary" />}
                actions={
                    <div className="flex flex-wrap items-end gap-2">
                        <Badge variant="outline" className="text-green-600 border-green-200">DRE & Caixa</Badge>
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-bold text-muted-foreground uppercase">De</label>
                            <Input
                                type="date"
                                value={dataInicio}
                                onChange={e => setDataInicio(e.target.value)}
                                className="text-sm border border-border rounded-sm px-2 py-1 bg-background"
                            />
                        </div>
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] font-bold text-muted-foreground uppercase">Até</label>
                            <Input
                                type="date"
                                value={dataFim}
                                onChange={e => setDataFim(e.target.value)}
                                className="text-sm border border-border rounded-sm px-2 py-1 bg-background"
                            />
                        </div>
                    </div>
                }
            />

            {/* ── KPI Cards ── */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card className="border-l-4 border-l-emerald-500/80 bg-card shadow-sm">
                    <CardHeader className="pb-1">
                        <CardTitle className="text-[10px] font-black uppercase text-emerald-700/70 tracking-[0.24em]">Receita Bruta</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {loadingDRE ? <Skeleton className="h-8 w-28" /> : (
                            <div className="text-2xl font-black text-emerald-700">{formatCurrency(dre?.receita_bruta ?? 0)}</div>
                        )}
                    </CardContent>
                </Card>

                <Card className="border-l-4 border-l-rose-500/80 bg-card shadow-sm">
                    <CardHeader className="pb-1">
                        <CardTitle className="text-[10px] font-black uppercase text-rose-700/70 tracking-[0.24em]">Custeio + Invest.</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {loadingDRE ? <Skeleton className="h-8 w-28" /> : (
                            <div className="text-2xl font-black text-rose-700">
                                {formatCurrency((dre?.total_custeio ?? 0) + (dre?.total_investimento ?? 0))}
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card className="border-l-4 border-l-blue-500/80 bg-card shadow-sm">
                    <CardHeader className="pb-1">
                        <CardTitle className="text-[10px] font-black uppercase text-blue-700/70 tracking-[0.24em]">Resultado Líquido</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {loadingDRE ? <Skeleton className="h-8 w-28" /> : (
                            <>
                                <div className="text-2xl font-black text-blue-700">{formatCurrency(dre?.resultado_liquido ?? 0)}</div>
                                <Badge variant="outline" className="bg-blue-50/80 text-blue-700 mt-1 border-blue-200 text-[9px] px-1.5 py-0">
                                    Margem {margem}%
                                </Badge>
                            </>
                        )}
                    </CardContent>
                </Card>

                <Card className="border-l-4 border-l-amber-500/80 bg-card shadow-sm">
                    <CardHeader className="pb-1">
                        <CardTitle className="text-[10px] font-black uppercase text-amber-800/70 tracking-[0.24em]">Saldo Realizado</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {loadingFluxo ? <Skeleton className="h-8 w-28" /> : (
                            <div className="text-2xl font-black text-amber-700">
                                {formatCurrency(totais?.total_saldo_realizado ?? 0)}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* ── Gráficos ── */}
            <div className="grid gap-6 md:grid-cols-3">
                {/* Fluxo de Caixa */}
                <Card className="md:col-span-2 border border-border bg-card shadow-sm">
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2 text-slate-700">
                            <Activity className="h-4 w-4 text-blue-600" /> Fluxo de Caixa (Realizado)
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {loadingFluxo ? (
                            <div className="h-[300px] bg-muted animate-pulse rounded-sm" />
                        ) : (
                            <svg style={{ height: 0, width: 0, position: "absolute" }}>
                                <defs>
                                    <linearGradient id="barReceita" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.8} />
                                        <stop offset="100%" stopColor="#10b981" stopOpacity={0.4} />
                                    </linearGradient>
                                    <linearGradient id="barDespesa" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#ef4444" stopOpacity={0.8} />
                                        <stop offset="100%" stopColor="#ef4444" stopOpacity={0.4} />
                                    </linearGradient>
                                </defs>
                            </svg>
                        )}
                        <div className="h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData} barGap={8}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                                    <XAxis dataKey="mes" axisLine={false} tickLine={false} />
                                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10 }}
                                        tickFormatter={v => `R$${(v / 1000).toFixed(0)}k`} />
                                    <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(0,0,0,0.05)" }} />
                                    <Legend iconType="circle" />
                                    <Bar dataKey="Receitas" fill="url(#barReceita)" radius={[4, 4, 0, 0]} barSize={20} />
                                    <Bar dataKey="Despesas" fill="url(#barDespesa)" radius={[4, 4, 0, 0]} barSize={20} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>

                {/* Top Categorias de Despesa */}
                <Card className="border border-border bg-card shadow-sm">
                    <CardHeader>
                        <CardTitle className="text-sm font-black uppercase tracking-[0.24em] text-slate-700">Top Despesas</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {pieData.length === 0 ? (
                            <div className="h-[250px] flex items-center justify-center text-sm text-muted-foreground">
                                Sem dados de categorias
                            </div>
                        ) : (
                            <>
                                <div className="h-[200px] w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie data={pieData} cx="50%" cy="50%"
                                                innerRadius={55} outerRadius={80}
                                                paddingAngle={4} dataKey="value">
                                                {pieData.map((_, i) => (
                                                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                                ))}
                                            </Pie>
                                            <Tooltip content={<ChartTooltip />} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="mt-3 space-y-1.5">
                                    {pieData.map((d, i) => (
                                        <div key={i} className="flex justify-between text-xs items-center">
                                            <div className="flex items-center gap-1.5">
                                                <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                                                <span className="truncate max-w-[120px] font-medium">{d.name}</span>
                                            </div>
                                            <span className="text-muted-foreground">{formatCurrency(d.value)}</span>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}
                    </CardContent>
                </Card>

                {/* DRE Sintético */}
                <Card className="md:col-span-3 border border-border bg-card shadow-sm">
                    <CardHeader>
                        <CardTitle className="text-base text-slate-700">Demonstrativo de Resultado — DRE</CardTitle>
                        <CardDescription>Período: {dataInicio} a {dataFim}</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loadingDRE ? (
                            <div className="space-y-2">
                                {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-10 w-full" />)}
                            </div>
                        ) : (
                            <div className="grid md:grid-cols-2 gap-8">
                                <div className="space-y-2 font-medium">
                                    <div className="flex justify-between p-2.5 rounded-sm bg-emerald-50/40 border border-emerald-100">
                                        <span className="text-muted-foreground text-xs uppercase flex items-center gap-1.5">
                                            <ArrowUpCircle size={13} className="text-emerald-600" /> Receita Bruta
                                        </span>
                                        <span className="font-bold">{formatCurrency(dre?.receita_bruta ?? 0)}</span>
                                    </div>
                                    <div className="flex justify-between p-2.5 text-rose-600 bg-rose-50/40 border border-rose-100 rounded-sm">
                                        <span className="text-xs uppercase font-bold">(-) Custeio</span>
                                        <span>- {formatCurrency(dre?.total_custeio ?? 0)}</span>
                                    </div>
                                    <div className="flex justify-between p-2.5 text-amber-700 bg-amber-50/40 border border-amber-100 rounded-sm">
                                        <span className="text-xs uppercase font-bold">(-) Investimento</span>
                                        <span>- {formatCurrency(dre?.total_investimento ?? 0)}</span>
                                    </div>
                                    <div className="flex justify-between p-2.5 border-y border-dashed border-slate-300 font-black bg-slate-50/40">
                                        <span className="text-sm uppercase">Resultado da Ativ. Rural</span>
                                        <span className={dre && dre.resultado_atividade_rural >= 0 ? "text-emerald-700" : "text-rose-600"}>
                                            {formatCurrency(dre?.resultado_atividade_rural ?? 0)}
                                        </span>
                                    </div>
                                </div>
                                <div className="space-y-2 font-medium">
                                    {(dre?.outras_receitas ?? 0) > 0 && (
                                        <div className="flex justify-between p-2.5 rounded-sm bg-blue-50/40 border border-blue-100">
                                            <span className="text-muted-foreground text-xs uppercase flex items-center gap-1.5">
                                                <Landmark size={13} className="text-blue-600" /> Outras Receitas
                                            </span>
                                            <span className="font-bold">{formatCurrency(dre?.outras_receitas ?? 0)}</span>
                                        </div>
                                    )}
                                    {(dre?.total_nao_dedutivel ?? 0) > 0 && (
                                        <div className="flex justify-between p-2.5 text-muted-foreground bg-slate-50/40 border border-slate-100 rounded-sm">
                                            <span className="text-xs uppercase">(-) Não Dedutível</span>
                                            <span>- {formatCurrency(dre?.total_nao_dedutivel ?? 0)}</span>
                                        </div>
                                    )}
                                    <div className={`flex justify-between p-4 rounded-sm font-black text-xl ${dre && dre.resultado_liquido >= 0 ? "bg-emerald-50/40 text-emerald-700 border border-emerald-100" : "bg-rose-50/40 text-rose-700 border border-rose-100"}`}>
                                        <span>RESULTADO LÍQUIDO</span>
                                        <span>{formatCurrency(dre?.resultado_liquido ?? 0)}</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground text-right">
                                        Margem: {margem}% · Receita Bruta: {formatCurrency(dre?.receita_bruta ?? 0)}
                                    </p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
