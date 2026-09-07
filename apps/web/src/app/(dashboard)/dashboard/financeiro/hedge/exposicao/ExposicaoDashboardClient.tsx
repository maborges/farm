"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    ExposicaoConsolidada,
    ExposicaoConsolidadaItem,
    HedgeExposicao,
} from "../types";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Download, Info, AlertTriangle, ShieldAlert, TrendingDown } from "lucide-react";
import { ExposicaoHistoricoChart } from "./ExposicaoHistoricoChart";
import { SimulacaoPainel } from "./SimulacaoPainel";
import { useAppStore } from "@/lib/stores/app-store";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { RecomendacoesInteligentes } from "./RecomendacoesInteligentes";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Shield,
    TrendingUp,
    BarChart3,
    Package,
    Wheat,
    CircleDollarSign,
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { formatCurrency } from "@/lib/utils";

// ─── Helpers ────────────────────────────────────────────────────────────────

function fmt(val: number): string {
    return val.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}

type Classificacao = "DESCOBERTO" | "EQUILIBRADO" | "SOBREPROTEGIDO";

const RISCO_CONFIG: Record<
    Classificacao,
    { label: string; badge: "destructive" | "default" | "secondary"; icon: typeof Shield; colorClass: string; progressClass: string }
> = {
    DESCOBERTO: {
        label: "Descoberto",
        badge: "destructive",
        icon: AlertTriangle,
        colorClass: "text-red-600",
        progressClass: "bg-red-500",
    },
    EQUILIBRADO: {
        label: "Equilibrado",
        badge: "default",
        icon: Shield,
        colorClass: "text-emerald-600",
        progressClass: "bg-emerald-500",
    },
    SOBREPROTEGIDO: {
        label: "Sobreprotegido",
        badge: "secondary",
        icon: TrendingUp,
        colorClass: "text-amber-600",
        progressClass: "bg-amber-500",
    },
};

// ─── Sub-componentes ─────────────────────────────────────────────────────────

export function RiscoBadge({ classificacao }: { classificacao: Classificacao }) {
    const cfg = RISCO_CONFIG[classificacao];
    const Icon = cfg.icon;
    return (
        <Badge variant={cfg.badge} className="gap-1 text-xs rounded-sm">
            <Icon className="h-3 w-3" />
            {cfg.label}
        </Badge>
    );
}

function KpiCard({
    label,
    value,
    sublabel,
    icon: Icon,
    loading,
    colorClass,
}: {
    label: string;
    value: string;
    sublabel?: string;
    icon: typeof Shield;
    loading: boolean;
    colorClass?: string;
}) {
    let v: "default" | "blue" | "emerald" | "red" | "amber" = "default";
    if (colorClass === "text-blue-600") v = "blue";
    if (colorClass === "text-emerald-600") v = "emerald";
    if (colorClass === "text-red-600") v = "red";
    if (colorClass === "text-amber-600") v = "amber";
    
    const styles = {
        default: { border: "border-l-border/70", title: "text-muted-foreground", value: "text-foreground" },
        blue: { border: "border-l-blue-500/80", title: "text-blue-700/70", value: "text-blue-700" },
        emerald: { border: "border-l-emerald-500/80", title: "text-emerald-700/70", value: "text-emerald-700" },
        red: { border: "border-l-red-500/80", title: "text-red-700/70", value: "text-red-700" },
        amber: { border: "border-l-amber-500/80", title: "text-amber-700/80", value: "text-amber-700" },
    }[v];

    return (
        <Card className={`rounded-sm border-l-4 ${styles.border}`}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className={`text-[10px] font-black uppercase tracking-[0.24em] ${styles.title}`}>{label}</CardTitle>
                <Icon className={`h-4 w-4 ${styles.title}`} />
            </CardHeader>
            <CardContent>
                {loading ? (
                    <Skeleton className="h-8 w-28 rounded-sm" />
                ) : (
                    <>
                        <div className={`text-3xl font-black tabular-nums ${styles.value}`}>{value}</div>
                        {sublabel && <p className="text-xs text-muted-foreground mt-0.5 font-medium">{sublabel}</p>}
                    </>
                )}
            </CardContent>
        </Card>
    );
}

