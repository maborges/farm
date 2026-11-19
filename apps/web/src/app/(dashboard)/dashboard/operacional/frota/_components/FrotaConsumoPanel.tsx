import Link from "next/link";
import { CheckCircle2, Droplets } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { cn } from "@/lib/utils";
import { FrotaConsumoDashboard } from "./types";
import { formatDateOrDash, formatNumber } from "./utils";

interface FrotaConsumoAlertasProps {
  consumoData: FrotaConsumoDashboard | undefined;
  hasProfessionalTier: boolean;
}

export function FrotaConsumoAlertas({
  consumoData,
  hasProfessionalTier,
}: FrotaConsumoAlertasProps) {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardHeader>
        <CardTitle>Alertas de consumo</CardTitle>
        <CardDescription>Resumo das principais anomalias de abastecimento e eficiência.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {!hasProfessionalTier ? (
          <TierUpgradeCard
            title="Consumo e eficiência no Profissional"
            description="Anomalias de abastecimento e indicadores de eficiência da frota fazem parte do plano Profissional."
            requiredTier="PROFISSIONAL"
            feature="frota_consumo_dashboard"
            surface="frota_dashboard"
          />
        ) : !consumoData || consumoData.alertas.length === 0 ? (
          <Alert variant="success">
            <CheckCircle2 />
            <AlertDescription>
              Nenhuma anomalia de consumo detectada.
            </AlertDescription>
          </Alert>
        ) : (
          consumoData.alertas.slice(0, 4).map((alerta) => (
            <div
              key={`${alerta.tipo}-${alerta.equipamento_id}-${alerta.detalhe}`}
              className={cn(
                "rounded-sm border p-4",
                alerta.severidade === "danger"
                  ? "border-alert-destructive-border bg-alert-destructive-bg text-alert-destructive-title"
                  : "border-alert-warning-border bg-alert-warning-bg text-alert-warning-title"
              )}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={alerta.severidade === "danger" ? "danger" : "warning"}>
                      {alerta.titulo}
                    </Badge>
                    <span className="text-sm font-medium">{alerta.equipamento_nome}</span>
                  </div>
                  <p
                    className={cn(
                      "text-sm",
                      alerta.severidade === "danger"
                        ? "text-alert-destructive-description"
                        : "text-alert-warning-description"
                    )}
                  >
                    {alerta.detalhe}
                  </p>
                </div>
                <div
                  className={cn(
                    "text-right text-xs",
                    alerta.severidade === "danger"
                      ? "text-alert-destructive-description"
                      : "text-alert-warning-description"
                  )}
                >
                  {alerta.data_referencia ? formatDateOrDash(alerta.data_referencia) : "Sem data"}
                </div>
              </div>
            </div>
          ))
        )}
        {hasProfessionalTier ? (
          <div className="flex justify-end">
            <Button asChild variant="outline" size="sm" className="h-8 gap-1.5">
              <Link href="/dashboard/operacional/frota/consumo">
                <Droplets className="size-3.5" />
                Ver consumo e eficiência
              </Link>
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

interface FrotaEficienciaRankingProps {
  consumoData: FrotaConsumoDashboard | undefined;
  hasProfessionalTier: boolean;
}

export function FrotaEficienciaRanking({
  consumoData,
  hasProfessionalTier,
}: FrotaEficienciaRankingProps) {
  return (
    <>
      {consumoData ? (
        <Card className="rounded-sm shadow-sm">
          <CardHeader>
            <CardTitle>Eficiência operacional</CardTitle>
            <CardDescription>Ranking de consumo para comparação direta entre equipamentos.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {consumoData.ranking_eficiencia.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sem ranking de eficiência consolidado.</p>
            ) : (
              consumoData.ranking_eficiencia.slice(0, 3).map((item, index) => (
                <div key={item.equipamento_id} className="rounded-sm border p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-muted-foreground">#{index + 1}</div>
                      <div className="font-medium">{item.equipamento_nome}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.equipamento_tipo} • {item.metrica_principal}
                      </div>
                    </div>
                    <div className="text-right text-xs">
                      <div className="font-semibold">
                        {item.eficiencia_score !== null ? formatNumber(item.eficiencia_score) : "—"}
                      </div>
                      <div className="text-muted-foreground">
                        {item.consumo_medio_l_h !== null
                          ? `${formatNumber(item.consumo_medio_l_h)} L/h`
                          : item.consumo_medio_km_l !== null
                            ? `${formatNumber(item.consumo_medio_km_l)} L/km`
                            : "Sem métrica"}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
            <div className="flex justify-end">
              <Button asChild variant="outline" size="sm" className="h-8 gap-1.5">
                <Link href="/dashboard/operacional/frota/consumo">
                  <Droplets className="size-3.5" />
                  Ver ranking
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : !hasProfessionalTier ? (
        <TierUpgradeCard
          title="Eficiência operacional no Profissional"
          description="Ranking de eficiência por consumo depende do plano Profissional."
          requiredTier="PROFISSIONAL"
          feature="frota_consumo_ranking"
          surface="frota_dashboard"
        />
      ) : null}
    </>
  );
}
