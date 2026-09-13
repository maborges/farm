"use client";

import { use, useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { trackMonetizationEvent } from "@/lib/monetization";
import { getSafraLabel } from "@/lib/safra-label";
import {
    BarChart2, Download, ArrowLeft, TrendingUp, TrendingDown,
    DollarSign, Wheat, AlertCircle,
} from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell,
} from "recharts";
import { useHasTier } from "@/hooks/use-has-tier";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CenarioUnidade {
    id: string;
    production_unit_id: string;
    cultivo_nome: string | null;
    area_nome: string | null;
    area_ha: number;
    percentual_participacao: number;
    produtividade_efetiva: number | null;
    preco_efetivo: number | null;
    custo_ha_efetivo: number | null;
    producao_total: number | null;
    receita_bruta: number | null;
    custo_total: number | null;
    margem_contribuicao: number | null;
    margem_pct: number | null;
    ponto_equilibrio: number | null;
    custo_base_fonte: string | null;
}

interface ComparativoColuna {
    cenario_id: string;
    nome: string;
    tipo: string;
    eh_base: boolean;
    area_total_ha: number | null;
    receita_bruta_total: number | null;
    custo_total: number | null;
    margem_contribuicao_total: number | null;
    resultado_liquido_total: number | null;
    ponto_equilibrio_sc_ha: number | null;
    unidades: CenarioUnidade[];
}

interface CenarioListItem {
    id: string;
    nome: string;
    tipo: string;
    eh_base: boolean;
    status: string;
    receita_bruta_total: number | null;
    custo_total: number | null;
    margem_contribuicao_total: number | null;
    ponto_equilibrio_sc_ha: number | null;
}

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
    nome?: string | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// Cores via CSS custom properties — compatíveis com dark mode
// shadcn/ui define --chart-1..5 e --muted-foreground no tema
const CHART_COLORS = [
    "hsl(var(--chart-1))",
    "hsl(var(--chart-2))",
    "hsl(var(--chart-3))",
    "hsl(var(--chart-4))",
    "hsl(var(--chart-5))",
    "hsl(var(--chart-1) / 0.6)",
];
const BASE_COLOR = "hsl(var(--muted-foreground))";

const TIPO_BADGE: Record<string, string> = {
    BASE: "secondary",
    OTIMISTA: "default",
    PESSIMISTA: "destructive",
    CUSTOM: "outline",
};
const TIPO_LABEL: Record<string, string> = {
    BASE: "Base", OTIMISTA: "Otimista", PESSIMISTA: "Pessimista", CUSTOM: "Personalizado",
};

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

function fmtBRL(v: number | null): string {
    if (v === null || v === undefined) return "—";
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });
}

