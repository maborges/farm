"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    LayoutDashboard, Users, Building2, TrendingUp, HandCoins,
    ArrowUpRight, Activity, Zap, ShieldCheck
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { formatCurrency } from "@/lib/utils";
import {
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    AreaChart, Area, PieChart, Pie, Cell
} from "recharts";

interface DashboardStats {
    resumo: {
        mrr: number;
        tenants_ativos: number;
        tenants_total: number;
        usuarios_total: number;
    };
    graficos: {
        receita: Array<{ mes: string; valor: number }>;
        planos: Array<{ name: string; value: number }>;
    };
    plataforma: {
        versao: string;
        status: string;
    };
}

const PIE_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"];

export default function BackofficeDashboardPage() {
    const { data: stats, isLoading } = useQuery<DashboardStats>({
        queryKey: ["backoffice", "stats"],
        queryFn: () => apiFetch("/backoffice/dashboard/stats"),
    });

    if (isLoading) {
        return (
            <div className="flex-1 flex flex-col gap-6 w-full px-4 md:px-8 py-8">
                <Skeleton className="h-16 w-full" />
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-32 w-full" />
                    ))}
                </div>
                <div className="grid gap-6 lg:grid-cols-7">
                    <Skeleton className="h-[360px] lg:col-span-4" />
                    <Skeleton className="h-[360px] lg:col-span-3" />
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col gap-6 w-full px-4 md:px-8 py-8">
            <PageHeader
                title="Dashboard Executivo"
                description="Saúde financeira e operacional do DeepFarms em tempo real."
                icon={<LayoutDashboard className="text-primary" size={22} />}
            />

            {/* ── KPI Cards ── */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">
                            MRR (Recorrência)
                        </CardTitle>
                        <HandCoins className="size-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black">{formatCurrency(stats?.resumo.mrr ?? 0)}</div>
                        <p className="text-xs text-green-600 flex items-center gap-1 mt-1 font-semibold">
                            <ArrowUpRight size={12} /> +12.5% vs mês anterior
                        </p>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">
                            Contas Ativas
                        </CardTitle>
                        <Building2 className="size-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black">{stats?.resumo.tenants_ativos}</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            de {stats?.resumo.tenants_total} cadastradas
                        </p>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">
                            Usuários Totais
                        </CardTitle>
                        <Users className="size-4 text-amber-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black">{stats?.resumo.usuarios_total}</div>
                        <p className="text-xs text-green-600 flex items-center gap-1 mt-1 font-semibold">
                            <ArrowUpRight size={12} /> +4 novos hoje
                        </p>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">
                            Status do Sistema
                        </CardTitle>
                        <ShieldCheck className="size-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black uppercase text-green-600">
                            {stats?.plataforma.status}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Uptime 99.9% · v{stats?.plataforma.versao}
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* ── Gráficos ── */}
            <div className="grid gap-6 lg:grid-cols-7">
                <Card className="lg:col-span-4">
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                            <Activity className="size-4 text-primary" /> Tendência de Faturamento
                        </CardTitle>
                        <CardDescription>Evolução do MRR nos últimos 6 meses.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={stats?.graficos.receita}>
                                    <defs>
                                        <linearGradient id="gradValor" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                                    <XAxis dataKey="mes" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10 }} tickFormatter={(v) => `R$ ${v}`} />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "hsl(var(--card))",
                                            borderRadius: "4px",
                                            border: "1px solid hsl(var(--border))",
                                        }}
                                        formatter={((v: unknown) => [formatCurrency(Number(v ?? 0)), "Receita"]) as Parameters<typeof Tooltip>[0]["formatter"]}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="valor"
                                        stroke="#10b981"
                                        strokeWidth={3}
                                        fillOpacity={1}
                                        fill="url(#gradValor)"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>

                <Card className="lg:col-span-3">
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                            <Zap className="size-4 text-blue-500" /> Mix de Assinaturas
                        </CardTitle>
                        <CardDescription>Distribuição de clientes por plano.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex items-center justify-center">
                        <div className="h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={stats?.graficos.planos}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={70}
                                        outerRadius={100}
                                        paddingAngle={4}
                                        dataKey="value"
                                    >
                                        {stats?.graficos.planos.map((_, index) => (
                                            <Cell
                                                key={`cell-${index}`}
                                                fill={PIE_COLORS[index % PIE_COLORS.length]}
                                            />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "hsl(var(--card))",
                                            borderRadius: "4px",
                                            border: "1px solid hsl(var(--border))",
                                        }}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
