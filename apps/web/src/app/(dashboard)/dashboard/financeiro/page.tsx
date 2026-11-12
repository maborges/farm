"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
    ArrowUpRight, ArrowDownRight, CreditCard,
    AlertTriangle, Bell, Clock, CheckCircle2,
    TrendingUp, Wallet, LayoutDashboard,
    DollarSign, Receipt, BarChart3, Scale, ShieldCheck, FileSpreadsheet, ArrowLeftRight, Landmark,
} from "lucide-react";
import { IAPredicoesCard } from "@/components/ia/ia-predicoes-card";
import { IAEstresseCard } from "@/components/ia/ia-estresse-card";
import { IAPlanoAcaoCard } from "@/components/ia/ia-plano-acao-card";
import { PageHeader } from "@/components/shared/page-header";
import { QuickActionGrid } from "@/components/ui/quick-action-grid";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Legend,
} from "recharts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface VencimentoProximo {
    id: string;
    tipo: "RECEITA" | "DESPESA";
    descricao: string;
    valor: number;
    data_vencimento: string;
    dias_restantes: number;
    pessoa_nome: string | null;
}

interface AlertaFinanceiro {
    tipo: string;
    nivel: "INFO" | "ALERTA" | "CRITICO";
    mensagem: string;
    valor: number;
}

interface DashboardData {
    data_referencia: string;
    total_recebido_mes: number;
    total_pago_mes: number;
    saldo_mes: number;
    total_a_receber: number;
    total_a_pagar: number;
    total_atrasado_receitas: number;
    total_atrasado_despesas: number;
    vencendo_7d: VencimentoProximo[];
    alertas: AlertaFinanceiro[];
}

interface FluxoData {
    periodos: Array<{
        periodo: string;
        receitas_realizadas: number;
        despesas_realizadas: number;
        saldo_acumulado: number;
    }>;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

function mesLabel(periodoIso: string) {
    const d = new Date(periodoIso + "T00:00:00");
    return d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
}

const today = new Date();
const sixMonthsAgo = new Date(today.getFullYear(), today.getMonth() - 5, 1);
const dataInicio = sixMonthsAgo.toISOString().split("T")[0];
const dataFim = today.toISOString().split("T")[0];

const nivelColor: Record<string, string> = {
    INFO: "bg-blue-100 text-blue-700",
    ALERTA: "bg-amber-100 text-amber-700",
    CRITICO: "bg-red-100 text-red-700",
};

const ChartTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-background/95 border border-border p-3 rounded-sm shadow-xl text-xs">
            <p className="font-bold text-muted-foreground uppercase mb-1 tracking-wide">{label}</p>
            {payload.map((e: any, i: number) => (
                <div key={i} className="flex items-center gap-2 py-0.5">
                    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: e.color }} />
                    <span>{e.name}:</span>
                    <span className="font-black ml-auto">{fmt(e.value)}</span>
                </div>
            ))}
        </div>
    );
};

// ── Page ─────────────────────────────────────────────────────────────────────

