"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  BarChart3,
  CalendarRange,
  CheckCircle2,
  ListChecks,
  MessageSquare,
  Target,
  TriangleAlert,
  History,
} from "lucide-react";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { getSafraLabel } from "@/lib/safra-label";
import { useHasTier } from "@/hooks/use-has-tier";
import { PageHeader } from "@/components/shared/page-header";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { EmptyState } from "@/components/shared/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface SafraResumo {
  id: string;
  cultura: string | null;
  ano_safra: string;
  nome?: string | null;
}

interface ProductionUnitResumo {
  id: string;
  cultivo_nome?: string | null;
  area_nome?: string | null;
}

interface PrioridadeWarning {
  codigo: string;
  titulo: string;
  severidade: string;
  mensagem: string;
  origem: string;
}

interface PrioridadeHistoricoItem {
  id: string;
  prioridade_id: string;
  evento_tipo: "STATUS" | "COMENTARIO";
  status_anterior?: PrioridadeItem["status"] | null;
  status_novo?: PrioridadeItem["status"] | null;
  observacao?: string | null;
  comentario?: string | null;
  responsavel_id?: string | null;
  responsavel_nome?: string | null;
  alterado_em: string;
}

interface PrioridadeStatusResponse {
  prioridade_id: string;
  prioridade_status_id: string;
  status_atual: PrioridadeItem["status"];
  historico: PrioridadeHistoricoItem[];
  sujeito_reconciliacao: boolean;
}

interface PrioridadeItem {
  scope: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  id: string;
  label: string;
  tipo:
    | "MARGEM_ABAIXO_MEDIA_TENANT"
    | "CUSTO_HECTARE_ACIMA_MEDIA"
    | "PRODUCTION_UNIT_BAIXA_EFICIENCIA"
    | "EQUIPAMENTO_CUSTO_ELEVADO"
    | "JORNADA_BAIXA_PRODUTIVIDADE"
    | "RESULTADO_OPERACIONAL_NEGATIVO"
    | "RESULTADO_SAFRA_ABAIXO_BENCHMARK"
    | "RECORRENCIA_WARNING_ECONOMICO"
    | "RECORRENCIA_INCONSISTENCIA_OPERACIONAL";
  severidade: "INFO" | "ATENCAO" | "RISCO_OPERACIONAL" | "RISCO_ECONOMICO" | "PRIORIDADE_CRITICA";
  score_prioridade: number;
  origem: "DIAGNOSTICO" | "RECOMENDACAO" | "BENCHMARK" | "WARNING";
  origem_codigo: string;
  origem_titulo: string;
  impacto_estimado?: number | null;
  contexto_operacional: string;
  contexto_economico: string;
  acao_sugerida: string;
  entidade_tipo: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  entidade_id: string;
  entidade_label: string;
  status: "NOVA" | "VISUALIZADA" | "EM_ANALISE" | "RESOLVIDA" | "IGNORADA";
  warnings_relevantes: string[];
  recorrencia: number;
  fontes_relacionadas: string[];
  posicao?: number | null;
}

interface PrioridadeResumo {
  total: number;
  nova: number;
  visualizada: number;
  em_analise: number;
  resolvida: number;
  ignorada: number;
  info: number;
  atencao: number;
  risco_operacional: number;
  risco_economico: number;
  prioridade_critica: number;
  por_origem: Record<string, number>;
  por_tipo: Record<string, number>;
}

interface PrioridadeResponse {
  tenant_id: string;
  gerado_em: string;
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  prioridades: PrioridadeItem[];
  resumo: PrioridadeResumo;
  warnings: PrioridadeWarning[];
  sujeito_reconciliacao: boolean;
  observacao_reconciliacao: string | null;
}

const statusTone = {
  NOVA: { label: "Nova", variant: "priority" as const },
  VISUALIZADA: { label: "Visualizada", variant: "secondary" as const },
  EM_ANALISE: { label: "Em análise", variant: "diagnostic" as const },
  RESOLVIDA: { label: "Resolvida", variant: "success" as const },
  IGNORADA: { label: "Ignorada", variant: "warning" as const },
} as const;

