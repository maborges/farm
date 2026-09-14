"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { DollarSign, MapPin, ShieldAlert, Sprout, Tractor } from "lucide-react";

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

interface AgriculturaResumo {
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  custo_hora_estimado: number | null;
  custo_km_estimado: number | null;
  operacao_mais_cara: string | null;
  operacao_mais_cara_custo: number | null;
  talhao_mais_caro: string | null;
  talhao_mais_caro_custo: number | null;
  equipamento_mais_usado: string | null;
  equipamento_mais_usado_valor: number | null;
}

interface AgriculturaSafraItem {
  safra_id: string | null;
  safra_nome: string;
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  custo_hora_estimado: number | null;
  custo_km_estimado: number | null;
  total_jornadas: number;
}

interface AgriculturaTalhaoItem {
  talhao_id: string | null;
  talhao_nome: string;
  safra_id: string | null;
  safra_nome: string | null;
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  custo_hora_estimado: number | null;
  custo_km_estimado: number | null;
  total_jornadas: number;
}

interface AgriculturaOperacaoItem {
  tipo_operacao: string;
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  custo_hora_estimado: number | null;
  custo_km_estimado: number | null;
  total_jornadas: number;
}

interface AgriculturaEquipamentoSafraItem {
  safra_id: string | null;
  safra_nome: string;
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  custo_hora_estimado: number | null;
  custo_km_estimado: number | null;
  total_jornadas: number;
}

interface AgriculturaResumoResponse {
  resumo: AgriculturaResumo;
  por_safra: AgriculturaSafraItem[];
  por_talhao: AgriculturaTalhaoItem[];
  por_operacao: AgriculturaOperacaoItem[];
  equipamentos_por_safra: AgriculturaEquipamentoSafraItem[];
}

