"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CloudSun, Wind, Droplets, Thermometer, MapPin, CloudRain, AlertTriangle, Info, Calendar, RefreshCcw } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { RecomendacoesOperacionais } from "@/components/agricola/climatico/recomendacoes-operacionais";
import { RecomendacoesPecuaria } from "@/components/pecuaria/climatico/recomendacoes-pecuaria";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

interface ResumoClimatico {
    unidade_produtiva_id: string;
    data_registro: string | null;
    temperatura_atual: number | null;
    temperatura_min: number | null;
    temperatura_max: number | null;
    umidade: number | null;
    precipitacao_mm: number | null;
    vento_kmh: number | null;
    condicao: string | null;
    fonte: string | null;
    status_operacional: string;
    alertas_ativos: number;
}

interface AlertaClimatico {
    id: string;
    severity: string;
    priority: string;
    title: string;
    description: string;
    source_type: string;
    created_at: string;
}

interface PrevisaoClima {
    id: string;
    data_previsao: string;
    precipitacao_mm: number | null;
    temp_max_c: number | null;
    temp_min_c: number | null;
    probabilidade_chuva_pct: number | null;
    periodos?: PrevisaoPeriodo[];
    atualizado_em: string;
}

interface PrevisaoPeriodo {
    horario: string;
    temperatura_c: number | null;
    sensacao_c: number | null;
    precipitacao_mm: number | null;
    probabilidade_chuva_pct: number | null;
    umidade_pct: number | null;
    vento_kmh: number | null;
    condicao: string | null;
    icone: string | null;
}

const EMPTY_RESUMO: ResumoClimatico = {
    unidade_produtiva_id: "",
    data_registro: null,
    temperatura_atual: null,
    temperatura_min: null,
    temperatura_max: null,
    umidade: null,
    precipitacao_mm: null,
    vento_kmh: null,
    condicao: null,
    fonte: null,
    status_operacional: "SEM_DADOS",
    alertas_ativos: 0,
};

interface ClimaticoDashboardClientProps {
    mode?: "agricola" | "pecuaria";
}

