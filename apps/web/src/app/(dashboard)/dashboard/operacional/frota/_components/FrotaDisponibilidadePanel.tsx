import Link from "next/link";
import { CalendarClock, Lock, ShieldAlert, Tractor, Wrench } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { KpiCard } from "./FrotaKPICards";
import { FrotaDisponibilidadeDashboard } from "./types";

interface FrotaDisponibilidadeKPICardsProps {
  disponibilidadeData: FrotaDisponibilidadeDashboard | undefined;
  hasProfessionalTier: boolean;
}

export function FrotaDisponibilidadeKPICards({
  disponibilidadeData,
  hasProfessionalTier,
}: FrotaDisponibilidadeKPICardsProps) {
  return (
    <>
      {disponibilidadeData ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <KpiCard
            title="Disponíveis"
            value={disponibilidadeData.resumo.disponiveis}
            description={`${disponibilidadeData.resumo.checklist_pendente} checklist pendente`}
            icon={Tractor}
          />
          <KpiCard
            title="Em uso"
            value={disponibilidadeData.resumo.em_uso}
            description="Operação em andamento"
            icon={CalendarClock}
            tone={disponibilidadeData.resumo.em_uso > 0 ? "warning" : "default"}
          />
          <KpiCard
            title="Bloqueados"
            value={disponibilidadeData.resumo.bloqueados}
            description={`${disponibilidadeData.resumo.nao_conformes} não conformes`}
            icon={Lock}
            tone={disponibilidadeData.resumo.bloqueados > 0 ? "danger" : "default"}
          />
          <KpiCard
            title="Em manutenção"
            value={disponibilidadeData.resumo.em_manutencao}
            description="OS e indisponibilidade ativa"
            icon={Wrench}
            tone={disponibilidadeData.resumo.em_manutencao > 0 ? "warning" : "default"}
          />
          <KpiCard
            title="Docs vencidos"
            value={disponibilidadeData.resumo.documentos_vencidos}
            description="Pendências documentais"
            icon={ShieldAlert}
            tone={disponibilidadeData.resumo.documentos_vencidos > 0 ? "danger" : "default"}
          />
        </div>
      ) : !hasProfessionalTier ? (
        <TierUpgradeCard
          title="Disponibilidade no Profissional"
          description="Bloqueio/liberação, checklist e disponibilidade operacional consolidada ficam liberados no plano Profissional."
          requiredTier="PROFISSIONAL"
          feature="frota_disponibilidade_dashboard"
          surface="frota_dashboard"
        />
      ) : null}
    </>
  );
}

interface FrotaDisponibilidadePanelProps {
  disponibilidadeData: FrotaDisponibilidadeDashboard | undefined;
  hasProfessionalTier: boolean;
}

export function FrotaDisponibilidadePanel({
  disponibilidadeData,
  hasProfessionalTier,
}: FrotaDisponibilidadePanelProps) {
  return (
    <>
      {disponibilidadeData ? (
        <Card className="rounded-sm shadow-sm">
          <CardHeader>
            <CardTitle>Disponibilidade operacional</CardTitle>
            <CardDescription>Resumo do bloqueio, checklist e conformidade da frota.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="rounded-sm border p-3">
              <div className="font-medium">{disponibilidadeData.resumo.disponiveis} equipamento(s) disponível(is)</div>
              <div className="text-xs text-muted-foreground">
                {disponibilidadeData.resumo.em_uso} em uso, {disponibilidadeData.resumo.bloqueados} bloqueado(s)
              </div>
            </div>
            <div className="rounded-sm border p-3">
              <div className="font-medium">{disponibilidadeData.resumo.checklist_pendente} checklist(s) pendente(s)</div>
              <div className="text-xs text-muted-foreground">
                {disponibilidadeData.resumo.nao_conformes} não conforme(s) e {disponibilidadeData.resumo.documentos_vencidos} documento(s) vencido(s)
              </div>
            </div>
            <div className="flex justify-end">
              <Button asChild variant="outline" size="sm" className="h-8 gap-1.5">
                <Link href="/dashboard/operacional/frota/disponibilidade">
                  <Lock className="size-3.5" />
                  Ver disponibilidade
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : !hasProfessionalTier ? (
        <TierUpgradeCard
          title="Disponibilidade operacional no Profissional"
          description="Checklist, bloqueios e visão consolidada de disponibilidade da frota exigem o plano Profissional."
          requiredTier="PROFISSIONAL"
          feature="frota_disponibilidade_resumo"
          surface="frota_dashboard"
        />
      ) : null}
    </>
  );
}
export default FrotaDisponibilidadePanel;