const severityTone = {
  INFO: { label: "Info", variant: "info" as const },
  ATENCAO: { label: "Atenção", variant: "warning" as const },
  RISCO_OPERACIONAL: { label: "Risco operacional", variant: "attention" as const },
  RISCO_ECONOMICO: { label: "Risco econômico", variant: "danger" as const },
  PRIORIDADE_CRITICA: { label: "Prioridade crítica", variant: "critical" as const },
} as const;

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(value));
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatMoney(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

function groupByOrigin(items: PrioridadeItem[]) {
  return items.reduce<Record<string, PrioridadeItem[]>>((acc, item) => {
    (acc[item.origem] ||= []).push(item);
    return acc;
  }, {});
}

export default function PrioridadesOperacionaisEconomicasAgricolaPage() {
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const queryClient = useQueryClient();
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const unidadesProdutivas = useAppStore((state) => state.unidadesProdutivasAutorizadas);

  const [selectedSafraId, setSelectedSafraId] = useState<string>("");
  const [selectedProductionUnitId, setSelectedProductionUnitId] = useState<string>("TODAS");
  const [selectedUnidadeProdutivaId, setSelectedUnidadeProdutivaId] = useState<string>("");
  const [dataInicio, setDataInicio] = useState<string>("");
  const [dataFim, setDataFim] = useState<string>("");
  const [observacoes, setObservacoes] = useState<Record<string, string>>({});
  const [comentarios, setComentarios] = useState<Record<string, string>>({});
  const [selectedPrioridadeId, setSelectedPrioridadeId] = useState<string>("");

  const effectiveUnidadeProdutivaId = selectedUnidadeProdutivaId || activeFazendaId || "";
  const safraScopeId = effectiveUnidadeProdutivaId || undefined;

  const { data: safras = [], isLoading: isLoadingSafras } = useQuery<SafraResumo[]>({
    queryKey: ["agricola-prioridades", "safras", safraScopeId],
    queryFn: () => apiFetch(`/safras${safraScopeId ? `?unidade_produtiva_id=${safraScopeId}` : ""}`),
    enabled: hasProfessionalTier,
  });

  const effectiveSafraId = selectedSafraId || safras[0]?.id || "";

  const { data: productionUnits = [], isLoading: isLoadingProductionUnits } = useQuery<ProductionUnitResumo[]>({
    queryKey: ["agricola-prioridades", "production-units", effectiveSafraId],
    queryFn: () => apiFetch(`/safras/${effectiveSafraId}/production-units`),
    enabled: hasProfessionalTier && !!effectiveSafraId,
  });

  const prioridadeParams = useMemo(() => {
    if (!effectiveSafraId) return null;
    return {
      safra_id: effectiveSafraId,
      production_unit_id: selectedProductionUnitId !== "TODAS" ? selectedProductionUnitId : undefined,
      unidade_produtiva_id: effectiveUnidadeProdutivaId || undefined,
      data_inicio: dataInicio || undefined,
      data_fim: dataFim || undefined,
    };
  }, [dataFim, dataInicio, effectiveSafraId, effectiveUnidadeProdutivaId, selectedProductionUnitId]);

  const {
    data: prioridades,
    isLoading: isLoadingPrioridades,
    isError: isErrorPrioridades,
    error: prioridadesError,
    refetch: refetchPrioridades,
  } = useQuery<PrioridadeResponse>({
    queryKey: ["agricola-prioridades", "v1", prioridadeParams],
    queryFn: () => apiFetch("/agricola/prioridades/v1", { params: prioridadeParams ?? undefined }),
    enabled: hasProfessionalTier && !!prioridadeParams,
  });

  const groups = useMemo(() => groupByOrigin(prioridades?.prioridades ?? []), [prioridades?.prioridades]);
  const activePrioridadeId = useMemo(() => {
    if (selectedPrioridadeId && prioridades?.prioridades.some((item) => item.id === selectedPrioridadeId)) {
      return selectedPrioridadeId;
    }
    return prioridades?.prioridades[0]?.id ?? "";
  }, [prioridades?.prioridades, selectedPrioridadeId]);

  const selectedPrioridade = useMemo(
    () => prioridades?.prioridades.find((item) => item.id === activePrioridadeId) ?? null,
    [activePrioridadeId, prioridades?.prioridades],
  );
  const periodLabel =
    prioridades?.data_inicio || prioridades?.data_fim
      ? `${formatDate(prioridades?.data_inicio)} → ${formatDate(prioridades?.data_fim)}`
      : "Sem recorte temporal";

  const historicoQuery = useQuery<PrioridadeStatusResponse>({
    queryKey: ["agricola-prioridades", "historico", selectedPrioridade?.id, prioridadeParams],
    queryFn: () => {
      if (!prioridadeParams || !selectedPrioridade) {
        throw new Error("Seleção de prioridade indisponível.");
      }
      return apiFetch(`/agricola/prioridades/v1/${encodeURIComponent(selectedPrioridade.id)}/historico`, {
        params: prioridadeParams,
      });
    },
    enabled: hasProfessionalTier && !!prioridadeParams && !!selectedPrioridade,
  });

  const statusMutation = useMutation({
    mutationFn: async ({
      prioridadeId,
      status,
      observacao,
    }: {
      prioridadeId: string;
      status: PrioridadeItem["status"];
      observacao?: string;
    }) => {
      if (!prioridadeParams) {
        throw new Error("Filtro da prioridade indisponível.");
      }
      return apiFetch(`/agricola/prioridades/v1/${encodeURIComponent(prioridadeId)}/status`, {
        method: "PATCH",
        params: prioridadeParams,
        body: {
          status,
          observacao: observacao?.trim() || undefined,
        },
      });
    },
    onSuccess: async (_, variables) => {
      await queryClient.invalidateQueries({ queryKey: ["agricola-prioridades", "v1", prioridadeParams] });
      await queryClient.invalidateQueries({ queryKey: ["agricola-prioridades", "historico", variables.prioridadeId, prioridadeParams] });
      await refetchPrioridades();
      toast.success("Status da prioridade atualizado", {
        description: `Prioridade marcada como ${variables.status.toLowerCase().replaceAll("_", " ")}.`,
      });
    },
    onError: (error: Error) => {
      toast.error("Não foi possível atualizar o status", {
        description: error.message,
      });
    },
  });

  const comentarioMutation = useMutation({
    mutationFn: async ({ prioridadeId, comentario }: { prioridadeId: string; comentario: string }) => {
      if (!prioridadeParams) {
        throw new Error("Filtro da prioridade indisponível.");
      }
      return apiFetch(`/agricola/prioridades/v1/${encodeURIComponent(prioridadeId)}/comentarios`, {
        method: "POST",
        params: prioridadeParams,
        body: {
          comentario,
        },
      });
    },
    onSuccess: async (_, variables) => {
      await queryClient.invalidateQueries({ queryKey: ["agricola-prioridades", "v1", prioridadeParams] });
      await queryClient.invalidateQueries({ queryKey: ["agricola-prioridades", "historico", variables.prioridadeId, prioridadeParams] });
      await refetchPrioridades();
      toast.success("Comentário registrado", {
        description: "A prioridade foi atualizada com um comentário interno.",
      });
      setComentarios((current) => ({ ...current, [variables.prioridadeId]: "" }));
    },
    onError: (error: Error) => {
      toast.error("Não foi possível salvar o comentário", {
        description: error.message,
      });
    },
  });

  const atualizarStatus = (prioridadeId: string, status: PrioridadeItem["status"]) => {
    statusMutation.mutate({
      prioridadeId,
      status,
      observacao: observacoes[prioridadeId],
    });
  };

  const adicionarComentario = (prioridadeId: string) => {
    const comentario = comentarios[prioridadeId]?.trim();
    if (!comentario) {
      toast.error("Digite um comentário curto antes de salvar.");
      return;
    }
    comentarioMutation.mutate({ prioridadeId, comentario });
  };

  if (!hasProfessionalTier) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <PageHeader
          title="Central Inteligente de Prioridades Agrícolas"
          description="Fila consolidada de prioridades operacionais e econômicas derivada da DRE agrícola v1."
          breadcrumbs={[
            { label: "Agrícola", href: "/dashboard/agricola" },
            { label: "Central Inteligente de Prioridades Agrícolas" },
          ]}
          icon={<Target className="size-5" />}
        />
        <TierUpgradeCard
          title="Central de prioridades disponível no PROFISSIONAL"
          description="A central consolida diagnóstico, recomendações, benchmark e warnings oficiais."
          requiredTier="PROFISSIONAL"
          feature="agricola.prioridades_v1"
          surface="agricola.prioridades.page"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Central Inteligente de Prioridades Agrícolas"
        description="Fila consolidada e ordenada por prioridade, sem engine paralela nem recálculo fora da DRE agrícola v1."
        breadcrumbs={[
          { label: "Agrícola", href: "/dashboard/agricola" },
          { label: "DRE Agrícola v1", href: "/dashboard/agricola/dre" },
          { label: "Central Inteligente de Prioridades Agrícolas" },
        ]}
        actions={(
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" size="sm" className="rounded-sm">
              <Link href="/dashboard/agricola/diagnostico">
                <ListChecks className="size-4" />
                Abrir diagnóstico
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm" className="rounded-sm">
              <Link href="/dashboard/agricola/recomendacoes">
                <Target className="size-4" />
                Abrir recomendações
              </Link>
            </Button>
          </div>
        )}
        icon={<Target className="size-5" />}
      />

      <Alert className="rounded-sm">
        <AlertCircle className="size-4" />
        <AlertTitle>Fila oficial consolidada</AlertTitle>
        <AlertDescription>
          A central agrega diagnósticos, recomendações, benchmark e warnings oficiais em uma ordem determinística.
        </AlertDescription>
      </Alert>

      {prioridades?.sujeito_reconciliacao && (
        <Alert className="rounded-sm border-amber-200 bg-amber-50/70 text-amber-950">
          <TriangleAlert className="size-4" />
          <AlertTitle>Reconciliação pendente</AlertTitle>
          <AlertDescription>Prioridades sujeitas à reconciliação.</AlertDescription>
        </Alert>
      )}

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <CalendarRange className="size-4 text-muted-foreground" />
            Filtros oficiais
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid gap-4 lg:grid-cols-4">
            <div className="flex flex-col gap-1.5">
              <label id="prioridade-safra-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Safra
              </label>
              <Select
                value={effectiveSafraId}
                onValueChange={(value) => {
                  setSelectedSafraId(value);
                  setSelectedProductionUnitId("TODAS");
                }}
                disabled={isLoadingSafras || safras.length === 0}
              >
                <SelectTrigger aria-labelledby="prioridade-safra-label" data-testid="prioridade-safra-select">
                  <SelectValue placeholder={isLoadingSafras ? "Carregando safras..." : "Selecionar safra"} />
                </SelectTrigger>
                <SelectContent>
                  {safras.map((safra) => (
                    <SelectItem key={safra.id} value={safra.id}>
                      {getSafraLabel(safra)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label id="prioridade-unidade-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Unidade produtiva
              </label>
              <Select
                value={effectiveUnidadeProdutivaId}
                onValueChange={(value) => {
                  setSelectedUnidadeProdutivaId(value === "TODAS" ? "" : value);
                  setSelectedSafraId("");
                  setSelectedProductionUnitId("TODAS");
                }}
              >
                <SelectTrigger aria-labelledby="prioridade-unidade-label" data-testid="prioridade-unidade-produtiva-select">
                  <SelectValue placeholder="Selecionar unidade" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODAS">Todas as unidades</SelectItem>
                  {unidadesProdutivas.map((unidade) => (
                    <SelectItem key={unidade.id} value={unidade.id}>
                      {unidade.nome ?? unidade.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label id="prioridade-production-unit-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                ProductionUnit
              </label>
              <Select
                value={selectedProductionUnitId}
                onValueChange={setSelectedProductionUnitId}
                disabled={isLoadingProductionUnits || productionUnits.length === 0}
              >
                <SelectTrigger aria-labelledby="prioridade-production-unit-label" data-testid="prioridade-production-unit-select">
                  <SelectValue placeholder={isLoadingProductionUnits ? "Carregando unidades..." : "Todas as unidades"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODAS">Todas as unidades</SelectItem>
                  {productionUnits.map((unit) => (
                    <SelectItem key={unit.id} value={unit.id}>
                      {unit.area_nome ?? unit.cultivo_nome ?? unit.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="prioridade-data-inicio" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data inicial
                </label>
                <Input id="prioridade-data-inicio" data-testid="prioridade-data-inicio" type="date" value={dataInicio} onChange={(event) => setDataInicio(event.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="prioridade-data-fim" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data final
                </label>
                <Input id="prioridade-data-fim" data-testid="prioridade-data-fim" type="date" value={dataFim} onChange={(event) => setDataFim(event.target.value)} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoadingPrioridades ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <Card key={item} className="rounded-sm shadow-sm">
              <CardContent className="p-5 flex items-start gap-4">
                <Skeleton className="size-10 rounded-sm" />
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-8 w-32" />
                  <Skeleton className="h-3 w-20" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard color="agro" icon={Target} label="Total de prioridades" value={String(prioridades?.resumo.total ?? 0)} subtitle={periodLabel} />
          <StatCard color="warning" icon={TriangleAlert} label="Prioridades críticas" value={String(prioridades?.resumo.prioridade_critica ?? 0)} subtitle="Top da fila consolidada" />
          <StatCard color="operacional" icon={AlertCircle} label="Riscos operacionais" value={String((prioridades?.resumo.risco_operacional ?? 0) + (prioridades?.resumo.atencao ?? 0))} subtitle="Consolidação assistida" />
          <StatCard color="primary" icon={CheckCircle2} label="Novas" value={String(prioridades?.resumo.nova ?? 0)} subtitle="Sem automação de execução" />
        </div>
      )}

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <ListChecks className="size-4 text-muted-foreground" />
            Lista consolidada por prioridade
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {prioridades?.prioridades?.length ? (
            prioridades.prioridades.map((item) => {
              const tone = severityTone[item.severidade];
              const status = statusTone[item.status];
              return (
                <div
                  key={`${item.tipo}-${item.id}-${item.posicao ?? item.label}`}
                  className={cn(
                    "rounded-sm border p-4 flex flex-col gap-2 md:flex-row md:items-start md:justify-between transition-colors",
                    activePrioridadeId === item.id ? "border-primary/40 bg-primary/5" : "bg-background",
                  )}
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={tone.variant} className="rounded-sm">{tone.label}</Badge>
                      <Badge variant="outline" className="rounded-sm">
                        {item.tipo.split("_").join(" ")}
                      </Badge>
                      <Badge variant={status.variant} className="rounded-sm">{status.label}</Badge>
                    </div>
                    <p className="text-sm font-bold">{item.entidade_label}</p>
                    <p className="text-sm text-muted-foreground">{item.contexto_operacional}</p>
                    <p className="text-xs text-muted-foreground">{item.contexto_economico}</p>
                      <p className="text-sm font-medium">Ação sugerida: {item.acao_sugerida}</p>
                    <div className="flex flex-wrap gap-2 pt-1">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="rounded-sm"
                        onClick={() => setSelectedPrioridadeId(item.id)}
                      >
                        <History className="size-4" />
                        Histórico
                      </Button>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <Badge variant="secondary" className="rounded-sm">
                        Score {item.score_prioridade}
                      </Badge>
                      <Badge variant="outline" className="rounded-sm">
                        {item.origem}
                      </Badge>
                      <Badge variant="outline" className="rounded-sm">
                        Recorrência {item.recorrencia}
                      </Badge>
                      <Badge variant="outline" className="rounded-sm">
                        Impacto {formatMoney(item.impacto_estimado)}
                      </Badge>
                    </div>
                    <div className="rounded-sm border bg-muted/20 p-3 mt-3 flex flex-col gap-3">
                      <Textarea
                        value={observacoes[item.id] ?? ""}
                        onChange={(event) => setObservacoes((current) => ({ ...current, [item.id]: event.target.value }))}
                        placeholder="Observação curta para o acompanhamento operacional"
                        rows={2}
                        className="resize-none rounded-sm"
                        disabled={statusMutation.isPending}
                      />
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-sm"
                          onClick={() => atualizarStatus(item.id, "VISUALIZADA")}
                          disabled={statusMutation.isPending}
                        >
                          Visualizada
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-sm"
                          onClick={() => atualizarStatus(item.id, "EM_ANALISE")}
                          disabled={statusMutation.isPending}
                        >
                          Em análise
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-sm"
                          onClick={() => atualizarStatus(item.id, "RESOLVIDA")}
                          disabled={statusMutation.isPending}
                        >
                          Resolver
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-sm"
                          onClick={() => atualizarStatus(item.id, "IGNORADA")}
                          disabled={statusMutation.isPending}
                        >
                          Ignorar
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Status operacional sem impacto no cálculo oficial. Atualizações ficam registradas no audit log do tenant.
                      </p>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground md:text-right space-y-1">
                    <p className="font-semibold text-foreground">#{item.posicao ?? "—"}</p>
                    <p>Entidade: {item.entidade_tipo}</p>
                    <p>Status: {item.status}</p>
                    <p>Origem: {item.origem_codigo}</p>
                    <p>Fontes: {item.fontes_relacionadas.join(", ") || "—"}</p>
                  </div>
                </div>
              );
            })
          ) : (
            <EmptyState
              icon={<Target />}
              title="Nenhuma prioridade relevante"
              description="No recorte selecionado, a fila oficial não encontrou prioridades acionáveis acima do limiar governado."
            />
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        {Object.entries(groups).map(([origem, items]) => (
          <Card key={origem} className="rounded-sm shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center justify-between gap-2">
                <span>{origem.split("_").join(" ")}</span>
                <Badge variant="secondary" className="rounded-sm">
                  {items.length}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {items.slice(0, 3).map((item) => (
                <div key={`${origem}-${item.id}`} className="rounded-sm border p-3 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={severityTone[item.severidade].variant} className="rounded-sm">{severityTone[item.severidade].label}</Badge>
                    <Badge variant={statusTone[item.status].variant} className="rounded-sm">{statusTone[item.status].label}</Badge>
                  </div>
                  <p className="text-sm font-semibold">{item.entidade_label}</p>
                  <p className="text-xs text-muted-foreground">{item.acao_sugerida}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <MessageSquare className="size-4 text-muted-foreground" />
              Comentários e acompanhamento
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedPrioridade ? (
              <>
                <div className="rounded-sm border bg-muted/20 p-4 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={severityTone[selectedPrioridade.severidade].variant} className="rounded-sm">
                      {severityTone[selectedPrioridade.severidade].label}
                    </Badge>
                    <Badge variant={statusTone[selectedPrioridade.status].variant} className="rounded-sm">
                      {statusTone[selectedPrioridade.status].label}
                    </Badge>
                    <Badge variant="outline" className="rounded-sm">
                      {selectedPrioridade.origem.split("_").join(" ")}
                    </Badge>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-semibold">{selectedPrioridade.entidade_label}</p>
                    <p className="text-xs text-muted-foreground">{selectedPrioridade.contexto_operacional}</p>
                    <p className="text-xs text-muted-foreground">{selectedPrioridade.acao_sugerida}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="prioridade-comentario" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Comentário interno
                  </label>
                  <Textarea
                    id="prioridade-comentario"
                    data-testid="prioridade-comentario"
                    rows={4}
                    maxLength={240}
                    placeholder="Registrar observação curta, sem alterar o cálculo oficial."
                    value={comentarios[selectedPrioridade.id] ?? ""}
                    onChange={(event) =>
                      setComentarios((current) => ({
                        ...current,
                        [selectedPrioridade.id]: event.target.value,
                      }))
                    }
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      size="sm"
                      className="rounded-sm"
                      onClick={() => adicionarComentario(selectedPrioridade.id)}
                      disabled={comentarioMutation.isPending}
                    >
                      Salvar comentário
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="rounded-sm"
                      onClick={() => setComentarios((current) => ({ ...current, [selectedPrioridade.id]: "" }))}
                    >
                      Limpar
                    </Button>
                  </div>
                </div>

                <div className="rounded-sm border p-4 space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <History className="size-4 text-muted-foreground" />
                      <p className="text-sm font-semibold">Histórico simples</p>
                    </div>
                    <Badge variant="outline" className="rounded-sm">
                      {historicoQuery.data?.historico.length ?? 0} eventos
                    </Badge>
                  </div>
                  {historicoQuery.isLoading ? (
                    <div className="space-y-2">
                      <Skeleton className="h-16 w-full rounded-sm" />
                      <Skeleton className="h-16 w-full rounded-sm" />
                    </div>
                  ) : (historicoQuery.data?.historico.length ?? 0) > 0 ? (
                    <div className="space-y-3">
                      {historicoQuery.data?.historico.map((item) => (
                        <div key={item.id} className="rounded-sm bg-muted/30 border p-3 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge
                              variant={item.evento_tipo === "COMENTARIO" ? "diagnostic" : statusTone[item.status_novo ?? "NOVA"].variant}
                              className="rounded-sm"
                            >
                              {item.evento_tipo === "COMENTARIO" ? "Comentário" : `Status ${statusTone[item.status_novo ?? "NOVA"].label}`}
                            </Badge>
                            <span className="text-xs text-muted-foreground">{formatDateTime(item.alterado_em)}</span>
                          </div>
                          {item.evento_tipo === "STATUS" ? (
                            <p className="text-sm">
                              <span className="font-medium">{item.status_anterior ?? "NOVA"}</span>
                              {" → "}
                              <span className="font-semibold">{item.status_novo ?? "NOVA"}</span>
                            </p>
                          ) : null}
                          {item.comentario ? <p className="text-sm text-foreground">{item.comentario}</p> : null}
                          {item.observacao ? <p className="text-xs text-muted-foreground">Observação: {item.observacao}</p> : null}
                          <p className="text-xs text-muted-foreground">
                            {item.responsavel_nome ?? "Sistema"} {item.responsavel_id ? `• ${item.responsavel_id}` : ""}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Nenhum evento registrado para esta prioridade.</p>
                  )}
                </div>
              </>
            ) : (
              <EmptyState
                icon={<MessageSquare />}
                title="Selecione uma prioridade"
                description="Escolha um item da fila para registrar comentários internos e revisar o histórico simples."
              />
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <History className="size-4 text-muted-foreground" />
              Resumo do acompanhamento
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-sm border p-4 space-y-2">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Prioridade selecionada</p>
              <p className="text-sm font-semibold">{selectedPrioridade?.entidade_label ?? "Nenhuma selecionada"}</p>
              <p className="text-xs text-muted-foreground">{selectedPrioridade?.contexto_economico ?? "Selecione uma prioridade da fila."}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <StatCard label="Eventos" value={String(historicoQuery.data?.historico.length ?? 0)} icon={History} />
              <StatCard label="Status atual" value={historicoQuery.data?.status_atual ?? selectedPrioridade?.status ?? "—"} icon={CheckCircle2} />
            </div>
            <p className="text-xs text-muted-foreground">
              O acompanhamento de status e comentários é operacional e fica registrado apenas no `TenantAuditLog`, sem alterar a DRE, KPIs ou a prioridade oficial.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="size-4 text-muted-foreground" />
            Resumo por origem e tipo
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {Object.entries(prioridades?.resumo.por_origem ?? {}).map(([origem, total]) => (
            <Badge key={origem} variant="outline" className="rounded-sm px-3 py-1.5">
              {origem.split("_").join(" ")}: {total}
            </Badge>
          ))}
          {Object.entries(prioridades?.resumo.por_tipo ?? {}).map(([tipo, total]) => (
            <Badge key={tipo} variant="outline" className="rounded-sm px-3 py-1.5">
              {tipo.split("_").join(" ")}: {total}
            </Badge>
          ))}
          {!Object.keys(prioridades?.resumo.por_origem ?? {}).length && !Object.keys(prioridades?.resumo.por_tipo ?? {}).length && (
            <span className="text-sm text-muted-foreground">Sem agrupamentos disponíveis.</span>
          )}
        </CardContent>
      </Card>

      {isErrorPrioridades && (
        <div className="p-6">
          <EmptyState
            icon={<BarChart3 />}
            title="Não foi possível carregar as prioridades"
            description={(prioridadesError as Error)?.message || "Verifique o recorte selecionado e tente novamente."}
          />
        </div>
      )}
    </div>
  );
}
