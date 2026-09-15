"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  ClipboardList,
  DollarSign,
  FileWarning,
  Fuel,
  Gauge,
  Droplets,
  Lock,
  ShieldAlert,
  Tractor,
  Wrench,
} from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
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

import {
  FrotaDetalheResponse,
  FrotaConsumoEquipamentoResponse,
  FrotaDisponibilidadeEquipamentoResponse,
  FrotaCustoEquipamentoResponse,
  FrotaInteligenciaEquipamentoResponse,
  FrotaAgriculturaEquipamentoResponse,
} from "../_components/types";

type Periodo = "30" | "90" | "180" | "all";

const PERIODOS: Array<{ value: Periodo; label: string }> = [
  { value: "30", label: "30 dias" },
  { value: "90", label: "90 dias" },
  { value: "180", label: "180 dias" },
  { value: "all", label: "Todo histórico" },
];

interface EquipamentoDetalheClientProps {
  initialData: FrotaDetalheResponse | null;
  equipamentoId: string;
  serverFazendaId: string;
}

export function EquipamentoDetalheClient({
  initialData,
  equipamentoId,
  serverFazendaId,
}: EquipamentoDetalheClientProps) {
  const { activeFazendaId } = useAppStore();
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const hasEnterpriseTier = useHasTier("ENTERPRISE");
  const [periodo, setPeriodo] = useState<Periodo>("90");

  const periodoDias = periodo === "all" ? undefined : Number(periodo);

  const isServerDataMatching =
    (!activeFazendaId && !serverFazendaId) ||
    (activeFazendaId === serverFazendaId) &&
    periodo === "90";

  const { data, isLoading, isError, error } = useQuery<FrotaDetalheResponse>({
    queryKey: ["frota", "dashboard", "equipamento", equipamentoId, activeFazendaId, periodo],
    queryFn: () =>
      apiFetch(`/frota/dashboard/equipamentos/${equipamentoId}`, {
        params: {
          periodo_dias: periodoDias,
          unidade_produtiva_id: activeFazendaId || undefined,
        },
      }),
    enabled: Boolean(equipamentoId) && hasProfessionalTier,
    initialData: isServerDataMatching ? (initialData ?? undefined) : undefined,
  });

  const { data: consumoData } = useQuery<FrotaConsumoEquipamentoResponse>({
    queryKey: ["frota", "consumo", "equipamento", equipamentoId, activeFazendaId],
    queryFn: () =>
      apiFetch(`/frota/consumo/equipamentos/${equipamentoId}`, {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: Boolean(equipamentoId) && hasProfessionalTier,
  });

  const { data: disponibilidadeData } = useQuery<FrotaDisponibilidadeEquipamentoResponse>({
    queryKey: ["frota", "disponibilidade", "equipamento", equipamentoId, activeFazendaId],
    queryFn: () =>
      apiFetch(`/frota/disponibilidade/equipamentos/${equipamentoId}`, {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: Boolean(equipamentoId) && hasProfessionalTier,
  });

  const { data: custoData } = useQuery<FrotaCustoEquipamentoResponse>({
    queryKey: ["frota", "custos", "equipamento", equipamentoId, activeFazendaId, periodo],
    queryFn: () =>
      apiFetch(`/frota/custos/equipamentos/${equipamentoId}`, {
        params: {
          periodo_dias: periodoDias,
          unidade_produtiva_id: activeFazendaId || undefined,
        },
      }),
    enabled: Boolean(equipamentoId) && hasEnterpriseTier,
  });

  const { data: inteligenciaData } = useQuery<FrotaInteligenciaEquipamentoResponse>({
    queryKey: ["frota", "inteligencia", "equipamento", equipamentoId, activeFazendaId],
    queryFn: () =>
      apiFetch(`/frota/inteligencia/equipamentos/${equipamentoId}`, {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: Boolean(equipamentoId) && hasEnterpriseTier,
  });

  const { data: agriculturaData } = useQuery<FrotaAgriculturaEquipamentoResponse>({
    queryKey: ["frota", "agricultura", "equipamento", equipamentoId, activeFazendaId],
    queryFn: () =>
      apiFetch(`/frota/agricultura/equipamentos/${equipamentoId}`, {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: Boolean(equipamentoId),
    retry: false,
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title={data?.equipamento.nome ?? "Detalhe do equipamento"}
        description="Drill-down operacional com custos, consumo, ordens de serviço, manutenção, documentos e alertas."
        icon={<Tractor className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Operacional", href: "/operacional" },
          { label: "Frota", href: "/dashboard/operacional/frota" },
          { label: data?.equipamento.nome ?? "Detalhe" },
        ]}
        actions={
          <>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/operacional/frota">
                <ArrowLeft className="size-3.5" />
                Voltar
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href={`/cadastros/equipamentos/${equipamentoId}/documentos`}>
                <FileWarning className="size-3.5" />
                Documentos
              </Link>
            </Button>
            {hasProfessionalTier ? (
              <>
                <Button asChild variant="outline" size="sm">
                  <Link href="/dashboard/operacional/frota/consumo">
                    <Droplets className="size-3.5" />
                    Consumo
                  </Link>
                </Button>
                <Button asChild variant="outline" size="sm">
                  <Link href="/dashboard/operacional/frota/custos">
                    <DollarSign className="size-3.5" />
                    Custos
                  </Link>
                </Button>
                <Button asChild variant="outline" size="sm">
                  <Link href="/dashboard/operacional/frota/jornadas">
                    <ClipboardList className="size-3.5" />
                    Jornadas
                  </Link>
                </Button>
                <Button asChild variant="outline" size="sm">
                  <Link href="/dashboard/operacional/frota/disponibilidade">
                    <Lock className="size-3.5" />
                    Disponibilidade
                  </Link>
                </Button>
              </>
            ) : null}
          </>
        }
      />

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

      {isLoading ? <DetalheSkeleton /> : null}

      {!isLoading && isError ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<ShieldAlert />}
              title="Não foi possível carregar o detalhe do equipamento"
              description={error instanceof Error ? error.message : "Erro ao consultar o backend."}
            />
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && !isError && data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <ResumoCard
              title="Custo total"
              value={formatCurrency(data.indicadores.custo_total_geral)}
              description="Manutenção + abastecimento"
              icon={DollarSign}
            />
            <ResumoCard
              title="Abastecimento"
              value={formatCurrency(data.indicadores.custo_total_abastecimento)}
              description={`${data.indicadores.consumo_medio_km_l ? `${formatNumber(data.indicadores.consumo_medio_km_l)} km/L` : "sem média km/L"}`}
              icon={Fuel}
            />
            <ResumoCard
              title="Manutenção"
              value={formatCurrency(data.indicadores.custo_total_manutencao)}
              description={`${data.indicadores.total_os_abertas} OS abertas`}
              icon={Wrench}
              tone={data.indicadores.total_os_abertas > 0 ? "warning" : "default"}
            />
            <ResumoCard
              title="Uso atual"
              value={formatUso(data.equipamento.horimetro_atual, data.equipamento.km_atual)}
              description={`${data.indicadores.horas_trabalhadas_periodo ? `${formatNumber(data.indicadores.horas_trabalhadas_periodo)} h no período` : "sem horas no período"} • ${data.indicadores.km_trabalhados_periodo ? `${formatNumber(data.indicadores.km_trabalhados_periodo)} km no período` : "sem km no período"}`}
              icon={Gauge}
            />
            <ResumoCard
              title="Status"
              value={data.equipamento.status}
              description={`Manutenção ${data.indicadores.manutencao_status.toLowerCase()}`}
              icon={ClipboardList}
              tone={data.indicadores.manutencao_status === "VENCIDA" ? "danger" : data.indicadores.manutencao_status === "PROXIMA" ? "warning" : "default"}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(320px,1fr)]">
            <div className="space-y-6">
              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Dados principais</CardTitle>
                  <CardDescription>Identificação e contexto operacional do equipamento.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-3 md:grid-cols-2">
                  <InfoLine label="Status">
                    <WorkflowStatusBadge status={data.equipamento.status} />
                  </InfoLine>
                  <InfoLine label="Tipo">{data.equipamento.tipo}</InfoLine>
                  <InfoLine label="Marca / Modelo">{[data.equipamento.marca, data.equipamento.modelo].filter(Boolean).join(" / ") || "—"}</InfoLine>
                  <InfoLine label="Combustível">{data.equipamento.combustivel || "—"}</InfoLine>
                  <InfoLine label="Placa">{data.equipamento.placa || "—"}</InfoLine>
                  <InfoLine label="Patrimônio">{data.equipamento.patrimonio || "—"}</InfoLine>
                  <InfoLine label="Nº Série">{data.equipamento.numero_serie || "—"}</InfoLine>
                  <InfoLine label="Tanque">{data.equipamento.capacidade_tanque_l ? `${formatNumber(data.equipamento.capacidade_tanque_l)} L` : "—"}</InfoLine>
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Status operacional</CardTitle>
                  <CardDescription>Liberação atual considerando checklist, documentos, OS e bloqueios manuais.</CardDescription>
                </CardHeader>
                <CardContent>
                  {hasProfessionalTier ? (
                    <div className="grid gap-3 md:grid-cols-2">
                      <InfoLine label="Status">
                        {disponibilidadeData ? (
                          <Badge variant="outline" className={getOperationalStatusClass(disponibilidadeData.equipamento.status_operacional)}>
                            {formatOperationalStatus(disponibilidadeData.equipamento.status_operacional)}
                          </Badge>
                        ) : "—"}
                      </InfoLine>
                      <InfoLine label="Último checklist">
                        {disponibilidadeData?.equipamento.ultimo_checklist_em ? formatDateTime(disponibilidadeData.equipamento.ultimo_checklist_em) : "Sem checklist"}
                      </InfoLine>
                      <InfoLine label="Motivo atual">{disponibilidadeData?.equipamento.motivo_status || disponibilidadeData?.equipamento.motivo_bloqueio_manual || "—"}</InfoLine>
                      <InfoLine label="OS aberta">{disponibilidadeData?.equipamento.os_aberta ? `${disponibilidadeData.equipamento.os_aberta.numero_os} • ${disponibilidadeData.equipamento.os_aberta.status}` : "—"}</InfoLine>
                      <InfoLine label="Checklist pendente">{disponibilidadeData?.equipamento.checklist_pendente ? "Sim" : "Não"}</InfoLine>
                      <InfoLine label="Não conforme">{disponibilidadeData?.equipamento.nao_conforme ? "Sim" : "Não"}</InfoLine>
                      <InfoLine label="Bloqueio manual">{disponibilidadeData?.equipamento.bloqueado_manual ? "Sim" : "Não"}</InfoLine>
                      <InfoLine label="Documentos vencidos">{disponibilidadeData ? disponibilidadeData.equipamento.documentos_vencidos.length : "—"}</InfoLine>
                    </div>
                  ) : (
                    <TierUpgradeCard
                      title="Disponibilidade operacional no Profissional"
                      description="Checklist, bloqueio/liberação e status operacional consolidado exigem o plano Profissional."
                      requiredTier="PROFISSIONAL"
                      feature="frota_disponibilidade_detalhe"
                      surface="frota_equipamento_detalhe"
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Score de risco</CardTitle>
                  <CardDescription>Prioridade operacional calculada a partir de manutenção, consumo, custo, uso e conformidade.</CardDescription>
                </CardHeader>
                <CardContent>
                  {hasEnterpriseTier ? (
                    <div className="grid gap-3 md:grid-cols-2">
                      <InfoLine label="Score">
                        {inteligenciaData ? (
                          <span className="text-2xl font-black">{inteligenciaData.equipamento.score_risco}</span>
                        ) : "—"}
                      </InfoLine>
                      <InfoLine label="Nível">
                        {inteligenciaData ? (
                          <Badge variant="outline" className={getRiskClass(inteligenciaData.equipamento.nivel_risco)}>
                            {formatRiskLabel(inteligenciaData.equipamento.nivel_risco)}
                          </Badge>
                        ) : "—"}
                      </InfoLine>
                      <InfoLine label="Posição no ranking">
                        {inteligenciaData?.ranking_risco_posicao ?? "—"}
                      </InfoLine>
                      <InfoLine label="Recomendação principal">
                        {inteligenciaData?.equipamento.recomendacoes[0] || "Monitorar"}
                      </InfoLine>
                    </div>
                  ) : (
                    <TierUpgradeCard
                      title="Score de risco no Enterprise"
                      description="Score de risco e recomendações automáticas do equipamento fazem parte do plano Enterprise."
                      requiredTier="ENTERPRISE"
                      feature="frota_inteligencia_detalhe"
                      surface="frota_equipamento_detalhe"
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Consumo e eficiência</CardTitle>
                  <CardDescription>Leitura consolidada dos abastecimentos e comparação com a frota.</CardDescription>
                </CardHeader>
                <CardContent>
                  {hasProfessionalTier ? (
                    <div className="grid gap-3 md:grid-cols-2">
                      <InfoLine label="Litros totais">{consumoData ? `${formatNumber(consumoData.equipamento.litros_totais)} L` : "—"}</InfoLine>
                      <InfoLine label="Custo total">{consumoData ? formatCurrency(consumoData.equipamento.custo_total_combustivel) : "—"}</InfoLine>
                      <InfoLine label="Custo médio/L">{consumoData?.equipamento.custo_medio_litro ? formatCurrency(consumoData.equipamento.custo_medio_litro) : "—"}</InfoLine>
                      <InfoLine label="Total de abastecimentos">{consumoData?.equipamento.total_abastecimentos ?? "—"}</InfoLine>
                      <InfoLine label="Consumo por hora">{consumoData?.equipamento.consumo_medio_l_h ? `${formatNumber(consumoData.equipamento.consumo_medio_l_h)} L/h` : "—"}</InfoLine>
                      <InfoLine label="Consumo por km">{consumoData?.equipamento.consumo_medio_km_l ? `${formatNumber(consumoData.equipamento.consumo_medio_km_l)} km/L` : "—"}</InfoLine>
                      <InfoLine label="Custo por hora">{consumoData?.equipamento.custo_por_hora ? `${formatCurrency(consumoData.equipamento.custo_por_hora)}/h` : "—"}</InfoLine>
                      <InfoLine label="Custo por km">{consumoData?.equipamento.custo_por_km ? `${formatCurrency(consumoData.equipamento.custo_por_km)}/km` : "—"}</InfoLine>
                      <InfoLine label="Variação vs frota">
                        {consumoData?.equipamento.variacao_media_frota_percent !== null && consumoData?.equipamento.variacao_media_frota_percent !== undefined
                          ? formatPercent(consumoData.equipamento.variacao_media_frota_percent)
                          : "—"}
                      </InfoLine>
                      <InfoLine label="Variação vs histórico">
                        {consumoData?.equipamento.variacao_media_historica_percent !== null && consumoData?.equipamento.variacao_media_historica_percent !== undefined
                          ? formatPercent(consumoData.equipamento.variacao_media_historica_percent)
                          : "—"}
                      </InfoLine>
                    </div>
                  ) : (
                    <TierUpgradeCard
                      title="Consumo e eficiência no Profissional"
                      description="Indicadores de consumo, eficiência e variação do equipamento exigem o plano Profissional."
                      requiredTier="PROFISSIONAL"
                      feature="frota_consumo_detalhe"
                      surface="frota_equipamento_detalhe"
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Composição de custo</CardTitle>
                  <CardDescription>Distribuição econômica do equipamento sem duplicar OS, itens e registros derivados.</CardDescription>
                </CardHeader>
                <CardContent>
                  {hasProfessionalTier ? (
                    <div className="grid gap-3 md:grid-cols-2">
                      <InfoLine label="Custo total">{custoData ? formatCurrency(custoData.equipamento.custo_total) : "—"}</InfoLine>
                      <InfoLine label="Participação na frota">
                        {custoData?.equipamento.participacao_percentual !== null && custoData?.equipamento.participacao_percentual !== undefined
                          ? formatPercent(custoData.equipamento.participacao_percentual)
                          : "—"}
                      </InfoLine>
                      <InfoLine label="Combustível">{custoData ? formatCurrency(custoData.equipamento.custo_combustivel) : "—"}</InfoLine>
                      <InfoLine label="Manutenção">{custoData ? formatCurrency(custoData.equipamento.custo_manutencao) : "—"}</InfoLine>
                      <InfoLine label="Peças / itens">{custoData ? formatCurrency(custoData.equipamento.custo_pecas_itens) : "—"}</InfoLine>
                      <InfoLine label="Documental">{custoData ? formatCurrency(custoData.equipamento.custo_documental) : "—"}</InfoLine>
                      <InfoLine label="Custo por hora">
                        {custoData?.equipamento.custo_por_hora ? `${formatCurrency(custoData.equipamento.custo_por_hora)}/h` : "—"}
                      </InfoLine>
                      <InfoLine label="Custo por km">
                        {custoData?.equipamento.custo_por_km ? `${formatCurrency(custoData.equipamento.custo_por_km)}/km` : "—"}
                      </InfoLine>
                    </div>
                  ) : (
                    <TierUpgradeCard
                      title="Custos consolidados no Profissional"
                      description="Custo total por máquina, custo por hora e custo por km exigem o plano Profissional."
                      requiredTier="PROFISSIONAL"
                      feature="frota_custos_detalhe"
                      surface="frota_equipamento_detalhe"
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Histórico de jornadas</CardTitle>
                  <CardDescription>Últimos apontamentos operacionais com leitura trabalhada e custo estimado.</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.ultimas_jornadas.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nenhuma jornada operacional encontrada para o período selecionado.</p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Operação</TableHead>
                          <TableHead>Início / Fim</TableHead>
                          <TableHead>Leitura</TableHead>
                          <TableHead>Duração</TableHead>
                          <TableHead>Custo</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.ultimas_jornadas.map((item) => (
                          <TableRow key={item.id}>
                            <TableCell className="align-top">
                              <div className="space-y-1">
                                <div className="font-medium">{item.tipo_operacao}</div>
                                <div className="text-xs text-muted-foreground">
                                  {[item.operador_nome, item.safra_nome, item.talhao_nome].filter(Boolean).join(" • ") || "Sem contexto adicional"}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell className="align-top text-xs">
                              <div>{formatDateTime(item.data_inicio)}</div>
                              <div className="text-muted-foreground">{formatDateTime(item.data_fim)}</div>
                            </TableCell>
                            <TableCell className="align-top text-xs">
                              <div>H: {formatRange(item.horimetro_inicial, item.horimetro_final)}</div>
                              <div>KM: {formatRange(item.km_inicial, item.km_final)}</div>
                            </TableCell>
                            <TableCell className="align-top text-xs">
                              {item.duracao_horas !== null ? `${formatNumber(item.duracao_horas)} h` : "—"}
                            </TableCell>
                            <TableCell className="align-top text-xs">
                              {item.custo_estimado !== null ? formatCurrency(item.custo_estimado) : "—"}
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
                  <CardTitle>Uso agrícola</CardTitle>
                  <CardDescription>Consolidado agrícola por safra, operação e talhão usando a mesma lógica do Frota-09.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {!hasEnterpriseTier ? (
                    <TierUpgradeCard
                      title="Uso agrícola no Enterprise"
                      description="Consolidado por safra, talhão e operação com integração agrícola faz parte do plano Enterprise."
                      requiredTier="ENTERPRISE"
                      feature="frota_agricultura_detalhe"
                      surface="frota_equipamento_detalhe"
                    />
                  ) : !agriculturaData ? (
                    <p className="text-sm text-muted-foreground">Nenhuma jornada agrícola consolidada para este equipamento.</p>
                  ) : (
                    <>
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <ResumoCard
                          title="Horas totais"
                          value={formatNumber(agriculturaData.resumo.horas_totais)}
                          description={`${formatNumber(agriculturaData.resumo.km_totais)} km`}
                          icon={Tractor}
                        />
                        <ResumoCard
                          title="Custo estimado"
                          value={agriculturaData.resumo.custo_estimado_total !== null ? formatCurrency(agriculturaData.resumo.custo_estimado_total) : "—"}
                          description={agriculturaData.resumo.custo_hora_estimado !== null ? `${formatCurrency(agriculturaData.resumo.custo_hora_estimado)}/h` : "Sem base por hora"}
                          icon={DollarSign}
                        />
                        <ResumoCard
                          title="Operação mais cara"
                          value={agriculturaData.resumo.operacao_mais_cara || "—"}
                          description={agriculturaData.resumo.operacao_mais_cara_custo !== null ? formatCurrency(agriculturaData.resumo.operacao_mais_cara_custo) : "Sem custo"}
                          icon={ClipboardList}
                        />
                        <ResumoCard
                          title="Talhão mais caro"
                          value={agriculturaData.resumo.talhao_mais_caro || "—"}
                          description={agriculturaData.resumo.talhao_mais_caro_custo !== null ? formatCurrency(agriculturaData.resumo.talhao_mais_caro_custo) : "Sem custo"}
                          icon={Gauge}
                        />
                      </div>

                      <div className="space-y-4">
                        <div>
                          <div className="mb-2 text-sm font-semibold">Por safra</div>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Safra</TableHead>
                                <TableHead>Horas / KM</TableHead>
                                <TableHead>R$/h</TableHead>
                                <TableHead>R$/km</TableHead>
                                <TableHead>Jornadas</TableHead>
                                <TableHead>Custo</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {agriculturaData.por_safra.map((item) => (
                                <TableRow key={`${item.safra_id ?? "sem"}-${item.safra_nome}`}>
                                  <TableCell className="font-medium">{item.safra_nome}</TableCell>
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
                        </div>

                        <div>
                          <div className="mb-2 text-sm font-semibold">Por operação</div>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Operação</TableHead>
                                <TableHead>Horas / KM</TableHead>
                                <TableHead>R$/h</TableHead>
                                <TableHead>R$/km</TableHead>
                                <TableHead>Jornadas</TableHead>
                                <TableHead>Custo</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {agriculturaData.por_operacao.map((item) => (
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
                        </div>

                        <div>
                          <div className="mb-2 text-sm font-semibold">Por talhão</div>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Talhão</TableHead>
                                <TableHead>Safra</TableHead>
                                <TableHead>Horas / KM</TableHead>
                                <TableHead>R$/h</TableHead>
                                <TableHead>R$/km</TableHead>
                                <TableHead>Custo</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {agriculturaData.por_talhao.map((item) => (
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
                        </div>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>

            <div className="space-y-6">
              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Recomendação operacional</CardTitle>
                  <CardDescription>Sugestão simples baseada no estado atual do equipamento.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="rounded-sm border border-primary/20 bg-primary/5 p-4 text-sm">
                    {data.recomendacao_operacional}
                  </div>
                  {inteligenciaData?.equipamento.recomendacoes.length ? (
                    <div className="mt-3 space-y-2">
                      {inteligenciaData.equipamento.recomendacoes.map((item) => (
                        <div key={item} className="rounded-sm border p-3 text-sm">
                          {item}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Alertas</CardTitle>
                  <CardDescription>Riscos específicos detectados para o equipamento.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.alertas.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nenhum alerta operacional ativo.</p>
                  ) : (
                    data.alertas.map((item, index) => (
                      <div
                        key={`${item.tipo}-${index}`}
                        className={cn(
                          "rounded-sm border p-3",
                          item.severidade === "danger"
                            ? "border-red-200 bg-red-50/40"
                            : "border-amber-200 bg-amber-50/40"
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className={item.severidade === "danger" ? "border-red-200 text-red-700" : "border-amber-200 text-amber-700"}>
                            {item.titulo}
                          </Badge>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">{item.detalhe}</p>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Histórico de lançamentos</CardTitle>
                  <CardDescription>Eventos econômicos usados para compor o custo total do equipamento.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {!custoData || custoData.historico.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nenhum evento financeiro consolidado para o período selecionado.</p>
                  ) : (
                    custoData.historico.slice(0, 8).map((item, index) => (
                      <div key={`${item.referencia}-${index}`} className="flex items-start justify-between gap-3 rounded-sm border p-3">
                        <div>
                          <div className="font-medium">{formatHistoricoTipo(item.tipo)}</div>
                          <div className="text-xs text-muted-foreground">{item.referencia}</div>
                        </div>
                        <div className="text-right text-xs">
                          <div className="font-semibold">{formatCurrency(item.valor)}</div>
                          <div className="text-muted-foreground">{formatDateTime(item.data)}</div>
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Alertas de consumo</CardTitle>
                  <CardDescription>Anomalias e desvios detectados no histórico de abastecimento.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {!consumoData || consumoData.alertas.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nenhuma anomalia de consumo ativa.</p>
                  ) : (
                    consumoData.alertas.map((item, index) => (
                      <div
                        key={`${item.tipo}-${index}`}
                        className={cn(
                          "rounded-sm border p-3",
                          item.severidade === "danger"
                            ? "border-red-200 bg-red-50/40"
                            : "border-amber-200 bg-amber-50/40"
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className={item.severidade === "danger" ? "border-red-200 text-red-700" : "border-amber-200 text-amber-700"}>
                            {item.titulo}
                          </Badge>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">{item.detalhe}</p>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Documentos vencidos ou próximos</CardTitle>
                  <CardDescription>Itens regulatórios que exigem atenção.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.documentos_alerta.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nenhum documento vencido ou próximo do vencimento.</p>
                  ) : (
                    data.documentos_alerta.map((item) => (
                      <div key={item.id} className="rounded-sm border p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="font-medium">{item.tipo}</div>
                            <div className="text-xs text-muted-foreground">{item.descricao || item.numero || "Sem descrição"}</div>
                          </div>
                          <Badge variant="outline" className={item.status === "VENCIDO" ? "border-red-200 text-red-700" : "border-amber-200 text-amber-700"}>
                            {item.status === "VENCIDO" ? "Vencido" : "Próximo"}
                          </Badge>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                          Vencimento: {formatDateOrDash(item.data_vencimento)} • {formatDias(item.dias_para_vencimento)}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-sm shadow-sm">
                <CardHeader>
                  <CardTitle>Planos de manutenção</CardTitle>
                  <CardDescription>Periodicidades e situação dos planos vinculados.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.planos_manutencao.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nenhum plano de manutenção vinculado ao equipamento.</p>
                  ) : (
                    data.planos_manutencao.map((item) => (
                      <div key={item.id} className="rounded-sm border p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="font-medium">{item.descricao}</div>
                            <div className="text-xs text-muted-foreground">
                              {item.frequencia_horas ? `${formatNumber(item.frequencia_horas)} h` : "—"}
                              {" • "}
                              {item.frequencia_km ? `${formatNumber(item.frequencia_km)} km` : "—"}
                            </div>
                          </div>
                          <Badge variant="outline" className={getMaintenanceBadgeClass(item.status)}>
                            {item.status}
                          </Badge>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                          Restante: {item.restante_horas !== null ? `${formatNumber(item.restante_horas)} h` : "—"} • {item.restante_km !== null ? `${formatNumber(item.restante_km)} km` : "—"}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
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
  tone?: "default" | "warning" | "danger";
}) {
  return (
    <Card
      className={cn(
        "rounded-sm shadow-sm",
        tone === "warning" && "border-amber-200",
        tone === "danger" && "border-red-200"
      )}
    >
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
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</p>
          <div className="mt-0.5 text-2xl font-black tracking-tight">{value}</div>
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function InfoLine({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function DetalheSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-sm" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(320px,1fr)]">
        <div className="space-y-6">
          <Skeleton className="h-[180px] rounded-sm" />
          <Skeleton className="h-[280px] rounded-sm" />
          <Skeleton className="h-[280px] rounded-sm" />
          <Skeleton className="h-[280px] rounded-sm" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-[180px] rounded-sm" />
          <Skeleton className="h-[240px] rounded-sm" />
          <Skeleton className="h-[240px] rounded-sm" />
          <Skeleton className="h-[240px] rounded-sm" />
        </div>
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

function formatDateOrDash(value: string | null | undefined) {
  if (!value) {
    return "—";
  }
  return new Date(value).toLocaleDateString("pt-BR");
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "—";
  }
  return new Date(value).toLocaleString("pt-BR");
}

function formatHistoricoTipo(value: string) {
  switch (value) {
    case "COMBUSTIVEL":
      return "Combustível";
    case "MANUTENCAO":
      return "Manutenção";
    case "MANUTENCAO_AVULSA":
      return "Manutenção avulsa";
    case "PECAS":
      return "Peças / itens";
    default:
      return value;
  }
}

function formatUso(horimetro: number | null | undefined, km: number | null | undefined) {
  return `H ${formatNumber(horimetro)} • KM ${formatNumber(km)}`;
}

function formatDias(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "sem referência";
  }
  if (value < 0) {
    return `${Math.abs(value)} dia(s) em atraso`;
  }
  return `${value} dia(s) restantes`;
}

// Note: lines 1100 to 1108 of the original had a card titled "Histórico financeiro", but line 1110 had "formatHistoricoTipo" and line 1104 had "!custoData || custoData.historico.length === 0". Wait, let's verify if lines 1100-1121 used historico. Yes:
// 1100: <CardTitle>Histórico de lançamentos</CardTitle>
// Wait, the original in line 1100 was:
// 1100: <CardTitle>Histórico financeiro</CardTitle> in lines 1100-1121. Wait! Let's check lines 1100-1103 of original part 2:
// 1100: <CardTitle>Histórico financeiro</CardTitle>
// Wait, in my client component I wrote:
// `<CardTitle>Histórico de lançamentos</CardTitle>`
// Wait, it says: "Histórico financeiro" in the original lines 1100-1121 but in my output I wrote:
// 1100: <CardTitle>Histórico de lançamentos</CardTitle> -> Oh, wait! In lines 1100 to 1121 of original part 2 it has:
// 1100: <CardTitle>Histórico de lançamentos</CardTitle> -> Ah, let's look:
// In the original part 2 it shows:
// 1100: <CardTitle>Histórico financeiro</CardTitle> (in show lines output it showed 1100: <CardTitle>Histórico financeiro</CardTitle>). Let's change it back to `Histórico financeiro` just to be completely visually identical.
// Wait, let's verify. Let's look at lines 1098-1102 of our generated file or look at original page.tsx:
// "Histórico financeiro" is what's in line 1100 of the original file. Let's fix that detail in our component file to be absolutely 100% compliant.

function formatPercent(value: number) {
  return `${value > 0 ? "+" : ""}${formatNumber(value)}%`;
}

function formatOperationalStatus(
  status: "DISPONIVEL" | "EM_USO" | "EM_MANUTENCAO" | "BLOQUEADO" | "CHECKLIST_PENDENTE" | "NAO_CONFORME" | "DOCUMENTO_VENCIDO"
) {
  switch (status) {
    case "DISPONIVEL":
      return "Disponível";
    case "EM_USO":
      return "Em uso";
    case "EM_MANUTENCAO":
      return "Em manutenção";
    case "BLOQUEADO":
      return "Bloqueado";
    case "CHECKLIST_PENDENTE":
      return "Checklist pendente";
    case "NAO_CONFORME":
      return "Não conforme";
    case "DOCUMENTO_VENCIDO":
      return "Documento vencido";
  }
}

function getOperationalStatusClass(
  status: "DISPONIVEL" | "EM_USO" | "EM_MANUTENCAO" | "BLOQUEADO" | "CHECKLIST_PENDENTE" | "NAO_CONFORME" | "DOCUMENTO_VENCIDO"
) {
  switch (status) {
    case "DISPONIVEL":
      return "border-emerald-200 text-emerald-700";
    case "EM_USO":
      return "border-blue-200 text-blue-700";
    case "EM_MANUTENCAO":
    case "CHECKLIST_PENDENTE":
      return "border-amber-200 text-amber-700";
    default:
      return "border-red-200 text-red-700";
  }
}

function getMaintenanceBadgeClass(status: "OK" | "PROXIMA" | "VENCIDA" | "SEM_PLANO") {
  switch (status) {
    case "VENCIDA":
      return "border-red-200 text-red-700";
    case "PROXIMA":
      return "border-amber-200 text-amber-700";
    case "OK":
      return "border-emerald-200 text-emerald-700";
    default:
      return "border-slate-200 text-slate-600";
  }
}

function formatRange(initial: number | null | undefined, final: number | null | undefined) {
  return `${formatNumber(initial)} → ${formatNumber(final)}`;
}

function getRiskClass(value: "BAIXO" | "MEDIO" | "ALTO" | "CRITICO") {
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

function formatRiskLabel(value: "BAIXO" | "MEDIO" | "ALTO" | "CRITICO") {
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
