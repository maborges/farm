import Link from "next/link";
import { Eye } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { FrotaEquipamento } from "./types";
import {
  formatCurrency,
  formatDateOrDash,
  formatNumber,
  getMaintenanceBadgeClass,
  MANUTENCAO_LABELS,
  RISCO_LABELS,
} from "./utils";

interface FrotaEquipamentosTableProps {
  equipamentos: FrotaEquipamento[];
}

export function FrotaEquipamentosTable({
  equipamentos,
}: FrotaEquipamentosTableProps) {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardHeader>
        <CardTitle>Equipamentos da frota</CardTitle>
        <CardDescription>Status operacional, custo acumulado, OS em aberto e indicadores de risco.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {equipamentos.map((equipamento) => (
          <div key={equipamento.equipamento_id} className="rounded-sm border p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0 space-y-1">
                <div className="font-medium">{equipamento.nome}</div>
                <div className="text-xs text-muted-foreground">
                  {[equipamento.tipo, equipamento.marca, equipamento.modelo].filter(Boolean).join(" • ")}
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  <WorkflowStatusBadge status={equipamento.status} />
                  <Badge variant="outline" className={getMaintenanceBadgeClass(equipamento.manutencao_status)}>
                    {MANUTENCAO_LABELS[equipamento.manutencao_status]}
                  </Badge>
                  {equipamento.jornada_aberta ? (
                    <Badge variant="outline" className="border-amber-200 text-amber-700">
                      Em uso
                    </Badge>
                  ) : null}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <div className="min-w-0">
                  <div className="text-[10px] font-black uppercase text-muted-foreground">Uso</div>
                  <div className="mt-1 text-xs space-y-1">
                    <div>Horímetro: {formatNumber(equipamento.horimetro_atual)}</div>
                    <div>KM: {formatNumber(equipamento.km_atual)}</div>
                    <div className="text-muted-foreground">
                      Últ. abastecimento: {formatDateOrDash(equipamento.ultimo_abastecimento_em)}
                    </div>
                  </div>
                </div>

                <div className="min-w-0">
                  <div className="text-[10px] font-black uppercase text-muted-foreground">Custos</div>
                  <div className="mt-1 text-xs space-y-1">
                    <div className="font-medium">{formatCurrency(equipamento.custo_total)}</div>
                    <div className="text-muted-foreground">Combustível: {formatCurrency(equipamento.custo_abastecimento)}</div>
                    <div className="text-muted-foreground">Manutenção: {formatCurrency(equipamento.custo_manutencao)}</div>
                    <div className="text-muted-foreground">
                      {equipamento.custo_por_hora !== null ? `${formatCurrency(equipamento.custo_por_hora)}/h` : "—"}
                      {" • "}
                      {equipamento.custo_por_km !== null ? `${formatCurrency(equipamento.custo_por_km)}/km` : "—"}
                    </div>
                  </div>
                </div>

                <div className="min-w-0">
                  <div className="text-[10px] font-black uppercase text-muted-foreground">OS</div>
                  <div className="mt-1 text-xs">
                    <Badge variant="outline">{equipamento.os_abertas} aberta(s)</Badge>
                  </div>
                </div>

                <div className="min-w-0">
                  <div className="text-[10px] font-black uppercase text-muted-foreground">Risco</div>
                  <div className="mt-1">
                    {equipamento.riscos.length === 0 ? (
                      <Badge variant="outline" className="border-emerald-200 text-emerald-700">
                        Sem alerta
                      </Badge>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {equipamento.riscos.map((risco) => (
                          <Badge key={risco} variant="outline" className="border-amber-200 text-amber-700">
                            {RISCO_LABELS[risco]}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex justify-end lg:self-center">
                <Button asChild variant="outline" size="sm" className="h-8 gap-1.5">
                  <Link href={`/dashboard/operacional/frota/${equipamento.equipamento_id}`}>
                    <Eye className="size-3.5" />
                    Ver detalhe
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
export default FrotaEquipamentosTable;
