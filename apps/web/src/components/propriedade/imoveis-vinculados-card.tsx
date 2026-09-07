"use client";

import Link from "next/link";
import { AlertTriangle, ArrowUpRight, Home, Link2, MapPinned } from "lucide-react";

import { usePermission } from "@/hooks/use-permission";
import { useVisaoTerritorial } from "@/lib/hooks/use-territorial-visao";
import { cn } from "@/lib/utils";
import type { TerritoryReadView } from "@/types/global";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/empty-state";
import { buildLinkedImoveisViewModel } from "./imoveis-vinculados-view-model";

function formatArea(value: string | number | null) {
  if (value === null || value === undefined || value === "") return "—";
  const numericValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numericValue)) return "—";
  return `${numericValue.toLocaleString("pt-BR", { maximumFractionDigits: 4 })} ha`;
}

function formatEnumLabel(value?: string | null) {
  if (!value) return "—";
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

function buildImovelModuleHref(unidadeProdutivaId: string) {
  return `/cadastros/imoveis?unidade_produtiva_id=${encodeURIComponent(unidadeProdutivaId)}`;
}

function buildTerritorialHref(unidadeProdutivaId: string) {
  return `/cadastros/propriedades/${unidadeProdutivaId}/visao-territorial`;
}

function buildImovelHref(imovelId: string) {
  return `/cadastros/imoveis/${imovelId}/visao-fundiaria`;
}

export function ImoveisVinculadosCard({
  unidadeProdutivaId,
  territory,
  title = "Imóveis Rurais Vinculados",
  description = "Documentos, áreas oficiais e dados fundiários são mantidos no cadastro de cada Imóvel Rural.",
  compact = false,
  className,
}: {
  unidadeProdutivaId?: string;
  territory?: TerritoryReadView | null;
  title?: string;
  description?: string;
  compact?: boolean;
  className?: string;
}) {
  const canCreateImovel = usePermission("tenant:imoveis:create");
  const { data: visaoTerritorial } = useVisaoTerritorial(unidadeProdutivaId ?? "");
  const model = buildLinkedImoveisViewModel(territory, visaoTerritorial);

  return (
    <Card className={cn("rounded-sm shadow-sm", className)}>
      <CardHeader className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          {unidadeProdutivaId ? (
            <Button size="sm" variant="outline" asChild className="shrink-0 rounded-sm">
              <Link href={buildTerritorialHref(unidadeProdutivaId)}>
                Ver vínculos
                <ArrowUpRight className="size-3.5" />
              </Link>
            </Button>
          ) : null}
        </div>
        {model.hasAmbiguity ? (
          <div className="flex items-start gap-2 rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-800/30 dark:bg-amber-950/20 dark:text-amber-300">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
            <span>Há vários imóveis vinculados e nenhum está marcado como principal. A operação não escolhe um imóvel automaticamente.</span>
          </div>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-4">
        {model.items.length === 0 ? (
          <div className="rounded-sm border border-dashed bg-muted/10 py-10">
            <EmptyState
              icon={<Home />}
              title="Nenhum Imóvel Rural vinculado."
              description="Cadastre ou vincule um imóvel para manter documentos, áreas oficiais e dados fundiários fora da edição operacional."
              secondaryAction={{
                label: "Vincular imóvel existente",
                href: unidadeProdutivaId ? buildTerritorialHref(unidadeProdutivaId) : undefined,
              }}
              className="border-0 bg-transparent py-0"
            />
            <div className="mt-4 flex flex-wrap justify-center gap-2 px-4">
              {canCreateImovel && unidadeProdutivaId ? (
                <Button size="sm" variant="outline" asChild className="rounded-sm">
                  <Link href={buildImovelModuleHref(unidadeProdutivaId)}>
                    <MapPinned className="size-3.5" />
                    Cadastrar Imóvel Rural
                  </Link>
                </Button>
              ) : (
                <Button size="sm" variant="outline" disabled className="rounded-sm">
                  <MapPinned className="size-3.5" />
                  Cadastrar Imóvel Rural
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className={cn("grid gap-3", compact ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-2")}>
            {model.items.map((item) => {
              const municipioUf = [item.municipio, item.uf].filter(Boolean).join(" / ");
              return (
                <div key={item.id} className="rounded-sm border bg-muted/20 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-foreground">{item.nome}</p>
                      <p className="text-xs text-muted-foreground">
                        {municipioUf || "Município oficial não informado"}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {item.principal ? (
                        <Badge className="rounded-sm text-[10px] uppercase">Principal</Badge>
                      ) : null}
                      {item.tipoVinculo ? (
                        <Badge variant="outline" className="rounded-sm text-[10px] uppercase">
                          {formatEnumLabel(item.tipoVinculo)}
                        </Badge>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-muted-foreground">Matrícula</p>
                      <p>{item.matricula || "—"}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-muted-foreground">CAR</p>
                      <p>{item.car || "—"}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-muted-foreground">Área oficial</p>
                      <p>{formatArea(item.areaTotalHa)}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-muted-foreground">Status documental</p>
                      <p>{item.statusDocumental ? formatEnumLabel(item.statusDocumental) : "Não informado"}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-muted-foreground">Área vinculada</p>
                      <p>{formatArea(item.areaVinculada)}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-muted-foreground">Percentual vinculado</p>
                      <p>{item.percentualVinculado ? `${item.percentualVinculado}%` : "—"}</p>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" asChild className="rounded-sm">
                      <Link href={buildImovelHref(item.id)}>
                        Abrir Imóvel Rural
                        <ArrowUpRight className="size-3.5" />
                      </Link>
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {unidadeProdutivaId ? (
          <div className="flex flex-wrap gap-2 border-t pt-2">
            {canCreateImovel ? (
              <Button size="sm" variant="outline" asChild className="rounded-sm">
                <Link href={buildImovelModuleHref(unidadeProdutivaId)}>
                  <MapPinned className="size-3.5" />
                  Cadastrar Imóvel Rural
                </Link>
              </Button>
            ) : (
              <Button size="sm" variant="outline" disabled className="rounded-sm">
                <MapPinned className="size-3.5" />
                Cadastrar Imóvel Rural
              </Button>
            )}
            <Button size="sm" variant="outline" asChild className="rounded-sm">
              <Link href={buildTerritorialHref(unidadeProdutivaId)}>
                <Link2 className="size-3.5" />
                Vincular imóvel existente
              </Link>
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
