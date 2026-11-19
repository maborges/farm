"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    Cloud,
    Minus,
    Plus,
    Satellite,
    Trash2,
    TrendingDown,
    TrendingUp,
} from "lucide-react";
import {
    CartesianGrid,
    Line,
    LineChart,
    ReferenceLine,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
    Dialog,
    DialogBody,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface NDVIImagem {
    id: string;
    talhao_id: string;
    data_captura: string;
    cobertura_nuvens_pct: number | null;
    indice_medio: number | null;
    indice_minimo: number | null;
    indice_maximo: number | null;
    url_imagem_colorida: string | null;
    satelite?: string;
    created_at: string;
}

interface SerieTemporal {
    talhao_id: string;
    total_imagens: number;
    indice_atual: number | null;
    tendencia: "SUBINDO" | "CAINDO" | "ESTAVEL" | null;
    dados: { data: string; indice_medio: number | null; cobertura_nuvens_pct: number | null }[];
}

interface ChartPoint {
    data: string;
    dataRaw: string;
    indice_medio: number | null;
    indice_minimo: number | null;
    indice_maximo: number | null;
    cobertura_nuvens_pct: number | null;
}

interface TooltipPayloadItem {
    payload?: ChartPoint;
}

interface CustomTooltipProps {
    active?: boolean;
    payload?: TooltipPayloadItem[];
    label?: string;
}

interface Props {
    talhoes: { id: string; nome: string }[];
    selectedTalhaoId?: string | null;
    onSelectTalhao?: (talhaoId: string) => void;
    onRegistroAlterado?: () => void;
    manualOpen?: boolean;
    onManualOpenChange?: (open: boolean) => void;
}

interface ManualFormState {
    data_captura: string;
    indice_medio: string;
    indice_minimo: string;
    indice_maximo: string;
    cobertura_nuvens_pct: string;
    satelite: string;
}

const INITIAL_MANUAL_FORM: ManualFormState = {
    data_captura: "",
    indice_medio: "",
    indice_minimo: "",
    indice_maximo: "",
    cobertura_nuvens_pct: "",
    satelite: "Manual",
};

function ndviColor(v: number | null): string {
    if (v === null) return "text-muted-foreground";
    if (v >= 0.6) return "text-emerald-600 dark:text-emerald-400";
    if (v >= 0.4) return "text-green-600 dark:text-green-400";
    if (v >= 0.2) return "text-amber-600 dark:text-amber-400";
    return "text-red-600 dark:text-red-400";
}

function ndviLabel(v: number | null): string {
    if (v === null) return "—";
    if (v >= 0.6) return "Vegetação densa";
    if (v >= 0.4) return "Vegetação moderada";
    if (v >= 0.2) return "Vegetação esparsa";
    if (v >= 0) return "Solo exposto / estresse";
    return "Água / nuvem";
}

function ndviBadgeClass(v: number | null): string {
    if (v === null) return "bg-muted text-muted-foreground";
    if (v >= 0.6) return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20";
    if (v >= 0.4) return "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20";
    if (v >= 0.2) return "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20";
    return "bg-destructive/10 text-destructive border-destructive/20";
}

function validateManualForm(form: ManualFormState): string | null {
    if (!form.data_captura || !form.indice_medio) {
        return "Informe a data da captura e o NDVI médio.";
    }
    const medio = Number(form.indice_medio);
    if (Number.isNaN(medio) || medio < -1 || medio > 1) {
        return "NDVI médio deve estar entre -1,0 e 1,0.";
    }
    const min = form.indice_minimo !== "" ? Number(form.indice_minimo) : null;
    const max = form.indice_maximo !== "" ? Number(form.indice_maximo) : null;
    if (min !== null && (Number.isNaN(min) || min < -1 || min > 1)) {
        return "NDVI mínimo deve estar entre -1,0 e 1,0.";
    }
    if (max !== null && (Number.isNaN(max) || max < -1 || max > 1)) {
        return "NDVI máximo deve estar entre -1,0 e 1,0.";
    }
    if (min !== null && max !== null && min > max) {
        return "NDVI mínimo não pode ser maior que o NDVI máximo.";
    }
    if (min !== null && medio < min) {
        return "NDVI médio não pode ser menor que o NDVI mínimo.";
    }
    if (max !== null && medio > max) {
        return "NDVI médio não pode ser maior que o NDVI máximo.";
    }
    if (form.cobertura_nuvens_pct !== "") {
        const nuvens = Number(form.cobertura_nuvens_pct);
        if (Number.isNaN(nuvens) || nuvens < 0 || nuvens > 100) {
            return "Cobertura de nuvens deve estar entre 0% e 100%.";
        }
    }
    return null;
}

function formatErrorMessage(err: unknown, fallback: string): string {
    if (err instanceof Error && err.message) {
        return err.message;
    }
    return fallback;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
        <div className="space-y-1 rounded-sm border border-border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
            <p className="font-medium">{label}</p>
            {d?.indice_medio != null && (
                <p>
                    NDVI:{" "}
                    <strong className={ndviColor(d.indice_medio)}>
                        {d.indice_medio.toFixed(3)}
                    </strong>
                </p>
            )}
            {d?.indice_minimo != null && (
                <p className="text-muted-foreground">Mín: {d.indice_minimo.toFixed(3)}</p>
            )}
            {d?.indice_maximo != null && (
                <p className="text-muted-foreground">Máx: {d.indice_maximo.toFixed(3)}</p>
            )}
            {d?.cobertura_nuvens_pct != null && (
                <p className="flex items-center gap-1 text-muted-foreground">
                    <Cloud className="size-3" /> {d.cobertura_nuvens_pct.toFixed(0)}% nuvens
                </p>
            )}
        </div>
    );
}

