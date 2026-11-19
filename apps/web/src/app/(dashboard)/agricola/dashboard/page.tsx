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
import { QuickActionGrid, QuickActionItem } from "@/components/ui/quick-action-grid";
import {
    AlertTriangle, Bell, Bug, ArrowRight, TrendingUp, Sprout,
    DollarSign, RefreshCw, LayoutDashboard, Target, Lock,
    ClipboardList, MapPin, Package, BookOpen, CheckCircle2, Wheat
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
        <Card className="shadow-xs border border-border/70 rounded-sm flex flex-col">
            <CardHeader className="pb-3 border-b border-border/40">
                <CardTitle className="text-sm font-semibold">Produção vs Meta</CardTitle>
                <CardDescription className="text-xs">Acompanhamento de sacas em relação ao objetivo</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 p-4">
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
                <Card key={item.label} className="shadow-xs border border-border/70 rounded-sm hover:border-primary/50 transition-all">
                    <CardContent className="p-5 flex items-start gap-4">
                        <div className={cn("size-10 rounded-sm flex items-center justify-center shrink-0", item.bg)}>
                            <item.icon className={cn("size-5", item.color)} />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">{item.label}</p>
                            <p className="text-2xl font-bold tabular-nums tracking-tight mt-0.5">{item.value}</p>
                            <p className="text-xs text-muted-foreground mt-1 font-normal">{item.sub}</p>
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

    if (!hasChecklist && !hasNDE) {
        return (
            <div className="rounded-sm border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-sm bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="size-5" />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Nenhum alerta fitossanitário ou de checklist ativo</p>
                        <p className="text-xs text-muted-foreground">Suas safras estão em conformidade com o NDE de pragas e com as etapas planejadas.</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <Card className="shadow-xs border border-alert-warning-border rounded-sm">
            <CardHeader className="pb-3 border-b border-border/40">
                <div className="flex items-center gap-3">
                    <div className="size-9 rounded-sm bg-alert-warning-bg text-alert-warning-icon border border-alert-warning-border flex items-center justify-center shrink-0">
                        <AlertTriangle className="size-4.5" aria-hidden="true" />
                    </div>
                    <div>
                        <CardTitle className="text-base font-semibold">Central de Alertas Fitossanitários e Checklist</CardTitle>
                        <CardDescription className="text-xs">
                            {totalAlertas} ocorrência{totalAlertas !== 1 ? "s" : ""} ativa{totalAlertas !== 1 ? "s" : ""} exigindo atenção técnica
                        </CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                <Tabs defaultValue={hasChecklist ? "checklist" : "nde"}>
                    <TabsList className="w-full justify-start rounded-none h-9 bg-muted/20 px-4 border-b">
                        <TabsTrigger value="checklist" disabled={!hasChecklist} className="rounded-sm text-xs font-semibold">
                            Checklist ({checklist.length})
                        </TabsTrigger>
                        <TabsTrigger value="nde" disabled={!hasNDE} className="rounded-sm text-xs font-semibold">
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
                                            ? "border-alert-destructive-border bg-alert-destructive-bg text-alert-destructive-title"
                                            : "border-alert-warning-border bg-alert-warning-bg text-alert-warning-title"
                                    )}
                                >
                                    <div className={cn("size-2 rounded-full", a.severidade === "CRITICO" ? "bg-alert-destructive-icon" : "bg-alert-warning-icon")} />
                                    <span className="flex-1 min-w-0">
                                        <span className="font-bold">{a.safra}</span>
                                        <span className={a.severidade === "CRITICO" ? "text-alert-destructive-description" : "text-alert-warning-description"}>
                                            {" "}— {a.pendentes} pendência(s) em{" "}
                                        </span>
                                        <span className="font-semibold">{FASE_LABEL[a.fase] ?? a.fase}</span>
                                    </span>
                                    <Badge
                                        variant={a.severidade === "CRITICO" ? "danger" : "warning"}
                                        className="text-[10px] shrink-0 font-black"
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
                                    className="flex items-center gap-3 px-4 py-2.5 rounded-sm border border-alert-destructive-border bg-alert-destructive-bg text-alert-destructive-title text-sm"
                                >
                                    <Bug className="size-4 shrink-0 text-alert-destructive-icon" />
                                    <span className="flex-1 min-w-0">
                                        <span className="font-bold">{a.safra}</span>
                                        <span className="text-alert-destructive-description"> — </span>
                                        <span className="font-bold">{a.agente}</span>
                                        <span className="text-xs text-alert-destructive-description ml-2">nv {a.nivel} ≥ NDE {a.nde}</span>
                                    </span>
                                    <Badge variant="danger" className="text-[10px] shrink-0 font-black">
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
        <Card className="shadow-xs border border-border/70 rounded-sm">
            <CardHeader className="pb-3 border-b border-border/40">
                <CardTitle className="text-sm font-semibold">Estágios Fenológicos</CardTitle>
                <CardDescription className="text-xs">Últimas observações registradas no campo</CardDescription>
            </CardHeader>
            <CardContent className="p-3">
                <div className="grid gap-2 grid-cols-1">
                    {data.map((f, i) => (
                        <div key={i} className="flex items-center gap-3 px-3 py-2 border border-border/60 rounded-sm hover:bg-muted/30 transition-colors">
                            <div className="size-8 rounded-sm bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 flex items-center justify-center shrink-0">
                                <span className="text-xs font-bold">
                                    {f.estagio_codigo ?? "?"}
                                </span>
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-xs font-semibold truncate text-foreground">{f.safra}</p>
                                <p className="text-[11px] text-muted-foreground mt-0.5 truncate">
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
                <Alert variant="destructive">
                    <AlertTriangle />
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

            {/* ── Comandos & Ações Rápidas no Topo ── */}
            <QuickActionGrid
                label="Comandos & Ações Rápidas da Safra"
                columnsClassName="grid-cols-2 sm:grid-cols-4 lg:grid-cols-8"
                actions={[
                    {
                        title: "Safras",
                        description: "Painéis e ciclos produtivos da lavoura",
                        icon: Sprout,
                        href: "/agricola/safras",
                    },
                    {
                        title: "Mapa & Talhões",
                        description: "Zoneamento geográfico e limites dos talhões",
                        icon: MapPin,
                        href: "/agricola/mapa",
                    },
                    {
                        title: "Caderno de Campo",
                        description: "Registro de atividades diárias de manejo",
                        icon: BookOpen,
                        href: "/agricola/caderno",
                    },
                    {
                        title: "Operações",
                        description: "Histórico e apontamentos operacionais de máquinas",
                        icon: ClipboardList,
                        href: "/agricola/operacoes",
                    },
                    {
                        title: "Monitoramento",
                        description: "Controle de pragas, doenças e armadilhas fitossanitárias",
                        icon: Bug,
                        href: "/agricola/monitoramento",
                    },
                    {
                        title: "Insumos da Safra",
                        description: "Estoque, sementes, defensivos e aplicações por talhão",
                        icon: Package,
                        href: estoqueHref,
                    },
                    {
                        title: "Romaneios",
                        description: "Controle de cargas, pesagens e colheita",
                        icon: Wheat,
                        href: "/agricola/romaneios",
                    },
                    {
                        title: "DRE da Safra",
                        description: "Custos operacionais e resultado gerencial",
                        icon: DollarSign,
                        href: "/dashboard/financeiro/dre",
                    },
                ]}
            />

            {/* ── KPIs primários ── */}
            <PrimaryKPIs kpis={data.kpis} />

            {/* ── Main Dashboard Grid ── */}
            <div className="grid gap-6 lg:grid-cols-3 items-start auto-rows-max">
                {/* Lateral: Charts e Fenologia */}
                <div className="space-y-6 min-w-0">
                    <ProductionChart kpis={data.kpis} />

                    <Card className="shadow-xs border border-border/70 rounded-sm">
                        <CardHeader className="pb-3 border-b border-border/40">
                            <CardTitle className="text-sm font-semibold">Dados Financeiros da Safra</CardTitle>
                        </CardHeader>
                        <CardContent className="p-4 space-y-3">
                            <div className="bg-emerald-500/10 p-3.5 rounded-sm border border-emerald-500/20">
                                <p className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-widest">Receita de Colheita</p>
                                <p className="text-xl font-bold text-emerald-800 dark:text-emerald-300 mt-1">{fmtBRL(data.kpis.receita_colheita)}</p>
                            </div>
                            <div className="flex items-center justify-between text-xs font-semibold px-3 py-2 bg-muted/30 rounded-sm">
                                <span className="text-muted-foreground">Margem Operacional</span>
                                <span className="text-emerald-600 font-bold">+12.4%</span>
                            </div>
                        </CardContent>
                    </Card>

                    <FenologiaGrid data={data.fenologia_atual} />
                </div>

                {/* Centro: Kanban e Alertas */}
                <div className="lg:col-span-2 space-y-6 min-w-0">
                    <Card className="shadow-xs border border-border/70 rounded-sm">
                        <CardHeader className="pb-3 border-b border-border/40 flex flex-row items-center justify-between space-y-0">
                            <div className="flex flex-row items-center gap-2">
                                <Sprout className="size-4.5 text-primary" />
                                <CardTitle className="text-base font-semibold">Acompanhamento de Safras</CardTitle>
                                <CardDescription className="text-xs">Fluxo visual por estágio de produção</CardDescription>
                            </div>
                            <Button asChild variant="ghost" size="sm" className="h-7 text-xs rounded-sm">
                                <Link href="/agricola/safras">
                                    Detalhes das Safras <ArrowRight className="size-3 ml-1" />
                                </Link>
                            </Button>
                        </CardHeader>
                        <CardContent className="p-4">
                            <SafrasKanban safrasPorFase={data.safras_por_fase} />
                        </CardContent>
                    </Card>

                    <AlertasSection checklist={data.alertas_checklist} nde={data.alertas_nde} />
                </div>
            </div>
        </div>
    );
}
