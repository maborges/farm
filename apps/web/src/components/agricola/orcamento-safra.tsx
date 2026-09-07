"use client";

import { useLayoutEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody, DialogDescription } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Plus, Pencil, Trash2, TrendingUp, TrendingDown, AlertTriangle, DollarSign, XCircle, Save } from "lucide-react";
import { toast } from "sonner";
import { useForm, Controller, useWatch, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ItemOrcamentoCreateSchema, type ItemOrcamentoCreate } from "@farm/zod-schemas";
import { ProdutoCombobox } from "@/components/shared/produto-combobox";
import { EquipamentoCombobox } from "@/components/shared/equipamento-combobox";
import { ColaboradorCombobox } from "@/components/shared/colaborador-combobox";
import { TipoServicoCombobox } from "@/components/shared/tiposervico-combobox";
import { UnidadeMedidaCombobox } from "@/components/shared/unidade-medida-combobox";

// ── Types ─────────────────────────────────────────────────────────────────────

type Categoria =
    | "SEMENTE" | "FERTILIZANTE" | "DEFENSIVO" | "MATERIAL" | "MAQUINARIO" | "COMBUSTIVEL"
    | "MAO_DE_OBRA" | "SERVICO" | "SEGURO" | "OUTROS";

interface Cultivo {
    id: string;
    cultura: string;
    cultivar_nome: string | null;
}

type OrigemItem = "PRODUTO" | "MAQUINA" | "PESSOA" | "SERVICO" | "MANUAL";

interface ItemOrcamento {
    id: string;
    categoria: Categoria;
    descricao: string;
    quantidade: number;
    unidade: string;
    unidade_medida_id: string | null;
    origem_tipo: OrigemItem;
    origem_id: string | null;
    custo_unitario: number;
    custo_unitario_snapshot: number | null;
    custo_unitario_ajustado: number | null;
    custo_unitario_efetivo: number;
    custo_total: number;
    ordem: number;
    observacoes: string | null;
    cultivo_id: string | null;
}

const ORIGENS: { value: OrigemItem; label: string }[] = [
    { value: "MANUAL", label: "Manual (digitar valor)" },
    { value: "PRODUTO", label: "Produto do cadastro" },
    { value: "MAQUINA", label: "Máquina/equipamento" },
    { value: "PESSOA", label: "Pessoa/colaborador" },
    { value: "SERVICO", label: "Serviço" },
];

interface CustoCategoria {
    categoria: string;
    custo_total: number;
    custo_por_ha: number;
    percentual: number;
}

interface OrcamentoPrevisto {
    custo_total: number;
    custo_por_ha: number;
    receita_esperada: number;
    receita_por_ha: number;
    margem_bruta: number;
    ponto_equilibrio_sc_ha: number | null;
    por_categoria: CustoCategoria[];
}

interface OrcamentoRealizado {
    custo_operacoes: number;
    custo_rateios: number;
    custo_total: number;
    custo_por_ha: number;
    por_categoria: CustoCategoria[];
}

interface DesvioOrcamento {
    custo_desvio_valor: number;
    custo_desvio_pct: number;
    status: string;
}

