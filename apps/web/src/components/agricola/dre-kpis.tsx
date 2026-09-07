"use client";

import { AlertCircle, DollarSign, Factory, LineChart, Percent, Sprout, Tractor, Wallet, TrendingUp } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KPICard, moeda, num } from "@/components/shared/kpi-card";

export interface AgricolaDreKpisData {
  area_total_ha: number;
  receita_liquida: number;
  custo_operacional_total: number;
  margem_bruta: number;
  resultado_operacional: number;
  margem_pct: number | null;
  custo_por_hectare: number | null;
  receita_por_hectare: number | null;
  resultado_por_hectare: number | null;
  sujeito_reconciliacao: boolean;
  observacao_reconciliacao: string | null;
  warnings_relevantes: string[];
}

export function AgricolaDreKpis({
  kpis,
  fallback,
}: {
  kpis?: AgricolaDreKpisData | null;
  fallback?: AgricolaDreKpisData;
}) {
  const data = kpis ?? fallback;

  if (!data) {
    return null;
  }

  return (
    <Card className="rounded-sm shadow-sm" data-testid="agricola-dre-kpis">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <LineChart className="size-4 text-muted-foreground" />
          KPIs financeiros agrícolas oficiais
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {data.sujeito_reconciliacao && (
          <Alert className="rounded-sm">
            <AlertCircle className="size-4" />
            <AlertTitle>Valores sujeitos à reconciliação</AlertTitle>
            <AlertDescription>
              {data.observacao_reconciliacao ?? "A DRE retornou warnings relevantes e os KPIs devem ser tratados como leitura operacional sujeita à reconciliação."}
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <KPICard
            label="Receita Líquida"
            value={moeda(data.receita_liquida)}
            subtitle="Fonte consolidada: DRE agrícola v1"
            icon={Wallet}
            iconBg="bg-emerald-100"
            iconColor="text-emerald-600"
          />
          <KPICard
            label="Custo Operacional Total"
            value={moeda(data.custo_operacional_total)}
            subtitle="Custos diretos + operacionais + despesas"
            icon={Factory}
            iconBg="bg-amber-100"
            iconColor="text-amber-600"
          />
          <KPICard
            label="Margem Bruta"
            value={moeda(data.margem_bruta)}
            subtitle="Receita líquida - custos diretos"
            icon={TrendingUp}
            iconBg="bg-blue-100"
            iconColor="text-blue-600"
          />
          <KPICard
            label="Resultado Operacional"
            value={moeda(data.resultado_operacional)}
            subtitle="Margem bruta - custos e despesas"
            icon={LineChart}
            iconBg={data.resultado_operacional < 0 ? "bg-red-100" : "bg-emerald-100"}
            iconColor={data.resultado_operacional < 0 ? "text-red-600" : "text-emerald-600"}
            valueColor={data.resultado_operacional < 0 ? "text-red-600" : undefined}
            cardClassName={data.resultado_operacional < 0 ? "border-red-200" : undefined}
          />
          <KPICard
            label="Margem %"
            value={data.margem_pct !== null ? `${num(data.margem_pct, 1)}%` : "—"}
            subtitle="Resultado operacional / receita líquida"
            icon={Percent}
            iconBg={data.margem_pct !== null && data.margem_pct < 0 ? "bg-red-100" : "bg-cyan-100"}
            iconColor={data.margem_pct !== null && data.margem_pct < 0 ? "text-red-600" : "text-cyan-600"}
            valueColor={data.margem_pct !== null && data.margem_pct < 0 ? "text-red-600" : undefined}
            cardClassName={data.margem_pct !== null && data.margem_pct < 0 ? "border-red-200" : undefined}
          />
          <KPICard
            label="Custo por hectare"
            value={data.custo_por_hectare !== null ? moeda(data.custo_por_hectare) : "—"}
            subtitle={data.area_total_ha > 0 ? `${num(data.area_total_ha, 1)} ha consolidados` : "Área consolidada indisponível"}
            icon={Tractor}
            iconBg="bg-amber-50"
            iconColor="text-amber-700"
          />
          <KPICard
            label="Receita por hectare"
            value={data.receita_por_hectare !== null ? moeda(data.receita_por_hectare) : "—"}
            subtitle={data.area_total_ha > 0 ? `${num(data.area_total_ha, 1)} ha consolidados` : "Área consolidada indisponível"}
            icon={Sprout}
            iconBg="bg-emerald-50"
            iconColor="text-emerald-700"
          />
          <KPICard
            label="Resultado por hectare"
            value={data.resultado_por_hectare !== null ? moeda(data.resultado_por_hectare) : "—"}
            subtitle={data.area_total_ha > 0 ? `${num(data.area_total_ha, 1)} ha consolidados` : "Área consolidada indisponível"}
            icon={DollarSign}
            iconBg={data.resultado_por_hectare !== null && data.resultado_por_hectare < 0 ? "bg-red-100" : "bg-slate-100"}
            iconColor={data.resultado_por_hectare !== null && data.resultado_por_hectare < 0 ? "text-red-600" : "text-slate-600"}
            valueColor={data.resultado_por_hectare !== null && data.resultado_por_hectare < 0 ? "text-red-600" : undefined}
            cardClassName={data.resultado_por_hectare !== null && data.resultado_por_hectare < 0 ? "border-red-200" : undefined}
          />
        </div>
      </CardContent>
    </Card>
  );
}
