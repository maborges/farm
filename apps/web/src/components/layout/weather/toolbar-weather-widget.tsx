"use client";

import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useAppStore } from "@/lib/stores/app-store";
import { AlertTriangle, CalendarDays, Cloud, CloudDrizzle, CloudFog, CloudLightning, CloudRain, CloudSnow, Droplets, Gauge, Loader2, Sun, Thermometer, Wind } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

interface ClimaResumo {
    temperatura_atual: number | null;
    temperatura_min: number | null;
    temperatura_max: number | null;
    umidade: number | null;
    precipitacao_mm: number | null;
    vento_kmh: number | null;
    condicao: string | null;
    data_registro: string | null;
    alertas_ativos: number;
}

interface ClimaPeriodo {
    horario: string;
    temperatura_c: number | null;
    precipitacao_mm: number | null;
    probabilidade_chuva_pct: number | null;
    umidade_pct: number | null;
    vento_kmh: number | null;
    condicao: string | null;
}

interface ClimaPrevisao {
    data_previsao: string;
    precipitacao_mm: number | null;
    temp_max_c: number | null;
    temp_min_c: number | null;
    probabilidade_chuva_pct: number | null;
    periodos?: ClimaPeriodo[];
}

function WeatherIcon({ condition, className }: { condition?: string; className?: string }) {
    if (!condition) return <Cloud className={className} />;
    const c = condition.toLowerCase();
    if (c.includes("rain") || c.includes("chuva")) return <CloudRain className={className} />;
    if (c.includes("drizzle") || c.includes("garoa")) return <CloudDrizzle className={className} />;
    if (c.includes("thunder") || c.includes("tempestade")) return <CloudLightning className={className} />;
    if (c.includes("snow") || c.includes("neve")) return <CloudSnow className={className} />;
    if (c.includes("clear") || c.includes("limpo") || c.includes("sol")) return <Sun className={className} />;
    if (c.includes("fog") || c.includes("neblina")) return <CloudFog className={className} />;
    return <Cloud className={className} />;
}

