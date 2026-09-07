"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useForm, Controller, useFieldArray } from "react-hook-form";
import { toast } from "sonner";
import { Plus, DollarSign, Layers, BarChart2, Activity, CheckCircle2, XCircle, Pencil, ClipboardList, Sprout, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { getSafraLabel } from "@/lib/safra-label";

const FASES = [
    { key: "PLANEJADA",       label: "Planejamento" },
    { key: "PREPARO_SOLO",    label: "Preparo Solo" },
    { key: "PLANTIO",         label: "Plantio" },
    { key: "DESENVOLVIMENTO", label: "Desenvolvimento" },
    { key: "COLHEITA",        label: "Colheita" },
    { key: "POS_COLHEITA",    label: "Pós-Colheita" },
    { key: "ENCERRADA",       label: "Encerrada" },
];

interface Cultivo {
    id: string;
    cultura: string | null;
    cultivar_nome: string | null;
}

interface TipoOperacao {
    id: string;
    tipo_operacao: string;
    fases_permitidas: string[];
    descricao?: string | null;
}

interface FaseKPI {
    fase: string;
    total_operacoes: number;
    custo_total: number;
    custo_por_ha: number;
    area_total_ha: number;
}

interface ResumoFase {
    safra_id: string;
    fases: FaseKPI[];
    custo_total_safra: number;
}

interface Operacao {
    id: string;
    talhao_id: string;
    tipo: string;
    subtipo: string | null;
    descricao: string;
    fase_safra: string | null;
    data_realizada: string;
    area_aplicada_ha: number | null;
    custo_total: number;
    custo_por_ha: number;
    status: string;
    insumos: Array<{
        id: string;
        produto_id: string;
        dose_por_ha: number;
        unidade: string;
    }>;
}

interface OperacaoUpdateForm {
    tipo: string;
    descricao: string;
    data_realizada: string;
    fase_safra: string;
    area_aplicada_ha: string;
    custo_total: string;
    insumos: InsumoCreateForm[];
}

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
    status: string;
}

interface AreaRural {
    id: string;
    nome: string;
    unidade_produtiva_id: string;
    area_hectares: number | null;
    area_hectares_manual?: number | null;
}

interface PessoaRelacionamento {
    id: string;
    unidade_produtiva_id: string | null;
    ativo_desde?: string | null;
    ativo_ate?: string | null;
    tipo: {
        id: string;
        codigo: string;
        nome: string;
    };
}

interface Pessoa {
    id: string;
    tipo: "PF" | "PJ";
    nome_exibicao: string;
    relacionamentos: PessoaRelacionamento[];
}

interface Equipamento {
    id: string;
    nome: string;
    tipo: string;
    marca?: string;
    modelo?: string;
    status: string;
}

interface Produto {
    id: string;
    nome: string;
    unidade_padrao?: string | null;
}

interface InsumoCreateForm {
    produto_id: string;
    dose_por_ha: number;
    unidade: string;
}

interface OperacaoCreateForm {
    talhao_id: string;
    tipo: string;
    descricao: string;
    data_realizada: string;
    fase_safra: string;
    area_aplicada_ha: string;
    custo_total: string;
    cultivo_id: string;
    hora_inicio: string;
    hora_fim: string;
    maquina_id: string;
    implemento: string;
    operador_id: string;
    observacoes: string;
    insumos: InsumoCreateForm[];
}

function fmt(d: string) {
    return format(new Date(d + "T12:00:00"), "dd/MM/yyyy", { locale: ptBR });
}

