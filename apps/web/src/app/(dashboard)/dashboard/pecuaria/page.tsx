"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import Link from "next/link";
import {
    PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
    Tooltip as ReTooltip, ResponsiveContainer
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { format, parseISO, isValid } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    Beef, Layers, MapPin, Scale, Syringe, Baby, Skull, LayoutDashboard,
    Weight, Shuffle, ChevronRight, TrendingUp, Activity
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { QuickActionGrid } from "@/components/ui/quick-action-grid";

// ── Types ─────────────────────────────────────────────────────────────────────

interface LoteBovino {
    id: string;
    identificacao: string;
    categoria: string;
    raca: string;
    quantidade_cabecas: number;
    peso_medio_kg: number;
    piquete_id?: string;
    ativo: boolean;
    data_formacao: string;
}

interface ManejoLote {
    id: string;
    lote_id: string;
    tipo_evento: string;
    data_evento: string;
    quantidade_cabecas?: number;
    peso_total_kg?: number;
    observacoes?: string;
}

interface PiqueAreaResumo {
    area_pastagem_ha: number;
    lotacao_ua_ha: number;
    arrobas_totais: number;
    arrobas_por_hectare: number;
    custo_total_por_arroba: number;
}

interface PiqueteTerritorial {
    id: string;
    nome: string;
    area_hectares: number | null;
    dados_extras?: {
        capacidade_suporte_ua?: number | null;
    } | null;
    ativo: boolean;
}

// ── Config ────────────────────────────────────────────────────────────────────

const CATEGORIA_COLORS: Record<string, string> = {
    "Bezerros":        "#3b82f6",
    "Vacas Paridas":   "#ec4899",
    "Novilhas":        "#8b5cf6",
    "Bois em Engorda": "#f59e0b",
    "Reprodutores":    "#ef4444",
    "Touros":          "#dc2626",
};
const DEFAULT_COLOR = "#6b7280";

const EVENTO_CONFIG: Record<string, { label: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
    NASCIMENTO:    { label: "Nascimento",    color: "text-green-600",  icon: Baby },
    MORTE:         { label: "Morte",         color: "text-red-600",    icon: Skull },
    PESAGEM:       { label: "Pesagem",       color: "text-blue-600",   icon: Weight },
    VACINACAO:     { label: "Vacinação",     color: "text-purple-600", icon: Syringe },
    TRANSFERENCIA: { label: "Transferência", color: "text-orange-600", icon: Shuffle },
};

function fmtDate(s?: string) {
    if (!s) return "—";
    try {
        const d = parseISO(s);
        return isValid(d) ? format(d, "dd/MM/yy", { locale: ptBR }) : "—";
    } catch { return "—"; }
}

function getCategoriaColor(cat: string) {
    return CATEGORIA_COLORS[cat] ?? DEFAULT_COLOR;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function PecuariaDashboard() {
    const { activeFazendaId, isVisaoGrupo } = useAppStore();
    const qs = activeFazendaId && !isVisaoGrupo ? `?unidade_produtiva_id=${activeFazendaId}` : "";

    const { data: lotes = [] } = useQuery<LoteBovino[]>({
        queryKey: ["lotes-bovinos", activeFazendaId],
        queryFn: () => apiFetch<LoteBovino[]>(`/pecuaria/lotes${qs}`),
        enabled: !!activeFazendaId,
    });

    const { data: manejos = [] } = useQuery<ManejoLote[]>({
        queryKey: ["pecuaria-manejos"],
        queryFn: () => apiFetch<ManejoLote[]>("/pecuaria/manejos/"),
    });

    const { data: piquetes = [] } = useQuery<PiqueteTerritorial[]>({
        queryKey: ["piquetes", activeFazendaId],
        queryFn: () => apiFetch<PiqueteTerritorial[]>(`/cadastros/areas-rurais?tipo=PIQUETE&unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId,
    });

    const { data: resumoEconomico } = useQuery<PiqueAreaResumo>({
        queryKey: ["pecuaria-resumo-economico", activeFazendaId],
        queryFn: () => apiFetch<PiqueAreaResumo>(`/pecuaria/dashboard/resumo${qs}`),
        enabled: !!activeFazendaId,
    });

    const quickActions = [
        { href: "/dashboard/pecuaria/lotes", icon: Beef, label: "Lotes & Rebanho", desc: "Controle e pesagens", color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/10" },
        { href: "/dashboard/pecuaria/manejo", icon: Syringe, label: "Manejo & Sanidade", desc: "Vacinas e tratamentos", color: "text-purple-600 dark:text-purple-400", bg: "bg-purple-500/10" },
        { href: "/dashboard/pecuaria/piquetes", icon: MapPin, label: "Piquetes & Pastos", desc: "Lotação e suporte", color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10" },
        { href: "/dashboard/pecuaria/genetica", icon: Activity, label: "Genética & Matrizes", desc: "Reprodução e IATF", color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-500/10" },
        { href: "/dashboard/pecuaria/confinamento", icon: Layers, label: "Confinamento", desc: "Dietas e engorda", color: "text-orange-600 dark:text-orange-400", bg: "bg-orange-500/10" },
        { href: "/dashboard/pecuaria/leite", icon: TrendingUp, label: "Produção Leiteira", desc: "Ordenhas e tanques", color: "text-cyan-600 dark:text-cyan-400", bg: "bg-cyan-500/10" },
        { href: "/dashboard/pecuaria/relatorios", icon: Scale, label: "Relatórios Zootécnicos", desc: "GMD e curva de peso", color: "text-indigo-600 dark:text-indigo-400", bg: "bg-indigo-500/10" },
    ];

    // ── KPIs ─────────────────────────────────────────────────────────────────
    const kpis = useMemo(() => {
        const ativos = lotes.filter(l => l.ativo);
        const totalCabecas = ativos.reduce((s, l) => s + l.quantidade_cabecas, 0);
        const pesoMedio = totalCabecas > 0
            ? ativos.reduce((s, l) => s + l.peso_medio_kg * l.quantidade_cabecas, 0) / totalCabecas
            : 0;
        const totalUA = ativos.reduce((s, l) => s + l.quantidade_cabecas * 0.5, 0);
        return {
            totalCabecas,
            lotesAtivos: ativos.length,
            pesoMedio,
            totalUA,
            piquetesAtivos: piquetes.filter(p => p.ativo).length,
        };
    }, [lotes, piquetes]);

    // ── Chart: composição por categoria ──────────────────────────────────────
    const categoriaData = useMemo(() => {
        const map = new Map<string, number>();
        for (const l of lotes.filter(l => l.ativo)) {
            map.set(l.categoria, (map.get(l.categoria) ?? 0) + l.quantidade_cabecas);
        }
        return Array.from(map.entries()).map(([name, value]) => ({ name, value }));
    }, [lotes]);

    // ── Chart: cabeças por raça ───────────────────────────────────────────────
    const racaData = useMemo(() =>
        [...new Map<string, number>(
            lotes.filter(l => l.ativo).map(l => [l.raca, (lotes.filter(x => x.raca === l.raca && x.ativo).reduce((s, x) => s + x.quantidade_cabecas, 0))])
        ).entries()]
            .map(([raca, cabecas]) => ({ raca, cabecas }))
            .sort((a, b) => b.cabecas - a.cabecas)
            .slice(0, 6),
    [lotes]);

    // ── Piquete load ──────────────────────────────────────────────────────────
    const activePiquetes = useMemo(() =>
        piquetes.filter(p => p.ativo).map(p => {
            const cabecas = lotes.filter(l => l.ativo && l.piquete_id === p.id)
                .reduce((s, l) => s + l.quantidade_cabecas, 0);
            const ua = cabecas * 0.5;
            const capacidade = p.dados_extras?.capacidade_suporte_ua ?? null;
            const lotPct = capacidade ? Math.min(100, (ua / capacidade) * 100) : null;
            return { ...p, cabecas, lotPct };
        }),
    [piquetes, lotes]);

    // ── Recent manejos ────────────────────────────────────────────────────────
    const recentManejos = useMemo(() =>
        [...manejos]
            .sort((a, b) => new Date(b.data_evento).getTime() - new Date(a.data_evento).getTime())
            .slice(0, 8),
    [manejos]);

    // ── Render ────────────────────────────────────────────────────────────────
    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Painel de Rebanhos"
                description="Painel zootécnico — lotes, manejos sanitários, piquetes e indicadores zootécnicos"
                icon={<LayoutDashboard className="size-6 text-primary" />}
                breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Pecuária" }]}
                actions={
                    <div className="flex gap-2">
                        <Button asChild variant="outline" size="sm" className="h-8 text-xs rounded-sm">
                            <Link href="/dashboard/pecuaria/lotes">Ver Lotes</Link>
                        </Button>
                        <Button asChild size="sm" className="h-8 text-xs rounded-sm">
                            <Link href="/dashboard/pecuaria/manejo">Registrar Manejo</Link>
                        </Button>
                    </div>
                }
            />

            {/* ── Comandos & Ações Rápidas da Pecuária no Topo ── */}
            <QuickActionGrid
                label="Ações & Comandos do Rebanho"
                columnsClassName="grid-cols-2 sm:grid-cols-4 lg:grid-cols-7"
                actions={quickActions.map(a => ({
                    title: a.label,
                    description: a.desc,
                    icon: a.icon,
                    href: a.href,
                }))}
            />

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {[
                    { label: "Total de Cabeças", value: kpis.totalCabecas.toLocaleString("pt-BR"), icon: Beef, color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/10" },
                    { label: "Lotes Ativos", value: kpis.lotesAtivos, icon: Layers, color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-500/10" },
                    { label: "Piquetes", value: kpis.piquetesAtivos, icon: MapPin, color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10" },
                    { label: "Peso Médio (kg)", value: kpis.pesoMedio.toFixed(0), icon: Scale, color: "text-purple-600 dark:text-purple-400", bg: "bg-purple-500/10" },
                    { label: "UA Estimada", value: kpis.totalUA.toFixed(0), icon: Activity, color: "text-orange-600 dark:text-orange-400", bg: "bg-orange-500/10" },
                ].map(({ label, value, icon: Icon, color, bg }) => (
                    <Card key={label} className="shadow-xs border border-border/70 rounded-sm">
                        <CardContent className="p-4">
                            <div className="flex items-start justify-between gap-2">
                                <div>
                                    <div className="text-2xl font-bold leading-none tabular-nums">{value}</div>
                                    <div className="text-xs text-muted-foreground mt-1.5 leading-tight font-medium">{label}</div>
                                </div>
                                <div className={`p-2 rounded-sm ${bg} ${color}`}>
                                    <Icon className="size-4.5" />
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Indicadores Econômicos & Lotação */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                    { label: "Lotação (UA/ha)", value: (resumoEconomico?.lotacao_ua_ha ?? 0).toFixed(2) },
                    { label: "Arrobas / ha (@/ha)", value: (resumoEconomico?.arrobas_por_hectare ?? 0).toFixed(2) },
                    {
                        label: "Custo Total / @",
                        value: (resumoEconomico?.custo_total_por_arroba ?? 0).toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                        }),
                    },
                    { label: "Área de Pastagem (ha)", value: (resumoEconomico?.area_pastagem_ha ?? 0).toFixed(1) },
                ].map((item) => (
                    <Card key={item.label} className="shadow-xs border border-border/70 rounded-sm">
                        <CardContent className="p-4">
                            <div className="text-xs text-muted-foreground font-medium">{item.label}</div>
                            <div className="text-xl font-bold mt-1 tabular-nums">{item.value}</div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base">Composição do Rebanho</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {categoriaData.length === 0 ? (
                            <div className="h-44 flex items-center justify-center text-muted-foreground text-sm">
                                Nenhum lote ativo
                            </div>
                        ) : (
                            <div className="flex gap-4 items-center">
                                <ResponsiveContainer width="45%" height={170}>
                                    <PieChart>
                                        <Pie data={categoriaData} dataKey="value" cx="50%" cy="50%" innerRadius={36} outerRadius={68}>
                                            {categoriaData.map((entry, i) => (
                                                <Cell key={i} fill={getCategoriaColor(entry.name)} />
                                            ))}
                                        </Pie>
                                        <ReTooltip formatter={(v: unknown, n: unknown) => [`${v} cab.`, `${n}`]} />
                                    </PieChart>
                                </ResponsiveContainer>
                                <div className="flex-1 space-y-1.5">
                                    {categoriaData.map((entry, i) => (
                                        <div key={i} className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: getCategoriaColor(entry.name) }} />
                                                <span className="text-xs truncate max-w-[100px]">{entry.name}</span>
                                            </div>
                                            <span className="text-xs font-medium">{entry.value.toLocaleString("pt-BR")}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base">Cabeças por Raça</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {racaData.length === 0 ? (
                            <div className="h-44 flex items-center justify-center text-muted-foreground text-sm">
                                Nenhum lote ativo
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height={170}>
                                <BarChart data={racaData} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
                                    <XAxis type="number" tick={{ fontSize: 11 }} />
                                    <YAxis dataKey="raca" type="category" width={75} tick={{ fontSize: 11 }} />
                                    <ReTooltip formatter={(v: unknown) => [`${v} cab.`, "Cabeças"]} />
                                    <Bar dataKey="cabecas" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Piquetes + Manejos */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                <Card>
                    <CardHeader className="pb-2 flex flex-row items-center justify-between">
                        <CardTitle className="text-base">Piquetes — Lotação</CardTitle>
                        <Link href="/dashboard/pecuaria/piquetes" className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-0.5 transition-colors">
                            Ver todos <ChevronRight className="h-3 w-3" />
                        </Link>
                    </CardHeader>
                    <CardContent>
                        {activePiquetes.length === 0 ? (
                            <div className="py-8 text-center text-sm text-muted-foreground">
                                <MapPin className="h-8 w-8 mx-auto mb-2 opacity-40" />
                                Nenhum piquete cadastrado
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {activePiquetes.slice(0, 6).map(p => {
                                    const pct = p.lotPct ?? 0;
                                    const barColor = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-green-500";
                                    return (
                                        <div key={p.id}>
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="font-medium text-sm truncate">{p.nome}</span>
                                                <span className="text-xs text-muted-foreground shrink-0 ml-2">
                                                    {p.cabecas} cab. · {p.area_hectares ?? 0} ha
                                                </span>
                                            </div>
                                            {p.lotPct !== null ? (
                                                <div className="flex items-center gap-2">
                                                    <div className="flex-1 bg-muted rounded-full h-1.5">
                                                        <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                                                    </div>
                                                    <span className="text-xs text-muted-foreground w-8 text-right">{pct.toFixed(0)}%</span>
                                                </div>
                                            ) : (
                                                <div className="text-xs text-muted-foreground">Capacidade não definida</div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2 flex flex-row items-center justify-between">
                        <CardTitle className="text-base">Últimos Manejos</CardTitle>
                        <Link href="/dashboard/pecuaria/manejo" className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-0.5 transition-colors">
                            Ver todos <ChevronRight className="h-3 w-3" />
                        </Link>
                    </CardHeader>
                    <CardContent>
                        {recentManejos.length === 0 ? (
                            <div className="py-8 text-center text-sm text-muted-foreground">
                                <Syringe className="h-8 w-8 mx-auto mb-2 opacity-40" />
                                Nenhum manejo registrado
                            </div>
                        ) : (
                            <div className="space-y-2.5">
                                {recentManejos.map(m => {
                                    const cfg = EVENTO_CONFIG[m.tipo_evento] ?? { label: m.tipo_evento, color: "text-muted-foreground", icon: Activity };
                                    const Icon = cfg.icon;
                                    const lote = lotes.find(l => l.id === m.lote_id);
                                    return (
                                        <div key={m.id} className="flex items-start gap-3">
                                            <div className={`mt-0.5 shrink-0 ${cfg.color}`}>
                                                <Icon className="size-4" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-baseline justify-between gap-2">
                                                    <span className="text-sm font-medium">{cfg.label}</span>
                                                    <span className="text-xs text-muted-foreground shrink-0">{fmtDate(m.data_evento)}</span>
                                                </div>
                                                <div className="text-xs text-muted-foreground truncate">
                                                    {lote?.identificacao ?? "Lote desconhecido"}
                                                    {m.quantidade_cabecas ? ` — ${m.quantidade_cabecas} cab.` : ""}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
