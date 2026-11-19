"use client";

import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { PageHeader } from "@/components/shared/page-header";
import { IACommercialAssistantWidget } from "@/components/ia/ia-commercial-assistant-widget";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
    BrainCircuit,
    Activity,
    TrendingUp,
    Clock,
    CheckCircle2,
    AlertCircle,
    DollarSign,
    Target,
    Zap,
    BarChart3,
    ArrowRight,
    MousePointerClick,
    Eye,
    Lightbulb,
    ShieldAlert,
    RotateCcw,
    Users
} from "lucide-react";
import { useIAGrowthMetricas, useIAGrowthConfig, useIAGrowthConfigUpdate, useIAGrowthConfigReverter, useIAGrowthHistorico, useIAGrowthSugestoes, useIAGrowthSugestaoAplicar, useIAGrowthSugestaoIgnorar, useIAGrowthSugestoesDesempenho, useIAGrowthChurnPerformance, useIAGrowthPlanoRecomendadoMetricas, useIAGrowthOportunidades, useIAGrowthAutopilotStatus, useIAGrowthOfertasPerformance, useIAGrowthIncentivos, useIAGrowthIncentivosPendentes, useIAGrowthROI, useIAGrowthLearningWeights, useIAGrowthLearningRecalcular, type IAGrowthSugestao, type IAGrowthSugestaoDesempenho, type IAGrowthOportunidadeItem } from "@/hooks";
import { PlanoRecomendadoCard } from "@/components/ia/plano-recomendado-card";
import { IncentivoGrowthCard } from "@/components/ia/incentivo-growth-card";
import { IncentivoGrowthApprovalCard } from "@/components/ia/incentivo-growth-approval-card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { History, ArrowRight as ArrowRightIcon, Sparkles, X, ChevronUp } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell
} from "recharts";

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function MetricCard({
    title,
    value,
    subtitle,
    icon: Icon,
    color = "emerald"
}: {
    title: string;
    value: string;
    subtitle?: string;
    icon: any;
    color?: string;
}) {
    const colorClasses: Record<string, string> = {
        emerald: "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400",
        blue: "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
        amber: "bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400",
        purple: "bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400",
    };

    return (
        <Card className="rounded-sm shadow-sm overflow-hidden">
            <CardContent className="p-5">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">{title}</p>
                        <h3 className="text-2xl font-bold">{value}</h3>
                        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
                    </div>
                    <div className={`p-2.5 rounded-sm ${colorClasses[color]}`}>
                        <Icon size={20} />
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

function FunnelStep({ label, value, sublabel, icon: Icon, isLast = false }: any) {
    return (
        <div className="flex flex-col items-center flex-1 relative">
            <div className="size-12 rounded-full bg-emerald-50 dark:bg-emerald-900/20 border-2 border-emerald-500/20 flex items-center justify-center mb-3 z-10">
                <Icon className="size-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <p className="text-sm font-bold text-center">{value}</p>
            <p className="text-[10px] text-muted-foreground text-center uppercase tracking-tight font-medium">{label}</p>
            {sublabel && <p className="text-[9px] text-emerald-600 dark:text-emerald-400 font-bold mt-1">{sublabel}</p>}
            {!isLast && (
                <div className="hidden md:block absolute top-6 left-[calc(50%+24px)] w-[calc(100%-48px)] h-[1px] bg-emerald-100 dark:bg-emerald-800" />
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

interface IAPerformanceMetrics {
    economia_total_gerada: number;
    economia_media_por_decisao: number;
    taxa_acerto_ia: number;
    tempo_medio_decisao: number;
    taxa_conclusao_acoes: number;
}

interface IAPerformanceFunil {
    gerados: number;
    visualizados: number;
    executados: number;
    concluidos: number;
}

interface IAPerformanceDashboard {
    metrics: IAPerformanceMetrics;
    funil: IAPerformanceFunil;
    resumo_performance: string;
}

interface IARecomendacaoUpgrade {
    deve_recomendar: boolean;
    mensagem: string;
    economia_gerada: number;
    roi_estimado: number;
    tipo: "UPGRADE_PLANO" | "COMPRAR_CREDITOS" | string;
}

interface IAAutopilotMetricas {
    total_acoes_automaticas: number;
    impacto_financeiro_simulado_total: number;
    taxa_aprovacao_implicita: number;
    indicador_confianca: number;
    insight: string;
}

export default function IAPerformancePage() {
    const currentUser = useAppStore((state) => state.user);
    const canReviewIncentives = currentUser?.tenant_role === "owner";
    const { data: dashboardData, isLoading: isDashboardLoading } = useQuery<IAPerformanceDashboard>({
        queryKey: ["ia-performance-dashboard"],
        queryFn: () => apiFetch("/ia/performance/dashboard"),
    });

    const { data: recomendacao, isLoading: isRecomendacaoLoading } = useQuery<IARecomendacaoUpgrade>({
        queryKey: ["ia-performance-recomendacao"],
        queryFn: () => apiFetch("/ia/performance/recomendacao-upgrade"),
    });

    const { data: autopilotMetrics, isLoading: isAutopilotLoading } = useQuery<IAAutopilotMetricas>({
        queryKey: ["ia-autopilot-metricas"],
        queryFn: () => apiFetch("/ia/autopilot/metricas"),
    });

    const handleUpgradeClick = async () => {
        // Tracking: upgrade_intention_created (Step 203)
        console.log("Tracking: upgrade_intention_created", { context: "ia_roi_dashboard" });
        // Simulação de ação comercial
        window.location.href = recomendacao?.tipo === "UPGRADE_PLANO" ? "/dashboard/configuracoes/assinatura" : "/dashboard/configuracoes/assinatura?comprar_creditos=true";
    };

    if (isDashboardLoading || isRecomendacaoLoading || isAutopilotLoading) {
        return (
            <div className="p-6 space-y-6">
                <div className="flex justify-between items-center">
                    <Skeleton className="h-10 w-64" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-28 w-full" />)}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <Skeleton className="h-[400px] lg:col-span-2" />
                    <Skeleton className="h-[400px]" />
                </div>
            </div>
        );
    }

    if (!dashboardData) {
        return null;
    }

    const { metrics, funil, resumo_performance } = dashboardData;

    const chartData = [
        { name: "Alerta", value: funil.gerados },
        { name: "Visualizado", value: funil.visualizados },
        { name: "Executado", value: funil.executados },
        { name: "Concluído", value: funil.concluidos },
    ];

    return (
        <div className="p-6 space-y-6 bg-slate-50/50 dark:bg-slate-950/50 min-h-screen">
            <PageHeader
                title="Performance & Eficiência"
                description="Consolidado de eficiência, taxas de conversão e ROI das ações assistidas."
                icon={<Activity className="text-emerald-600" size={24} />}
                actions={<IACommercialAssistantWidget surface="performance" compact triggerLabel="Assistente IA" />}
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Inteligência Artificial", href: "/dashboard/ia" },
                    { label: "Performance" },
                ]}
            />

            {/* Resumo de Performance IA */}
            <Card variant="brand" className="shadow-lg relative">
                <div className="absolute top-0 right-0 p-8 opacity-10">
                    <BrainCircuit size={120} />
                </div>
                <CardContent className="p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <Zap className="size-5 text-card-description fill-current" />
                        <h2 className="text-lg font-bold">Resumo Estratégico</h2>
                    </div>
                    <p className="text-xl md:text-2xl font-light leading-relaxed max-w-3xl">
                        {resumo_performance}
                    </p>
                    <div className="mt-6 flex gap-4">
                        <Badge className="bg-white/15 hover:bg-white/15 border-none text-white px-3 py-1 rounded-sm text-xs">
                            ROI Estimado: {metrics.economia_total_gerada > 0 ? ((metrics.economia_total_gerada / 50) * 100).toFixed(0) + "%" : "Calculando..."}
                        </Badge>
                        <Badge className="bg-white/20 hover:bg-white/20 border-none text-white px-3 py-1 rounded-sm text-xs">
                            Status: Operação Saudável
                        </Badge>
                    </div>
                </CardContent>
            </Card>

            {/* KPIs Principais */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                    title="Economia Total"
                    value={`R$ ${metrics.economia_total_gerada.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
                    subtitle="Gerada por decisões da IA"
                    icon={DollarSign}
                    color="emerald"
                />
                <MetricCard
                    title="Taxa de Acerto"
                    value={`${metrics.taxa_acerto_ia}%`}
                    subtitle="Feedbacks positivos de utilidade"
                    icon={Target}
                    color="blue"
                />
                <MetricCard
                    title="Tempo Médio"
                    value={`${metrics.tempo_medio_decisao} min`}
                    subtitle="Entre alerta e execução"
                    icon={Clock}
                    color="purple"
                />
                <MetricCard
                    title="Ações Concluídas"
                    value={funil.concluidos.toString()}
                    subtitle={`${metrics.taxa_conclusao_acoes}% de conversão final`}
                    icon={CheckCircle2}
                    color="amber"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Gráfico de Conversão (Funil) */}
                <Card className="rounded-sm shadow-sm lg:col-span-2 overflow-hidden">
                    <CardHeader className="bg-slate-50/80 dark:bg-slate-900/50 border-b">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <BarChart3 size={16} className="text-emerald-600" />
                            Funil de Conversão do Copiloto
                        </CardTitle>
                        <CardDescription>Jornada do insight à decisão concluída</CardDescription>
                    </CardHeader>
                    <CardContent className="p-8">
                        <div className="flex flex-col md:flex-row items-center justify-between gap-4 py-8">
                            <FunnelStep
                                label="Alertas Gerados"
                                value={funil.gerados}
                                icon={AlertCircle}
                            />
                            <FunnelStep
                                label="Visualizados"
                                value={funil.visualizados}
                                sublabel={`${((funil.visualizados / (funil.gerados || 1)) * 100).toFixed(0)}%`}
                                icon={Clock}
                            />
                            <FunnelStep
                                label="Executados"
                                value={funil.executados}
                                sublabel={`${((funil.executados / (funil.visualizados || 1)) * 100).toFixed(0)}%`}
                                icon={Zap}
                            />
                            <FunnelStep
                                label="Concluídos"
                                value={funil.concluidos}
                                sublabel={`${((funil.concluidos / (funil.executados || 1)) * 100).toFixed(0)}%`}
                                icon={CheckCircle2}
                                isLast
                            />
                        </div>

                        <div className="h-[250px] w-full mt-8">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis
                                        dataKey="name"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{ fontSize: 10, fontWeight: 500 }}
                                    />
                                    <YAxis hide />
                                    <Tooltip
                                        contentStyle={{ borderRadius: '4px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                        cursor={{ fill: 'rgba(16, 185, 129, 0.05)' }}
                                    />
                                    <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={50}>
                                        {chartData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={index === 3 ? "#10b981" : "#94a3b8"} fillOpacity={0.8} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>

                {/* Insights Adicionais e Recomendação de Crescimento */}
                <div className="space-y-6">
                    <Card className="rounded-sm shadow-sm">
                        <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                            <CardTitle className="text-sm font-bold">Destaques da IA</CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="divide-y">
                                <div className="p-4 space-y-2">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-bold text-muted-foreground uppercase">Eficiência de Custo</span>
                                        <Badge variant="outline" className="text-[10px] rounded-sm text-emerald-600 border-emerald-600/20">Alta</Badge>
                                    </div>
                                    <p className="text-sm text-slate-700 dark:text-slate-300">
                                        A economia média de <strong>R$ {metrics.economia_media_por_decisao.toLocaleString("pt-BR")}</strong> por decisão assistida é 14x superior ao custo de processamento da IA.
                                    </p>
                                </div>
                                <div className="p-4 space-y-2">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-bold text-muted-foreground uppercase">Agilidade Decisória</span>
                                        <Badge variant="outline" className="text-[10px] rounded-sm text-blue-600 border-blue-600/20">Otimizada</Badge>
                                    </div>
                                    <p className="text-sm text-slate-700 dark:text-slate-300">
                                        O tempo médio de <strong>{metrics.tempo_medio_decisao} minutos</strong> indica que os usuários estão confiando nas recomendações para decisões rápidas.
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Step 203: Recomendação de Crescimento baseada em ROI */}
                    {recomendacao?.deve_recomendar && (
                        <Card variant="success" className="shadow-md">
                            <CardHeader className="pb-3">
                                <div className="flex items-center gap-2 mb-1">
                                    <div className="p-1 rounded-sm bg-alert-success-border/40 text-alert-success-icon">
                                        <TrendingUp size={14} />
                                    </div>
                                    <CardTitle className="text-sm font-bold">Recomendação de Crescimento</CardTitle>
                                </div>
                                <CardDescription className="text-[11px]">Análise inteligente de ROI e escala</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <p className="text-sm font-medium text-card-title leading-snug">
                                    {recomendacao.mensagem}
                                </p>

                                <div className="bg-card/80 p-3 rounded-sm border border-alert-success-border">
                                    <div className="flex justify-between items-center text-[10px] text-muted-foreground uppercase font-bold mb-1">
                                        <span>Ganho Realizado</span>
                                        <span>Potencial de ROI</span>
                                    </div>
                                    <div className="flex justify-between items-end">
                                        <span className="text-lg font-bold text-alert-success-title">R$ {recomendacao.economia_gerada.toLocaleString("pt-BR")}</span>
                                        <span className="text-xs font-bold text-alert-success-icon">{recomendacao.roi_estimado.toFixed(1)}x retorno</span>
                                    </div>
                                </div>

                                <button
                                    onClick={handleUpgradeClick}
                                    className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-bold py-2.5 rounded-sm transition-all shadow-sm"
                                >
                                    {recomendacao.tipo === "UPGRADE_PLANO" ? "Ver Planos de Upgrade" : "Solicitar Créditos de IA"}
                                    <ArrowRight size={14} />
                                </button>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>
            {/* Seção Autopilot (Step 211) */}
            <div className="space-y-4">
                <div className="flex items-center gap-2">
                    <Zap className="size-5 text-amber-500 fill-amber-500" />
                    <h2 className="text-lg font-bold">Eficiência do Autopilot</h2>
                    <Badge variant="outline" className="text-[10px] uppercase rounded-sm border-amber-500/20 text-amber-600 bg-amber-500/5">Beta</Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <MetricCard
                        title="Automações"
                        value={autopilotMetrics?.total_acoes_automaticas?.toString() || "0"}
                        subtitle="Ações executadas sem intervenção"
                        icon={Zap}
                        color="amber"
                    />
                    <MetricCard
                        title="Impacto Automático"
                        value={`R$ ${autopilotMetrics?.impacto_financeiro_simulado_total?.toLocaleString("pt-BR", { minimumFractionDigits: 2 }) || "0,00"}`}
                        subtitle="Valor otimizado pelo Autopilot"
                        icon={TrendingUp}
                        color="emerald"
                    />
                    <MetricCard
                        title="Aceitação"
                        value={`${autopilotMetrics?.taxa_aprovacao_implicita || 0}%`}
                        subtitle="Ações mantidas pelo usuário"
                        icon={CheckCircle2}
                        color="blue"
                    />
                    <Card className="rounded-sm shadow-sm overflow-hidden">
                        <CardContent className="p-5">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Confiança do Sistema</p>
                                    <div className="flex items-end gap-2">
                                        <h3 className="text-2xl font-bold">{autopilotMetrics?.indicador_confianca || 0}%</h3>
                                        <Badge className={`mb-1 text-[8px] rounded-sm py-0 h-4 border-none ${(autopilotMetrics?.indicador_confianca || 0) > 80 ? "bg-emerald-500" : "bg-amber-500"}`}>
                                            {(autopilotMetrics?.indicador_confianca || 0) > 80 ? "ALTA" : "MÉDIA"}
                                        </Badge>
                                    </div>
                                </div>
                                <div className="p-2.5 rounded-sm bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400">
                                    <Target size={20} />
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <Card variant="warning" className="shadow-sm">
                    <CardContent className="p-4 flex items-start gap-3">
                        <div className="p-2 rounded-full bg-alert-warning-border/40 text-alert-warning-icon mt-0.5">
                            <BrainCircuit size={16} />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-card-title">
                                Insight do Autopilot
                            </p>
                            <p className="text-sm text-card-description mt-1">
                                {autopilotMetrics?.insight || "O Autopilot está analisando dados para gerar insights."}
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <AutopilotGrowthSection />
            <ROIGrowthSection />
            <AprendizadoGrowthSection />
            {canReviewIncentives && <AprovacaoIncentivosSection />}
            <IncentivosControladosSection />
            <PlanoRecomendacaoSection />
            <OfertasPerformanceSection />
            <OportunidadesReceitaSection />
            <GrowthConversaoSection />
            <GrowthChurnSection />
            <SugestoesSection />
            <DesempenhoSugestoesSection />
        </div>
    );
}

const AUTOPILOT_MODE_LABELS: Record<string, string> = {
    BAIXO: "Conservador",
    MEDIO: "Balanceado",
    ALTO: "Agressivo",
};

const AUTOPILOT_ACTION_LABELS: Record<string, string> = {
    CTA_AGRESSIVO: "CTA agressivo",
    EXPERIMENTO_COPY: "Experimento de copy",
    ASSISTENTE_PROATIVO: "Assistente proativo",
    COPY_EDUCATIVA: "Copy educativa",
    CTA_PREVENTIVO: "CTA preventivo",
    CONTEUDO_EDUCATIVO: "Conteúdo educativo",
    REENGAJAMENTO_LEVE: "Reengajamento leve",
};

interface IAAutopilotConfigResponse {
    ativo: boolean;
    autopilot_enabled: boolean;
    growth_incentivos_enabled: boolean;
    nivel_autonomia: "BAIXO" | "MEDIO" | "ALTO";
    tipos_permitidos: string[];
    limite_impacto_percentual: number;
    updated_at: string;
}

function AutopilotGrowthSection() {
    const queryClient = useQueryClient();
    const { data: status, isLoading: statusLoading } = useIAGrowthAutopilotStatus(30);
    const { data: config } = useQuery<IAAutopilotConfigResponse>({
        queryKey: ["ia-autopilot-config"],
        queryFn: () => apiFetch("/ia/autopilot/config"),
    });

    const { mutate: updateConfig, isPending } = useMutation({
        mutationFn: (payload: Partial<Pick<IAAutopilotConfigResponse, "ativo" | "autopilot_enabled" | "nivel_autonomia" | "growth_incentivos_enabled">>) =>
            apiFetch("/ia/autopilot/config", {
                method: "PATCH",
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["ia-autopilot-config"] });
            queryClient.invalidateQueries({ queryKey: ["ia-growth-autopilot-status"] });
            queryClient.invalidateQueries({ queryKey: ["ia-growth-incentivos"] });
            queryClient.invalidateQueries({ queryKey: ["ia-growth-plano-recomendado"] });
        },
    });

    const ativo = config?.autopilot_enabled ?? config?.ativo ?? status?.ativo ?? false;
    const incentivosAtivos = config?.growth_incentivos_enabled ?? false;
    const nivel = config?.nivel_autonomia ?? status?.nivel_autonomia ?? "MEDIO";
    const modo = AUTOPILOT_MODE_LABELS[nivel] ?? "Balanceado";
    const recentes = status?.recentes ?? [];

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                    <ShieldAlert size={16} className="text-primary" />
                    <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                        Automação comercial
                    </h2>
                    <Badge variant="outline" className={`text-[9px] rounded-sm ${ativo ? "border-emerald-500/20 text-emerald-700 bg-emerald-500/5" : "border-slate-400/20 text-slate-600 bg-slate-500/5"}`}>
                        {ativo ? "ON" : "OFF"}
                    </Badge>
                    <Badge variant="outline" className="text-[9px] rounded-sm">
                        {modo}
                    </Badge>
                    <Badge variant="outline" className="text-[9px] rounded-sm">
                        Oferta {status?.tipo_oferta ? (OFERTA_LABELS[status.tipo_oferta]?.label ?? status.tipo_oferta) : "—"}
                    </Badge>
                    <Badge variant="outline" className={`text-[9px] rounded-sm ${incentivosAtivos ? "border-blue-500/20 text-blue-700 bg-blue-500/5" : "border-slate-400/20 text-slate-600 bg-slate-500/5"}`}>
                        Incentivos {incentivosAtivos ? "ON" : "OFF"}
                    </Badge>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                    <Label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Ativo</Label>
                    <Switch
                        checked={ativo}
                        disabled={isPending}
                        onCheckedChange={checked => updateConfig({ ativo: checked, autopilot_enabled: checked })}
                    />
                    <Label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Incentivos</Label>
                    <Switch
                        checked={incentivosAtivos}
                        disabled={isPending}
                        onCheckedChange={checked => updateConfig({ growth_incentivos_enabled: checked })}
                    />
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Card className="rounded-sm shadow-sm">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Estado</p>
                        <p className="mt-2 text-2xl font-black">{ativo ? "Ligado" : "Desligado"}</p>
                        <p className="text-[11px] text-muted-foreground">Tudo auditável e sem upgrade automático.</p>
                        {status?.mensagem_oferta && (
                            <p className="mt-2 text-[11px] text-muted-foreground leading-relaxed">{status.mensagem_oferta}</p>
                        )}
                        {status?.beneficio_destacado && (
                            <p className="mt-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
                                Benefício destacado: {status.beneficio_destacado}
                            </p>
                        )}
                    </CardContent>
                </Card>
                <Card className="rounded-sm shadow-sm">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Ações executadas</p>
                        <p className="mt-2 text-2xl font-black tabular-nums">{status?.acoes_executadas ?? 0}</p>
                        <p className="text-[11px] text-muted-foreground">IA executou esta ação internamente.</p>
                    </CardContent>
                </Card>
                <Card className="rounded-sm shadow-sm">
                    <CardContent className="p-4 flex items-center justify-between gap-3">
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Impacto estimado</p>
                            <p className="mt-2 text-2xl font-black tabular-nums">
                                {`R$ ${(status?.impacto_estimado ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
                            </p>
                            <p className="text-[11px] text-muted-foreground">Priorização consultiva sem billing real.</p>
                        </div>
                        <Target className="text-emerald-600" size={18} />
                    </CardContent>
                </Card>
            </div>

            <Card className="rounded-sm shadow-sm">
                <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                    <CardTitle className="text-sm font-bold">Modo de execução</CardTitle>
                    <CardDescription>Controle manual sobre a intensidade do autopilot.</CardDescription>
                </CardHeader>
                <CardContent className="p-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                    {[
                        { id: "BAIXO", label: "Conservador", desc: "Somente ações preventivas e travadas." },
                        { id: "MEDIO", label: "Balanceado", desc: "Combina prevenção, assistente e oportunidades." },
                        { id: "ALTO", label: "Agressivo", desc: "Maior cobertura com copy e CTA prioritários." },
                    ].map(option => (
                        <button
                            key={option.id}
                            type="button"
                            disabled={isPending}
                            onClick={() => updateConfig({ nivel_autonomia: option.id as "BAIXO" | "MEDIO" | "ALTO" })}
                            className={`rounded-sm border px-3 py-3 text-left transition-all ${nivel === option.id ? "border-primary bg-primary/5" : "border-border hover:border-primary/40 hover:bg-muted/30"}`}
                        >
                            <div className="flex items-center justify-between gap-2">
                                <span className="text-[10px] font-black uppercase tracking-widest">{option.label}</span>
                                {nivel === option.id && <StatusBadge status="ativo" />}
                            </div>
                            <p className="mt-1 text-[11px] text-muted-foreground leading-relaxed">{option.desc}</p>
                        </button>
                    ))}
                </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm">
                <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                    <CardTitle className="text-sm font-bold">Ações recentes</CardTitle>
                    <CardDescription>Transparência total sobre o que a IA executou.</CardDescription>
                </CardHeader>
                <CardContent className="p-4">
                    {statusLoading ? (
                        <div className="space-y-3">
                            {[1, 2, 3].map(i => <Skeleton key={i} className="h-16 rounded-sm" />)}
                        </div>
                    ) : recentes.length === 0 ? (
                        <div className="rounded-sm border border-dashed border-border px-4 py-6 text-center">
                            <p className="text-sm font-medium">Nenhuma ação automatizada registrada no período.</p>
                            <p className="mt-1 text-xs text-muted-foreground">Ações aparecerão aqui quando o autopilot executar uma recomendação.</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {recentes.map(item => (
                                <div key={item.id} className="rounded-sm border border-border/60 bg-muted/20 p-3 space-y-2">
                                    <div className="flex items-center justify-between gap-3 flex-wrap">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <Badge variant="outline" className="text-[9px] rounded-sm">
                                                {AUTOPILOT_ACTION_LABELS[item.tipo_acao] ?? item.tipo_acao}
                                            </Badge>
                                            <Badge variant="outline" className="text-[9px] rounded-sm">
                                                {item.contexto}
                                            </Badge>
                                            <Badge variant="outline" className={`text-[9px] rounded-sm ${OFERTA_LABELS[item.tipo_oferta]?.cls ?? OFERTA_LABELS.CONSULTIVO.cls}`}>
                                                {OFERTA_LABELS[item.tipo_oferta]?.label ?? item.tipo_oferta}
                                            </Badge>
                                            <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                                                IA executou esta ação
                                            </span>
                                        </div>
                                        <span className="text-[10px] text-muted-foreground">
                                            {new Date(item.executada_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
                                        </span>
                                    </div>
                                    <p className="text-xs text-muted-foreground leading-relaxed">{item.motivo}</p>
                                    {item.mensagem_oferta && (
                                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                                            {item.mensagem_oferta}
                                        </p>
                                    )}
                                    {item.beneficio_destacado && (
                                        <p className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
                                            Benefício destacado: {item.beneficio_destacado}
                                        </p>
                                    )}
                                    <div className="flex items-center gap-2 flex-wrap text-[10px]">
                                        <Badge variant="outline" className="rounded-sm">
                                            Score {item.score_oportunidade.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                                        </Badge>
                                        <Badge variant="outline" className="rounded-sm">
                                            Churn {item.churn_risk.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                                        </Badge>
                                        <Badge variant="outline" className="rounded-sm">
                                            {`R$ ${item.impacto_estimado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
                                        </Badge>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

function ROIGrowthSection() {
    const { data, isLoading } = useIAGrowthROI(30);

    if (isLoading) {
        return (
            <div className="mt-8 space-y-4">
                <div className="flex items-center gap-2">
                    <DollarSign size={16} className="text-emerald-600" />
                    <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                        Retorno das ações comerciais
                    </h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="h-24 rounded-sm" />)}
                </div>
            </div>
        );
    }

    if (!data) return null;

    const funnelData = data.funil.map(item => ({ name: item.etapa, value: item.valor }));

    const rankingBlock = (title: string, items: { label: string; taxa_conversao: number; total: number; impacto_estimado: number }[]) => (
        <Card className="rounded-sm shadow-sm">
            <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                <CardTitle className="text-sm font-bold">{title}</CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-3">
                {items.length === 0 ? (
                    <p className="text-xs text-muted-foreground">Sem dados suficientes no período.</p>
                ) : (
                    items.slice(0, 3).map((item, index) => (
                        <div key={item.label} className="flex items-center justify-between gap-3 rounded-sm border border-border/50 px-3 py-2">
                            <div className="min-w-0">
                                <p className="text-xs font-semibold truncate">{index + 1}. {item.label}</p>
                                <p className="text-[10px] text-muted-foreground">{item.total} ocorrências</p>
                            </div>
                            <div className="text-right">
                                <p className="text-xs font-bold tabular-nums">{item.taxa_conversao.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%</p>
                                <p className="text-[10px] text-emerald-600 font-semibold">{`R$ ${item.impacto_estimado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}</p>
                            </div>
                        </div>
                    ))
                )}
            </CardContent>
        </Card>
    );

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
                <DollarSign size={16} className="text-emerald-600" />
                <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                    Retorno das ações comerciais
                </h2>
                <Badge variant="outline" className="text-[9px] rounded-sm">Estimado</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
                <MetricCard title="Receita influenciada" value={`R$ ${data.receita_potencial_influenciada.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`} subtitle="Estimativa conservadora" icon={TrendingUp} color="emerald" />
                <MetricCard title="Receita convertida" value={`R$ ${data.receita_estimada_convertida.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`} subtitle="Conversões estimadas" icon={DollarSign} color="blue" />
                <MetricCard title="Conversões" value={data.conversoes.toString()} subtitle="Upgrade ou ação concluída" icon={CheckCircle2} color="amber" />
                <MetricCard title="CTR" value={`${data.ctr.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%`} subtitle="Exibição → clique" icon={MousePointerClick} color="purple" />
                <MetricCard title="Aceite incentivos" value={`${data.taxa_aceite_incentivos.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%`} subtitle={`${data.incentivos_aceitos} aceitos`} icon={Sparkles} color="blue" />
                <MetricCard title="Usuários recuperados" value={data.usuarios_recuperados_churn.toString()} subtitle="Usuários recuperados pelas ações de retenção" icon={ShieldAlert} color="emerald" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card className="rounded-sm shadow-sm">
                    <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                        <CardTitle className="text-sm font-bold">Funil executivo</CardTitle>
                        <CardDescription>Exibição → Clique → Conversão → Upgrade</CardDescription>
                    </CardHeader>
                    <CardContent className="p-4 h-[280px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={funnelData}>
                                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                                <YAxis tick={{ fontSize: 10 }} />
                                <Tooltip />
                                <Bar dataKey="value" fill="#059669" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card className="rounded-sm shadow-sm">
                    <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                        <CardTitle className="text-sm font-bold">Resumo executivo</CardTitle>
                        <CardDescription>Visão consolidada do impacto estimado</CardDescription>
                    </CardHeader>
                    <CardContent className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {[
                            { label: "CTAs exibidos", value: data.ctas_exibidos },
                            { label: "Cliques", value: data.cliques },
                            { label: "Recomendações de plano", value: data.recomendacoes_plano },
                            { label: "Upgrades influenciados", value: data.upgrades_influenciados },
                            { label: "Ações do autopilot", value: data.acoes_autopilot_executadas },
                            { label: "Conversões", value: data.conversoes },
                        ].map(item => (
                            <div key={item.label} className="rounded-sm border border-border/60 bg-muted/20 p-3">
                                <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{item.label}</p>
                                <p className="mt-1 text-xl font-black tabular-nums">{item.value}</p>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {rankingBlock("Melhor persona", data.ranking_personas)}
                {rankingBlock("Melhor abordagem", data.ranking_abordagens)}
                {rankingBlock("Melhor tipo de oferta", data.ranking_tipos_oferta)}
                {rankingBlock("Melhor incentivo", data.ranking_incentivos)}
            </div>

            <div className="rounded-sm border border-dashed border-border px-4 py-3 text-xs text-muted-foreground">
                Receita e conversões são <span className="font-semibold text-foreground">estimadas</span> quando não há billing real consolidado.
            </div>
        </div>
    );
}

function AprendizadoGrowthSection() {
    const { data, isLoading } = useIAGrowthLearningWeights(30);
    const recalcularMut = useIAGrowthLearningRecalcular();

    const pesos = data?.pesos ?? [];
    const agrupado = pesos.reduce<Record<string, typeof pesos>>((acc, item) => {
        acc[item.dimensao] = acc[item.dimensao] || [];
        acc[item.dimensao].push(item);
        return acc;
    }, {});

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                    <RotateCcw size={16} className="text-primary" />
                    <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                        Otimização das ações comerciais
                    </h2>
                    <Badge variant="outline" className="text-[9px] rounded-sm">Auditável</Badge>
                </div>
                <Button
                    size="sm"
                    variant="outline"
                    className="rounded-sm text-xs font-bold gap-1.5"
                    onClick={() => recalcularMut.mutate(30)}
                    disabled={recalcularMut.isPending}
                >
                    <RotateCcw data-icon="inline-start" />
                    Recalcular aprendizado
                </Button>
            </div>

            {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-24 rounded-sm" />)}
                </div>
            ) : !data ? null : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <MetricCard
                            title="Pesos ativos"
                            value={data.total.toString()}
                            subtitle={data.ultima_atualizacao ? `Atualizado em ${new Date(data.ultima_atualizacao).toLocaleString("pt-BR")}` : "Sem atualização"}
                            icon={RotateCcw}
                            color="blue"
                        />
                        <MetricCard
                            title="Amostras"
                            value={pesos.reduce((acc, item) => acc + item.amostras, 0).toString()}
                            subtitle="Base usada pelo aprendizado"
                            icon={Users}
                            color="emerald"
                        />
                        <MetricCard
                            title="Conversões"
                            value={pesos.reduce((acc, item) => acc + item.conversoes, 0).toString()}
                            subtitle="Resultado observado"
                            icon={TrendingUp}
                            color="amber"
                        />
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {["TIMING", "PERSONA", "ABORDAGEM", "OFERTA", "AUTOPILOT"].map((dimensao) => {
                            const items = agrupado[dimensao] ?? [];
                            return (
                                <Card key={dimensao} className="rounded-sm shadow-sm">
                                    <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                                        <CardTitle className="text-sm font-bold">{dimensao}</CardTitle>
                                        <CardDescription>Pesos aprendidos no período</CardDescription>
                                    </CardHeader>
                                    <CardContent className="p-4 space-y-3">
                                        {items.length === 0 ? (
                                            <p className="text-xs text-muted-foreground">Sem dados suficientes.</p>
                                        ) : (
                                            items.slice(0, 4).map((item) => (
                                                <div key={item.id} className="rounded-sm border border-border/60 bg-muted/20 p-3 space-y-2">
                                                    <div className="flex items-center justify-between gap-2">
                                                        <p className="text-xs font-semibold truncate">{item.chave}</p>
                                                        <Badge variant="outline" className="rounded-sm text-[9px]">
                                                            Peso {item.peso_atual.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                                                        </Badge>
                                                    </div>
                                                    <div className="flex items-center justify-between gap-2 text-[10px] text-muted-foreground">
                                                        <span>{item.amostras} amostras</span>
                                                        <span>{item.conversoes} conversões</span>
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>

                    <div className="rounded-sm border border-dashed border-border px-4 py-3 text-xs text-muted-foreground">
                        A variação dos pesos é limitada por recalculo para manter o comportamento auditável e estável.
                    </div>
                </>
            )}

            {recalcularMut.data?.mensagem && (
                <div className="rounded-sm border border-emerald-500/20 bg-emerald-50/40 dark:bg-emerald-950/10 px-4 py-3 text-xs text-emerald-700 dark:text-emerald-300">
                    {recalcularMut.data.mensagem}
                </div>
            )}
        </div>
    );
}

function IncentivosControladosSection() {
    const { data, isLoading } = useIAGrowthIncentivos({ periodoDias: 90, limite: 6 });

    const incentivos = data?.incentivos ?? [];

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
                <Sparkles size={16} className="text-blue-600" />
                <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                    Incentivos Controlados
                </h2>
                <Badge variant="outline" className="text-[9px] rounded-sm">Incentivos comerciais</Badge>
            </div>

            {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24 rounded-sm" />)}
                </div>
            ) : !data ? null : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                        <MetricCard
                            title="Oferecidos"
                            value={data.oferecidos.toString()}
                            subtitle="Benefícios temporários auditados"
                            icon={Sparkles}
                            color="blue"
                        />
                        <MetricCard
                            title="Aceitos"
                            value={data.aceitos.toString()}
                            subtitle="Usuários que aderiram ao incentivo"
                            icon={CheckCircle2}
                            color="emerald"
                        />
                        <MetricCard
                            title="Recusados"
                            value={data.recusados.toString()}
                            subtitle="Oferta rejeitada sem impacto"
                            icon={X}
                            color="amber"
                        />
                        <MetricCard
                            title="Taxa de aceite"
                            value={`${data.taxa_aceite.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%`}
                            subtitle={`${data.conversao_pos_incentivo.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}% pós-incentivo`}
                            icon={TrendingUp}
                            color="purple"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Card className="rounded-sm shadow-sm md:col-span-2">
                            <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                                <CardTitle className="text-sm font-bold">Distribuição de status</CardTitle>
                                <CardDescription>Controle operacional dos incentivos oferecidos no período.</CardDescription>
                            </CardHeader>
                            <CardContent className="p-4 grid grid-cols-2 sm:grid-cols-5 gap-3">
                                {[
                                    { label: "Oferecidos", value: data.oferecidos },
                                    { label: "Aceitos", value: data.aceitos },
                                    { label: "Recusados", value: data.recusados },
                                    { label: "Expirados", value: data.expirados },
                                    { label: "Cancelados", value: data.cancelados },
                                ].map((item) => (
                                    <div key={item.label} className="rounded-sm border border-border/60 bg-muted/20 p-3">
                                        <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">{item.label}</p>
                                        <p className="mt-1 text-xl font-black tabular-nums">{item.value}</p>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </div>

                    <div className="space-y-3">
                        {incentivos.length === 0 ? (
                            <div className="rounded-sm border border-dashed border-border px-4 py-6 text-center">
                                <p className="text-sm font-medium">Nenhum incentivo controlado no período.</p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                    Os incentivos aparecem quando a recomendação comercial entende que o benefício temporário faz sentido.
                                </p>
                            </div>
                        ) : (
                            incentivos.map((incentivo) => (
                                <IncentivoGrowthCard
                                    key={incentivo.id}
                                    incentivo={incentivo}
                                    compact
                                />
                            ))
                        )}
                    </div>
                </>
            )}
        </div>
    );
}

function AprovacaoIncentivosSection() {
    const { data, isLoading } = useIAGrowthIncentivosPendentes(90, 6);

    const incentivos = data?.incentivos ?? [];

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
                <ShieldAlert size={16} className="text-amber-600" />
                <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                    Aprovação de Incentivos
                </h2>
                <Badge variant="outline" className="text-[9px] rounded-sm">Owner only</Badge>
            </div>

            {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 rounded-sm" />)}
                </div>
            ) : !data ? null : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <MetricCard
                            title="Pendentes"
                            value={data.pendentes.toString()}
                            subtitle="Aguardam revisão humana"
                            icon={Clock}
                            color="amber"
                        />
                        <MetricCard
                            title="Aprovados"
                            value={data.aprovados.toString()}
                            subtitle="Liberados para oferta ao usuário"
                            icon={CheckCircle2}
                            color="emerald"
                        />
                        <MetricCard
                            title="Reprovados"
                            value={data.reprovados.toString()}
                            subtitle="Bloqueados pela governança"
                            icon={X}
                            color="blue"
                        />
                    </div>

                    <div className="space-y-3">
                        {incentivos.length === 0 ? (
                            <div className="rounded-sm border border-dashed border-border px-4 py-6 text-center">
                                <p className="text-sm font-medium">Nenhum incentivo pendente de aprovação.</p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                    Incentivos sensíveis aparecem aqui antes de serem liberados ao usuário final.
                                </p>
                            </div>
                        ) : (
                            incentivos.map((incentivo) => (
                                <IncentivoGrowthApprovalCard
                                    key={incentivo.id}
                                    incentivo={incentivo}
                                />
                            ))
                        )}
                    </div>
                </>
            )}
        </div>
    );
}

function GrowthConversaoSection() {
    const { data, isLoading } = useIAGrowthMetricas(30);
    const { data: configs, isLoading: configLoading } = useIAGrowthConfig();
    const { mutate: updateConfig, isPending: updating } = useIAGrowthConfigUpdate();
    const { mutate: reverterConfig, isPending: revertendo } = useIAGrowthConfigReverter();

    const CLF_CONFIG = {
        ALTA: { cls: "border-emerald-500/30 text-emerald-700 bg-emerald-500/5", label: "Alta" },
        MÉDIA: { cls: "border-blue-500/30 text-blue-700 bg-blue-500/5", label: "Média" },
        BAIXA: { cls: "border-rose-500/30 text-rose-700 bg-rose-500/5", label: "Baixa" },
    } as const;

    const getConfig = (contexto: string) =>
        configs?.find(c => c.contexto === contexto);

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <MousePointerClick size={16} className="text-primary" />
                    <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                        Performance de Conversão da IA
                    </h2>
                    <Badge variant="outline" className="text-[9px] rounded-sm">Últimos 30 dias</Badge>
                </div>
                <HistoricoDrawer />
            </div>

            {isLoading ? (
                <div className="grid grid-cols-3 gap-3">
                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 rounded-sm" />)}
                </div>
            ) : !data ? null : (
                <>
                    <div className="grid grid-cols-3 gap-3">
                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-4 flex items-center gap-3">
                                <Eye size={20} className="text-muted-foreground shrink-0" />
                                <div>
                                    <p className="text-2xl font-black tabular-nums">{data.total_exibicoes}</p>
                                    <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Exibições</p>
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-4 flex items-center gap-3">
                                <MousePointerClick size={20} className="text-primary shrink-0" />
                                <div>
                                    <p className="text-2xl font-black tabular-nums">{data.total_cliques}</p>
                                    <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Cliques</p>
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-4 flex items-center gap-3">
                                <Target size={20} className="text-emerald-600 shrink-0" />
                                <div>
                                    <p className="text-2xl font-black tabular-nums">{data.taxa_conversao_geral.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%</p>
                                    <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Conversão geral</p>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {data.por_contexto.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            {data.por_contexto.map(c => {
                                const clf = CLF_CONFIG[c.classificacao] ?? CLF_CONFIG.BAIXA;
                                const cfg = getConfig(c.contexto);
                                return (
                                    <Card key={c.contexto} className="rounded-sm shadow-sm">
                                        <CardContent className="p-4 space-y-3">
                                            <div className="flex items-center justify-between">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{c.contexto}</p>
                                                <Badge variant="outline" className={`text-[9px] rounded-sm ${clf.cls}`}>{clf.label}</Badge>
                                            </div>
                                            <p className="text-xl font-black tabular-nums">{c.taxa_conversao.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%</p>
                                            <p className="text-[10px] text-muted-foreground">{c.total_cliques}/{c.total_exibicoes} cliques</p>

                                            {/* Controles de ajuste manual (Growth-03) */}
                                            {!configLoading && cfg && (
                                                <div className="pt-2 border-t border-border/40 space-y-2">
                                                    <div className="flex items-center justify-between">
                                                        <Label className="text-[10px] font-black uppercase text-muted-foreground">Exibir CTA</Label>
                                                        <Switch
                                                            checked={cfg.ativo}
                                                            disabled={updating}
                                                            onCheckedChange={val =>
                                                                updateConfig({ contexto: c.contexto, dados: { ativo: val } })
                                                            }
                                                        />
                                                    </div>
                                                    <div className="flex items-center justify-between gap-2">
                                                        <Label className="text-[10px] font-black uppercase text-muted-foreground shrink-0">Cooldown (h)</Label>
                                                        <Input
                                                            type="number"
                                                            min={1}
                                                            max={168}
                                                            defaultValue={cfg.cooldown_horas}
                                                            className="h-6 text-[10px] w-16 text-right rounded-sm"
                                                            disabled={updating}
                                                            onBlur={e => {
                                                                const val = parseInt(e.target.value);
                                                                if (!isNaN(val) && val !== cfg.cooldown_horas)
                                                                    updateConfig({ contexto: c.contexto, dados: { cooldown_horas: val } });
                                                            }}
                                                        />
                                                    </div>
                                                    <button
                                                        onClick={() => reverterConfig(c.contexto)}
                                                        disabled={revertendo}
                                                        className="text-[9px] text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
                                                    >
                                                        Reverter para padrão
                                                    </button>
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>
                                );
                            })}
                        </div>
                    )}

                    {data.recomendacoes.length > 0 && (
                        <div className="space-y-2">
                            {data.recomendacoes.map((r, i) => (
                                <div key={i} className="flex items-start gap-2 rounded-sm border border-border bg-muted/20 px-3 py-2">
                                    <Lightbulb size={12} className="text-amber-500 shrink-0 mt-0.5" />
                                    <p className="text-[11px] text-muted-foreground leading-snug">{r}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

function GrowthChurnSection() {
    const { data, isLoading } = useIAGrowthChurnPerformance(30);

    const churnTone: Record<string, string> = {
        BAIXO: "text-emerald-700 border-emerald-500/20 bg-emerald-500/5",
        MEDIO: "text-amber-700 border-amber-500/20 bg-amber-500/5",
        ALTO: "text-rose-700 border-rose-500/20 bg-rose-500/5",
    };

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center gap-2">
                <ShieldAlert size={16} className="text-amber-600" />
                <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                    Risco de Churn
                </h2>
                <Badge variant="outline" className="text-[9px] rounded-sm">Retenção de clientes</Badge>
            </div>

            {isLoading ? (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24 rounded-sm" />)}
                </div>
            ) : !data ? null : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                        <MetricCard
                            title="Usuarios avaliados"
                            value={data.total_usuarios_avaliados.toString()}
                            subtitle="Base atual de churn monitorada"
                            icon={Users}
                            color="blue"
                        />
                        <MetricCard
                            title="Recuperacao alto risco"
                            value={`${data.recuperacao_alto_risco.taxa_recuperacao.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%`}
                            subtitle={`${data.recuperacao_alto_risco.usuarios_recuperados} usuários reengajados`}
                            icon={RotateCcw}
                            color="amber"
                        />
                        <MetricCard
                            title="Conversao preventiva"
                            value={`${data.impacto_cta_preventivo.conversao.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%`}
                            subtitle={`${data.impacto_cta_preventivo.cliques} cliques em CTAs de ajuda`}
                            icon={TrendingUp}
                            color="emerald"
                        />
                        <MetricCard
                            title="Dismiss preventivo"
                            value={data.impacto_cta_preventivo.dismisses.toString()}
                            subtitle="Sinal de atrito a monitorar"
                            icon={AlertCircle}
                            color="purple"
                        />
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <Card className="rounded-sm shadow-sm">
                            <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                                <CardTitle className="text-sm font-bold">Distribuição por nível</CardTitle>
                                <CardDescription>Percentual atual de usuários por intensidade de risco.</CardDescription>
                            </CardHeader>
                            <CardContent className="p-4 space-y-3">
                                {data.distribuicao_niveis.map(item => (
                                    <div key={item.nivel} className="flex items-center justify-between rounded-sm border border-border/60 px-3 py-2">
                                        <div className="flex items-center gap-2">
                                            <Badge variant="outline" className={`rounded-sm text-[9px] ${churnTone[item.nivel] ?? churnTone.BAIXO}`}>
                                                {item.nivel}
                                            </Badge>
                                            <span className="text-xs text-muted-foreground">{item.usuarios} usuarios</span>
                                        </div>
                                        <span className="text-sm font-black tabular-nums">
                                            {item.percentual.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%
                                        </span>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>

                        <Card className="rounded-sm shadow-sm">
                            <CardHeader className="border-b bg-slate-50/80 dark:bg-slate-900/50">
                                <CardTitle className="text-sm font-bold">Conversao por Nivel</CardTitle>
                                <CardDescription>Resposta dos usuarios ao CTA preventivo por risco registrado.</CardDescription>
                            </CardHeader>
                            <CardContent className="p-4 space-y-3">
                                {data.conversao_por_nivel.map(item => (
                                    <div key={item.nivel} className="rounded-sm border border-border/60 px-3 py-3 space-y-1.5">
                                        <div className="flex items-center justify-between">
                                            <Badge variant="outline" className={`rounded-sm text-[9px] ${churnTone[item.nivel] ?? churnTone.BAIXO}`}>
                                                {item.nivel}
                                            </Badge>
                                            <span className="text-sm font-black tabular-nums">
                                                {item.conversao.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%
                                            </span>
                                        </div>
                                        <p className="text-[11px] text-muted-foreground">
                                            {item.cliques} cliques em {item.exibicoes} exibições
                                        </p>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </div>
                </>
            )}
        </div>
    );
}

const OPORTUNIDADE_CONFIG = {
    ALTO_POTENCIAL: { cls: "text-emerald-700 border-emerald-500/20 bg-emerald-500/5", label: "Alto potencial" },
    TRAVADO: { cls: "text-amber-700 border-amber-500/20 bg-amber-500/5", label: "Travado" },
    RISCO: { cls: "text-rose-700 border-rose-500/20 bg-rose-500/5", label: "Risco" },
    NEUTRO: { cls: "text-slate-600 border-slate-400/20 bg-slate-500/5", label: "Neutro" },
} as const;

const PERSONA_LABEL: Record<string, string> = {
    todos: "Todas",
    CONSERVADOR: "Conservador",
    EXPLORADOR: "Explorador",
    ORIENTADO_A_RESULTADO: "Orientado a resultado",
    INICIANTE: "Iniciante",
    AVANCADO: "Avançado",
};

const PLANO_LABEL: Record<string, string> = {
    todos: "Todos",
    BASICO: "Básico",
    PROFISSIONAL: "Profissional",
    ENTERPRISE: "Enterprise",
};

const CATEGORIA_LABEL: Record<string, string> = {
    todos: "Todas",
    ALTO_POTENCIAL: "Alto potencial",
    TRAVADO: "Travado",
    RISCO: "Risco",
    NEUTRO: "Neutro",
};

function OportunidadesReceitaSection() {
    const [periodoDias, setPeriodoDias] = React.useState(30);
    const [persona, setPersona] = React.useState("todos");
    const [plano, setPlano] = React.useState("todos");
    const [contexto, setContexto] = React.useState("todos");
    const [categoria, setCategoria] = React.useState("todos");

    const { data, isLoading } = useIAGrowthOportunidades({
        periodoDias,
        limite: 12,
        persona,
        plano,
        contexto,
        categoria,
    });

    const contextosDisponiveis = React.useMemo(() => {
        const base = ["todos", "progresso", "acao", "resumo", ...(data?.contextos_disponiveis ?? [])];
        return Array.from(new Set(base));
    }, [data?.contextos_disponiveis]);

    const oportunidades = data?.oportunidades ?? [];
    const totalImpacto = data?.impacto_total_estimado ?? 0;

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                    <Target size={16} className="text-primary" />
                    <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                        Oportunidades de Receita
                    </h2>
                    <Badge variant="outline" className="text-[9px] rounded-sm border-primary/30 text-primary">
                        Oportunidades comerciais
                    </Badge>
                </div>
                {data && (
                    <Badge variant="outline" className="text-[10px] rounded-sm border-emerald-500/20 text-emerald-700 bg-emerald-500/5">
                        Impacto total estimado: {totalImpacto.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                    </Badge>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
                <div className="space-y-1">
                    <Label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Período</Label>
                    <Select value={String(periodoDias)} onValueChange={value => setPeriodoDias(Number(value))}>
                        <SelectTrigger className="h-8 text-xs rounded-sm">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="15">15 dias</SelectItem>
                            <SelectItem value="30">30 dias</SelectItem>
                            <SelectItem value="60">60 dias</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1">
                    <Label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Persona</Label>
                    <Select value={persona} onValueChange={setPersona}>
                        <SelectTrigger className="h-8 text-xs rounded-sm">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {Object.entries(PERSONA_LABEL).map(([value, label]) => (
                                <SelectItem key={value} value={value}>
                                    {label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1">
                    <Label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Plano</Label>
                    <Select value={plano} onValueChange={setPlano}>
                        <SelectTrigger className="h-8 text-xs rounded-sm">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {Object.entries(PLANO_LABEL).map(([value, label]) => (
                                <SelectItem key={value} value={value}>
                                    {label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1">
                    <Label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Contexto</Label>
                    <Select value={contexto} onValueChange={setContexto}>
                        <SelectTrigger className="h-8 text-xs rounded-sm">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {contextosDisponiveis.map((value) => (
                                <SelectItem key={value} value={value}>
                                    {value === "todos" ? "Todos" : value}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1">
                    <Label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Categoria</Label>
                    <Select value={categoria} onValueChange={setCategoria}>
                        <SelectTrigger className="h-8 text-xs rounded-sm">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {Object.entries(CATEGORIA_LABEL).map(([value, label]) => (
                                <SelectItem key={value} value={value}>
                                    {label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <div className="flex items-center justify-end">
                <button
                    type="button"
                    onClick={() => {
                        setPeriodoDias(30);
                        setPersona("todos");
                        setPlano("todos");
                        setContexto("todos");
                        setCategoria("todos");
                    }}
                    className="text-[10px] font-black uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors"
                >
                    Limpar filtros
                </button>
            </div>

            {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24 rounded-sm" />)}
                </div>
            ) : !data ? null : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Total priorizado</p>
                                <p className="mt-2 text-2xl font-black tabular-nums">{data.total_oportunidades}</p>
                                <p className="text-[11px] text-muted-foreground">Usuários com maior potencial de receita</p>
                            </CardContent>
                        </Card>
                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Alto potencial</p>
                                <p className="mt-2 text-2xl font-black tabular-nums text-emerald-600">{data.alto_potencial}</p>
                                <p className="text-[11px] text-muted-foreground">Fit alto, churn baixo e uso forte</p>
                            </CardContent>
                        </Card>
                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Travados</p>
                                <p className="mt-2 text-2xl font-black tabular-nums text-amber-600">{data.travados}</p>
                                <p className="text-[11px] text-muted-foreground">Fit alto sem conversão recente</p>
                            </CardContent>
                        </Card>
                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Risco</p>
                                <p className="mt-2 text-2xl font-black tabular-nums text-rose-600">{data.risco}</p>
                                <p className="text-[11px] text-muted-foreground">Usar abordagem consultiva e preventiva</p>
                            </CardContent>
                        </Card>
                    </div>

                    {oportunidades.length === 0 ? (
                        <Card className="rounded-sm shadow-sm border-dashed">
                            <CardContent className="p-6 text-center">
                                <p className="text-sm font-medium">Nenhuma oportunidade encontrada para os filtros atuais.</p>
                                <p className="mt-1 text-xs text-muted-foreground">Ajuste os filtros para ampliar a priorização.</p>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="space-y-3">
                            {oportunidades.map((item: IAGrowthOportunidadeItem, index: number) => {
                                const categoriaCfg = OPORTUNIDADE_CONFIG[item.categoria] ?? OPORTUNIDADE_CONFIG.NEUTRO;
                                return (
                                    <Card key={item.usuario_id} className="rounded-sm shadow-sm">
                                        <CardContent className="p-4 space-y-4">
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="space-y-2 min-w-0">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <Badge variant="outline" className={`text-[9px] rounded-sm ${categoriaCfg.cls}`}>
                                                            {index + 1}. {categoriaCfg.label}
                                                        </Badge>
                                                        <Badge variant="outline" className="text-[9px] rounded-sm">
                                                            {item.nivel}
                                                        </Badge>
                                                        <Badge variant="outline" className={`text-[9px] rounded-sm ${OFERTA_LABELS[item.tipo_oferta]?.cls ?? OFERTA_LABELS.CONSULTIVO.cls}`}>
                                                            {OFERTA_LABELS[item.tipo_oferta]?.label ?? item.tipo_oferta}
                                                        </Badge>
                                                        <Badge variant="outline" className="text-[9px] rounded-sm">
                                                            {item.churn_risk_level === "ALTO" ? "Churn alto" : item.churn_risk_level === "MEDIO" ? "Churn médio" : "Churn baixo"}
                                                        </Badge>
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold leading-tight">{item.usuario_label}</p>
                                                        <p className="text-[11px] text-muted-foreground">
                                                            {PERSONA_LABEL[item.persona ?? "todos"] ?? item.persona ?? "Sem persona"} · {item.contexto}
                                                        </p>
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <p className="text-xl font-black tabular-nums">{item.impacto_estimado_label}</p>
                                                    <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">Impacto estimado</p>
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                <div className="rounded-sm border border-border/60 bg-muted/20 p-3 space-y-1.5">
                                                    <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Plano</p>
                                                    <p className="text-sm font-medium">
                                                        {item.plano_atual_label} → {item.plano_recomendado_label}
                                                    </p>
                                                    <p className="text-[11px] text-muted-foreground">
                                                        Score fit {item.score_fit.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                                                    </p>
                                                </div>
                                                <div className="rounded-sm border border-border/60 bg-muted/20 p-3 space-y-1.5">
                                                    <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Engajamento</p>
                                                    <p className="text-sm font-medium">
                                                        Oportunidade {item.score_oportunidade.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                                                    </p>
                                                    <p className="text-[11px] text-muted-foreground">
                                                        {item.cta_clicks} cliques · {item.cta_views} exibições · {item.assistente_interacoes} interações com assistente
                                                    </p>
                                                </div>
                                                <div className="rounded-sm border border-border/60 bg-muted/20 p-3 space-y-1.5">
                                                    <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Ação sugerida</p>
                                                    <p className="text-sm font-medium">{item.acao_sugerida}</p>
                                                    <p className="text-[11px] text-muted-foreground">
                                                        {item.cta_label} · {item.cta_url}
                                                    </p>
                                                    {item.mensagem_oferta && (
                                                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                                                            {item.mensagem_oferta}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                );
                            })}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

const CAMPO_LABEL: Record<string, string> = {
    ativo: "Exibir CTA",
    cooldown_horas: "Cooldown (h)",
    prioridade: "Prioridade",
};

function HistoricoDrawer() {
    const [contextoFiltro, setContextoFiltro] = React.useState<string>("todos");
    const contextoParam = contextoFiltro === "todos" ? undefined : contextoFiltro;
    const { data: historico, isLoading } = useIAGrowthHistorico(contextoParam, 30);

    return (
        <Sheet>
            <SheetTrigger asChild>
                <button className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors">
                    <History size={12} />
                    Histórico de ajustes
                </button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[420px] sm:max-w-[420px] overflow-y-auto">
                <SheetHeader className="mb-4">
                    <SheetTitle className="text-sm font-black uppercase tracking-widest">Histórico de Ajustes</SheetTitle>
                </SheetHeader>

                <div className="mb-4">
                    <Select value={contextoFiltro} onValueChange={setContextoFiltro}>
                        <SelectTrigger className="h-8 text-xs rounded-sm">
                            <SelectValue placeholder="Filtrar por contexto" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="todos">Todos os contextos</SelectItem>
                            <SelectItem value="progresso">Progresso</SelectItem>
                            <SelectItem value="acao">Ação</SelectItem>
                            <SelectItem value="resumo">Resumo</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {isLoading ? (
                    <div className="space-y-3">
                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-16 rounded-sm" />)}
                    </div>
                ) : !historico || historico.length === 0 ? (
                    <p className="text-[11px] text-muted-foreground text-center py-8">Nenhuma alteração registrada nos últimos 30 dias.</p>
                ) : (
                    <div className="space-y-2">
                        {historico.map(item => (
                            <div key={item.id} className="rounded-sm border border-border bg-muted/10 p-3 space-y-1.5">
                                <div className="flex items-center justify-between gap-2">
                                    <Badge variant="outline" className="text-[9px] rounded-sm capitalize">{item.contexto}</Badge>
                                    <span className="text-[9px] text-muted-foreground">{new Date(item.criado_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</span>
                                </div>
                                <div className="flex items-center gap-2 text-[11px]">
                                    <span className="font-bold text-muted-foreground">{CAMPO_LABEL[item.campo_alterado] ?? item.campo_alterado}:</span>
                                    <span className="line-through text-rose-500/70">{item.valor_anterior ?? "—"}</span>
                                    <ArrowRightIcon size={10} className="text-muted-foreground shrink-0" />
                                    <span className="font-bold text-emerald-600">{item.valor_novo}</span>
                                </div>
                                <p className="text-[9px] text-muted-foreground">por {item.alterado_por_nome}</p>
                            </div>
                        ))}
                    </div>
                )}
            </SheetContent>
        </Sheet>
    );
}

const IMPACTO_CONFIG = {
    ALTO: { cls: "border-rose-500/30 text-rose-700 bg-rose-500/5", label: "Alto impacto" },
    MÉDIO: { cls: "border-amber-500/30 text-amber-700 bg-amber-500/5", label: "Médio impacto" },
    BAIXO: { cls: "border-slate-400/30 text-slate-600 bg-slate-500/5", label: "Baixo impacto" },
} as const;

const TIPO_LABEL: Record<string, string> = {
    DESATIVAR: "Desativar contexto",
    REDUZIR_COOLDOWN: "Reduzir cooldown",
    AUMENTAR_PRIORIDADE: "Aumentar prioridade",
    ESTABILIZAR: "Estabilizar configuração",
};

function SugestoesSection() {
    const { data, isLoading } = useIAGrowthSugestoes(30);
    const { mutate: aplicar, isPending: aplicando } = useIAGrowthSugestaoAplicar();
    const { mutate: ignorar, isPending: ignorando } = useIAGrowthSugestaoIgnorar();
    const busy = aplicando || ignorando;

    const sugestoes = data?.sugestoes ?? [];

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-primary animate-pulse" />
                <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                    Sugestões de Otimização
                </h2>
                {data && data.total > 0 && (
                    <Badge variant="outline" className="text-[9px] rounded-sm border-primary/30 text-primary">
                        {data.total} sugestão{data.total !== 1 ? "ões" : ""}
                    </Badge>
                )}
            </div>

            {isLoading ? (
                <div className="space-y-3">
                    {[1, 2].map(i => <Skeleton key={i} className="h-24 rounded-sm" />)}
                </div>
            ) : sugestoes.length === 0 ? (
                <div className="rounded-sm border border-border bg-muted/10 px-4 py-6 text-center">
                    <p className="text-[11px] text-muted-foreground">Nenhuma sugestão no momento. Continue monitorando as métricas.</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {sugestoes.map(s => {
                        const imp = IMPACTO_CONFIG[s.impacto] ?? IMPACTO_CONFIG.BAIXO;
                        return (
                            <Card key={s.id} className="rounded-sm shadow-sm">
                                <CardContent className="p-4 space-y-3">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <Badge variant="outline" className="text-[9px] rounded-sm capitalize">{s.contexto}</Badge>
                                            <Badge variant="outline" className={`text-[9px] rounded-sm ${imp.cls}`}>{imp.label}</Badge>
                                            <span className="text-[9px] text-muted-foreground uppercase font-bold tracking-wider">{TIPO_LABEL[s.tipo] ?? s.tipo}</span>
                                        </div>
                                        <button
                                            disabled={busy}
                                            onClick={() => ignorar(s.id)}
                                            className="text-muted-foreground hover:text-foreground transition-colors shrink-0 disabled:opacity-40"
                                        >
                                            <X size={12} />
                                        </button>
                                    </div>

                                    <p className="text-xs text-muted-foreground leading-relaxed">{s.justificativa}</p>

                                    <div className="flex items-center justify-between gap-3">
                                        <div className="flex items-center gap-1.5">
                                            <ChevronUp size={10} className="text-emerald-500" />
                                            <span className="text-[9px] text-muted-foreground">Confiança: {Math.round(s.confianca * 100)}%</span>
                                        </div>
                                        {s.aplicavel && (
                                            <button
                                                disabled={busy}
                                                onClick={() => aplicar(s.id)}
                                                className="text-[10px] font-black uppercase tracking-widest text-primary hover:underline disabled:opacity-50 transition-all"
                                            >
                                                Aplicar sugestão →
                                            </button>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

const TIPO_LABEL_DESEMP: Record<string, string> = {
    DESATIVAR: "Desativar",
    REDUZIR_COOLDOWN: "Reduzir cooldown",
    AUMENTAR_PRIORIDADE: "Aumentar prioridade",
    ESTABILIZAR: "Estabilizar",
};

function DesempenhoSugestoesSection() {
    const { data, isLoading } = useIAGrowthSugestoesDesempenho(30);

    const variacaoColor = (v: number) =>
        v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-500" : "text-muted-foreground";

    return (
        <div className="mt-8 space-y-4">
            <div className="flex items-center gap-2">
                <BarChart3 size={16} className="text-primary" />
                <h2 className="text-sm font-black uppercase tracking-widest text-foreground">
                    Desempenho das Sugestões
                </h2>
                <Badge variant="outline" className="text-[9px] rounded-sm">Últimos 30 dias</Badge>
            </div>

            {isLoading ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="h-20 rounded-sm" />)}
                </div>
            ) : !data ? null : (
                <>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        {[
                            { label: "Geradas", value: data.total_geradas, cls: "text-foreground" },
                            { label: "Aplicadas", value: data.total_aplicadas, cls: "text-emerald-600" },
                            { label: "Ignoradas", value: data.total_ignoradas, cls: "text-muted-foreground" },
                            { label: "Taxa de aplicação", value: `${data.taxa_aplicacao.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%`, cls: data.taxa_aplicacao >= 50 ? "text-emerald-600" : "text-amber-600" },
                            { label: "Conversão antes", value: `${data.conversao_media_antes.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%`, cls: "text-foreground" },
                            { label: "Conversão depois", value: `${data.conversao_media_depois.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%`, cls: variacaoColor(data.variacao_media) },
                        ].map(c => (
                            <Card key={c.label} className="rounded-sm shadow-sm">
                                <CardContent className="p-4">
                                    <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1">{c.label}</p>
                                    <p className={`text-xl font-black tabular-nums ${c.cls}`}>{c.value}</p>
                                </CardContent>
                            </Card>
                        ))}
                    </div>

                    {data.com_ganho.length > 0 && (
                        <div className="space-y-2">
                            <p className="text-[10px] font-black uppercase tracking-widest text-emerald-700">Com ganho de conversão</p>
                            {data.com_ganho.map(s => (
                                <div key={s.sugestao_id} className="flex items-center justify-between rounded-sm border border-emerald-500/20 bg-emerald-500/5 px-3 py-2">
                                    <div className="flex items-center gap-2">
                                        <Badge variant="outline" className="text-[9px] rounded-sm capitalize">{s.contexto}</Badge>
                                        <span className="text-[10px] text-muted-foreground">{TIPO_LABEL_DESEMP[s.tipo] ?? s.tipo}</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-[10px]">
                                        <span className="text-muted-foreground">{s.taxa_antes.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}% → {s.taxa_depois.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%</span>
                                        <span className="font-black text-emerald-600">+{s.variacao.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {data.sem_ganho.length > 0 && (
                        <div className="space-y-2">
                            <p className="text-[10px] font-black uppercase tracking-widest text-rose-600">Sem ganho aparente</p>
                            {data.sem_ganho.map(s => (
                                <div key={s.sugestao_id} className="flex items-center justify-between rounded-sm border border-rose-500/20 bg-rose-500/5 px-3 py-2">
                                    <div className="flex items-center gap-2">
                                        <Badge variant="outline" className="text-[9px] rounded-sm capitalize">{s.contexto}</Badge>
                                        <span className="text-[10px] text-muted-foreground">{TIPO_LABEL_DESEMP[s.tipo] ?? s.tipo}</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-[10px]">
                                        <span className="text-muted-foreground">{s.taxa_antes.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}% → {s.taxa_depois.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%</span>
                                        <span className="font-black text-rose-500">{s.variacao.toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {data.total_aplicadas === 0 && (
                        <p className="text-[11px] text-muted-foreground text-center py-4">
                            Nenhuma sugestão foi aplicada ainda. Aplique sugestões acima para ver o impacto aqui.
                        </p>
                    )}
                </>
            )}
        </div>
    );
}

// ─── IA-Growth-16: Recomendação de Plano (consultiva) ────────────────────────

function PlanoRecomendacaoSection() {
    const { data: metricas, isLoading } = useIAGrowthPlanoRecomendadoMetricas(30);

    const totalRecs = metricas?.total_recomendacoes ?? 0;
    const totalClicks = (metricas?.distribuicao ?? []).reduce((acc, d) => acc + (d.total_clicks ?? 0), 0);
    const totalConv = (metricas?.distribuicao ?? []).reduce((acc, d) => acc + (d.total_conversoes ?? 0), 0);
    const ctrGeral = totalRecs > 0 ? totalClicks / totalRecs : 0;
    const convGeral = totalRecs > 0 ? totalConv / totalRecs : 0;

    return (
        <Card className="rounded-sm shadow-sm overflow-hidden">
            <CardHeader className="bg-emerald-50/40 dark:bg-emerald-950/10 border-b">
                <div className="flex items-center justify-between gap-2">
                    <div>
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <Sparkles size={16} className="text-emerald-600" />
                            Recomendação de Plano
                        </CardTitle>
                        <CardDescription className="text-xs mt-1">
                            Como a venda consultiva da IA está performando — últimos 30 dias.
                        </CardDescription>
                    </div>
                    <Badge variant="outline" className="text-[10px] rounded-sm">
                        {totalRecs} recomendações
                    </Badge>
                </div>
            </CardHeader>

            <CardContent className="p-5 space-y-5">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="lg:col-span-1">
                        <PlanoRecomendadoCard />
                    </div>
                    <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-3 self-start">
                        <KpiPequeno label="CTR geral" value={`${(ctrGeral * 100).toFixed(1)}%`} />
                        <KpiPequeno label="Conversão geral" value={`${(convGeral * 100).toFixed(1)}%`} />
                        <KpiPequeno label="Total cliques" value={`${totalClicks}`} />
                    </div>
                </div>

                <div>
                    <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-2">
                        Distribuição por plano recomendado
                    </p>
                    {isLoading ? (
                        <Skeleton className="h-24 w-full" />
                    ) : (metricas?.distribuicao ?? []).length === 0 ? (
                        <p className="text-xs text-muted-foreground italic py-4 text-center">
                            Nenhuma recomendação emitida no período.
                        </p>
                    ) : (
                        <div className="overflow-x-auto rounded-sm border">
                            <table className="w-full text-xs">
                                <thead className="bg-muted/40 text-[10px] uppercase tracking-wider text-muted-foreground">
                                    <tr>
                                        <th className="text-left px-3 py-2 font-bold">Plano recomendado</th>
                                        <th className="text-right px-3 py-2 font-bold">Recomendações</th>
                                        <th className="text-right px-3 py-2 font-bold">Cliques</th>
                                        <th className="text-right px-3 py-2 font-bold">CTR</th>
                                        <th className="text-right px-3 py-2 font-bold">Conversões</th>
                                        <th className="text-right px-3 py-2 font-bold">Taxa conv.</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {metricas!.distribuicao.map((d) => (
                                        <tr key={d.plano} className="border-t">
                                            <td className="px-3 py-2 font-medium">{d.plano_label}</td>
                                            <td className="px-3 py-2 text-right tabular-nums">{d.total_recomendacoes}</td>
                                            <td className="px-3 py-2 text-right tabular-nums">{d.total_clicks}</td>
                                            <td className="px-3 py-2 text-right tabular-nums text-emerald-700 dark:text-emerald-400">
                                                {(d.taxa_clique * 100).toFixed(1)}%
                                            </td>
                                            <td className="px-3 py-2 text-right tabular-nums">{d.total_conversoes}</td>
                                            <td className="px-3 py-2 text-right tabular-nums font-bold">
                                                {(d.taxa_conversao * 100).toFixed(1)}%
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

const OFERTA_LABELS: Record<string, { label: string; cls: string }> = {
    SEM_INCENTIVO: { label: "Recomendado", cls: "text-emerald-700 border-emerald-500/20 bg-emerald-500/5" },
    INCENTIVO_LEVE: { label: "Sugestão", cls: "text-blue-700 border-blue-500/20 bg-blue-500/5" },
    INCENTIVO_FORTE: { label: "Oportunidade", cls: "text-amber-700 border-amber-500/20 bg-amber-500/5" },
    EDUCATIVO: { label: "Ajuda", cls: "text-sky-700 border-sky-500/20 bg-sky-500/5" },
    CONSULTIVO: { label: "Ajuda", cls: "text-slate-700 border-slate-400/20 bg-slate-500/5" },
};

function OfertasPerformanceSection() {
    const { data, isLoading } = useIAGrowthOfertasPerformance(30);
    const rows = data?.performance ?? [];
    const topOffer = rows[0];

    return (
        <Card className="rounded-sm shadow-sm overflow-hidden">
            <CardHeader className="bg-slate-50/80 dark:bg-slate-900/50 border-b">
                <div className="flex items-center justify-between gap-2">
                    <div>
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <BarChart3 size={16} className="text-primary" />
                            Performance de Ofertas
                        </CardTitle>
                        <CardDescription className="text-xs mt-1">
                            Conversão, distribuição e impacto estimado por tipo de oferta.
                        </CardDescription>
                    </div>
                    <Badge variant="outline" className="text-[10px] rounded-sm">
                        Últimos 30 dias
                    </Badge>
                </div>
            </CardHeader>

            <CardContent className="p-5 space-y-5">
                {isLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-sm" />)}
                    </div>
                ) : !data ? null : (
                    <>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                            <MetricCard
                                title="Recomendações"
                                value={data.total_recomendacoes.toString()}
                                subtitle="Total de ofertas emitidas"
                                icon={Sparkles}
                                color="blue"
                            />
                            <MetricCard
                                title="Conversões"
                                value={data.total_conversoes.toString()}
                                subtitle="Ofertas que viraram ação"
                                icon={MousePointerClick}
                                color="emerald"
                            />
                            <MetricCard
                                title="Impacto em receita"
                                value={`R$ ${data.impacto_total_estimado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
                                subtitle="Estimativa consolidada"
                                icon={DollarSign}
                                color="amber"
                            />
                            <Card className="rounded-sm shadow-sm overflow-hidden">
                                <CardContent className="p-5">
                                    <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Tipo líder</p>
                                    <h3 className="text-2xl font-bold">{topOffer ? (OFERTA_LABELS[topOffer.tipo_oferta]?.label ?? topOffer.tipo_oferta) : "—"}</h3>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {topOffer ? `${(topOffer.participacao * 100).toFixed(1)}% da distribuição` : "Aguardando dados"}
                                    </p>
                                </CardContent>
                            </Card>
                        </div>

                        {rows.length > 0 && (
                            <div className="overflow-x-auto rounded-sm border">
                                <table className="w-full text-xs">
                                    <thead className="bg-muted/40 text-[10px] uppercase tracking-wider text-muted-foreground">
                                        <tr>
                                            <th className="text-left px-3 py-2 font-bold">Tipo de oferta</th>
                                            <th className="text-right px-3 py-2 font-bold">Distribuição</th>
                                            <th className="text-right px-3 py-2 font-bold">Conversões</th>
                                            <th className="text-right px-3 py-2 font-bold">Taxa conv.</th>
                                            <th className="text-right px-3 py-2 font-bold">Impacto</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rows.map((row) => {
                                            const cfg = OFERTA_LABELS[row.tipo_oferta] ?? OFERTA_LABELS.CONSULTIVO;
                                            return (
                                                <tr key={row.tipo_oferta} className="border-t">
                                                    <td className="px-3 py-2">
                                                        <Badge variant="outline" className={`text-[9px] rounded-sm ${cfg.cls}`}>
                                                            {cfg.label}
                                                        </Badge>
                                                    </td>
                                                    <td className="px-3 py-2 text-right tabular-nums">
                                                        {(row.participacao * 100).toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%
                                                    </td>
                                                    <td className="px-3 py-2 text-right tabular-nums">{row.total_conversoes}</td>
                                                    <td className="px-3 py-2 text-right tabular-nums font-bold">
                                                        {(row.taxa_conversao * 100).toLocaleString("pt-BR", { minimumFractionDigits: 1 })}%
                                                    </td>
                                                    <td className="px-3 py-2 text-right tabular-nums">
                                                        {row.impacto_estimado_label}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </>
                )}
            </CardContent>
        </Card>
    );
}

function KpiPequeno({ label, value }: { label: string; value: string }) {
    return (
        <Card className="rounded-sm shadow-none border">
            <CardContent className="p-4">
                <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1">{label}</p>
                <p className="text-xl font-bold tabular-nums">{value}</p>
            </CardContent>
        </Card>
    );
}
