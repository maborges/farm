"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  BarChart3,
  CalendarRange,
  Layers3,
  Target,
  TriangleAlert,
  WandSparkles,
} from "lucide-react";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { getSafraLabel } from "@/lib/safra-label";
import { useHasTier } from "@/hooks/use-has-tier";
import { PageHeader } from "@/components/shared/page-header";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { EmptyState } from "@/components/shared/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { ConvertPlanoTaskModal } from "@/components/agricola/inteligencia-operacional/convert-plan-task-modal";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type Severidade = "INFO" | "ATENCAO" | "RISCO_OPERACIONAL" | "RISCO_ECONOMICO" | "PRIORIDADE_CRITICA";
type BadgeTone = "critical" | "danger" | "attention" | "warning" | "info" | "priority" | "diagnostic" | "recommendation" | "secondary" | "outline";

interface SafraResumo {
  id: string;
  cultura: string | null;
  ano_safra: string;
  nome?: string | null;
}

interface ProductionUnitResumo {
  id: string;
  nome?: string | null;
  cultivo_nome?: string | null;
  area_nome?: string | null;
}

interface UnidadeProdutivaAutorizada {
  id: string;
  nome?: string | null;
  area_nome?: string | null;
  cultivo_nome?: string | null;
}

interface PlanoFonte {
  origem_analitica: "PRIORIDADE" | "DIAGNOSTICO" | "RECOMENDACAO";
  codigo: string;
  titulo: string;
  severidade: Severidade;
  scope: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY" | "TENANT";
  entidade_tipo: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  entidade_id: string;
  entidade_label: string;
}

interface PlanoItem {
  id: string;
  chave: string;
  scope: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  titulo: string;
  resumo: string;
  motivo: string;
  severidade: Severidade;
  impacto_estimado?: number | null;
  acoes_sugeridas: string[];
  prazo_sugerido: string;
  contexto_operacional: string;
  origem_primaria: PlanoFonte;
  fontes_analiticas: PlanoFonte[];
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  entidade_tipo: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  entidade_id: string;
  entidade_label: string;
  posicao?: number | null;
}

interface PlanoResumo {
  total: number;
  info: number;
  atencao: number;
  risco_operacional: number;
  risco_economico: number;
  prioridade_critica: number;
  por_origem: Record<string, number>;
  por_entidade_tipo: Record<string, number>;
  por_prazo: Record<string, number>;
}

interface PlanoResponse {
  tenant_id: string;
  gerado_em: string;
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  planos: PlanoItem[];
  resumo: PlanoResumo;
  warnings: Array<{
    codigo: string;
    titulo: string;
    severidade: string;
    mensagem: string;
    origem: string;
  }>;
  sujeito_reconciliacao: boolean;
  observacao_reconciliacao: string | null;
}

const severityTone: Record<Severidade, { label: string; variant: BadgeTone }> = {
  PRIORIDADE_CRITICA: { label: "Prioridade crítica", variant: "critical" },
  RISCO_ECONOMICO: { label: "Risco econômico", variant: "danger" },
  RISCO_OPERACIONAL: { label: "Risco operacional", variant: "attention" },
  ATENCAO: { label: "Atenção", variant: "warning" },
  INFO: { label: "Info", variant: "info" },
};

const sourceTone: Record<PlanoFonte["origem_analitica"], { label: string; variant: BadgeTone }> = {
  PRIORIDADE: { label: "Prioridade", variant: "priority" },
  DIAGNOSTICO: { label: "Diagnóstico", variant: "diagnostic" },
  RECOMENDACAO: { label: "Recomendação", variant: "recommendation" },
};

const severityOrder: Severidade[] = ["PRIORIDADE_CRITICA", "RISCO_ECONOMICO", "RISCO_OPERACIONAL", "ATENCAO", "INFO"];

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(value));
}