export function ToolbarWeatherWidget() {
    const { activeFazendaId } = useAppStore();

    const { data: clima, isLoading: isLoadingResumo } = useQuery<ClimaResumo | null>({
        queryKey: ["clima-resumo", activeFazendaId],
        queryFn: async () => {
            if (!activeFazendaId) return null;
            return apiFetch(`/climatico/resumo/${activeFazendaId}`, {
                suppressErrorLog: true,
            });
        },
        enabled: !!activeFazendaId,
        refetchInterval: 1000 * 60 * 30, // 30 minutos
    });

    const { data: previsoes = [], isLoading: isLoadingPrevisao } = useQuery<ClimaPrevisao[]>({
        queryKey: ["clima-previsao-toolbar", activeFazendaId],
        queryFn: async () => {
            if (!activeFazendaId) return [];
            return apiFetch<ClimaPrevisao[]>(`/climatico/previsao/${activeFazendaId}?dias=5`, {
                suppressErrorLog: true,
            });
        },
        enabled: !!activeFazendaId,
        refetchInterval: 1000 * 60 * 30,
    });

    if (!activeFazendaId) return null;

    if (isLoadingResumo || isLoadingPrevisao) {
        return (
            <div className="flex items-center gap-1.5 px-2 py-1 text-xs text-muted-foreground border-l border-border">
                <Loader2 className="size-3 animate-spin" />
            </div>
        );
    }

    if (!clima || clima.temperatura_atual === null) {
        return null;
    }

    const hoje = new Date().toISOString().slice(0, 10);
    const previsaoHoje = previsoes.find((previsao) => previsao.data_previsao === hoje) ?? previsoes[0];
    const periodosHoje = previsaoHoje?.periodos ?? [];
    const proximoPeriodo = periodosHoje[0];
    const probabilidadeChuva = proximoPeriodo?.probabilidade_chuva_pct ?? previsaoHoje?.probabilidade_chuva_pct;
    const formatarHorario = (horario: string) => {
        const data = new Date(`${horario.replace(" ", "T")}Z`);
        return data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    };

    return (
        <Popover>
            <PopoverTrigger asChild>
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-9 gap-2 rounded-sm border-l border-border px-3 text-xs font-medium text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                    aria-label="Abrir informações climáticas"
                >
                    <WeatherIcon condition={clima.condicao} className="size-4 text-primary/80" />
                    <span className="font-semibold text-foreground">{Math.round(clima.temperatura_atual)}°</span>
                    <span className="hidden items-center gap-1 md:flex">
                        <Droplets className="size-3.5 text-cyan-600" />
                        {clima.umidade ?? "--"}%
                    </span>
                    {probabilidadeChuva !== null && probabilidadeChuva !== undefined && (
                        <span className="hidden items-center gap-1 text-blue-600 lg:flex">
                            <CloudRain className="size-3.5" />
                            {Math.round(probabilidadeChuva)}%
                        </span>
                    )}
                    {clima.alertas_ativos > 0 && <AlertTriangle className="size-3.5 text-amber-500" />}
                </Button>
            </PopoverTrigger>
            <PopoverContent align="end" sideOffset={8} className="w-[min(850px,calc(100vw-2rem))] rounded-sm p-0">
                <div className="border-b border-border/50 bg-white/10 px-4 py-3 backdrop-blur-sm">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <p className="text-sm font-semibold text-foreground">Condições climáticas</p>
                            <p className="text-[11px] text-muted-foreground">Atualização da unidade produtiva</p>
                        </div>
                        <WeatherIcon condition={clima.condicao} className="size-7 text-primary" />
                    </div>
                </div>
                
                <div className="grid grid-cols-1 divide-y md:grid-cols-3 md:divide-x md:divide-y-0 border-border">
                    {/* Coluna 1: Agora */}
                    <div className="p-4">
                        <div className="mb-3 text-xs font-semibold text-muted-foreground">Condições Atuais</div>
                        <div className="grid grid-cols-2 gap-2">
                            <Metric icon={<Thermometer className="size-3.5 text-red-500" />} label="Temperatura" value={`${Math.round(clima.temperatura_atual)}°C`} />
                            <Metric icon={<Droplets className="size-3.5 text-cyan-600" />} label="Umidade" value={`${clima.umidade ?? "--"}%`} />
                            <Metric icon={<Wind className="size-3.5 text-sky-600" />} label="Vento" value={`${clima.vento_kmh ?? "--"} km/h`} />
                            <Metric icon={<CloudRain className="size-3.5 text-blue-600" />} label="Chuva agora" value={`${clima.precipitacao_mm ?? 0} mm`} />
                            <Metric icon={<Thermometer className="size-3.5 text-orange-500" />} label="Máxima do dia" value={`${previsaoHoje?.temp_max_c ?? clima.temperatura_max ?? "--"}°C`} />
                            <Metric icon={<Thermometer className="size-3.5 text-indigo-500" />} label="Mínima do dia" value={`${previsaoHoje?.temp_min_c ?? clima.temperatura_min ?? "--"}°C`} />
                        </div>
                    </div>

                    {/* Coluna 2: Previsão dos próximos dias */}
                    {previsoes.length > 0 && (
                        <div className="p-4">
                            <div className="mb-3 flex items-center gap-2">
                                <CalendarDays className="size-3.5 text-primary" />
                                <p className="text-xs font-semibold">Próximos dias</p>
                            </div>
                            <div className="space-y-1.5">
                                {previsoes.slice(0, 6).map((previsao) => {
                                    const data = new Date(`${previsao.data_previsao}T12:00:00`);
                                    const dia = data.toLocaleDateString("pt-BR", { weekday: "short" }).replace(".", "");
                                    const dataFormatada = data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
                                    return (
                                        <div key={previsao.data_previsao} className="flex items-center gap-2 rounded-sm border border-border/50 bg-white/35 px-2 py-1.5 text-[11px] backdrop-blur-sm dark:bg-white/10">
                                            <span className="w-16 font-semibold capitalize">{dia} {dataFormatada}</span>
                                            <WeatherIcon condition={previsao.data_previsao === previsaoHoje?.data_previsao ? clima.condicao : undefined} className="size-3.5 text-primary/70" />
                                            <span className="ml-auto text-orange-600">{previsao.temp_max_c ?? "--"}°</span>
                                            <span className="text-indigo-600">{previsao.temp_min_c ?? "--"}°</span>
                                            <span className="flex items-center gap-0.5 text-blue-600">
                                                <CloudRain className="size-3" />
                                                {Math.round(previsao.probabilidade_chuva_pct ?? 0)}%
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Coluna 3: Próximos períodos */}
                    {periodosHoje.length > 0 && (
                        <div className="p-4">
                            <div className="mb-3 flex items-center gap-2">
                                <Gauge className="size-3.5 text-primary" />
                                <p className="text-xs font-semibold">Hoje</p>
                            </div>
                            <div className="max-h-[200px] space-y-1.5 overflow-y-auto pr-1">
                                {periodosHoje.slice(0, 8).map((periodo) => (
                                        <div key={periodo.horario} className="flex items-center justify-between rounded-sm border border-border/50 bg-white/35 px-2 py-1.5 text-[11px] backdrop-blur-sm dark:bg-white/10">
                                        <span className="w-12 font-semibold">{formatarHorario(periodo.horario)}</span>
                                        <span>{periodo.temperatura_c ?? "--"}°C</span>
                                        <span className="text-blue-600">{Math.round(periodo.probabilidade_chuva_pct ?? 0)}%</span>
                                        <span className="text-muted-foreground">{periodo.precipitacao_mm ?? 0} mm</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <div className="flex items-center justify-between border-t border-border bg-muted/10 px-4 py-2.5 text-[11px] text-muted-foreground">
                    <span>{clima.condicao || "Condição não informada"}</span>
                    <span>{clima.alertas_ativos > 0 ? `${clima.alertas_ativos} alerta(s)` : "Sem alertas"}</span>
                </div>
            </PopoverContent>
        </Popover>
    );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
    return (
        <div className="rounded-sm border border-border/50 bg-white/35 px-2.5 py-2 backdrop-blur-sm dark:bg-white/10">
            <div className="mb-1 flex items-center gap-1.5 text-[10px] text-muted-foreground">{icon}{label}</div>
            <p className="text-sm font-semibold text-foreground">{value}</p>
        </div>
    );
}
