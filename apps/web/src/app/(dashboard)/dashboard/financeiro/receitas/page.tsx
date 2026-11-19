"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import {
    Plus, Loader2,
    DollarSign, FileText, CheckCircle2, CreditCard, Landmark
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Input } from "@/components/ui/input";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Dialog,
    DialogBody,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { parseLocaleNumber } from "@/lib/utils";
import { PessoaSelect } from "@/components/cadastros/PessoaSelect";

interface ReceitaCreate {
    unidade_produtiva_id: string;
    plano_conta_id: string;
    descricao: string;
    valor_total: number;
    data_emissao: string;
    data_vencimento: string;
    status: "A_RECEBER" | "RECEBIDO" | "RECEBIDO_PARCIAL" | "CANCELADO";
    cliente?: string;
    pessoa_id?: string;
    nota_fiscal?: string;
}

type Receita = {
    id: string;
    descricao: string;
    cliente: string | null;
    valor_total: number;
    data_vencimento: string;
    status: "A_RECEBER" | "RECEBIDO" | "RECEBIDO_PARCIAL" | "CANCELADO";
    nota_fiscal: string | null;
};

function NovaReceitaDialog({
    open,
    fazendaId,
    planos,
    planosLoading,
    planosErro,
    onOpenChange,
}: {
    open: boolean;
    fazendaId: string;
    planos: any[];
    planosLoading: boolean;
    planosErro: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState<Omit<ReceitaCreate, "unidade_produtiva_id">>({
        plano_conta_id: "",
        descricao: "",
        valor_total: 0,
        data_emissao: new Date().toISOString().split("T")[0],
        data_vencimento: new Date().toISOString().split("T")[0],
        status: "A_RECEBER",
        cliente: "",
        pessoa_id: "",
        nota_fiscal: "",
    });

    const mutation = useMutation({
        mutationFn: (payload: ReceitaCreate) =>
            apiFetch("/financeiro/receitas/", { method: "POST", body: JSON.stringify(payload) }),
        onSuccess: () => {
            toast.success("Receita lançada com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["receitas"] });
            onOpenChange(false);
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao lançar receita."),
    });

    const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        if (!fazendaId) return toast.error("Selecione uma fazenda.");
        if (!form.plano_conta_id) return toast.error("Selecione a categoria de receita.");
        
        const payload = { ...form, unidade_produtiva_id: fazendaId };
        if (!payload.pessoa_id) delete payload.pessoa_id;
        if (!payload.cliente) delete payload.cliente;

        mutation.mutate(payload);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-xl p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
                <DialogHeader className="px-6 pt-6 pb-2">
                    <div className="flex items-center gap-2.5">
                        <div className="size-8 rounded-sm bg-emerald-500/10 flex items-center justify-center">
                            <Landmark className="size-4 text-emerald-600" />
                        </div>
                        <DialogTitle>Novo Lançamento de Receita</DialogTitle>
                    </div>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="flex flex-col">
                    <DialogBody className="px-6 py-6 space-y-4">
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">
                                Descrição <span className="text-red-500">*</span>
                            </Label>
                            <Input
                                required
                                placeholder="Ex: Venda de 500 sacas de Milho"
                                className="h-8 rounded-sm"
                                value={form.descricao}
                                onChange={e => setForm(f => ({ ...f, descricao: e.target.value }))}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">
                                    Categoria <span className="text-red-500">*</span>
                                </Label>
                                <Select
                                    value={form.plano_conta_id}
                                    onValueChange={(value) => setForm(f => ({ ...f, plano_conta_id: value }))}
                                >
                                    <SelectTrigger className="h-8 rounded-sm">
                                        <SelectValue placeholder="Selecione..." />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {planosLoading ? (
                                            <SelectItem value="loading" disabled>Carregando...</SelectItem>
                                        ) : planosErro ? (
                                            <SelectItem value="error" disabled>Erro</SelectItem>
                                        ) : planos.length === 0 ? (
                                            <SelectItem value="empty" disabled>Nenhuma categoria</SelectItem>
                                        ) : (
                                            planos.map((p: any) => (
                                                <SelectItem key={String(p.id)} value={String(p.id)}>
                                                    {p.codigo} - {p.nome}
                                                </SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">
                                    Cliente <span className="text-red-500">*</span>
                                </Label>
                                <PessoaSelect
                                    value={form.pessoa_id}
                                    onChange={(value) => setForm(f => ({ ...f, pessoa_id: value || "" }))}
                                    placeholder="Buscar cliente..."
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Data de emissão</Label>
                                <Input
                                    type="date"
                                    className="h-8 rounded-sm"
                                    value={form.data_emissao}
                                    onChange={e => setForm(f => ({ ...f, data_emissao: e.target.value }))}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">
                                    Vencimento <span className="text-red-500">*</span>
                                </Label>
                                <Input
                                    required
                                    type="date"
                                    className="h-8 rounded-sm"
                                    value={form.data_vencimento}
                                    onChange={e => setForm(f => ({ ...f, data_vencimento: e.target.value }))}
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">
                                    Valor Total (R$) <span className="text-red-500">*</span>
                                </Label>
                                <div className="relative">
                                    <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                    <Input
                                        required
                                        type="number"
                                        step="0.01"
                                        min="0.01"
                                        className="h-8 rounded-sm pl-9"
                                        value={form.valor_total}
                                        onChange={e => setForm(f => ({ ...f, valor_total: parseLocaleNumber(e.target.value) }))}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Nota Fiscal</Label>
                                <div className="relative">
                                    <FileText size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                    <Input
                                        placeholder="Nº da NF-e"
                                        className="h-8 rounded-sm pl-9"
                                        value={form.nota_fiscal}
                                        onChange={e => setForm(f => ({ ...f, nota_fiscal: e.target.value }))}
                                    />
                                </div>
                            </div>
                        </div>
                    </DialogBody>

                    <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                        <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => onOpenChange(false)}>
                            Cancelar
                        </Button>
                        <Button type="submit" variant="default" size="sm" disabled={mutation.isPending} className="rounded-sm">
                            {mutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={14} className="mr-2" />}
                            {mutation.isPending ? "Salvando..." : "Lançar receita"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}



export default function ReceitasPage() {
    const { activeFazendaId, isVisaoGrupo, tenant, _hasHydrated: hasHydrated } = useAppStore();
    const queryClient = useQueryClient();
    const [showModal, setShowModal] = useState(false);

    const { data: planos = [], isLoading: planosLoading, isError: planosErro } = useQuery({
        queryKey: ["planos-conta", "RECEITA"],
        queryFn: () => apiFetch<any[]>("/financeiro/planos-conta/", {
            params: { tipo: "RECEITA" },
        }),
        enabled: hasHydrated && !!tenant?.id && !!activeFazendaId,
    });

    const hasCategoriasReceita = planos.length > 0;

    const marcarRecebido = useMutation({
        mutationFn: (rec: Receita) =>
            apiFetch(`/financeiro/receitas/${rec.id}`, {
                method: "PATCH",
                body: JSON.stringify({ valor_recebido: rec.valor_total, status: "RECEBIDO" }),
            }),
        onSuccess: () => {
            toast.success("Receita marcada como recebida!");
            queryClient.invalidateQueries({ queryKey: ["receitas"] });
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao atualizar."),
    });

    const { data: receitas = [], isLoading } = useQuery({
        queryKey: ["receitas", activeFazendaId, isVisaoGrupo],
        queryFn: () => apiFetch<Receita[]>(
            isVisaoGrupo ? "/financeiro/receitas/" : `/financeiro/receitas/?unidade_produtiva_id=${activeFazendaId}`
        ),
        enabled: hasHydrated && !!tenant?.id && (isVisaoGrupo || !!activeFazendaId),
    });

    const columns: ColumnDef<Receita>[] = [
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            cell: (value) => (
                <WorkflowStatusBadge status={value} className="shadow-sm" />
            ),
            sortable: true,
            filterable: true,
            exportFormat: (value) => value,
        },
        {
            id: "descricao",
            header: "Descrição e Cliente",
            accessorKey: "descricao",
            cell: (value, row) => (
                <div>
                    <p className="font-semibold text-foreground">{value}</p>
                    {row.cliente && (
                        <p className="text-xs text-foreground/60 font-medium mt-0.5">
                            Cliente: {row.cliente}
                        </p>
                    )}
                </div>
            ),
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar descrição...",
            exportFormat: (value, row) => row.cliente ? `${value} (Cliente: ${row.cliente})` : value,
        },
        {
            id: "data_vencimento",
            header: "Vencimento",
            accessorKey: "data_vencimento",
            cell: (value) => (
                <span className="text-foreground/70">
                    {new Date(value).toLocaleDateString('pt-BR')}
                </span>
            ),
            sortable: true,
            exportFormat: (value) => new Date(value).toLocaleDateString('pt-BR'),
        },
        {
            id: "valor_total",
            header: "Valor Total (R$)",
            accessorKey: "valor_total",
            cell: (value) => (
                <span className="font-bold text-blue-600 dark:text-blue-400">
                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)}
                </span>
            ),
            sortable: true,
            exportFormat: (value) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value),
        },
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            cell: (_, row) => (
                row.status === "A_RECEBER" || row.status === "RECEBIDO_PARCIAL" ? (
                    <div className="flex items-center justify-end gap-0">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="size-8 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/50"
                            onClick={(e) => {
                                e.stopPropagation();
                                marcarRecebido.mutate(row);
                            }}
                            disabled={marcarRecebido.isPending}
                            title="Marcar como Recebido"
                        >
                            <CheckCircle2 className="size-4" />
                        </Button>
                    </div>
                ) : null
            ),
        },
    ];

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Minhas Receitas"
                description="Acompanhe vendas de grãos, gado e outros faturamentos da fazenda."
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Minhas Receitas" },
                ]}
                icon={<CreditCard className="text-primary" size={22} />}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                            if (!activeFazendaId) return toast.error("Selecione uma fazenda.");
                            if (!hasCategoriasReceita) return toast.error("Cadastre categorias de receita no plano de contas antes de lançar receitas.");
                            setShowModal(true);
                        }}
                        disabled={!activeFazendaId || !hasCategoriasReceita}
                        className="rounded-sm"
                    >
                        <Plus className="mr-1.5 size-3.5" />
                        Nova Receita
                    </Button>
                }
            />

            {!planosLoading && !hasCategoriasReceita ? (
                <Card variant="warning">
                    <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="space-y-1">
                            <p className="text-sm font-semibold text-card-title">Sem categorias de receita</p>
                            <p className="text-sm text-card-description">
                                Cadastre um plano de conta do tipo receita para liberar o lançamento.
                            </p>
                        </div>
                        <Button asChild variant="outline" size="sm" className="border-alert-warning-border bg-card/80">
                            <Link href="/dashboard/financeiro/planos-conta">Abrir plano de contas</Link>
                        </Button>
                    </CardContent>
                </Card>
            ) : null}

            <DataTable
                data={receitas}
                columns={columns}
                searchable
                searchPlaceholder="Buscar nota ou cliente..."
                exportable
                exportFileName="receitas"
                emptyMessage="Sem receitas encontradas."
                isLoading={isLoading}
            />

            {activeFazendaId && (
                <NovaReceitaDialog
                    open={showModal}
                    fazendaId={activeFazendaId}
                    planos={planos}
                    planosLoading={planosLoading}
                    planosErro={planosErro}
                    onOpenChange={setShowModal}
                />
            )}
        </div>
    );
}
