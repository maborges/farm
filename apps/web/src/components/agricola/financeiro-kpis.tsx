"use client";

import { DollarSign, TrendingUp, TrendingDown, Leaf, Calculator } from "lucide-react";
import { KPICard, moeda, num } from "@/components/shared/kpi-card";

interface FinanceiroResumo {
    total_operacoes: number;
    custo_operacoes_total: number;
    custo_por_ha: number;
    total_romaneios: number;
    total_sacas: number;
    produtividade_sc_ha: number | null;
    despesa_total: number;
    receita_total: number;
    lucro_bruto: number;
    roi_pct: number | null;
}

export function FinanceiroKPIs({ financeiro }: { financeiro: FinanceiroResumo }) {
    const lucroNegativo = financeiro.lucro_bruto < 0;
    const roiPositivo = financeiro.roi_pct !== null && financeiro.roi_pct >= 0;

    return (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <KPICard
                label="Despesa Total"
                value={moeda(financeiro.despesa_total)}
                subtitle={`${financeiro.total_operacoes} operações`}
                icon={DollarSign}
                tone="warning"
                valueSize="base"
            />
            <KPICard
                label="Receita Total"
                value={moeda(financeiro.receita_total)}
                subtitle={`${financeiro.total_romaneios} romaneios`}
                icon={TrendingUp}
                tone="success"
                valueSize="base"
            />
            <KPICard
                label="Lucro Bruto"
                value={moeda(financeiro.lucro_bruto)}
                subtitle={`${num(financeiro.custo_por_ha, 1)}/ha`}
                icon={lucroNegativo ? TrendingDown : TrendingUp}
                tone={lucroNegativo ? "destructive" : "success"}
                valueSize="base"
                valueTone={lucroNegativo ? "destructive" : undefined}
                highlightBorder={lucroNegativo}
            />
            <KPICard
                label="Produtividade"
                value={financeiro.produtividade_sc_ha !== null ? num(financeiro.produtividade_sc_ha) : "—"}
                subtitle={`sc/ha (${financeiro.total_sacas.toFixed(0)} sacas)`}
                icon={Leaf}
                tone="warning"
            />
            <KPICard
                label="ROI"
                value={financeiro.roi_pct !== null ? `${num(financeiro.roi_pct)}%` : "—"}
                subtitle="retorno sobre investimento"
                icon={Calculator}
                tone={roiPositivo ? "info" : "destructive"}
                valueSize="base"
                valueTone={!roiPositivo ? "destructive" : undefined}
                highlightBorder={!roiPositivo}
            />
        </div>
    );
}
