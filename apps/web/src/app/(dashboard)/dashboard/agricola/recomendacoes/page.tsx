"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  BarChart3,
  CalendarRange,
  CheckCircle2,
  CircleAlert,
  Lightbulb,
  LineChart,
  Sparkles,
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
import { cn } from "@/lib/utils";

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

interface RecomendacaoWarning {
  codigo: string;
  titulo: string;
  severidade: string;
  mensagem: string;
  origem: string;
}

interface RecomendacaoItem {
  scope: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  id: string;
  label: string;
  tipo:
    | "REVISAO_OPERACAO"
    | "INSPECAO_EQUIPAMENTO"
    | "REVISAO_JORNADA"
    | "ANALISE_PRODUCTION_UNIT"
    | "INVESTIGACAO_MARGEM_NEGATIVA"
    | "REVISAO_CUSTO_HECTARE"
    | "REVISAO_RECONCILIACAO_ECONOMICA"
    | "AUDITORIA_INCONSISTENCIA_OPERACIONAL"
    | "ANALISE_SAFRA_BENCHMARK";
  severidade: "INFO" | "ATENCAO" | "RISCO_OPERACIONAL" | "RISCO_ECONOMICO";
  origem_diagnostica_codigo: string;
  origem_diagnostica_titulo: string;
  contexto_operacional: string;
  contexto_economico: string;
  explicacao_objetiva: string;
  acao_sugerida: string;
  entidade_tipo: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  entidade_id: string;
  entidade_label: string;
  status: "NOVA" | "VISUALIZADA" | "ACEITA" | "IGNORADA";
  warnings_relevantes: string[];
  posicao?: number | null;
}

interface RecomendacaoResumo {
  total: number;
  nova: number;
  visualizada: number;
  aceita: number;
  ignorada: number;
  info: number;
  atencao: number;
  risco_operacional: number;
  risco_economico: number;
  por_tipo: Record<string, number>;
}

interface RecomendacaoResponse {
  tenant_id: string;
  gerado_em: string;
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  recomendacoes: RecomendacaoItem[];
  resumo: RecomendacaoResumo;
  warnings: RecomendacaoWarning[];
  sujeito_reconciliacao: boolean;
  observacao_reconciliacao: string | null;
}

const statusTone = {
  NOVA: { label: "Nova", variant: "priority" as const },
  VISUALIZADA: { label: "Visualizada", variant: "secondary" as const },
  ACEITA: { label: "Aceita", variant: "success" as const },
  IGNORADA: { label: "Ignorada", variant: "warning" as const },
} as const;

const severityTone = {
  INFO: { label: "Info", variant: "info" as const },
  ATENCAO: { label: "Atenção", variant: "warning" as const },
  RISCO_OPERACIONAL: { label: "Risco operacional", variant: "attention" as const },
  RISCO_ECONOMICO: { label: "Risco econômico", variant: "danger" as const },
} as const;

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(value));
}

function groupByType(items: RecomendacaoItem[]) {
  return items.reduce<Record<string, RecomendacaoItem[]>>((acc, item) => {
    (acc[item.tipo] ||= []).push(item);
    return acc;
  }, {});
}