function fmtNum(v: number | null, dec = 3): string {
    if (v === null || v === undefined) return "—";
    return v.toLocaleString("pt-BR", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function fmtPct(v: number | null): string {
    if (v === null || v === undefined) return "—";
    return v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
}

function fmtSc(v: number | null): string {
    if (v === null || v === undefined) return "—";
    return fmtNum(v, 3) + " sc/ha";
}

function brlShort(v: number): string {
    if (Math.abs(v) >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1)}M`;
    if (Math.abs(v) >= 1_000) return `R$ ${(v / 1_000).toFixed(0)}K`;
    return `R$ ${v.toFixed(0)}`;
}

// ---------------------------------------------------------------------------
// Diff helpers — positivo = melhor que BASE
// ---------------------------------------------------------------------------

function diffClass(val: number | null, base: number | null, lowerIsBetter = false): string {
    if (val === null || base === null) return "";
    const diff = lowerIsBetter ? base - val : val - base;
    if (diff > 0.001) return "text-emerald-600 font-semibold";
    if (diff < -0.001) return "text-destructive font-semibold";
    return "";
}

// ---------------------------------------------------------------------------
// Chart component
// ---------------------------------------------------------------------------

interface KpiChartProps {
    title: string;
    field: keyof ComparativoColuna;
    data: ComparativoColuna[];
    formatter?: (v: number) => string;
    lowerIsBetter?: boolean;
}

function KpiChart({ title, field, data, formatter = brlShort }: KpiChartProps) {
    const chartData = data.map((c, i) => ({
        name: c.nome.length > 14 ? c.nome.slice(0, 13) + "…" : c.nome,
        value: (c[field] as number | null) ?? 0,
        fill: c.eh_base ? BASE_COLOR : CHART_COLORS[i % CHART_COLORS.length],
    }));

    return (
        <Card className="rounded-sm shadow-sm">
            <CardHeader className="pb-2 pt-4 px-4">
                <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
                <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                        <YAxis tickFormatter={formatter} tick={{ fontSize: 10 }} width={56} />
                        <Tooltip
                            formatter={(v: unknown) => formatter(v as number)}
                            contentStyle={{ fontSize: 12, borderRadius: 4 }}
                        />
                        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                            {chartData.map((entry, index) => (
                                <Cell key={index} fill={entry.fill} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function ProfessionalTierBlock({ safraId, safraLabel }: { safraId: string; safraLabel: string }) {
    useEffect(() => {
        trackMonetizationEvent("monetization_blocked", {
            feature: "agricola.cenarios.comparativo",
            surface: "agricola.cenarios.comparativo.page",
            requiredTier: "PROFISSIONAL",
        });
    }, [safraId]);

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title={`Comparativo de Cenários — ${safraLabel}`}
                icon={<BarChart2 className="text-purple-600" size={22} />}
                description="Disponível no plano Profissional."
            />
            <Card className="rounded-sm shadow-sm">
                <CardContent className="flex flex-col gap-3 p-4">
                    <div className="flex items-center gap-2 text-sm font-medium">
                        <AlertCircle className="size-4 text-muted-foreground" />
                        Plano Profissional necessário
                    </div>
                    <p className="text-sm text-muted-foreground">
                        A comparação multi-cenário e os indicadores lado a lado exigem o plano Profissional.
                    </p>
                    <Button variant="outline" size="sm" asChild className="w-fit">
                        <Link href={`/agricola/safras/${safraId}/cenarios`} aria-label="Voltar para Cenários" title="Voltar para Cenários">
                            <ArrowLeft className="size-3.5" />
                        </Link>
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}

function ComparativoContent({ id, safraLabel }: { id: string; safraLabel: string }) {
    const { data: cenarios = [], isLoading: isLoadingList } = useQuery<CenarioListItem[]>({
        queryKey: ["safra-cenarios-comparativo-list", id],
        queryFn: () => apiFetch(`/safras/${id}/cenarios`),
    });

    const baseId = useMemo(() => cenarios.find((c) => c.eh_base)?.id ?? null, [cenarios]);

    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    // Auto-select BASE when it loads
    const effectiveIds = useMemo(() => {
        const ids = new Set(selectedIds);
        if (baseId) ids.add(baseId);
        return ids;
    }, [selectedIds, baseId]);

    const idsArray = useMemo(() => Array.from(effectiveIds), [effectiveIds]);

    const { data: comparativo, isLoading: isLoadingComp, isError } = useQuery<{ cenarios: ComparativoColuna[] }>({
        queryKey: ["safra-comparativo", id, idsArray.join(",")],
        queryFn: () => {
            const params = new URLSearchParams();
            idsArray.forEach((id) => params.append("ids", id));
            return apiFetch(`/safras/${id}/cenarios/comparativo?${params.toString()}`);
        },
        enabled: idsArray.length >= 1 && !!baseId,
    });

    const colunas: ComparativoColuna[] = useMemo(() => comparativo?.cenarios ?? [], [comparativo]);
    const base = colunas.find((c) => c.eh_base) ?? null;

    // União de PU IDs das colunas para linhas da tabela detalhada
    const puIds = useMemo(() => {
        const ids = new Set<string>();
        colunas.forEach((c) => c.unidades?.forEach((u) => ids.add(u.production_unit_id)));
        return Array.from(ids);
    }, [colunas]);

    const getUnidade = (coluna: ComparativoColuna, puId: string): CenarioUnidade | null =>
        coluna.unidades?.find((u) => u.production_unit_id === puId) ?? null;

    const getPuLabel = (puId: string): string => {
        for (const c of colunas) {
            const u = c.unidades?.find((u) => u.production_unit_id === puId);
            if (u) return [u.cultivo_nome, u.area_nome].filter(Boolean).join(" / ") || puId.slice(0, 8);
        }
        return puId.slice(0, 8);
    };

    const toggleCenario = (cenarioId: string) => {
        if (cenarioId === baseId) return; // BASE é fixo
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(cenarioId)) next.delete(cenarioId);
            else next.add(cenarioId);
            return next;
        });
    };

    const nonBaseCenarios = cenarios.filter((c) => !c.eh_base && c.status === "ATIVO");

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title={`Comparativo de Cenários — ${safraLabel}`}
                icon={<BarChart2 className="text-purple-600" size={22} />}
                description="Análise lado a lado dos cenários econômicos da safra"
                actions={
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" asChild>
                            <Link href={`/agricola/safras/${id}/cenarios`} aria-label="Voltar" title="Voltar">
                                <ArrowLeft className="size-3.5" />
                            </Link>
                        </Button>
                        <Button variant="outline" size="sm" disabled title="Exportação PDF disponível em breve">
                            <Download className="size-3.5 mr-1.5" /> Exportar PDF
                        </Button>
                    </div>
                }
            />

            {/* Seleção de cenários */}
            {isLoadingList ? (
                <Skeleton className="h-16 w-full" />
            ) : nonBaseCenarios.length > 0 ? (
                <Card className="rounded-sm shadow-sm">
                    <CardContent className="px-4 py-3">
                        <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
                            Selecionar cenários para comparar
                        </p>
                        <div className="flex flex-wrap gap-4">
                            {/* BASE fixo */}
                            <div className="flex items-center gap-2 opacity-60 cursor-not-allowed">
                                <Checkbox id="cenario-base" checked disabled />
                                <Label htmlFor="cenario-base" className="text-sm cursor-not-allowed">
                                    {cenarios.find((c) => c.eh_base)?.nome ?? "Base"}
                                    <Badge variant="secondary" className="ml-1.5 text-[10px] h-4 rounded-sm">BASE</Badge>
                                </Label>
                            </div>
                            {nonBaseCenarios.map((c) => (
                                <div key={c.id} className="flex items-center gap-2">
                                    <Checkbox
                                        id={`cenario-${c.id}`}
                                        checked={effectiveIds.has(c.id)}
                                        onCheckedChange={() => toggleCenario(c.id)}
                                    />
                                    <Label htmlFor={`cenario-${c.id}`} className="text-sm cursor-pointer">
                                        {c.nome}
                                        <Badge
                                            variant={TIPO_BADGE[c.tipo] as "default" | "secondary" | "destructive" | "outline"}
                                            className="ml-1.5 text-[10px] h-4 rounded-sm"
                                        >
                                            {TIPO_LABEL[c.tipo] ?? c.tipo}
                                        </Badge>
                                    </Label>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            ) : null}

            {isLoadingComp && (
                <div className="space-y-4">
                    <Skeleton className="h-32 w-full" />
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-52 w-full" />)}
                    </div>
                </div>
            )}

            {isError && (
                <div className="flex items-center gap-2 text-destructive text-sm p-4 border border-destructive/30 rounded-sm bg-destructive/5">
                    <AlertCircle className="size-4" />
                    Erro ao carregar comparativo. Tente novamente.
                </div>
            )}

            {!isLoadingComp && colunas.length > 0 && (
                <>
                    {/* Tabela KPI lado a lado */}
                    <Card className="rounded-sm shadow-sm overflow-hidden">
                        <CardHeader className="pb-2 pt-4 px-4 border-b">
                            <CardTitle className="text-sm font-semibold">KPIs por Cenário</CardTitle>
                        </CardHeader>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-muted/40">
                                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-muted-foreground w-44">Indicador</th>
                                        {colunas.map((c) => (
                                            <th key={c.cenario_id} className="text-right px-4 py-2.5 text-xs font-semibold min-w-36">
                                                <div className="flex items-center justify-end gap-1.5">
                                                    {c.nome}
                                                    {c.eh_base && (
                                                        <Badge variant="secondary" className="text-[10px] h-4 rounded-sm">BASE</Badge>
                                                    )}
                                                </div>
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y">
                                    {/* Área — sem highlight (neutro) */}
                                    <tr className="hover:bg-muted/20">
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground font-medium">Área Total</td>
                                        {colunas.map((c) => (
                                            <td key={c.cenario_id} className="px-4 py-2.5 text-right tabular-nums text-xs text-muted-foreground">
                                                {c.area_total_ha ? fmtNum(c.area_total_ha, 2) + " ha" : "—"}
                                            </td>
                                        ))}
                                    </tr>
                                    {/* Receita */}
                                    <tr className="hover:bg-muted/20">
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                                            <TrendingUp className="size-3 text-emerald-500" /> Receita Bruta
                                        </td>
                                        {colunas.map((c) => (
                                            <td key={c.cenario_id} className={cn("px-4 py-2.5 text-right tabular-nums text-xs", !c.eh_base && diffClass(c.receita_bruta_total, base?.receita_bruta_total ?? null))}>
                                                {fmtBRL(c.receita_bruta_total)}
                                            </td>
                                        ))}
                                    </tr>
                                    {/* Custo */}
                                    <tr className="hover:bg-muted/20">
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                                            <TrendingDown className="size-3 text-destructive" /> Custo Total
                                        </td>
                                        {colunas.map((c) => (
                                            <td key={c.cenario_id} className={cn("px-4 py-2.5 text-right tabular-nums text-xs", !c.eh_base && diffClass(c.custo_total, base?.custo_total ?? null, true))}>
                                                {fmtBRL(c.custo_total)}
                                            </td>
                                        ))}
                                    </tr>
                                    {/* Margem */}
                                    <tr className="hover:bg-muted/20 bg-muted/10">
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                                            <DollarSign className="size-3 text-primary" /> Margem de Contribuição
                                        </td>
                                        {colunas.map((c) => {
                                            const pct = c.receita_bruta_total && c.margem_contribuicao_total
                                                ? (c.margem_contribuicao_total / c.receita_bruta_total * 100)
                                                : null;
                                            return (
                                                <td key={c.cenario_id} className={cn("px-4 py-2.5 text-right tabular-nums text-xs", !c.eh_base && diffClass(c.margem_contribuicao_total, base?.margem_contribuicao_total ?? null))}>
                                                    {fmtBRL(c.margem_contribuicao_total)}
                                                    {pct !== null && (
                                                        <span className="text-muted-foreground ml-1">({fmtPct(pct)})</span>
                                                    )}
                                                </td>
                                            );
                                        })}
                                    </tr>
                                    {/* Ponto de Equilíbrio */}
                                    <tr className="hover:bg-muted/20">
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                                            <Wheat className="size-3 text-amber-500" /> Ponto de Equilíbrio
                                        </td>
                                        {colunas.map((c) => (
                                            <td key={c.cenario_id} className={cn("px-4 py-2.5 text-right tabular-nums text-xs", !c.eh_base && diffClass(c.ponto_equilibrio_sc_ha, base?.ponto_equilibrio_sc_ha ?? null, true))}>
                                                {fmtSc(c.ponto_equilibrio_sc_ha)}
                                            </td>
                                        ))}
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </Card>

                    {/* 4 gráficos */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <KpiChart title="Receita Bruta" field="receita_bruta_total" data={colunas} />
                        <KpiChart title="Custo Total" field="custo_total" data={colunas} lowerIsBetter />
                        <KpiChart title="Margem de Contribuição" field="margem_contribuicao_total" data={colunas} />
                        <KpiChart
                            title="Ponto de Equilíbrio (sc/ha)"
                            field="ponto_equilibrio_sc_ha"
                            data={colunas}
                            formatter={(v) => fmtNum(v, 1)}
                            lowerIsBetter
                        />
                    </div>

                    {/* Legenda de cores */}
                    <div className="flex flex-wrap gap-3">
                        {colunas.map((c, i) => (
                            <div key={c.cenario_id} className="flex items-center gap-1.5">
                                <span
                                    className="inline-block size-3 rounded-sm"
                                    style={{ background: c.eh_base ? BASE_COLOR : CHART_COLORS[i % CHART_COLORS.length] }}
                                />
                                <span className="text-xs text-muted-foreground">{c.nome}</span>
                            </div>
                        ))}
                    </div>

                    {/* Detalhe por unidade produtiva */}
                    {puIds.length > 0 && (
                        <Card className="rounded-sm shadow-sm overflow-hidden">
                            <CardHeader className="pb-2 pt-4 px-4 border-b">
                                <CardTitle className="text-sm font-semibold">Detalhe por Unidade Produtiva</CardTitle>
                            </CardHeader>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="bg-muted/40">
                                            <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground w-40">Unidade / Indicador</th>
                                            {colunas.map((c) => (
                                                <th key={c.cenario_id} className="text-right px-4 py-2 text-xs font-semibold min-w-32">
                                                    {c.nome}
                                                    {c.eh_base && (
                                                        <Badge variant="secondary" className="ml-1.5 text-[10px] h-4 rounded-sm">BASE</Badge>
                                                    )}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y">
                                        {puIds.map((puId) => {
                                            const label = getPuLabel(puId);
                                            const baseUnidade = base ? getUnidade(base, puId) : null;

                                            type PuRow = {
                                                label: string;
                                                get: (u: CenarioUnidade) => number | null;
                                                fmt: (u: CenarioUnidade | null) => string;
                                                lowerBetter?: boolean;
                                            };
                                            const rows: PuRow[] = [
                                                { label: "Produtividade", get: (u) => u.produtividade_efetiva, fmt: (u) => u?.produtividade_efetiva ? fmtNum(u.produtividade_efetiva, 1) + " sc/ha" : "—" },
                                                { label: "Preço", get: (u) => u.preco_efetivo, fmt: (u) => fmtBRL(u?.preco_efetivo ?? null) },
                                                { label: "Custo/ha", get: (u) => u.custo_ha_efetivo, fmt: (u) => fmtBRL(u?.custo_ha_efetivo ?? null), lowerBetter: true },
                                                { label: "Receita", get: (u) => u.receita_bruta, fmt: (u) => fmtBRL(u?.receita_bruta ?? null) },
                                                { label: "Margem", get: (u) => u.margem_contribuicao, fmt: (u) => fmtBRL(u?.margem_contribuicao ?? null) },
                                                { label: "PE", get: (u) => u.ponto_equilibrio, fmt: (u) => fmtSc(u?.ponto_equilibrio ?? null), lowerBetter: true },
                                            ];

                                            return rows.map((row, rowIdx) => (
                                                <tr key={`${puId}-${row.label}`} className={cn("hover:bg-muted/20", rowIdx === 0 && "border-t-2 border-muted")}>
                                                    <td className="px-4 py-1.5 text-xs">
                                                        {rowIdx === 0
                                                            ? <span className="font-semibold">{label}</span>
                                                            : <span className="text-muted-foreground pl-3">{row.label}</span>
                                                        }
                                                    </td>
                                                    {colunas.map((c) => {
                                                        const u = getUnidade(c, puId);
                                                        if (rowIdx === 0) {
                                                            return <td key={c.cenario_id} className="px-4 py-1.5 text-xs text-right tabular-nums text-muted-foreground">{u?.area_ha ? fmtNum(u.area_ha, 2) + " ha" : "—"}</td>;
                                                        }
                                                        const val = u ? row.get(u) : null;
                                                        const baseVal = baseUnidade ? row.get(baseUnidade) : null;
                                                        return (
                                                            <td key={c.cenario_id} className={cn("px-4 py-1.5 text-xs text-right tabular-nums", !c.eh_base && diffClass(val, baseVal, row.lowerBetter))}>
                                                                {row.fmt(u)}
                                                            </td>
                                                        );
                                                    })}
                                                </tr>
                                            ));
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </Card>
                    )}
                </>
            )}

            {!isLoadingComp && !isLoadingList && !baseId && (
                <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground gap-3">
                    <BarChart2 className="size-8 opacity-30" />
                    <p className="text-sm">Nenhum cenário BASE encontrado.</p>
                    <Button variant="outline" size="sm" asChild>
                        <Link href={`/agricola/safras/${id}/cenarios`}>Ir para Cenários</Link>
                    </Button>
                </div>
            )}
        </div>
    );
}

export default function ComparativoPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    const { data: safra } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = safra ? getSafraLabel(safra) : "Safra";

    if (!hasProfessionalTier) {
        return <ProfessionalTierBlock safraId={id} safraLabel={safraLabel} />;
    }

    return <ComparativoContent id={id} safraLabel={safraLabel} />;
}
