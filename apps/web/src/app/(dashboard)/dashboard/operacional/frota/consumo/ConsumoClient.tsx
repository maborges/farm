"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BarChart3, CheckCircle2, Droplets, Gauge, ShieldAlert, Tractor, Wrench } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiFetch } from "@/lib/api";
import { useHasTier } from "@/hooks/use-has-tier";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";
import { KpiCard as ResumoCard } from "../_components/FrotaKPICards";

import { ConsumoResponse, ConsumoResumo, ConsumoRankingItem } from "./types";

interface ConsumoClientProps {
  initialData: ConsumoResponse | null;
  serverFazendaId: string;
}

export function ConsumoClient({ initialData, serverFazendaId }: ConsumoClientProps) {
  const { activeFazendaId } = useAppStore();
  const hasProfessionalTier = useHasTier("PROFISSIONAL");

  const isServerDataMatching = (!activeFazendaId && !serverFazendaId) || (activeFazendaId === serverFazendaId);

  const { data, isLoading, isError, error } = useQuery<ConsumoResponse>({
    queryKey: ["frota", "consumo", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/consumo", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasProfessionalTier,
    initialData: isServerDataMatching ? (initialData ?? undefined) : undefined,
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Consumo & Eficiência"
        description="Inteligência operacional de abastecimento com eficiência por equipamento, custos e alertas de anomalia."
        icon={<Droplets className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Operacional", href: "/operacional" },
          { label: "Frota", href: "/dashboard/operacional/frota" },
          { label: "Consumo" },
        ]}
        actions={
          <>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/operacional/frota">
                <Tractor className="size-3.5" />
                Dashboard Frota
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/operacional/manutencoes">
                <Wrench className="size-3.5" />
                Manutenções
              </Link>
            </Button>
          </>
        }
      />

      {!hasProfessionalTier ? (
        <TierUpgradeCard
          title="Consumo e eficiência disponíveis no Profissional"
          description="Indicadores de eficiência, ranking e alertas operacionais de abastecimento exigem o plano Profissional."
          requiredTier="PROFISSIONAL"
          feature="frota_consumo_eficiencia"
          surface="frota_consumo_page"
        />
      ) : null}

      {isLoading ? <ConsumoSkeleton /> : null}

      {hasProfessionalTier && !isLoading && isError ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<ShieldAlert />}
              title="Não foi possível carregar a eficiência da frota"
              description={error instanceof Error ? error.message : "Erro ao consultar o backend."}
            />
          </CardContent>
        </Card>
      ) : null}

      {hasProfessionalTier && !isLoading && !isError && data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <ResumoCard title="Litros totais" value={`${formatNumber(data.resumo.litros_totais)} L`} description="Combustível registrado" icon={Droplets} />
            <ResumoCard title="Custo total" value={formatCurrency(data.resumo.custo_total_combustivel)} description="Investimento acumulado" icon={BarChart3} />
            <ResumoCard title="Custo médio/L" value={data.resumo.custo_medio_litro ? formatCurrency(data.resumo.custo_medio_litro) : "—"} description="Preço médio do combustível" icon={Gauge} />
            <ResumoCard
              title="Consumo médio"
              value={resolveConsumoResumo(data.resumo)}
              description="Hora e km quando disponíveis"
              icon={Gauge}
            />
            <ResumoCard
              title="Equip. com anomalia"
              value={data.resumo.equipamentos_com_anomalia}
              description={`${data.resumo.total_alertas} alerta(s) ativo(s)`}
              icon={AlertTriangle}
              tone={data.resumo.equipamentos_com_anomalia > 0 ? "danger" : "default"}
            />
          </div>

          {data.ranking_eficiencia.length === 0 && data.alertas.length === 0 ? (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-6">
                <EmptyState
                  icon={<Droplets />}
                  title="Histórico insuficiente para eficiência"
                  description="Registre abastecimentos com leituras de horímetro ou km para formar os indicadores."
                />
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,1fr)]">
              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Ranking de eficiência</CardTitle>
                  <CardDescription>Comparativo por equipamento usando a melhor métrica disponível para cada ativo.</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.ranking_eficiencia.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Ainda não há dados suficientes para montar o ranking.</p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Equipamento</TableHead>
                          <TableHead>Métrica</TableHead>
                          <TableHead>Eficiência</TableHead>
                          <TableHead>Custo operacional</TableHead>
                          <TableHead>Variação frota</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.ranking_eficiencia.map((item, index) => (
                          <TableRow key={item.equipamento_id}>
                            <TableCell className="align-top">
                              <div className="space-y-1">
                                <div className="font-medium">
                                  #{index + 1} {item.equipamento_nome}
                                </div>
                                <div className="text-xs text-muted-foreground">{item.equipamento_tipo}</div>
                              </div>
                            </TableCell>
                            <TableCell className="align-top">{formatMetrica(item.metrica_principal)}</TableCell>
                            <TableCell className="align-top">
                              <div className="space-y-1 text-xs">
                                <div className="font-medium">{item.eficiencia_score ? `${formatNumber(item.eficiencia_score)} pts` : "—"}</div>
                                <div className="text-muted-foreground">
                                  {item.consumo_medio_km_l !== null
                                    ? `${formatNumber(item.consumo_medio_km_l)} km/L`
                                    : item.consumo_medio_l_h !== null
                                      ? `${formatNumber(item.consumo_medio_l_h)} L/h`
                                      : "sem histórico"}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell className="align-top text-xs text-muted-foreground">
                              {item.custo_por_km !== null
                                ? `${formatCurrency(item.custo_por_km)}/km`
                                : item.custo_por_hora !== null
                                  ? `${formatCurrency(item.custo_por_hora)}/h`
                                  : "—"}
                            </TableCell>
                            <TableCell className="align-top">
                              {item.variacao_media_frota_percent !== null ? (
                                <Badge variant="outline">
                                  {formatPercent(item.variacao_media_frota_percent)}
                                </Badge>
                              ) : (
                                "—"
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Alertas de consumo</CardTitle>
                  <CardDescription>Principais anomalias encontradas no histórico de abastecimento.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.alertas.length === 0 ? (
                    <Alert variant="success">
                      <CheckCircle2 />
                      <AlertDescription>
                        Nenhuma anomalia de consumo detectada no momento.
                      </AlertDescription>
                    </Alert>
                  ) : (
                    data.alertas.map((alerta) => (
                      <div
                        key={`${alerta.tipo}-${alerta.equipamento_id}-${alerta.detalhe}`}
                        className={cn(
                          "rounded-sm border p-4",
                          alerta.severidade === "danger"
                            ? "border-alert-destructive-border bg-alert-destructive-bg text-alert-destructive-title"
                            : "border-alert-warning-border bg-alert-warning-bg text-alert-warning-title"
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
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
                              "text-xs",
                              alerta.severidade === "danger"
                                ? "text-alert-destructive-description"
                                : "text-alert-warning-description"
                            )}
                          >
                            {alerta.data_referencia ? formatDateTime(alerta.data_referencia) : "Sem data"}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

function ConsumoSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-sm" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,1fr)]">
        <Skeleton className="h-[520px] rounded-sm" />
        <Skeleton className="h-[520px] rounded-sm" />
      </div>
    </div>
  );
}

function resolveConsumoResumo(resumo: ConsumoResumo) {
  const partes = [];
  if (resumo.consumo_medio_l_h !== null) partes.push(`${formatNumber(resumo.consumo_medio_l_h)} L/h`);
  if (resumo.consumo_medio_km_l !== null) partes.push(`${formatNumber(resumo.consumo_medio_km_l)} km/L`);
  return partes.length > 0 ? partes.join(" • ") : "—";
}

function formatCurrency(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value ?? 0);
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(value);
}

function formatPercent(value: number) {
  return `${value > 0 ? "+" : ""}${formatNumber(value)}%`;
}

function formatMetrica(value: ConsumoRankingItem["metrica_principal"]) {
  if (value === "HORIMETRO") return "Horímetro";
  if (value === "KM") return "KM";
  if (value === "AMBOS") return "Ambos";
  return "Indisponível";
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}
