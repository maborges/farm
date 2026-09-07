import Link from "next/link";
import { Tractor } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { FrotaAgriculturaDashboard } from "./types";
import { formatCurrency, formatNumber } from "./utils";

interface FrotaUsoAgricolaPanelProps {
  agriculturaData: FrotaAgriculturaDashboard | undefined;
  hasEnterpriseTier: boolean;
}

export function FrotaUsoAgricolaPanel({
  agriculturaData,
  hasEnterpriseTier,
}: FrotaUsoAgricolaPanelProps) {
  return (
    <>
      {agriculturaData ? (
        <Card className="rounded-sm shadow-sm">
          <CardHeader>
            <CardTitle>Uso agrícola</CardTitle>
            <CardDescription>Consolidação por safra, talhão e operação a partir das jornadas finalizadas.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="rounded-sm border p-3">
              <div className="font-medium">
                {formatNumber(agriculturaData.resumo.horas_totais)} h e {formatNumber(agriculturaData.resumo.km_totais)} km
              </div>
              <div className="text-xs text-muted-foreground">
                {agriculturaData.resumo.custo_estimado_total !== null
                  ? `${formatCurrency(agriculturaData.resumo.custo_estimado_total)} estimado`
                  : "Sem custo estimado consolidado"}
              </div>
            </div>
            <div className="rounded-sm border p-3">
              <div className="font-medium">
                {agriculturaData.resumo.operacao_mais_cara || "Sem operação destacada"}
              </div>
              <div className="text-xs text-muted-foreground">
                {agriculturaData.resumo.talhao_mais_caro || "Sem talhão"} • {agriculturaData.resumo.equipamento_mais_usado || "Sem equipamento líder"}
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Apontamentos</div>
                <div className="mt-1 font-medium">{agriculturaData.resumo.apontamentos_total}</div>
                <div className="text-xs text-muted-foreground">
                  {formatNumber(agriculturaData.resumo.hectares_totais)} ha em campo
                </div>
              </div>
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Produtividade</div>
                <div className="mt-1 font-medium">
                  {agriculturaData.resumo.produtividade_media_ha_hora !== null
                    ? `${formatNumber(agriculturaData.resumo.produtividade_media_ha_hora)} ha/h`
                    : "—"}
                </div>
                <div className="text-xs text-muted-foreground">
                  Custo por ha: {agriculturaData.resumo.custo_medio_por_ha !== null ? formatCurrency(agriculturaData.resumo.custo_medio_por_ha) : "—"}
                </div>
              </div>
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Operação líder</div>
                <div className="mt-1 font-medium">
                  {agriculturaData.apontamentos_por_operacao[0]?.tipo_operacao || "—"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {agriculturaData.apontamentos_por_operacao[0]
                    ? `${formatNumber(agriculturaData.apontamentos_por_operacao[0].hectares_totais)} ha • ${formatCurrency(agriculturaData.apontamentos_por_operacao[0].custo_total)}`
                    : "Sem apontamentos consolidados"}
                </div>
              </div>
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Operador líder</div>
                <div className="mt-1 font-medium">
                  {agriculturaData.apontamentos_por_operador[0]?.operador_nome || "—"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {agriculturaData.apontamentos_por_operador[0]
                    ? `${formatNumber(agriculturaData.apontamentos_por_operador[0].hectares_totais)} ha • ${agriculturaData.apontamentos_por_operador[0].apontamentos} apontamentos`
                    : "Sem apontamentos consolidados"}
                </div>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Talhão líder</div>
                <div className="mt-1 font-medium">
                  {agriculturaData.apontamentos_por_talhao[0]?.talhao_nome || "—"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {agriculturaData.apontamentos_por_talhao[0]
                    ? `${formatNumber(agriculturaData.apontamentos_por_talhao[0].hectares_totais)} ha • ${agriculturaData.apontamentos_por_talhao[0].apontamentos} apontamentos`
                    : "Sem apontamentos consolidados"}
                </div>
              </div>
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Equipamento líder</div>
                <div className="mt-1 font-medium">
                  {agriculturaData.equipamentos_por_apontamento[0]?.equipamento_nome || "—"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {agriculturaData.equipamentos_por_apontamento[0]
                    ? `${formatNumber(agriculturaData.equipamentos_por_apontamento[0].hectares_totais)} ha • ${agriculturaData.equipamentos_por_apontamento[0].apontamentos} apontamentos`
                    : "Sem apontamentos consolidados"}
                </div>
              </div>
            </div>
            <div className="flex justify-end">
              <Button asChild variant="outline" size="sm" className="h-8 gap-1.5">
                <Link href="/dashboard/operacional/frota/agricultura">
                  <Tractor className="size-3.5" />
                  Ver uso agrícola
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : !hasEnterpriseTier ? (
        <TierUpgradeCard
          title="Uso agrícola no Enterprise"
          description="Integração Frota x Agricultura e custo por safra, talhão e operação exigem o plano Enterprise."
          requiredTier="ENTERPRISE"
          feature="frota_agricultura_dashboard"
          surface="frota_dashboard"
        />
      ) : null}
    </>
  );
}
export default FrotaUsoAgricolaPanel;
