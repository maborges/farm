"use client";

import { useQuery } from "@tanstack/react-query";
import { Lightbulb, ArrowRight, TrendingDown, PackageSearch, TrendingUp } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface RecomendacaoSafra {
    tipo: string;  // REVISAR_CUSTOS | ANALISAR_INSUMOS | VER_EVOLUCAO
    mensagem: string;
    acao: string;
    rota: string;
}

const TIPO_CONFIG: Record<
    string,
    {
        icon: React.ReactNode;
        iconWrapClass: string;
        badgeLabel: string;
        badgeClass: string;
    }
> = {
    REVISAR_CUSTOS: {
        icon: <TrendingDown className="size-3.5" />,
        iconWrapClass: "bg-destructive/10 text-destructive",
        badgeLabel: "Urgente",
        badgeClass: "border-destructive/40 text-destructive bg-destructive/5",
    },
    ANALISAR_INSUMOS: {
        icon: <PackageSearch className="size-3.5" />,
        iconWrapClass: "bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400",
        badgeLabel: "Atenção",
        badgeClass:
            "border-amber-300 text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40",
    },
    VER_EVOLUCAO: {
        icon: <TrendingUp className="size-3.5" />,
        iconWrapClass:
            "bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400",
        badgeLabel: "Acompanhe",
        badgeClass:
            "border-blue-300 text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/40",
    },
};

const FALLBACK_CONFIG = {
    icon: <Lightbulb className="size-3.5" />,
    iconWrapClass: "bg-muted text-muted-foreground",
    badgeLabel: "Dica",
    badgeClass: "border-muted-foreground/30 text-muted-foreground bg-muted/40",
};

interface Props {
    safraId: string;
}

/**
 * Exibe recomendações acionáveis geradas pelo backend com base em regras
 * determinísticas. Cada recomendação inclui um botão que redireciona o
 * usuário para a tela relevante de ação.
 * Revalida a cada 60 segundos e ao invalidar "financeiro-recomendacoes".
 */
export function RecomendacoesCard({ safraId }: Props) {
    const { data: recomendacoes } = useQuery<RecomendacaoSafra[]>({
        queryKey: ["financeiro-recomendacoes", safraId],
        queryFn: () =>
            apiFetch(`/financeiro/lancamentos/recomendacoes?safra_id=${safraId}`),
        staleTime: 60_000,
        refetchInterval: 60_000,
        enabled: !!safraId,
    });

    if (!recomendacoes || recomendacoes.length === 0) return null;

    return (
        <section
            className="rounded-sm border border-emerald-200/60 dark:border-emerald-800/30 bg-card shadow-sm"
            aria-label="Recomendações para a safra"
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-border/60">
                <div className="flex items-center gap-2">
                    <span className="size-8 rounded-sm bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
                        <Lightbulb className="size-4 text-emerald-600 dark:text-emerald-400" />
                    </span>
                    <div>
                        <p className="text-sm font-bold tracking-tight">
                            Recomendações
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                            {recomendacoes.length} ação{recomendacoes.length !== 1 ? "ões" : ""} sugerida{recomendacoes.length !== 1 ? "s" : ""}
                        </p>
                    </div>
                </div>
                <Badge
                    variant="outline"
                    className="h-5 px-2 text-[10px] font-black border-emerald-300 text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40"
                >
                    {recomendacoes.length} nova{recomendacoes.length !== 1 ? "s" : ""}
                </Badge>
            </div>

            {/* Recommendation list */}
            <div className="flex flex-col gap-2 p-3">
                {recomendacoes.map((rec, i) => {
                    const cfg = TIPO_CONFIG[rec.tipo] ?? FALLBACK_CONFIG;
                    return (
                        <div
                            key={i}
                            className="flex items-center gap-3 rounded-sm border border-border/60 bg-background/60 px-3 py-2.5 transition-colors hover:bg-muted/30"
                        >
                            <span
                                className={cn(
                                    "size-6 rounded flex items-center justify-center shrink-0",
                                    cfg.iconWrapClass,
                                )}
                            >
                                {cfg.icon}
                            </span>

                            <p className="flex-1 text-sm font-medium leading-snug text-foreground min-w-0">
                                {rec.mensagem}
                            </p>

                            <div className="flex items-center gap-2 shrink-0">
                                <Badge
                                    variant="outline"
                                    className={cn(
                                        "h-5 px-2 text-[10px] font-black rounded-sm hidden sm:flex",
                                        cfg.badgeClass,
                                    )}
                                >
                                    {cfg.badgeLabel}
                                </Badge>

                                <Button
                                    asChild
                                    variant="outline"
                                    size="sm"
                                    className="h-8 rounded-sm px-3 text-xs font-semibold"
                                >
                                    <Link href={rec.rota}>
                                        {rec.acao}
                                        <ArrowRight data-icon="inline-end" />
                                    </Link>
                                </Button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}
