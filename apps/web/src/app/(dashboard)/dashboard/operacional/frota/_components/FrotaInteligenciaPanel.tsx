import Link from "next/link";
import { BrainCircuit } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { FrotaInteligenciaDashboard } from "./types";
import { formatRiskLabel, getRiskClass } from "./utils";

interface FrotaInteligenciaPanelProps {
  inteligenciaData: FrotaInteligenciaDashboard | undefined;
  hasEnterpriseTier: boolean;
}

export function FrotaInteligenciaPanel({
  inteligenciaData,
  hasEnterpriseTier,
}: FrotaInteligenciaPanelProps) {
  return (
    <>
      {inteligenciaData ? (
        <Card className="rounded-sm shadow-sm">
          <CardHeader>
            <CardTitle>Frota em risco</CardTitle>
            <CardDescription>Top 5 equipamentos com maior criticidade operacional.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-sm border p-3">
              <div className="font-medium">{inteligenciaData.resumo.equipamentos_criticos} crítico(s)</div>
              <div className="text-xs text-muted-foreground">
                {inteligenciaData.resumo.equipamentos_alto_risco} equipamento(s) em alto risco
              </div>
            </div>
            {inteligenciaData.ranking_risco.slice(0, 5).map((item) => (
              <div key={item.equipamento_id} className="rounded-sm border p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{item.equipamento_nome}</div>
                    <div className="text-xs text-muted-foreground">{item.detalhe || item.equipamento_tipo}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold">{item.score_risco ?? "—"}</div>
                    {item.nivel_risco ? (
                      <Badge variant="outline" className={getRiskClass(item.nivel_risco)}>
                        {formatRiskLabel(item.nivel_risco)}
                      </Badge>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
            <div className="flex justify-end">
              <Button asChild variant="outline" size="sm" className="h-8 gap-1.5">
                <Link href="/dashboard/operacional/frota/inteligencia">
                  <BrainCircuit className="size-3.5" />
                  Ver inteligência
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : !hasEnterpriseTier ? (
        <TierUpgradeCard
          title="Inteligência operacional no Enterprise"
          description="Score de risco e recomendações automáticas ficam liberados no plano Enterprise."
          requiredTier="ENTERPRISE"
          feature="frota_inteligencia_dashboard"
          surface="frota_dashboard"
        />
      ) : null}
    </>
  );
}
export default FrotaInteligenciaPanel;
