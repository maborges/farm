"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ChevronRight, BarChart2, GitCompare, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { trackCTA } from "@/lib/analytics";

interface InsightDashboard {
    total_custos: number;
    quantidade_lancamentos: number;
}

const passos = [
    {
        icon: <GitCompare className="size-4 text-primary" />,
        titulo: "Compare cenários de safra",
        descricao: "Simule margens com diferentes preços e produtividades antes de tomar decisões.",
        href: "/dashboard/settings/billing",
        cta: "Disponível no Profissional",
    },
    {
        icon: <BarChart2 className="size-4 text-primary" />,
        titulo: "Analise custos por categoria",
        descricao: "Identifique onde estão os maiores gastos e otimize sua operação.",
        href: "/dashboard/settings/billing",
        cta: "Disponível no Profissional",
    },
    {
        icon: <Lightbulb className="size-4 text-primary" />,
        titulo: "Projeções automáticas",
        descricao: "Antecipe resultados com base no histórico e nas condições de mercado.",
        href: "/dashboard/settings/billing",
        cta: "Disponível no Enterprise",
    },
];

export function ProximoPassoBlock() {
    const { data } = useQuery<InsightDashboard>({
        queryKey: ["lancamentos-insight"],
        queryFn: () => apiFetch("/financeiro/lancamentos/insight"),
        staleTime: 30_000,
    });

    const temCustos = data && data.total_custos > 0;

    useEffect(() => {
        if (temCustos) {
            trackCTA({ event: "monetization_cta_viewed", context: "dashboard_proximo_passo" });
        }
    }, [temCustos]);

    if (!temCustos) return null;

    return (
        <section aria-labelledby="proximo-passo-heading">
            <div className="flex items-center justify-between mb-4">
                <h2 id="proximo-passo-heading" className="text-sm font-semibold text-muted-foreground uppercase">
                    Próximo nível de valor
                </h2>
                <Button variant="ghost" size="sm" className="text-xs text-muted-foreground" asChild>
                    <Link href="/dashboard/settings/billing">
                        Ver planos <ChevronRight className="size-3 ml-0.5" />
                    </Link>
                </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
                {passos.map((passo) => (
                    <Link
                        key={passo.titulo}
                        href={passo.href}
                        className="group rounded-sm border border-dashed border-muted-foreground/25 bg-muted/30 p-4 hover:border-primary/40 hover:bg-primary/5 transition-colors"
                        onClick={() => trackCTA({
                            event: "monetization_cta_clicked",
                            context: "dashboard_proximo_passo",
                            meta: { titulo: passo.titulo },
                        })}
                    >
                        <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-2">
                                {passo.icon}
                                <span className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                                    {passo.titulo}
                                </span>
                            </div>
                            <p className="text-xs text-muted-foreground leading-relaxed">
                                {passo.descricao}
                            </p>
                            <span className="text-[10px] font-semibold text-primary/70 mt-1">
                                {passo.cta} →
                            </span>
                        </div>
                    </Link>
                ))}
            </div>
        </section>
    );
}