function formatImpact(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value)} pts`;
}

function groupPlansBy<T>(items: T[], keyFn: (item: T) => string) {
  return items.reduce<Record<string, T[]>>((acc, item) => {
    const key = keyFn(item);
    (acc[key] ||= []).push(item);
    return acc;
  }, {});
}

function displayContextLabel(item: PlanoItem) {
  return `${item.entidade_tipo === "PRODUCTION_UNIT" ? "ProductionUnit" : item.entidade_tipo} • ${item.entidade_label}`;
}

function renderSourceBadges(item: PlanoItem) {
  return (
    <div className="flex flex-wrap gap-2">
      <Badge variant={sourceTone[item.origem_primaria.origem_analitica].variant} className="rounded-sm">
        {sourceTone[item.origem_primaria.origem_analitica].label}
      </Badge>
      <Badge variant="outline" className="rounded-sm">
        {item.prazo_sugerido}
      </Badge>
      <Badge variant="outline" className="rounded-sm">
        {displayContextLabel(item)}
      </Badge>
    </div>
  );
}

function PlanoCard({ item, onCreateTask }: { item: PlanoItem; onCreateTask: (item: PlanoItem) => void }) {
  return (
    <Card className="rounded-sm shadow-sm border overflow-hidden">
      <CardContent className="p-4 space-y-3">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={severityTone[item.severidade].variant} className="rounded-sm">
                {severityTone[item.severidade].label}
              </Badge>
              <span className="text-xs text-muted-foreground">#{String(item.posicao ?? 0).padStart(2, "0")}</span>
            </div>
            <h3 className="text-sm font-bold text-foreground text-balance">{item.titulo}</h3>
            <p className="text-xs text-muted-foreground text-pretty">{item.resumo}</p>
          </div>
          <div className="text-right space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Impacto estimado</p>
            <p className="text-sm font-black tabular-nums">{formatImpact(item.impacto_estimado)}</p>
          </div>
        </div>

        {renderSourceBadges(item)}

        <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr]">
          <div className="space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Motivo</p>
            <p className="text-sm text-foreground">{item.motivo}</p>
          </div>
          <div className="space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Ações sugeridas</p>
            <ul className="space-y-1">
              {item.acoes_sugeridas.map((acao) => (
                <li key={acao} className="text-sm text-foreground flex items-start gap-2">
                  <span className="mt-1 size-1.5 rounded-full bg-primary shrink-0" />
                  <span>{acao}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/60">
          <div className="flex flex-wrap gap-2">
            {item.fontes_analiticas.map((fonte) => (
              <Badge key={`${fonte.origem_analitica}:${fonte.codigo}:${fonte.entidade_id}`} variant={sourceTone[fonte.origem_analitica].variant} className="rounded-sm">
                {fonte.origem_analitica} · {fonte.codigo}
              </Badge>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <p className="text-xs text-muted-foreground">Contexto operacional: {item.contexto_operacional}</p>
            <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => onCreateTask(item)}>
              Criar tarefa
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function InteligenciaOperacionalAgricolaPage() {
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const unidadesProdutivas = useAppStore(
    (state) => state.unidadesProdutivasAutorizadas
  ) as UnidadeProdutivaAutorizada[];

  const [selectedSafraId, setSelectedSafraId] = useState<string>("");
  const [selectedProductionUnitId, setSelectedProductionUnitId] = useState<string>("TODAS");
  const [selectedUnidadeProdutivaId, setSelectedUnidadeProdutivaId] = useState<string>("");
  const [dataInicio, setDataInicio] = useState<string>("");
  const [dataFim, setDataFim] = useState<string>("");
  const [planoParaConversao, setPlanoParaConversao] = useState<PlanoItem | null>(null);

  const effectiveUnidadeProdutivaId = selectedUnidadeProdutivaId || activeFazendaId || "";
  const safraScopeId = effectiveUnidadeProdutivaId || undefined;

  const { data: safras = [], isLoading: isLoadingSafras } = useQuery<SafraResumo[]>({
    queryKey: ["agricola-inteligencia-operacional", "safras", safraScopeId],
    queryFn: () => apiFetch(`/safras${safraScopeId ? `?unidade_produtiva_id=${safraScopeId}` : ""}`),
    enabled: hasProfessionalTier,
  });

  const effectiveSafraId = selectedSafraId || safras[0]?.id || "";

  const { data: productionUnits = [], isLoading: isLoadingProductionUnits } = useQuery<ProductionUnitResumo[]>({
    queryKey: ["agricola-inteligencia-operacional", "production-units", effectiveSafraId],
    queryFn: () => apiFetch(`/safras/${effectiveSafraId}/production-units`),
    enabled: hasProfessionalTier && !!effectiveSafraId,
  });

  const planoParams = useMemo(() => {
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
    data: planoResposta,
    isLoading: isLoadingPlano,
    isError: isErrorPlano,
    error: planoError,
  } = useQuery<PlanoResponse>({
    queryKey: ["agricola-inteligencia-operacional", "v1", planoParams],
    queryFn: () => apiFetch("/agricola/inteligencia-operacional/v1", { params: planoParams ?? undefined }),
    enabled: hasProfessionalTier && !!planoParams,
  });

  const planos = useMemo(() => planoResposta?.planos ?? [], [planoResposta?.planos]);
  const periodLabel =
    planoResposta?.data_inicio || planoResposta?.data_fim
      ? `${formatDate(planoResposta?.data_inicio)} → ${formatDate(planoResposta?.data_fim)}`
      : "Sem recorte temporal";

  const planosPorSeveridade = useMemo(() => {
    const agrupados = groupPlansBy(planos, (item) => item.severidade);
    return severityOrder
      .map((severidade) => ({
        severidade,
        items: agrupados[severidade] ?? [],
      }))
      .filter((grupo) => grupo.items.length > 0);
  }, [planos]);

  const planosPorContexto = useMemo(() => {
    const filtrados = planos.filter((item) => item.entidade_tipo === "SAFRA" || item.entidade_tipo === "PRODUCTION_UNIT");
    const agrupados = Object.entries(groupPlansBy(filtrados, (item) => `${item.scope}:${item.entidade_tipo}:${item.entidade_id}`))
      .map(([chave, items]) => ({
        chave,
        titulo: displayContextLabel(items[0]),
        scope: items[0].scope,
        items,
      }))
      .sort((a, b) => a.titulo.localeCompare(b.titulo, "pt-BR"));
    return agrupados;
  }, [planos]);

  if (!hasProfessionalTier) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <PageHeader
          title="Inteligência Operacional Aplicada"
          description="Planos operacionais assistidos derivados da cadeia analítica oficial."
          breadcrumbs={[
            { label: "Agrícola", href: "/dashboard/agricola" },
            { label: "Inteligência Operacional Aplicada" },
          ]}
          icon={<WandSparkles className="size-5" />}
        />
        <TierUpgradeCard
          title="Inteligência operacional disponível no PROFISSIONAL"
          description="A nova camada é somente leitura e deriva de prioridades, recomendações e diagnósticos governados."
          requiredTier="PROFISSIONAL"
          feature="agricola.inteligencia_operacional_v1"
          surface="agricola.inteligencia_operacional.page"
        />
      </div>
    );
  }

  if (!activeFazendaId) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <PageHeader
          title="Inteligência Operacional Aplicada"
          description="Planos operacionais assistidos derivados da cadeia analítica oficial."
          breadcrumbs={[
            { label: "Agrícola", href: "/dashboard/agricola" },
            { label: "Inteligência Operacional Aplicada" },
          ]}
          icon={<WandSparkles className="size-5" />}
        />
        <EmptyState
          icon={<WandSparkles />}
          title="Selecione uma propriedade"
          description="Escolha uma fazenda no seletor acima para gerar os planos operacionais assistidos."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Inteligência Operacional Aplicada"
        description="Planos assistidos e somente leitura, derivados da cadeia oficial de diagnóstico, recomendações e prioridades."
        breadcrumbs={[
          { label: "Agrícola", href: "/dashboard/agricola" },
          { label: "Prioridades Agrícolas", href: "/dashboard/agricola/prioridades" },
          { label: "Inteligência Operacional Aplicada" },
        ]}
        actions={(
          <Button asChild variant="outline" size="sm" className="rounded-sm">
            <Link href="/dashboard/agricola/prioridades">
              <Target className="size-4" />
              Abrir prioridades
            </Link>
          </Button>
        )}
        icon={<WandSparkles className="size-5" />}
      />

      <Alert className="rounded-sm border-sky-200 bg-sky-50/60 text-sky-950">
        <AlertCircle className="size-4" />
        <AlertTitle>Leitura assistida</AlertTitle>
        <AlertDescription>
          Esta camada não executa ações, não altera tarefas reais, não usa workflow engine e não recalcula analytics.
        </AlertDescription>
      </Alert>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {isLoadingPlano ? (
          <>
            {Array.from({ length: 4 }).map((_, index) => (
              <Card key={index} className="rounded-sm shadow-sm border">
                <CardContent className="p-5 flex items-start gap-4">
                  <Skeleton className="size-10 rounded-sm" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-7 w-14" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </>
        ) : (
          <>
            <StatCard
              icon={Layers3}
              label="Planos sugeridos"
              value={planoResposta?.resumo.total ?? 0}
              subtitle={periodLabel}
              color="agro"
            />
            <StatCard
              icon={TriangleAlert}
              label="Prioridade crítica"
              value={planoResposta?.resumo.prioridade_critica ?? 0}
              subtitle="Demandas imediatas"
              color="destructive"
            />
            <StatCard
              icon={BarChart3}
              label="Riscos totais"
              value={(planoResposta?.resumo.risco_economico ?? 0) + (planoResposta?.resumo.risco_operacional ?? 0)}
              subtitle="Econômicos + operacionais"
              color="warning"
            />
            <StatCard
              icon={CalendarRange}
              label="Contextos rastreados"
              value={Object.keys(planoResposta?.resumo.por_entidade_tipo ?? {}).length}
              subtitle="Safra e ProductionUnit"
              color="operacional"
            />
          </>
        )}
      </div>

      <Card className="rounded-sm shadow-sm border overflow-hidden">
        <CardContent className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="size-10 rounded-sm bg-[var(--module-agro-bg)] flex items-center justify-center shrink-0">
              <WandSparkles className="size-5 text-[var(--module-agro)]" />
            </div>
            <div className="flex flex-col gap-1">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-sm font-black uppercase tracking-wider">Visão assistida de planos</h2>
                <Badge variant="secondary" className="rounded-sm">Somente leitura</Badge>
              </div>
              <p className="text-sm text-muted-foreground max-w-2xl">
                Os planos são derivados de prioridades, recomendações e diagnósticos oficiais, com ações sugeridas e rastreabilidade da origem analítica.
              </p>
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <AlertCircle className="size-3.5" />
                Nenhuma execução automática, nenhum scheduler e nenhum workflow paralelo.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button asChild variant="outline" size="sm" className="rounded-sm">
              <Link href="/dashboard/agricola/diagnostico">
                <Target className="size-4" />
                Abrir diagnóstico
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <section className="grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
        <Card className="rounded-sm shadow-sm border overflow-hidden">
          <CardHeader className="border-b border-border/60 bg-muted/20">
            <CardTitle className="text-sm flex items-center gap-2">
              <TriangleAlert className="size-4" />
              Planos por severidade
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-6">
            {isLoadingPlano ? (
              <div className="space-y-4">
                <Skeleton className="h-40 w-full rounded-sm" />
                <Skeleton className="h-40 w-full rounded-sm" />
              </div>
            ) : isErrorPlano ? (
              <div className="text-sm text-destructive">
                {(planoError as Error)?.message || "Não foi possível carregar os planos operacionais assistidos."}
              </div>
            ) : planosPorSeveridade.length === 0 ? (
              <EmptyState
                icon={<Layers3 />}
                title="Nenhum plano sugerido no recorte atual"
                description="O recorte está consistente para a visão operacional assistida."
                action={{ label: "Abrir prioridades", href: "/dashboard/agricola/prioridades" }}
              />
            ) : (
              planosPorSeveridade.map((grupo) => (
                <div key={grupo.severidade} className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge variant={severityTone[grupo.severidade].variant} className="rounded-sm">
                        {severityTone[grupo.severidade].label}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{grupo.items.length} plano(s)</span>
                    </div>
                    <span className="text-xs text-muted-foreground">Ordenado por prioridade definida</span>
                  </div>
                    <div className="grid gap-3">
                    {grupo.items.map((item) => (
                      <PlanoCard key={item.id} item={item} onCreateTask={setPlanoParaConversao} />
                    ))}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm shadow-sm border overflow-hidden">
          <CardHeader className="border-b border-border/60 bg-muted/20">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="size-4" />
              Resumo da cadeia
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-sm border p-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Por origem</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(planoResposta?.resumo.por_origem ?? {}).map(([origem, quantidade]) => (
                    <Badge key={origem} variant="outline" className="rounded-sm bg-white">
                      {origem}: {quantidade}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="rounded-sm border p-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Por prazo</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(planoResposta?.resumo.por_prazo ?? {}).map(([prazo, quantidade]) => (
                    <Badge key={prazo} variant="outline" className="rounded-sm bg-white">
                      {prazo}: {quantidade}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-sm border p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Notas de governança</p>
              <ul className="mt-2 space-y-2 text-sm text-foreground">
                <li>• A nova camada não cria tarefas reais.</li>
                <li>• A origem de cada plano permanece rastreável até diagnóstico, recomendação ou prioridade.</li>
                <li>• O payload mantém o recorte de tenant, safra, ProductionUnit e período.</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </section>

      <Card className="rounded-sm shadow-sm border overflow-hidden">
        <CardHeader className="border-b border-border/60 bg-muted/20">
          <CardTitle className="text-sm flex items-center gap-2">
            <Layers3 className="size-4" />
            Planos por safra e ProductionUnit
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 space-y-4">
          <p className="text-xs text-muted-foreground">
            Os demais contextos operacionais permanecem disponíveis na visão por severidade.
          </p>
          {planosPorContexto.length === 0 ? (
            <EmptyState
              icon={<Layers3 />}
              title="Nenhum contexto operacional encontrado"
              description="Os planos aparecerão aqui quando houver elementos rastreáveis no recorte atual."
            />
          ) : (
            planosPorContexto.map((grupo) => (
              <div key={grupo.chave} className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="rounded-sm">
                      {grupo.scope}
                    </Badge>
                    <h3 className="text-sm font-bold">{grupo.titulo}</h3>
                  </div>
                  <span className="text-xs text-muted-foreground">{grupo.items.length} plano(s)</span>
                </div>
                <div className="grid gap-3">
                  {grupo.items.map((item) => (
                    <PlanoCard key={item.id} item={item} onCreateTask={setPlanoParaConversao} />
                  ))}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card className="rounded-sm shadow-sm border overflow-hidden">
        <CardContent className="p-5 grid gap-4 lg:grid-cols-4">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Safra</label>
            <Select value={selectedSafraId} onValueChange={setSelectedSafraId}>
              <SelectTrigger className="rounded-sm">
                <SelectValue placeholder={isLoadingSafras ? "Carregando safras..." : "Selecione uma safra"} />
              </SelectTrigger>
              <SelectContent>
                {safras.map((safra) => (
                  <SelectItem key={safra.id} value={safra.id}>
                    {getSafraLabel(safra as any)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Unidade produtiva</label>
            <Select
              value={selectedUnidadeProdutivaId || "__DEFAULT__"}
              onValueChange={(value) => setSelectedUnidadeProdutivaId(value === "__DEFAULT__" ? "" : value)}
            >
              <SelectTrigger className="rounded-sm">
                <SelectValue placeholder="Fazenda principal" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__DEFAULT__">Fazenda principal</SelectItem>
                {unidadesProdutivas.map((up) => (
                  <SelectItem key={up.id} value={up.id}>
                    {up.nome || up.area_nome || up.cultivo_nome || up.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">ProductionUnit</label>
            <Select value={selectedProductionUnitId} onValueChange={setSelectedProductionUnitId}>
              <SelectTrigger className="rounded-sm">
                <SelectValue placeholder={isLoadingProductionUnits ? "Carregando..." : "Todas"} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="TODAS">Todas</SelectItem>
                {productionUnits.map((pu) => (
                  <SelectItem key={pu.id} value={pu.id}>
                    {pu.area_nome || pu.cultivo_nome || pu.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Período</label>
            <div className="grid grid-cols-2 gap-2">
              <Input
                type="date"
                value={dataInicio}
                onChange={(event) => setDataInicio(event.target.value)}
                className="rounded-sm"
              />
              <Input
                type="date"
                value={dataFim}
                onChange={(event) => setDataFim(event.target.value)}
                className="rounded-sm"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <ConvertPlanoTaskModal
        open={Boolean(planoParaConversao)}
        onOpenChange={(open) => {
          if (!open) {
            setPlanoParaConversao(null);
          }
        }}
        plano={planoParaConversao}
        safraId={effectiveSafraId}
        productionUnitId={selectedProductionUnitId !== "TODAS" ? selectedProductionUnitId : undefined}
        unidadeProdutivaId={effectiveUnidadeProdutivaId || undefined}
        dataInicio={dataInicio || undefined}
        dataFim={dataFim || undefined}
      />
    </div>
  );
}
