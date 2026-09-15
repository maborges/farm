"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BrainCircuit, DollarSign, ShieldAlert, Tractor, Zap } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
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

type NivelRisco = "BAIXO" | "MEDIO" | "ALTO" | "CRITICO";

interface InteligenciaResumo {
  total_equipamentos: number;
  equipamentos_criticos: number;
  equipamentos_alto_risco: number;
  equipamentos_medio_risco: number;
  equipamentos_baixo_risco: number;
  alertas_consolidados: number;
}

interface InteligenciaFator {
  chave: string;
  titulo: string;
  peso: number;
  pontuacao: number;
  detalhe: string | null;
}

interface InteligenciaEquipamento {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  equipamento_status: string;
  score_risco: number;
  nivel_risco: NivelRisco;
  custo_total: number;
  custo_por_hora: number | null;
  custo_por_km: number | null;
  eficiencia_score: number | null;
  jornada_aberta: boolean;
  horas_trabalhadas_recentes: number | null;
  km_trabalhados_recentes: number | null;
  dias_sem_abastecimento: number | null;
  os_abertas: number;
  os_aberta_antiga: boolean;
  manutencao_status: "OK" | "PROXIMA" | "VENCIDA" | "SEM_PLANO";
  checklist_status: "OK" | "PENDENTE" | "NAO_CONFORME" | "SEM_EXIGENCIA";
  documento_vencido: boolean;
  consumo_alerta: boolean;
  custo_alerta: boolean;
  uso_intensivo_alerta: boolean;
  recomendacoes: string[];
  fatores: InteligenciaFator[];
}

interface InteligenciaRankingItem {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  valor: number | null;
  score_risco: number | null;
  nivel_risco: NivelRisco | null;
  detalhe: string | null;
}

interface InteligenciaResponse {
  resumo: InteligenciaResumo;
  equipamentos: InteligenciaEquipamento[];
  ranking_risco: InteligenciaRankingItem[];
  ranking_mais_caros: InteligenciaRankingItem[];
  ranking_menos_eficientes: InteligenciaRankingItem[];
  recomendacoes_gerais: string[];
}

