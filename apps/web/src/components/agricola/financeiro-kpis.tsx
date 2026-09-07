"use client";

import { DollarSign, TrendingUp, TrendingDown, Leaf, Calculator } from "lucide-react";
import { cn } from "@/lib/utils";
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
                iconBg="bg-amber-100"
                iconColor="text-amber-600"
                valueSize="base"
            />
            <KPICard
                label="Receita Total"
                value={moeda(financeiro.receita_total)}
                subtitle={`${financeiro.total_romaneios} romaneios`}
                icon={TrendingUp}
                iconBg="bg-emerald-100"
                iconColor="text-emerald-600"
                valueSize="base"
            />
            <KPICard
                label="Lucro Bruto"
                value={moeda(financeiro.lucro_bruto)}
                subtitle={`${num(financeiro.custo_por_ha, 1)}/ha`}
                icon={lucroNegativo ? TrendingDown : TrendingUp}
                iconBg={cn(lucroNegativo ? "bg-red-100" : "bg-green-100")}
                iconColor={cn(lucroNegativo ? "text-red-600" : "text-green-600")}
                valueSize="base"
                valueColor={lucroNegativo ? "text-red-600" : undefined}
                cardClassName={lucroNegativo ? "border-red-200" : undefined}
            />
            <KPICard
                label="Produtividade"
                value={financeiro.produtividade_sc_ha !== null ? num(financeiro.produtividade_sc_ha) : "—"}
                subtitle={`sc/ha (${financeiro.total_sacas.toFixed(0)} sacas)`}
                icon={Leaf}
                iconBg="bg-yellow-100"
                iconColor="text-yellow-600"
            />
            <KPICard
                label="ROI"
                value={financeiro.roi_pct !== null ? `${num(financeiro.roi_pct)}%` : "—"}
                subtitle="retorno sobre investimento"
                icon={Calculator}
                iconBg={cn(roiPositivo ? "bg-blue-100" : "bg-red-100")}
                iconColor={cn(roiPositivo ? "text-blue-600" : "text-red-600")}
                valueSize="base"
                valueColor={!roiPositivo ? "text-red-600" : undefined}
                cardClassName={!roiPositivo ? "border-red-200" : undefined}
            />
        </div>
    );
}