function CoberturaGauge({
    percentual,
    classificacao,
}: {
    percentual: number;
    classificacao: Classificacao;
}) {
    const cfg = RISCO_CONFIG[classificacao];
    const clamped = Math.min(percentual, 100);

    return (
        <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Cobertura Financeira</span>
                <span className={`font-bold text-lg tabular-nums ${cfg.colorClass}`}>
                    {percentual.toFixed(1)}%
                </span>
            </div>
            <div className="relative h-3 w-full rounded-full bg-muted overflow-hidden">
                <div
                    className={`absolute left-0 top-0 h-full rounded-full transition-all duration-500 ${cfg.progressClass}`}
                    style={{ width: `${clamped}%` }}
                />
                {/* Marcador dos limites */}
                <div className="absolute left-[70%] top-0 h-full w-px bg-amber-400 opacity-60" />
                <div className="absolute left-[100%] top-0 h-full w-px bg-red-400 opacity-60" />
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>0%</span>
                <span className="text-amber-600">70%</span>
                <span className="text-red-500">110%</span>
            </div>
        </div>
    );
}

// ─── Tabela de Consolidado ───────────────────────────────────────────────────

function TabelaConsolidado({ itens }: { itens: ExposicaoConsolidadaItem[] }) {
    if (!itens.length) {
        return (
            <p className="text-sm text-muted-foreground text-center py-8">
                Nenhuma safra com meta de produção cadastrada.
            </p>
        );
    }

    return (
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead className="text-xs">Safra</TableHead>
                    <TableHead className="text-xs">Commodity</TableHead>
                    <TableHead className="text-xs text-right">Exp. Bruta (sc)</TableHead>
                    <TableHead className="text-xs text-right">Vendido (sc)</TableHead>
                    <TableHead className="text-xs text-right">Hedgeado (sc)</TableHead>
                    <TableHead className="text-xs text-right">Aberta (sc)</TableHead>
                    <TableHead className="text-xs text-right">Cobertura</TableHead>
                    <TableHead className="text-xs text-center">Risco</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {itens.map((item, i) => (
                    <TableRow key={i} className="text-sm">
                        <TableCell className="font-medium">{item.ano_safra ?? "—"}</TableCell>
                        <TableCell>{item.commodity ?? "—"}</TableCell>
                        <TableCell className="text-right tabular-nums">{fmt(item.exposicao_bruta_sc)}</TableCell>
                        <TableCell className="text-right tabular-nums text-blue-600">{fmt(item.ja_vendido_sc)}</TableCell>
                        <TableCell className="text-right tabular-nums text-emerald-600">{fmt(item.ja_hedgeado_sc)}</TableCell>
                        <TableCell className="text-right tabular-nums font-semibold">{fmt(item.exposicao_aberta_sc)}</TableCell>
                        <TableCell className="text-right tabular-nums">{item.percentual_cobertura.toFixed(1)}%</TableCell>
                        <TableCell className="text-center">
                            <RiscoBadge classificacao={item.classificacao_risco} />
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    );
}

// ─── Client Component Principal ──────────────────────────────────────────────

import { PlanTierId } from "@/types/global";

export function ExposicaoDashboardClient({
    initialConsolidado,
    planTier,
}: {
    initialConsolidado: ExposicaoConsolidada | null;
    planTier: PlanTierId;
}) {
    const { data: consolidado, isLoading } = useQuery<ExposicaoConsolidada>({
        queryKey: ["financeiro", "hedge", "exposicao", "consolidado"],
        queryFn: () => apiFetch("/financeiro/hedge/exposicao/consolidado"),
        initialData: initialConsolidado ?? undefined,
        staleTime: 60 * 1000,
    });

    const { data: exposicao, isLoading: expLoading } = useQuery<HedgeExposicao>({
        queryKey: ["financeiro", "hedge", "exposicao"],
        queryFn: () => apiFetch("/financeiro/hedge/exposicao"),
        staleTime: 60 * 1000,
    });

    const loading = isLoading || expLoading;
    const risco = consolidado?.classificacao_risco_global ?? "DESCOBERTO";

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Exposição Física × Financeira"
                description="Visão analítica da cobertura comercial e risco de preço"
                breadcrumbs={[{ label: "Financeiro", href: "/dashboard/financeiro" }, { label: "Hedge" }, { label: "Exposição" }]}
                icon={<ShieldAlert className="text-primary" size={22} />}
            />

            {/* ── Indicador de Risco Global ── */}
            <Card className="rounded-sm border-0 shadow-sm bg-gradient-to-r from-card to-muted/30">
                <CardContent className="pt-6">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                        <div className="space-y-1">
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">
                                Classificação de Risco Global
                            </p>
                            {loading ? (
                                <Skeleton className="h-8 w-40 rounded-sm" />
                            ) : (
                                <div className="flex items-center gap-3">
                                    <span className="text-3xl font-bold">
                                        {consolidado?.percentual_cobertura_global.toFixed(1) ?? "0.0"}%
                                    </span>
                                    <RiscoBadge classificacao={risco} />
                                </div>
                            )}
                            <p className="text-xs text-muted-foreground">
                                coberto · {RISCO_CONFIG[risco].label.toLowerCase()}
                            </p>
                        </div>
                        <div className="md:w-1/2">
                            {loading ? (
                                <Skeleton className="h-10 w-full rounded-sm" />
                            ) : (
                                <CoberturaGauge
                                    percentual={consolidado?.percentual_cobertura_global ?? 0}
                                    classificacao={risco}
                                />
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Tabs defaultValue="geral" className="w-full">
                <TabsList className="mb-4">
                    <TabsTrigger value="geral">Visão Geral</TabsTrigger>
                    <TabsTrigger value="simulador">Simulador (ENTERPRISE)</TabsTrigger>
                </TabsList>
                
                <TabsContent value="geral" className="space-y-6 mt-6">
                    {/* ── Recomendações Inteligentes (ENTERPRISE) ── */}
                    {planTier === "ENTERPRISE" && (
                        <RecomendacoesInteligentes />
                    )}

                    {/* ── KPIs: Exposição Física ── */}
                    <div>
                        <h3 className="text-sm font-semibold tracking-tight text-muted-foreground uppercase mb-3">
                            Exposição Física
                        </h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <KpiCard
                                label="Produção Estimada"
                                value={`${fmt(exposicao?.producao_estimada_sc ?? 0)} sc`}
                                icon={Wheat}
                                loading={expLoading}
                            />
                            <KpiCard
                                label="Estoque Físico"
                                value={`${fmt(exposicao?.estoque_fisico_sc ?? 0)} sc`}
                                sublabel="commodities em armazém"
                                icon={Package}
                                loading={expLoading}
                            />
                            <KpiCard
                                label="Exposição Bruta"
                                value={`${fmt(exposicao?.exposicao_bruta_sc ?? 0)} sc`}
                                sublabel="produção + estoque"
                                icon={BarChart3}
                                loading={expLoading}
                            />
                            <KpiCard
                                label="Compromissos Físicos"
                                value={`${fmt(exposicao?.ja_vendido_sc ?? 0)} sc`}
                                sublabel="vendas confirmadas/entregues"
                                icon={CircleDollarSign}
                                colorClass="text-blue-600"
                                loading={expLoading}
                            />
                        </div>
                    </div>

                    {/* ── KPIs: Cobertura Financeira ── */}
                    <div>
                        <h3 className="text-sm font-semibold tracking-tight text-muted-foreground uppercase mb-3">
                            Proteção Financeira
                        </h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <KpiCard
                                label="Proteção Financeira"
                                value={`${fmt(exposicao?.ja_hedgeado_sc ?? 0)} sc`}
                                sublabel="contratos futuros abertos"
                                icon={Shield}
                                colorClass="text-emerald-600"
                                loading={expLoading}
                            />
                            <KpiCard
                                label="Exposição Líquida"
                                value={`${fmt(exposicao?.exposicao_liquida_sc ?? 0)} sc`}
                                sublabel="bruta − compromissos"
                                icon={BarChart3}
                                loading={expLoading}
                            />
                            <KpiCard
                                label="Exposição Aberta"
                                value={`${fmt(exposicao?.exposicao_aberta_sc ?? 0)} sc`}
                                sublabel="sem cobertura financeira"
                                icon={AlertTriangle}
                                colorClass={
                                    (exposicao?.exposicao_aberta_sc ?? 0) > 0
                                        ? "text-red-600"
                                        : "text-emerald-600"
                                }
                                loading={expLoading}
                            />
                            <KpiCard
                                label="Hedge Ratio"
                                value={`${((exposicao?.hedge_ratio ?? 0) * 100).toFixed(1)}%`}
                                sublabel="proteção / exposição liq."
                                icon={TrendingDown}
                                loading={expLoading}
                            />
                        </div>
                    </div>

                    {/* ── Gráfico Histórico de Exposição (ENTERPRISE) ── */}
                    <ExposicaoHistoricoChart />

                    {/* ── Tabela Consolidada por Safra / Commodity ── */}
                    <Card className="rounded-sm">
                        <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
                            <CardTitle className="text-sm font-semibold">
                                Consolidado por Safra e Commodity
                            </CardTitle>
                            <Button variant="outline" size="sm" className="h-8 text-xs font-normal">
                                <Download className="size-3.5 mr-1.5" />
                                Exportar
                            </Button>
                        </CardHeader>
                        <CardContent>
                            {loading ? (
                                <div className="space-y-2">
                                    {[1, 2, 3].map((i) => (
                                        <Skeleton key={i} className="h-10 w-full rounded-sm" />
                                    ))}
                                </div>
                            ) : (
                                <TabelaConsolidado
                                    itens={consolidado?.por_safra_commodity ?? []}
                                />
                            )}
                        </CardContent>
                    </Card>

                    {/* ── Totais Globais ── */}
                    {consolidado && (
                        <Card className="rounded-sm bg-muted/30">
                            <CardContent className="pt-4 pb-4">
                                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                                    <div>
                                        <p className="text-xs text-muted-foreground">Exp. Bruta Total</p>
                                        <p className="font-bold tabular-nums">{fmt(consolidado.total_exposicao_bruta_sc)} sc</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground">Compromissos</p>
                                        <p className="font-bold tabular-nums text-blue-600">{fmt(consolidado.total_compromissos_sc)} sc</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground">Proteção</p>
                                        <p className="font-bold tabular-nums text-emerald-600">{fmt(consolidado.total_protecao_sc)} sc</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground">Aberta (sem cobertura)</p>
                                        <p className="font-bold tabular-nums text-red-600">{fmt(consolidado.total_exposicao_aberta_sc)} sc</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground">Cobertura Global</p>
                                        <p className={`font-bold tabular-nums ${RISCO_CONFIG[risco].colorClass}`}>
                                            {consolidado.percentual_cobertura_global.toFixed(1)}%
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>

                <TabsContent value="simulador" className="space-y-8 mt-6">
                    {planTier === "ENTERPRISE" ? (
                        <SimulacaoPainel />
                    ) : (
                        <div className="max-w-2xl mx-auto pt-8">
                            <TierUpgradeCard 
                                title="Simulador de Exposição Físico-Financeira" 
                                description="Acesse nossa ferramenta preditiva para criar cenários (what-if) sobre a produção, vendas e hedge futuro, projetando instantaneamente o impacto no risco de caixa da fazenda." 
                                requiredTier="ENTERPRISE" 
                                feature="hedge_simulator" 
                                surface="hedge_dashboard" 
                            />
                        </div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}