export function NdviTalhao({
    talhoes,
    selectedTalhaoId,
    onSelectTalhao,
    onRegistroAlterado,
    manualOpen,
    onManualOpenChange,
}: Props) {
    const qc = useQueryClient();
    const [internalTalhaoId, setInternalTalhaoId] = useState<string>("");
    const [internalManualOpen, setInternalManualOpen] = useState(false);
    const [manualForm, setManualForm] = useState<ManualFormState>(INITIAL_MANUAL_FORM);

    const effectiveTalhaoId = useMemo(() => {
        if (selectedTalhaoId && talhoes.some((t) => t.id === selectedTalhaoId)) {
            return selectedTalhaoId;
        }
        if (internalTalhaoId && talhoes.some((t) => t.id === internalTalhaoId)) {
            return internalTalhaoId;
        }
        return talhoes[0]?.id ?? "";
    }, [selectedTalhaoId, internalTalhaoId, talhoes]);

    const isManualOpen = manualOpen ?? internalManualOpen;
    const setIsManualOpen = (open: boolean) => {
        if (manualOpen === undefined) {
            setInternalManualOpen(open);
        }
        onManualOpenChange?.(open);
    };

    const handleSelectTalhao = (id: string) => {
        setInternalTalhaoId(id);
        onSelectTalhao?.(id);
    };

    const { data: serie, isLoading: loadingSerie } = useQuery<SerieTemporal>({
        queryKey: ["ndvi-serie", effectiveTalhaoId],
        queryFn: () => apiFetch(`/ndvi/serie-temporal/${effectiveTalhaoId}`),
        enabled: Boolean(effectiveTalhaoId),
    });

    const { data: imagens = [], isLoading: loadingImagens } = useQuery<NDVIImagem[]>({
        queryKey: ["ndvi-imagens", effectiveTalhaoId],
        queryFn: () => apiFetch(`/ndvi/?talhao_id=${effectiveTalhaoId}`),
        enabled: Boolean(effectiveTalhaoId),
    });

    const invalidateAll = () => {
        qc.invalidateQueries({ queryKey: ["ndvi-serie", effectiveTalhaoId] });
        qc.invalidateQueries({ queryKey: ["ndvi-imagens", effectiveTalhaoId] });
        qc.invalidateQueries({ queryKey: ["ndvi-resumo"] });
        onRegistroAlterado?.();
    };

    const registrarManual = useMutation({
        mutationFn: () =>
            apiFetch("/ndvi/registro-manual", {
                method: "POST",
                body: JSON.stringify({
                    talhao_id: effectiveTalhaoId,
                    data_captura: manualForm.data_captura,
                    indice_medio: Number(manualForm.indice_medio),
                    indice_minimo:
                        manualForm.indice_minimo !== "" ? Number(manualForm.indice_minimo) : null,
                    indice_maximo:
                        manualForm.indice_maximo !== "" ? Number(manualForm.indice_maximo) : null,
                    cobertura_nuvens_pct:
                        manualForm.cobertura_nuvens_pct !== ""
                            ? Number(manualForm.cobertura_nuvens_pct)
                            : null,
                    satelite: manualForm.satelite.trim() || "Manual",
                }),
            }),
        onSuccess: () => {
            toast.success("Registro NDVI adicionado.");
            invalidateAll();
            setIsManualOpen(false);
            setManualForm(INITIAL_MANUAL_FORM);
        },
        onError: (err: unknown) => {
            toast.error(formatErrorMessage(err, "Erro ao registrar índice NDVI."));
        },
    });

    const excluirImagem = useMutation({
        mutationFn: (imagemId: string) =>
            apiFetch(`/ndvi/${imagemId}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Registro NDVI excluído.");
            invalidateAll();
        },
        onError: (err: unknown) => {
            toast.error(formatErrorMessage(err, "Erro ao excluir registro NDVI."));
        },
    });

    const handleSubmitManual = () => {
        const erro = validateManualForm(manualForm);
        if (erro) {
            toast.error(erro);
            return;
        }
        registrarManual.mutate();
    };

    const talhaoNome = talhoes.find((t) => t.id === effectiveTalhaoId)?.nome ?? "—";

    const chartData = useMemo<ChartPoint[]>(() => {
        const imagemMap = Object.fromEntries(imagens.map((i) => [i.data_captura, i]));
        return (serie?.dados ?? []).map((d) => {
            const img = imagemMap[d.data];
            return {
                data: format(new Date(d.data + "T12:00:00"), "dd/MM", { locale: ptBR }),
                dataRaw: d.data,
                indice_medio: d.indice_medio,
                indice_minimo: img?.indice_minimo ?? null,
                indice_maximo: img?.indice_maximo ?? null,
                cobertura_nuvens_pct: d.cobertura_nuvens_pct,
            };
        });
    }, [imagens, serie?.dados]);

    const sortedImagens = useMemo(
        () => [...imagens].sort((a, b) => b.data_captura.localeCompare(a.data_captura)),
        [imagens],
    );

    const latestNuvensPct = sortedImagens[0]?.cobertura_nuvens_pct ?? null;

    const imagemColumns = useMemo<ColumnDef<NDVIImagem>[]>(
        () => [
            {
                id: "data_captura",
                header: "Data",
                accessorKey: "data_captura",
                sortable: true,
                cell: (val) =>
                    format(new Date(String(val) + "T12:00:00"), "dd/MM/yyyy", { locale: ptBR }),
                exportFormat: (val) =>
                    format(new Date(String(val) + "T12:00:00"), "dd/MM/yyyy", { locale: ptBR }),
            },
            {
                id: "indice_medio",
                header: "NDVI Médio",
                accessorKey: "indice_medio",
                sortable: true,
                cell: (val) => {
                    const num = val as number | null;
                    return num != null ? (
                        <Badge className={cn("rounded-sm font-mono text-xs", ndviBadgeClass(num))}>
                            {num.toFixed(3)}
                        </Badge>
                    ) : (
                        "—"
                    );
                },
                exportFormat: (val) =>
                    val != null ? Number(val).toFixed(3) : "—",
            },
            {
                id: "indice_minimo",
                header: "Mín",
                accessorKey: "indice_minimo",
                sortable: true,
                cell: (val) => (val != null ? Number(val).toFixed(3) : "—"),
                exportFormat: (val) => (val != null ? Number(val).toFixed(3) : "—"),
            },
            {
                id: "indice_maximo",
                header: "Máx",
                accessorKey: "indice_maximo",
                sortable: true,
                cell: (val) => (val != null ? Number(val).toFixed(3) : "—"),
                exportFormat: (val) => (val != null ? Number(val).toFixed(3) : "—"),
            },
            {
                id: "cobertura_nuvens_pct",
                header: "Nuvens",
                accessorKey: "cobertura_nuvens_pct",
                sortable: true,
                cell: (val) => {
                    const nuvens = val as number | null;
                    return nuvens != null ? (
                        <span
                            className={cn(
                                "text-xs",
                                nuvens >= 30 ? "font-medium text-amber-600" : "text-muted-foreground",
                            )}
                        >
                            {nuvens.toFixed(0)}%
                        </span>
                    ) : (
                        "—"
                    );
                },
                exportFormat: (val) => (val != null ? `${Number(val).toFixed(0)}%` : "—"),
            },
            {
                id: "satelite",
                header: "Origem / Satélite",
                accessorKey: "satelite",
                sortable: true,
                cell: (val) => (val ? String(val) : "Manual"),
            },
            {
                id: "classificacao",
                header: "Classificação",
                accessorFn: (row) => ndviLabel(row.indice_medio),
                sortable: true,
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
                            className="rounded-sm border-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                            title="Excluir registro"
                            aria-label="Excluir registro"
                            disabled={excluirImagem.isPending}
                            onClick={() => excluirImagem.mutate(row.id)}
                        >
                            <Trash2 className="size-3.5" />
                        </Button>
                    </div>
                ),
            },
        ],
        [excluirImagem],
    );

    const TrendIcon =
        serie?.tendencia === "SUBINDO"
            ? TrendingUp
            : serie?.tendencia === "CAINDO"
              ? TrendingDown
              : Minus;

    const trendColor =
        serie?.tendencia === "SUBINDO"
            ? "text-emerald-600"
            : serie?.tendencia === "CAINDO"
              ? "text-red-500"
              : "text-muted-foreground";

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
                <Select value={effectiveTalhaoId} onValueChange={handleSelectTalhao}>
                    <SelectTrigger className="h-8 w-56 rounded-sm text-sm">
                        <SelectValue placeholder="Selecione o talhão" />
                    </SelectTrigger>
                    <SelectContent>
                        {talhoes.map((t) => (
                            <SelectItem key={t.id} value={t.id}>
                                {t.nome}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <Badge variant="info" className="gap-1.5 rounded-sm font-normal">
                    <Satellite className="size-3.5" />
                    Coleta automática Sentinel-2 em breve — modo registro manual ativo
                </Badge>

                <div className="ml-auto flex items-center gap-2">
                    <Dialog open={isManualOpen} onOpenChange={setIsManualOpen}>
                        <DialogTrigger asChild>
                            <Button
                                variant="outline"
                                size="sm"
                                className="rounded-sm"
                                disabled={!effectiveTalhaoId}
                            >
                                <Plus className="mr-1.5 size-4" />
                                Registro manual
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-xl rounded-sm">
                            <DialogHeader className="border-b">
                                <DialogTitle>
                                    Registrar índice NDVI manualmente — {talhaoNome}
                                </DialogTitle>
                            </DialogHeader>
                            <DialogBody className="grid gap-4 md:grid-cols-2">
                                <div className="space-y-1.5">
                                    <Label>Data da captura *</Label>
                                    <Input
                                        type="date"
                                        className="h-8 rounded-sm text-sm"
                                        value={manualForm.data_captura}
                                        onChange={(e) =>
                                            setManualForm((f) => ({
                                                ...f,
                                                data_captura: e.target.value,
                                            }))
                                        }
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <Label>Origem / Satélite</Label>
                                    <Input
                                        type="text"
                                        className="h-8 rounded-sm text-sm"
                                        placeholder="Ex: Manual, QGIS, Drone"
                                        value={manualForm.satelite}
                                        onChange={(e) =>
                                            setManualForm((f) => ({
                                                ...f,
                                                satelite: e.target.value,
                                            }))
                                        }
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <Label>NDVI médio * (-1 a 1)</Label>
                                    <Input
                                        type="number"
                                        step="0.001"
                                        min="-1"
                                        max="1"
                                        className="h-8 rounded-sm text-sm"
                                        value={manualForm.indice_medio}
                                        onChange={(e) =>
                                            setManualForm((f) => ({
                                                ...f,
                                                indice_medio: e.target.value,
                                            }))
                                        }
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <Label>Cobertura de nuvens (%)</Label>
                                    <Input
                                        type="number"
                                        step="1"
                                        min="0"
                                        max="100"
                                        placeholder="0 a 100"
                                        className="h-8 rounded-sm text-sm"
                                        value={manualForm.cobertura_nuvens_pct}
                                        onChange={(e) =>
                                            setManualForm((f) => ({
                                                ...f,
                                                cobertura_nuvens_pct: e.target.value,
                                            }))
                                        }
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <Label>NDVI mínimo</Label>
                                    <Input
                                        type="number"
                                        step="0.001"
                                        min="-1"
                                        max="1"
                                        className="h-8 rounded-sm text-sm"
                                        value={manualForm.indice_minimo}
                                        onChange={(e) =>
                                            setManualForm((f) => ({
                                                ...f,
                                                indice_minimo: e.target.value,
                                            }))
                                        }
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <Label>NDVI máximo</Label>
                                    <Input
                                        type="number"
                                        step="0.001"
                                        min="-1"
                                        max="1"
                                        className="h-8 rounded-sm text-sm"
                                        value={manualForm.indice_maximo}
                                        onChange={(e) =>
                                            setManualForm((f) => ({
                                                ...f,
                                                indice_maximo: e.target.value,
                                            }))
                                        }
                                    />
                                </div>
                                <p className="text-xs text-muted-foreground md:col-span-2">
                                    Registre leituras calculadas no QGIS, por drone ou provedor
                                    externo. Os indicadores da propriedade e alertas são atualizados
                                    automaticamente.
                                </p>
                            </DialogBody>
                            <DialogFooter className="border-t px-6 pb-6 pt-4">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="rounded-sm"
                                    onClick={() => setIsManualOpen(false)}
                                >
                                    Cancelar
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="rounded-sm border-primary/40 text-primary hover:bg-primary/10"
                                    disabled={
                                        !manualForm.data_captura ||
                                        !manualForm.indice_medio ||
                                        registrarManual.isPending
                                    }
                                    onClick={handleSubmitManual}
                                >
                                    {registrarManual.isPending ? "Salvando…" : "Registrar"}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            {!effectiveTalhaoId ? (
                <p className="py-10 text-center text-sm text-muted-foreground">
                    Selecione um talhão para visualizar o NDVI.
                </p>
            ) : loadingSerie ? (
                <div className="space-y-3">
                    <Skeleton className="h-8 w-48 rounded-sm" />
                    <Skeleton className="h-56 w-full rounded-sm" />
                </div>
            ) : !serie || serie.total_imagens === 0 ? (
                <div className="space-y-3 rounded-sm border py-12 text-center">
                    <Satellite className="mx-auto size-10 text-muted-foreground/50" />
                    <p className="text-sm text-muted-foreground">
                        Nenhum registro NDVI cadastrado para <strong>{talhaoNome}</strong>.
                    </p>
                    <Button
                        variant="outline"
                        size="sm"
                        className="rounded-sm"
                        onClick={() => setIsManualOpen(true)}
                    >
                        <Plus className="mr-1.5 size-4" />
                        Registrar leitura manual
                    </Button>
                </div>
            ) : (
                <>
                    <div className="grid gap-4 md:grid-cols-3">
                        <Card className="rounded-sm">
                            <CardContent className="p-4">
                                <p className="mb-1 text-xs text-muted-foreground">NDVI Atual</p>
                                <p className={cn("text-2xl font-bold", ndviColor(serie.indice_atual))}>
                                    {serie.indice_atual?.toFixed(3) ?? "—"}
                                </p>
                                {serie.indice_atual != null && (
                                    <p className="mt-0.5 text-xs text-muted-foreground">
                                        {ndviLabel(serie.indice_atual)}
                                    </p>
                                )}
                            </CardContent>
                        </Card>
                        <Card className="rounded-sm">
                            <CardContent className="p-4">
                                <p className="mb-1 text-xs text-muted-foreground">Tendência</p>
                                <div
                                    className={cn(
                                        "flex items-center gap-1.5 text-lg font-semibold",
                                        trendColor,
                                    )}
                                >
                                    <TrendIcon className="size-5" />
                                    {serie.tendencia === "SUBINDO"
                                        ? "Subindo"
                                        : serie.tendencia === "CAINDO"
                                          ? "Caindo"
                                          : "Estável"}
                                </div>
                                <p className="mt-0.5 text-xs text-muted-foreground">
                                    {serie.total_imagens} registro(s) salvo(s)
                                </p>
                            </CardContent>
                        </Card>
                        <Card className="rounded-sm">
                            <CardContent className="p-4">
                                <p className="mb-1 text-xs text-muted-foreground">Última Captura</p>
                                <p className="text-lg font-semibold">
                                    {chartData.length > 0
                                        ? format(
                                              new Date(
                                                  chartData[chartData.length - 1].dataRaw + "T12:00:00",
                                              ),
                                              "dd/MM/yyyy",
                                              { locale: ptBR },
                                          )
                                        : "—"}
                                </p>
                                {latestNuvensPct != null && (
                                    <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                                        <Cloud className="size-3" />
                                        {latestNuvensPct.toFixed(0)}% cobertura de nuvens
                                    </p>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    <Card className="rounded-sm">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm">
                                Série Temporal NDVI — {talhaoNome}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <ResponsiveContainer width="100%" height={240}>
                                <LineChart
                                    data={chartData}
                                    margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                    <XAxis
                                        dataKey="data"
                                        tick={{ fontSize: 11 }}
                                        tickLine={false}
                                    />
                                    <YAxis
                                        domain={[-0.1, 1]}
                                        tick={{ fontSize: 11 }}
                                        tickLine={false}
                                        tickFormatter={(v: number) => v.toFixed(1)}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    <ReferenceLine
                                        y={0.6}
                                        stroke="#10b981"
                                        strokeDasharray="4 4"
                                        label={{ value: "0.6", fontSize: 10, fill: "#10b981" }}
                                    />
                                    <ReferenceLine
                                        y={0.4}
                                        stroke="#eab308"
                                        strokeDasharray="4 4"
                                        label={{ value: "0.4", fontSize: 10, fill: "#eab308" }}
                                    />
                                    <ReferenceLine
                                        y={0.2}
                                        stroke="#ef4444"
                                        strokeDasharray="4 4"
                                        label={{ value: "0.2", fontSize: 10, fill: "#ef4444" }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="indice_medio"
                                        stroke="#10b981"
                                        strokeWidth={2}
                                        dot={{ r: 3, fill: "#10b981" }}
                                        activeDot={{ r: 5 }}
                                        connectNulls
                                        name="NDVI médio"
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                            <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1">
                                    <span className="inline-block h-0.5 w-3 rounded bg-emerald-500" />{" "}
                                    NDVI médio
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="inline-block h-px w-3 border-t border-dashed border-emerald-500" />{" "}
                                    ≥0.6 densa
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="inline-block h-px w-3 border-t border-dashed border-yellow-500" />{" "}
                                    ≥0.4 moderada
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="inline-block h-px w-3 border-t border-dashed border-red-500" />{" "}
                                    ≥0.2 esparsa
                                </span>
                            </div>
                        </CardContent>
                    </Card>

                    <DataTable
                        data={sortedImagens}
                        columns={imagemColumns}
                        searchable={true}
                        searchPlaceholder="Buscar por data, satélite ou classificação..."
                        exportable={true}
                        exportFileName="ndvi-registros-talhao"
                        isLoading={loadingImagens}
                        emptyMessage="Nenhum registro NDVI para este talhão."
                    />
                </>
            )}
        </div>
    );
}
