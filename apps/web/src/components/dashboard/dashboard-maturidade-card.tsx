"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Gauge, TrendingDown, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/api";

interface PilarMaturidade {
    chave: string;
    nome: string;
    score: number;
    href: string;
}

interface PontoMelhoria {
    pilar: string;
    score: number;
    recomendacao: string;
    href: string;
}

interface GovernancaFinanceiraESG {
    projetos_capex_avaliados: number;
    projetos_capex_viaveis: number;
    projetos_capex_inviaveis: number;
    projetos_inviaveis_abertos: number;
    vpl_carteira_capex: number;
    status_governanca_esg: "SEM_CAPEX" | "SOLIDA" | "ATENCAO";
    recomendacao_esg: string;
}

interface MaturidadeResponse {
    competencia: string;
    unidade_produtiva_id: string | null;
    score_geral: number;
    tendencia_mes_anterior: number | null;
    pilares: PilarMaturidade[];
    pontos_melhoria: PontoMelhoria[];
    governanca_financeira?: GovernancaFinanceiraESG;
}

interface Props {
    unidadeProdutivaId?: string | null;
}

export function DashboardMaturidadeCard({ unidadeProdutivaId }: Props) {
    const qs = unidadeProdutivaId ? `?unidade_produtiva_id=${unidadeProdutivaId}` : "";
    const { data, isLoading } = useQuery<MaturidadeResponse>({
        queryKey: ["dashboard-maturidade", unidadeProdutivaId ?? "grupo"],
        queryFn: () => apiFetch(`/dashboard/maturidade${qs}`),
        staleTime: 120_000,
    });

    if (isLoading) {
        return <Skeleton className="h-48 w-full rounded-sm" />;
    }

    if (!data) return null;

    const scoreTone =
        data.score_geral >= 75
            ? "text-emerald-700 dark:text-emerald-400"
            : data.score_geral >= 45
                ? "text-amber-700 dark:text-amber-400"
                : "text-destructive";

    return (
        <Card className="rounded-sm">
            <CardHeader className="pb-3 flex flex-row items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <Gauge className="size-4 text-primary" />
                    <CardTitle className="text-sm font-semibold">Score de Maturidade da Fazenda</CardTitle>
                    <Badge variant="outline" className="rounded-sm text-[11px]">
                        {data.competencia}
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`text-2xl font-bold tabular-nums ${scoreTone}`}>
                        {data.score_geral.toFixed(1)}
                    </span>
                    <span className="text-xs text-muted-foreground">/ 100</span>
                    {data.tendencia_mes_anterior !== null && (
                        <Badge
                            className={`rounded-sm text-[11px] ${
                                data.tendencia_mes_anterior >= 0
                                    ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                                    : "bg-destructive/10 text-destructive border-destructive/20"
                            }`}
                        >
                            {data.tendencia_mes_anterior >= 0 ? (
                                <TrendingUp className="size-3 mr-1" />
                            ) : (
                                <TrendingDown className="size-3 mr-1" />
                            )}
                            {data.tendencia_mes_anterior >= 0 ? "+" : ""}
                            {data.tendencia_mes_anterior.toFixed(1)} pts
                        </Badge>
                    )}
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {data.pilares.map((pilar) => (
                        <Link
                            key={pilar.chave}
                            href={pilar.href}
                            className="rounded-sm border p-3 hover:bg-muted/40 transition-colors space-y-2"
                        >
                            <div className="flex items-center justify-between text-xs">
                                <span className="font-medium">{pilar.nome}</span>
                                <span className="font-bold tabular-nums">{pilar.score.toFixed(0)}%</span>
                            </div>
                            <Progress value={pilar.score} className="h-1.5" />
                        </Link>
                    ))}
                </div>

                {data.governanca_financeira && (
                    <div className="rounded-sm border bg-muted/20 p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <div className="space-y-0.5 text-xs">
                            <div className="flex items-center gap-2">
                                <span className="font-semibold">Governança Financeira (Pilar G — ESG)</span>
                                <Badge
                                    variant="outline"
                                    className={`rounded-sm text-[10px] ${
                                        data.governanca_financeira.status_governanca_esg === "SOLIDA"
                                            ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
                                            : data.governanca_financeira.status_governanca_esg === "ATENCAO"
                                              ? "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30"
                                              : ""
                                    }`}
                                >
                                    {data.governanca_financeira.status_governanca_esg === "SOLIDA"
                                        ? `Sólida (${data.governanca_financeira.projetos_capex_viaveis}/${data.governanca_financeira.projetos_capex_avaliados} viáveis)`
                                        : data.governanca_financeira.status_governanca_esg === "ATENCAO"
                                          ? `Atenção (${data.governanca_financeira.projetos_capex_inviaveis} inviável)`
                                          : "Sem CapEx"}
                                </Badge>
                                {data.governanca_financeira.projetos_capex_avaliados > 0 && (
                                    <span className="font-semibold tabular-nums">
                                        VPL:{" "}
                                        {data.governanca_financeira.vpl_carteira_capex.toLocaleString("pt-BR", {
                                            style: "currency",
                                            currency: "BRL",
                                        })}
                                    </span>
                                )}
                            </div>
                            <p className="text-[11px] text-muted-foreground">
                                {data.governanca_financeira.recomendacao_esg}
                            </p>
                        </div>
                        <Button asChild variant="outline" size="sm" className="rounded-sm h-7 text-xs shrink-0">
                            <Link href="/dashboard/financeiro/viabilidade">
                                Viabilidade (VPL/TIR) <ArrowRight className="size-3 ml-1" />
                            </Link>
                        </Button>
                    </div>
                )}

                {data.pontos_melhoria.length > 0 && (
                    <div className="rounded-sm border bg-muted/20 p-3 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold">O que está puxando a nota para baixo</span>
                            <Button asChild variant="outline" size="sm" className="rounded-sm h-7 text-xs">
                                <Link href="/dashboard/planos-acao">
                                    Planos de Ação <ArrowRight className="size-3 ml-1" />
                                </Link>
                            </Button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {data.pontos_melhoria.map((ponto) => (
                                <Link
                                    key={ponto.pilar}
                                    href={ponto.href}
                                    className="text-xs flex items-start justify-between gap-2 rounded-sm border bg-background px-2.5 py-2 hover:border-primary/40"
                                >
                                    <div>
                                        <span className="font-semibold">{ponto.pilar}:</span>{" "}
                                        <span className="text-muted-foreground">{ponto.recomendacao}</span>
                                    </div>
                                    <Badge variant="outline" className="rounded-sm shrink-0 text-[10px]">
                                        {ponto.score.toFixed(0)}
                                    </Badge>
                                </Link>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
