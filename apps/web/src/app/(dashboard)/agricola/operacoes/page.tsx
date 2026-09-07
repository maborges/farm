"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
    Tractor, Plus, ThermometerSun, Wind, Trash2,
    Settings2, Calendar, Sprout, AlertCircle, XCircle, Save, CheckCircle2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
    DialogTrigger, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useForm, Controller, useFieldArray, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
    OperacaoAgricolaCreateSchema, type OperacaoAgricolaCreate,
    OperacaoAgricolaResponse,
} from "@farm/zod-schemas";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { formatDateShort } from "@farm/utils";

interface Safra { id: string; ano_safra: string; cultura: string; status: string; }
interface AreaRural { id: string; nome: string; area_ha: number; tipo: string; }
interface Produto { id: string; nome: string; unidade_padrao: string; tipo: string; }
interface TipoOperacao { id: string; tipo_operacao: string; fases_permitidas: string[]; descricao?: string | null; }

const STATUS_BADGE: Record<string, string> = {
    REALIZADA: "bg-blue-600 text-white",
    EM_ANDAMENTO: "bg-yellow-500 text-white",
    PLANEJADA: "bg-slate-400 text-white",
};

export default function OperacoesPage() {
    const queryClient = useQueryClient();
    const activeFazendaId = useAppStore((s) => s.activeFazendaId);

    const [selectedSafraId, setSelectedSafraId] = useState<string>("all");
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [efetivarRow, setEfetivarRow] = useState<OperacaoAgricolaResponse | null>(null);
    const [dataEfetivacao, setDataEfetivacao] = useState<string>("");

    // ── Data fetching ──────────────────────────────────────────────────────────
    const { data: safras = [], isLoading: isLoadingSafras } = useQuery<Safra[]>({
        queryKey: ["safras"],
        queryFn: () => apiFetch("/safras"),
    });

    const { data: talhoes = [] } = useQuery<AreaRural[]>({
        queryKey: ["areas-rurais", "talhoes", activeFazendaId],
        queryFn: () => {
            const params = new URLSearchParams({ tipo: "TALHAO" });
            if (activeFazendaId) params.set("unidade_produtiva_id", activeFazendaId);
            return apiFetch(`/cadastros/areas-rurais/?${params}`);
        },
        enabled: true,
    });

    const { data: produtos = [] } = useQuery<Produto[]>({
        queryKey: ["produtos-insumos"],
        queryFn: () => apiFetch("/cadastros/produtos?ativo=true"),
        staleTime: 5 * 60 * 1000,
    });

    const { data: tiposOperacao = [] } = useQuery<TipoOperacao[]>({
        queryKey: ["operacoes-tipos"],
        queryFn: () => apiFetch("/operacoes/tipos"),
        staleTime: 5 * 60 * 1000,
    });

    const activeSafras = safras.filter((s) => !["ENCERRADA", "CANCELADA"].includes(s.status));
    const safraSelecionadaParam = selectedSafraId === "all" ? undefined : selectedSafraId;
    const apiUrl = safraSelecionadaParam
        ? `/operacoes?safra_id=${safraSelecionadaParam}`
        : "/operacoes";

    const { data: operacoes = [], isLoading: isLoadingOps } = useQuery<OperacaoAgricolaResponse[]>({
        queryKey: ["operacoes", safraSelecionadaParam],
        queryFn: () => apiFetch(apiUrl),
    });

    // ── Mutations ──────────────────────────────────────────────────────────────
    const createMutation = useMutation({
        mutationFn: (data: OperacaoAgricolaCreate) =>
            apiFetch("/operacoes/", { method: "POST", body: JSON.stringify(data) }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["operacoes"] });
            toast.success("Registro salvo no caderno de campo!");
            setIsAddOpen(false);
            reset();
        },
        onError: (err: any) => toast.error(err?.message ?? "Erro ao registrar operação"),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/operacoes/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["operacoes"] });
            toast.success("Operação removida.");
            setDeleteId(null);
        },
        onError: () => toast.error("Erro ao remover operação."),
    });

    const efetivarMutation = useMutation({
        mutationFn: ({ id, data_realizada }: { id: string; data_realizada: string }) =>
            apiFetch(`/operacoes/${id}`, {
                method: "PATCH",
                body: JSON.stringify({ status: "REALIZADA", data_realizada }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["operacoes"] });
            toast.success("OS efetivada com sucesso.");
            setEfetivarRow(null);
        },
        onError: (err: any) => toast.error(err?.message ?? "Erro ao efetivar a OS."),
    });

    // ── Form ───────────────────────────────────────────────────────────────────
    const { register, handleSubmit, control, reset, watch, formState: { errors } } = useForm<OperacaoAgricolaCreate>({
        resolver: zodResolver(OperacaoAgricolaCreateSchema) as unknown as Resolver<OperacaoAgricolaCreate>,
        defaultValues: {
            safra_id: "",
            talhao_id: "",
            tipo: "PULVERIZAÇÃO",
            descricao: "",
            data_realizada: new Date().toISOString().split("T")[0],
            insumos: [],
            status: "REALIZADA",
            custo_total: 0,
            custo_por_ha: 0,
            subtipo: null,
            data_prevista: null,
            hora_inicio: null,
            hora_fim: null,
            maquina_id: null,
            implemento: null,
            operador_id: null,
            temperatura_c: null,
            umidade_rel: null,
            vento_kmh: null,
            direcao_vento: null,
            condicao_clima: null,
            latitude: null,
            longitude: null,
            fase_safra: null,
            observacoes: null,
            fotos: []
        },
    });

    const { fields: insumosFields, append: appendInsumo, remove: removeInsumo } = useFieldArray({
        control,
        name: "insumos",
    });
    const talhaoSelecionadoId = watch("talhao_id");
    const talhaoSelecionado = talhoes.find((talhao) => talhao.id === talhaoSelecionadoId);

    const getTipoLabel = (tipo: string) =>
        tiposOperacao.find((item) => item.tipo_operacao === tipo)?.descricao || tipo;

    const optionalNumberField = {
        setValueAs: (value: string) => (value === "" ? null : Number(value)),
    };

    // ── Table columns ──────────────────────────────────────────────────────────
    const columns: ColumnDef<OperacaoAgricolaResponse>[] = [
        {
            id: "data",
            header: "Data",
            accessorKey: "data_realizada",
            sortable: true,
            cell: (val: string) => (
                <div className="flex items-center gap-1.5">
                    <Calendar className="size-3.5 text-muted-foreground" />
                    {formatDateShort(val)}
                </div>
            ),
        },
        {
            id: "tipo",
            header: "Tipo",
            accessorKey: "tipo",
            sortable: true,
            filterable: true,
            cell: (val: string) => <Badge variant="secondary" className="font-semibold">{getTipoLabel(val)}</Badge>,
        },
        {
            id: "descricao",
            header: "Descrição",
            accessorKey: "descricao",
            cell: (val: string) => (
                <span className="block max-w-[min(28rem,35vw)] whitespace-normal break-words text-sm font-medium">
                    {val}
                </span>
            ),
        },
        {
            id: "clima",
            header: "Clima",
            cell: (_: unknown, row: OperacaoAgricolaResponse) => (
                <div className="flex flex-col gap-0.5 text-xs text-muted-foreground">
                    {row.temperatura_c && (
                        <span className="flex items-center gap-1">
                            <ThermometerSun className="size-3" /> {row.temperatura_c}°C
                        </span>
                    )}
                    {row.vento_kmh && (
                        <span className="flex items-center gap-1">
                            <Wind className="size-3" /> {row.vento_kmh} km/h
                        </span>
                    )}
                    {!row.temperatura_c && !row.vento_kmh && (
                        <span className="italic">Não inf.</span>
                    )}
                </div>
            ),
        },
        {
            id: "insumos",
            header: "Insumos",
            cell: (_: unknown, row: OperacaoAgricolaResponse) => (
                <div className="flex gap-1 flex-wrap">
                    {row.insumos?.length > 0 ? (
                        row.insumos.map((ins, i) => (
                            <Badge key={i} variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200">
                                {ins.dose_por_ha.toFixed(1)} {ins.unidade}/ha
                            </Badge>
                        ))
                    ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                    )}
                </div>
            ),
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            sortable: true,
            filterable: true,
            cell: (val: string) => (
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${STATUS_BADGE[val] ?? "bg-muted text-muted-foreground"}`}>
                    {val}
                </span>
            ),
        },
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            cell: (_: unknown, row: OperacaoAgricolaResponse) => (
                <div className="flex items-center gap-0 justify-end">
                    {row.status === "PLANEJADA" && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="size-7 text-primary hover:text-primary"
                            onClick={() => {
                                setDataEfetivacao(new Date().toISOString().split("T")[0]);
                                setEfetivarRow(row);
                            }}
                            aria-label="Efetivar OS"
                            title="Efetivar OS (marcar como Realizada)"
                        >
                            <CheckCircle2 className="size-3.5" />
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-destructive hover:text-destructive"
                        onClick={() => setDeleteId(row.id)}
                        aria-label="Excluir operação"
                    >
                        <Trash2 className="size-3.5" />
                    </Button>
                </div>
            ),
        },
    ];

    if (isLoadingSafras || isLoadingOps) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-10 w-64 rounded-sm" />
                <Skeleton className="h-12 w-full rounded-sm" />
                <Skeleton className="h-96 w-full rounded-sm" />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Operações do Campo"
                description="Registro, histórico e rastreabilidade das operações agrícolas."
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Operações do Campo" }]}
                icon={<Tractor className="text-primary" size={22} />}
                actions={
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => window.open(`/api/v1/operacoes/export/pdf${safraSelecionadaParam ? `?safra_id=${safraSelecionadaParam}` : ""}`)}
                        >
                            Baixar PDF
                        </Button>

                        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                            <DialogTrigger
                                render={
                                    <Button variant="outline" size="sm" className="rounded-sm">
                                        <Plus className="size-3.5 mr-1.5" /> Registrar no Caderno
                                    </Button>
                                }
                            />
                            <DialogContent className="max-w-xl p-0">
                                <form onSubmit={handleSubmit((d) => createMutation.mutate(d as OperacaoAgricolaCreate))}>
                                    <DialogHeader>
                                        <DialogTitle className="flex items-center gap-2.5">
                                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                                                <Tractor className="size-4 text-primary" />
                                            </div>
                                            Novo Registro no Caderno
                                        </DialogTitle>
                                    </DialogHeader>

                                    <DialogBody className="grid gap-4 max-h-[70vh] overflow-y-auto">
                                        {/* Safra + Talhão */}
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-2">
                                                <Label htmlFor="safra_id">Safra</Label>
                                                <Controller
                                                    name="safra_id"
                                                    control={control}
                                                    render={({ field }) => {
                                                        const safraSelecionada = activeSafras.find(s => s.id === field.value);
                                                        return (
                                                            <Select value={field.value || ""} onValueChange={field.onChange}>
                                                                <SelectTrigger id="safra_id" className="h-8 text-xs rounded-sm">
                                                                    <SelectValue placeholder={safraSelecionada ? `${safraSelecionada.cultura} — ${safraSelecionada.ano_safra}` : "Selecione a safra"} />
                                                                </SelectTrigger>
                                                                <SelectContent className="rounded-sm">
                                                                    {activeSafras.map((s) => (
                                                                        <SelectItem key={s.id} value={s.id}>
                                                                            {s.cultura} — {s.ano_safra}
                                                                        </SelectItem>
                                                                    ))}
                                                                </SelectContent>
                                                            </Select>
                                                        );
                                                    }}
                                                />
                                                {errors.safra_id && <p className="text-xs text-destructive">{errors.safra_id.message}</p>}
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="talhao_id">Talhão</Label>
                                                <Controller
                                                    name="talhao_id"
                                                    control={control}
                                                    render={({ field }) => {
                                                        const talhaoSelecionado = talhoes.find(t => t.id === field.value);
                                                        return (
                                                            <Select value={field.value || ""} onValueChange={field.onChange}>
                                                                <SelectTrigger id="talhao_id" className="h-8 text-xs rounded-sm">
                                                                    <SelectValue placeholder={talhaoSelecionado ? `${talhaoSelecionado.nome} (${talhaoSelecionado.area_ha} ha)` : "Selecione o talhão"} />
                                                                </SelectTrigger>
                                                                <SelectContent className="rounded-sm">
                                                                    {talhoes.map((t) => (
                                                                        <SelectItem key={t.id} value={t.id}>
                                                                            {t.nome}{t.area_ha ? ` (${t.area_ha} ha)` : ""}
                                                                        </SelectItem>
                                                                    ))}
                                                                </SelectContent>
                                                            </Select>
                                                        );
                                                    }}
                                                />
                                                {errors.talhao_id && <p className="text-xs text-destructive">{errors.talhao_id.message}</p>}
                                            </div>
                                        </div>

                                        {/* Tipo + Data + Status */}
                                        <div className="grid grid-cols-3 gap-4">
                                            <div className="space-y-2">
                                                <Label htmlFor="tipo">Tipo</Label>
                                                <Controller
                                                    name="tipo"
                                                    control={control}
                                                    render={({ field }) => {
                                                        const tipoSelecionado = tiposOperacao.find((t) => t.tipo_operacao === field.value);
                                                        return (
                                                        <Select value={field.value || ""} onValueChange={field.onChange}>
                                                            <SelectTrigger id="tipo" className="h-8 text-xs rounded-sm">
                                                                <SelectValue placeholder={tipoSelecionado?.descricao || tipoSelecionado?.tipo_operacao || "Selecione"} />
                                                            </SelectTrigger>
                                                            <SelectContent className="rounded-sm">
                                                                {tiposOperacao.map((t) => (
                                                                    <SelectItem key={t.id} value={t.tipo_operacao}>
                                                                        {t.descricao || t.tipo_operacao}
                                                                    </SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    )}}
                                                />
                                                {errors.tipo && <p className="text-xs text-destructive">{errors.tipo.message}</p>}
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="data_realizada">Data Realizada</Label>
                                                <Input id="data_realizada" type="date" className="h-8 text-xs rounded-sm" {...register("data_realizada")} />
                                                {errors.data_realizada && <p className="text-xs text-destructive">{errors.data_realizada.message}</p>}
                                            </div>
                                            <div className="space-y-2">
                                                <Label htmlFor="status">Status</Label>
                                                <Controller
                                                    name="status"
                                                    control={control}
                                                    render={({ field }) => {
                                                        const statusLabels: Record<string, string> = {
                                                            REALIZADA: "Realizada",
                                                            EM_ANDAMENTO: "Em Andamento",
                                                            PLANEJADA: "Planejada",
                                                        };
                                                        return (
                                                            <Select value={field.value || ""} onValueChange={field.onChange}>
                                                                <SelectTrigger id="status" className="h-8 text-xs rounded-sm">
                                                                    <SelectValue placeholder={field.value ? statusLabels[field.value] : "Selecione"} />
                                                                </SelectTrigger>
                                                                <SelectContent className="rounded-sm">
                                                                    <SelectItem value="REALIZADA">Realizada</SelectItem>
                                                                    <SelectItem value="EM_ANDAMENTO">Em Andamento</SelectItem>
                                                                    <SelectItem value="PLANEJADA">Planejada</SelectItem>
                                                                </SelectContent>
                                                            </Select>
                                                        );
                                                    }}
                                                />
                                                {errors.status && <p className="text-xs text-destructive">{errors.status.message}</p>}
                                            </div>
                                        </div>

                                        {/* Descrição */}
                                        <div className="space-y-2">
                                            <Label htmlFor="descricao">Descrição</Label>
                                            <Input id="descricao" className="h-8 text-xs rounded-sm" placeholder="Ex: Aplicação de Fungicida Preventivo" {...register("descricao")} />
                                            {errors.descricao && <p className="text-xs text-destructive">{errors.descricao.message}</p>}
                                        </div>

                                        <div className="space-y-2">
                                            <Label htmlFor="area_aplicada_ha">Área Aplicada (ha)</Label>
                                            <Input
                                                id="area_aplicada_ha"
                                                type="number"
                                                step="0.01"
                                                max={talhaoSelecionado?.area_ha ?? undefined}
                                                className="h-8 text-xs rounded-sm"
                                                placeholder={talhaoSelecionado?.area_ha ? `Máx. ${talhaoSelecionado.area_ha} ha` : "0.00"}
                                                {...register("area_aplicada_ha", {
                                                    valueAsNumber: true,
                                                    validate: (value) => {
                                                        if (!Number.isFinite(value) || value <= 0) {
                                                            return "Área aplicada deve ser maior que zero";
                                                        }
                                                        if (talhaoSelecionado?.area_ha != null && value > talhaoSelecionado.area_ha) {
                                                            return `Área aplicada não pode ser maior que ${talhaoSelecionado.area_ha} ha`;
                                                        }
                                                        return true;
                                                    },
                                                })}
                                            />
                                            {errors.area_aplicada_ha && <p className="text-xs text-destructive">{errors.area_aplicada_ha.message}</p>}
                                        </div>

                                        {/* Clima */}
                                        <div className="rounded-sm border bg-muted/20 p-4 space-y-4">
                                            <h4 className="text-xs font-semibold uppercase text-muted-foreground flex items-center gap-1.5">
                                                <ThermometerSun className="size-3.5" /> Condições Climáticas (opcional)
                                            </h4>
                                            <div className="grid grid-cols-3 gap-4">
                                                <div className="space-y-2">
                                                    <Label htmlFor="temperatura_c" className="text-xs font-medium">Temperatura (°C)</Label>
                                                    <Input id="temperatura_c" type="number" step="0.1" className="h-8 text-xs rounded-sm" placeholder="25.5" {...register("temperatura_c", optionalNumberField)} />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label htmlFor="umidade_rel" className="text-xs font-medium">Umidade (%)</Label>
                                                    <Input id="umidade_rel" type="number" step="0.1" className="h-8 text-xs rounded-sm" placeholder="60" {...register("umidade_rel", optionalNumberField)} />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label htmlFor="vento_kmh" className="text-xs font-medium">Vento (km/h)</Label>
                                                    <Input id="vento_kmh" type="number" step="0.1" className="h-8 text-xs rounded-sm" placeholder="12" {...register("vento_kmh", optionalNumberField)} />
                                                </div>
                                            </div>
                                        </div>

                                        {/* Insumos */}
                                        <div className="rounded-sm border bg-muted/20 p-4 space-y-4">
                                            <div className="flex items-center justify-between">
                                                <h4 className="text-xs font-semibold uppercase text-muted-foreground flex items-center gap-1.5">
                                                    <Sprout className="size-3.5" /> Insumos Aplicados
                                                </h4>
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    size="sm"
                                                    className="rounded-sm h-8 text-xs"
                                                    onClick={() => appendInsumo({ produto_id: "", dose_por_ha: 0, unidade: "L" })}
                                                >
                                                    <Plus className="size-3.5 mr-1" />
                                                    Adicionar
                                                </Button>
                                            </div>

                                            {insumosFields.length === 0 && (
                                                <p className="text-sm text-muted-foreground text-center py-2">
                                                    Nenhum insumo vinculado. Clique em &quot;Adicionar&quot; para incluir.
                                                </p>
                                            )}

                                            {insumosFields.map((field, index) => (
                                                <div key={field.id} className="flex items-end gap-3 rounded-sm border bg-background p-3">
                                                    <div className="flex-1 space-y-2">
                                                        <Label htmlFor={`insumos.${index}.produto_id`}>Produto</Label>
                                                        <Controller
                                                            name={`insumos.${index}.produto_id`}
                                                            control={control}
                                                            render={({ field: f }) => {
                                                                const produtoSelecionado = produtos.find(p => p.id === f.value);
                                                                return (
                                                                    <Select value={f.value || ""} onValueChange={f.onChange}>
                                                                        <SelectTrigger id={`insumos.${index}.produto_id`} className="h-8 text-xs rounded-sm">
                                                                            <SelectValue placeholder={produtoSelecionado ? produtoSelecionado.nome : "Selecionar produto"} />
                                                                        </SelectTrigger>
                                                                        <SelectContent className="rounded-sm">
                                                                            {produtos.map((p) => (
                                                                                <SelectItem key={p.id} value={p.id}>
                                                                                    {p.nome}
                                                                                </SelectItem>
                                                                            ))}
                                                                        </SelectContent>
                                                                    </Select>
                                                                );
                                                            }}
                                                        />
                                                        {errors.insumos?.[index]?.produto_id && (
                                                            <p className="text-xs text-destructive">{errors.insumos[index]?.produto_id?.message}</p>
                                                        )}
                                                    </div>
                                                    <div className="w-24 space-y-2">
                                                        <Label htmlFor={`insumos.${index}.dose_por_ha`} className="text-xs">Dose/ha</Label>
                                                        <Input
                                                            id={`insumos.${index}.dose_por_ha`}
                                                            type="number"
                                                            step="0.01"
                                                            className="h-8 text-xs rounded-sm"
                                                            placeholder="0.00"
                                                            {...register(`insumos.${index}.dose_por_ha`, { valueAsNumber: true })}
                                                        />
                                                        {errors.insumos?.[index]?.dose_por_ha && (
                                                            <p className="text-xs text-destructive">{errors.insumos[index]?.dose_por_ha?.message}</p>
                                                        )}
                                                    </div>
                                                    <div className="w-20 space-y-2">
                                                        <Label htmlFor={`insumos.${index}.unidade`} className="text-xs">Unidade</Label>
                                                        <Input
                                                            id={`insumos.${index}.unidade`}
                                                            className="h-8 text-xs rounded-sm"
                                                            placeholder="L"
                                                            {...register(`insumos.${index}.unidade`)}
                                                        />
                                                    </div>
                                                    <Button
                                                        type="button"
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-9 w-9 text-muted-foreground hover:text-destructive shrink-0"
                                                        onClick={() => removeInsumo(index)}
                                                    >
                                                        <Trash2 className="size-4" />
                                                    </Button>
                                                </div>
                                            ))}
                                        </div>
                                    </DialogBody>

                                    <DialogFooter>
                                        <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => setIsAddOpen(false)} disabled={createMutation.isPending}>
                                            <XCircle className="size-3.5 mr-1.5" />
                                            Cancelar
                                        </Button>
                                        <Button type="submit" variant="outline" size="sm" className="rounded-sm border-primary/50 text-primary hover:bg-primary/5" disabled={createMutation.isPending}>
                                            <Save className="size-3.5 mr-1.5" />
                                            {createMutation.isPending ? "Salvando..." : "Salvar"}
                                        </Button>
                                    </DialogFooter>
                                </form>
                            </DialogContent>
                        </Dialog>
                    </div>
                }
            />

            {/* Filtro de safra */}
            <Card className="shadow-sm rounded-sm">
                <CardContent className="px-6 py-4">
                    <div className="flex gap-4 items-end max-w-sm">
                        <div className="flex-1 space-y-1.5">
                            <Label className="text-xs uppercase text-muted-foreground tracking-wider">Filtrar por Safra</Label>
                            <Select value={selectedSafraId} onValueChange={setSelectedSafraId}>
                                <SelectTrigger className="font-medium h-8 text-xs rounded-sm">
                                    <SelectValue placeholder="Todas as Safras Ativas" />
                                </SelectTrigger>
                                <SelectContent className="rounded-sm">
                                    <SelectItem value="all">Todas as Safras Ativas</SelectItem>
                                    {activeSafras.map((s) => (
                                        <SelectItem key={s.id} value={s.id}>
                                            {s.cultura} — {s.ano_safra}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Tabela */}
            <DataTable
                data={operacoes}
                columns={columns}
                searchable
                searchPlaceholder="Buscar por descrição, tipo ou status..."
                exportable
                emptyMessage="Nenhuma operação agrícola registrada."
            />

            {/* Efetivar OS */}
            <AlertDialog open={!!efetivarRow} onOpenChange={(v) => { if (!v) setEfetivarRow(null); }}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2">
                            <CheckCircle2 className="size-4 text-primary" /> Efetivar OS?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            A operação &quot;{efetivarRow?.descricao}&quot; será marcada como Realizada, gerando os
                            efeitos de estoque, custo e caderno de campo. Esta ação não pode ser desfeita.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <div className="space-y-2 px-1">
                        <Label htmlFor="data_efetivacao">Data de execução</Label>
                        <Input
                            id="data_efetivacao"
                            type="date"
                            className="h-8 text-xs rounded-sm"
                            value={dataEfetivacao}
                            max={new Date().toISOString().split("T")[0]}
                            onChange={(e) => setDataEfetivacao(e.target.value)}
                        />
                    </div>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => efetivarRow && efetivarMutation.mutate({ id: efetivarRow.id, data_realizada: dataEfetivacao })}
                            disabled={efetivarMutation.isPending || !dataEfetivacao}
                        >
                            {efetivarMutation.isPending ? "Efetivando..." : "Efetivar"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Confirm delete */}
            <AlertDialog open={!!deleteId} onOpenChange={(v) => { if (!v) setDeleteId(null); }}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2">
                            <AlertCircle className="size-4 text-destructive" /> Remover operação?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            Esta ação não pode ser desfeita. O registro será removido do caderno de campo.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            className="bg-destructive hover:bg-destructive/90"
                            onClick={() => deleteId && deleteMutation.mutate(deleteId)}
                            disabled={deleteMutation.isPending}
                        >
                            Remover
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