interface OrcamentoData {
    safra_id: string;
    cultura: string;
    ano_safra: string;
    area_ha: number;
    status_safra: string;
    previsto: OrcamentoPrevisto | null;
    realizado: OrcamentoRealizado;
    desvio: DesvioOrcamento | null;
    itens: ItemOrcamento[];
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORIAS: { value: Categoria; label: string; variant: "default" | "secondary" | "destructive" | "outline" | "ghost" | "warning" }[] = [
    { value: "SEMENTE",      label: "Semente",       variant: "secondary" },
    { value: "FERTILIZANTE", label: "Fertilizante",  variant: "outline" },
    { value: "DEFENSIVO",    label: "Defensivo",     variant: "destructive" },
    { value: "MATERIAL",     label: "Material",      variant: "secondary" },
    { value: "MAQUINARIO",   label: "Maquinário",    variant: "outline" },
    { value: "COMBUSTIVEL",  label: "Combustível",   variant: "warning" },
    { value: "MAO_DE_OBRA",  label: "Mão de Obra",   variant: "default" },
    { value: "SERVICO",      label: "Serviço",       variant: "ghost" },
    { value: "SEGURO",       label: "Seguro",        variant: "warning" },
    { value: "OUTROS",       label: "Outros",        variant: "outline" },
];

function categoriaLabel(cat: string) {
    return CATEGORIAS.find((c) => c.value === cat)?.label ?? cat;
}

function categoriaVariant(cat: string) {
    return CATEGORIAS.find((c) => c.value === cat)?.variant ?? "outline";
}

function brl(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function labelCase(value: string) {
    return value
        .toLowerCase()
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function ItemModal({
    open,
    onClose,
    safraId,
    item,
}: {
    open: boolean;
    onClose: () => void;
    safraId: string;
    item?: ItemOrcamento;
}) {
    const qc = useQueryClient();

    const { data: cultivos = [] } = useQuery<Cultivo[]>({
        queryKey: ["cultivos", safraId],
        queryFn: () => apiFetch(`/safras/${safraId}/cultivos`),
        enabled: open,
    });

    const { register, handleSubmit, control, reset, setValue, formState: { errors } } = useForm<ItemOrcamentoCreate>({
        resolver: zodResolver(ItemOrcamentoCreateSchema) as unknown as Resolver<ItemOrcamentoCreate>,
        defaultValues: {
            cultivo_id: null,
            categoria: "OUTROS",
            descricao: "",
            quantidade: 1,
            unidade: "un",
            unidade_medida_id: null,
            origem_tipo: "MANUAL",
            origem_id: null,
            custo_unitario: null,
            custo_unitario_ajustado: null,
            ordem: 0,
            observacoes: "",
        },
    });

    const [origemTipo, setOrigemTipo] = useState<ItemOrcamentoCreate["origem_tipo"]>("MANUAL");

    useLayoutEffect(() => {
        if (!open) return;

        if (item) {
            reset({
                cultivo_id: item.cultivo_id ?? null,
                categoria: item.categoria,
                descricao: item.descricao,
                quantidade: item.quantidade,
                unidade: item.unidade,
                unidade_medida_id: item.unidade_medida_id ?? null,
                origem_tipo: item.origem_tipo,
                origem_id: item.origem_id,
                custo_unitario: item.custo_unitario,
                custo_unitario_ajustado: item.custo_unitario_ajustado,
                ordem: item.ordem,
                observacoes: item.observacoes ?? "",
            });
            setOrigemTipo(item.origem_tipo);
            return;
        }

        reset({
            cultivo_id: cultivos.length === 1 ? cultivos[0].id : null,
            categoria: "OUTROS",
            descricao: "",
            quantidade: 1,
            unidade: "un",
            unidade_medida_id: null,
            origem_tipo: "MANUAL",
            origem_id: null,
            custo_unitario: null,
            custo_unitario_ajustado: null,
            ordem: 0,
            observacoes: "",
        });
        setOrigemTipo("MANUAL");
    }, [cultivos, item, open, reset]);

    const isManual = origemTipo === "MANUAL";

    const qtt = useWatch({ control, name: "quantidade" }) || 0;
    const custoManual = useWatch({ control, name: "custo_unitario" }) || 0;
    const unit = isManual ? custoManual : item?.custo_unitario_efetivo ?? 0;
    const total = qtt * unit;

    const save = useMutation({
        mutationFn: (data: ItemOrcamentoCreate) => {
            const payload: ItemOrcamentoCreate = {
                ...data,
                cultivo_id: data.cultivo_id ?? (cultivos.length === 1 ? cultivos[0].id : null),
            };
            return item
                ? apiFetch(`/agricola/planejamento/safras/${safraId}/itens/${item.id}`, {
                      method: "PATCH",
                      body: JSON.stringify(payload),
                  })
                : apiFetch(`/agricola/planejamento/safras/${safraId}/itens`, {
                      method: "POST",
                      body: JSON.stringify(payload),
                  });
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["orcamento", safraId] });
            toast.success("Item salvo com sucesso.");
            onClose();
        },
        onError: (err: any) => {
            toast.error(err.message || "Erro ao salvar item");
        }
    });

    const onSubmit = handleSubmit(
        (data) => save.mutate(data),
        (errors) => {
            console.error("Erros de validação:", JSON.stringify(errors, null, 2));
            toast.error("Preencha todos os campos obrigatórios corretamente.");
        }
    );

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg p-0 gap-0">
                <form onSubmit={onSubmit} className="flex flex-col min-h-0">
                    <DialogHeader className="px-6 py-6 border-b">
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                <DollarSign className="size-4 text-primary" />
                            </div>
                            <div className="space-y-0.5 text-left">
                                <DialogTitle>{item ? "Editar item" : "Novo item"}</DialogTitle>
                                <DialogDescription>
                                    Informe os dados do insumo ou serviço para compor o orçamento da safra.
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <ScrollArea className="flex-1 max-h-[65vh]">
                        <DialogBody className="flex flex-col gap-4 py-6">
                            <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Categoria</Label>
                            <Controller
                                name="categoria"
                                control={control}
                                render={({ field }) => (
                                    <Select value={field.value} onValueChange={field.onChange}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Selecione a categoria" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {CATEGORIAS.map((c) => (
                                                <SelectItem key={c.value} value={c.value}>
                                                    {c.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                )}
                            />
                            {errors.categoria && <p className="text-destructive text-[10px]">{errors.categoria.message as string}</p>}
                        </div>
                        {cultivos.length > 1 && (
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Cultivo <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                <Controller
                                    name="cultivo_id"
                                    control={control}
                                    render={({ field }) => (
                                        <Select
                                            value={field.value ?? "__ALL__"}
                                            onValueChange={(value) => field.onChange(value === "__ALL__" ? null : value)}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="Todos os cultivos" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="__ALL__">
                                                    Geral da safra
                                                </SelectItem>
                                                {cultivos.map((c) => (
                                                    <SelectItem key={c.id} value={c.id}>
                                                        {c.cultura}{c.cultivar_nome ? ` · ${c.cultivar_nome}` : ""}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    )}
                                />
                            </div>
                        )}
                        {cultivos.length === 1 && (
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Cultivo</Label>
                                <div className="h-9 rounded-sm border bg-muted/40 px-3 text-xs flex items-center text-muted-foreground">
                                    {cultivos[0].cultura}{cultivos[0].cultivar_nome ? ` · ${cultivos[0].cultivar_nome}` : ""}
                                </div>
                                <input type="hidden" {...register("cultivo_id")} />
                            </div>
                        )}
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Descrição</Label>
                            <Input {...register("descricao")} placeholder="Ex: Ureia 45% N" />
                            {errors.descricao && <p className="text-destructive text-[10px]">{errors.descricao.message as string}</p>}
                        </div>
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Origem do custo</Label>
                            <Controller
                                name="origem_tipo"
                                control={control}
                                render={({ field }) => (
                                    <Select
                                        value={field.value}
                                        onValueChange={(value) => {
                                            field.onChange(value);
                                            setOrigemTipo(value as ItemOrcamentoCreate["origem_tipo"]);
                                            // Limpa campos da origem anterior — só em troca real do
                                            // usuário (Select fica disabled em modo de edição).
                                            if (value === "MANUAL") {
                                                setValue("origem_id", null);
                                            } else {
                                                setValue("custo_unitario", null);
                                            }
                                        }}
                                        disabled={!!item}
                                    >
                                        <SelectTrigger>
                                            <SelectValue placeholder="Selecione a origem" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {ORIGENS.map((o) => (
                                                <SelectItem key={o.value} value={o.value}>
                                                    {o.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                )}
                            />
                            {item && (
                                <p className="text-[11px] text-muted-foreground">
                                    A origem não pode ser alterada após criado o item.
                                </p>
                            )}
                            {(errors as any).origem_tipo && <p className="text-destructive text-[10px]">{(errors as any).origem_tipo.message as string}</p>}
                        </div>
                        {!isManual && !item && (
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">
                                    {origemTipo === "PRODUTO" && "Produto"}
                                    {origemTipo === "MAQUINA" && "Máquina"}
                                    {origemTipo === "PESSOA" && "Pessoa"}
                                    {origemTipo === "SERVICO" && "Tipo de serviço"}
                                </Label>
                                <Controller
                                    name="origem_id"
                                    control={control}
                                    render={({ field }) => {
                                        if (origemTipo === "PRODUTO") {
                                            return (
                                                <ProdutoCombobox
                                                    value={field.value ?? ""}
                                                    onChange={(val) => field.onChange(val || null)}
                                                />
                                            );
                                        }
                                        if (origemTipo === "MAQUINA") {
                                            return (
                                                <EquipamentoCombobox
                                                    value={field.value ?? ""}
                                                    onChange={(val) => field.onChange(val || null)}
                                                />
                                            );
                                        }
                                        if (origemTipo === "PESSOA") {
                                            return (
                                                <ColaboradorCombobox
                                                    value={field.value ?? ""}
                                                    onChange={(val) => field.onChange(val || null)}
                                                />
                                            );
                                        }
                                        if (origemTipo === "SERVICO") {
                                            return (
                                                <TipoServicoCombobox
                                                    value={field.value ?? ""}
                                                    onChange={(val) => field.onChange(val || null)}
                                                />
                                            );
                                        }
                                        return (
                                            <Input
                                                value={field.value ?? ""}
                                                onChange={(e) => field.onChange(e.target.value || null)}
                                                placeholder="Cole o ID do registro de origem"
                                            />
                                        );
                                    }}
                                />
                                {(errors as any).origem_id && <p className="text-destructive text-[10px]">{(errors as any).origem_id.message as string}</p>}
                            </div>
                        )}
                        <div className="grid grid-cols-3 gap-3">
                            <div className="grid gap-1.5 col-span-1">
                                <Label className="text-xs font-medium">Qtd.</Label>
                                <Input type="number" step="0.01" {...register("quantidade", { setValueAs: (v) => v === "" || isNaN(Number(v)) ? null : Number(v) })} placeholder="0" />
                                {errors.quantidade && <p className="text-destructive text-[10px]">{errors.quantidade.message as string}</p>}
                            </div>
                            <div className="grid gap-1.5 col-span-1">
                                <Label className="text-xs font-medium">Unidade</Label>
                                <Controller
                                    name="unidade_medida_id"
                                    control={control}
                                    render={({ field }) => (
                                        <UnidadeMedidaCombobox
                                            value={field.value}
                                            onChange={(id, unidade) => {
                                                field.onChange(id);
                                                if (unidade) setValue("unidade", unidade.codigo);
                                            }}
                                        />
                                    )}
                                />
                                <Input {...register("unidade")} placeholder="kg, sc, L..." className="h-7 text-[11px]" />
                                {errors.unidade && <p className="text-destructive text-[10px]">{errors.unidade.message as string}</p>}
                            </div>
                            <div className="grid gap-1.5 col-span-1">
                                {isManual ? (
                                    <>
                                        <Label className="text-xs font-medium">Custo Unit. (R$)</Label>
                                        <Input type="number" step="0.01" {...register("custo_unitario", { setValueAs: (v) => v === "" || isNaN(Number(v)) ? null : Number(v) })} placeholder="0,00" />
                                        {errors.custo_unitario && <p className="text-destructive text-[10px]">{errors.custo_unitario.message as string}</p>}
                                    </>
                                ) : (
                                    <>
                                        <Label className="text-xs font-medium">Custo capturado (R$)</Label>
                                        <div className="h-9 rounded-sm border bg-muted/40 px-3 text-xs flex items-center text-muted-foreground">
                                            {item ? brl(item.custo_unitario_snapshot ?? 0) : "capturado ao salvar"}
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                        {item && !isManual && (
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Ajuste manual (R$) <span className="text-[10px] text-muted-foreground">(opcional, não altera o cadastro mestre)</span></Label>
                                <Input
                                    type="number"
                                    step="0.01"
                                    {...register("custo_unitario_ajustado", { setValueAs: (v) => v === "" || isNaN(Number(v)) ? null : Number(v) })}
                                    placeholder={`Padrão: ${brl(item.custo_unitario_snapshot ?? 0)}`}
                                />
                                {(errors as any).custo_unitario_ajustado && <p className="text-destructive text-[10px]">{(errors as any).custo_unitario_ajustado.message as string}</p>}
                            </div>
                        )}
                        {total > 0 && (
                            <p className="text-sm text-muted-foreground text-right">
                                Total: <strong>{brl(total)}</strong>
                            </p>
                        )}
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Observações (opcional)</Label>
                            <Textarea {...register("observacoes")} rows={2} />
                        </div>
                    </DialogBody>
                    </ScrollArea>
                    <DialogFooter className="px-6 py-4 border-t bg-muted/50">
                        <Button variant="outline" size="sm" onClick={onClose} type="button">
                            <XCircle className="size-3.5 mr-1.5" />
                            Cancelar
                        </Button>
                        <Button size="sm" type="submit" disabled={save.isPending}>
                            <Save className="size-3.5 mr-1.5" />
                            {save.isPending ? "Salvando…" : "Salvar"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function OrcamentoSafra({ safraId }: { safraId: string }) {
    const qc = useQueryClient();
    const [showModal, setShowModal] = useState(false);
    const [editItem, setEditItem] = useState<ItemOrcamento | undefined>();
    const [deleteId, setDeleteId] = useState<string | null>(null);

    const { data: cultivos = [] } = useQuery<Cultivo[]>({
        queryKey: ["cultivos", safraId],
        queryFn: () => apiFetch(`/safras/${safraId}/cultivos`),
    });

    const { data, isLoading, isError, error } = useQuery<OrcamentoData>({
        queryKey: ["orcamento", safraId],
        queryFn: () => apiFetch(`/agricola/planejamento/safras/${safraId}/orcamento`),
    });

    const delMutation = useMutation({
        mutationFn: (itemId: string) =>
            apiFetch(`/agricola/planejamento/safras/${safraId}/itens/${itemId}`, {
                method: "DELETE",
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["orcamento", safraId] });
            setDeleteId(null);
        },
    });

    const getCultivoLabel = (cultivoId?: string | null) => {
        if (!cultivoId) return "Geral da safra";
        const cultivo = cultivos.find((item) => item.id === cultivoId);
        if (!cultivo) return "Cultivo não identificado";
        return `${cultivo.cultura}${cultivo.cultivar_nome ? ` · ${cultivo.cultivar_nome}` : ""}`;
    };

    if (isLoading) {
        return <p className="text-sm text-muted-foreground py-6 text-center">Carregando orçamento…</p>;
    }

    if (isError) {
        return (
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-6 text-center">
                <p className="text-sm font-medium text-destructive">Não foi possível carregar o orçamento desta safra.</p>
                <p className="mt-1 text-sm text-muted-foreground">{error instanceof Error ? error.message : "Erro desconhecido ao consultar dados."}</p>
            </div>
        );
    }

    if (!data) return null;

    const { previsto, realizado, desvio, itens, area_ha } = data;

    // Group itens by categoria
    const grouped = CATEGORIAS.map((cat) => ({
        ...cat,
        itens: itens.filter((i) => i.categoria === cat.value),
    })).filter((g) => g.itens.length > 0);

    const desvioColor =
        !desvio || desvio.status === "SEM_ORCAMENTO"
            ? "text-muted-foreground"
            : desvio.status === "DENTRO"
            ? "text-green-600"
            : "text-red-600";

    return (
        <div className="flex flex-col gap-6">
            <Card>
                <CardHeader className="pb-3">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div className="space-y-1">
                            <Badge variant="secondary" className="w-fit">Resumo</Badge>
                            <CardTitle>Orçamento de custeio</CardTitle>
                            <CardDescription>
                                {data.cultura} · Safra {data.ano_safra} · {area_ha} ha
                            </CardDescription>
                        </div>
                        <div className="flex flex-wrap gap-2 md:justify-end">
                            <Badge variant="outline">{labelCase(data.status_safra)}</Badge>
                            <Badge variant="outline">{previsto ? "Planejado" : "Sem orçamento previsto"}</Badge>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-sm border bg-muted/30 p-4">
                        <p className="text-xs text-muted-foreground">Custo previsto</p>
                        <p className="mt-1 text-lg font-semibold">{previsto ? brl(previsto.custo_total) : "—"}</p>
                        <p className="text-xs text-muted-foreground">{previsto ? `${brl(previsto.custo_por_ha)}/ha` : "Aguardando lançamento"}</p>
                    </div>
                    <div className="rounded-sm border bg-muted/30 p-4">
                        <p className="text-xs text-muted-foreground">Custo realizado</p>
                        <p className="mt-1 text-lg font-semibold">{brl(realizado.custo_total)}</p>
                        <p className="text-xs text-muted-foreground">{brl(realizado.custo_por_ha)}/ha</p>
                    </div>
                    <div className="rounded-sm border bg-muted/30 p-4">
                        <p className="text-xs text-muted-foreground">Desvio</p>
                        {desvio && desvio.status !== "SEM_ORCAMENTO" ? (
                            <div className={cn("mt-1 flex items-center gap-2", desvioColor)}>
                                {desvio.status === "DENTRO" ? <TrendingDown className="size-4" /> : <TrendingUp className="size-4" />}
                                <span className="text-lg font-semibold">
                                    {desvio.custo_desvio_pct > 0 ? "+" : ""}
                                    {desvio.custo_desvio_pct.toFixed(1)}%
                                </span>
                            </div>
                        ) : (
                            <p className="mt-1 text-lg font-semibold text-muted-foreground">Sem orçamento</p>
                        )}
                        {desvio && desvio.status !== "SEM_ORCAMENTO" && (
                            <p className="text-xs text-muted-foreground">{brl(desvio.custo_desvio_valor)}</p>
                        )}
                    </div>
                    <div className="rounded-sm border bg-muted/30 p-4">
                        <p className="text-xs text-muted-foreground">Receita esperada</p>
                        <p className="mt-1 text-lg font-semibold">{previsto ? brl(previsto.receita_esperada) : "—"}</p>
                        <p className="text-xs text-muted-foreground">
                            {previsto?.ponto_equilibrio_sc_ha ? `P.E.: ${previsto.ponto_equilibrio_sc_ha.toFixed(1)} sc/ha` : "Sem ponto de equilíbrio"}
                        </p>
                    </div>
                </CardContent>
            </Card>

            {previsto?.por_categoria?.length ? (
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle>Previsto por categoria</CardTitle>
                        <CardDescription>Distribuição do orçamento previsto por grupo de custo.</CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Categoria</TableHead>
                                    <TableHead className="text-right">Previsto</TableHead>
                                    <TableHead className="text-right">Previsto/ha</TableHead>
                                    <TableHead className="text-right">Participação</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {previsto.por_categoria.map((c) => (
                                    <TableRow key={c.categoria}>
                                        <TableCell>
                                            <Badge variant={categoriaVariant(c.categoria)}>{categoriaLabel(c.categoria)}</Badge>
                                        </TableCell>
                                        <TableCell className="text-right font-medium">{brl(c.custo_total)}</TableCell>
                                        <TableCell className="text-right text-muted-foreground">{brl(c.custo_por_ha)}</TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                                                    <div
                                                        className="h-full rounded-full bg-primary"
                                                        style={{ width: `${Math.min(c.percentual, 100)}%` }}
                                                    />
                                                </div>
                                                <span className="w-12 text-right text-xs text-muted-foreground">
                                                    {c.percentual.toFixed(1)}%
                                                </span>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                                <TableRow className="bg-muted/40 font-medium">
                                    <TableCell>Total</TableCell>
                                    <TableCell className="text-right">{brl(previsto.custo_total)}</TableCell>
                                    <TableCell className="text-right text-muted-foreground">{brl(previsto.custo_por_ha)}</TableCell>
                                    <TableCell className="text-right text-muted-foreground">{area_ha} ha</TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            ) : null}

            <Card>
                <CardHeader className="pb-3">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div className="space-y-1">
                            <CardTitle>Itens do orçamento previsto</CardTitle>
                            <CardDescription>
                                Cadastre insumos, serviços e demais custos previstos para esta safra.
                            </CardDescription>
                        </div>
                        <Button size="sm" onClick={() => { setEditItem(undefined); setShowModal(true); }}>
                            <Plus className="size-4 mr-1.5" /> Adicionar item
                        </Button>
                    </div>
                </CardHeader>
                <CardContent className="flex flex-col gap-4">
                    {itens.length === 0 ? (
                        <div className="flex flex-col items-center gap-3 rounded-sm border border-dashed px-6 py-10 text-center">
                            <AlertTriangle className="size-8 text-muted-foreground/50" />
                            <div className="space-y-1">
                                <p className="text-sm font-medium">Nenhum item cadastrado</p>
                                <p className="text-sm text-muted-foreground">
                                    Adicione itens para começar a comparar o planejado com o realizado.
                                </p>
                            </div>
                            <Button variant="outline" size="sm" onClick={() => { setEditItem(undefined); setShowModal(true); }}>
                                <Plus className="size-4 mr-1.5" /> Adicionar primeiro item
                            </Button>
                        </div>
                    ) : (
                        grouped.map((group) => (
                            <div key={group.value} className="overflow-hidden rounded-sm border">
                                <div className="flex items-center justify-between gap-3 border-b bg-muted/40 px-4 py-3">
                                    <div className="flex items-center gap-2">
                                        <Badge variant={categoriaVariant(group.value)}>{group.label}</Badge>
                                        <span className="text-xs text-muted-foreground">{group.itens.length} item(ns)</span>
                                    </div>
                                    <span className="text-sm font-medium">
                                        {brl(group.itens.reduce((s, i) => s + i.custo_total, 0))}
                                    </span>
                                </div>
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Cultivo</TableHead>
                                            <TableHead>Descrição</TableHead>
                                            <TableHead className="text-center w-20">Qtd.</TableHead>
                                            <TableHead className="text-center w-16">Und.</TableHead>
                                            <TableHead className="text-right w-32">Custo unit.</TableHead>
                                            <TableHead className="text-right w-32">Total</TableHead>
                                            <TableHead className="text-right w-20">Ações</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {group.itens.map((item) => (
                                            <TableRow key={item.id}>
                                                <TableCell className={cn(item.cultivo_id ? "text-foreground" : "text-muted-foreground")}>
                                                    {getCultivoLabel(item.cultivo_id)}
                                                </TableCell>
                                                <TableCell>{item.descricao}</TableCell>
                                                <TableCell className="text-center">{item.quantidade}</TableCell>
                                                <TableCell className="text-center text-muted-foreground">{item.unidade}</TableCell>
                                                <TableCell className="text-right">{brl(item.custo_unitario)}</TableCell>
                                                <TableCell className="text-right font-medium">{brl(item.custo_total)}</TableCell>
                                                <TableCell className="text-right">
                                                    <div className="flex items-center justify-end gap-0.5">
                                                        <Button
                                                            size="icon"
                                                            variant="ghost"
                                                            className="size-7"
                                                            onClick={() => { setEditItem(item); setShowModal(true); }}
                                                        >
                                                            <Pencil className="size-3.5" />
                                                        </Button>
                                                        <Button
                                                            size="icon"
                                                            variant="ghost"
                                                            className="size-7 text-destructive hover:text-destructive"
                                                            onClick={() => setDeleteId(item.id)}
                                                        >
                                                            <Trash2 className="size-3.5" />
                                                        </Button>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        ))
                    )}
                </CardContent>
                {(realizado.custo_operacoes > 0 || realizado.custo_rateios > 0) && (
                    <CardFooter className="flex flex-col items-start gap-3 border-t bg-muted/30 md:flex-row md:items-center md:justify-between">
                        <div>
                            <p className="text-xs uppercase tracking-wide text-muted-foreground">Operações agrícolas</p>
                            <p className="mt-1 font-medium">{brl(realizado.custo_operacoes)}</p>
                        </div>
                        <div>
                            <p className="text-xs uppercase tracking-wide text-muted-foreground">Rateios financeiros</p>
                            <p className="mt-1 font-medium">{brl(realizado.custo_rateios)}</p>
                        </div>
                    </CardFooter>
                )}
            </Card>

            {showModal && (
                <ItemModal
                    open={showModal}
                    onClose={() => { setShowModal(false); setEditItem(undefined); }}
                    safraId={safraId}
                    item={editItem}
                />
            )}

            <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Remover item?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Esta ação não pode ser desfeita e removerá o item permanentemente do orçamento.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setDeleteId(null)}>
                            Cancelar
                        </AlertDialogCancel>
                        <AlertDialogAction
                            variant="destructive"
                            onClick={() => deleteId && delMutation.mutate(deleteId)}
                            disabled={delMutation.isPending}
                        >
                            <Trash2 className="size-3.5 mr-1.5" />
                            {delMutation.isPending ? "Removendo…" : "Remover"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
