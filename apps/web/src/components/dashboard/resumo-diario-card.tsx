"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, Loader2, ChevronRight, TrendingDown, TrendingUp, DollarSign, BrainCircuit } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useSafrasAtivas } from "@/hooks/use-agricola";

const dashboardCardButtonClass = "h-8 rounded-sm px-3 text-xs font-semibold";

interface ResumoDiario {
    texto_resumo: string;
    saude_financeira: {
        receita: number;
        custos: number;
        margem: number;
    };
    risco_principal: string;
    oportunidade_principal: string;
    recomendacao_ia: string;
    ia_disponivel: boolean;
    acao_sugerida?: {
        acao: "SIMULACAO" | "AJUSTE_CENARIO" | "ANALISE_DETALHADA";
        parametros: Record<string, any>;
        descricao: string;
    };
}

export function ResumoDiarioCard({ safraId }: { safraId?: string }) {
    const router = useRouter();
    const activeFazendaId = useAppStore((state) => state.activeFazendaId);
    const activeGrupoId = useAppStore((state) => state.activeGrupoId);
    const grupos = useAppStore((state) => state.grupos);
    const firstUnidadeProdutivaId = useAppStore((state) => state.unidadesProdutivasAutorizadas[0]?.id ?? null);
    const hasHydrated = useAppStore((state) => state._hasHydrated);
    const grupoAtivo = grupos.find((grupo) => grupo.id === activeGrupoId) ?? grupos[0] ?? null;
    const fazendasDoGrupoAtivo = grupoAtivo?.fazendas ?? [];
    const activeFazendaValida = !!activeFazendaId && fazendasDoGrupoAtivo.some((fazenda) => fazenda.id === activeFazendaId);
    const fallbackFazendaId = fazendasDoGrupoAtivo[0]?.id ?? firstUnidadeProdutivaId ?? undefined;
    const unidadeContextoId = activeFazendaValida ? activeFazendaId : fallbackFazendaId;
    const { data: safras = [], isLoading: safrasLoading } = useSafrasAtivas(unidadeContextoId);
    const effectiveSafraId = safraId ?? safras[0]?.id;

    const { data: resumo, isLoading } = useQuery<ResumoDiario>({
        queryKey: ["resumo-diario", effectiveSafraId],
        queryFn: () => apiFetch(`/ia/financeiro/resumo-diario?safra_id=${effectiveSafraId}`),
        enabled: !!effectiveSafraId,
        staleTime: 600_000, // 10 minutos
    });

    if (!hasHydrated || isLoading || safrasLoading) {
        return (
            <Card className="border-primary/10">
                <CardContent className="flex h-32 items-center justify-center">
                    <Loader2 className="size-5 animate-spin text-primary/30" />
                </CardContent>
            </Card>
        );
    }

    if (!effectiveSafraId) {
        return (
            <Card className="overflow-hidden border-dashed bg-muted/30">
                <CardHeader className="pb-3 border-b border-border/60">
                    <div className="flex items-center gap-2">
                        <div className="bg-primary/10 p-2 rounded-sm">
                            <BrainCircuit size={18} className="text-primary" />
                        </div>
                        <div>
                            <CardTitle className="text-sm font-semibold uppercase tracking-tight">Briefing Diário: Insights da IA</CardTitle>
                            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">Selecione uma fazenda com safra ativa para gerar o resumo</p>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                    <p className="text-sm text-muted-foreground leading-relaxed">
                        Não foi possível identificar uma safra ativa no contexto atual. Verifique se a fazenda ativa já foi carregada ou selecione uma safra manualmente no Copiloto.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-2">
                        <Button asChild size="sm" className={dashboardCardButtonClass}>
                            <Link href="/dashboard/agricola">Abrir agrícola</Link>
                        </Button>
                        <Button asChild variant="outline" size="sm" className={dashboardCardButtonClass}>
                            <Link href="/dashboard">Voltar ao dashboard</Link>
                        </Button>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!resumo) {
        return null;
    }

    const handleExecutarSugestao = async (sugestao: NonNullable<ResumoDiario["acao_sugerida"]>) => {
        // Step 201: Registrar ação assistida
        let actionId = "";
        try {
            const resp = await apiFetch("/ia/acoes-assistidas/registrar", {
                method: "POST",
                body: {
                    origem: "RESUMO_DIARIO",
                    origem_id: null, // Resumo diário é global/por safra no contexto atual
                    tipo_acao: sugestao.acao,
                    parametros_json: sugestao.parametros
                }
            });
            actionId = (resp as any).id;
        } catch (e) {
            console.error("Erro ao registrar ação assistida:", e);
        }

        const actionParam = actionId ? `&action_id=${actionId}` : "";

        if (sugestao.acao === "SIMULACAO") {
            const params = new URLSearchParams();
            if (sugestao.parametros.receita_percentual !== undefined) params.set("receita", sugestao.parametros.receita_percentual.toString());
            if (sugestao.parametros.custos_percentual !== undefined) params.set("custos", sugestao.parametros.custos_percentual.toString());
            router.push(`/dashboard/financeiro/dre?safra_id=${safraId}&${params.toString()}&auto_simular=true${actionParam}`);
        } else if (sugestao.acao === "AJUSTE_CENARIO") {
            router.push(`/dashboard/agricola/safras/${safraId}/cenarios?ajuste_sugerido=true&cenario_id=${sugestao.parametros.cenario_id}${actionParam}`);
        }
    };

    return (
        <Card className="relative overflow-hidden border-primary/20 bg-gradient-to-br from-primary/[0.03] via-background to-background shadow-lg shadow-primary/5">
            <div className="absolute top-0 right-0 p-4 opacity-[0.03] pointer-events-none">
                <Sparkles size={120} className="text-primary" />
            </div>
            
            <CardHeader className="pb-3 border-b border-primary/5">
                <div className="flex items-center gap-2">
                    <div className="bg-primary/10 p-2 rounded-sm">
                        <Sparkles size={18} className="text-primary" />
                    </div>
                    <div>
                        <CardTitle className="text-sm font-semibold uppercase tracking-tight">Briefing Diário: Insights da IA</CardTitle>
                        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">Resumo consolidado para tomada de decisão</p>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="p-6 space-y-6">
                {/* Texto IA */}
                <div className="space-y-2">
                    <p className="text-base font-medium leading-relaxed text-foreground/90 italic">
                        &quot;{resumo.texto_resumo}&quot;
                    </p>
                </div>

                {/* Grid de Métricas */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-background/50 p-4 rounded-sm border border-primary/5 flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-sm">
                            <TrendingUp size={16} className="text-blue-600" />
                        </div>
                        <div>
                            <p className="text-[10px] font-semibold uppercase text-muted-foreground">Receita</p>
                            <p className="text-sm font-bold">R$ {resumo.saude_financeira.receita.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
                        </div>
                    </div>
                    <div className="bg-background/50 p-4 rounded-sm border border-primary/5 flex items-center gap-3">
                        <div className="p-2 bg-amber-500/10 rounded-sm">
                            <TrendingDown size={16} className="text-amber-600" />
                        </div>
                        <div>
                            <p className="text-[10px] font-semibold uppercase text-muted-foreground">Custos</p>
                            <p className="text-sm font-bold">R$ {resumo.saude_financeira.custos.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
                        </div>
                    </div>
                    <div className="bg-background/50 p-4 rounded-sm border border-primary/5 flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-sm">
                            <DollarSign size={16} className="text-primary" />
                        </div>
                        <div>
                            <p className="text-[10px] font-semibold uppercase text-muted-foreground">Margem Atual</p>
                            <p className={cn("text-sm font-semibold", resumo.saude_financeira.margem < 10 ? "text-destructive" : "text-primary")}>
                                {resumo.saude_financeira.margem.toFixed(1)}%
                            </p>
                        </div>
                    </div>
                </div>

                {/* Risco e Oportunidade */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                    <div className="space-y-2 border-l-2 border-destructive/20 pl-4">
                        <Badge variant="outline" className="text-destructive border-destructive/20 bg-destructive/5 text-[9px] font-semibold uppercase py-0 px-2 h-4">Risco do Dia</Badge>
                        <p className="text-xs font-medium text-muted-foreground line-clamp-2">{resumo.risco_principal}</p>
                    </div>
                    <div className="space-y-2 border-l-2 border-primary/20 pl-4">
                        <Badge variant="outline" className="text-primary border-primary/20 bg-primary/5 text-[9px] font-semibold uppercase py-0 px-2 h-4">Oportunidade</Badge>
                        <p className="text-xs font-medium text-muted-foreground line-clamp-2">{resumo.oportunidade_principal}</p>
                    </div>
                </div>

                {/* Footer / Ação */}
                <div className="pt-6 border-t border-primary/5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div className="flex-1">
                        <div className="flex items-center gap-1.5 mb-1">
                            <Sparkles size={12} className="text-primary" />
                            <p className="text-[10px] font-semibold uppercase text-primary/70">Recomendação do Copiloto</p>
                        </div>
                        <p className="text-xs font-bold leading-tight text-foreground/80">{resumo.recomendacao_ia}</p>
                    </div>
                    <div className="flex flex-col sm:flex-row gap-2">
                        {resumo.acao_sugerida && (
                            <Button 
                                variant="default" 
                                size="sm" 
                                onClick={() => handleExecutarSugestao(resumo.acao_sugerida!)}
                                className={dashboardCardButtonClass}
                            >
                                <Sparkles data-icon="inline-start" />
                                Executar sugestão
                            </Button>
                        )}
                        <Button 
                            size="sm" 
                            variant="outline" 
                            onClick={() => router.push(`/dashboard/financeiro/dre?safra_id=${safraId}`)}
                            className={dashboardCardButtonClass}
                        >
                            Analisar safra completa
                            <ChevronRight data-icon="inline-end" />
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