export default function FinanceiroDashboard() {
    const { activeFazendaId, isVisaoGrupo, token, _hasHydrated } = useAppStore();
    const fqParam = activeFazendaId && !isVisaoGrupo ? `?unidade_produtiva_id=${activeFazendaId}` : "";
    const canLoadFinanceiro = _hasHydrated && !!token && (isVisaoGrupo || !!activeFazendaId);

    const { data: dash, isLoading: loadingDash } = useQuery<DashboardData>({
        queryKey: ["fin-dashboard", activeFazendaId, isVisaoGrupo],
        queryFn: () => apiFetch(`/relatorios/dashboard${fqParam}`),
        enabled: canLoadFinanceiro,
    });

    const { data: fluxo, isLoading: loadingFluxo } = useQuery<FluxoData>({
        queryKey: ["fin-fluxo", activeFazendaId, isVisaoGrupo, dataInicio, dataFim],
        queryFn: () =>
            apiFetch(
                `/relatorios/fluxo-caixa?data_inicio=${dataInicio}&data_fim=${dataFim}${activeFazendaId && !isVisaoGrupo ? `&unidade_produtiva_id=${activeFazendaId}` : ""}`
            ),
        enabled: canLoadFinanceiro,
    });

    const { data: despesas = [], isLoading: loadingDesp } = useQuery<any[]>({
        queryKey: ["despesas-rec", activeFazendaId, isVisaoGrupo],
        queryFn: () => apiFetch(isVisaoGrupo ? "/financeiro/despesas/" : `/financeiro/despesas/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: canLoadFinanceiro,
    });

    const { data: receitas = [], isLoading: loadingRec } = useQuery<any[]>({
        queryKey: ["receitas-rec", activeFazendaId, isVisaoGrupo],
        queryFn: () => apiFetch(isVisaoGrupo ? "/financeiro/receitas/" : `/financeiro/receitas/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: canLoadFinanceiro,
    });

    const chartData = (fluxo?.periodos ?? []).map(p => ({
        mes: mesLabel(p.periodo),
        Receitas: p.receitas_realizadas,
        Despesas: p.despesas_realizadas,
        Saldo: p.saldo_acumulado,
    }));

    // Preserve the source collection explicitly. Inferring the type from
    // `cliente` is incorrect for receipts such as owner contributions, which
    // commonly have no customer field (they may only have `pessoa_id`).
    const movimentacoes = [
        ...receitas.map((m: any) => ({ ...m, _tipoMovimentacao: "RECEITA" as const })),
        ...despesas.map((m: any) => ({ ...m, _tipoMovimentacao: "DESPESA" as const })),
    ]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5);

    const isLoading = loadingDash || loadingDesp || loadingRec;

    const quickActions = [
        { href: "/dashboard/financeiro/contas-pagar", icon: ArrowDownRight, title: "Contas a Pagar", desc: "Títulos a liquidar e fornecedores", badge: dash?.total_a_pagar ? fmt(dash.total_a_pagar) : undefined },
        { href: "/dashboard/financeiro/receitas", icon: ArrowUpRight, title: "Contas a Receber", desc: "Entradas e faturamento", badge: dash?.total_a_receber ? fmt(dash.total_a_receber) : undefined },
        { href: "/dashboard/financeiro/fluxo-caixa", icon: TrendingUp, title: "Fluxo de Caixa", desc: "Projeção diária e mensal consolidada" },
        { href: "/dashboard/financeiro/dre", icon: BarChart3, title: "DRE Gerencial", desc: "Demonstrativo de resultado e margens" },
        { href: "/dashboard/financeiro/conciliacao", icon: ArrowLeftRight, title: "Conciliação Bancária", desc: "Extratos e conciliação OFX" },
        { href: "/dashboard/financeiro/contas-bancarias", icon: Landmark, title: "Contas Bancárias", desc: "Saldos e instituições financeiras" },
        { href: "/dashboard/financeiro/hedge/painel", icon: ShieldCheck, title: "Hedge & Commodities", desc: "Contratos futuros e travas de preço" },
        { href: "/dashboard/financeiro/relatorios", icon: FileSpreadsheet, title: "Relatórios & LCDPR", desc: "Livro caixa e demonstrativos" },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Painel Financeiro"
                icon={<LayoutDashboard className="text-primary" size={22} />}
                description="Fluxo de caixa e indicadores do mês corrente."
                breadcrumbs={[{ label: "Financeiro", href: "/dashboard/financeiro" }, { label: "Visão Geral" }]}
                actions={
                    <Button asChild variant="outline" size="sm" className="rounded-sm">
                        <Link href="/dashboard/financeiro/comercializacoes">Comercializações</Link>
                    </Button>
                }
            />

            {/* Quick Actions Grid */}
            <QuickActionGrid
                actions={quickActions.map(a => ({
                    title: a.title,
                    description: a.desc,
                    icon: a.icon,
                    href: a.href,
                    badge: a.badge,
                }))}
            />

            {/* ── KPIs do mês ── */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="border-l-[3px] border-l-emerald-500/80 bg-card shadow-sm">
                    <CardContent className="p-6">
                        <p className="text-[10px] uppercase tracking-[0.24em] text-emerald-700/70 font-black mb-1">Recebido no Mês</p>
                        {isLoading ? (
                            <div className="h-9 w-32 bg-muted animate-pulse rounded-sm" />
                        ) : (
                            <p className="text-3xl font-black text-emerald-700 tabular-nums">
                                {fmt(dash?.total_recebido_mes ?? 0)}
                            </p>
                        )}
                        <div className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50/80 dark:bg-emerald-950/20 w-fit px-2 py-0.5 rounded-full border border-emerald-200/80">
                            <ArrowUpRight className="size-3.5" /> a receber: {fmt(dash?.total_a_receber ?? 0)}
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-rose-500/80 bg-card shadow-sm">
                    <CardContent className="p-6">
                        <p className="text-[10px] uppercase tracking-[0.24em] text-rose-700/70 font-black mb-1">Pago no Mês</p>
                        {isLoading ? (
                            <div className="h-9 w-32 bg-muted animate-pulse rounded-sm" />
                        ) : (
                            <p className="text-3xl font-black text-rose-700 tabular-nums">
                                {fmt(dash?.total_pago_mes ?? 0)}
                            </p>
                        )}
                        <div className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-rose-700 bg-rose-50/80 dark:bg-rose-950/20 w-fit px-2 py-0.5 rounded-full border border-rose-200/80">
                            <AlertTriangle className="size-3.5" /> atrasado: {fmt(dash?.total_atrasado_despesas ?? 0)}
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-amber-500/80 bg-card shadow-sm">
                    <CardContent className="p-6">
                        <p className="text-[10px] uppercase tracking-[0.24em] text-amber-800/70 font-black mb-1">Saldo do Mês</p>
                        {isLoading ? (
                            <div className="h-9 w-32 bg-white/60 animate-pulse rounded-sm" />
                        ) : (
                            <p className="text-3xl font-black text-amber-800 tabular-nums">
                                {fmt(dash?.saldo_mes ?? 0)}
                            </p>
                        )}
                        <p className="text-xs text-amber-900/60 mt-3">
                            a pagar em aberto: {fmt(dash?.total_a_pagar ?? 0)}
                        </p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                {/* ── Gráfico Fluxo de Caixa ── */}
                <Card className="lg:col-span-3 flex flex-col border-slate-200 bg-card shadow-sm">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-semibold text-slate-600 flex items-center gap-2">
                            <TrendingUp className="size-4 text-blue-600" /> Fluxo de Caixa — Últimos 6 Meses
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 px-4 pb-4">
                        {loadingFluxo ? (
                            <div className="h-[260px] w-full bg-muted animate-pulse rounded-sm" />
                        ) : chartData.length === 0 ? (
                            <div className="h-[260px] flex items-center justify-center text-sm text-muted-foreground">
                                Nenhum dado de fluxo no período.
                            </div>
                        ) : (
                            <div className="h-[260px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                                        <defs>
                                            <linearGradient id="gradRec" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                            </linearGradient>
                                            <linearGradient id="gradDesp" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                                        <XAxis dataKey="mes" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                                        <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10 }}
                                            tickFormatter={v => `R$${(v / 1000).toFixed(0)}k`} />
                                        <Tooltip content={<ChartTooltip />} />
                                        <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                                        <Area type="monotone" dataKey="Receitas" stroke="#10b981" strokeWidth={2}
                                            fill="url(#gradRec)" />
                                        <Area type="monotone" dataKey="Despesas" stroke="#ef4444" strokeWidth={2}
                                            fill="url(#gradDesp)" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* IA Painel: Predições, Estresse e Plano de Ação */}
                <div className="lg:col-span-2 flex flex-col gap-4">
                    {/* Plano de Ação IA (Step 208) */}
                    <IAPlanoAcaoCard />

                    {/* IA Predições (Step 205) */}
                    <IAPredicoesCard safraId="" />

                    {/* IA Estresse (Step 206) */}
                    <IAEstresseCard />

                    {/* Próximos Vencimentos */}
                    <Card className="flex flex-col border-amber-200/60 bg-card shadow-sm">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-semibold text-amber-700 flex items-center gap-2">
                                <Clock className="size-4 text-amber-600" /> Vencendo em 7 dias
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="px-4 pb-4">
                            {loadingDash ? (
                                <div className="space-y-2">
                                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
                                </div>
                            ) : (dash?.vencendo_7d ?? []).length === 0 ? (
                                <div className="flex items-center gap-2 text-sm text-muted-foreground py-3">
                                    <CheckCircle2 className="size-4 text-green-500" /> Nenhum vencimento nos próximos 7 dias.
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {(dash?.vencendo_7d ?? []).slice(0, 5).map(v => (
                                        <div key={v.id} className="flex items-center justify-between p-2 rounded-sm border border-border/40 bg-muted/20 hover:bg-muted/40 transition-colors">
                                            <div className="flex items-center gap-2 min-w-0">
                                                <div className={`size-6 rounded-full flex items-center justify-center shrink-0 ${v.tipo === "RECEITA" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                                    {v.tipo === "RECEITA" ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="text-xs font-semibold truncate">{v.descricao}</p>
                                                    <p className="text-[10px] text-muted-foreground">{v.dias_restantes}d · {new Date(v.data_vencimento).toLocaleDateString("pt-BR")}</p>
                                                </div>
                                            </div>
                                            <p className={`text-xs font-black shrink-0 ml-2 ${v.tipo === "RECEITA" ? "text-green-700" : "text-red-600"}`}>
                                                {fmt(v.valor)}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Alertas */}
                    {(dash?.alertas ?? []).length > 0 && (
                        <Card className="border-rose-200/60 bg-card shadow-sm">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-semibold text-rose-700 flex items-center gap-2">
                                    <Bell className="size-4 text-rose-600" /> Alertas
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="px-4 pb-4 space-y-2">
                                {(dash?.alertas ?? []).slice(0, 4).map((a, i) => (
                                    <div key={i} className="flex items-start gap-2 p-2 rounded-sm border border-rose-200/50 bg-rose-50/40 dark:bg-rose-950/10">
                                        <AlertTriangle size={13} className={a.nivel === "CRITICO" ? "text-red-600 mt-0.5" : a.nivel === "ALERTA" ? "text-amber-600 mt-0.5" : "text-blue-600 mt-0.5"} />
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs leading-relaxed">{a.mensagem}</p>
                                            {a.valor > 0 && (
                                                <Badge className={`text-[9px] h-4 px-1.5 mt-1 border-none ${nivelColor[a.nivel] ?? ""}`}>
                                                    {fmt(a.valor)}
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>

            {/* ── Últimas Movimentações ── */}
            <Card className="border-l-[3px] border-l-[var(--module-financeiro)] bg-card shadow-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                        <CreditCard className="size-4" /> Últimas Movimentações
                    </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4">
                    {loadingDesp || loadingRec ? (
                        <div className="space-y-2">
                            {[1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
                        </div>
                    ) : movimentacoes.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-4 text-center">
                            Nenhuma movimentação. Registre receitas ou despesas.
                        </p>
                    ) : (
                        <div className="space-y-2">
                            {movimentacoes.map((m: any) => (
                                <div key={m.id} className="flex items-center justify-between p-3 rounded-sm border border-border/50 hover:bg-muted/30 transition-colors">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className={`size-8 rounded-sm flex items-center justify-center shrink-0 ${m._tipoMovimentacao === "RECEITA" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                            {m._tipoMovimentacao === "RECEITA" ? <ArrowUpRight className="size-4" /> : <ArrowDownRight className="size-4" />}
                                        </div>
                                        <div className="min-w-0">
                                            <p className="text-sm font-semibold truncate">{m.descricao}</p>
                                            <p className="text-xs text-muted-foreground">{new Date(m.data_vencimento).toLocaleDateString("pt-BR")}</p>
                                        </div>
                                    </div>
                                    <p className={`text-sm font-black tabular-nums shrink-0 ${m._tipoMovimentacao === "RECEITA" ? "text-green-700" : "text-destructive"}`}>
                                        {m._tipoMovimentacao === "RECEITA" ? "+" : "-"}{fmt(m.valor_total).replace("R$\u00a0", "").replace("R$ ", "").trim()}
                                    </p>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
