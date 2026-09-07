import Link from "next/link";
import { CalendarClock, Eye } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  FrotaRankingItem,
  FrotaUltimoAbastecimento,
  FrotaJornadaDashboardItem,
} from "./types";
import { formatCurrency, formatDateTime, formatNumber } from "./utils";

interface FrotaManutencoesPanelProps {
  rankingMaiorCusto: FrotaRankingItem[];
  ultimosAbastecimentos: FrotaUltimoAbastecimento[];
  ultimasJornadas: FrotaJornadaDashboardItem[];
}

export function FrotaManutencoesPanel({
  rankingMaiorCusto,
  ultimosAbastecimentos,
  ultimasJornadas,
}: FrotaManutencoesPanelProps) {
  return (
    <div className="space-y-6">
      <Card className="rounded-sm shadow-sm">
        <CardHeader>
          <CardTitle>Ranking de maior custo</CardTitle>
          <CardDescription>Máquinas com maior custo acumulado considerando abastecimento e manutenção.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {rankingMaiorCusto.length === 0 ? (
            <p className="text-sm text-muted-foreground">Ainda não há custos acumulados para ranquear.</p>
          ) : (
            rankingMaiorCusto.map((item, index) => (
              <div key={item.equipamento_id} className="rounded-sm border p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-muted-foreground">#{index + 1}</div>
                    <div className="font-medium">{item.equipamento_nome}</div>
                    <div className="text-xs text-muted-foreground">
                      {item.tipo} • {item.os_abertas} OS aberta(s)
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold">{formatCurrency(item.custo_total)}</div>
                    <div className="text-xs text-muted-foreground">
                      {formatCurrency(item.custo_abastecimento)} combustível
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatCurrency(item.custo_manutencao)} manutenção
                    </div>
                    <div className="mt-2">
                      <Button asChild variant="outline" size="sm" className="h-8 gap-1.5">
                        <Link href={`/dashboard/operacional/frota/${item.equipamento_id}`}>
                          <Eye className="size-3.5" />
                          Ver detalhe
                        </Link>
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card className="rounded-sm shadow-sm">
        <CardHeader>
          <CardTitle>Últimos abastecimentos</CardTitle>
          <CardDescription>Registros mais recentes para acompanhamento de consumo e custo.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {ultimosAbastecimentos.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum abastecimento registrado até o momento.</p>
          ) : (
            ultimosAbastecimentos.map((abastecimento) => (
              <div key={abastecimento.id} className="flex items-start justify-between gap-3 rounded-sm border p-3">
                <div className="min-w-0">
                  <div className="font-medium">{abastecimento.equipamento_nome}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatDateTime(abastecimento.data)} • {abastecimento.tipo_combustivel}
                  </div>
                </div>
                <div className="text-right text-xs">
                  <div className="font-semibold">{formatCurrency(abastecimento.custo_total)}</div>
                  <div className="text-muted-foreground">{formatNumber(abastecimento.litros)} L</div>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card className="rounded-sm shadow-sm">
        <CardHeader>
          <CardTitle>Últimas jornadas</CardTitle>
          <CardDescription>Uso operacional recente com leitura trabalhada e custo estimado.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {ultimasJornadas.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhuma jornada operacional registrada até o momento.</p>
          ) : (
            ultimasJornadas.map((jornada) => (
              <div key={jornada.jornada_id} className="rounded-sm border p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-medium">{jornada.equipamento_nome}</div>
                    <div className="text-xs text-muted-foreground">
                      {jornada.tipo_operacao} • {jornada.operador_nome || "Sem operador"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDateTime(jornada.data_inicio)}
                    </div>
                  </div>
                  <div className="text-right text-xs">
                    <div className="font-semibold">
                      {jornada.custo_estimado !== null ? formatCurrency(jornada.custo_estimado) : "—"}
                    </div>
                    <div className="text-muted-foreground">
                      {jornada.horas_trabalhadas !== null
                        ? `${formatNumber(jornada.horas_trabalhadas)} h`
                        : jornada.km_trabalhados !== null
                          ? `${formatNumber(jornada.km_trabalhados)} km`
                          : "Sem leitura final"}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
          <div className="flex justify-end">
            <Button asChild variant="outline" size="sm" className="h-8 gap-1.5">
              <Link href="/dashboard/operacional/frota/jornadas">
                <CalendarClock className="size-3.5" />
                Ver jornadas
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
export default FrotaManutencoesPanel;
