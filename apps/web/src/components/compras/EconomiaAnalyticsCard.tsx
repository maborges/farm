"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingDown, Award, Percent, ShoppingBag, BarChart3, Users, Trophy, Handshake } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { 
    AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
    PieChart, Pie, Cell, Legend
} from "recharts";

interface EconomiaData {
    economia_total: number;
    economia_media_percentual: number;
    total_pedidos: number;
    melhor_decisao: {
        item: string;
        economia: number;
    };
}

interface SerieTemporalItem {
    periodo: string;
    economia_total: number;
}

interface SerieTemporalData {
    items: SerieTemporalItem[];
}

interface CategoriaItem {
    categoria: string;
    economia_total: number;
    percentual: number;
}

interface CategoriaData {
    items: CategoriaItem[];
}

interface UsuarioItem {
    usuario_id: string | null;
    usuario_nome: string;
    economia_total: number;
    economia_percentual: number;
    total_pedidos: number;
}

interface UsuarioData {
    items: UsuarioItem[];
}

interface FornecedorItem {
    fornecedor_nome: string;
    economia_total: number;
    economia_percentual: number;
    total_pedidos: number;
}

interface FornecedorData {
    items: FornecedorItem[];
}

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#6366f1", "#8b5cf6"];

const fmt = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

