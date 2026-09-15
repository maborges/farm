"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SafrasKanban } from "@/components/agricola/safras-kanban";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
    AlertTriangle, Bell, Bug, ArrowRight, TrendingUp, Sprout,
    DollarSign, RefreshCw, LayoutDashboard, Target, Lock
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { useHasTier } from "@/hooks/use-has-tier";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";
import { useAppStore } from "@/lib/stores/app-store";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    Cell
} from "recharts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DashboardData {
    kpis: {
        total_safras_ativas: number;
        total_safras_encerradas: number;
        area_total_ha: number;
        custo_acumulado: number;
        meta_producao_sc: number;
        sacas_colhidas: number;
        receita_colheita: number;
        total_alertas: number;
    };
    safras_por_fase: Record<string, Array<{
        id: string;
        cultura: string | null;
        ano_safra: string;
        status: string;
    }>>;
    alertas_checklist: {
        safra_id: string;
        safra: string;
        fase: string;
        pendentes: number;
        severidade: "CRITICO" | "AVISO";
    }[];
    alertas_nde: {
        safra_id: string;
        safra: string;
        agente: string;
        nivel: number;
        nde: number;
        data: string;
        severidade: "CRITICO";
    }[];
    fenologia_atual: {
        safra_id: string;
        safra: string;
        estagio_codigo: string | null;
        estagio_nome: string | null;
        data_observacao: string | null;
    }[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const FASE_LABEL: Record<string, string> = {
    PLANEJADA: "Planejamento",
    PREPARO_SOLO: "Preparo Solo",
    PLANTIO: "Plantio",
    DESENVOLVIMENTO: "Desenvolvimento",
    COLHEITA: "Colheita",
    POS_COLHEITA: "Pós-Colheita",
};

function fmt(d: string) {
    return format(new Date(d + "T12:00:00"), "dd/MM/yy", { locale: ptBR });
}

function fmtBRL(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function getPrimarySafraId(safrasPorFase: DashboardData["safras_por_fase"]) {
    const phaseOrder = ["PLANEJADA", "PREPARO_SOLO", "PLANTIO", "DESENVOLVIMENTO", "COLHEITA", "POS_COLHEITA"];

    for (const phase of phaseOrder) {
        const safra = safrasPorFase[phase]?.[0];
        if (safra?.id) return safra.id;
    }

    for (const safraList of Object.values(safrasPorFase)) {
        const safra = safraList[0];
        if (safra?.id) return safra.id;
    }

    return null;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProductionChart({ kpis }: { kpis: DashboardData["kpis"] }) {
    const data = [
        { name: "Meta", valor: kpis.meta_producao_sc, color: "#94a3b8" },
        { name: "Colhido", valor: kpis.sacas_colhidas, color: "#10b981" }
    ];
    const hasData = kpis.meta_producao_sc > 0 || kpis.sacas_colhidas > 0;

    return (
        <Card className="shadow-md hover:shadow-lg transition-shadow duration-200 rounded-lg flex flex-col">
            <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold">Produção vs Meta</CardTitle>
                <CardDescription className="text-sm">Acompanhamento de sacas em relação ao objetivo</CardDescription>
            </CardHeader>
            <CardContent className="flex-1">
                {hasData ? (
                    <div className="h-[180px] w-full mt-4 relative">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                                data={data}
                                layout="vertical"
                                margin={{ left: 10, right: 30, top: 0, bottom: 0 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} strokeOpacity={0.1} />
                                <XAxis type="number" hide />
                                <YAxis
                                    dataKey="name"
                                    type="category"
                                    axisLine={false}
                                    tickLine={false}
                                    width={70}
                                    className="text-[11px] font-bold fill-foreground"
                                />
                                <Tooltip
                                    cursor={{ fill: "rgba(0,0,0,0.05)" }}
                                    contentStyle={{ borderRadius: "4px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)", fontSize: "11px" }}
                                    isAnimationActive={false}
                                />
                                <Bar
                                    dataKey="valor"
                                    radius={[0, 4, 4, 0]}
                                    barSize={24}
                                    isAnimationActive={false}
                                >
                                    {data.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                ) : (
                    <div className="h-[180px] flex flex-col items-center justify-center text-center p-4">
                        <div className="size-10 rounded-full bg-muted flex items-center justify-center mb-3">
                            <TrendingUp className="size-5 text-muted-foreground opacity-50" />
                        </div>
                        <p className="text-xs font-bold text-foreground">Sem dados de produção</p>
                        <p className="text-[10px] text-muted-foreground mt-1 max-w-[150px]">
                            Defina uma meta ou registre colheitas para visualizar o progresso.
                        </p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function PrimaryKPIs({ kpis }: { kpis: DashboardData["kpis"] }) {
    const pct = kpis.meta_producao_sc > 0
        ? Math.min(100, Math.round((kpis.sacas_colhidas / kpis.meta_producao_sc) * 100))
        : 0;

    const items = [
        {
            label: "Safras Ativas",
            value: kpis.total_safras_ativas.toString(),
            sub: `${kpis.total_safras_encerradas} encerradas`,
            icon: Sprout,
            color: "text-emerald-600",
            bg: "bg-emerald-100 dark:bg-emerald-900/30",
        },
        {
            label: "Área Total",
            value: `${kpis.area_total_ha.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} ha`,
            sub: "Hectares em produção",
            icon: Target,
            color: "text-blue-600",
            bg: "bg-blue-100 dark:bg-blue-900/30",
        },
        {
            label: "Custo Acumulado",
            value: fmtBRL(kpis.custo_acumulado),
            sub: "Insumos e serviços",
            icon: DollarSign,
            color: "text-amber-600",
            bg: "bg-amber-100 dark:bg-amber-900/30",
        },
        {
            label: "Sacas Colhidas",
            value: kpis.sacas_colhidas.toLocaleString("pt-BR", { maximumFractionDigits: 0 }),
            sub: pct > 0 ? `${pct}% da meta` : "Sem meta",
            icon: TrendingUp,
            color: "text-emerald-600",
            bg: "bg-emerald-100 dark:bg-emerald-900/30",
        },
    ];

    return (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {items.map((item) => (
                <Card key={item.label} className="shadow-md hover:shadow-lg transition-all duration-200 rounded-lg hover:-translate-y-0.5">
                    <CardContent className="p-6 flex items-start gap-4">
                        <div className={cn("size-11 rounded-lg flex items-center justify-center shrink-0", item.bg)}>
                            <item.icon className={cn("size-5", item.color)} />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">{item.label}</p>
                            <p className="text-3xl font-black tabular-nums tracking-tight mt-1">{item.value}</p>
                            <p className="text-xs text-muted-foreground mt-2 font-medium">{item.sub}</p>
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}

function AlertasSection({
    checklist,
    nde,
}: {
    checklist: DashboardData["alertas_checklist"];
    nde: DashboardData["alertas_nde"];
}) {
    const hasChecklist = checklist.length > 0;
    const hasNDE = nde.length > 0;
    const totalAlertas = checklist.length + nde.length;

    if (!hasChecklist && !hasNDE) return null;

    return (
        <Card className="shadow-md hover:shadow-lg transition-all duration-200 rounded-lg border-amber-200/50 dark:border-amber-900/30">
            <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                    <div className="size-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0">
                        <AlertTriangle className="size-5 text-amber-600" aria-hidden="true" />
                    </div>
                    <div>
                        <CardTitle className="text-lg font-bold">Central de Alertas</CardTitle>
                        <CardDescription className="text-sm">
                            {totalAlertas} ocorrência{totalAlertas !== 1 ? "s" : ""} ativa{totalAlertas !== 1 ? "s" : ""}
                        </CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                <Tabs defaultValue={hasChecklist ? "checklist" : "nde"}>
                    <TabsList className="w-full justify-start rounded-none h-10 bg-muted/30 px-4 border-b">
                        <TabsTrigger value="checklist" disabled={!hasChecklist} className="rounded-none text-xs font-bold uppercase tracking-wider">
                            Checklist ({checklist.length})
                        </TabsTrigger>
                        <TabsTrigger value="nde" disabled={!hasNDE} className="rounded-none text-xs font-bold uppercase tracking-wider">
                            NDE - Pragas ({nde.length})
                        </TabsTrigger>
                    </TabsList>

                    <div className="p-4 space-y-2">
                        <TabsContent value="checklist" className="mt-0 space-y-2">
                            {checklist.map((a, i) => (
                                <div
                                    key={i}
                                    className={cn(
                                        "flex items-center gap-3 px-4 py-2.5 rounded-sm border text-sm",
                                        a.severidade === "CRITICO"
                                            ? "bg-red-50 border-red-200 dark:bg-red-950/20"
                                            : "bg-amber-50 border-amber-200 dark:bg-amber-950/20"
                                    )}
                                >
                                    <div className={cn("size-2 rounded-full", a.severidade === "CRITICO" ? "bg-red-500" : "bg-amber-500")} />
                                    <span className="flex-1 min-w-0">
                                        <span className="font-bold">{a.safra}</span>
                                        <span className="text-muted-foreground"> — {a.pendentes} pendência(s) em </span>
                                        <span className="font-semibold">{FASE_LABEL[a.fase] ?? a.fase}</span>
                                    </span>
                                    <Badge
                                        variant="outline"
                                        className={cn(
                                            "text-[10px] shrink-0 rounded-sm font-black h-5",
                                            a.severidade === "CRITICO"
                                                ? "text-red-700 border-red-300 bg-white dark:bg-transparent"
                                                : "text-amber-700 border-amber-300 bg-white dark:bg-transparent"
                                        )}
                                    >
                                        {a.severidade}
                                    </Badge>
                                </div>
                            ))}
                        </TabsContent>

                        <TabsContent value="nde" className="mt-0 space-y-2">
                            {nde.map((a, i) => (
                                <div
                                    key={i}
                                    className="flex items-center gap-3 px-4 py-2.5 rounded-sm bg-red-50 border border-red-200 text-sm dark:bg-red-950/20"
                                >
                                    <Bug className="size-4 shrink-0 text-red-500" />
                                    <span className="flex-1 min-w-0">
                                        <span className="font-bold">{a.safra}</span>
                                        <span className="text-muted-foreground"> — </span>
                                        <span className="font-bold text-red-600">{a.agente}</span>
                                        <span className="text-xs opacity-70 ml-2">nv {a.nivel} ≥ NDE {a.nde}</span>
                                    </span>
                                    <Badge variant="outline" className="text-[10px] text-red-700 border-red-300 shrink-0 rounded-sm font-black bg-white dark:bg-transparent h-5">
                                        CONTROLE
                                    </Badge>
                                </div>
                            ))}
                        </TabsContent>
                    </div>
                </Tabs>
            </CardContent>
        </Card>
    );
}

function FenologiaGrid({ data }: { data: DashboardData["fenologia_atual"] }) {
    if (data.length === 0) return null;

    return (
        <Card className="shadow-md hover:shadow-lg transition-all duration-200 rounded-lg">
            <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold">Estágios Fenológicos</CardTitle>
                <CardDescription className="text-sm">Últimas observações em campo</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="grid gap-2 grid-cols-1">
                    {data.map((f, i) => (
                        <div key={i} className="flex items-center gap-3 px-3 py-2.5 border border-border rounded-lg hover:bg-muted/50 hover:border-border/60 transition-all duration-200 group cursor-default">
                            <div className="size-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center shrink-0">
                                <span className="text-sm font-black text-emerald-700 dark:text-emerald-400">
                                    {f.estagio_codigo ?? "?"}
                                </span>
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-semibold truncate text-foreground">{f.safra}</p>
                                <p className="text-xs text-muted-foreground font-medium mt-0.5 truncate">
                                    {f.estagio_nome ?? "Intermediário"}
                                    {f.data_observacao && <span className="text-muted-foreground"> • {fmt(f.data_observacao)}</span>}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardAgricolaPage() {
    const token = useAppStore((s) => s.token);
    const hasHydrated = useAppStore((s) => s._hasHydrated);
    const isReady = hasHydrated && !!token;
    const authHeaders = token ? { Authorization: `Bearer ${token}` } : undefined;
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    useMonetizationPromptTracking(!hasProfessionalTier, {
        feature: "agricola.dashboard.alertas",
        surface: "agricola.dashboard.page",
        requiredTier: "PROFISSIONAL",
        ctaLabel: "Ver planos",
    });
    const { data, isLoading, error, refetch } = useQuery<DashboardData>({
        queryKey: ["agricola-dashboard", token],
        queryFn: () => {
            if (!token) {
                throw new Error("Sessão não disponível para carregar o dashboard.");
            }
            console.log("🌾 DashboardAgricolaPage token status", {
                hasToken: Boolean(token),
                tokenPrefix: token.slice(0, 16),
            });
            return apiFetch("/agricola/dashboard/", {
                headers: { Authorization: `Bearer ${token}` },
            });
        },
        enabled: isReady,
        refetchInterval: 5 * 60 * 1000,
        retry: false,
    });

    const alertaMutation = useMutation({
        mutationFn: () => {
            if (!hasProfessionalTier) {
                trackMonetizationEvent("monetization_blocked", {
                    feature: "agricola.dashboard.alerts_refresh",
                    surface: "agricola.dashboard.page",
                    requiredTier: "PROFISSIONAL",
                    ctaLabel: "Verificar Alertas",
                    reason: "mutation_guard",
                });
                throw new Error("Recurso disponível no plano PROFISSIONAL.");
            }
            return apiFetch("/agricola/dashboard/verificar-alertas", {
                method: "POST",
                headers: authHeaders,
            });
        },
        onSuccess: () => {
            toast.success("Verificação de alertas iniciada.");
            setTimeout(() => refetch(), 3000);
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao verificar alertas."),
    });

    if (!isReady || isLoading) {
        return (
            <div className="space-y-6 p-6">
                <Skeleton className="h-10 w-64" />
                <div className="grid grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map((i) => (
                        <Skeleton key={i} className="h-28 rounded-sm" />
                    ))}
                </div>
                <Skeleton className="h-64 w-full rounded-sm" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <Alert className="rounded-sm border-destructive/30">
                    <AlertTriangle className="size-4" />
                    <AlertTitle>Falha ao carregar o Painel de Safras</AlertTitle>
                    <AlertDescription className="space-y-3">
                        <p>{error instanceof Error ? error.message : "Erro de autenticação ao consultar o dashboard."}</p>
                        <Button size="sm" onClick={() => refetch()}>
                            <RefreshCw className="size-4 mr-1.5" />
                            Tentar novamente
                        </Button>
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    if (!data) return null;

    const primarySafraId = getPrimarySafraId(data.safras_por_fase);
    const estoqueHref = primarySafraId ? `/agricola/safras/${primarySafraId}/estoque` : "/agricola/safras";

    return (
        <div className="p-6 space-y-8">
            {/* ── Header ── */}
            <PageHeader
                title="Painel Agrícola"
                description="Visão consolidada de safras, custos, produção e alertas"
                icon={<LayoutDashboard className="size-6 text-primary" />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Dashboard" }]}
                actions={
                    <div className="flex gap-2">
                        <Button size="sm" onClick={() => refetch()} aria-label="Atualizar dashboard">
                            <RefreshCw className="size-4 mr-1.5" />
                            Atualizar
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => alertaMutation.mutate()}
                            disabled={!hasProfessionalTier || alertaMutation.isPending}
                        >
                            <Bell className="size-4 mr-1.5" />
                            Verificar Alertas
                        </Button>
                    </div>
                }
            />

            {!hasProfessionalTier && (
                <Alert className="rounded-sm">
                    <Lock className="size-4" />
                    <AlertTitle>Alertas inteligentes disponíveis no PROFISSIONAL</AlertTitle>
                    <AlertDescription className="space-y-3">
                        <p>
                            A visão operacional agrícola continua disponível. A verificação automática de alertas exige plano Profissional.
                        </p>
                        <Button
                            asChild
                            size="sm"
                            className="rounded-sm"
                            onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                                feature: "agricola.dashboard.alertas",
                                surface: "agricola.dashboard.page",
                                requiredTier: "PROFISSIONAL",
                                ctaLabel: "Ver planos",
                            })}
                        >
                            <Link href="/dashboard/settings/billing">Ver planos</Link>
                        </Button>
                    </AlertDescription>
                </Alert>
            )}

            {/* ── KPIs primários ── */}
            <PrimaryKPIs kpis={data.kpis} />

            {/* ── Main Dashboard Grid ── */}
            <div className="grid gap-6 lg:grid-cols-3 items-start auto-rows-max">
                {/* Lateral: Charts e Fenologia */}
                <div className="space-y-6 min-w-0">
                    <ProductionChart kpis={data.kpis} />

                    <Card className="shadow-md hover:shadow-lg transition-all duration-200 rounded-lg">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base font-bold">Dados Financeiros</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="bg-emerald-50 dark:bg-emerald-950/20 p-4 rounded-lg border border-emerald-100 dark:border-emerald-900/30 hover:border-emerald-200 dark:hover:border-emerald-800/50 transition-colors">
                                <p className="text-xs font-bold text-emerald-600 uppercase tracking-widest">Receita de Colheita</p>
                                <p className="text-2xl font-black text-emerald-700 dark:text-emerald-400 mt-2">{fmtBRL(data.kpis.receita_colheita)}</p>
                            </div>
                            <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider px-3 py-2 bg-muted/40 rounded-lg">
                                <span className="text-muted-foreground">ROI Estimado</span>
                                <span className="text-emerald-600">+12.4%</span>
                            </div>
                        </CardContent>
                    </Card>

                    <FenologiaGrid data={data.fenologia_atual} />
                </div>

                {/* Centro: Kanban e Alertas */}
                <div className="lg:col-span-2 space-y-6 min-w-0">
                    <Card className="shadow-md hover:shadow-lg transition-all duration-200 rounded-lg">
                        <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
                            <div className="flex flex-row items-center gap-2">
                                <Sprout className="size-5 text-emerald-600" />
                                <CardTitle className="text-lg font-bold">Acompanhamento de Safras
                                </CardTitle>
                                <CardDescription className="text-xs">Fluxo visual por estágio de produção</CardDescription>
                            </div>
                            <Link href="/agricola/safras">
                                <Button variant="ghost" size="sm">
                                    Detalhes das Safras <ArrowRight className="size-3 ml-1" />
                                </Button>
                            </Link>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <SafrasKanban safrasPorFase={data.safras_por_fase} />
                        </CardContent>
                    </Card>

                    <AlertasSection checklist={data.alertas_checklist} nde={data.alertas_nde} />
                </div>
            </div>

            {/* ── Atalhos no rodapé ── */}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {[
                    { label: "Caderno de Campo", sub: "Atividades diárias", href: "/agricola/caderno" },
                    { label: "Operações do Campo", sub: "Registro e histórico operacional", href: "/agricola/operacoes" },
                    { label: "Insumos", sub: "Estoque e aplicações", href: estoqueHref },
                    { label: "Financeiro", sub: "Custos e ROI", href: "/financeiro" },
                ].map((link, i) => (
                    <Link key={i} href={link.href} className="flex flex-col p-4 bg-card border rounded-sm hover:border-primary transition-all group">
                        <p className="text-sm font-bold tracking-tight">{link.label}</p>
                        <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider mt-0.5">{link.sub}</p>
                    </Link>
                ))}
            </div>
        </div>
    );
}
