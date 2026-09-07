"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
    FileText, Download, TrendingUp,
    PieChart as PieChartIcon,
    Printer,
    AlertCircle,
    ArrowRight, Map, History, Receipt, Lock, LineChart as LineChartIcon
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { formatCurrency } from "@/lib/utils";
import { useHasTier } from "@/hooks/use-has-tier";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Cell,
    PieChart, Pie, Legend, LineChart, Line, Area
} from 'recharts';
import { Badge } from "@/components/ui/badge";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "@/components/ui/select";

interface AgricolaReport {
    resumo: {
        total_hectares: number;
        safras_ativas: number;
        custo_medio_ha: number;
        previsao_colheita_ton: number;
        usando_ultima_safra_encerrada?: boolean;
    };
    produtividade_por_cultura: Array<{ cultura: string, area: number, produtividade: number, unidade: string }>;
    uso_insumos: Array<{ insumo: string, quantidade: number, unidade: string, custo: number }>;
    cronograma_atividades: Array<{ data: string, atividade: string, status: string }>;
}

interface TalhaoSimple {
    id: string;
    nome: string;
    area: number;
    cultura: string;
}

interface TalhaoDetail {
    id: string;
    nome: string;
    area: number;
    cultura_atual: string;
    data_plantio: string;
    dias_ciclo: number;
    estagio_fenologico: string;
    historico_produtividade: Array<{ safra: string, produtividade: number }>;
    custos_acumulados: {
        preparo_solo: number;
        sementes: number;
        fertilizantes: number;
        defensivos: number;
        operacoes: number;
        total: number;
        por_ha: number;
    };
    apontamentos_recentes: Array<{ data: string, tipo: string, detalhe: string }>;
}

interface ProfitabilityReport {
    lucro_total: number;
    margem_media: number;
    roi_geral: number;
    receita_total: number;
    por_talhao: Array<{
        id: string;
        nome: string;
        receita: number;
        custo: number;
        lucro: number;
        margem: number;
    }>;
    distribuicao_lucro_cultura: Array<{ name: string; value: number }>;
}

interface ChartPayloadEntry {
    color?: string;
    fill?: string;
    name?: string;
    value: number | string;
    unit?: string;
}

interface ChartTooltipProps {
    active?: boolean;
    payload?: ChartPayloadEntry[];
    label?: string | number;
    currency?: boolean;
}

