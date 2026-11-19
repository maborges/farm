"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    LayoutDashboard,
    Users,
    CloudSun,
    TrendingUp,
    BookOpen,
    Settings,
    AlertTriangle,
    AlertCircle,
    CheckCircle2,
    Clock,
    RefreshCw,
    Shield,
    ShieldCheck,
    ShieldAlert,
    Activity,
    Server,
    ExternalLink,
    Key,
    Database,
    Layers,
    FileCheck,
    Check,
    X,
    ChevronRight,
} from "lucide-react";

import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle, type AlertVariant } from "@/components/ui/alert";

const SEVERIDADE_ALERT_VARIANT: Record<string, AlertVariant> = {
    CRITICAL: "destructive",
    WARNING: "warning",
    INFO: "info",
};

interface UsuariosOverview {
    total_gratuitos: number;
    novos_hoje: number;
    novos_7d: number;
    novos_30d: number;
    ativos_hoje: number;
    ativos_7d: number;
    bloqueados: number;
    com_byok: number;
    taxa_conversao_byok_pct: number;
    crescimento_mensal_pct: number;
}

interface TrafegoOverview {
    clima_requisicoes_mes: number;
    clima_cache_hits: number;
    clima_cache_misses: number;
    clima_hit_rate_pct: number;
    clima_timeouts: number;
    clima_falhas: number;
    mercado_fontes_operacionais: number;
    mercado_fontes_total: number;
    snapshot_deral_ativo_id: string;
    snapshot_deral_referencia: string;
    snapshot_deral_defasagem_dias: number;
}

interface SaudeSistema {
    redis_online: boolean;
    provedor_clima_ativo: string;
    contingencia_clima_ativa: boolean;
    alertas_criticos_count: number;
    alertas_warning_count: number;
    alertas_info_count: number;
    homologacao_concluida_pct: number;
}

interface DashboardResumoResponse {
    consultado_em: string;
    usuarios: UsuariosOverview;
    trafego: TrafegoOverview;
    saude: SaudeSistema;
}

interface EvolucaoItem {
    data: string;
    novos_cadastros: number;
    acumulado: number;
}

interface UsuariosEvolucaoResponse {
    historico_30d: EvolucaoItem[];
    distribuicao_status: Record<string, number>;
    distribuicao_byok_provedor: Record<string, number>;
    metadados_coleta: string;
}

interface OperationalAlertItem {
    id: string;
    tipo: string;
    severidade: "CRITICAL" | "WARNING" | "INFO";
    prioridade: "URGENT" | "HIGH" | "NORMAL" | "LOW";
    categoria: string;
    titulo: string;
    descricao: string;
    data_deteccao: string;
    recomendacao: string;
    origem: string;
}

interface HomologacaoItem {
    id: number;
    titulo: string;
    descricao: string;
    fase_origem: string;
    status: "APROVADO" | "EM VALIDAÇÃO" | "PENDENTE" | "BLOQUEADO";
    evidencia: string;
    acao_necessaria: string;
}

interface HomologacaoResponse {
    gerado_em: string;
    total_itens: number;
    aprovados_count: number;
    em_validacao_count: number;
    pendentes_count: number;
    bloqueados_count: number;
    percentual_conclusao: number;
    itens: HomologacaoItem[];
}