export default function RecomendacoesOperacionaisEconomicasAgricolaPage() {
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const unidadesProdutivas = useAppStore((state) => state.unidadesProdutivasAutorizadas);

  const [selectedSafraId, setSelectedSafraId] = useState<string>("");
  const [selectedProductionUnitId, setSelectedProductionUnitId] = useState<string>("TODAS");
  const [selectedUnidadeProdutivaId, setSelectedUnidadeProdutivaId] = useState<string>("");
  const [dataInicio, setDataInicio] = useState<string>("");
  const [dataFim, setDataFim] = useState<string>("");

  const effectiveUnidadeProdutivaId = selectedUnidadeProdutivaId || activeFazendaId || "";
  const safraScopeId = effectiveUnidadeProdutivaId || undefined;

  const { data: safras = [], isLoading: isLoadingSafras } = useQuery<SafraResumo[]>({
    queryKey: ["agricola-recomendacoes", "safras", safraScopeId],
        queryFn: () => apiFetch(`/safras/${safraScopeId ? `?unidade_produtiva_id=${safraScopeId}` : ""}`),
    enabled: hasProfessionalTier,
  });

  const effectiveSafraId = selectedSafraId || safras[0]?.id || "";

  const { data: productionUnits = [], isLoading: isLoadingProductionUnits } = useQuery<ProductionUnitResumo[]>({
    queryKey: ["agricola-recomendacoes", "production-units", effectiveSafraId],
    queryFn: () => apiFetch(`/safras/${effectiveSafraId}/production-units`),
    enabled: hasProfessionalTier && !!effectiveSafraId,
  });

  const recomendacaoParams = useMemo(() => {
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
    data: recomendacoes,
    isLoading: isLoadingRecomendacoes,
    isError: isErrorRecomendacoes,
    error: recomendacoesError,
  } = useQuery<RecomendacaoResponse>({
    queryKey: ["agricola-recomendacoes", "v1", recomendacaoParams],
    queryFn: () => apiFetch("/agricola/recomendacoes/v1", { params: recomendacaoParams ?? undefined }),
    enabled: hasProfessionalTier && !!recomendacaoParams,
  });

  const groups = useMemo(() => groupByType(recomendacoes?.recomendacoes ?? []), [recomendacoes?.recomendacoes]);
  const periodLabel =
    recomendacoes?.data_inicio || recomendacoes?.data_fim
      ? `${formatDate(recomendacoes?.data_inicio)} → ${formatDate(recomendacoes?.data_fim)}`
      : "Sem recorte temporal";

  if (!hasProfessionalTier) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <PageHeader
          title="Recomendações Operacionais e Econômicas Assistidas"
          description="Leitura oficial assistida derivada da DRE agrícola v1."
          breadcrumbs={[
            { label: "Agrícola", href: "/dashboard/agricola" },
            { label: "Recomendações Operacionais e Econômicas Assistidas" },
          ]}
          icon={<Sparkles className="size-5" />}
        />
        <TierUpgradeCard
          title="Recomendações agrícolas disponíveis no PROFISSIONAL"
          description="A visão oficial de recomendações reutiliza DRE agrícola v1, diagnósticos oficiais e analytics governados."
          requiredTier="PROFISSIONAL"
          feature="agricola.recomendacoes_v1"
          surface="agricola.recomendacoes.page"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Recomendações Operacionais e Econômicas Assistidas"
        description="Recomendações oficiais e determinísticas derivadas da DRE agrícola v1 e dos diagnósticos governados."
        breadcrumbs={[
          { label: "Agrícola", href: "/dashboard/agricola" },
          { label: "DRE Agrícola v1", href: "/dashboard/agricola/dre" },
          { label: "Recomendações Operacionais e Econômicas Assistidas" },
        ]}
        actions={(
          <Button asChild variant="outline" size="sm" className="rounded-sm">
            <Link href="/dashboard/agricola/diagnostico">
              <LineChart className="size-4" />
              Abrir diagnóstico
            </Link>
          </Button>
        )}
        icon={<Sparkles className="size-5" />}
      />

      <Alert className="rounded-sm">
        <AlertCircle className="size-4" />
        <AlertTitle>Leitura oficial</AlertTitle>
        <AlertDescription>
          As recomendações consomem DiagnosticoService e os analytics oficiais já consolidados. Não há IA generativa, automação autônoma nem recálculo fora da DRE.
        </AlertDescription>
      </Alert>

      {recomendacoes?.sujeito_reconciliacao && (
        <Alert className="rounded-sm border-amber-200 bg-amber-50/70 text-amber-950">
          <AlertCircle className="size-4" />
          <AlertTitle>Reconciliação pendente</AlertTitle>
          <AlertDescription>Recomendações sujeitas à reconciliação.</AlertDescription>
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
              <label id="recomendacao-safra-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                <SelectTrigger aria-labelledby="recomendacao-safra-label" data-testid="recomendacao-safra-select">
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
              <label id="recomendacao-unidade-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                <SelectTrigger aria-labelledby="recomendacao-unidade-label" data-testid="recomendacao-unidade-produtiva-select">
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
              <label id="recomendacao-production-unit-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                ProductionUnit
              </label>
              <Select
                value={selectedProductionUnitId}
                onValueChange={setSelectedProductionUnitId}
                disabled={isLoadingProductionUnits || productionUnits.length === 0}
              >
                <SelectTrigger aria-labelledby="recomendacao-production-unit-label" data-testid="recomendacao-production-unit-select">
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
                <label htmlFor="recomendacao-data-inicio" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data inicial
                </label>
                <Input id="recomendacao-data-inicio" data-testid="recomendacao-data-inicio" type="date" value={dataInicio} onChange={(event) => setDataInicio(event.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="recomendacao-data-fim" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data final
                </label>
                <Input id="recomendacao-data-fim" data-testid="recomendacao-data-fim" type="date" value={dataFim} onChange={(event) => setDataFim(event.target.value)} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoadingRecomendacoes ? (
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
          <StatCard color="agro" icon={Sparkles} label="Total de recomendações" value={String(recomendacoes?.resumo.total ?? 0)} subtitle="Leitura assistida" />
          <StatCard color="operacional" icon={CircleAlert} label="Riscos operacionais" value={String(recomendacoes?.resumo.risco_operacional ?? 0)} subtitle={periodLabel} />
          <StatCard color="warning" icon={AlertCircle} label="Riscos econômicos" value={String(recomendacoes?.resumo.risco_economico ?? 0)} subtitle="Governadas pela DRE v1" />
          <StatCard color="primary" icon={CheckCircle2} label="Novas" value={String(recomendacoes?.resumo.nova ?? 0)} subtitle="Sem execução automática" />
        </div>
      )}

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Lightbulb className="size-4 text-muted-foreground" />
            Lista leve de ações sugeridas
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {recomendacoes?.recomendacoes?.length ? (
            recomendacoes.recomendacoes.map((item) => {
              const tone = severityTone[item.severidade];
              const status = statusTone[item.status];
              return (
                <div key={`${item.tipo}-${item.id}-${item.posicao ?? item.label}`} className="rounded-sm border p-4 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={tone.variant} className="rounded-sm">{tone.label}</Badge>
                      <Badge variant="outline" className="rounded-sm">
                        {item.tipo.replaceAll("_", " ")}
                      </Badge>
                      <Badge variant={status.variant} className="rounded-sm">{status.label}</Badge>
                    </div>
                    <p className="text-sm font-bold">{item.explicacao_objetiva}</p>
                    <p className="text-sm text-muted-foreground">{item.entidade_label}</p>
                    <p className="text-sm">{item.contexto_operacional}</p>
                    <p className="text-xs text-muted-foreground">{item.contexto_economico}</p>
                    <p className="text-sm font-medium">Ação sugerida: {item.acao_sugerida}</p>
                  </div>
                  <div className="text-xs text-muted-foreground md:text-right space-y-1">
                    <p className="font-semibold text-foreground">#{item.posicao ?? "—"}</p>
                    <p>Entidade: {item.entidade_tipo}</p>
                    <p>Status: {item.status}</p>
                    <p>Origem: {item.origem_diagnostica_codigo}</p>
                  </div>
                </div>
              );
            })
          ) : (
            <EmptyState
              icon={<Sparkles />}
              title="Nenhuma recomendação relevante"
              description="No recorte selecionado, a leitura governada não encontrou recomendações acionáveis acima do limiar oficial."
            />
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        {Object.entries(groups).map(([tipo, items]) => (
          <Card key={tipo} className="rounded-sm shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center justify-between gap-2">
                <span>{tipo.replaceAll("_", " ")}</span>
                <Badge variant="secondary" className="rounded-sm">
                  {items.length}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {items.slice(0, 3).map((item) => (
                <div key={`${tipo}-${item.id}`} className="rounded-sm border p-3 space-y-1">
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

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="size-4 text-muted-foreground" />
            Resumo por tipo
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {Object.entries(recomendacoes?.resumo.por_tipo ?? {}).map(([tipo, total]) => (
            <Badge key={tipo} variant="outline" className="rounded-sm px-3 py-1.5">
              {tipo.replaceAll("_", " ")}: {total}
            </Badge>
          ))}
          {!Object.keys(recomendacoes?.resumo.por_tipo ?? {}).length && (
            <span className="text-sm text-muted-foreground">Sem agrupamentos disponíveis.</span>
          )}
        </CardContent>
      </Card>

      {isErrorRecomendacoes && (
        <div className="p-6">
          <EmptyState
            icon={<BarChart3 />}
            title="Não foi possível carregar as recomendações"
            description={(recomendacoesError as Error)?.message || "Verifique o recorte selecionado e tente novamente."}
          />
        </div>
      )}
    </div>
  );
}
