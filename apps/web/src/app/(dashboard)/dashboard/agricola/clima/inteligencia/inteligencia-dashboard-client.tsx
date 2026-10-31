"use client";

import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/lib/stores/app-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CloudSun, BrainCircuit, RefreshCcw } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { GduCard } from "@/components/agricola/climatico/gdu-card";
import { AnaliseRisco } from "@/components/agricola/climatico/analise-risco";
import { GraficoHistorico } from "@/components/agricola/climatico/grafico-historico";
import { fetchInteligenciaClimatica, fetchHistoricoClima } from "@/lib/agricola/clima-api";
import { apiFetch } from "@/lib/api";
import { JanelaPulverizacaoCard } from "@/components/clima/inteligencia/agricultura/janela-pulverizacao";
import { BalancoHidricoCard } from "@/components/clima/inteligencia/agricultura/balanco-hidrico";
import { RiscoDoencasCard } from "@/components/clima/inteligencia/agricultura/risco-doencas";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function InteligenciaDashboardClient() {
    const { activeFazendaId } = useAppStore();
    const { toast } = useToast();

    const { data: inteligencia, error: inteligenciaError, isLoading: loadingIntel, refetch: refetchIntel } = useQuery({
        queryKey: ["agricola", "climatico", "inteligencia", activeFazendaId],
        queryFn: () => fetchInteligenciaClimatica(activeFazendaId!),
        enabled: !!activeFazendaId,
        retry: false,
    });

    const { data: rawHistorico, isLoading: loadingHist, refetch: refetchHist } = useQuery({
        queryKey: ["historico-clima", activeFazendaId],
        queryFn: () => fetchHistoricoClima(activeFazendaId ?? "", 30),
        enabled: !!activeFazendaId,
    });

    const router = useRouter();

    useEffect(() => {
        if (inteligencia?.agricultura?.risco_doencas) {
            const hasAutoCopied = inteligencia.agricultura.risco_doencas.some(r => r.auto_copied);
            if (hasAutoCopied) {
                toast({
                    title: "Modelos Personalizados!",
                    description: "Foram copiados modelos fitossanitários globais para a sua fazenda. Você pode personalizar os alertas.",
                    action: {
                        label: "Personalizar",
                            onClick: () => router.push("/dashboard/agricola/clima/inteligencia/modelos")
                    },
                    duration: 10000,
                });
            }
        }
    }, [inteligencia?.agricultura?.risco_doencas, toast, router]);

    const isLoading = loadingIntel || loadingHist;
    const refetch = async () => {
        await Promise.all([refetchIntel(), refetchHist()]);
    };

    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-32 w-full rounded-sm" />
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mt-6">
                    <div className="lg:col-span-1 space-y-6">
                        <Skeleton className="h-32 w-full rounded-sm" />
                        <Skeleton className="h-48 w-full rounded-sm" />
                    </div>
                    <div className="lg:col-span-3">
                        <Skeleton className="h-96 w-full rounded-sm" />
                    </div>
                </div>
            </div>
        );
    }

    if (inteligenciaError) {
        return (
            <div className="p-6">
                <Card className="border-destructive/40">
                    <CardHeader>
                        <CardTitle className="text-destructive">Erro na Inteligência Climática</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>Produtor: {useAppStore.getState().tenant?.id ?? "não informado"}</p>
                        <p>Unidade produtiva: {activeFazendaId ?? "não informada"}</p>
                        <p>{inteligenciaError instanceof Error ? inteligenciaError.message : "Erro desconhecido ao carregar os dados avançados."}</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const hasData = (inteligencia?.historico?.length ?? 0) > 0;

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Inteligência Climática"
                description="Painel avançado de monitoramento fenológico, riscos e histórico."
                icon={<BrainCircuit className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Clima", href: "/dashboard/agricola/clima/monitoramento" }, { label: "Inteligência" }]}
                actions={
                    <div className="flex gap-2 items-center">
                        <button
                            onClick={() => {
                                toast({ title: "Atualizando", description: "Buscando dados no servidor..." });
                                refetch().then(() => {
                                    toast({ title: "Dados Atualizados", description: "O painel de inteligência foi recarregado." });
                                });
                            }}
                            className="bg-primary text-primary-foreground hover:bg-primary/90 px-3 py-1.5 text-xs font-medium rounded-sm flex items-center gap-2"
                        >
                            <RefreshCcw size={14} />
                            Atualizar Painel
                        </button>
                    </div>
                }
            />

            {!hasData ? (
                <div className="space-y-6">
                    <Card className="border-dashed border-2 border-border/60 bg-muted/30">
                        <CardContent className="p-16 flex flex-col items-center justify-center text-center space-y-4">
                            <CloudSun size={48} className="text-muted-foreground/50" />
                            <div>
                                <h3 className="text-lg font-bold">Nenhum Histórico Encontrado</h3>
                                <p className="text-sm text-muted-foreground max-w-sm">
                                    O processamento de inteligência exige dados históricos armazenados. Verifique se a integração climática está ativa e gerando registros.
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                    <RiscoDoencasCard
                        data={inteligencia?.agricultura?.risco_doencas}
                        status={inteligencia?.risco_fitossanitario_status}
                    />
                </div>
            ) : (
                <div className="mt-6 space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                        <div className="lg:col-span-1 space-y-6">
                            <GduCard gduAcumulado={inteligencia.gdu_acumulado} />
                            <AnaliseRisco riscos={inteligencia.riscos} />
                        </div>
                        <div className="lg:col-span-3">
                            <GraficoHistorico dados={(rawHistorico || []).map(item => ({
                                data: item.data_registro,
                                temp_max: item.temp_max_c,
                                temp_min: item.temp_min_c,
                                temp_media: item.temp_media_c,
                                precipitacao: item.precipitacao_mm
                            }))} />
                        </div>
                    </div>

                    <div className="pt-4">
                        <h2 className="text-xl font-bold tracking-tight mb-4">Análise Fitossanitária</h2>
                        {!inteligencia.agricultura ? (
                            <div className="flex flex-col items-center justify-center py-16 text-center gap-3 text-muted-foreground border rounded-lg border-dashed">
                                <span className="text-5xl">🌱</span>
                                <p className="font-semibold text-foreground">Nenhuma safra ativa encontrada</p>
                                <p className="text-sm max-w-sm">O motor de inteligência fitossanitária analisa automaticamente as culturas plantadas nas safras ativas desta unidade produtiva.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                <div className="lg:col-span-2">
                                    <JanelaPulverizacaoCard data={inteligencia.agricultura?.janela_pulverizacao} />
                                </div>
                                <div className="lg:col-span-1">
                                    <BalancoHidricoCard data={inteligencia.agricultura?.balanco_hidrico} />
                                </div>
                                <div className="lg:col-span-3">
                                    <RiscoDoencasCard
                                        data={inteligencia.agricultura?.risco_doencas}
                                        status={inteligencia.risco_fitossanitario_status}
                                    />
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
