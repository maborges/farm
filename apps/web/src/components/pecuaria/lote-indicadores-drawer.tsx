"use client";

import * as React from "react";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  BarChart3,
  CalendarDays,
  DollarSign,
  MapPin,
  RefreshCw,
  Scale,
  TrendingUp,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";

import { fetchLoteIndicadores, type LoteIndicadores } from "@/lib/pecuaria/lotes-api";
import { formatCurrency } from "@/lib/utils";

type LoteIndicadoresDrawerProps = {
  open: boolean;
  loteId: string | null;
  loteNome?: string | null;
  onOpenChange: (open: boolean) => void;
};

const numberFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

function formatKg(value: number | null | undefined) {
  if (value == null) return "—";
  return `${numberFormatter.format(value)} kg`;
}

function formatArrobas(value: number | null | undefined) {
  if (value == null) return "—";
  return `${numberFormatter.format(value)} @`;
}

function formatGmd(value: number | null | undefined) {
  if (value == null) return "GMD indisponível";
  return `${numberFormatter.format(value)} kg/dia`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString("pt-BR");
}

function MetricCard({
  icon,
  title,
  value,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  value: React.ReactNode;
  description?: string;
}) {
  return (
    <Card size="sm" className="border-border-subtle rounded-sm shadow-none">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
            {icon}
          </div>
          <div className="min-w-0">
            <CardDescription className="text-xs uppercase tracking-wide">{title}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <CardTitle className="text-xl font-semibold tabular-nums">{value}</CardTitle>
        {description ? <p className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
      </CardContent>
    </Card>
  );
}

function MetricSkeleton() {
  return (
    <Card size="sm" className="border-border-subtle rounded-sm shadow-none">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <Skeleton className="size-8 rounded-sm" />
          <Skeleton className="h-3 w-24 rounded-sm" />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <Skeleton className="h-7 w-32 rounded-sm" />
        <Skeleton className="mt-2 h-3 w-40 rounded-sm" />
      </CardContent>
    </Card>
  );
}

export function LoteIndicadoresDrawer({
  open,
  loteId,
  loteNome,
  onOpenChange,
}: LoteIndicadoresDrawerProps) {
  const { data, isLoading, isError, refetch } = useQuery<LoteIndicadores>({
    queryKey: ["pecuaria", "lotes", loteId, "indicadores"],
    queryFn: () => {
      if (!loteId) throw new Error("Lote não informado.");
      return fetchLoteIndicadores(loteId);
    },
    enabled: open && Boolean(loteId),
  });

  const nomeExibicao = data?.nome_lote ?? loteNome ?? "Lote pecuário";
  const margemPositiva = (data?.margem_bruta_estimada ?? 0) >= 0;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto p-0 sm:max-w-3xl">
        <SheetHeader className="border-b px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <BarChart3 size={18} />
            </div>
            <div className="min-w-0">
              <SheetTitle className="truncate text-lg font-semibold">Indicadores do Lote</SheetTitle>
              <SheetDescription className="truncate">{nomeExibicao}</SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="space-y-6 px-6 py-5">
          {isLoading ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 12 }).map((_, index) => (
                <MetricSkeleton key={index} />
              ))}
            </div>
          ) : isError ? (
            <Card className="border-destructive/20 bg-destructive/5 rounded-sm shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-destructive">
                  Não foi possível carregar os indicadores
                </CardTitle>
                <CardDescription>
                  Verifique a conexão com a API e tente novamente.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" size="sm" className="rounded-sm" onClick={() => refetch()}>
                  <RefreshCw className="size-3.5 mr-1.5" />
                  Tentar novamente
                </Button>
              </CardContent>
            </Card>
          ) : data ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={data.modo_gestao === "INDIVIDUAL" ? "default" : "secondary"} className="rounded-sm">
                  {data.modo_gestao === "INDIVIDUAL" ? "Gestão Individual" : "Gestão por Lote"}
                </Badge>
                <Badge variant="outline" className="rounded-sm">
                  Rendimento de carcaça: {numberFormatter.format(data.rendimento_carcaca_pct)}%
                </Badge>
                <Badge variant="outline" className="rounded-sm">
                  Cabeças ativas: {data.quantidade_animais.toLocaleString("pt-BR")}
                </Badge>
                <Badge variant="outline" className="rounded-sm">
                  GMD: {formatGmd(data.gmd_medio_kg_dia)}
                </Badge>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Desempenho Zootécnico e Pastagem
                </h4>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  <MetricCard
                    icon={<Users size={16} />}
                    title="Cabeças Ativas"
                    value={data.quantidade_animais.toLocaleString("pt-BR")}
                  />
                  <MetricCard
                    icon={<Scale size={16} />}
                    title="Peso Vivo Total / Médio"
                    value={formatKg(data.peso_total_kg)}
                    description={`Média: ${formatKg(data.peso_medio_kg)} por cabeça`}
                  />
                  <MetricCard
                    icon={<Activity size={16} />}
                    title="Arrobas Totais / Produzidas"
                    value={formatArrobas(data.arrobas_totais)}
                    description={`Produzidas: ${formatArrobas(data.arrobas_produzidas)}`}
                  />
                  <MetricCard
                    icon={<Activity size={16} />}
                    title="GMD Médio"
                    value={formatGmd(data.gmd_medio_kg_dia)}
                  />
                  <MetricCard
                    icon={<CalendarDays size={16} />}
                    title="Última Pesagem"
                    value={formatDate(data.ultima_pesagem)}
                  />
                  <MetricCard
                    icon={<MapPin size={16} />}
                    title="Lotação / Produtividade"
                    value={`${numberFormatter.format(data.lotacao_ua_ha)} UA/ha`}
                    description={`${numberFormatter.format(data.arrobas_por_hectare)} @/ha em ${numberFormatter.format(data.area_piquete_ha)} ha`}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Custos Reais e Ponto de Equilíbrio
                </h4>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  <MetricCard
                    icon={<DollarSign size={16} />}
                    title="Investimento Aquisição"
                    value={formatCurrency(data.custo_aquisicao_total)}
                  />
                  <MetricCard
                    icon={<DollarSign size={16} />}
                    title="Custo Sanitário"
                    value={formatCurrency(data.custo_sanitario_total)}
                    description={`${formatCurrency(data.custo_sanitario_por_cabeca)}/cab · ${formatCurrency(data.custo_sanitario_por_arroba)}/@`}
                  />
                  <MetricCard
                    icon={<DollarSign size={16} />}
                    title="Custo Nutrição & Outros"
                    value={formatCurrency(data.custo_nutricao_total + data.custo_outros_total)}
                    description={`Nutrição: ${formatCurrency(data.custo_nutricao_total)} · Outros: ${formatCurrency(data.custo_outros_total)}`}
                  />
                  <MetricCard
                    icon={<DollarSign size={16} />}
                    title="Custo Operacional Total"
                    value={formatCurrency(data.custo_total_operacional)}
                    description={`${formatCurrency(data.custo_total_por_arroba)} por @ total`}
                  />
                  <MetricCard
                    icon={<DollarSign size={16} />}
                    title="Custo / @ Produzida"
                    value={formatCurrency(data.custo_por_arroba_produzida)}
                    description="Operacional sobre o ganho no período."
                  />
                  <MetricCard
                    icon={<Scale size={16} />}
                    title="Break-even (R$/@)"
                    value={formatCurrency(data.custo_break_even_por_arroba)}
                    description="Preço mínimo da @ para cobrir aquisição + custos."
                  />
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Valor de Mercado e Margem Estimada
                </h4>
                <div className="grid gap-3 sm:grid-cols-3">
                  <MetricCard
                    icon={<TrendingUp size={16} />}
                    title="Cotação de Referência"
                    value={
                      data.cotacao_arroba_referencia != null
                        ? `${formatCurrency(data.cotacao_arroba_referencia)}/@`
                        : "Indisponível"
                    }
                    description={
                      data.fonte_cotacao ? `Fonte: ${data.fonte_cotacao}` : "Sem cotação ativa"
                    }
                  />
                  <MetricCard
                    icon={<DollarSign size={16} />}
                    title="Valor de Mercado Estimado"
                    value={
                      data.valor_mercado_estimado != null
                        ? formatCurrency(data.valor_mercado_estimado)
                        : "—"
                    }
                  />
                  <MetricCard
                    icon={<DollarSign size={16} />}
                    title="Margem Bruta Estimada"
                    value={
                      <span className={margemPositiva ? "text-emerald-600 dark:text-emerald-400" : "text-destructive"}>
                        {data.margem_bruta_estimada != null
                          ? formatCurrency(data.margem_bruta_estimada)
                          : "—"}
                      </span>
                    }
                    description={
                      data.margem_estimada_por_cabeca != null
                        ? `${formatCurrency(data.margem_estimada_por_cabeca)} por cabeça`
                        : undefined
                    }
                  />
                </div>
              </div>
            </>
          ) : (
            <Card className="border-border-subtle bg-muted/20 rounded-sm shadow-none">
              <CardContent className="py-6 text-sm text-muted-foreground">
                Selecione um lote para visualizar seus indicadores.
              </CardContent>
            </Card>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
