"use client";

import { useMemo, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Layers, MapPin, Maximize2, Scale } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";

export interface PiqueteArea {
  id: string;
  nome: string;
  tipo: string;
  area_hectares: number | null;
  area_hectares_manual?: number | null;
  ativo: boolean;
  dados_extras?: {
    capacidade_suporte_ua?: number | null;
  } | null;
}

export interface AreaRuralOption {
  id: string;
  nome: string;
  tipo: string;
}

function ResumoCard({
  title,
  value,
  description,
  icon: Icon,
  tone = "default",
}: {
  title: string;
  value: string | number;
  description: string;
  icon: typeof MapPin;
  tone?: "default" | "success" | "warning";
}) {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</div>
            <div className="text-2xl font-semibold leading-none">{value}</div>
            <div className="text-xs text-muted-foreground">{description}</div>
          </div>
          <div
            className={cn(
              "flex size-10 items-center justify-center rounded-sm border",
              tone === "success" && "border-emerald-200 bg-emerald-50 text-emerald-700",
              tone === "warning" && "border-amber-200 bg-amber-50 text-amber-700",
              tone === "default" && "border-primary/20 bg-primary/5 text-primary"
            )}
          >
            <Icon className="size-4" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PiqueteSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <Card key={index} className="rounded-sm shadow-sm">
          <CardContent className="space-y-4 p-5">
            <div className="flex items-start justify-between">
              <Skeleton className="size-10 rounded-sm" />
              <Skeleton className="h-6 w-16 rounded-sm" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-5 w-2/3 rounded-sm" />
              <Skeleton className="h-4 w-1/2 rounded-sm" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Skeleton className="h-16 rounded-sm" />
              <Skeleton className="h-16 rounded-sm" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: value % 1 === 0 ? 0 : 1,
    maximumFractionDigits: 1,
  }).format(value);
}

export function PiquetesClient({
  initialData = [],
  initialAreas = [],
  initialActiveFazendaId,
}: {
  initialData?: PiqueteArea[];
  initialAreas?: AreaRuralOption[];
  initialActiveFazendaId?: string;
}) {
  const { activeFazendaId } = useAppStore();
  const router = useRouter();

  const { data: piquetes = [], isLoading } = useQuery<PiqueteArea[]>({
    queryKey: ["piquetes", activeFazendaId],
    queryFn: () => apiFetch<PiqueteArea[]>(`/cadastros/areas-rurais?tipo=PIQUETE&unidade_produtiva_id=${activeFazendaId}`),
    enabled: Boolean(activeFazendaId),
    initialData: activeFazendaId === initialActiveFazendaId ? initialData : undefined,
  });

  const resumo = useMemo(() => {
    const ativos = piquetes.filter((item) => item.ativo);
    const areaTotal = ativos.reduce((sum, item) => sum + Number(item.area_hectares ?? item.area_hectares_manual ?? 0), 0);
    const capacidadeTotal = ativos.reduce(
      (sum, item) => sum + Number(item.dados_extras?.capacidade_suporte_ua || 0),
      0
    );

    return {
      total: piquetes.length,
      ativos: ativos.length,
      areaTotal,
      capacidadeTotal,
    };
  }, [piquetes]);

  const columns = useMemo<ColumnDef<PiqueteArea>[]>(() => [
    {
      id: "nome",
      header: "Nome",
      accessorKey: "nome",
      cell: (value) => (
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-sm bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0 ring-1 ring-emerald-200">
            <MapPin className="size-4" />
          </div>
          <span className="font-medium">{value as string}</span>
        </div>
      ),
    },
    {
      id: "area_hectares",
      header: "Área (ha)",
      accessorFn: (row) => row.area_hectares ?? row.area_hectares_manual,
      cell: (value) => (value ? `${formatNumber(Number(value))} ha` : "—"),
    },
    {
      id: "capacidade",
      header: "Capacidade (UA)",
      accessorFn: (row) => row.dados_extras?.capacidade_suporte_ua,
      cell: (value) => (value ? `${formatNumber(Number(value))} UA` : "—"),
    },
    {
      id: "ativo",
      header: "Status",
      accessorKey: "ativo",
      cell: (value) => (
        <Badge
          variant="outline"
          className={cn(
            value
              ? "border-emerald-200 bg-emerald-50 text-emerald-700 rounded-sm"
              : "border-rose-200 bg-rose-50 text-rose-700 rounded-sm"
          )}
        >
          {value ? "Ativo" : "Inativo"}
        </Badge>
      ),
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: () => (
          <div className="flex items-center gap-0 justify-end">
          </div>
      )
    }
  ], []);

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Piquetes & Pastagens"
        description="Consulta zootécnica das subdivisões de pastejo cadastradas em Propriedades."
        icon={<MapPin className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Pecuária", href: "/dashboard/pecuaria" },
          { label: "Piquetes" },
        ]}
        actions={
          <Button
            size="sm"
            variant="outline"
            className="rounded-sm"
            onClick={() => router.push("/cadastros/propriedades")}
          >
            <MapPin className="size-3.5 mr-1.5" />
            Gerenciar Estrutura em Propriedades
          </Button>
        }
      />

      {!activeFazendaId ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<MapPin />}
              title="Selecione uma fazenda para visualizar os piquetes"
              description="A listagem e o cadastro dependem do contexto da unidade produtiva ativa."
            />
          </CardContent>
        </Card>
      ) : null}

      {activeFazendaId ? (
        <>
          {!isLoading && piquetes.length === 0 ? (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-6">
                <EmptyState
                  icon={<MapPin />}
                  title="Nenhum piquete cadastrado para esta fazenda."
                  description="Cadastre as áreas e subdivisões de pastagem (tipo PIQUETE) em Propriedades para acompanhar aqui a lotação e a capacidade de suporte."
                  action={{
                    label: "Gerenciar Estrutura em Propriedades",
                    onClick: () => router.push("/cadastros/propriedades"),
                  }}
                />
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <ResumoCard
                  title="Piquetes ativos"
                  value={resumo.ativos}
                  description={`${resumo.total} cadastrado(s) no total`}
                  icon={Layers}
                />
                <ResumoCard
                  title="Área total"
                  value={`${formatNumber(resumo.areaTotal)} ha`}
                  description="Soma das áreas ativas"
                  icon={Maximize2}
                  tone="success"
                />
                <ResumoCard
                  title="Capacidade suporte"
                  value={formatNumber(resumo.capacidadeTotal)}
                  description="UA estimada em piquetes ativos"
                  icon={Scale}
                  tone="warning"
                />
              </div>

              <Card className="shadow-sm">
                <CardHeader className="border-b">
                  <CardTitle>Lista de Piquetes</CardTitle>
                  <CardDescription>
                    Consulte os piquetes e pastagens cadastrados nesta Área Operacional.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-4">
                  <DataTable
                    columns={columns}
                    data={piquetes}
                    isLoading={isLoading}
                    searchable={true}
                    searchPlaceholder="Buscar piquete..."
                    exportable={true}
                    exportFileName="piquetes_export"
                    emptyMessage="Nenhum piquete cadastrado ou encontrado."
                  />
                </CardContent>
              </Card>
            </>
          )}
        </>
      ) : null}
    </div>
  );
}
