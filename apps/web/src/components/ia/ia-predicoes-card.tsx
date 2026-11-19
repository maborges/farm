"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    AlertCircle, TrendingDown, TrendingUp,
    Zap, Clock, ShieldAlert, Sparkles
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAppStore } from "@/lib/stores/app-store";
import { useSafrasAtivas } from "@/hooks/use-agricola";

interface IAPredicaoResponse {
    risco: string;
    descricao: string;
    impacto_estimado: number;
    tempo_estimado: string;
    acao_recomendada: string;
    confianca: number;
}

const fmt = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

export function IAPredicoesCard({ safraId }: { safraId?: string }) {
    const activeFazendaId = useAppStore((state) => state.activeFazendaId);
    const activeGrupoId = useAppStore((state) => state.activeGrupoId);
    const grupos = useAppStore((state) => state.grupos);
    const firstUnidadeProdutivaId = useAppStore((state) => state.unidadesProdutivasAutorizadas[0]?.id ?? null);
    const grupoAtivo = grupos.find((grupo) => grupo.id === activeGrupoId) ?? grupos[0] ?? null;
    const fazendasDoGrupoAtivo = grupoAtivo?.fazendas ?? [];
    const activeFazendaValida = !!activeFazendaId && fazendasDoGrupoAtivo.some((fazenda) => fazenda.id === activeFazendaId);
    const fallbackFazendaId = fazendasDoGrupoAtivo[0]?.id ?? firstUnidadeProdutivaId ?? undefined;
    const unidadeContextoId = activeFazendaValida ? activeFazendaId : fallbackFazendaId;
    const { data: safras = [], isLoading: safrasLoading } = useSafrasAtivas(unidadeContextoId);
    const effectiveSafraId = safraId ?? safras[0]?.id;

    const { data: predicao, isLoading } = useQuery<IAPredicaoResponse>({
        queryKey: ["ia-predicao-risco", effectiveSafraId, activeFazendaId],
        queryFn: () => apiFetch(`/ia/financeiro/predicao-risco?safra_id=${effectiveSafraId}`),
        enabled: !!effectiveSafraId,
    });

    if (isLoading || safrasLoading) {
        return (
            <Card className="overflow-hidden border-primary/20 bg-primary/5">
                <CardHeader className="pb-2">
                    <Skeleton className="h-5 w-40" />
                </CardHeader>
                <CardContent className="space-y-4">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-20 w-full" />
                </CardContent>
            </Card>
        );
    }

    if (!effectiveSafraId) {
        return (
            <Card className="border-dashed bg-muted/30">
                <CardContent className="p-6 flex flex-col items-center text-center">
                    <ShieldAlert className="size-8 text-muted-foreground/40 mb-3" />
                    <h4 className="text-sm font-bold text-muted-foreground">Monitoramento Preditivo Indisponível</h4>
                    <p className="text-xs text-muted-foreground mt-1 max-w-[220px]">
                        Selecione uma fazenda com safra ativa para ativar previsões do Copiloto.
                    </p>
                </CardContent>
            </Card>
        );
    }

    if (!predicao || predicao.risco === "BAIXO") {
        return (
            <Card className="border-dashed bg-muted/30">
                <CardContent className="p-6 flex flex-col items-center text-center">
                    <ShieldAlert className="size-8 text-muted-foreground/40 mb-3" />
                    <h4 className="text-sm font-bold text-muted-foreground">Monitoramento Preditivo Ativo</h4>
                    <p className="text-xs text-muted-foreground mt-1 max-w-[200px]">
                        Nenhum risco financeiro iminente detectado para as próximas semanas.
                    </p>
                </CardContent>
            </Card>
        );
    }

    const isAlto = predicao.risco === "ALTO";

    return (
        <Card
            variant={isAlto ? "destructive" : "warning"}
            className={`border-l-4 ${isAlto ? "border-l-alert-destructive-icon" : "border-l-alert-warning-icon"}`}
        >
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <div className="flex items-center gap-2">
                    <Sparkles className="size-4 text-primary animate-pulse" />
                    <CardTitle className="text-sm font-black uppercase tracking-widest">
                        Previsões do Copiloto
                    </CardTitle>
                </div>
                <Badge variant={isAlto ? "destructive" : "warning"} className="text-[10px] font-black rounded-sm h-5">
                    RISCO {predicao.risco}
                </Badge>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-1.5">
                    <p className="text-sm font-bold text-card-title leading-tight">
                        {predicao.descricao}
                    </p>
                    <div className="flex items-center gap-2 text-[10px] text-card-description font-semibold">
                        <Clock className="size-3" /> Horizonte: {predicao.tempo_estimado}
                        <span className="opacity-30">|</span>
                        <Zap className="size-3 text-alert-warning-icon" /> Confiança: {(predicao.confianca * 100).toFixed(0)}%
                    </div>
                </div>

                <div className="p-3 bg-card/85 rounded-sm border border-border/50">
                    <p className="text-[10px] text-muted-foreground font-black uppercase mb-1">Impacto Estimado</p>
                    <div className="flex items-baseline gap-1">
                        <span className="text-xl font-black text-alert-destructive-icon">{fmt(predicao.impacto_estimado)}</span>
                        <span className="text-[10px] font-bold text-muted-foreground">de prejuízo projetado</span>
                    </div>
                </div>

                <div className="flex flex-col gap-2">
                    <p className="text-xs text-muted-foreground italic">
                        &quot;{predicao.acao_recomendada}&quot;
                    </p>
                    <Button size="sm" variant="outline" className="w-full text-xs font-bold gap-2 rounded-sm border-primary/20 hover:bg-primary/10">
                        <Zap className="size-3" /> Executar Simulação Preventiva
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
