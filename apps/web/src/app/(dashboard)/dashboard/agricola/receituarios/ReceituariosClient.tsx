"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFieldArray, useForm } from "react-hook-form";
import { toast } from "sonner";
import { FileSignature, Eye, Plus, ShieldCheck, Trash2 } from "lucide-react";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { PageHeader } from "@/components/shared/page-header";
import { PessoaSelect } from "@/components/cadastros/PessoaSelect";
import { ProdutoCombobox } from "@/components/shared/produto-combobox";
import type { ReceituarioAgronomico, ReceituarioAgronomicoCreate, ReceituarioItemCreate } from "@farm/zod-schemas";

interface Safra { id: string; ano_safra?: string; nome?: string }
interface Talhao { id: string; nome: string }

function receituariosUrl() {
    return "/agricola/receituarios";
}

async function fetchReceituarios() {
    return apiFetch<ReceituarioAgronomico[]>(receituariosUrl());
}

function formatDate(value: string | null) {
    if (!value) return "—";
    return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
}

const itemVazio: ReceituarioItemCreate = { produto_id: "", dose: 0, unidade_dose: "L/ha", cultura: null, praga_alvo: null };

interface FormValues {
    agronomo_pessoa_id: string;
    unidade_produtiva_id: string;
    safra_id: string;
    talhao_id: string;
    cultura: string;
    praga_alvo: string;
    data_emissao: string;
    validade_dias: number;
    observacoes: string;
    itens: ReceituarioItemCreate[];
}

