"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    AlertTriangle,
    Calendar,
    CheckCircle2,
    Eye,
    Info,
    Layers,
    Maximize2,
    Plus,
    RefreshCw,
    Satellite,
} from "lucide-react";

import { NdviTalhao } from "@/components/agricola/ndvi-talhao";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";
import { NdviMapView } from "./NdviMapView";
import {
    formatNdviVariation,
    getNdviStatusBadgeVariant,
    type AreaProdutivaGeo,
    type NDVIResumoPropriedade,
    type NDVITalhaoResumo,
    type NdviTalhaoOption,
} from "./ndvi-view-model";

type PeriodoFiltro = "30" | "90" | "180" | "all";

function formatDataBr(isoDate: string | null): string {
    if (!isoDate) return "—";
    return format(new Date(isoDate + "T12:00:00"), "dd/MM/yyyy", { locale: ptBR });
}

function buildResumoQueryPath(
    activeFazendaId: string | null,
    isVisaoGrupo: boolean,
    periodo: PeriodoFiltro,
): string {
    const params = new URLSearchParams();
    if (!isVisaoGrupo && activeFazendaId) {
        params.set("unidade_produtiva_id", activeFazendaId);
    }
    if (periodo !== "all") {
        params.set("periodo_dias", periodo);
    }
    const qs = params.toString();
    return qs ? `/ndvi/resumo?${qs}` : "/ndvi/resumo";
}

function buildAreasQueryPath(activeFazendaId: string | null, isVisaoGrupo: boolean): string {
    const params = new URLSearchParams({ apenas_produtivas: "true" });
    if (!isVisaoGrupo && activeFazendaId) {
        params.set("unidade_produtiva_id", activeFazendaId);
    }
    return `/cadastros/areas-rurais?${params.toString()}`;
}

function NdviDashboardSkeleton() {
    return (
        <div className="space-y-6 p-6">
            <Skeleton className="h-12 w-72 rounded-sm" />
            <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                <Skeleton className="h-[490px] rounded-sm md:col-span-2" />
                <div className="space-y-6">
                    <Skeleton className="h-56 rounded-sm" />
                    <Skeleton className="h-56 rounded-sm" />
                </div>
            </div>
            <Skeleton className="h-64 w-full rounded-sm" />
        </div>
    );
}