export default function FrotaInteligenciaPage() {
  const { activeFazendaId } = useAppStore();
  const hasEnterpriseTier = useHasTier("ENTERPRISE");

  const { data, isLoading, isError, error } = useQuery<InteligenciaResponse>({
    queryKey: ["frota", "inteligencia", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/inteligencia", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasEnterpriseTier,
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Inteligência"
        description="Priorização automática da frota com score de risco, sinais operacionais e recomendações acionáveis."
        icon={<BrainCircuit className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Operacional", href: "/operacional" },
          { label: "Frota", href: "/dashboard/operacional/frota" },
          { label: "Inteligência" },
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
                <Zap className="size-3.5" />
                Jornadas
              </Link>
            </Button>
          </>
        }
      />

      {!hasEnterpriseTier ? (
        <TierUpgradeCard
          title="Inteligência operacional disponível no Enterprise"
          description="Score de risco, recomendações automáticas e priorização avançada fazem parte do plano Enterprise."
          requiredTier="ENTERPRISE"
          feature="frota_inteligencia"
          surface="frota_inteligencia_page"
        />
      ) : null}

      {isLoading ? <InteligenciaSkeleton /> : null}

      {hasEnterpriseTier && !isLoading && isError ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<ShieldAlert />}
              title="Não foi possível carregar a inteligência da frota"
              description={error instanceof Error ? error.message : "Erro ao consultar o backend."}
            />
          </CardContent>
        </Card>
      ) : null}

      {hasEnterpriseTier && !isLoading && !isError && data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <ResumoCard title="Críticos" value={data.resumo.equipamentos_criticos} icon={AlertTriangle} tone={data.resumo.equipamentos_criticos > 0 ? "danger" : "default"} />
            <ResumoCard title="Alto risco" value={data.resumo.equipamentos_alto_risco} icon={AlertTriangle} tone={data.resumo.equipamentos_alto_risco > 0 ? "warning" : "default"} />
            <ResumoCard title="Médio risco" value={data.resumo.equipamentos_medio_risco} icon={BrainCircuit} />
            <ResumoCard title="Alertas consolidados" value={data.resumo.alertas_consolidados} icon={ShieldAlert} />
            <ResumoCard title="Total analisado" value={data.resumo.total_equipamentos} icon={Tractor} />
          </div>

          {data.equipamentos.length === 0 ? (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-6">
                <EmptyState
                  icon={<BrainCircuit />}
                  title="Sem base suficiente para inteligência"
                  description="Cadastre equipamentos e registre operação para habilitar a priorização automática."
                />
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(340px,1fr)]">
                <Card className="rounded-sm shadow-sm">
                  <CardHeader>
                    <CardTitle>Ranking de risco</CardTitle>
                    <CardDescription>Top equipamentos priorizados por criticidade operacional.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Equipamento</TableHead>
                          <TableHead>Score</TableHead>
                          <TableHead>Custos</TableHead>
                          <TableHead>Sinais</TableHead>
                          <TableHead>Recomendação</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.equipamentos.map((item) => (
                          <TableRow key={item.equipamento_id}>
                            <TableCell className="align-top">
                              <div className="space-y-1">
                                <div className="font-medium">{item.equipamento_nome}</div>
                                <div className="text-xs text-muted-foreground">{item.equipamento_tipo}</div>
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="space-y-2">
                                <div className="text-xl font-black">{item.score_risco}</div>
                                <Badge variant="outline" className={getRiskClass(item.nivel_risco)}>
                                  {formatNivel(item.nivel_risco)}
                                </Badge>
                              </div>
                            </TableCell>
                            <TableCell className="align-top text-xs">
                              <div>{formatCurrency(item.custo_total)}</div>
                              <div className="text-muted-foreground">
                                {item.custo_por_km !== null
                                  ? `${formatCurrency(item.custo_por_km)}/km`
                                  : item.custo_por_hora !== null
                                    ? `${formatCurrency(item.custo_por_hora)}/h`
                                    : "Sem base de uso"}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="flex flex-wrap gap-1">
                                {item.fatores.slice(0, 3).map((fator) => (
                                  <Badge key={fator.chave} variant="outline" className={getRiskClass(item.nivel_risco)}>
                                    {fator.titulo}
                                  </Badge>
                                ))}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="space-y-1 text-xs">
                                <div className="font-medium">{item.recomendacoes[0] || "Monitorar"}</div>
                                <div className="text-muted-foreground">
                                  <Link href={`/dashboard/operacional/frota/${item.equipamento_id}`} className="underline underline-offset-2">
                                    Abrir detalhe
                                  </Link>
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                <div className="space-y-6">
                  <Card className="rounded-sm shadow-sm">
                    <CardHeader>
                      <CardTitle>Equipamentos críticos</CardTitle>
                      <CardDescription>Foco imediato de atenção da operação.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {data.ranking_risco.length === 0 ? (
                        <p className="text-sm text-muted-foreground">Nenhum equipamento crítico no momento.</p>
                      ) : (
                        data.ranking_risco.map((item, index) => (
                          <div key={item.equipamento_id} className="rounded-sm border p-3">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <div className="text-xs font-medium text-muted-foreground">#{index + 1}</div>
                                <div className="font-medium">{item.equipamento_nome}</div>
                                <div className="text-xs text-muted-foreground">{item.detalhe || item.equipamento_tipo}</div>
                              </div>
                              <div className="text-right">
                                <div className="text-lg font-black">{item.score_risco ?? "—"}</div>
                                {item.nivel_risco ? (
                                  <Badge variant="outline" className={getRiskClass(item.nivel_risco)}>
                                    {formatNivel(item.nivel_risco)}
                                  </Badge>
                                ) : null}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </CardContent>
                  </Card>

                  <Card className="rounded-sm shadow-sm">
                    <CardHeader>
                      <CardTitle>Recomendações automáticas</CardTitle>
                      <CardDescription>Temas que mais se repetem na frota.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {data.recomendacoes_gerais.length === 0 ? (
                        <div className="rounded-sm border border-emerald-200 bg-emerald-50/40 p-4 text-sm text-emerald-700">
                          Nenhuma recomendação prioritária neste momento.
                        </div>
                      ) : (
                        data.recomendacoes_gerais.map((item) => (
                          <div key={item} className="rounded-sm border p-3 text-sm">
                            {item}
                          </div>
                        ))
                      )}
                    </CardContent>
                  </Card>
                </div>
              </div>

              <div className="grid gap-6 xl:grid-cols-2">
                <Card className="rounded-sm shadow-sm">
                  <CardHeader>
                    <CardTitle>Mais caros</CardTitle>
                    <CardDescription>Equipamentos com maior peso financeiro acumulado.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {data.ranking_mais_caros.map((item) => (
                      <div key={item.equipamento_id} className="flex items-start justify-between gap-3 rounded-sm border p-3 text-sm">
                        <div>
                          <div className="font-medium">{item.equipamento_nome}</div>
                          <div className="text-xs text-muted-foreground">{item.equipamento_tipo}</div>
                        </div>
                        <div className="text-right font-semibold">{formatCurrency(item.valor)}</div>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card className="rounded-sm shadow-sm">
                  <CardHeader>
                    <CardTitle>Menos eficientes</CardTitle>
                    <CardDescription>Equipamentos com pior score relativo de eficiência.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {data.ranking_menos_eficientes.map((item) => (
                      <div key={item.equipamento_id} className="flex items-start justify-between gap-3 rounded-sm border p-3 text-sm">
                        <div>
                          <div className="font-medium">{item.equipamento_nome}</div>
                          <div className="text-xs text-muted-foreground">{item.equipamento_tipo}</div>
                        </div>
                        <div className="text-right font-semibold">{formatNumber(item.valor)} pts</div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
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
  tone = "default",
}: {
  title: string;
  value: string | number;
  icon: typeof BrainCircuit;
  tone?: "default" | "warning" | "danger";
}) {
  return (
    <Card className={cn("rounded-sm shadow-sm", tone === "warning" && "border-amber-200", tone === "danger" && "border-red-200")}>
      <CardContent className="flex items-start gap-4 p-5">
        <div
          className={cn(
            "flex size-10 items-center justify-center rounded-sm",
            tone === "default" && "bg-primary/10 text-primary",
            tone === "warning" && "bg-amber-100 text-amber-700",
            tone === "danger" && "bg-red-100 text-red-700"
          )}
        >
          <Icon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</div>
          <div className="mt-0.5 text-2xl font-black tracking-tight">{value}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function InteligenciaSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-sm" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(340px,1fr)]">
        <Skeleton className="h-[520px] rounded-sm" />
        <div className="space-y-6">
          <Skeleton className="h-[250px] rounded-sm" />
          <Skeleton className="h-[250px] rounded-sm" />
        </div>
      </div>
    </div>
  );
}

function formatNivel(value: NivelRisco) {
  switch (value) {
    case "BAIXO":
      return "Baixo";
    case "MEDIO":
      return "Médio";
    case "ALTO":
      return "Alto";
    case "CRITICO":
      return "Crítico";
  }
}

function getRiskClass(value: NivelRisco) {
  switch (value) {
    case "BAIXO":
      return "border-emerald-200 text-emerald-700";
    case "MEDIO":
      return "border-amber-200 text-amber-700";
    case "ALTO":
      return "border-orange-200 text-orange-700";
    case "CRITICO":
      return "border-red-200 text-red-700";
  }
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