export default function ClimaticoDashboardClient({ mode = "agricola" }: ClimaticoDashboardClientProps) {
    const { activeFazendaId } = useAppStore();
    const { toast } = useToast();

    const { data: resumo, error: resumoError, isLoading: isLoadingResumo } = useQuery<ResumoClimatico>({
        queryKey: ["agricola", "climatico", "resumo", activeFazendaId],
        queryFn: () => apiFetch(`/climatico/resumo/${activeFazendaId}`),
        enabled: !!activeFazendaId,
        retry: false,
    });

    const { data: alertas = [], error: alertasError, isLoading: isLoadingAlertas } = useQuery<AlertaClimatico[]>({
        queryKey: ["agricola", "climatico", "alertas", activeFazendaId],
        queryFn: () => apiFetch(`/climatico/alertas/${activeFazendaId}`),
        enabled: !!activeFazendaId,
        retry: false,
    });

    const { data: previsoes = [], error: previsoesError, isLoading: isLoadingPrevisao } = useQuery<PrevisaoClima[]>({
        queryKey: ["agricola", "climatico", "previsao", activeFazendaId],
        queryFn: () => apiFetch(`/climatico/previsao/${activeFazendaId}?dias=5`),
        enabled: !!activeFazendaId,
        retry: false,
    });

    const isLoading = isLoadingResumo || isLoadingAlertas || isLoadingPrevisao;

    const getStatusBadgeColor = (status?: string) => {
        if (status === "CRITICO") return "bg-red-500/10 text-red-600 border-red-200";
        if (status === "ATENCAO") return "bg-amber-500/10 text-amber-600 border-amber-200";
        if (status === "SEM_DADOS") return "bg-slate-500/10 text-slate-600 border-slate-200";
        return "bg-green-500/10 text-green-600 border-green-200";
    };

    const getSeverityBadge = (severity: string) => {
        if (severity === "CRITICAL") return <Badge variant="destructive" className="rounded-sm text-[10px]">Crítico</Badge>;
        if (severity === "WARNING") return <Badge variant="secondary" className="rounded-sm text-[10px] bg-amber-500 hover:bg-amber-600 text-white border-transparent">Atenção</Badge>;
        return <Badge variant="outline" className="rounded-sm text-[10px]">{severity}</Badge>;
    };

    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-32 w-full rounded-sm" />
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <Skeleton className="h-32 w-full rounded-sm" />
                    <Skeleton className="h-32 w-full rounded-sm" />
                    <Skeleton className="h-32 w-full rounded-sm" />
                    <Skeleton className="h-32 w-full rounded-sm" />
                </div>
            </div>
        );
    }

    const climateErrors = [resumoError, alertasError, previsoesError]
        .filter(Boolean)
        .map((error) => error instanceof Error ? error.message : "Erro desconhecido na API climática");

    if (climateErrors.length > 0 && !resumo) {
        return (
            <div className="p-6">
                <Card className="border-destructive/40">
                    <CardHeader>
                        <CardTitle className="text-destructive">Não foi possível carregar os dados climáticos</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>Tenant: {useAppStore.getState().tenant?.id ?? "não informado"}</p>
                        <p>Unidade produtiva: {activeFazendaId ?? "não informada"}</p>
                        {climateErrors.map((message, index) => <p key={`${message}-${index}`}>{message}</p>)}
                    </CardContent>
                </Card>
            </div>
        );
    }

    const clima = resumo ?? EMPTY_RESUMO;
    const hasData = resumo !== undefined && resumo.status_operacional !== "SEM_DADOS";

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title={`Estação Climática & Previsão ${mode === "pecuaria" ? "Pecuária" : ""}`}
                description={`Monitoramento climático para decisão de ${mode === "pecuaria" ? "manejo e bem-estar animal" : "plantio e colheita"}.`}
                icon={<CloudSun className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Clima", href: `/dashboard/${mode}/clima/monitoramento` }, { label: mode === "pecuaria" ? "Previsão Pecuária" : "Previsão Agrícola" }]}
                actions={
                    <div className="flex gap-2 items-center">
                        <button
                            onClick={() => {
                                toast({ title: "Sincronizando", description: "Buscando dados no OpenWeather..." });
                                apiFetch<{ message: string }>(`/climatico/sincronizar/${activeFazendaId}`, { method: "POST" })
                                    .then((res) => {
                                        if (res.message && res.message.includes("Erro")) {
                                            toast({ title: "Falha na Integração", description: res.message, variant: "destructive" });
                                        } else {
                                            toast({ title: "Sincronização Concluída", description: "O clima e a previsão foram atualizados." });
                                            window.location.reload();
                                        }
                                    })
                                    .catch(err => {
                                        console.error(err);
                                        toast({ title: "Erro", description: "Não foi possível comunicar com o servidor.", variant: "destructive" });
                                    });
                            }}
                            className="bg-primary text-primary-foreground hover:bg-primary/90 px-3 py-1.5 text-xs font-medium rounded-sm flex items-center gap-2"
                        >
                            <RefreshCcw size={14} />
                            Sincronizar
                        </button>
                        {hasData && (
                            <Badge variant="outline" className={`px-3 py-1 h-fit flex items-center gap-2 rounded-sm font-bold ${getStatusBadgeColor(resumo?.status_operacional)}`}>
                                <MapPin size={14} />
                                {clima.status_operacional === "CRITICO" && "Atenção Crítica"}
                                {clima.status_operacional === "ATENCAO" && "Atenção Requerida"}
                                {clima.status_operacional === "NORMAL" && "Clima Estável"}
                            </Badge>
                        )}
                        <Badge variant="secondary" className="px-3 py-1 bg-primary/10 text-primary border-primary/20 flex items-center gap-2 h-fit rounded-sm">
                            <Info size={14} />
                            Fonte: {clima.fonte || "Desconhecida"}
                        </Badge>
                    </div>
                }
            />

            {!hasData ? (
                <Card className="border-dashed border-2 border-border/60 bg-muted/30">
                    <CardContent className="p-16 flex flex-col items-center justify-center text-center space-y-4">
                        <CloudSun size={48} className="text-muted-foreground/50" />
                        <div>
                            <h3 className="text-lg font-bold">Nenhum Dado Climático Encontrado</h3>
                            <p className="text-sm text-muted-foreground max-w-sm">
                                A integração com o serviço meteorológico (OpenWeather) ainda não registrou dados para esta unidade produtiva ou está desativada.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            ) : (
                <>
                    {/* Current Weather Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <Card className="vuexy-card border-0 rounded-sm">
                            <CardContent className="p-6 flex items-center gap-4">
                                <div className="p-3 rounded-sm bg-orange-500/10 text-orange-600">
                                    <Thermometer size={24} />
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground uppercase font-semibold">Temperatura</p>
                                    <h3 className="text-2xl font-bold">{clima.temperatura_atual ?? "--"}°C</h3>
                                    <p className="text-[10px] text-muted-foreground font-medium">
                                        Máx: {clima.temperatura_max ?? "--"}°C | Mín: {clima.temperatura_min ?? "--"}°C
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="vuexy-card border-0 rounded-sm">
                            <CardContent className="p-6 flex items-center gap-4">
                                <div className="p-3 rounded-sm bg-blue-500/10 text-blue-600">
                                    <CloudRain size={24} />
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground uppercase font-semibold">Precipitação</p>
                                    <h3 className="text-2xl font-bold">{clima.precipitacao_mm ?? "--"}mm</h3>
                                    <p className="text-[10px] text-muted-foreground font-medium">Último registro</p>
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="vuexy-card border-0 rounded-sm">
                            <CardContent className="p-6 flex items-center gap-4">
                                <div className="p-3 rounded-sm bg-cyan-500/10 text-cyan-600">
                                    <Droplets size={24} />
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground uppercase font-semibold">Umidade Relativa</p>
                                    <h3 className="text-2xl font-bold">{clima.umidade ?? "--"}%</h3>
                                    <p className="text-[10px] text-muted-foreground font-medium">No momento</p>
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="vuexy-card border-0 rounded-sm">
                            <CardContent className="p-6 flex items-center gap-4">
                                <div className="p-3 rounded-sm bg-slate-500/10 text-slate-600">
                                    <Wind size={24} />
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground uppercase font-semibold">Vento</p>
                                    <h3 className="text-2xl font-bold">{clima.vento_kmh ?? "--"} km/h</h3>
                                    <p className="text-[10px] text-muted-foreground font-medium">Velocidade média</p>
                                </div>
                            </CardContent>
                        </Card>
                    </div>



                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                        <Card className="vuexy-card border-0 rounded-sm">
                            <CardHeader className="border-b p-5">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <AlertTriangle className="size-5 text-amber-500" />
                                        Alertas Climáticos Ativos
                                    </CardTitle>
                                    <Badge variant="outline" className="rounded-full bg-muted/50">{alertas.length}</Badge>
                                </div>
                            </CardHeader>
                            <CardContent className="p-0">
                                {alertas.length === 0 ? (
                                    <div className="p-10 text-center flex flex-col items-center text-muted-foreground">
                                        <CloudSun size={32} className="opacity-20 mb-3" />
                                        <p className="text-sm">Nenhum alerta climático ativo no momento.</p>
                                    </div>
                                ) : (
                                    <div className="divide-y divide-border/40">
                                        {alertas.map((alerta) => (
                                            <div key={alerta.id} className="p-5 flex flex-col gap-2 hover:bg-muted/20 transition-colors">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div>
                                                        <h4 className="text-sm font-bold">{alerta.title}</h4>
                                                        <p className="text-xs text-muted-foreground mt-1">{alerta.description}</p>
                                                    </div>
                                                    <div className="flex-shrink-0">
                                                        {getSeverityBadge(alerta.severity)}
                                                    </div>
                                                </div>
                                                <p className="text-[10px] text-muted-foreground/60 font-medium">
                                                    Registrado em: {new Date(alerta.created_at).toLocaleString('pt-BR')}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                        
                        <Card className="vuexy-card border-0 rounded-sm">
                            <CardHeader className="border-b p-5">
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <Info className="size-5 text-primary" />
                                    Último registro
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-6">
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center pb-2 border-b">
                                        <span className="text-sm text-muted-foreground font-medium">Data do Registro</span>
                                        <span className="text-sm font-bold">
                                            {clima.data_registro
                                                ? new Date(`${clima.data_registro}T12:00:00`).toLocaleDateString('pt-BR')
                                                : "--"}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center pb-2 border-b">
                                        <span className="text-sm text-muted-foreground font-medium">Status Operacional</span>
                                        <span className="text-sm font-bold capitalize">
                                            {clima.status_operacional.toLowerCase()}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center pb-2 border-b">
                                        <span className="text-sm text-muted-foreground font-medium">Fonte de Dados</span>
                                        <span className="text-sm font-bold">{clima.fonte || "--"}</span>
                                    </div>
                                    <div className="bg-primary/5 p-4 rounded-sm border border-primary/10 mt-4">
                                        <p className="text-xs font-medium text-primary">
                                            Os dados são atualizados regularmente pela integração com o serviço meteorológico.
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {mode === "agricola" && (
                        <div className="mt-8">
                            <RecomendacoesOperacionais />
                        </div>
                    )}
                    
                    {mode === "pecuaria" && (
                        <div className="mt-8">
                            <RecomendacoesPecuaria />
                        </div>
                    )}
                </>
            )}

            {/* Previsão do Tempo 5 Dias (independente de ter clima atual) */}
                    <div className="mt-8 space-y-4">
                        <div className="flex items-center gap-2 mb-4">
                            <Calendar className="size-5 text-primary" />
                            <h3 className="text-lg font-bold">Previsão do Tempo (5 dias)</h3>
                        </div>

                        {!previsoes.length ? (
                            <Card className="rounded-sm border-dashed">
                                <CardContent className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                                    <CloudRain className="size-12 mb-4 opacity-20" />
                                    <p>Nenhuma previsão disponível para esta unidade no momento.</p>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                                {previsoes.map((previsao) => {
                                    const date = new Date(previsao.data_previsao + "T12:00:00");
                                    const diaSemana = format(date, "EEEE", { locale: ptBR });
                                    const dataFormatada = format(date, "dd/MM", { locale: ptBR });

                                    return (
                                        <Card key={previsao.id} className="rounded-sm flex flex-col items-center text-center p-4 shadow-sm hover:shadow-md transition-shadow">
                                            <div className="text-sm font-medium capitalize text-muted-foreground mb-1">
                                                {diaSemana}
                                            </div>
                                            <div className="text-xl font-bold mb-4">
                                                {dataFormatada}
                                            </div>

                                            <div className="flex gap-4 mb-6">
                                                <div className="flex flex-col items-center text-red-500">
                                                    <Thermometer className="size-5 mb-1" />
                                                    <span className="text-lg font-bold">
                                                        {previsao.temp_max_c !== null ? Math.round(previsao.temp_max_c) : "--"}°
                                                    </span>
                                                    <span className="text-xs">Máx</span>
                                                </div>
                                                <div className="flex flex-col items-center text-blue-500">
                                                    <Thermometer className="size-5 mb-1" />
                                                    <span className="text-lg font-bold">
                                                        {previsao.temp_min_c !== null ? Math.round(previsao.temp_min_c) : "--"}°
                                                    </span>
                                                    <span className="text-xs">Mín</span>
                                                </div>
                                            </div>

                                            <div className="w-full space-y-2 bg-muted/30 rounded p-2 text-sm">
                                                <div className="flex justify-between items-center">
                                                    <span className="flex items-center gap-1 text-muted-foreground">
                                                        <CloudRain className="size-3.5" /> Chuva
                                                    </span>
                                                    <span className="font-semibold text-blue-600">
                                                        {previsao.precipitacao_mm !== null ? previsao.precipitacao_mm : 0} mm
                                                    </span>
                                                </div>
                                                <div className="flex justify-between items-center">
                                                    <span className="flex items-center gap-1 text-muted-foreground">
                                                        <Droplets className="size-3.5" /> Prob.
                                                    </span>
                                                    <span className="font-semibold">
                                                        {previsao.probabilidade_chuva_pct !== null ? Math.round(previsao.probabilidade_chuva_pct) : 0}%
                                                    </span>
                                                </div>
                                            </div>
                                            {(previsao.periodos ?? []).length > 0 && (
                                                <div className="mt-3 w-full space-y-1.5 text-left">
                                                    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                                        Previsão ao longo do dia
                                                    </p>
                                                    {(previsao.periodos ?? []).map((periodo) => {
                                                        const horario = new Date(periodo.horario.replace(" ", "T") + "Z");
                                                        return (
                                                            <div key={periodo.horario} className="rounded-sm border bg-background/70 px-2 py-1.5 text-xs">
                                                                <div className="flex items-center justify-between gap-2">
                                                                    <span className="font-medium">{format(horario, "HH:mm")}</span>
                                                                    <span className="font-semibold">
                                                                        {periodo.temperatura_c !== null ? Math.round(periodo.temperatura_c) : "--"}°
                                                                    </span>
                                                                    <span className="text-blue-600">
                                                                        {periodo.probabilidade_chuva_pct !== null ? Math.round(periodo.probabilidade_chuva_pct) : 0}%
                                                                    </span>
                                                                </div>
                                                                <div className="mt-1 flex items-center justify-between text-muted-foreground">
                                                                    <span>{periodo.condicao || "Sem descrição"}</span>
                                                                    <span>{periodo.precipitacao_mm ?? 0} mm</span>
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </Card>
                                    );
                                })}
                            </div>
                        )}
                    </div>
        </div>
    );
}
