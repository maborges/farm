"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/lib/stores/app-store";
import { fetchInteligenciaPecuaria } from "@/lib/pecuaria/clima-api";
import { RiscoTermicoCard } from "@/components/pecuaria/climatico/risco-termico-card";
import { HistoricoIthChart } from "@/components/pecuaria/climatico/historico-ith-chart";
import { PrevisaoPecuariaCards } from "@/components/pecuaria/climatico/previsao-pecuaria-cards";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

export function InteligenciaPecuariaClient() {
    const { activeFazendaId } = useAppStore();
    const [especie, setEspecie] = useState<string>("Bovino de Leite");

    const { data, isLoading, isError } = useQuery({
        queryKey: ["inteligencia-pecuaria", activeFazendaId, especie],
        queryFn: () => {
            if (!activeFazendaId) throw new Error("Fazenda não selecionada");
            return fetchInteligenciaPecuaria(activeFazendaId, especie);
        },
        enabled: !!activeFazendaId,
        refetchInterval: 1000 * 60 * 15, // 15 minutes
    });

    if (!activeFazendaId) {
        return (
            <Card>
                <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <AlertCircle className="size-10 mb-4 opacity-50" />
                    <p>Selecione uma fazenda no menu superior para visualizar o painel.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between bg-background/60 backdrop-blur-xl p-5 rounded-2xl border border-border/50 shadow-[0_4px_24px_-8px_rgba(0,0,0,0.1)] dark:shadow-none sticky top-6 z-20 transition-all">
                <div>
                    <h3 className="font-bold text-sm tracking-tight">Filtro de Análise</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        Os limites de tolerância térmica variam por espécie
                    </p>
                </div>
                <div className="w-full sm:w-72">
                    <Select value={especie} onValueChange={setEspecie}>
                        <SelectTrigger className="bg-background/80 hover:bg-background transition-colors h-10 rounded-xl">
                            <SelectValue placeholder="Selecione a espécie" />
                        </SelectTrigger>
                        <SelectContent className="rounded-xl">
                            <SelectItem value="Bovino de Leite" className="rounded-lg">Bovino de Leite</SelectItem>
                            <SelectItem value="Bovino de Corte" className="rounded-lg">Bovino de Corte</SelectItem>
                            <SelectItem value="Ovino" className="rounded-lg">Ovinos</SelectItem>
                            <SelectItem value="Caprino" className="rounded-lg">Caprinos</SelectItem>
                            <SelectItem value="Equino" className="rounded-lg">Equinos</SelectItem>
                            <SelectItem value="Suíno" className="rounded-lg">Suínos</SelectItem>
                            <SelectItem value="Bubalino" className="rounded-lg">Bubalinos</SelectItem>
                            <SelectItem value="Asinino" className="rounded-lg">Asininos</SelectItem>
                            <SelectItem value="Aves de Corte" className="rounded-lg">Aves de Corte</SelectItem>
                            <SelectItem value="Aves de Postura" className="rounded-lg">Aves de Postura</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {isLoading ? (
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 animate-pulse">
                    <div className="md:col-span-2 lg:col-span-2 space-y-4">
                        <Skeleton className="h-[220px] w-full rounded-2xl" />
                        <Skeleton className="h-[100px] w-full rounded-2xl" />
                    </div>
                    <div className="lg:col-span-1">
                        <Skeleton className="h-[340px] w-full rounded-2xl" />
                    </div>
                </div>
            ) : isError ? (
                <Card className="border-destructive/30 bg-gradient-to-r from-destructive/10 to-transparent rounded-2xl shadow-sm">
                    <CardContent className="flex items-center gap-4 py-8 text-destructive">
                        <div className="p-3 bg-destructive/10 rounded-full">
                            <AlertCircle className="size-6" />
                        </div>
                        <div>
                            <h3 className="font-semibold">Falha na Análise Climática</h3>
                            <p className="text-sm opacity-90 mt-1">Não foi possível carregar os dados de inteligência no momento. Tente novamente mais tarde.</p>
                        </div>
                    </CardContent>
                </Card>
            ) : data ? (
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                    <div className="md:col-span-2 lg:col-span-2">
                        <RiscoTermicoCard data={data} />
                    </div>
                    <div className="lg:col-span-3">
                        {!data.dados_atualizados && (
                            <Card className="border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-transparent rounded-xl shadow-sm">
                                <CardContent className="flex items-center gap-4 py-5 text-amber-900 dark:text-amber-300">
                                    <div className="p-2.5 bg-amber-500/20 rounded-full shrink-0">
                                        <AlertCircle className="size-5" />
                                    </div>
                                    <span className="text-sm font-medium leading-relaxed">O histórico climático está desatualizado. Recomenda-se atualizar a estação meteorológica antes de tomar decisões de manejo.</span>
                                </CardContent>
                            </Card>
                        )}
                        {data.alertas.length > 0 && (
                            <Card className="mt-6 border-red-500/20 bg-red-50/50 dark:bg-red-950/20 rounded-2xl shadow-sm overflow-hidden">
                                <div className="h-1 w-full bg-gradient-to-r from-red-500 to-orange-400" />
                                <CardContent className="space-y-3 py-5">
                                    <h3 className="text-sm font-bold flex items-center gap-2 text-red-700 dark:text-red-400">
                                        <AlertCircle className="size-4" />
                                        Alertas Climáticos Ativos
                                    </h3>
                                    <ul className="space-y-2">
                                        {data.alertas.map((alerta) => (
                                            <li key={alerta} className="text-sm text-muted-foreground flex items-start gap-2">
                                                <span className="mt-1.5 size-1.5 rounded-full bg-red-500/50 flex-shrink-0" />
                                                <span className="leading-relaxed">{alerta}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                    <div className="lg:col-span-3">
                        <HistoricoIthChart dados={data.historico} />
                    </div>
                    <div className="lg:col-span-3">
                        <PrevisaoPecuariaCards
                            previsao={data.previsao_ith}
                            estresse={data.estresse_previsto}
                            chuva={data.chuva_prevista}
                            janela={data.janela_manejo}
                        />
                    </div>
                </div>
            ) : (
                <Card className="border border-dashed border-muted-foreground/20 bg-gradient-to-b from-muted/10 to-muted/30 rounded-3xl shadow-none">
                    <CardContent className="flex flex-col items-center justify-center py-20 text-muted-foreground text-center">
                        <div className="p-6 bg-background rounded-full shadow-sm mb-6 relative">
                            <div className="absolute inset-0 bg-primary/5 rounded-full animate-ping opacity-75"></div>
                            <AlertCircle className="size-10 text-muted-foreground/40" />
                        </div>
                        <h3 className="text-xl font-semibold text-foreground">Sem Dados Climáticos Recentes</h3>
                        <p className="max-w-md mt-3 text-sm leading-relaxed">
                            Os painéis de inteligência zoossanitária e cálculo de risco térmico (ITH) baseiam-se na temperatura e umidade da fazenda nos últimos 2 dias. Registre novos dados para visualizar.
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