function moeda(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function getTalhaoAreaLabel(area: AreaRural) {
    const tamanho = area.area_hectares ?? area.area_hectares_manual;
    return tamanho != null ? `${area.nome} (${tamanho} ha)` : area.nome;
}

function getTalhaoAreaLimite(area: AreaRural | null | undefined) {
    return area?.area_hectares ?? area?.area_hectares_manual ?? null;
}

function emptyToNull<T>(value: T | ""): T | null {
    return value === "" ? null : value;
}

function isRelacionamentoAtivoHoje(relacionamento: PessoaRelacionamento) {
    const hoje = new Date();
    const inicio = relacionamento.ativo_desde ? new Date(`${relacionamento.ativo_desde}T00:00:00`) : null;
    const fim = relacionamento.ativo_ate ? new Date(`${relacionamento.ativo_ate}T23:59:59`) : null;

    if (inicio && inicio > hoje) return false;
    if (fim && fim < hoje) return false;
    return true;
}

const FASE_LABEL: Record<string, string> = Object.fromEntries(FASES.map(f => [f.key, f.label]));

const buildColunas = (
    onEdit: (operacao: Operacao) => void,
    getTipoLabel: (tipo: string) => string,
): ColumnDef<Operacao>[] => [
    {
        id: "data",
        header: "Data",
        accessorFn: (r) => fmt(r.data_realizada),
        sortable: true,
        cell: (v: string) => <span className="tabular-nums text-sm">{v}</span>,
    },
    {
        id: "tipo",
        header: "Tipo",
        accessorKey: "tipo",
        sortable: true,
        filterable: true,
        cell: (v: string) => <Badge variant="outline" className="text-xs">{getTipoLabel(v)}</Badge>,
    },
    {
        id: "descricao",
        header: "Descrição",
        accessorKey: "descricao",
        sortable: false,
        cell: (v: string) => <span className="text-sm line-clamp-1">{v}</span>,
    },
    {
        id: "area",
        header: "Área (ha)",
        accessorFn: (r) => r.area_aplicada_ha ? `${r.area_aplicada_ha} ha` : "—",
        sortable: true,
        cell: (v: string) => <span className="tabular-nums text-sm">{v}</span>,
    },
    {
        id: "custo",
        header: "Custo Total",
        accessorFn: (r) => moeda(r.custo_total),
        sortable: true,
        cell: (v: string) => <span className="tabular-nums text-sm font-medium">{v}</span>,
    },
    {
        id: "custo_ha",
        header: "R$/ha",
        accessorFn: (r) => r.custo_por_ha > 0 ? moeda(r.custo_por_ha) : "—",
        sortable: true,
        cell: (v: string) => <span className="tabular-nums text-xs text-muted-foreground">{v}</span>,
    },
    {
        id: "insumos",
        header: "Insumos",
        sortable: false,
        filterable: false,
        cell: (_: unknown, row: Operacao) => (
            <div className="flex flex-wrap gap-1">
                {row.insumos?.length > 0 ? (
                    row.insumos.map((insumo) => (
                        <Badge
                            key={insumo.id}
                            variant="outline"
                            className="border-emerald-200 bg-emerald-50 text-[10px] text-emerald-700"
                        >
                            {insumo.dose_por_ha.toFixed(1)} {insumo.unidade}/ha
                        </Badge>
                    ))
                ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                )}
            </div>
        ),
    },
    {
        id: "acoes",
        header: "",
        sortable: false,
        filterable: false,
        cell: (_: unknown, row: Operacao) => (
            <div className="flex justify-end">
                <Button
                    variant="ghost"
                    size="icon"
                    className="size-8"
                    onClick={() => onEdit(row)}
                    aria-label="Editar operação"
                >
                    <Pencil className="size-3.5" />
                </Button>
            </div>
        ),
    },
];

export default function OperacoesPorFasePage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const queryClient = useQueryClient();
    const [faseSelecionada, setFaseSelecionada] = useState("PLANEJADA");
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [editOperacao, setEditOperacao] = useState<Operacao | null>(null);

    const { data: safra } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = safra ? getSafraLabel(safra) : "";

    const { data: resumo, isLoading: loadingResumo } = useQuery<ResumoFase>({
        queryKey: ["operacoes-por-fase", id],
        queryFn: () => apiFetch(`/operacoes/safra/${id}/por-fase`),
    });

    const { data: operacoesFase, isLoading: loadingOps } = useQuery<Operacao[]>({
        queryKey: ["operacoes-fase", id, faseSelecionada],
        queryFn: () => apiFetch(`/operacoes/safra/${id}/fase/${faseSelecionada}`),
    });

    const { data: cultivos = [] } = useQuery<Cultivo[]>({
        queryKey: ["cultivos", id],
        queryFn: () => apiFetch(`/safras/${id}/cultivos`),
        enabled: !!id,
    });

    const { data: tiposOperacao = [] } = useQuery<TipoOperacao[]>({
        queryKey: ["operacoes-tipos"],
        queryFn: () => apiFetch("/operacoes/tipos"),
        staleTime: 5 * 60 * 1000,
    });

    const { data: todasAreas = [] } = useQuery<AreaRural[]>({
        queryKey: ["areas-rurais-talhoes"],
        queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
    });
    const { data: pessoas = [] } = useQuery<Pessoa[]>({
        queryKey: ["cadastros-pessoas-ativas"],
        queryFn: () => apiFetch("/cadastros/pessoas"),
    });
    const { data: equipamentos = [] } = useQuery<Equipamento[]>({
        queryKey: ["cadastros-equipamentos-ativos"],
        queryFn: () => apiFetch("/cadastros/equipamentos?status=ATIVO"),
    });
    const { data: produtos = [] } = useQuery<Produto[]>({
        queryKey: ["produtos-insumos"],
        queryFn: () => apiFetch("/cadastros/produtos?ativo=true"),
        staleTime: 5 * 60 * 1000,
    });

    const getTipoLabel = (tipo: string) =>
        tiposOperacao.find((item) => item.tipo_operacao === tipo)?.descricao || tipo;

    const {
        register,
        handleSubmit,
        control,
        reset,
        watch,
        formState: { errors },
    } = useForm<OperacaoCreateForm>({
        defaultValues: {
            talhao_id: "",
            tipo: "",
            descricao: "",
            data_realizada: new Date().toISOString().split("T")[0],
            fase_safra: safra?.status ?? "",
            area_aplicada_ha: "",
            custo_total: "0",
            cultivo_id: "",
            hora_inicio: "",
            hora_fim: "",
            maquina_id: "",
            implemento: "",
            operador_id: "",
            observacoes: "",
            insumos: [],
        },
    });
    const { fields: insumosFields, append: appendInsumo, remove: removeInsumo } = useFieldArray({
        control,
        name: "insumos",
    });

    const {
        register: registerEdit,
        handleSubmit: handleSubmitEdit,
        control: controlEdit,
        reset: resetEdit,
        watch: watchEdit,
        formState: { errors: editErrors },
    } = useForm<OperacaoUpdateForm>({
        defaultValues: {
            tipo: "",
            descricao: "",
            data_realizada: "",
            fase_safra: "",
            area_aplicada_ha: "",
            custo_total: "0",
            insumos: [],
        },
    });
    const {
        fields: editInsumosFields,
        append: appendEditInsumo,
        remove: removeEditInsumo,
        replace: replaceEditInsumos,
    } = useFieldArray({
        control: controlEdit,
        name: "insumos",
    });
    const tipoEditValue = watchEdit("tipo");
    const faseEditValue = watchEdit("fase_safra");
    const talhaoCreateId = watch("talhao_id");
    const tipoEditSelecionado = tiposOperacao.find((item) => item.tipo_operacao === tipoEditValue);
    const faseEditSelecionada = FASES.find((item) => item.key === faseEditValue);
    const talhaoSelecionado = todasAreas.find((area) => area.id === talhaoCreateId);
    const limiteAreaCreate = getTalhaoAreaLimite(talhaoSelecionado);
    const talhaoEdicao = todasAreas.find((area) => area.id === editOperacao?.talhao_id);
    const limiteAreaEdit = getTalhaoAreaLimite(talhaoEdicao);
    const operadoresDisponiveis = pessoas.filter((pessoa) =>
        pessoa.tipo === "PF" &&
        !!talhaoSelecionado?.unidade_produtiva_id &&
        pessoa.relacionamentos.some((relacionamento) =>
            relacionamento.unidade_produtiva_id === talhaoSelecionado.unidade_produtiva_id &&
            isRelacionamentoAtivoHoje(relacionamento)
        )
    );
    const mostrarAvisoOperadores = !!talhaoSelecionado && operadoresDisponiveis.length === 0;

    useEffect(() => {
        if (!editOperacao) return;

        resetEdit({
            tipo: editOperacao.tipo,
            descricao: editOperacao.descricao,
            data_realizada: editOperacao.data_realizada,
            fase_safra: editOperacao.fase_safra ?? safra?.status ?? "",
            area_aplicada_ha: editOperacao.area_aplicada_ha != null ? String(editOperacao.area_aplicada_ha) : "",
            custo_total: String(editOperacao.custo_total ?? 0),
            insumos: editOperacao.insumos?.map((insumo) => ({
                produto_id: insumo.produto_id,
                dose_por_ha: Number(insumo.dose_por_ha),
                unidade: insumo.unidade,
            })) ?? [],
        });
    }, [editOperacao, resetEdit, safra?.status]);

    const criarMutation = useMutation({
        mutationFn: (data: any) => apiFetch("/operacoes/", {
            method: "POST",
            body: JSON.stringify({
                ...data,
                safra_id: id,
                cultivo_id: emptyToNull(data.cultivo_id),
                hora_inicio: emptyToNull(data.hora_inicio),
                hora_fim: emptyToNull(data.hora_fim),
                maquina_id: emptyToNull(data.maquina_id),
                implemento: emptyToNull(data.implemento),
                operador_id: emptyToNull(data.operador_id),
                observacoes: emptyToNull(data.observacoes),
                area_aplicada_ha: Number(data.area_aplicada_ha),
                custo_total: data.custo_total ? Number(data.custo_total) : 0,
                insumos: (data.insumos ?? []).map((insumo: InsumoCreateForm) => ({
                    produto_id: insumo.produto_id,
                    dose_por_ha: Number(insumo.dose_por_ha),
                    unidade: insumo.unidade,
                })),
            }),
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["operacoes-por-fase", id] });
            queryClient.invalidateQueries({ queryKey: ["operacoes-fase", id] });
            toast.success("Operação desta safra registrada!");
            setIsAddOpen(false);
            reset();
        },
        onError: (e: any) => toast.error(e?.message ?? "Erro ao registrar operação"),
    });

    const editarMutation = useMutation({
        mutationFn: ({ operacaoId, data }: { operacaoId: string; data: OperacaoUpdateForm }) =>
            apiFetch(`/operacoes/${operacaoId}`, {
                method: "PATCH",
                    body: JSON.stringify({
                        tipo: data.tipo,
                        descricao: data.descricao,
                        data_realizada: data.data_realizada,
                        fase_safra: data.fase_safra,
                        area_aplicada_ha: data.area_aplicada_ha ? Number(data.area_aplicada_ha) : null,
                        custo_total: data.custo_total ? Number(data.custo_total) : 0,
                        insumos: (data.insumos ?? []).map((insumo) => ({
                            produto_id: insumo.produto_id,
                            dose_por_ha: Number(insumo.dose_por_ha),
                            unidade: insumo.unidade,
                        })),
                    }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["operacoes-por-fase", id] });
            queryClient.invalidateQueries({ queryKey: ["operacoes-fase", id] });
            toast.success("Operação atualizada!");
            setEditOperacao(null);
        },
        onError: (e: any) => toast.error(e?.message ?? "Erro ao atualizar operação"),
    });

    const fasesComDados = new Set(resumo?.fases.map(f => f.fase) ?? []);

    if (loadingResumo) {
        return (
            <div className="space-y-6 p-6">
                <Skeleton className="h-10 w-72" />
                <div className="grid grid-cols-4 gap-4">{[1,2,3,4].map(i => <Skeleton key={i} className="h-24" />)}</div>
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title={safraLabel ? `Execução por Fase — ${safraLabel}` : "Execução por Fase"}
                icon={<ClipboardList className="text-blue-600" size={22} />}
                description={safraLabel}
                actions={
                    <Button size="sm" variant="outline" onClick={() => setIsAddOpen(true)} className="rounded-sm h-8 group">
                        <Plus className="size-3.5 mr-1.5 transition-transform group-hover:scale-110" /> Nova Operação desta Safra
                    </Button>
                }
            />

            {/* KPIs gerais */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card className="shadow-sm">
                    <CardContent className="p-4 flex gap-3 items-start">
                        <DollarSign className="size-5 text-muted-foreground mt-0.5" />
                        <div>
                            <p className="text-xs text-muted-foreground">Custo Total Safra</p>
                            <p className="font-bold text-lg">{moeda(resumo?.custo_total_safra ?? 0)}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="shadow-sm">
                    <CardContent className="p-4 flex gap-3 items-start">
                        <Activity className="size-5 text-muted-foreground mt-0.5" />
                        <div>
                            <p className="text-xs text-muted-foreground">Total Operações</p>
                            <p className="font-bold text-lg">{resumo?.fases.reduce((a, f) => a + f.total_operacoes, 0) ?? 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="shadow-sm">
                    <CardContent className="p-4 flex gap-3 items-start">
                        <Layers className="size-5 text-muted-foreground mt-0.5" />
                        <div>
                            <p className="text-xs text-muted-foreground">Fases com Operações</p>
                            <p className="font-bold text-lg">{resumo?.fases.length ?? 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="shadow-sm">
                    <CardContent className="p-4 flex gap-3 items-start">
                        <BarChart2 className="size-5 text-muted-foreground mt-0.5" />
                        <div>
                            <p className="text-xs text-muted-foreground">Fase Atual</p>
                            <p className="font-bold">{FASE_LABEL[safra?.status ?? ""] ?? "—"}</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Barra de custo por fase */}
            {resumo && resumo.fases.length > 0 && (
                <Card className="shadow-sm">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base">Custo por Fase</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                        <div className="space-y-2.5">
                            {FASES.filter(f => fasesComDados.has(f.key)).map(f => {
                                const kpi = resumo.fases.find(r => r.fase === f.key);
                                if (!kpi) return null;
                                const pct = resumo.custo_total_safra > 0
                                    ? (kpi.custo_total / resumo.custo_total_safra) * 100
                                    : 0;
                                return (
                                    <div key={f.key} className="grid grid-cols-[120px_1fr_100px] items-center gap-3">
                                        <span className="text-xs font-medium text-right truncate">{f.label}</span>
                                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-primary rounded-full transition-all"
                                                style={{ width: `${pct}%` }}
                                            />
                                        </div>
                                        <span className="text-xs tabular-nums text-muted-foreground">{moeda(kpi.custo_total)}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Tabs por fase */}
            <Card className="shadow-sm">
                <CardContent className="p-6">
                    <Tabs value={faseSelecionada} onValueChange={setFaseSelecionada}>
                        <TabsList className="flex-wrap h-auto gap-1 mb-4">
                            {FASES.map(f => {
                                const kpi = resumo?.fases.find(r => r.fase === f.key);
                                return (
                                    <TabsTrigger key={f.key} value={f.key} className="gap-1.5">
                                        {f.label}
                                        {kpi && (
                                            <Badge variant="secondary" className="text-xs h-4 px-1">
                                                {kpi.total_operacoes}
                                            </Badge>
                                        )}
                                    </TabsTrigger>
                                );
                            })}
                        </TabsList>

                        {FASES.map(f => (
                            <TabsContent key={f.key} value={f.key}>
                                {/* KPI da fase */}
                                {resumo?.fases.find(r => r.fase === f.key) && (() => {
                                    const kpi = resumo.fases.find(r => r.fase === f.key)!;
                                    return (
                                        <div className="grid grid-cols-3 gap-3 mb-4">
                                            <div className="text-center p-3 bg-muted/30 rounded-lg">
                                                <p className="text-xs text-muted-foreground">Operações</p>
                                                <p className="font-bold text-lg">{kpi.total_operacoes}</p>
                                            </div>
                                            <div className="text-center p-3 bg-muted/30 rounded-lg">
                                                <p className="text-xs text-muted-foreground">Custo Total</p>
                                                <p className="font-bold">{moeda(kpi.custo_total)}</p>
                                            </div>
                                            <div className="text-center p-3 bg-muted/30 rounded-lg">
                                                <p className="text-xs text-muted-foreground">Custo/ha</p>
                                                <p className="font-bold">{moeda(kpi.custo_por_ha)}</p>
                                            </div>
                                        </div>
                                    );
                                })()}

                                {loadingOps ? (
                                    <Skeleton className="h-32 w-full" />
                                ) : (
                                    <DataTable
                                        data={operacoesFase ?? []}
                                        columns={buildColunas((operacao) => {
                                            setEditOperacao(operacao);
                                        }, getTipoLabel)}
                                        searchable
                                        searchPlaceholder="Buscar operação..."
                                        emptyMessage={`Nenhuma operação registrada na fase ${f.label}`}
                                    />
                                )}
                            </TabsContent>
                        ))}
                    </Tabs>
                </CardContent>
            </Card>

            {/* Modal nova operação */}
            <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                <DialogContent className="overflow-hidden p-0 sm:max-w-5xl">
                    <form onSubmit={handleSubmit(d => criarMutation.mutate(d))} className="flex max-h-[88vh] flex-col">
                        <DialogHeader className="border-b px-6 py-5">
                            <DialogTitle className="flex items-center gap-2.5">
                                <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                                    <Activity className="size-4 text-primary" />
                                </div>
                                Nova Operação desta Safra
                            </DialogTitle>
                        </DialogHeader>
                        <DialogBody className="space-y-5 overflow-y-auto px-6 py-5">
                            <div className="rounded-sm border border-primary/10 bg-primary/5 px-3 py-2.5">
                                <p className="text-sm text-muted-foreground">
                                    Registre a operação desta safra vinculando fase, talhão, cultivo e custo realizado.
                                </p>
                            </div>
                            <div className="grid gap-5 lg:grid-cols-12">
                                <div className="space-y-5 lg:col-span-7">
                                    <div className="grid gap-4 md:grid-cols-2">
                                        <div className="space-y-1.5 md:col-span-2">
                                            <Label className="text-xs font-medium">Talhão</Label>
                                            <Controller
                                                control={control}
                                                name="talhao_id"
                                                rules={{ required: true }}
                                                render={({ field }) => {
                                                    const talhaoSelecionado = todasAreas.find((area) => area.id === field.value);
                                                    return (
                                                        <Select value={field.value} onValueChange={field.onChange}>
                                                            <SelectTrigger className="h-9 rounded-sm">
                                                                <SelectValue
                                                                    placeholder={
                                                                        talhaoSelecionado
                                                                            ? getTalhaoAreaLabel(talhaoSelecionado)
                                                                            : "Selecione o talhão"
                                                                    }
                                                                />
                                                            </SelectTrigger>
                                                            <SelectContent className="rounded-sm">
                                                                {todasAreas.map((a) => (
                                                                    <SelectItem key={a.id} value={a.id} className="rounded-sm">
                                                                        {getTalhaoAreaLabel(a)}
                                                                    </SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    );
                                                }}
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium">Data Realizada</Label>
                                            <Input className="rounded-sm" type="date" {...register("data_realizada", { required: true })} />
                                        </div>
                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium">Tipo</Label>
                                            <Controller
                                                name="tipo"
                                                control={control}
                                                rules={{ required: true }}
                                                render={({ field }) => (
                                                    <Select onValueChange={field.onChange} value={field.value}>
                                                        <SelectTrigger className="rounded-sm"><SelectValue placeholder="Selecionar..." /></SelectTrigger>
                                                        <SelectContent className="rounded-sm">
                                                            {tiposOperacao.map(t => <SelectItem key={t.id} value={t.tipo_operacao} className="rounded-sm">{t.descricao || t.tipo_operacao}</SelectItem>)}
                                                        </SelectContent>
                                                    </Select>
                                                )}
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium">Fase <span className="text-[10px] text-muted-foreground">(auto)</span></Label>
                                            <Controller
                                                name="fase_safra"
                                                control={control}
                                                render={({ field }) => (
                                                    <Select onValueChange={field.onChange} value={field.value ?? safra?.status ?? ""}>
                                                        <SelectTrigger className="rounded-sm"><SelectValue placeholder="Fase atual" /></SelectTrigger>
                                                        <SelectContent className="rounded-sm">
                                                            {FASES.map(f => <SelectItem key={f.key} value={f.key} className="rounded-sm">{f.label}</SelectItem>)}
                                                        </SelectContent>
                                                    </Select>
                                                )}
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium">Cultivo <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                            {cultivos.length > 0 ? (
                                                <Controller
                                                    name="cultivo_id"
                                                    control={control}
                                                    render={({ field }) => (
                                                        <div className="flex items-center gap-2">
                                                            <Select onValueChange={field.onChange} value={field.value ?? ""}>
                                                                <SelectTrigger className="rounded-sm">
                                                                    <SelectValue placeholder="Todos os cultivos" />
                                                                </SelectTrigger>
                                                                <SelectContent className="rounded-sm">
                                                                    {cultivos.map(c => (
                                                                        <SelectItem key={c.id} value={c.id} className="rounded-sm">
                                                                            {c.cultura}{c.cultivar_nome ? ` · ${c.cultivar_nome}` : ""}
                                                                        </SelectItem>
                                                                    ))}
                                                                </SelectContent>
                                                            </Select>
                                                            <Button
                                                                type="button"
                                                                variant="outline"
                                                                size="sm"
                                                                className="rounded-sm shrink-0"
                                                                disabled={!field.value}
                                                                onClick={() => field.onChange("")}
                                                            >
                                                                Limpar
                                                            </Button>
                                                        </div>
                                                    )}
                                                />
                                            ) : (
                                                <Input className="rounded-sm" value="Nenhum cultivo disponível" disabled />
                                            )}
                                        </div>
                                        <div className="space-y-1.5 md:col-span-2">
                                            <Label className="text-xs font-medium">Descrição</Label>
                                            <Input className="rounded-sm" placeholder="Ex: Pulverização fungicida Asian Soy..." {...register("descricao", { required: true })} />
                                        </div>
                                        <div className="space-y-1.5 md:col-span-2">
                                            <Label className="text-xs font-medium">Observações <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                            <Textarea className="min-h-28 rounded-sm" placeholder="Condições da operação, restrições, notas de campo..." {...register("observacoes")} />
                                        </div>
                                    </div>
                                </div>
                                <div className="space-y-5 lg:col-span-5">
                                    <div className="rounded-sm border bg-muted/20 p-4">
                                        <div className="grid gap-4 sm:grid-cols-2">
                                            <div className="space-y-1.5">
                                                <Label className="text-xs font-medium">Hora Início <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                                <Input className="rounded-sm" type="time" {...register("hora_inicio")} />
                                            </div>
                                            <div className="space-y-1.5">
                                                <Label className="text-xs font-medium">Hora Fim <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                                <Input className="rounded-sm" type="time" {...register("hora_fim")} />
                                            </div>
                                            <div className="space-y-1.5">
                                                <Label className="text-xs font-medium">Área aplicada (ha)</Label>
                                                <Input
                                                    className="rounded-sm"
                                                    type="number"
                                                    step="0.01"
                                                    max={limiteAreaCreate ?? undefined}
                                                    {...register("area_aplicada_ha", {
                                                        required: "Área aplicada é obrigatória",
                                                        validate: (value) => {
                                                            const numero = Number(value);
                                                            if (!Number.isFinite(numero) || numero <= 0) {
                                                                return "Área aplicada deve ser maior que zero";
                                                            }
                                                            if (limiteAreaCreate != null && numero > limiteAreaCreate) {
                                                                return `Área aplicada não pode ser maior que ${limiteAreaCreate} ha`;
                                                            }
                                                            return true;
                                                        },
                                                    })}
                                                />
                                                {errors.area_aplicada_ha && (
                                                    <p className="text-xs text-destructive">{String(errors.area_aplicada_ha.message)}</p>
                                                )}
                                            </div>
                                            <div className="space-y-1.5">
                                                <Label className="text-xs font-medium">Custo Total (R$)</Label>
                                                <Input className="rounded-sm" type="number" step="0.01" defaultValue="0" {...register("custo_total")} />
                                            </div>
                                            <div className="space-y-1.5 sm:col-span-2">
                                                <Label className="text-xs font-medium">Operador <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                                <Controller
                                                    name="operador_id"
                                                    control={control}
                                                    render={({ field }) => (
                                                        <Select onValueChange={field.onChange} value={field.value ?? ""}>
                                                            <SelectTrigger className="rounded-sm">
                                                                <SelectValue placeholder={talhaoSelecionado ? "Selecionar operador" : "Selecione o talhão antes"} />
                                                            </SelectTrigger>
                                                            <SelectContent className="rounded-sm">
                                                                <SelectItem value="" className="rounded-sm">Sem operador</SelectItem>
                                                                {operadoresDisponiveis.map((pessoa) => (
                                                                    <SelectItem key={pessoa.id} value={pessoa.id} className="rounded-sm">
                                                                        {pessoa.nome_exibicao}
                                                                    </SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    )}
                                                />
                                                {talhaoSelecionado && (
                                                    <p className="text-[11px] text-muted-foreground">
                                                        Só aparecem pessoas físicas com vínculo ativo na mesma unidade produtiva do talhão.
                                                    </p>
                                                )}
                                                {mostrarAvisoOperadores && (
                                                    <Alert className="rounded-sm border-amber-200 bg-amber-50/70 text-amber-950">
                                                        <AlertTitle className="text-xs">Nenhum operador disponível</AlertTitle>
                                                        <AlertDescription className="text-xs space-y-1">
                                                            <p>
                                                                Esse talhão só aceita operadores com vínculo ativo com a unidade produtiva associada.
                                                            </p>
                                                            <p>
                                                                Cadastre ou ajuste isso em{" "}
                                                                <Link href="/cadastros/pessoas" className="font-medium underline underline-offset-2">
                                                                    Cadastros &gt; Pessoas &gt; Vínculos
                                                                </Link>
                                                                .
                                                            </p>
                                                        </AlertDescription>
                                                    </Alert>
                                                )}
                                            </div>
                                            <div className="space-y-1.5 sm:col-span-2">
                                                <Label className="text-xs font-medium">Máquina <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                                <Controller
                                                    name="maquina_id"
                                                    control={control}
                                                    render={({ field }) => (
                                                        <Select onValueChange={field.onChange} value={field.value ?? ""}>
                                                            <SelectTrigger className="rounded-sm"><SelectValue placeholder="Selecionar máquina" /></SelectTrigger>
                                                            <SelectContent className="rounded-sm">
                                                                <SelectItem value="" className="rounded-sm">Sem máquina</SelectItem>
                                                                {equipamentos.map((equipamento) => (
                                                                    <SelectItem key={equipamento.id} value={equipamento.id} className="rounded-sm">
                                                                        {equipamento.nome}{equipamento.marca ? ` · ${equipamento.marca}` : ""}{equipamento.modelo ? ` ${equipamento.modelo}` : ""}
                                                                    </SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    )}
                                                />
                                            </div>
                                            <div className="space-y-1.5 sm:col-span-2">
                                                <Label className="text-xs font-medium">Implemento <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                                <Input className="rounded-sm" placeholder="Ex: barra 24m, grade leve, plantadeira 11 linhas" {...register("implemento")} />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
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
                                    <div key={field.id} className="grid gap-3 rounded-sm border bg-background p-3 md:grid-cols-[minmax(0,1.8fr)_120px_96px_auto] md:items-end">
                                        <div className="space-y-2">
                                            <Label htmlFor={`insumos.${index}.produto_id`}>Produto</Label>
                                            <Controller
                                                name={`insumos.${index}.produto_id`}
                                                control={control}
                                                render={({ field: f }) => {
                                                    const produtoSelecionado = produtos.find((produto) => produto.id === f.value);
                                                    return (
                                                        <Select value={f.value || ""} onValueChange={f.onChange}>
                                                            <SelectTrigger id={`insumos.${index}.produto_id`} className="h-8 text-xs rounded-sm">
                                                                <SelectValue placeholder={produtoSelecionado ? produtoSelecionado.nome : "Selecionar produto"} />
                                                            </SelectTrigger>
                                                            <SelectContent className="rounded-sm">
                                                                {produtos.map((produto) => (
                                                                    <SelectItem key={produto.id} value={produto.id}>
                                                                        {produto.nome}
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
                                        <div className="space-y-2">
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
                                        <div className="space-y-2">
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
                                            className="h-9 w-9 text-muted-foreground hover:text-destructive shrink-0 md:self-end"
                                            onClick={() => removeInsumo(index)}
                                        >
                                            <Trash2 className="size-4" />
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        </DialogBody>
                        <DialogFooter className="gap-2 border-t px-6 py-4 sm:gap-0">
                            <Button variant="outline" size="sm" type="button" onClick={() => setIsAddOpen(false)} className="rounded-sm">
                                <XCircle className="size-3.5 mr-1.5" />
                                Cancelar
                            </Button>
                            <Button size="sm" variant="outline" type="submit" disabled={criarMutation.isPending} className="rounded-sm border-emerald-200 text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800">
                                <CheckCircle2 className="size-3.5 mr-1.5" />
                                Registrar nesta Safra
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            <Dialog open={!!editOperacao} onOpenChange={(open) => { if (!open) setEditOperacao(null); }}>
                <DialogContent className="sm:max-w-[520px]">
                    <form onSubmit={handleSubmitEdit((data) => {
                        if (!editOperacao) return;
                        editarMutation.mutate({ operacaoId: editOperacao.id, data });
                    })}>
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2.5">
                                <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                                    <Pencil className="size-4 text-primary" />
                                </div>
                                Editar Operação da Safra
                            </DialogTitle>
                        </DialogHeader>
                        <DialogBody className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <Label className="text-xs font-medium">Tipo</Label>
                                    <Controller
                                        name="tipo"
                                        control={controlEdit}
                                        render={({ field }) => (
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <SelectTrigger className="rounded-sm">
                                                    <SelectValue placeholder={tipoEditSelecionado?.descricao || tipoEditSelecionado?.tipo_operacao || "Selecionar..."} />
                                                </SelectTrigger>
                                                <SelectContent className="rounded-sm">
                                                    {tiposOperacao.map(t => <SelectItem key={t.id} value={t.tipo_operacao} className="rounded-sm">{t.descricao || t.tipo_operacao}</SelectItem>)}
                                                </SelectContent>
                                            </Select>
                                        )}
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <Label className="text-xs font-medium">Fase</Label>
                                    <Controller
                                        name="fase_safra"
                                        control={controlEdit}
                                        render={({ field }) => (
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <SelectTrigger className="rounded-sm">
                                                    <SelectValue placeholder={faseEditSelecionada?.label || "Fase"} />
                                                </SelectTrigger>
                                                <SelectContent className="rounded-sm">
                                                    {FASES.map(f => <SelectItem key={f.key} value={f.key} className="rounded-sm">{f.label}</SelectItem>)}
                                                </SelectContent>
                                            </Select>
                                        )}
                                    />
                                </div>
                            </div>
                            <div className="space-y-1.5">
                                <Label className="text-xs font-medium">Descrição</Label>
                                <Input className="rounded-sm" {...registerEdit("descricao", { required: true })} />
                            </div>
                            <div className="grid grid-cols-3 gap-4">
                                <div className="space-y-1.5">
                                    <Label className="text-xs font-medium">Data</Label>
                                    <Input className="rounded-sm" type="date" {...registerEdit("data_realizada", { required: true })} />
                                </div>
                                <div className="space-y-1.5">
                                    <Label className="text-xs font-medium">Área (ha)</Label>
                                    <Input
                                        className="rounded-sm"
                                        type="number"
                                        step="0.01"
                                        max={limiteAreaEdit ?? undefined}
                                        {...registerEdit("area_aplicada_ha", {
                                            required: "Área aplicada é obrigatória",
                                            validate: (value) => {
                                                const numero = Number(value);
                                                if (!Number.isFinite(numero) || numero <= 0) {
                                                    return "Área aplicada deve ser maior que zero";
                                                }
                                                if (limiteAreaEdit != null && numero > limiteAreaEdit) {
                                                    return `Área aplicada não pode ser maior que ${limiteAreaEdit} ha`;
                                                }
                                                return true;
                                            },
                                        })}
                                    />
                                    {editErrors.area_aplicada_ha && (
                                        <p className="text-xs text-destructive">{editErrors.area_aplicada_ha.message}</p>
                                    )}
                                </div>
                                <div className="space-y-1.5">
                                    <Label className="text-xs font-medium">Custo Total (R$)</Label>
                                    <Input className="rounded-sm" type="number" step="0.01" {...registerEdit("custo_total")} />
                                </div>
                            </div>
                            <div className="space-y-3 rounded-sm border bg-muted/20 p-4">
                                <div className="flex items-center justify-between">
                                    <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase text-muted-foreground">
                                        <Sprout className="size-3.5" /> Insumos vinculados
                                    </h4>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        className="rounded-sm h-8 text-xs"
                                        onClick={() => appendEditInsumo({ produto_id: "", dose_por_ha: 0, unidade: "L" })}
                                    >
                                        <Plus className="size-3.5 mr-1" />
                                        Adicionar
                                    </Button>
                                </div>
                                {editInsumosFields.length ? (
                                    <div className="space-y-2">
                                        {editInsumosFields.map((field, index) => (
                                            <div key={field.id} className="flex items-end gap-3 rounded-sm border bg-background p-3">
                                                <div className="flex-1 space-y-2">
                                                    <Label htmlFor={`edit.insumos.${index}.produto_id`}>Produto</Label>
                                                    <Controller
                                                        name={`insumos.${index}.produto_id`}
                                                        control={controlEdit}
                                                        render={({ field: f }) => {
                                                            const produtoSelecionado = produtos.find((produto) => produto.id === f.value);
                                                            return (
                                                                <Select value={f.value || ""} onValueChange={f.onChange}>
                                                                    <SelectTrigger id={`edit.insumos.${index}.produto_id`} className="h-8 text-xs rounded-sm">
                                                                        <SelectValue placeholder={produtoSelecionado ? produtoSelecionado.nome : "Selecionar produto"} />
                                                                    </SelectTrigger>
                                                                    <SelectContent className="rounded-sm">
                                                                        {produtos.map((produto) => (
                                                                            <SelectItem key={produto.id} value={produto.id}>
                                                                                {produto.nome}
                                                                            </SelectItem>
                                                                        ))}
                                                                    </SelectContent>
                                                                </Select>
                                                            );
                                                        }}
                                                    />
                                                </div>
                                                <div className="w-24 space-y-2">
                                                    <Label htmlFor={`edit.insumos.${index}.dose_por_ha`} className="text-xs">Dose/ha</Label>
                                                    <Input
                                                        id={`edit.insumos.${index}.dose_por_ha`}
                                                        type="number"
                                                        step="0.01"
                                                        className="h-8 text-xs rounded-sm"
                                                        placeholder="0.00"
                                                        {...registerEdit(`insumos.${index}.dose_por_ha`, { valueAsNumber: true })}
                                                    />
                                                </div>
                                                <div className="w-20 space-y-2">
                                                    <Label htmlFor={`edit.insumos.${index}.unidade`} className="text-xs">Unidade</Label>
                                                    <Input
                                                        id={`edit.insumos.${index}.unidade`}
                                                        className="h-8 text-xs rounded-sm"
                                                        placeholder="L"
                                                        {...registerEdit(`insumos.${index}.unidade`)}
                                                    />
                                                </div>
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-9 w-9 text-muted-foreground hover:text-destructive shrink-0"
                                                    onClick={() => removeEditInsumo(index)}
                                                >
                                                    <Trash2 className="size-4" />
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-muted-foreground">Nenhum insumo vinculado a esta operação.</p>
                                )}
                            </div>
                        </DialogBody>
                        <DialogFooter className="gap-2 sm:gap-0 pt-2">
                            <Button variant="outline" size="sm" type="button" onClick={() => setEditOperacao(null)} className="rounded-sm">
                                <XCircle className="size-3.5 mr-1.5" />
                                Cancelar
                            </Button>
                            <Button size="sm" variant="outline" type="submit" disabled={editarMutation.isPending} className="rounded-sm border-emerald-200 text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800">
                                <CheckCircle2 className="size-3.5 mr-1.5" />
                                Salvar Ajustes
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}
