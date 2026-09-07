"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  BarChart3,
  CalendarRange,
  LineChart,
  Search,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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

interface DiagnosticoWarning {
  codigo: string;
  titulo: string;
  severidade: string;
  mensagem: string;
  origem: string;
}

interface DiagnosticoItem {
  scope: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY" | "TENANT";
  id: string;
  label: string;
  codigo: string;
  titulo: string;
  severidade: "INFO" | "ATENCAO" | "RISCO_OPERACIONAL" | "RISCO_ECONOMICO";
  mensagem: string;
  categoria: "OPERACIONAL" | "ECONOMICO" | "RECORRENCIA";
  valor_observado?: number | null;
  valor_referencia?: number | null;
  desvio_pct?: number | null;
  sugestao?: string | null;
  warnings_relevantes: string[];
  posicao?: number | null;
}

interface DiagnosticoResumo {
  total: number;
  info: number;
  atencao: number;
  risco_operacional: number;
  risco_economico: number;
}

interface DiagnosticoResponse {
  tenant_id: string;
  gerado_em: string;
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  diagnosticos: DiagnosticoItem[];
  ranking: DiagnosticoItem[];
  resumo: DiagnosticoResumo;
  warnings: DiagnosticoWarning[];
  sujeito_reconciliacao: boolean;
  observacao_reconciliacao: string | null;
}

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function formatCurrency(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : currencyFormatter.format(value);
}
function formatDelta(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function severityTone(severidade: DiagnosticoItem["severidade"]) {
  if (severidade === "RISCO_ECONOMICO") {
    return { label: "Risco econômico", variant: "danger" as const };
  }
  if (severidade === "RISCO_OPERACIONAL") {
    return { label: "Risco operacional", variant: "attention" as const };
  }
  if (severidade === "ATENCAO") {
    return { label: "Atenção", variant: "warning" as const };
  }
  return { label: "Info", variant: "info" as const };
}

export default function DiagnosticoOperacionalEconomicoAgricolaPage() {
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

  const { data: safras = [], isLoading: isLoadingSafras, error: safraError } = useQuery<SafraResumo[]>({
    queryKey: ["agricola-diagnostico", "safras", safraScopeId],
    queryFn: () => apiFetch(`/safras${safraScopeId ? `?unidade_produtiva_id=${safraScopeId}` : ""}`),
    enabled: hasProfessionalTier,
  });

  const effectiveSafraId = selectedSafraId || safras[0]?.id || "";

  const { data: productionUnits = [], isLoading: isLoadingProductionUnits } = useQuery<ProductionUnitResumo[]>({
    queryKey: ["agricola-diagnostico", "production-units", effectiveSafraId],
    queryFn: () => apiFetch(`/safras/${effectiveSafraId}/production-units`),
    enabled: hasProfessionalTier && !!effectiveSafraId,
  });

  const diagnosticoParams = useMemo(() => {
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
    data: diagnostico,
    isLoading: isLoadingDiagnostico,
    isError: isErrorDiagnostico,
    error: diagnosticoError,
  } = useQuery<DiagnosticoResponse>({
    queryKey: ["agricola-diagnostico", "v1", diagnosticoParams],
    queryFn: () => apiFetch("/agricola/diagnostico/v1", { params: diagnosticoParams ?? undefined }),
    enabled: hasProfessionalTier && !!diagnosticoParams,
  });

  const periodoLabel =
    diagnostico?.data_inicio || diagnostico?.data_fim
      ? `${diagnostico?.data_inicio ? new Intl.DateTimeFormat("pt-BR").format(new Date(diagnostico.data_inicio)) : "—"} → ${diagnostico?.data_fim ? new Intl.DateTimeFormat("pt-BR").format(new Date(diagnostico.data_fim)) : "—"}`
      : "Sem recorte temporal";

  const topInsights = useMemo(() => diagnostico?.ranking.slice(0, 3) ?? [], [diagnostico?.ranking]);

  if (!hasProfessionalTier) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <PageHeader
          title="Diagnóstico Operacional e Econômico"
          description="Leitura oficial assistida derivada da DRE agrícola v1."
          breadcrumbs={[
            { label: "Agrícola", href: "/dashboard/agricola" },
            { label: "Diagnóstico Operacional e Econômico" },
          ]}
          icon={<ShieldAlert className="size-5" />}
        />
        <TierUpgradeCard
          title="Diagnóstico agrícola disponível no PROFISSIONAL"
          description="A visão oficial de diagnóstico reutiliza DRE agrícola v1, rentabilidade oficial, eficiência operacional oficial e benchmark oficial."
          requiredTier="PROFISSIONAL"
          feature="agricola.diagnostico_v1"
          surface="agricola.diagnostico.page"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Diagnóstico Operacional e Econômico"
        description="Diagnósticos oficiais de desvio operacional e econômico derivados exclusivamente da DRE agrícola v1 e dos analytics oficiais."
        breadcrumbs={[
          { label: "Agrícola", href: "/dashboard/agricola" },
          { label: "DRE Agrícola v1", href: "/dashboard/agricola/dre" },
          { label: "Diagnóstico Operacional e Econômico" },
        ]}
        actions={(
          <Button asChild variant="outline" size="sm" className="rounded-sm">
            <Link href="/dashboard/agricola/benchmark">
              <LineChart className="size-4" />
              Abrir benchmark
            </Link>
          </Button>
        )}
        icon={<ShieldAlert className="size-5" />}
      />

      <Alert className="rounded-sm">
        <AlertCircle className="size-4" />
        <AlertTitle>Leitura oficial</AlertTitle>
        <AlertDescription>
          O diagnóstico consome DREAgricolaV1Service, AgricolaDreKpiService, RentabilidadeService, EficienciaOperacionalService e BenchmarkService já consolidados. Não há recálculo fora da DRE.
        </AlertDescription>
      </Alert>

      {diagnostico?.sujeito_reconciliacao && (
        <Alert className="rounded-sm border-amber-200 bg-amber-50/70 text-amber-950">
          <AlertCircle className="size-4" />
          <AlertTitle>Reconciliação pendente</AlertTitle>
          <AlertDescription>Diagnósticos sujeitos à reconciliação.</AlertDescription>
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
              <label id="diagnostico-safra-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                <SelectTrigger aria-labelledby="diagnostico-safra-label" data-testid="diagnostico-safra-select">
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
              <label id="diagnostico-unidade-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                <SelectTrigger aria-labelledby="diagnostico-unidade-label" data-testid="diagnostico-unidade-produtiva-select">
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
              <label id="diagnostico-production-unit-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                ProductionUnit
              </label>
              <Select
                value={selectedProductionUnitId}
                onValueChange={setSelectedProductionUnitId}
                disabled={isLoadingProductionUnits || productionUnits.length === 0}
              >
                <SelectTrigger aria-labelledby="diagnostico-production-unit-label" data-testid="diagnostico-production-unit-select">
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
                <label htmlFor="diagnostico-data-inicio" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data inicial
                </label>
                <Input id="diagnostico-data-inicio" data-testid="diagnostico-data-inicio" type="date" value={dataInicio} onChange={(event) => setDataInicio(event.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="diagnostico-data-fim" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data final
                </label>
                <Input id="diagnostico-data-fim" data-testid="diagnostico-data-fim" type="date" value={dataFim} onChange={(event) => setDataFim(event.target.value)} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoadingDiagnostico ? (
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
          <StatCard color="agro" icon={AlertTriangle} label="Riscos econômicos" value={String(diagnostico?.resumo.risco_economico ?? 0)} subtitle="Desvios governados" />
          <StatCard color="operacional" icon={TrendingDown} label="Riscos operacionais" value={String(diagnostico?.resumo.risco_operacional ?? 0)} subtitle="Desvios governados" />
          <StatCard color="warning" icon={TrendingUp} label="Atenções" value={String(diagnostico?.resumo.atencao ?? 0)} subtitle={periodoLabel} />
          <StatCard color="primary" icon={BarChart3} label="Total de diagnósticos" value={String(diagnostico?.resumo.total ?? 0)} subtitle="Leitura assistida" />
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-3">
        {topInsights.map((item, index) => {
          const tone = severityTone(item.severidade);
          return (
            <Card key={`${item.codigo}-${item.id}-${index}`} className="rounded-sm shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Badge variant={tone.variant} className="rounded-sm">{tone.label}</Badge>
                  {item.titulo}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm font-semibold">{item.label}</p>
                <p className="text-xs text-muted-foreground">{item.mensagem}</p>
                <p className="text-xs text-muted-foreground">
                  Observado: {formatCurrency(item.valor_observado)} | Referência: {formatCurrency(item.valor_referencia)} | Desvio: {formatDelta(item.desvio_pct)}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Search className="size-4 text-muted-foreground" />
            Lista leve de insights
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {diagnostico?.diagnosticos?.length ? (
            diagnostico.diagnosticos.map((item) => {
              const tone = severityTone(item.severidade);
              return (
                <div key={`${item.codigo}-${item.id}-${item.posicao ?? item.label}`} className="rounded-sm border p-4 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={tone.variant} className="rounded-sm">{tone.label}</Badge>
                      <Badge variant="outline" className="rounded-sm">
                        {item.scope}
                      </Badge>
                    </div>
                    <p className="text-sm font-bold">{item.titulo}</p>
                    <p className="text-sm text-muted-foreground">{item.label}</p>
                    <p className="text-sm">{item.mensagem}</p>
                    {item.sugestao && <p className="text-xs text-muted-foreground">Sugestão: {item.sugestao}</p>}
                  </div>
                  <div className="text-xs text-muted-foreground md:text-right space-y-1">
                    <p className="font-semibold text-foreground">#{item.posicao ?? "—"}</p>
                    <p>Observado: {formatCurrency(item.valor_observado)}</p>
                    <p>Referência: {formatCurrency(item.valor_referencia)}</p>
                    <p>Desvio: {formatDelta(item.desvio_pct)}</p>
                  </div>
                </div>
              );
            })
          ) : (
            <EmptyState
              icon={<ShieldAlert />}
              title="Nenhum diagnóstico relevante"
              description="No recorte selecionado, a leitura governada não encontrou desvios acima do limiar oficial."
            />
          )}
        </CardContent>
      </Card>

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="size-4 text-muted-foreground" />
            Ranking simples de desvios
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isErrorDiagnostico ? (
            <div className="p-6">
              <EmptyState
                icon={<BarChart3 />}
                title="Não foi possível carregar o diagnóstico"
                description={(diagnosticoError as Error)?.message || (safraError as Error)?.message || "Verifique o recorte selecionado e tente novamente."}
              />
            </div>
          ) : diagnostico?.ranking?.length ? (
            <div className="overflow-x-auto">
              <Table data-testid="diagnostico-ranking-table">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Pos.</TableHead>
                    <TableHead>Severidade</TableHead>
                    <TableHead>Scope</TableHead>
                    <TableHead>Insight</TableHead>
                    <TableHead>Mensagem</TableHead>
                    <TableHead>Observado</TableHead>
                    <TableHead>Referência</TableHead>
                    <TableHead>Desvio</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {diagnostico.ranking.map((item) => {
                    const tone = severityTone(item.severidade);
                    return (
                      <TableRow key={`${item.codigo}-${item.id}-${item.posicao ?? item.label}`}>
                        <TableCell className="font-semibold tabular-nums">{item.posicao ?? "—"}</TableCell>
                        <TableCell>
                          <Badge variant={tone.variant} className="rounded-sm">{tone.label}</Badge>
                        </TableCell>
                        <TableCell>{item.scope}</TableCell>
                        <TableCell className="font-medium">{item.titulo}</TableCell>
                        <TableCell className="max-w-md text-muted-foreground">{item.mensagem}</TableCell>
                        <TableCell className="tabular-nums">{formatCurrency(item.valor_observado)}</TableCell>
                        <TableCell className="tabular-nums">{formatCurrency(item.valor_referencia)}</TableCell>
                        <TableCell className="tabular-nums">{formatDelta(item.desvio_pct)}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="p-6">
              <EmptyState
                icon={<ShieldAlert />}
                title="Sem ranking disponível"
                description="A leitura oficial não encontrou desvios classificáveis para o recorte selecionado."
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