const ChartTooltip = ({ active, payload, label, currency = false }: ChartTooltipProps) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-background/95 backdrop-blur-md border border-border p-3 rounded-sm shadow-2xl">
                <p className="text-[10px] font-bold text-muted-foreground uppercase mb-2 tracking-wider">{label}</p>
                {payload.map((entry, index) => (
                    <div key={index} className="flex items-center gap-3 py-1">
                        <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color || entry.fill }} />
                        <span className="text-xs font-medium text-foreground">{entry.name}:</span>
                        <span className="text-xs font-black ml-auto">
                            {currency ? formatCurrency(Number(entry.value)) : entry.value}
                            {entry.unit ? ` ${entry.unit}` : ""}
                        </span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

const tarefasColumns: ColumnDef<any>[] = [
    {
        id: "data",
        header: "Data",
        accessorKey: "data",
        cell: (val: any) => new Date(val).toLocaleDateString('pt-BR'),
    },
    {
        id: "atividade",
        header: "Tarefa",
        accessorKey: "atividade",
    },
    {
        id: "status",
        header: "Status",
        accessorKey: "status",
        cell: (val: any) => <Badge variant="secondary">{val}</Badge>
    }
];

const plColumns: ColumnDef<any>[] = [
    {
        id: "nome",
        header: "Talhão",
        accessorKey: "nome",
        cell: (val: any) => <span className="font-bold">{val}</span>
    },
    {
        id: "receita",
        header: "Receita Bruta",
        accessorKey: "receita",
        cell: (val: any) => <span className="font-medium">{formatCurrency(val)}</span>,
        exportFormat: (val: any) => formatCurrency(val)
    },
    {
        id: "custo",
        header: "Custo Total",
        accessorKey: "custo",
        cell: (val: any) => <span className="font-medium text-red-500/80">{formatCurrency(val)}</span>,
        exportFormat: (val: any) => formatCurrency(val)
    },
    {
        id: "lucro",
        header: "Lucro Líquido",
        accessorKey: "lucro",
        cell: (val: any) => <span className="font-black text-emerald-600">{formatCurrency(val)}</span>,
        exportFormat: (val: any) => formatCurrency(val)
    },
    {
        id: "margem",
        header: "Margem %",
        accessorKey: "margem",
        cell: (val: any) => (
            <div className="flex justify-end">
                <Badge className={`${Number(val) > 30 ? 'bg-emerald-500/10 text-emerald-600' : 'bg-amber-500/10 text-amber-600'} border-none font-bold`}>
                    {val}%
                </Badge>
            </div>
        )
    }
];

export default function AgricolaReportsPage() {
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    const [selectedTalhaoId, setSelectedTalhaoId] = useState<string | null>(null);
    useMonetizationPromptTracking(!hasProfessionalTier, {
        feature: "agricola.relatorios",
        surface: "agricola.relatorios.page",
        requiredTier: "PROFISSIONAL",
        ctaLabel: "Ver planos",
    });

    const { data: report, isLoading: isLoadingGeneral } = useQuery<AgricolaReport>({
        queryKey: ["agricola", "reports", "summary"],
        queryFn: () => apiFetch("/reports/agricola/summary"),
        enabled: hasProfessionalTier,
    });

    const { data: talhoes, isLoading: isLoadingTalhoes } = useQuery<TalhaoSimple[]>({
        queryKey: ["agricola", "reports", "talhoes"],
        queryFn: () => apiFetch("/reports/agricola/talhoes"),
        enabled: hasProfessionalTier,
    });

    const { data: talhaoDetail, isLoading: isLoadingDetail } = useQuery<TalhaoDetail>({
        queryKey: ["agricola", "reports", "talhao", selectedTalhaoId],
        queryFn: () => apiFetch(`/reports/agricola/talhao/${selectedTalhaoId}`),
        enabled: hasProfessionalTier && !!selectedTalhaoId
    });

    const { data: profitability } = useQuery<ProfitabilityReport>({
        queryKey: ["agricola", "reports", "profitability"],
        queryFn: () => apiFetch("/reports/agricola/profitability"),
        enabled: hasProfessionalTier,
    });

    if (!hasProfessionalTier) {
        return (
            <div className="p-6 space-y-6">
                <PageHeader
                    title="Centro de Relatórios Agrícola"
                    description="Análise consolidada de safras, produtividade e custos."
                    breadcrumbs={[
                        { label: "Dashboard", href: "/dashboard" },
                        { label: "Agrícola", href: "/dashboard/agricola" },
                        { label: "Relatórios" }
                    ]}
                    actions={
                        <Button asChild size="sm" variant="outline" className="rounded-sm">
                            <Link href="/dashboard/agricola/dre">
                                <LineChartIcon className="size-3.5 mr-1.5" />
                                DRE agrícola v1
                            </Link>
                        </Button>
                    }
                    icon={<FileText className="text-primary" size={22} />}
                />
                <Alert className="rounded-sm">
                    <Lock className="size-4" />
                    <AlertTitle>Relatórios agrícolas disponíveis no PROFISSIONAL</AlertTitle>
                    <AlertDescription className="space-y-3">
                        <p>
                            A operação agrícola básica permanece acessível. Relatórios gerenciais, lucratividade e insights exigem tier PROFISSIONAL.
                        </p>
                        <Button
                            asChild
                            size="sm"
                            className="rounded-sm"
                            onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                                feature: "agricola.relatorios",
                                surface: "agricola.relatorios.page",
                                requiredTier: "PROFISSIONAL",
                                ctaLabel: "Ver planos",
                            })}
                        >
                            <Link href="/dashboard/settings/billing">Ver planos</Link>
                        </Button>
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    if (isLoadingGeneral || isLoadingTalhoes) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-64 w-full rounded-sm" />
                <Skeleton className="h-96 w-full rounded-sm" />
            </div>
        );
    }

    const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'];

    return (
        <div className="p-6 space-y-6">
            <svg style={{ height: 0, width: 0, position: 'absolute' }}>
                <defs>
                    <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.8} />
                        <stop offset="100%" stopColor="#059669" stopOpacity={0.4} />
                    </linearGradient>
                    <linearGradient id="lineAreaGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                </defs>
            </svg>
            <PageHeader
                title="Centro de Relatórios Agrícola"
                description="Análise consolidada de safras, produtividade e custos."
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Agrícola", href: "/dashboard/agricola" },
                    { label: "Relatórios" }
                ]}
                icon={<FileText className="text-primary" size={22} />}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" className="gap-2">
                            <Printer size={14} /> Imprimir
                        </Button>
                        <Button variant="outline" size="sm" className="gap-2">
                            <Download size={14} /> Exportar PDF
                        </Button>
                    </div>
                }
            />

            <Tabs defaultValue="geral" className="w-full">
                <TabsList className="grid w-full max-w-2xl grid-cols-3 p-1 rounded-sm">
                    <TabsTrigger value="geral" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold rounded-sm">Visão Geral Fazenda</TabsTrigger>
                    <TabsTrigger value="talhao" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold rounded-sm">Análise por Talhão</TabsTrigger>
                    <TabsTrigger value="lucratividade" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold rounded-sm">Lucratividade & ROI</TabsTrigger>
                </TabsList>

                <TabsContent value="geral" className="space-y-6 pt-6">
                    {report?.resumo.usando_ultima_safra_encerrada && (
                        <Alert className="rounded-sm">
                            <AlertCircle className="size-4" />
                            <AlertTitle>Exibindo dados da última safra encerrada</AlertTitle>
                            <AlertDescription>
                                Não há nenhuma safra em andamento no momento. Os números abaixo refletem a
                                safra mais recente já encerrada, para referência.
                            </AlertDescription>
                        </Alert>
                    )}
                    {/* Quick Stats Grid */}
                    <div className="grid gap-6 md:grid-cols-4">
                        <Card className="shadow-sm rounded-sm">
                            <CardHeader className="pb-1 px-4 pt-4">
                                <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Área Total Gerenciada</CardTitle>
                            </CardHeader>
                            <CardContent className="px-4 pb-4">
                                <div className="text-2xl font-black text-blue-600">{report?.resumo.total_hectares} ha</div>
                            </CardContent>
                        </Card>
                        <Card className="shadow-sm rounded-sm">
                            <CardHeader className="pb-1 px-4 pt-4">
                                <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Previsão Colheita</CardTitle>
                            </CardHeader>
                            <CardContent className="px-4 pb-4">
                                <div className="text-2xl font-black text-amber-600">{report?.resumo.previsao_colheita_ton.toLocaleString()} ton</div>
                            </CardContent>
                        </Card>
                        <Card className="shadow-sm rounded-sm">
                            <CardHeader className="pb-1 px-4 pt-4">
                                <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Custo Médio / ha</CardTitle>
                            </CardHeader>
                            <CardContent className="px-4 pb-4">
                                <div className="text-2xl font-black text-emerald-600">{formatCurrency(report?.resumo.custo_medio_ha || 0)}</div>
                            </CardContent>
                        </Card>
                        <Card className="shadow-sm rounded-sm">
                            <CardHeader className="pb-1 px-4 pt-4">
                                <CardTitle className="text-[10px] font-black uppercase text-primary/60 tracking-widest">Safras Ativas</CardTitle>
                            </CardHeader>
                            <CardContent className="px-4 pb-4">
                                <div className="text-2xl font-black text-primary">{report?.resumo.safras_ativas}</div>
                            </CardContent>
                        </Card>
                    </div>

                    <div className="grid gap-6 md:grid-cols-2">
                        {/* Productivity Chart */}
                        <Card className="shadow-sm rounded-sm">
                            <CardHeader>
                                <CardTitle className="text-base flex items-center gap-2">
                                    <TrendingUp className="size-4 text-primary" /> Produtividade Estimada por Cultura
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="h-[300px] w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={report?.produtividade_por_cultura}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                                            <XAxis dataKey="cultura" axisLine={false} tickLine={false} />
                                            <YAxis axisLine={false} tickLine={false} />
                                            <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(0,0,0,0.05)' }} />
                                            <Bar dataKey="produtividade" name="Produtividade" fill="url(#barGradient)" radius={[8, 8, 0, 0]} barSize={40} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Input Usage */}
                        <Card className="shadow-sm rounded-sm">
                            <CardHeader>
                                <CardTitle className="text-base flex items-center gap-2">
                                    <PieChartIcon className="size-4 text-blue-500" /> Distribuição de Custos (Insumos)
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="h-[300px] w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={report?.uso_insumos}
                                                cx="50%"
                                                cy="50%"
                                                innerRadius={60}
                                                outerRadius={80}
                                                paddingAngle={5}
                                                dataKey="custo"
                                                nameKey="insumo"
                                            >
                                                {report?.uso_insumos.map((_, index) => (
                                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                                ))}
                                            </Pie>
                                            <Tooltip content={<ChartTooltip currency />} />
                                            <Legend />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    <div className="grid gap-6 md:grid-cols-3">
                        <Card className="md:col-span-2 shadow-sm rounded-sm">
                            <CardHeader>
                                <CardTitle className="text-base">Próximas Tarefas Planejadas</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <DataTable 
                                    data={report?.cronograma_atividades || []} 
                                    columns={tarefasColumns} 
                                    exportFileName="tarefas" 
                                />
                            </CardContent>
                        </Card>

                        <Card className="shadow-sm rounded-sm">
                            <CardHeader>
                                <CardTitle className="text-base flex items-center gap-2">
                                    <AlertCircle className="h-4 w-4 text-amber-500" /> Alertas
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="p-3 bg-amber-500/5 rounded-sm border border-amber-200/50 text-xs text-amber-700">
                                    <strong>Manutenção Vencida:</strong> Trator Case IH Puma 230.
                                </div>
                                <div className="p-3 bg-red-500/5 rounded-sm border border-red-200/50 text-xs text-red-700">
                                    <strong>Crítico:</strong> Janela de pulverização fecha em 48 h.
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="talhao" className="space-y-6 pt-6">
                    <div className="flex items-center gap-4 bg-muted/30 p-4 rounded-sm border border-border">
                        <div className="flex-1 max-w-sm">
                            <Select onValueChange={setSelectedTalhaoId}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Selecione um Talhão..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {talhoes?.map(t => (
                                        <SelectItem key={t.id} value={t.id}>{t.nome} ({t.area} ha) - {t.cultura}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        {selectedTalhaoId && (
                            <Badge variant="secondary" className="px-3 py-1">
                                {talhaoDetail?.cultura_atual}
                            </Badge>
                        )}
                    </div>

                    {selectedTalhaoId ? (
                        isLoadingDetail ? (
                            <Skeleton className="h-96 w-full" />
                        ) : (
                            <div className="grid gap-8 md:grid-cols-12">
                                <div className="md:col-span-8 space-y-6">
                                    {/* History Chart */}
                                    <Card className="shadow-sm rounded-sm">
                                        <CardHeader>
                                            <CardTitle className="text-base flex items-center gap-2">
                                                <History className="h-4 w-4 text-primary" /> Histórico de Produtividade (sc/ha)
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="h-[250px] w-full">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <LineChart data={talhaoDetail?.historico_produtividade}>
                                                        <defs>
                                                            <linearGradient id="colorProd" x1="0" y1="0" x2="0" y2="1">
                                                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                                            </linearGradient>
                                                        </defs>
                                                        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                                                        <XAxis dataKey="safra" axisLine={false} tickLine={false} tick={{ fontSize: 10 }} />
                                                        <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10 }} />
                                                        <Tooltip content={<ChartTooltip />} />
                                                        <Area type="monotone" dataKey="produtividade" stroke="none" fillOpacity={1} fill="url(#colorProd)" />
                                                        <Line type="monotone" dataKey="produtividade" name="Produtividade" stroke="#10b981" strokeWidth={4} dot={{ r: 6, fill: '#10b981', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 8, strokeWidth: 0 }} />
                                                    </LineChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    {/* Recent Postings */}
                                    <Card className="shadow-sm rounded-sm">
                                        <CardHeader>
                                            <CardTitle className="text-base flex items-center gap-2">
                                                <Map className="h-4 w-4 text-blue-500" /> Operações Recentes no Talhão
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-4">
                                                {talhaoDetail?.apontamentos_recentes.map((ap, i) => (
                                                    <div key={i} className="flex gap-4 p-4 rounded-sm border border-border bg-muted/10 hover:bg-muted/20 transition-colors">
                                                        <div className="min-w-[80px] text-xs font-bold text-muted-foreground uppercase pt-1">
                                                            {new Date(ap.data).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                                                        </div>
                                                        <div className="flex-1">
                                                            <p className="font-bold text-sm text-foreground">{ap.tipo}</p>
                                                            <p className="text-xs text-muted-foreground mt-1">{ap.detalhe}</p>
                                                        </div>
                                                        <ArrowRight className="h-4 w-4 text-muted-foreground self-center" />
                                                    </div>
                                                ))}
                                            </div>
                                        </CardContent>
                                    </Card>
                                </div>

                                <div className="md:col-span-4 space-y-6">
                                    {/* Plant Stats */}
                                    <Card className="shadow-sm rounded-sm">
                                        <CardHeader>
                                            <CardTitle className="text-base flex items-center gap-2">
                                                <TrendingUp className="h-4 w-4 text-primary" /> Status do Ciclo
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent className="pt-6 space-y-6">
                                            <div>
                                                <p className="text-[10px] text-muted-foreground uppercase font-bold">Data Plantio</p>
                                                <p className="text-lg font-black">{talhaoDetail?.data_plantio ? new Date(talhaoDetail.data_plantio).toLocaleDateString('pt-BR') : '-'}</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] text-muted-foreground uppercase font-bold">Estágio Atual</p>
                                                <p className="text-lg font-black text-primary">{talhaoDetail?.estagio_fenologico}</p>
                                            </div>
                                            <div className="pt-4 border-t">
                                                <div className="flex justify-between items-end mb-2">
                                                    <span className="text-xs font-bold">Progresso Safra</span>
                                                    <span className="text-xs font-black">{talhaoDetail?.dias_ciclo} Dias</span>
                                                </div>
                                                <div className="h-3 w-full bg-muted rounded-full overflow-hidden">
                                                    <div className="h-full bg-primary" style={{ width: '65%' }}></div>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    {/* Cost Summary */}
                                    <Card className="shadow-sm rounded-sm">
                                        <CardHeader>
                                            <CardTitle className="text-base flex items-center gap-2">
                                                <Receipt className="h-4 w-4 text-red-500" /> Resumo de Custos
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent className="space-y-2">
                                            <div className="flex justify-between text-xs py-1 border-b">
                                                <span className="text-muted-foreground">Insumos (Sementes/Específ.)</span>
                                                <span className="font-bold">{formatCurrency((talhaoDetail?.custos_acumulados.sementes || 0) + (talhaoDetail?.custos_acumulados.fertilizantes || 0))}</span>
                                            </div>
                                            <div className="flex justify-between text-xs py-1 border-b">
                                                <span className="text-muted-foreground">Defensivos</span>
                                                <span className="font-bold">{formatCurrency(talhaoDetail?.custos_acumulados.defensivos || 0)}</span>
                                            </div>
                                            <div className="flex justify-between text-xs py-1 border-b">
                                                <span className="text-muted-foreground">Operações/Mquinas</span>
                                                <span className="font-bold">{formatCurrency(talhaoDetail?.custos_acumulados.operacoes || 0)}</span>
                                            </div>
                                            <div className="mt-4 pt-4 border-t-2 border-primary/10">
                                                <div className="flex justify-between items-center">
                                                    <span className="text-sm font-black text-primary">INVESTIMENTO TOTAL</span>
                                                    <span className="text-lg font-black">{formatCurrency(talhaoDetail?.custos_acumulados.total || 0)}</span>
                                                </div>
                                                <p className="text-[10px] text-right text-muted-foreground mt-1">Custo Médio: {formatCurrency(talhaoDetail?.custos_acumulados.por_ha || 0)} / ha</p>
                                            </div>
                                        </CardContent>
                                    </Card>
                                </div>
                            </div>
                        )
                    ) : (
                        <div className="flex flex-col items-center justify-center p-20 text-center border-2 border-dashed rounded-sm bg-muted/10">
                            <Map className="h-12 w-12 text-muted-foreground mb-4 opacity-20" />
                            <h3 className="text-xl font-bold text-muted-foreground">Nenhum Talhão Selecionado</h3>
                            <p className="text-muted-foreground max-w-xs mt-2">Selecione um talhão no menu acima para ver o detalhamento individual de safra, custos e operações.</p>
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="lucratividade" className="space-y-6 pt-6">
                    <div className="grid gap-6 md:grid-cols-4">
                        <Card className="shadow-sm rounded-sm">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-[10px] font-black uppercase text-emerald-700 tracking-widest">Lucro Líquido Total</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-black text-emerald-600">{formatCurrency(profitability?.lucro_total || 0)}</div>
                            </CardContent>
                        </Card>

                        <Card className="shadow-sm rounded-sm">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Margem Líquida Média</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-black">{profitability?.margem_media}%</div>
                            </CardContent>
                        </Card>

                        <Card className="shadow-sm rounded-sm">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">ROI (Retorno sobre Invest.)</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-black text-primary">{profitability?.roi_geral}x</div>
                            </CardContent>
                        </Card>

                        <Card className="shadow-sm rounded-sm">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Receita Bruta Est.</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-black">{formatCurrency(profitability?.receita_total || 0)}</div>
                            </CardContent>
                        </Card>
                    </div>

                    <div className="grid gap-6 md:grid-cols-12">
                        <Card className="md:col-span-8 shadow-sm rounded-sm overflow-hidden">
                            <CardHeader className="border-b bg-muted/20">
                                <CardTitle className="text-lg font-black flex items-center gap-2 italic">
                                    <TrendingUp className="size-5 text-primary" /> P&L por Talhão (Comparativo)
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <DataTable 
                                    data={profitability?.por_talhao || []} 
                                    columns={plColumns} 
                                    exportFileName="pl_talhoes" 
                                />
                            </CardContent>
                        </Card>

                        <div className="md:col-span-4 space-y-6">
                            <Card className="shadow-sm rounded-sm">
                                <CardHeader>
                                    <CardTitle className="text-sm font-black uppercase tracking-widest">Origem do Lucro (Cultura)</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="h-[240px] w-full">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <PieChart>
                                                <Pie
                                                    data={profitability?.distribuicao_lucro_cultura}
                                                    cx="50%"
                                                    cy="50%"
                                                    innerRadius={40}
                                                    outerRadius={70}
                                                    paddingAngle={8}
                                                    dataKey="value"
                                                >
                                                    {profitability?.distribuicao_lucro_cultura.map((_, index) => (
                                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                                    ))}
                                                </Pie>
                                                <Tooltip content={<ChartTooltip currency />} />
                                            </PieChart>
                                        </ResponsiveContainer>
                                    </div>
                                    <div className="mt-4 space-y-2">
                                        {profitability?.distribuicao_lucro_cultura.map((item, i) => (
                                            <div key={i} className="flex justify-between items-center text-xs">
                                                <div className="flex items-center gap-2">
                                                    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                                                    <span className="font-bold">{item.name}</span>
                                                </div>
                                                <span className="text-muted-foreground">{formatCurrency(item.value)}</span>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>

                            <div className="p-6 bg-primary rounded-sm text-primary-foreground relative overflow-hidden group">
                                <div className="relative z-10 space-y-4">
                                    <h4 className="text-sm font-black uppercase tracking-[0.2em] opacity-80">Insights da IA</h4>
                                    <p className="text-xs font-medium leading-relaxed italic">
                                        O Talhão 02 apresenta o melhor ROI (48%). Recomendamos aumentar a adubação nitrogenada no próximo ciclo para replicar o resultado no Talhão 08.
                                    </p>
                                    <Button variant="outline" size="sm" className="w-full rounded-sm border-white/20 bg-white/10 hover:bg-white/20 text-white font-black text-[10px] uppercase">
                                        Explorar Mais Insights
                                    </Button>
                                </div>
                                <div className="absolute -right-8 -bottom-8 opacity-10 group-hover:rotate-12 transition-transform duration-500">
                                    <TrendingUp size={140} />
                                </div>
                            </div>
                        </div>
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}