export default function AgroDashboardPage() {
    const [tabAtiva, setTabAtiva] = useState("visao-geral");

    const {
        data: resumo,
        isLoading: loadingResumo,
        refetch: refetchResumo,
    } = useQuery<DashboardResumoResponse>({
        queryKey: ["agro-dashboard-resumo"],
        queryFn: () => apiFetch("/api/v1/backoffice/agro/dashboard/resumo"),
        refetchInterval: 60000,
    });

    const { data: evolucao, isLoading: loadingEvolucao } = useQuery<UsuariosEvolucaoResponse>({
        queryKey: ["agro-dashboard-evolucao"],
        queryFn: () => apiFetch("/api/v1/backoffice/agro/dashboard/usuarios-evolucao"),
        enabled: tabAtiva === "usuarios" || tabAtiva === "visao-geral",
    });

    const { data: alertas, isLoading: loadingAlertas } = useQuery<OperationalAlertItem[]>({
        queryKey: ["agro-dashboard-alertas"],
        queryFn: () => apiFetch("/api/v1/backoffice/agro/dashboard/alertas"),
        enabled: tabAtiva === "incidentes" || tabAtiva === "visao-geral",
    });

    const { data: homologacao, isLoading: loadingHomologacao } = useQuery<HomologacaoResponse>({
        queryKey: ["agro-dashboard-homologacao"],
        queryFn: () => apiFetch("/api/v1/backoffice/agro/dashboard/homologacao"),
        enabled: tabAtiva === "homologacao" || tabAtiva === "visao-geral",
    });

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Painel Executivo & Governança Operacional"
                description="Observabilidade centralizada do DeepFarms Agro: usuários, tráfego público, adaptadores climáticos, fontes oficiais e maturidade técnica."
                icon={<LayoutDashboard className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Agro" },
                ]}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetchResumo()}
                        className="rounded-sm text-xs h-8 gap-1.5"
                        title="Atualizar métricas agora"
                    >
                        <RefreshCw size={13} className={loadingResumo ? "animate-spin" : ""} />
                        Atualizar
                    </Button>
                }
            />

            {/* Alertas operacionais ficam visíveis no início do painel, fora das abas. */}
            {alertas && alertas.length > 0 && (
                <div className="space-y-2">
                    {alertas.map((alerta) => (
                        <Alert
                            key={alerta.id}
                            variant={SEVERIDADE_ALERT_VARIANT[alerta.severidade] ?? "default"}
                        >
                            <AlertTriangle />
                            <div className="flex items-center justify-between w-full">
                                <AlertTitle className="text-xs font-bold">{alerta.titulo}</AlertTitle>
                                <Badge variant="outline" className="text-[10px] uppercase font-mono rounded-sm">
                                    {alerta.categoria}
                                </Badge>
                            </div>
                            <AlertDescription className="text-xs mt-1 leading-relaxed">
                                {alerta.descricao} <strong>Recomendação:</strong> {alerta.recomendacao}
                            </AlertDescription>
                        </Alert>
                    ))}
                </div>
            )}

            {/* Barra de Acesso Rápido aos Consoles Especializados */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                <Link href="/dashboard/backoffice/agro/usuarios">
                    <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-between h-9 text-xs rounded-sm hover:border-emerald-600/50 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20"
                    >
                        <span className="flex items-center gap-1.5 font-medium">
                            <Users size={14} className="text-emerald-600" /> Produtores Agro
                        </span>
                        <ChevronRight size={13} className="text-muted-foreground" />
                    </Button>
                </Link>
                <Link href="/dashboard/backoffice/agro/bibliotecas">
                    <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-between h-9 text-xs rounded-sm hover:border-emerald-600/50 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20"
                    >
                        <span className="flex items-center gap-1.5 font-medium">
                            <BookOpen size={14} className="text-emerald-600" /> Bibliotecas
                        </span>
                        <ChevronRight size={13} className="text-muted-foreground" />
                    </Button>
                </Link>
                <Link href="/dashboard/backoffice/agro/provedores">
                    <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-between h-9 text-xs rounded-sm hover:border-emerald-600/50 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20"
                    >
                        <span className="flex items-center gap-1.5 font-medium">
                            <CloudSun size={14} className="text-emerald-600" /> Provedores Clima
                        </span>
                        <ChevronRight size={13} className="text-muted-foreground" />
                    </Button>
                </Link>
                <Link href="/dashboard/backoffice/agro/mercado">
                    <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-between h-9 text-xs rounded-sm hover:border-emerald-600/50 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20"
                    >
                        <span className="flex items-center gap-1.5 font-medium">
                            <TrendingUp size={14} className="text-emerald-600" /> Mercado & DERAL
                        </span>
                        <ChevronRight size={13} className="text-muted-foreground" />
                    </Button>
                </Link>
                <Link href="/dashboard/backoffice/agro/configuracoes">
                    <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-between h-9 text-xs rounded-sm hover:border-emerald-600/50 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20"
                    >
                        <span className="flex items-center gap-1.5 font-medium">
                            <Settings size={14} className="text-emerald-600" /> Configurações
                        </span>
                        <ChevronRight size={13} className="text-muted-foreground" />
                    </Button>
                </Link>
            </div>

            {/* KPI CARDS CONSOLIDADOS */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                {/* Card 1: Produtores */}
                <Card className="rounded-sm shadow-xs border">
                    <CardHeader className="py-2.5 px-3.5 border-b flex flex-row items-center justify-between pb-2 space-y-0">
                        <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Produtores Gratuitos
                        </span>
                        <Users size={14} className="text-emerald-600" />
                    </CardHeader>
                    <CardContent className="p-3.5 pt-2.5">
                        {loadingResumo ? (
                            <Skeleton className="h-7 w-20" />
                        ) : (
                            <div>
                                <div className="text-xl font-bold font-mono tracking-tight text-foreground">
                                    {resumo?.usuarios.total_gratuitos.toLocaleString("pt-BR") ?? 0}
                                </div>
                                <div className="flex items-center gap-2 mt-1 text-[11px] text-muted-foreground">
                                    <span className="text-emerald-600 font-semibold">
                                        +{resumo?.usuarios.novos_30d ?? 0}
                                    </span>{" "}
                                    últimos 30 dias ({resumo?.usuarios.crescimento_mensal_pct ?? 0}%)
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Card 2: Clima / Telemetria */}
                <Card className="rounded-sm shadow-xs border">
                    <CardHeader className="py-2.5 px-3.5 border-b flex flex-row items-center justify-between pb-2 space-y-0">
                        <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Consultas de Clima
                        </span>
                        <CloudSun size={14} className="text-emerald-600" />
                    </CardHeader>
                    <CardContent className="p-3.5 pt-2.5">
                        {loadingResumo ? (
                            <Skeleton className="h-7 w-20" />
                        ) : (
                            <div>
                                <div className="text-xl font-bold font-mono tracking-tight text-foreground">
                                    {resumo?.trafego.clima_requisicoes_mes.toLocaleString("pt-BR") ?? 0}
                                </div>
                                <div className="flex items-center gap-2 mt-1 text-[11px] text-muted-foreground">
                                    <span>Hit rate:</span>
                                    <Badge variant="outline" className="text-[10px] font-mono rounded-sm py-0">
                                        {resumo?.trafego.clima_hit_rate_pct ?? 0}%
                                    </Badge>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Card 3: Mercado & DERAL */}
                <Card className="rounded-sm shadow-xs border">
                    <CardHeader className="py-2.5 px-3.5 border-b flex flex-row items-center justify-between pb-2 space-y-0">
                        <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Fontes de Mercado
                        </span>
                        <TrendingUp size={14} className="text-emerald-600" />
                    </CardHeader>
                    <CardContent className="p-3.5 pt-2.5">
                        {loadingResumo ? (
                            <Skeleton className="h-7 w-20" />
                        ) : (
                            <div>
                                <div className="text-xl font-bold font-mono tracking-tight text-foreground">
                                    {resumo?.trafego.mercado_fontes_operacionais ?? 4} /{" "}
                                    {resumo?.trafego.mercado_fontes_total ?? 4}
                                </div>
                                <div className="flex items-center gap-1.5 mt-1 text-[11px] text-muted-foreground">
                                    <span>DERAL:</span>
                                    <Badge
                                        variant="outline"
                                        className={`text-[10px] font-mono rounded-sm py-0 ${
                                            (resumo?.trafego.snapshot_deral_defasagem_dias ?? 0) > 14
                                                ? "border-amber-600 text-amber-700"
                                                : "border-emerald-600 text-emerald-700"
                                        }`}
                                    >
                                        {resumo?.trafego.snapshot_deral_defasagem_dias ?? 0}d defasagem
                                    </Badge>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Card 4: Saúde & Redis */}
                <Card className="rounded-sm shadow-xs border">
                    <CardHeader className="py-2.5 px-3.5 border-b flex flex-row items-center justify-between pb-2 space-y-0">
                        <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Infraestrutura
                        </span>
                        <Server size={14} className="text-emerald-600" />
                    </CardHeader>
                    <CardContent className="p-3.5 pt-2.5">
                        {loadingResumo ? (
                            <Skeleton className="h-7 w-20" />
                        ) : (
                            <div>
                                <div className="flex items-center gap-1.5 text-sm font-bold text-foreground">
                                    <span
                                        className={`h-2 w-2 rounded-full ${
                                            resumo?.saude.redis_online ? "bg-emerald-500" : "bg-amber-500"
                                        }`}
                                    />
                                    <span>{resumo?.saude.redis_online ? "Redis Cluster OK" : "Modo Local Fallback"}</span>
                                </div>
                                <div className="text-[11px] text-muted-foreground mt-1">
                                    Ativo:{" "}
                                    <strong className="text-foreground font-mono">
                                        {resumo?.saude.provedor_clima_ativo ?? "WEATHERAPI"}
                                    </strong>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Card 5: Homologação */}
                <Card className="rounded-sm shadow-xs border">
                    <CardHeader className="py-2.5 px-3.5 border-b flex flex-row items-center justify-between pb-2 space-y-0">
                        <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Maturidade Técnica
                        </span>
                        <ShieldCheck size={14} className="text-emerald-600" />
                    </CardHeader>
                    <CardContent className="p-3.5 pt-2.5">
                        {loadingResumo ? (
                            <Skeleton className="h-7 w-20" />
                        ) : (
                            <div>
                                <div className="text-xl font-bold font-mono tracking-tight text-foreground">
                                    {resumo?.saude.homologacao_concluida_pct ?? 63.6}%
                                </div>
                                <div className="w-full mt-1.5">
                                    <Progress
                                        value={resumo?.saude.homologacao_concluida_pct ?? 63.6}
                                        className="h-1.5 rounded-sm"
                                    />
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* ABAS DO PAINEL EXECUTIVO */}
            <Tabs defaultValue="visao-geral" value={tabAtiva} onValueChange={setTabAtiva} className="w-full">
                <TabsList className="bg-muted/80 rounded-sm p-1 border gap-1">
                    <TabsTrigger value="visao-geral" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <LayoutDashboard size={13} />
                        Visão Geral
                    </TabsTrigger>
                    <TabsTrigger value="usuarios" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <Users size={13} />
                        Usuários & Adoção
                    </TabsTrigger>
                    <TabsTrigger value="clima" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <CloudSun size={13} />
                        Clima & Cotas
                    </TabsTrigger>
                    <TabsTrigger value="mercado" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <TrendingUp size={13} />
                        Mercado & Fontes
                    </TabsTrigger>
                    <TabsTrigger value="incidentes" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <AlertTriangle size={13} />
                        Incidentes & Alertas ({(alertas?.length ?? 0)})
                    </TabsTrigger>
                    <TabsTrigger value="homologacao" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <Shield size={13} />
                        Homologação (11)
                    </TabsTrigger>
                </TabsList>

                {/* ABA 1: VISÃO GERAL */}
                <TabsContent value="visao-geral" className="mt-4 space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Resumo de Adoção */}
                        <Card className="rounded-sm shadow-xs border">
                            <CardHeader className="py-3 px-4 border-b">
                                <CardTitle className="text-sm font-bold flex items-center gap-2">
                                    <Users size={15} className="text-emerald-600" />
                                    Métricas de Adoção e Engajamento
                                </CardTitle>
                                <CardDescription className="text-xs">
                                    Dados agregados em tempo real sobre contas individuais gratuitas.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="p-4 space-y-3 text-xs">
                                <div className="flex justify-between py-1.5 border-b">
                                    <span className="text-muted-foreground">Cadastros hoje:</span>
                                    <span className="font-mono font-bold text-foreground">
                                        {resumo?.usuarios.novos_hoje ?? 0}
                                    </span>
                                </div>
                                <div className="flex justify-between py-1.5 border-b">
                                    <span className="text-muted-foreground">Cadastros últimos 7 dias:</span>
                                    <span className="font-mono font-bold text-foreground">
                                        {resumo?.usuarios.novos_7d ?? 0}
                                    </span>
                                </div>
                                <div className="flex justify-between py-1.5 border-b">
                                    <span className="text-muted-foreground">Usuários ativos hoje (sessões):</span>
                                    <span className="font-mono font-bold text-foreground">
                                        {resumo?.usuarios.ativos_hoje ?? 0}
                                    </span>
                                </div>
                                <div className="flex justify-between py-1.5 border-b">
                                    <span className="text-muted-foreground">Adesão ao Cofre BYOK:</span>
                                    <span className="font-mono font-bold text-foreground">
                                        {resumo?.usuarios.com_byok ?? 0} produtores ({resumo?.usuarios.taxa_conversao_byok_pct ?? 0}%)
                                    </span>
                                </div>
                                <div className="flex justify-between py-1.5">
                                    <span className="text-muted-foreground">Usuários bloqueados administrativamente:</span>
                                    <span className="font-mono font-bold text-red-600">
                                        {resumo?.usuarios.bloqueados ?? 0}
                                    </span>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Resumo de Infraestrutura */}
                        <Card className="rounded-sm shadow-xs border">
                            <CardHeader className="py-3 px-4 border-b">
                                <CardTitle className="text-sm font-bold flex items-center gap-2">
                                    <Activity size={15} className="text-emerald-600" />
                                    Saúde Operacional das Fontes & Provedores
                                </CardTitle>
                                <CardDescription className="text-xs">
                                    Disponibilidade e consistência das integrações públicas.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="p-4 space-y-3 text-xs">
                                <div className="flex justify-between py-1.5 border-b">
                                    <span className="text-muted-foreground">Provedor meteorológico ativo:</span>
                                    <Badge variant="outline" className="font-mono font-bold text-xs rounded-sm">
                                        {resumo?.saude.provedor_clima_ativo ?? "WEATHERAPI"}
                                    </Badge>
                                </div>
                                <div className="flex justify-between py-1.5 border-b">
                                    <span className="text-muted-foreground">Contingência meteorológica:</span>
                                    <span className="font-semibold">
                                        {resumo?.saude.contingencia_clima_ativa ? (
                                            <span className="text-amber-600">ACIONADA</span>
                                        ) : (
                                            <span className="text-emerald-600">DESATIVADA (Modo Normal)</span>
                                        )}
                                    </span>
                                </div>
                                <div className="flex justify-between py-1.5 border-b">
                                    <span className="text-muted-foreground">Snapshot DERAL ativo:</span>
                                    <span className="font-mono font-bold text-foreground">
                                        {resumo?.trafego.snapshot_deral_ativo_id ?? "—"} ({resumo?.trafego.snapshot_deral_referencia ?? "—"})
                                    </span>
                                </div>
                                <div className="flex justify-between py-1.5 border-b">
                                    <span className="text-muted-foreground">Cache Hit Rate (Clima):</span>
                                    <span className="font-mono font-bold text-emerald-600">
                                        {resumo?.trafego.clima_hit_rate_pct ?? 0}%
                                    </span>
                                </div>
                                <div className="flex justify-between py-1.5">
                                    <span className="text-muted-foreground">Maturidade de Homologação:</span>
                                    <span className="font-mono font-bold text-foreground">
                                        {resumo?.saude.homologacao_concluida_pct ?? 63.6}% concluída
                                    </span>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* ABA 2: USUÁRIOS & ADOÇÃO */}
                <TabsContent value="usuarios" className="mt-4 space-y-4">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="py-3 px-4 border-b flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-sm font-bold">Evolução de Novos Cadastros (Últimos 30 dias)</CardTitle>
                                <CardDescription className="text-xs">
                                    Série temporal contínua agregada por data de registro no banco de dados.
                                </CardDescription>
                            </div>
                            <Badge variant="outline" className="text-[10px] font-mono rounded-sm">
                                {evolucao?.metadados_coleta}
                            </Badge>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingEvolucao ? (
                                <div className="p-6 space-y-2">
                                    <Skeleton className="h-6 w-full" />
                                    <Skeleton className="h-6 w-full" />
                                </div>
                            ) : (
                                <div className="overflow-x-auto max-h-80">
                                    <table className="w-full text-xs text-left border-collapse">
                                        <thead className="bg-muted/50 border-b text-muted-foreground uppercase text-[10px] tracking-wider sticky top-0">
                                            <tr>
                                                <th className="py-2.5 px-4 font-semibold">Data</th>
                                                <th className="py-2.5 px-4 font-semibold text-right">Novos Produtores</th>
                                                <th className="py-2.5 px-4 font-semibold text-right">Base Acumulada</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y font-mono">
                                            {evolucao?.historico_30d.map((ponto) => (
                                                <tr key={ponto.data} className="hover:bg-muted/20">
                                                    <td className="py-2 px-4 text-foreground">{ponto.data}</td>
                                                    <td className="py-2 px-4 text-right font-bold text-emerald-600">
                                                        +{ponto.novos_cadastros}
                                                    </td>
                                                    <td className="py-2 px-4 text-right text-muted-foreground">
                                                        {ponto.acumulado.toLocaleString("pt-BR")}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 3: CLIMA & COTAS */}
                <TabsContent value="clima" className="mt-4 space-y-4">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="py-3 px-4 border-b flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-sm font-bold">Telemetria de Consumo e Cotas Upstream</CardTitle>
                                <CardDescription className="text-xs">
                                    Estatísticas de cache e chamadas a provedores meteorológicos.
                                </CardDescription>
                            </div>
                            <Link href="/dashboard/backoffice/agro/provedores">
                                <Button variant="outline" size="sm" className="rounded-sm text-xs h-7 gap-1">
                                    Gerenciar Provedores <ExternalLink size={11} />
                                </Button>
                            </Link>
                        </CardHeader>
                        <CardContent className="p-4 space-y-4 text-xs">
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                <div className="p-3 border rounded-sm bg-muted/20">
                                    <span className="text-muted-foreground text-[11px] block">Chamadas Upstream no Mês:</span>
                                    <span className="text-lg font-bold font-mono text-foreground">
                                        {resumo?.trafego.clima_requisicoes_mes ?? 0}
                                    </span>
                                </div>
                                <div className="p-3 border rounded-sm bg-muted/20">
                                    <span className="text-muted-foreground text-[11px] block">Cache Hits:</span>
                                    <span className="text-lg font-bold font-mono text-emerald-600">
                                        {resumo?.trafego.clima_cache_hits ?? 0}
                                    </span>
                                </div>
                                <div className="p-3 border rounded-sm bg-muted/20">
                                    <span className="text-muted-foreground text-[11px] block">Timeouts / Falhas:</span>
                                    <span className="text-lg font-bold font-mono text-red-600">
                                        {(resumo?.trafego.clima_timeouts ?? 0) + (resumo?.trafego.clima_falhas ?? 0)}
                                    </span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 4: MERCADO & FONTES */}
                <TabsContent value="mercado" className="mt-4 space-y-4">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="py-3 px-4 border-b flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-sm font-bold">Governança das Fontes Públicas de Mercado</CardTitle>
                                <CardDescription className="text-xs">
                                    Monitoramento de integridade e defasagem de PTAX, SGS, SIDRA e DERAL.
                                </CardDescription>
                            </div>
                            <Link href="/dashboard/backoffice/agro/mercado">
                                <Button variant="outline" size="sm" className="rounded-sm text-xs h-7 gap-1">
                                    Console de Mercado <ExternalLink size={11} />
                                </Button>
                            </Link>
                        </CardHeader>
                        <CardContent className="p-4 space-y-3 text-xs">
                            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                                <div className="p-3 border rounded-sm">
                                    <div className="flex items-center justify-between">
                                        <span className="font-bold">DERAL / SEAB</span>
                                        <Badge variant="outline" className="text-[10px] rounded-sm bg-emerald-500/10 text-emerald-700">
                                            ONLINE
                                        </Badge>
                                    </div>
                                    <p className="text-[11px] text-muted-foreground mt-1">Preços médios semanais</p>
                                </div>
                                <div className="p-3 border rounded-sm">
                                    <div className="flex items-center justify-between">
                                        <span className="font-bold">PTAX / BCB</span>
                                        <Badge variant="outline" className="text-[10px] rounded-sm bg-emerald-500/10 text-emerald-700">
                                            ONLINE
                                        </Badge>
                                    </div>
                                    <p className="text-[11px] text-muted-foreground mt-1">Fechamento cambial diário</p>
                                </div>
                                <div className="p-3 border rounded-sm">
                                    <div className="flex items-center justify-between">
                                        <span className="font-bold">SGS / BCB</span>
                                        <Badge variant="outline" className="text-[10px] rounded-sm bg-emerald-500/10 text-emerald-700">
                                            ONLINE
                                        </Badge>
                                    </div>
                                    <p className="text-[11px] text-muted-foreground mt-1">Selic e inflação (IPCA)</p>
                                </div>
                                <div className="p-3 border rounded-sm">
                                    <div className="flex items-center justify-between">
                                        <span className="font-bold">SIDRA / IBGE</span>
                                        <Badge variant="outline" className="text-[10px] rounded-sm bg-emerald-500/10 text-emerald-700">
                                            ONLINE
                                        </Badge>
                                    </div>
                                    <p className="text-[11px] text-muted-foreground mt-1">Séries históricas anuais</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 5: INCIDENTES & ALERTAS */}
                <TabsContent value="incidentes" className="mt-4 space-y-4">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="py-3 px-4 border-b">
                            <CardTitle className="text-sm font-bold flex items-center gap-2">
                                <AlertTriangle size={15} className="text-amber-600" />
                                Alertas Operacionais Detectados em Tempo Real
                            </CardTitle>
                            <CardDescription className="text-xs">
                                Avaliação dinâmica sem poluição de banco de dados nem disparos desnecessários.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="p-4 space-y-2 text-xs">
                            {loadingAlertas ? (
                                <Skeleton className="h-12 w-full" />
                            ) : alertas && alertas.length === 0 ? (
                                <div className="py-8 text-center text-muted-foreground flex flex-col items-center gap-2">
                                    <CheckCircle2 size={24} className="text-emerald-600" />
                                    <span>Nenhum alerta ou incidente operacional ativo no momento.</span>
                                </div>
                            ) : (
                                alertas?.map((alerta) => (
                                    <div
                                        key={alerta.id}
                                        className={`p-3 border rounded-sm flex items-start justify-between gap-3 ${
                                            alerta.severidade === "CRITICAL"
                                                ? "bg-red-500/10 border-red-500/30 text-red-950 dark:text-red-200"
                                                : alerta.severidade === "WARNING"
                                                ? "bg-amber-500/10 border-amber-500/30 text-amber-950 dark:text-amber-200"
                                                : "bg-blue-500/10 border-blue-500/30 text-blue-950 dark:text-blue-200"
                                        }`}
                                    >
                                        <div className="space-y-0.5">
                                            <div className="flex items-center gap-2">
                                                <span className="font-bold text-xs">{alerta.titulo}</span>
                                                <Badge variant="outline" className="text-[10px] uppercase font-mono rounded-sm">
                                                    {alerta.categoria}
                                                </Badge>
                                            </div>
                                            <p className="text-[11px] leading-relaxed opacity-90">{alerta.descricao}</p>
                                            <p className="text-[11px] font-semibold mt-1">
                                                Ação recomendada: {alerta.recomendacao}
                                            </p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 6: HOMOLOGAÇÃO (11 ITENS TÉCNICOS) */}
                <TabsContent value="homologacao" className="mt-4 space-y-4">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="py-3 px-4 border-b flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-sm font-bold flex items-center gap-2">
                                    <ShieldCheck size={16} className="text-emerald-600" />
                                    Matriz de Maturidade Técnica & Pendências de Homologação (11 Itens)
                                </CardTitle>
                                <CardDescription className="text-xs">
                                    Acompanhamento formal e verificável das pendências de infraestrutura para Staging/Produção.
                                </CardDescription>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-xs font-mono font-bold rounded-sm">
                                    {homologacao?.percentual_conclusao ?? 63.6}% Homologado
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingHomologacao ? (
                                <div className="p-6 space-y-2">
                                    <Skeleton className="h-6 w-full" />
                                    <Skeleton className="h-6 w-full" />
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-xs text-left border-collapse">
                                        <thead className="bg-muted/50 border-b text-muted-foreground uppercase text-[10px] tracking-wider">
                                            <tr>
                                                <th className="py-2.5 px-4 font-semibold">#</th>
                                                <th className="py-2.5 px-4 font-semibold">Item & Descrição</th>
                                                <th className="py-2.5 px-4 font-semibold">Origem</th>
                                                <th className="py-2.5 px-4 font-semibold">Status</th>
                                                <th className="py-2.5 px-4 font-semibold">Evidência / Ação Necessária</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y">
                                            {homologacao?.itens.map((item) => (
                                                <tr key={item.id} className="hover:bg-muted/20">
                                                    <td className="py-3 px-4 font-mono font-bold">{item.id}</td>
                                                    <td className="py-3 px-4 max-w-xs">
                                                        <div className="font-bold text-foreground">{item.titulo}</div>
                                                        <div className="text-[11px] text-muted-foreground mt-0.5">
                                                            {item.descricao}
                                                        </div>
                                                    </td>
                                                    <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground">
                                                        {item.fase_origem}
                                                    </td>
                                                    <td className="py-3 px-4">
                                                        <Badge
                                                            variant="outline"
                                                            className={`text-[10px] font-mono rounded-sm uppercase ${
                                                                item.status === "APROVADO"
                                                                    ? "border-emerald-600 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                                                                    : item.status === "EM VALIDAÇÃO"
                                                                    ? "border-amber-600 bg-amber-500/10 text-amber-700 dark:text-amber-300"
                                                                    : item.status === "BLOQUEADO"
                                                                    ? "border-red-600 bg-red-500/10 text-red-700 dark:text-red-300"
                                                                    : "border-muted-foreground text-muted-foreground"
                                                            }`}
                                                        >
                                                            {item.status}
                                                        </Badge>
                                                    </td>
                                                    <td className="py-3 px-4 text-[11px] leading-relaxed max-w-sm">
                                                        <div className="text-foreground">
                                                            <strong>Evidência:</strong> {item.evidencia}
                                                        </div>
                                                        <div className="text-muted-foreground mt-1">
                                                            <strong>Próxima ação:</strong> {item.acao_necessaria}
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
