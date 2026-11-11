"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw, Satellite, Cloud, TrendingUp, TrendingDown, Minus, Plus } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogBody, DialogTrigger,
} from "@/components/ui/dialog";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ReferenceLine,
    ResponsiveContainer,
} from "recharts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface NDVIImagem {
    id: string;
    talhao_id: string;
    data_captura: string;
    cobertura_nuvens_pct: number | null;
    indice_medio: number | null;
    indice_minimo: number | null;
    indice_maximo: number | null;
    url_imagem_colorida: string | null;
    created_at: string;
}

interface SerieTemporal {
    talhao_id: string;
    total_imagens: number;
    indice_atual: number | null;
    tendencia: string | null;    // SUBINDO | CAINDO | ESTAVEL
    dados: { data: string; indice_medio: number | null; cobertura_nuvens_pct: number | null }[];
}

interface Props {
    talhoes: { id: string; nome: string }[];
}

// ── NDVI color band ────────────────────────────────────────────────────────────

function ndviColor(v: number | null): string {
    if (v === null) return "text-muted-foreground";
    if (v >= 0.6) return "text-emerald-600";
    if (v >= 0.4) return "text-green-500";
    if (v >= 0.2) return "text-yellow-500";
    return "text-red-500";
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

// ── Custom Tooltip ─────────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
        <div className="bg-popover text-popover-foreground border border-border rounded-sm shadow-md px-3 py-2 text-xs space-y-1">
            <p className="font-medium">{label}</p>
            {d?.indice_medio != null && (
                <p>NDVI: <strong className={ndviColor(d.indice_medio)}>{d.indice_medio.toFixed(3)}</strong></p>
            )}
            {d?.indice_minimo != null && <p className="text-muted-foreground">Mín: {d.indice_minimo.toFixed(3)}</p>}
            {d?.indice_maximo != null && <p className="text-muted-foreground">Máx: {d.indice_maximo.toFixed(3)}</p>}
            {d?.cobertura_nuvens_pct != null && (
                <p className="text-muted-foreground flex items-center gap-1">
                    <Cloud className="size-3" /> {d.cobertura_nuvens_pct.toFixed(0)}% nuvens
                </p>
            )}
        </div>
    );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function NdviTalhao({ talhoes }: Props) {
    const qc = useQueryClient();
    const [talhaoId, setTalhaoId] = useState<string>(talhoes[0]?.id ?? "");
    const [manualOpen, setManualOpen] = useState(false);
    const [manualForm, setManualForm] = useState({ data_captura: "", indice_medio: "", indice_minimo: "", indice_maximo: "" });

    const { data: serie, isLoading: loadingSerie } = useQuery<SerieTemporal>({
        queryKey: ["ndvi-serie", talhaoId],
        queryFn: () => apiFetch(`/ndvi/serie-temporal/${talhaoId}`),
        enabled: !!talhaoId,
    });

    const { data: imagens = [], isLoading: loadingImagens } = useQuery<NDVIImagem[]>({
        queryKey: ["ndvi-imagens", talhaoId],
        queryFn: () => apiFetch(`/ndvi/?talhao_id=${talhaoId}`),
        enabled: !!talhaoId,
    });

    const sync = useMutation({
        mutationFn: () =>
            apiFetch(`/ndvi/sincronizar/${talhaoId}`, { method: "POST" }),
        onSuccess: (res: any) => {
            toast.success(res?.message ?? "Sincronização iniciada.");
            qc.invalidateQueries({ queryKey: ["ndvi-serie", talhaoId] });
            qc.invalidateQueries({ queryKey: ["ndvi-imagens", talhaoId] });
        },
        onError: () => toast.error("Erro ao acionar sincronização."),
    });

    const registrarManual = useMutation({
        mutationFn: () =>
            apiFetch("/ndvi/registro-manual", {
                method: "POST",
                body: JSON.stringify({
                    talhao_id: talhaoId,
                    data_captura: manualForm.data_captura,
                    indice_medio: manualForm.indice_medio ? Number(manualForm.indice_medio) : null,
                    indice_minimo: manualForm.indice_minimo ? Number(manualForm.indice_minimo) : null,
                    indice_maximo: manualForm.indice_maximo ? Number(manualForm.indice_maximo) : null,
                    satelite: "Manual",
                }),
            }),
        onSuccess: () => {
            toast.success("Registro NDVI adicionado.");
            qc.invalidateQueries({ queryKey: ["ndvi-serie", talhaoId] });
            qc.invalidateQueries({ queryKey: ["ndvi-imagens", talhaoId] });
            setManualOpen(false);
            setManualForm({ data_captura: "", indice_medio: "", indice_minimo: "", indice_maximo: "" });
        },
        onError: () => toast.error("Erro ao registrar índice NDVI."),
    });

    const talhaoNome = talhoes.find((t) => t.id === talhaoId)?.nome ?? "—";

    // Prepare chart data — join serie dados with imagens for min/max
    const imagemMap = Object.fromEntries(imagens.map((i) => [i.data_captura, i]));
    const chartData = (serie?.dados ?? []).map((d) => {
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
            {/* Toolbar */}
            <div className="flex items-center gap-3 flex-wrap">
                <Select value={talhaoId} onValueChange={setTalhaoId}>
                    <SelectTrigger className="w-52">
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

                <div className="ml-auto flex items-center gap-2">
                    <Dialog open={manualOpen} onOpenChange={setManualOpen}>
                        <DialogTrigger asChild>
                            <Button variant="outline" size="sm" disabled={!talhaoId}>
                                <Plus className="size-4 mr-1.5" />
                                Registro manual
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-xl">
                            <DialogHeader className="border-b">
                                <DialogTitle>Registrar índice NDVI manualmente</DialogTitle>
                            </DialogHeader>
                            <DialogBody className="grid md:grid-cols-2 gap-4">
                                <div className="space-y-2 md:col-span-2">
                                    <Label>Data da captura *</Label>
                                    <Input
                                        type="date"
                                        value={manualForm.data_captura}
                                        onChange={(e) => setManualForm((f) => ({ ...f, data_captura: e.target.value }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>NDVI médio *</Label>
                                    <Input
                                        type="number" step="0.001" min="-1" max="1"
                                        value={manualForm.indice_medio}
                                        onChange={(e) => setManualForm((f) => ({ ...f, indice_medio: e.target.value }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>NDVI mínimo</Label>
                                    <Input
                                        type="number" step="0.001" min="-1" max="1"
                                        value={manualForm.indice_minimo}
                                        onChange={(e) => setManualForm((f) => ({ ...f, indice_minimo: e.target.value }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>NDVI máximo</Label>
                                    <Input
                                        type="number" step="0.001" min="-1" max="1"
                                        value={manualForm.indice_maximo}
                                        onChange={(e) => setManualForm((f) => ({ ...f, indice_maximo: e.target.value }))}
                                    />
                                </div>
                                <p className="text-xs text-muted-foreground md:col-span-2">
                                    Use para registrar um índice calculado fora da plataforma (QGIS, provedor terceiro) enquanto a sincronização automática via Sentinel-2 não está disponível.
                                </p>
                            </DialogBody>
                            <DialogFooter className="border-t px-6 pb-6 pt-4">
                                <Button variant="outline" onClick={() => setManualOpen(false)}>Cancelar</Button>
                                <Button
                                    disabled={!manualForm.data_captura || !manualForm.indice_medio || registrarManual.isPending}
                                    onClick={() => registrarManual.mutate()}
                                >
                                    Registrar
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => sync.mutate()}
                        disabled={sync.isPending || !talhaoId}
                    >
                        <RefreshCw className={cn("size-4 mr-1.5", sync.isPending && "animate-spin")} />
                        {sync.isPending ? "Sincronizando…" : "Sincronizar Sentinel-2"}
                    </Button>
                </div>
            </div>

            {!talhaoId ? (
                <p className="text-sm text-muted-foreground text-center py-10">
                    Selecione um talhão para visualizar o NDVI.
                </p>
            ) : loadingSerie ? (
                <div className="space-y-3">
                    <Skeleton className="h-8 w-48" />
                    <Skeleton className="h-56 w-full" />
                </div>
            ) : !serie || serie.total_imagens === 0 ? (
                <div className="text-center py-14 border rounded-lg space-y-3">
                    <Satellite className="size-10 mx-auto text-muted-foreground/50" />
                    <p className="text-sm text-muted-foreground">
                        Nenhuma imagem NDVI para <strong>{talhaoNome}</strong>.
                    </p>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => sync.mutate()}
                        disabled={sync.isPending}
                    >
                        <RefreshCw className={cn("size-4 mr-1.5", sync.isPending && "animate-spin")} />
                        Buscar imagens agora
                    </Button>
                </div>
            ) : (
                <>
                    {/* KPIs */}
                    <div className="grid gap-4 md:grid-cols-3">
                        <Card>
                            <CardContent className="p-4">
                                <p className="text-xs text-muted-foreground mb-1">NDVI Atual</p>
                                <p className={cn("text-2xl font-bold", ndviColor(serie.indice_atual))}>
                                    {serie.indice_atual?.toFixed(3) ?? "—"}
                                </p>
                                {serie.indice_atual != null && (
                                    <p className="text-xs text-muted-foreground mt-0.5">
                                        {ndviLabel(serie.indice_atual)}
                                    </p>
                                )}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardContent className="p-4">
                                <p className="text-xs text-muted-foreground mb-1">Tendência</p>
                                <div className={cn("flex items-center gap-1.5 text-lg font-semibold", trendColor)}>
                                    <TrendIcon className="size-5" />
                                    {serie.tendencia === "SUBINDO"
                                        ? "Subindo"
                                        : serie.tendencia === "CAINDO"
                                        ? "Caindo"
                                        : "Estável"}
                                </div>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    {serie.total_imagens} imagens registradas
                                </p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardContent className="p-4">
                                <p className="text-xs text-muted-foreground mb-1">Última Captura</p>
                                <p className="text-lg font-semibold">
                                    {chartData.length > 0
                                        ? format(
                                              new Date(
                                                  chartData[chartData.length - 1].dataRaw + "T12:00:00"
                                              ),
                                              "dd/MM/yyyy",
                                              { locale: ptBR }
                                          )
                                        : "—"}
                                </p>
                                {imagens[imagens.length - 1]?.cobertura_nuvens_pct != null && (
                                    <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                                        <Cloud className="size-3" />
                                        {imagens[imagens.length - 1].cobertura_nuvens_pct!.toFixed(0)}% cobertura de nuvens
                                    </p>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Gráfico */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Série Temporal NDVI — {talhaoNome}</CardTitle>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <ResponsiveContainer width="100%" height={240}>
                                <LineChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
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
                                        tickFormatter={(v) => v.toFixed(1)}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    {/* Faixas de referência */}
                                    <ReferenceLine y={0.6} stroke="#10b981" strokeDasharray="4 4" label={{ value: "0.6", fontSize: 10, fill: "#10b981" }} />
                                    <ReferenceLine y={0.4} stroke="#eab308" strokeDasharray="4 4" label={{ value: "0.4", fontSize: 10, fill: "#eab308" }} />
                                    <ReferenceLine y={0.2} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "0.2", fontSize: 10, fill: "#ef4444" }} />
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
                            <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2 flex-wrap">
                                <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-emerald-500 rounded" /> NDVI médio</span>
                                <span className="flex items-center gap-1"><span className="inline-block w-3 h-px border-t border-dashed border-emerald-500" /> ≥0.6 densa</span>
                                <span className="flex items-center gap-1"><span className="inline-block w-3 h-px border-t border-dashed border-yellow-500" /> ≥0.4 moderada</span>
                                <span className="flex items-center gap-1"><span className="inline-block w-3 h-px border-t border-dashed border-red-500" /> ≥0.2 esparsa</span>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Tabela de registros */}
                    {!loadingImagens && imagens.length > 0 && (
                        <div className="rounded-lg border overflow-hidden">
                            <table className="w-full text-sm">
                                <thead className="bg-muted/50">
                                    <tr>
                                        <th className="text-left px-4 py-2.5 font-medium">Data</th>
                                        <th className="text-right px-4 py-2.5 font-medium">NDVI Médio</th>
                                        <th className="text-right px-4 py-2.5 font-medium hidden sm:table-cell">Mín</th>
                                        <th className="text-right px-4 py-2.5 font-medium hidden sm:table-cell">Máx</th>
                                        <th className="text-right px-4 py-2.5 font-medium">Nuvens</th>
                                        <th className="text-left px-4 py-2.5 font-medium hidden md:table-cell">Classificação</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y">
                                    {[...imagens]
                                        .sort((a, b) => b.data_captura.localeCompare(a.data_captura))
                                        .map((img) => (
                                            <tr key={img.id} className="hover:bg-muted/20">
                                                <td className="px-4 py-2.5">
                                                    {format(new Date(img.data_captura + "T12:00:00"), "dd/MM/yyyy", { locale: ptBR })}
                                                </td>
                                                <td className="px-4 py-2.5 text-right">
                                                    {img.indice_medio != null ? (
                                                        <Badge className={cn("font-mono text-xs", ndviBadgeClass(img.indice_medio))}>
                                                            {img.indice_medio.toFixed(3)}
                                                        </Badge>
                                                    ) : "—"}
                                                </td>
                                                <td className="px-4 py-2.5 text-right text-muted-foreground hidden sm:table-cell">
                                                    {img.indice_minimo?.toFixed(3) ?? "—"}
                                                </td>
                                                <td className="px-4 py-2.5 text-right text-muted-foreground hidden sm:table-cell">
                                                    {img.indice_maximo?.toFixed(3) ?? "—"}
                                                </td>
                                                <td className="px-4 py-2.5 text-right">
                                                    {img.cobertura_nuvens_pct != null ? (
                                                        <span className={cn("text-xs", img.cobertura_nuvens_pct > 30 ? "text-amber-600" : "text-muted-foreground")}>
                                                            {img.cobertura_nuvens_pct.toFixed(0)}%
                                                        </span>
                                                    ) : "—"}
                                                </td>
                                                <td className="px-4 py-2.5 text-xs text-muted-foreground hidden md:table-cell">
                                                    {ndviLabel(img.indice_medio)}
                                                </td>
                                            </tr>
                                        ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
