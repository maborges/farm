import Link from "next/link";
import { DollarSign, Droplets, Tractor, Wrench } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { KpiCard } from "./FrotaKPICards";
import { FrotaCustoDashboard, FrotaResumo } from "./types";
import { formatCurrency, formatNumber } from "./utils";

interface FrotaCustosKPICardsProps {
  custosData: FrotaCustoDashboard | undefined;
  hasProfessionalTier: boolean;
}

export function FrotaCustosKPICards({
  custosData,
  hasProfessionalTier,
}: FrotaCustosKPICardsProps) {
  return (
    <>
      {custosData ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            title="Custo total frota"
            value={formatCurrency(custosData.resumo.custo_total_frota)}
            description="Consolidação financeira"
            icon={DollarSign}
          />
          <KpiCard
            title="Combustível"
            value={formatCurrency(custosData.resumo.custo_combustivel)}
            description={formatCurrency(custosData.resumo.custo_medio_por_equipamento) + " por equipamento"}
            icon={Droplets}
          />
          <KpiCard
            title="Manutenção + peças"
            value={formatCurrency(custosData.resumo.custo_manutencao + custosData.resumo.custo_pecas_itens)}
            description={formatCurrency(custosData.resumo.custo_pecas_itens) + " em peças"}
            icon={Wrench}
            tone={custosData.resumo.custo_manutencao + custosData.resumo.custo_pecas_itens > 0 ? "warning" : "default"}
          />
          <KpiCard
            title="Equipamento mais caro"
            value={custosData.resumo.equipamento_mais_caro_nome || "—"}
            description={
              custosData.resumo.equipamento_mais_caro_total !== null
                ? formatCurrency(custosData.resumo.equipamento_mais_caro_total)
                : "Sem custo acumulado"
            }
            icon={Tractor}
          />
        </div>
      ) : !hasProfessionalTier ? (
        <TierUpgradeCard
          title="Custos avançados no Profissional"
          description="Custo total por máquina, custo por hora e leitura financeira consolidada exigem o plano Profissional."
          requiredTier="PROFISSIONAL"
          feature="frota_custos_dashboard"
          surface="frota_dashboard"
        />
      ) : null}
    </>
  );
}

interface FrotaCustosPanelProps {
  custosData: FrotaCustoDashboard | undefined;
  resumo: FrotaResumo;
  hasProfessionalTier: boolean;
}

export function FrotaCustosPanel({
  custosData,
  resumo,
  hasProfessionalTier,
}: FrotaCustosPanelProps) {
  return (
    <>
      {custosData ? (
        <Card className="rounded-sm shadow-sm">
          <CardHeader>
            <CardTitle>Resumo financeiro</CardTitle>
            <CardDescription>Leitura econômica da frota com custo por hectare, prevenção e correção.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Hectares apontados</div>
                <div className="mt-1 font-medium">{formatNumber(resumo.hectares_totais_apontados)}</div>
              </div>
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Custo por hectare</div>
                <div className="mt-1 font-medium">
                  {resumo.custo_por_hectare !== null ? formatCurrency(resumo.custo_por_hectare) : "—"}
                </div>
              </div>
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Rentabilidade</div>
                <div className="mt-1 font-medium">
                  {resumo.indice_rentabilidade_operacional !== null
                    ? `${formatNumber(resumo.indice_rentabilidade_operacional)} ha / R$ 1.000`
                    : "—"}
                </div>
              </div>
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Preventivo</div>
                <div className="mt-1 font-medium">{formatCurrency(resumo.custo_preventivo_total)}</div>
                <div className="text-xs text-muted-foreground">
                  {formatNumber(resumo.proporcao_custo_preventivo_percentual)}% do custo de manutenção
                </div>
              </div>
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Corretivo</div>
                <div className="mt-1 font-medium">{formatCurrency(resumo.custo_corretivo_total)}</div>
                <div className="text-xs text-muted-foreground">
                  {formatNumber(resumo.hectares_totais_apontados)} ha apontados
                </div>
              </div>
              <div className="rounded-sm border p-3">
                <div className="text-[10px] font-black uppercase text-muted-foreground">Ociosidade</div>
                <div className="mt-1 font-medium">{resumo.equipamentos_ociosos} equipamento(s)</div>
              </div>
            </div>
            <div className="flex justify-end">
              <Button asChild variant="outline" size="sm" className="h-8 gap-1.5">
                <Link href="/dashboard/operacional/frota/custos">
                  <DollarSign className="size-3.5" />
                  Ver custos totais
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : !hasProfessionalTier ? (
        <TierUpgradeCard
          title="Resumo financeiro no Profissional"
          description="Custos totais, combustível, manutenção e peças consolidadas ficam liberados no plano Profissional."
          requiredTier="PROFISSIONAL"
          feature="frota_custos_resumo"
          surface="frota_dashboard"
        />
      ) : null}
    </>
  );
}
export default FrotaCustosPanel;
