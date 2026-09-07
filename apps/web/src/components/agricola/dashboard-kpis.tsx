"use client";

import { Sprout, DollarSign, AlertTriangle, Wheat, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { KPICard, moeda, num } from "@/components/shared/kpi-card";

interface KPIs {
    total_safras_ativas: number;
    total_safras_encerradas: number;
    area_total_ha: number;
    custo_acumulado: number;
    meta_producao_sc: number;
    sacas_colhidas: number;
    receita_colheita: number;
    total_alertas: number;
}

export function DashboardKPIs({ kpis }: { kpis: KPIs }) {
    const pct_colhido = kpis.meta_producao_sc > 0
        ? Math.min(100, Math.round((kpis.sacas_colhidas / kpis.meta_producao_sc) * 100))
        : null;

    const temAlertas = kpis.total_alertas > 0;

    return (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <KPICard
                label="Safras Ativas"
                value={kpis.total_safras_ativas}
                subtitle={`${kpis.total_safras_encerradas} encerradas`}
                icon={Sprout}
                iconBg="bg-emerald-100"
                iconColor="text-emerald-600"
            />
            <KPICard
                label="Área Plantada"
                value={num(kpis.area_total_ha)}
                subtitle="hectares"
                icon={Sprout}
                iconBg="bg-blue-100"
                iconColor="text-blue-600"
            />
            <KPICard
                label="Custo Acumulado"
                value={moeda(kpis.custo_acumulado)}
                subtitle="insumos aplicados"
                icon={DollarSign}
                iconBg="bg-amber-100"
                iconColor="text-amber-600"
                valueSize="base"
            />
            <KPICard
                label="Sacas Colhidas"
                value={num(kpis.sacas_colhidas)}
                subtitle={pct_colhido !== null ? `${pct_colhido}% da meta` : undefined}
                icon={Wheat}
                iconBg="bg-yellow-100"
                iconColor="text-yellow-600"
            />
            <KPICard
                label="Receita Colheita"
                value={moeda(kpis.receita_colheita)}
                subtitle="romaneios registrados"
                icon={TrendingUp}
                iconBg="bg-green-100"
                iconColor="text-green-600"
                valueSize="base"
            />
            <KPICard
                label="Alertas"
                value={kpis.total_alertas}
                subtitle="checklist + NDE"
                icon={AlertTriangle}
                iconBg={cn(temAlertas ? "bg-red-100" : "bg-muted")}
                iconColor={cn(temAlertas ? "text-red-600" : "text-muted-foreground")}
                valueColor={temAlertas ? "text-red-600" : undefined}
                cardClassName={temAlertas ? "border-red-200" : undefined}
            />
        </div>
    );
}