export function ReceituariosClient({
    initialReceituarios,
    initialActiveFazendaId,
}: {
    initialReceituarios: ReceituarioAgronomico[];
    initialActiveFazendaId?: string;
}) {
    const qc = useQueryClient();
    const { activeFazendaId } = useAppStore();
    const [showDialog, setShowDialog] = useState(false);

    const { data: receituarios = [], isLoading } = useQuery<ReceituarioAgronomico[]>({
        queryKey: ["agricola", "receituarios"],
        queryFn: fetchReceituarios,
        initialData: activeFazendaId === initialActiveFazendaId ? initialReceituarios : undefined,
    });

    const { data: safras = [] } = useQuery<Safra[]>({
        queryKey: ["safras", activeFazendaId],
        queryFn: () => apiFetch<Safra[]>(`/safras/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId && showDialog,
    });

    const { data: talhoes = [] } = useQuery<Talhao[]>({
        queryKey: ["talhoes", activeFazendaId],
        queryFn: () => apiFetch<Talhao[]>(`/cadastros/areas-rurais/?tipo=TALHAO&unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId && showDialog,
    });

    const { register, control, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<FormValues>({
        defaultValues: {
            agronomo_pessoa_id: "",
            unidade_produtiva_id: activeFazendaId ?? "",
            safra_id: "",
            talhao_id: "",
            cultura: "",
            praga_alvo: "",
            data_emissao: new Date().toISOString().slice(0, 10),
            validade_dias: 90,
            observacoes: "",
            itens: [itemVazio],
        },
    });
    const { fields, append, remove } = useFieldArray({ control, name: "itens" });

    const criarMut = useMutation({
        mutationFn: (payload: ReceituarioAgronomicoCreate) =>
            apiFetch<ReceituarioAgronomico>("/agricola/receituarios", { method: "POST", body: payload }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["agricola", "receituarios"] });
            setShowDialog(false);
            reset();
            toast.success("Receituário criado como rascunho.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao criar receituário."),
    });

    const onSubmit = (values: FormValues) => {
        const payload: ReceituarioAgronomicoCreate = {
            agronomo_pessoa_id: values.agronomo_pessoa_id,
            unidade_produtiva_id: values.unidade_produtiva_id || activeFazendaId || "",
            safra_id: values.safra_id || null,
            talhao_id: values.talhao_id || null,
            operacao_agricola_id: null,
            cultura: values.cultura || null,
            praga_alvo: values.praga_alvo || null,
            data_emissao: values.data_emissao,
            validade_dias: Number(values.validade_dias) || 90,
            observacoes: values.observacoes || null,
            itens: values.itens.map((item) => ({
                ...item,
                dose: Number(item.dose),
            })),
        };
        criarMut.mutate(payload);
    };

    const columns: ColumnDef<ReceituarioAgronomico>[] = useMemo(() => [
        {
            id: "numero",
            header: "Receituário",
            accessorKey: "numero",
            cell: (_value, row) => (
                <div className="min-w-[140px]">
                    <div className="font-medium leading-tight">{row.numero ?? row.id.slice(0, 8)}</div>
                    <div className="text-[11px] text-muted-foreground">CREA {row.crea_numero}/{row.crea_uf}</div>
                </div>
            ),
        },
        {
            id: "cultura",
            header: "Cultura / Praga-alvo",
            accessorKey: "cultura",
            cell: (_value, row) => (
                <div className="text-sm">
                    <div>{row.cultura ?? "—"}</div>
                    <div className="text-[11px] text-muted-foreground">{row.praga_alvo ?? "—"}</div>
                </div>
            ),
        },
        {
            id: "data_validade",
            header: "Validade",
            accessorKey: "data_validade",
            cell: (_value, row) => formatDate(row.data_validade),
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            filterOptions: [
                { value: "RASCUNHO", label: "Rascunho" },
                { value: "EMITIDO", label: "Emitido" },
                { value: "VENCIDO", label: "Vencido" },
                { value: "CANCELADO", label: "Cancelado" },
            ],
            cell: (_value, row) => <WorkflowStatusBadge status={row.status} />,
        },
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            isActionColumn: true,
            cell: (_value, row) => (
                <div className="flex items-center justify-end gap-1">
                    <Button size="icon-sm" variant="ghost" title="Ver detalhes" asChild>
                        <Link href={`/dashboard/agricola/receituarios/${row.id}`}>
                            <Eye className="size-3.5" />
                        </Link>
                    </Button>
                </div>
            ),
        },
    ], []);

    return (
        <div className="flex flex-col gap-5 p-4 sm:p-6">
            <PageHeader
                title="Receituário Agronômico"
                description="Documentos legais de receituário (Lei 7.802/1989) para venda e aplicação de defensivos, com agrônomo e CREA responsáveis."
                icon={<FileSignature className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Agricultura", href: "/dashboard/agricola" },
                    { label: "Receituário Agronômico" },
                ]}
                actions={
                    <Button
                        size="sm"
                        onClick={() => setShowDialog(true)}
                        className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                        variant="outline"
                    >
                        <Plus className="size-4 mr-1.5" /> Novo Receituário
                    </Button>
                }
            />

            <Card className="rounded-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <ShieldCheck className="size-4 text-primary" /> Receituários emitidos
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <DataTable
                        data={receituarios}
                        columns={columns}
                        isLoading={isLoading}
                        searchPlaceholder="Buscar por número, cultura..."
                        exportFileName="receituarios-agronomicos"
                        emptyMessage="Nenhum receituário cadastrado ainda."
                    />
                </CardContent>
            </Card>

            <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) reset(); }}>
                <DialogContent className="max-w-xl">
                    <DialogHeader className="border-b">
                        <DialogTitle>Novo Receituário Agronômico</DialogTitle>
                        <DialogDescription>
                            Cria o receituário como rascunho. Anexe o PDF assinado na tela de detalhes para emiti-lo.
                        </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleSubmit(onSubmit)} className="flex min-h-0 flex-col">
                        <div className="grid max-h-[65vh] gap-4 overflow-y-auto px-6 pb-2 md:grid-cols-2">
                            <div className="space-y-2 md:col-span-2">
                                <Label>Agrônomo responsável (CREA) <span className="text-destructive">*</span></Label>
                                <PessoaSelect
                                    value={watch("agronomo_pessoa_id")}
                                    onChange={(value) => setValue("agronomo_pessoa_id", value ?? "", { shouldValidate: true })}
                                    tiposRelacionamento={["AGRONOMO"]}
                                    placeholder="Selecione o agrônomo..."
                                />
                                <input type="hidden" {...register("agronomo_pessoa_id", { required: true })} />
                                {errors.agronomo_pessoa_id && <span className="text-xs text-destructive">Selecione o agrônomo.</span>}
                            </div>

                            <div className="space-y-2">
                                <Label>Safra</Label>
                                <Select value={watch("safra_id")} onValueChange={(v) => setValue("safra_id", v)}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Opcional" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {safras.map((s) => (
                                            <SelectItem key={s.id} value={s.id}>{s.ano_safra ?? s.nome ?? s.id}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label>Talhão</Label>
                                <Select value={watch("talhao_id")} onValueChange={(v) => setValue("talhao_id", v)}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Opcional" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {talhoes.map((t) => (
                                            <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label>Cultura</Label>
                                <Input {...register("cultura")} placeholder="Ex: Café" />
                            </div>

                            <div className="space-y-2">
                                <Label>Praga-alvo</Label>
                                <Input {...register("praga_alvo")} placeholder="Ex: Broca-do-café" />
                            </div>

                            <div className="space-y-2">
                                <Label>Data de emissão <span className="text-destructive">*</span></Label>
                                <Input type="date" {...register("data_emissao", { required: true })} />
                            </div>

                            <div className="space-y-2">
                                <Label>Validade (dias) <span className="text-destructive">*</span></Label>
                                <Input type="number" {...register("validade_dias", { required: true, valueAsNumber: true })} />
                            </div>

                            <div className="space-y-2 md:col-span-2">
                                <div className="flex items-center justify-between">
                                    <Label>Produtos receitados</Label>
                                    <Button type="button" size="sm" variant="outline" onClick={() => append(itemVazio)}>
                                        <Plus className="size-3.5 mr-1" /> Item
                                    </Button>
                                </div>
                                {fields.map((field, index) => (
                                    <div key={field.id} className="flex items-end gap-2 rounded-sm border p-2">
                                        <div className="flex-1 space-y-1">
                                            <Label className="text-xs">Produto</Label>
                                            <ProdutoCombobox
                                                value={watch(`itens.${index}.produto_id` as const)}
                                                onChange={(produtoId) => setValue(`itens.${index}.produto_id` as const, produtoId, { shouldValidate: true })}
                                            />
                                        </div>
                                        <div className="w-24 space-y-1">
                                            <Label className="text-xs">Dose</Label>
                                            <Input type="number" step="0.01" {...register(`itens.${index}.dose` as const, { valueAsNumber: true })} />
                                        </div>
                                        <div className="w-24 space-y-1">
                                            <Label className="text-xs">Unidade</Label>
                                            <Input {...register(`itens.${index}.unidade_dose` as const)} placeholder="L/ha" />
                                        </div>
                                        <Button type="button" size="icon-sm" variant="ghost" onClick={() => remove(index)} disabled={fields.length === 1}>
                                            <Trash2 className="size-3.5 text-destructive" />
                                        </Button>
                                    </div>
                                ))}
                            </div>

                            <div className="space-y-2 md:col-span-2">
                                <Label>Observações</Label>
                                <Textarea {...register("observacoes")} rows={2} />
                            </div>
                        </div>

                        <DialogFooter className="border-t px-6 pb-6 pt-4">
                            <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>Cancelar</Button>
                            <Button type="submit" disabled={criarMut.isPending}>
                                {criarMut.isPending ? "Salvando..." : "Criar rascunho"}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}
