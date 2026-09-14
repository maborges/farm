"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, DollarSign, Fuel, ShieldAlert, Tractor, Wallet, Wrench } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
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

import { CustoResponse, Periodo } from "./types";

interface CustosClientProps {
  initialData: CustoResponse | null;
  serverFazendaId: string;
}

const PERIODOS: Array<{ value: Periodo; label: string }> = [
  { value: "30", label: "30 dias" },
  { value: "90", label: "90 dias" },
  { value: "180", label: "180 dias" },
  { value: "all", label: "Todo histórico" },
];

export function CustosClient({ initialData, serverFazendaId }: CustosClientProps) {
  const { activeFazendaId } = useAppStore();
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const [periodo, setPeriodo] = useState<Periodo>("90");
  const periodoDias = periodo === "all" ? undefined : Number(periodo);

  const isServerDataMatching =
    ((!activeFazendaId && !serverFazendaId) || (activeFazendaId === serverFazendaId)) &&
    (periodo === "90");

  const { data, isLoading, isError, error } = useQuery<CustoResponse>({
    queryKey: ["frota", "custos", activeFazendaId, periodo],
    queryFn: () =>
      apiFetch("/frota/custos", {
        params: {
          periodo_dias: periodoDias,
          unidade_produtiva_id: activeFazendaId || undefined,
        },
      }),
    enabled: hasProfessionalTier,
    initialData: isServerDataMatching ? (initialData ?? undefined) : undefined,
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Custos Totais da Frota"
        description="Consolidação econômica por equipamento com combustível, manutenção, peças e custo operacional por hora ou km."
        icon={<Wallet className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Operacional", href: "/operacional" },
          { label: "Frota", href: "/dashboard/operacional/frota" },
          { label: "Custos" },
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
              <Link href="/dashboard/operacional/frota/consumo">
                <Fuel className="size-3.5" />
                Consumo
              </Link>
            </Button>
          </>
        }
      />

      {!hasProfessionalTier ? (
        <TierUpgradeCard
          title="Custos avançados disponíveis no Profissional"
          description="Consolidação de custo por máquina, custo por hora e custo por km exigem o plano Profissional."
          requiredTier="PROFISSIONAL"
          feature="frota_custos"
          surface="frota_custos_page"
        />
      ) : (
        <div className="flex flex-wrap gap-2">
          {PERIODOS.map((item) => (
            <Button
              key={item.value}
              variant={periodo === item.value ? "default" : "outline"}
              size="sm"
              onClick={() => setPeriodo(item.value)}
            >
              {item.label}
            </Button>
          ))}
        </div>
      )}

      {isLoading ? <CustosSkeleton /> : null}

      {hasProfessionalTier && !isLoading && isError ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<ShieldAlert />}
              title="Não foi possível carregar os custos da frota"
              description={error instanceof Error ? error.message : "Erro ao consultar o backend."}
            />
          </CardContent>
        </Card>
      ) : null}

      {hasProfessionalTier && !isLoading && !isError && data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <ResumoCard title="Custo total" value={formatCurrency(data.resumo.custo_total_frota)} description="Frota consolidada" icon={Wallet} />
            <ResumoCard title="Combustível" value={formatCurrency(data.resumo.custo_combustivel)} description="Abastecimentos" icon={Fuel} />
            <ResumoCard title="Manutenção" value={formatCurrency(data.resumo.custo_manutencao)} description="Mão de obra e avulsas" icon={Wrench} />
            <ResumoCard title="Peças / Itens" value={formatCurrency(data.resumo.custo_pecas_itens)} description="Itens de OS" icon={BarChart3} />
            <ResumoCard title="Média por equipamento" value={formatCurrency(data.resumo.custo_medio_por_equipamento)} description="Base filtrada" icon={DollarSign} />
            <ResumoCard
              title="Equipamento mais caro"
              value={data.resumo.equipamento_mais_caro_nome || "—"}
              description={
                data.resumo.equipamento_mais_caro_total !== null
                  ? formatCurrency(data.resumo.equipamento_mais_caro_total)
                  : "Sem custo acumulado"
              }
              icon={Tractor}
              tone={data.resumo.equipamento_mais_caro_total ? "warning" : "default"}
            />
          </div>

          {data.equipamentos.length === 0 ? (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-6">
                <EmptyState
                  icon={<Wallet />}
                  title="Nenhum custo encontrado"
                  description="A base atual não possui abastecimentos, ordens de serviço ou manutenções para o filtro selecionado."
                />
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(320px,1fr)]">
              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Tabela analítica por equipamento</CardTitle>
                  <CardDescription>Composição de custo consolidada sem duplicar OS, itens e registros derivados.</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Equipamento</TableHead>
                        <TableHead>Uso</TableHead>
                        <TableHead>Combustível</TableHead>
                        <TableHead>Manutenção</TableHead>
                        <TableHead>Peças</TableHead>
                        <TableHead>Total</TableHead>
                        <TableHead>Custo/h km</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.equipamentos.map((item) => (
                        <TableRow key={item.equipamento_id}>
                          <TableCell className="align-top">
                            <div className="space-y-1">
                              <div className="font-medium">{item.equipamento_nome}</div>
                              <div className="text-xs text-muted-foreground">
                                {item.equipamento_tipo} • {item.equipamento_status}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="align-top text-xs">
                            <div>H: {formatNumber(item.horimetro_atual)}</div>
                            <div>KM: {formatNumber(item.km_atual)}</div>
                          </TableCell>
                          <TableCell className="align-top">{formatCurrency(item.custo_combustivel)}</TableCell>
                          <TableCell className="align-top">{formatCurrency(item.custo_manutencao)}</TableCell>
                          <TableCell className="align-top">{formatCurrency(item.custo_pecas_itens)}</TableCell>
                          <TableCell className="align-top">
                            <div className="space-y-1">
                              <div className="font-semibold">{formatCurrency(item.custo_total)}</div>
                              <div className="text-xs text-muted-foreground">
                                {item.participacao_percentual !== null ? `${formatNumber(item.participacao_percentual)}% da frota` : "—"}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="align-top text-xs">
                            <div>{item.custo_por_hora !== null ? `${formatCurrency(item.custo_por_hora)}/h` : "—"}</div>
                            <div>{item.custo_por_km !== null ? `${formatCurrency(item.custo_por_km)}/km` : "—"}</div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Ranking financeiro</CardTitle>
                  <CardDescription>Equipamentos com maior peso no custo total da frota.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.ranking.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Ainda não há dados suficientes para ranquear.</p>
                  ) : (
                    data.ranking.map((item, index) => (
                      <div key={item.equipamento_id} className="rounded-sm border p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-xs font-medium text-muted-foreground">#{index + 1}</div>
                            <div className="font-medium">{item.equipamento_nome}</div>
                            <div className="text-xs text-muted-foreground">{item.equipamento_tipo}</div>
                          </div>
                          <div className="text-right text-xs">
                            <div className="font-semibold">{formatCurrency(item.custo_total)}</div>
                            <div className="text-muted-foreground">
                              {item.participacao_percentual !== null ? `${formatNumber(item.participacao_percentual)}% da frota` : "—"}
                            </div>
                            <div className="mt-1 text-muted-foreground">
                              {item.custo_por_km !== null
                                ? `${formatCurrency(item.custo_por_km)}/km`
                                : item.custo_por_hora !== null
                                  ? `${formatCurrency(item.custo_por_hora)}/h`
                                  : "Sem base de uso"}
                            </div>
                            <div className="mt-2">
                              <Button asChild variant="ghost" size="sm">
                                <Link href={`/dashboard/operacional/frota/${item.equipamento_id}`}>
                                  <Tractor className="size-3.5" />
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
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

function ResumoCard({
  title,
  value,
  description,
  icon: Icon,
  tone = "default",
}: {
  title: string;
  value: string;
  description: string;
  icon: typeof Tractor;
  tone?: "default" | "warning";
}) {
  return (
    <Card className={cn("rounded-sm shadow-sm", tone === "warning" && "border-amber-200")}>
      <CardContent className="flex items-start gap-4 p-5">
        <div
          className={cn(
            "flex size-10 items-center justify-center rounded-sm",
            tone === "default" && "bg-primary/10 text-primary",
            tone === "warning" && "bg-amber-100 text-amber-700"
          )}
        >
          <Icon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</p>
          <div className="mt-0.5 truncate text-2xl font-black tracking-tight">{value}</div>
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function CustosSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-sm" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(320px,1fr)]">
        <Skeleton className="h-[520px] rounded-sm" />
        <Skeleton className="h-[520px] rounded-sm" />
      </div>
    </div>
  );
}

function formatCurrency(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value ?? 0);
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }

  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);
}