export function EconomiaAnalyticsCard() {
    const { data, isLoading } = useQuery<EconomiaData>({
        queryKey: ["economia-analytics"],
        queryFn: () => apiFetch("/compras/analytics/economia"),
    });

    const { data: trend, isLoading: isLoadingTrend } = useQuery<SerieTemporalData>({
        queryKey: ["economia-trend"],
        queryFn: () => apiFetch("/compras/analytics/economia/serie-temporal"),
    });

    const { data: categories, isLoading: isLoadingCats } = useQuery<CategoriaData>({
        queryKey: ["economia-categories"],
        queryFn: () => apiFetch("/compras/analytics/economia/por-categoria"),
    });

    const { data: usuarios } = useQuery<UsuarioData>({
        queryKey: ["economia-usuarios"],
        queryFn: () => apiFetch("/compras/analytics/economia/por-usuario"),
    });

    const { data: fornecedores } = useQuery<FornecedorData>({
        queryKey: ["economia-fornecedores"],
        queryFn: () => apiFetch("/compras/analytics/economia/por-fornecedor"),
    });

    if (isLoading || isLoadingTrend || isLoadingCats) {
        return <Skeleton className="h-[240px] w-full rounded-sm" />;
    }

    if (!data || data.economia_total === 0) {
        return null;
    }

    return (
        <Card className="border-green-200 bg-green-50/30 dark:bg-green-950/10">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold flex items-center gap-2 text-green-700 dark:text-green-400">
                    <TrendingDown className="size-4" />
                    Economia Gerada pelo Sistema
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="flex flex-col xl:flex-row gap-6">
                    {/* Métricas Principais */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-1 gap-4 xl:w-[280px]">
                        <div className="space-y-1">
                            <p className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
                                <Award className="size-3" /> Economia Total
                            </p>
                            <p className="text-2xl font-black text-green-600 tabular-nums">
                                {fmt(data.economia_total)}
                            </p>
                        </div>

                        <div className="space-y-1">
                            <p className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
                                <Percent className="size-3" /> Média por Compra
                            </p>
                            <p className="text-2xl font-black text-green-600 tabular-nums">
                                {data.economia_media_percentual.toFixed(1)}%
                            </p>
                        </div>

                        <div className="space-y-1">
                            <p className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
                                <ShoppingBag className="size-3" /> Pedidos Analisados
                            </p>
                            <p className="text-2xl font-black text-muted-foreground tabular-nums">
                                {data.total_pedidos}
                            </p>
                        </div>

                        <div className="space-y-1 bg-white/50 dark:bg-black/20 p-2 rounded-sm border border-green-100 dark:border-green-900/50">
                            <p className="text-[10px] uppercase font-bold text-green-700 dark:text-green-400">
                                🚀 Maior Economia
                            </p>
                            <div className="flex items-center justify-between gap-2">
                                <p className="text-xs font-bold truncate max-w-[120px]">
                                    {data.melhor_decisao.item}
                                </p>
                                <p className="text-xs font-black text-green-600">
                                    +{fmt(data.melhor_decisao.economia)}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Gráfico de Evolução */}
                        <div className="min-h-[180px] bg-white/30 dark:bg-black/10 rounded-sm p-4 border border-green-100/50 dark:border-green-900/20">
                            <div className="flex items-center justify-between mb-4">
                                <p className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
                                    <BarChart3 className="size-3" /> Tendência de Savings (Mensal)
                                </p>
                            </div>
                            <ResponsiveContainer width="100%" height={140}>
                                <AreaChart data={trend?.items || []}>
                                    <defs>
                                        <linearGradient id="colorEconomia" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#10b98120" />
                                    <XAxis 
                                        dataKey="periodo" 
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{ fontSize: 10, fontWeight: 600 }}
                                        dy={10}
                                    />
                                    <YAxis hide />
                                    <Tooltip 
                                        contentStyle={{ 
                                            borderRadius: '4px', 
                                            border: 'none', 
                                            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                                            fontSize: '12px'
                                        }}
                                        formatter={(value: number) => [fmt(value), "Economia"]}
                                    />
                                    <Area 
                                        type="monotone" 
                                        dataKey="economia_total" 
                                        stroke="#10b981" 
                                        strokeWidth={3}
                                        fillOpacity={1} 
                                        fill="url(#colorEconomia)" 
                                        animationDuration={1500}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Distribuição por Categoria */}
                        <div className="min-h-[180px] bg-white/30 dark:bg-black/10 rounded-sm p-4 border border-green-100/50 dark:border-green-900/20">
                            <div className="flex items-center justify-between mb-2">
                                <p className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
                                    <Percent className="size-3" /> Breakdown por Categoria
                                </p>
                            </div>
                            <ResponsiveContainer width="100%" height={160}>
                                <PieChart>
                                    <Pie
                                        data={categories?.items || []}
                                        dataKey="economia_total"
                                        nameKey="categoria"
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={40}
                                        outerRadius={60}
                                        paddingAngle={5}
                                        animationDuration={1500}
                                    >
                                        {(categories?.items || []).map((_, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} strokeWidth={0} />
                                        ))}
                                    </Pie>
                                    <Tooltip 
                                        contentStyle={{ 
                                            borderRadius: '4px', 
                                            border: 'none', 
                                            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                                            fontSize: '12px'
                                        }}
                                        formatter={(value: number, name: string) => [fmt(value), name]}
                                    />
                                    <Legend 
                                        layout="vertical" 
                                        align="right" 
                                        verticalAlign="middle"
                                        iconType="circle"
                                        formatter={(value, entry: any) => (
                                            <span className="text-[10px] font-bold text-muted-foreground uppercase">
                                                {value} ({entry.payload.percentual}%)
                                            </span>
                                        )}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>

                {/* Performance dos Compradores */}
                {usuarios && usuarios.items.length > 0 && (
                    <div className="mt-4 border-t border-green-100 dark:border-green-900/30 pt-4">
                        <p className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1 mb-3">
                            <Users className="size-3" /> Performance dos Compradores
                        </p>
                        <div className="space-y-2">
                            {usuarios.items.map((u, idx) => (
                                <div key={u.usuario_id ?? "sem-usuario"} className="flex items-center gap-3">
                                    <span className="text-[10px] font-black text-muted-foreground w-4 tabular-nums">{idx + 1}</span>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-1.5">
                                            <span className="text-xs font-bold truncate">{u.usuario_nome}</span>
                                            {idx === 0 && (
                                                <span className="inline-flex items-center gap-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 text-[9px] font-black px-1.5 py-0.5 rounded-sm uppercase">
                                                    <Trophy className="size-2.5" /> Top Performer
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2 mt-0.5">
                                            <div className="flex-1 h-1 bg-green-100 dark:bg-green-900/30 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-green-500 rounded-full"
                                                    style={{ width: `${u.economia_percentual}%` }}
                                                />
                                            </div>
                                            <span className="text-[10px] text-muted-foreground tabular-nums">{u.economia_percentual.toFixed(1)}%</span>
                                        </div>
                                    </div>
                                    <div className="text-right shrink-0">
                                        <p className="text-xs font-black text-green-600 tabular-nums">{fmt(u.economia_total)}</p>
                                        <p className="text-[10px] text-muted-foreground">{u.total_pedidos} pedido{u.total_pedidos !== 1 ? "s" : ""}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
                {/* Performance por Fornecedor */}
                {fornecedores && fornecedores.items.length > 0 && (
                    <div className="mt-4 border-t border-green-100 dark:border-green-900/30 pt-4">
                        <p className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1 mb-3">
                            <Handshake className="size-3" /> Performance por Fornecedor
                        </p>
                        <div className="space-y-2">
                            {fornecedores.items.map((f, idx) => (
                                <div key={f.fornecedor_nome} className="flex items-center gap-3">
                                    <span className="text-[10px] font-black text-muted-foreground w-4 tabular-nums">{idx + 1}</span>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-1.5">
                                            <span className="text-xs font-bold truncate">{f.fornecedor_nome}</span>
                                            {idx === 0 && (
                                                <span className="inline-flex items-center gap-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 text-[9px] font-black px-1.5 py-0.5 rounded-sm uppercase">
                                                    <Trophy className="size-2.5" /> Melhor Parceiro
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2 mt-0.5">
                                            <div className="flex-1 h-1 bg-blue-100 dark:bg-blue-900/30 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-blue-500 rounded-full"
                                                    style={{ width: `${f.economia_percentual}%` }}
                                                />
                                            </div>
                                            <span className="text-[10px] text-muted-foreground tabular-nums">{f.economia_percentual.toFixed(1)}%</span>
                                        </div>
                                    </div>
                                    <div className="text-right shrink-0">
                                        <p className="text-xs font-black text-blue-600 tabular-nums">{fmt(f.economia_total)}</p>
                                        <p className="text-[10px] text-muted-foreground">{f.total_pedidos} pedido{f.total_pedidos !== 1 ? "s" : ""}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
