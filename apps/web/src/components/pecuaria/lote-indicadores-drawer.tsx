"use client"

import * as React from "react"
import { useQuery } from "@tanstack/react-query"
import { CalendarDays, BarChart3, DollarSign, Scale, Users, Activity } from "lucide-react"

import { apiFetch } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

export type LoteIndicadores = {
  lote_id: string
  nome_lote: string
  quantidade_animais: number
  peso_total_kg: number | null
  peso_medio_kg: number | null
  gmd_medio_kg_dia: number | null
  ultima_pesagem: string | null
  custo_sanitario_total: number | null
  custo_sanitario_por_cabeca: number | null
  custo_sanitario_por_kg: number | null
  custo_sanitario_por_arroba: number | null
  custo_aquisicao_total: number | null
}

type LoteIndicadoresDrawerProps = {
  open: boolean
  loteId: string | null
  loteNome?: string | null
  onOpenChange: (open: boolean) => void
}

const numberFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

function formatKg(value: number | null | undefined) {
  if (value == null) return "—"
  return `${numberFormatter.format(value)} kg`
}

function formatGmd(value: number | null | undefined) {
  if (value == null) return "GMD indisponível"
  return `${numberFormatter.format(value)} kg/dia`
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleDateString("pt-BR")
}

function MetricCard({
  icon,
  title,
  value,
  description,
}: {
  icon: React.ReactNode
  title: string
  value: React.ReactNode
  description?: string
}) {
  return (
    <Card size="sm" className="border-border-subtle shadow-none">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
            {icon}
          </div>
          <div className="min-w-0">
            <CardDescription className="text-xs uppercase tracking-wide">
              {title}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <CardTitle className="text-xl font-semibold tabular-nums">
          {value}
        </CardTitle>
        {description ? (
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        ) : null}
      </CardContent>
    </Card>
  )
}

function MetricSkeleton() {
  return (
    <Card size="sm" className="border-border-subtle shadow-none">
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
  )
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
      if (!loteId) {
        throw new Error("Lote não informado.")
      }
      return apiFetch(`/pecuaria/lotes/${loteId}/indicadores`)
    },
    enabled: open && Boolean(loteId),
  })

  const nomeExibicao = data?.nome_lote ?? loteNome ?? "Lote pecuário"

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto p-0 sm:max-w-3xl">
        <SheetHeader className="border-b px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <BarChart3 size={18} />
            </div>
            <div className="min-w-0">
              <SheetTitle className="truncate text-lg font-semibold">
                Indicadores do Lote
              </SheetTitle>
              <SheetDescription className="truncate">
                {nomeExibicao}
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="space-y-6 px-6 py-5">
          {isLoading ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 10 }).map((_, index) => (
                <MetricSkeleton key={index} />
              ))}
            </div>
          ) : isError ? (
            <Card className="border-destructive/20 bg-destructive/5 shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-destructive">
                  Não foi possível carregar os indicadores
                </CardTitle>
                <CardDescription>
                  Verifique a conexão com a API e tente novamente.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" size="sm" onClick={() => refetch()}>
                  Tentar novamente
                </Button>
              </CardContent>
            </Card>
          ) : data ? (
            <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                <MetricCard
                  icon={<Users size={16} />}
                  title="Quantidade de animais"
                  value={data.quantidade_animais.toLocaleString("pt-BR")}
                />
                <MetricCard
                  icon={<Scale size={16} />}
                  title="Peso total"
                  value={formatKg(data.peso_total_kg)}
                />
                <MetricCard
                  icon={<Scale size={16} />}
                  title="Peso médio"
                  value={formatKg(data.peso_medio_kg)}
                />
                <MetricCard
                  icon={<Activity size={16} />}
                  title="GMD médio"
                  value={formatGmd(data.gmd_medio_kg_dia)}
                />
                <MetricCard
                  icon={<CalendarDays size={16} />}
                  title="Última pesagem"
                  value={formatDate(data.ultima_pesagem)}
                />
                <MetricCard
                  icon={<DollarSign size={16} />}
                  title="Custo sanitário total"
                  value={formatCurrency(data.custo_sanitario_total ?? 0)}
                />
                <MetricCard
                  icon={<DollarSign size={16} />}
                  title="Custo por cabeça"
                  value={formatCurrency(data.custo_sanitario_por_cabeca ?? 0)}
                />
                <MetricCard
                  icon={<DollarSign size={16} />}
                  title="Custo por kg"
                  value={formatCurrency(data.custo_sanitario_por_kg ?? 0)}
                />
                <MetricCard
                  icon={<DollarSign size={16} />}
                  title="Custo por arroba (@)"
                  value={formatCurrency(data.custo_sanitario_por_arroba ?? 0)}
                  description="Valor sanitário agregado por arroba."
                />
                <MetricCard
                  icon={<DollarSign size={16} />}
                  title="Custo inicial"
                  value={formatCurrency(data.custo_aquisicao_total ?? 0)}
                  description="Valor de aquisição dos animais ativos do lote."
                />
              </div>

              <Card className="border-border-subtle bg-muted/20 shadow-none">
                <CardContent className="flex flex-wrap items-center gap-2 py-4">
                  <Badge variant="outline">Lote ID: {data.lote_id}</Badge>
                  <Badge variant="outline">
                    Animais ativos: {data.quantidade_animais.toLocaleString("pt-BR")}
                  </Badge>
                  <Badge variant="outline">
                    GMD: {data.gmd_medio_kg_dia == null ? "indisponível" : `${numberFormatter.format(data.gmd_medio_kg_dia)} kg/dia`}
                  </Badge>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="border-border-subtle bg-muted/20 shadow-none">
              <CardHeader>
                <CardTitle className="text-base">Nenhum indicador disponível</CardTitle>
                <CardDescription>
                  Selecione um lote para carregar o resumo econômico e zootécnico.
                </CardDescription>
              </CardHeader>
            </Card>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