export function NdviDashboardClient() {
    const queryClient = useQueryClient();
    const { activeFazendaId, isVisaoGrupo, _hasHydrated } = useAppStore();
    const [periodo, setPeriodo] = useState<PeriodoFiltro>("all");
    const [selectedTalhaoId, setSelectedTalhaoId] = useState<string | null>(null);
    const [manualModalOpen, setManualModalOpen] = useState(false);
    const serieSectionRef = useRef<HTMLDivElement>(null);

    const resumoPath = buildResumoQueryPath(activeFazendaId, isVisaoGrupo, periodo);
    const areasPath = buildAreasQueryPath(activeFazendaId, isVisaoGrupo);

    const {
        data: resumo,
        isLoading: loadingResumo,
        isFetching: fetchingResumo,
        isError: isErrorResumo,
        error: errorResumo,
    } = useQuery<NDVIResumoPropriedade>({
        queryKey: ["ndvi-resumo", activeFazendaId, isVisaoGrupo, periodo],
        queryFn: () => apiFetch(resumoPath),
        enabled: _hasHydrated,
    });

    const {
        data: areas = [],
        isLoading: loadingAreas,
        isError: isErrorAreas,
    } = useQuery<AreaProdutivaGeo[]>({
        queryKey: ["ndvi-areas-produtivas", activeFazendaId, isVisaoGrupo],
        queryFn: () => apiFetch(areasPath),
        enabled: _hasHydrated,
    });

    const talhoesResumo = useMemo(() => resumo?.talhoes ?? [], [resumo?.talhoes]);

    const talhoesOptions = useMemo<NdviTalhaoOption[]>(() => {
        if (talhoesResumo.length > 0) {
            return talhoesResumo.map((t) => ({ id: t.talhao_id, nome: t.talhao_nome }));
        }
        return areas.map((a) => ({ id: a.id, nome: a.nome }));
    }, [talhoesResumo, areas]);

    const effectiveSelectedTalhaoId = useMemo(() => {
        if (selectedTalhaoId && talhoesOptions.some((t) => t.id === selectedTalhaoId)) {
            return selectedTalhaoId;
        }
        return talhoesOptions[0]?.id ?? null;
    }, [selectedTalhaoId, talhoesOptions]);

    const resumoPorTalhao = useMemo(
        () => new Map(talhoesResumo.map((t) => [t.talhao_id, t])),
        [talhoesResumo],
    );

    const handleRefreshAll = useCallback(() => {
        queryClient.invalidateQueries({ queryKey: ["ndvi-resumo"] });
        queryClient.invalidateQueries({ queryKey: ["ndvi-areas-produtivas"] });
        queryClient.invalidateQueries({ queryKey: ["ndvi-serie"] });
        queryClient.invalidateQueries({ queryKey: ["ndvi-imagens"] });
    }, [queryClient]);

    const handleFocusTalhao = useCallback((talhaoId: string) => {
        setSelectedTalhaoId(talhaoId);
        serieSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, []);

    const handleOpenManual = useCallback(() => {
        setManualModalOpen(true);
        serieSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, []);

    const columns = useMemo<ColumnDef<NDVITalhaoResumo>[]>(
        () => [
            {
                id: "talhao_nome",
                header: "Área / Talhão",
                accessorKey: "talhao_nome",
                sortable: true,
            },
            {
                id: "tipo_area",
                header: "Tipo",
                accessorKey: "tipo_area",
                sortable: true,
            },
            {
                id: "area_hectares",
                header: "Área (ha)",
                accessorKey: "area_hectares",
                sortable: true,
                cell: (val) => (val != null ? `${Number(val).toFixed(1)} ha` : "—"),
                exportFormat: (val) => (val != null ? Number(val).toFixed(2) : "—"),
            },
            {
                id: "indice_atual",
                header: "NDVI Atual",
                accessorKey: "indice_atual",
                sortable: true,
                cell: (val) =>
                    val != null ? (
                        <span className="font-mono font-semibold">{Number(val).toFixed(3)}</span>
                    ) : (
                        "—"
                    ),
                exportFormat: (val) => (val != null ? Number(val).toFixed(3) : "—"),
            },
            {
                id: "variacao_pct",
                header: "Variação",
                accessorKey: "variacao_pct",
                sortable: true,
                cell: (val) => {
                    const num = val as number | null;
                    return (
                        <span
                            className={cn(
                                "font-mono font-semibold",
                                num == null
                                    ? "text-muted-foreground"
                                    : num > 0
                                      ? "text-emerald-600 dark:text-emerald-400"
                                      : num < 0
                                        ? "text-red-600 dark:text-red-400"
                                        : "text-muted-foreground",
                            )}
                        >
                            {formatNdviVariation(num)}
                        </span>
                    );
                },
                exportFormat: (val) => formatNdviVariation(val as number | null),
            },
            {
                id: "cobertura_nuvens_pct",
                header: "Nuvens",
                accessorKey: "cobertura_nuvens_pct",
                sortable: true,
                cell: (val) => (val != null ? `${Number(val).toFixed(0)}%` : "—"),
                exportFormat: (val) => (val != null ? `${Number(val).toFixed(0)}%` : "—"),
            },
            {
                id: "ultima_captura",
                header: "Última Leitura",
                accessorKey: "ultima_captura",
                sortable: true,
                cell: (val) => formatDataBr(val as string | null),
                exportFormat: (val) => formatDataBr(val as string | null),
            },
            {
                id: "classificacao",
                header: "Status",
                accessorKey: "classificacao",
                sortable: true,
                cell: (val) => {
                    const label = String(val);
                    return (
                        <Badge variant={getNdviStatusBadgeVariant(label)} className="rounded-sm">
                            {label}
                        </Badge>
                    );
                },
            },
            {
                id: "acoes",
                header: "",
                isActionColumn: true,
                exportable: false,
                cell: (_val, row) => (
                    <div className="flex justify-end gap-0">
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            className="rounded-sm border-0 text-primary hover:bg-primary/10 hover:text-primary"
                            title="Ver série temporal do talhão"
                            aria-label={`Ver série temporal de ${row.talhao_nome}`}
                            onClick={() => handleFocusTalhao(row.talhao_id)}
                        >
                            <Eye className="size-3.5" />
                        </Button>
                    </div>
                ),
            },
        ],
        [handleFocusTalhao],
    );

    if (!_hasHydrated || loadingResumo || loadingAreas) {
        return <NdviDashboardSkeleton />;
    }

    const erroMsg =
        errorResumo instanceof Error && errorResumo.message
            ? errorResumo.message
            : "Não foi possível carregar o monitoramento NDVI.";

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="NDVI & Monitoramento Satelital"
                description="Acompanhe o vigor vegetativo das áreas produtivas com mapa, série temporal e registro manual."
                icon={<Satellite className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "NDVI" }]}
                actions={
                    <div className="flex flex-wrap items-center gap-2">
                        <Select
                            value={periodo}
                            onValueChange={(value) => setPeriodo(value as PeriodoFiltro)}
                        >
                            <SelectTrigger className="h-8 w-44 rounded-sm text-xs">
                                <Calendar className="mr-1.5 size-3.5 text-muted-foreground" />
                                <SelectValue placeholder="Período" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="30">Últimos 30 dias</SelectItem>
                                <SelectItem value="90">Últimos 90 dias</SelectItem>
                                <SelectItem value="180">Últimos 180 dias</SelectItem>
                                <SelectItem value="all">Todo o período</SelectItem>
                            </SelectContent>
                        </Select>

                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            onClick={handleRefreshAll}
                            disabled={fetchingResumo}
                        >
                            <RefreshCw
                                className={cn("mr-1.5 size-3.5", fetchingResumo && "animate-spin")}
                            />
                            Atualizar
                        </Button>

                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            onClick={handleOpenManual}
                            disabled={talhoesOptions.length === 0}
                        >
                            <Plus className="mr-1.5 size-3.5" />
                            Registro manual
                        </Button>
                    </div>
                }
            />

            {(isErrorResumo || isErrorAreas) && (
                <Alert variant="destructive" className="rounded-sm">
                    <AlertTriangle className="size-4" />
                    <AlertTitle>Erro ao consultar dados NDVI</AlertTitle>
                    <AlertDescription>{erroMsg}</AlertDescription>
                </Alert>
            )}

            {resumo && !resumo.sincronizacao_automatica_disponivel && (
                <Alert className="rounded-sm">
                    <Info className="size-4" />
                    <AlertTitle>Monitoramento via registros reais</AlertTitle>
                    <AlertDescription>
                        Os índices, alertas e cores no mapa utilizam exclusivamente as leituras
                        registradas na propriedade. A coleta automática via satélite Sentinel-2 ainda
                        não está configurada neste ambiente; utilize <strong>Registro manual</strong>{" "}
                        para lançar leituras de QGIS, drone ou provedor externo.
                    </AlertDescription>
                </Alert>
            )}

            {!isErrorResumo && talhoesOptions.length === 0 ? (
                <Card className="rounded-sm">
                    <CardContent className="flex flex-col items-center justify-center gap-3 p-10 text-center">
                        <Satellite className="size-10 text-muted-foreground/50" />
                        <div className="space-y-1">
                            <p className="text-sm font-medium">
                                Nenhuma área produtiva cadastrada nesta propriedade
                            </p>
                            <p className="text-xs text-muted-foreground">
                                Cadastre talhões ou piquetes na propriedade ativa para iniciar o
                                monitoramento de vigor vegetativo (NDVI).
                            </p>
                        </div>
                        <Button variant="outline" size="sm" className="rounded-sm" asChild>
                            <Link href="/cadastros/propriedades">Ir para Propriedades</Link>
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <>
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                        <Card className="overflow-hidden rounded-sm shadow-sm md:col-span-2">
                            <CardHeader className="border-b bg-primary/5 px-5 py-3">
                                <div className="flex items-center justify-between gap-2">
                                    <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-primary">
                                        <Maximize2 className="size-4" />
                                        Monitoramento Espacial
                                    </CardTitle>
                                    <Badge variant="outline" className="rounded-sm text-[10px]">
                                        {resumo?.areas_monitoradas ?? 0} /{" "}
                                        {resumo?.total_areas_produtivas ?? areas.length} ÁREAS COM
                                        LEITURA
                                    </Badge>
                                </div>
                            </CardHeader>
                            <CardContent className="p-0">
                                <NdviMapView
                                    areas={areas}
                                    resumoPorTalhao={resumoPorTalhao}
                                    selectedTalhaoId={effectiveSelectedTalhaoId}
                                    onSelectTalhao={setSelectedTalhaoId}
                                />
                            </CardContent>
                        </Card>

                        <div className="flex flex-col gap-6">
                            <Card className="rounded-sm shadow-sm">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                        Média da Propriedade
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="flex flex-col items-center gap-2 pb-6 pt-2 text-center">
                                    <div className="text-5xl font-bold text-primary">
                                        {resumo?.media_ndvi_propriedade != null
                                            ? resumo.media_ndvi_propriedade.toFixed(3)
                                            : "—"}
                                    </div>
                                    <Badge
                                        variant={getNdviStatusBadgeVariant(
                                            resumo?.classificacao_geral ?? "Sem dados",
                                        )}
                                        className="rounded-sm uppercase"
                                    >
                                        {resumo?.classificacao_geral ?? "Sem dados"}
                                    </Badge>
                                    <p className="mt-2 text-xs text-muted-foreground">
                                        {resumo?.areas_monitoradas ?? 0} de{" "}
                                        {resumo?.total_areas_produtivas ?? 0} área(s) monitorada(s)
                                        {" · "}
                                        {resumo?.total_registros ?? 0} registro(s)
                                    </p>
                                    {resumo?.variacao_media_pct != null && (
                                        <p className="text-xs text-muted-foreground">
                                            Variação média recente:{" "}
                                            <span
                                                className={cn(
                                                    "font-semibold",
                                                    resumo.variacao_media_pct >= 0
                                                        ? "text-emerald-600 dark:text-emerald-400"
                                                        : "text-red-600 dark:text-red-400",
                                                )}
                                            >
                                                {formatNdviVariation(resumo.variacao_media_pct)}
                                            </span>
                                        </p>
                                    )}
                                </CardContent>
                            </Card>

                            <Card className="flex-1 rounded-sm shadow-sm">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                        Alertas de Monitoramento
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3 pt-1">
                                    {!resumo || resumo.alertas.length === 0 ? (
                                        <div className="flex items-start gap-2.5 rounded-sm border bg-muted/20 p-3 text-xs text-muted-foreground">
                                            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                                            <span>
                                                Nenhum alerta crítico ou de atenção para o filtro
                                                selecionado.
                                            </span>
                                        </div>
                                    ) : (
                                        resumo.alertas.slice(0, 6).map((alerta, idx) => (
                                            <button
                                                key={`${alerta.talhao_id}-${alerta.tipo}-${idx}`}
                                                type="button"
                                                onClick={() => handleFocusTalhao(alerta.talhao_id)}
                                                className={cn(
                                                    "flex w-full items-center justify-between gap-2 rounded-sm border p-3 text-left transition-colors",
                                                    alerta.severidade === "CRITICO"
                                                        ? "border-destructive/25 bg-destructive/5 hover:bg-destructive/10"
                                                        : "border-amber-500/25 bg-amber-500/5 hover:bg-amber-500/10",
                                                )}
                                            >
                                                <div className="min-w-0">
                                                    <p className="truncate text-sm font-semibold">
                                                        {alerta.talhao_nome}
                                                    </p>
                                                    <p className="truncate text-xs text-muted-foreground">
                                                        {alerta.detalhe}
                                                    </p>
                                                </div>
                                                <Badge
                                                    variant={
                                                        alerta.severidade === "CRITICO"
                                                            ? "danger"
                                                            : "warning"
                                                    }
                                                    className="shrink-0 rounded-sm text-[10px]"
                                                >
                                                    {alerta.titulo}
                                                </Badge>
                                            </button>
                                        ))
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    </div>

                    <Card className="rounded-sm shadow-sm">
                        <CardHeader className="border-b bg-primary/5 px-5 py-3">
                            <div className="flex items-center gap-2 text-primary">
                                <Layers className="size-4" />
                                <CardTitle className="text-sm font-semibold uppercase tracking-wider">
                                    Consolidado por Área Produtiva
                                </CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="p-4">
                            <DataTable
                                data={talhoesResumo}
                                columns={columns}
                                searchable={true}
                                searchPlaceholder="Buscar por talhão, piquete ou status..."
                                exportable={true}
                                exportFileName="ndvi-consolidado-areas"
                                emptyMessage="Nenhuma área produtiva encontrada."
                            />
                        </CardContent>
                    </Card>

                    <div ref={serieSectionRef} id="ndvi-serie-talhao">
                        <Card className="rounded-sm shadow-sm">
                            <CardHeader className="border-b bg-primary/5 px-5 py-3">
                                <div className="flex items-center gap-2 text-primary">
                                    <Satellite className="size-4" />
                                    <CardTitle className="text-sm font-semibold uppercase tracking-wider">
                                        Análise Temporal e Registros do Talhão
                                    </CardTitle>
                                </div>
                            </CardHeader>
                            <CardContent className="p-5">
                                <NdviTalhao
                                    talhoes={talhoesOptions}
                                    selectedTalhaoId={effectiveSelectedTalhaoId}
                                    onSelectTalhao={setSelectedTalhaoId}
                                    onRegistroAlterado={handleRefreshAll}
                                    manualOpen={manualModalOpen}
                                    onManualOpenChange={setManualModalOpen}
                                />
                            </CardContent>
                        </Card>
                    </div>
                </>
            )}
        </div>
    );
}