export default function FrotaAgriculturaPage() {
  const { activeFazendaId } = useAppStore();
  const hasEnterpriseTier = useHasTier("ENTERPRISE");

  const { data, isLoading, isError, error } = useQuery<AgriculturaResumoResponse>({
    queryKey: ["frota", "agricultura", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/agricultura/resumo", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasEnterpriseTier,
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Uso Agrícola da Frota"
        description="Consolidação das jornadas da frota por safra, talhão, operação e equipamento com custo estimado."
        icon={<Sprout className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Operacional", href: "/operacional" },
          { label: "Frota", href: "/dashboard/operacional/frota" },
          { label: "Uso Agrícola" },
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
              <Link href="/dashboard/operacional/frota/jornadas">
                <Sprout className="size-3.5" />
                Jornadas
              </Link>
            </Button>
          </>
        }
      />

      {!hasEnterpriseTier ? (
        <TierUpgradeCard
          title="Integração Frota x Agricultura disponível no Enterprise"
          description="Custo por safra, talhão e operação com integração agrícola faz parte do tier Enterprise."
          requiredTier="ENTERPRISE"
          feature="frota_agricultura"
          surface="frota_agricultura_page"
        />
      ) : null}

      {isLoading ? <AgriculturaSkeleton /> : null}

      {hasEnterpriseTier && !isLoading && isError ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<ShieldAlert />}
              title="Não foi possível carregar o uso agrícola"
              description={error instanceof Error ? error.message : "Erro ao consultar o backend."}
            />
          </CardContent>
        </Card>
      ) : null}

      {hasEnterpriseTier && !isLoading && !isError && data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <ResumoCard title="Horas totais" value={formatNumber(data.resumo.horas_totais)} icon={Tractor} />
            <ResumoCard title="KM totais" value={formatNumber(data.resumo.km_totais)} icon={MapPin} />
            <ResumoCard
              title="Custo estimado"
              value={data.resumo.custo_estimado_total !== null ? formatCurrency(data.resumo.custo_estimado_total) : "—"}
              icon={DollarSign}
              description={
                data.resumo.custo_hora_estimado !== null || data.resumo.custo_km_estimado !== null
                  ? [data.resumo.custo_hora_estimado !== null ? `${formatCurrency(data.resumo.custo_hora_estimado)}/h` : null, data.resumo.custo_km_estimado !== null ? `${formatCurrency(data.resumo.custo_km_estimado)}/km` : null]
                      .filter(Boolean)
                      .join(" • ")
                  : "Sem base unitária"
              }
            />
            <ResumoCard title="Operação mais cara" value={data.resumo.operacao_mais_cara || "—"} icon={Sprout} description={data.resumo.operacao_mais_cara_custo !== null ? formatCurrency(data.resumo.operacao_mais_cara_custo) : "Sem custo"} />
            <ResumoCard title="Talhão mais caro" value={data.resumo.talhao_mais_caro || "—"} icon={MapPin} description={data.resumo.talhao_mais_caro_custo !== null ? formatCurrency(data.resumo.talhao_mais_caro_custo) : "Sem custo"} />
            <ResumoCard title="Equipamento mais usado" value={data.resumo.equipamento_mais_usado || "—"} icon={Tractor} description={data.resumo.equipamento_mais_usado_valor !== null ? formatNumber(data.resumo.equipamento_mais_usado_valor) : "Sem leitura"} />
          </div>

          {data.por_safra.length === 0 && data.por_talhao.length === 0 && data.por_operacao.length === 0 ? (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-6">
                <EmptyState
                  icon={<Sprout />}
                  title="Sem jornadas agrícolas consolidadas"
                  description="Registre jornadas finalizadas com safra, talhão ou operação para formar a leitura agrícola."
                />
              </CardContent>
            </Card>
          ) : (
            <>
              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Custo por safra</CardTitle>
                  <CardDescription>Horas, km, jornadas e custo estimado agregado por safra.</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                        <TableRow>
                          <TableHead>Safra</TableHead>
                          <TableHead>Horas</TableHead>
                          <TableHead>KM</TableHead>
                          <TableHead>R$/h</TableHead>
                          <TableHead>R$/km</TableHead>
                          <TableHead>Jornadas</TableHead>
                          <TableHead>Custo estimado</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.por_safra.map((item) => (
                        <TableRow key={`${item.safra_id ?? "sem"}-${item.safra_nome}`}>
                          <TableCell className="font-medium">{item.safra_nome}</TableCell>
                          <TableCell>{formatNumber(item.horas_totais)}</TableCell>
                          <TableCell>{formatNumber(item.km_totais)}</TableCell>
                          <TableCell>{item.custo_hora_estimado !== null ? formatCurrency(item.custo_hora_estimado) : "—"}</TableCell>
                          <TableCell>{item.custo_km_estimado !== null ? formatCurrency(item.custo_km_estimado) : "—"}</TableCell>
                          <TableCell>{item.total_jornadas}</TableCell>
                          <TableCell>{item.custo_estimado_total !== null ? formatCurrency(item.custo_estimado_total) : "—"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <div className="grid gap-6 xl:grid-cols-2">
                <Card className="rounded-sm shadow-sm">
                  <CardHeader>
                    <CardTitle>Custo por talhão</CardTitle>
                    <CardDescription>Talhões com maior uso operacional estimado.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Talhão</TableHead>
                          <TableHead>Safra</TableHead>
                          <TableHead>Horas/KM</TableHead>
                          <TableHead>R$/h</TableHead>
                          <TableHead>R$/km</TableHead>
                          <TableHead>Custo</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.por_talhao.map((item) => (
                          <TableRow key={`${item.talhao_id ?? "sem"}-${item.safra_id ?? "sem-safra"}`}>
                            <TableCell className="font-medium">{item.talhao_nome}</TableCell>
                            <TableCell>{item.safra_nome || "—"}</TableCell>
                            <TableCell className="text-xs">
                              <div>{formatNumber(item.horas_totais)} h</div>
                              <div>{formatNumber(item.km_totais)} km</div>
                            </TableCell>
                            <TableCell>{item.custo_hora_estimado !== null ? formatCurrency(item.custo_hora_estimado) : "—"}</TableCell>
                            <TableCell>{item.custo_km_estimado !== null ? formatCurrency(item.custo_km_estimado) : "—"}</TableCell>
                            <TableCell>{item.custo_estimado_total !== null ? formatCurrency(item.custo_estimado_total) : "—"}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                <Card className="rounded-sm shadow-sm">
                  <CardHeader>
                    <CardTitle>Custo por tipo de operação</CardTitle>
                    <CardDescription>Ranking das operações mais caras usando jornadas reais.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Operação</TableHead>
                          <TableHead>Horas/KM</TableHead>
                          <TableHead>R$/h</TableHead>
                          <TableHead>R$/km</TableHead>
                          <TableHead>Jornadas</TableHead>
                          <TableHead>Custo</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.por_operacao.map((item) => (
                          <TableRow key={item.tipo_operacao}>
                            <TableCell className="font-medium">{item.tipo_operacao}</TableCell>
                            <TableCell className="text-xs">
                              <div>{formatNumber(item.horas_totais)} h</div>
                              <div>{formatNumber(item.km_totais)} km</div>
                            </TableCell>
                            <TableCell>{item.custo_hora_estimado !== null ? formatCurrency(item.custo_hora_estimado) : "—"}</TableCell>
                            <TableCell>{item.custo_km_estimado !== null ? formatCurrency(item.custo_km_estimado) : "—"}</TableCell>
                            <TableCell>{item.total_jornadas}</TableCell>
                            <TableCell>{item.custo_estimado_total !== null ? formatCurrency(item.custo_estimado_total) : "—"}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Equipamentos por safra</CardTitle>
                  <CardDescription>Máquinas mais usadas dentro de cada safra.</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                        <TableRow>
                          <TableHead>Safra</TableHead>
                          <TableHead>Equipamento</TableHead>
                          <TableHead>Uso</TableHead>
                          <TableHead>R$/h</TableHead>
                          <TableHead>R$/km</TableHead>
                          <TableHead>Jornadas</TableHead>
                          <TableHead>Custo estimado</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.equipamentos_por_safra.map((item) => (
                        <TableRow key={`${item.safra_id ?? "sem"}-${item.equipamento_id}`}>
                          <TableCell>{item.safra_nome}</TableCell>
                          <TableCell className="font-medium">{item.equipamento_nome}</TableCell>
                          <TableCell className="text-xs">
                            <div>{formatNumber(item.horas_totais)} h</div>
                            <div>{formatNumber(item.km_totais)} km</div>
                          </TableCell>
                          <TableCell>{item.custo_hora_estimado !== null ? formatCurrency(item.custo_hora_estimado) : "—"}</TableCell>
                          <TableCell>{item.custo_km_estimado !== null ? formatCurrency(item.custo_km_estimado) : "—"}</TableCell>
                          <TableCell>{item.total_jornadas}</TableCell>
                          <TableCell>{item.custo_estimado_total !== null ? formatCurrency(item.custo_estimado_total) : "—"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}
        </>
      ) : null}
    </div>
  );
}

function ResumoCard({
  title,
  value,
  icon: Icon,
  description,
}: {
  title: string;
  value: string;
  icon: typeof Sprout;
  description?: string;
}) {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardContent className="flex items-start gap-4 p-5">
        <div className="flex size-10 items-center justify-center rounded-sm bg-primary/10 text-primary">
          <Icon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</div>
          <div className={cn("mt-0.5 text-2xl font-black tracking-tight", value.length > 18 && "text-lg")}>{value}</div>
          {description ? <div className="mt-1 text-xs text-muted-foreground">{description}</div> : null}
        </div>
      </CardContent>
    </Card>
  );
}

function AgriculturaSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-sm" />
        ))}
      </div>
      <Skeleton className="h-[320px] rounded-sm" />
      <div className="grid gap-6 xl:grid-cols-2">
        <Skeleton className="h-[320px] rounded-sm" />
        <Skeleton className="h-[320px] rounded-sm" />
      </div>
      <Skeleton className="h-[360px] rounded-sm" />
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
