"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { TrendingDown, TrendingUp, CircleDollarSign, AlertTriangle, ArrowRight } from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { trackCTA } from "@/lib/analytics";
import { Button } from "@/components/ui/button";

interface CategoriaBreakdown {
    nome: string;
    valor: number;
}

const CATEGORIA_LABEL: Record<string, string> = {
    INSUMOS: "Insumos",
    MAO_OBRA: "Mão de obra",
    OPERACOES: "Operações",
    ADMINISTRATIVO: "Administrativo",
};

interface InsightDashboard {
    total_custos: number;
    quantidade_lancamentos: number;
    safra_nome: string | null;
    cenario_custo_total: number | null;
    cenario_receita_total: number | null;
    cenario_margem: number | null;
    mensagem: string | null;
    categorias: CategoriaBreakdown[];
}

function fmt(value: number) {
    return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function InsightFinanceiroCard() {
    const { data, isLoading } = useQuery<InsightDashboard>({
        queryKey: ["lancamentos-insight"],
        queryFn: () => apiFetch("/financeiro/lancamentos/insight"),
        staleTime: 30_000,
    });

    useEffect(() => {
        if (data && data.total_custos > 0) {
            trackCTA({ event: "monetization_cta_viewed", context: "dashboard_financeiro_insight" });
        }
    }, [data]);

    if (isLoading || !data || data.total_custos === 0) return null;

    const margemNegativa = data.cenario_margem !== null && data.cenario_margem < 0;

    return (
        <section className={`rounded-sm border p-5 shadow-sm ${margemNegativa ? "border-destructive/30 bg-card" : "border-emerald-500/20 bg-card"}`}>
            <div className="flex flex-col gap-4">
                {/* KPIs */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="space-y-1">
                        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                            Indicadores Financeiros{data.safra_nome ? ` — Safra ${data.safra_nome}` : ""}
                        </p>
                        {data.mensagem && (
                            <p className={`text-sm font-semibold flex items-center gap-1.5 ${margemNegativa ? "text-destructive" : "text-emerald-700 dark:text-emerald-400"}`}>
                                {margemNegativa
                                    ? <AlertTriangle className="size-4" />
                                    : <TrendingUp className="size-4" />}
                                {data.mensagem}
                            </p>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-6">
                        <KpiItem
                            label="Total de custos"
                            value={fmt(data.total_custos)}
                            sub={`${data.quantidade_lancamentos} lançamento${data.quantidade_lancamentos !== 1 ? "s" : ""}`}
                            icon={<CircleDollarSign className="size-4 text-destructive" />}
                        />
                        {data.cenario_receita_total !== null && (
                            <KpiItem
                                label="Receita estimada"
                                value={fmt(data.cenario_receita_total)}
                                icon={<TrendingUp className="size-4 text-emerald-600" />}
                            />
                        )}
                        {data.cenario_margem !== null && (
                            <KpiItem
                                label="Margem atual"
                                value={fmt(data.cenario_margem)}
                                icon={margemNegativa
                                    ? <TrendingDown className="size-4 text-destructive" />
                                    : <TrendingUp className="size-4 text-emerald-600" />}
                                destaque={margemNegativa ? "destructive" : "success"}
                            />
                        )}
                    </div>
                </div>

                {/* Top categorias */}
                {data.categorias.length > 0 && (
                    <div className="flex flex-wrap gap-3">
                        {data.categorias.slice(0, 2).map((cat) => (
                            <div key={cat.nome} className="flex items-center gap-2 rounded-sm bg-background border border-border px-3 py-1.5">
                                <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                                    {CATEGORIA_LABEL[cat.nome] ?? cat.nome}
                                </span>
                                <span className="text-sm font-black tabular-nums text-foreground">
                                    {fmt(cat.valor)}
                                </span>
                            </div>
                        ))}
                        {data.categorias.length > 2 && (
                            <span className="text-xs text-muted-foreground self-center">
                                +{data.categorias.length - 2} categorias
                            </span>
                        )}
                    </div>
                )}

                {/* CTA de upgrade contextual */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-sm border border-dashed border-muted-foreground/30 bg-background px-4 py-3">
                    <p className="text-xs text-muted-foreground">
                        <span className="font-semibold text-foreground">Quer detalhar custos por categoria e comparar cenários?</span>{" "}
                        Disponível no plano Profissional.
                    </p>
                    <Button
                        size="sm"
                        variant="outline"
                        className="h-8 rounded-sm px-3 text-xs font-semibold shrink-0"
                        asChild
                        onClick={() => trackCTA({
                            event: "monetization_cta_clicked",
                            context: "dashboard_financeiro_insight",
                            meta: { total_custos: data.total_custos },
                        })}
                    >
                        <Link href="/dashboard/settings/billing">
                            Ver planos
                            <ArrowRight data-icon="inline-end" />
                        </Link>
                    </Button>
                </div>
            </div>
        </section>
    );
}

function KpiItem({
    label, value, sub, icon, destaque,
}: {
    label: string;
    value: string;
    sub?: string;
    icon?: React.ReactNode;
    destaque?: "destructive" | "success";
}) {
    const valueClass = destaque === "destructive"
        ? "text-destructive"
        : destaque === "success"
            ? "text-emerald-700 dark:text-emerald-400"
            : "text-foreground";

    return (
        <div className="flex flex-col gap-0.5 min-w-[120px]">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1">
                {icon}{label}
            </span>
            <span className={`text-lg font-black tabular-nums ${valueClass}`}>{value}</span>
            {sub && <span className="text-[10px] text-muted-foreground">{sub}</span>}
        </div>
    );
}
