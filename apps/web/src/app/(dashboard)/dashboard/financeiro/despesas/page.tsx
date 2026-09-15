"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import {
    Receipt, Plus, X, Loader2,
    DollarSign, FileText, Building2, CheckCircle2, Wallet
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Input } from "@/components/ui/input";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { parseLocaleNumber } from "@/lib/utils";
import { PessoaSelect } from "@/components/cadastros/PessoaSelect";

interface DespesaCreate {
    unidade_produtiva_id: string;
    plano_conta_id: string;
    descricao: string;
    valor_total: number;
    data_emissao: string;
    data_vencimento: string;
    status: string;
    fornecedor?: string;
    pessoa_id?: string;
    nota_fiscal?: string;
}

type Despesa = {
    id: string;
    descricao: string;
    fornecedor: string | null;
    valor_total: number;
    data_vencimento: string;
    status: "A_PAGAR" | "LIBERADO_PAGAMENTO" | "PAGO" | "ATRASADO";
    nota_fiscal: string | null;
};

function NovaDespesaModal({
    fazendaId,
    planos,
    planosLoading,
    planosErro,
    onClose,
}: {
    fazendaId: string;
    planos: any[];
    planosLoading: boolean;
    planosErro: boolean;
    onClose: () => void;
}) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState<Omit<DespesaCreate, "unidade_produtiva_id">>({
        plano_conta_id: "",
        descricao: "",
        valor_total: 0,
        data_emissao: new Date().toISOString().split("T")[0],
        data_vencimento: new Date().toISOString().split("T")[0],
        status: "A_PAGAR",
        pessoa_id: "",
        fornecedor: "",
        nota_fiscal: "",
    });

    const mutation = useMutation({
        mutationFn: (payload: DespesaCreate) =>
            apiFetch("/financeiro/despesas/", { method: "POST", body: JSON.stringify(payload) }),
        onSuccess: () => {
            toast.success("Despesa lançada com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["despesas"] });
            onClose();
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao lançar despesa."),
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!fazendaId) return toast.error("Selecione uma fazenda.");
        if (!form.plano_conta_id) return toast.error("Selecione a categoria.");
        if (!form.pessoa_id) return toast.error("Selecione o fornecedor.");
        
        const payload = { ...form, unidade_produtiva_id: fazendaId };
        if (!payload.pessoa_id) delete payload.pessoa_id;
        
        mutation.mutate(payload);
    };

    return (
        <DialogContent className="max-w-xl p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
            <DialogHeader className="px-6 pt-6 pb-2">
                <div className="flex items-center gap-2.5">
                    <div className="size-8 rounded-sm bg-orange-500/10 flex items-center justify-center">
                        <Wallet className="size-4 text-orange-600" />
                    </div>
                    <DialogTitle>Novo Lançamento de Despesa</DialogTitle>
                </div>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="flex flex-col">
                <DialogBody className="px-6 py-6 space-y-4">
                    <div className="space-y-2">
                        <Label className="text-sm font-medium">
                            Descrição do Gasto <span className="text-red-500">*</span>
                        </Label>
                        <Input
                            required
                            placeholder="Ex: Compra de Fertilizante NPK"
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
                                            <SelectItem key={p.id} value={p.id}>
                                                {p.codigo} - {p.nome}
                                            </SelectItem>
                                        ))
                                    )}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Favorecido <span className="text-red-500">*</span></Label>
                            <PessoaSelect
                                value={form.pessoa_id}
                                onChange={(value) => setForm(f => ({ ...f, pessoa_id: value || "" }))}
                                placeholder="Buscar favorecido..."
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
                            <Label className="text-sm font-medium">Vencimento <span className="text-red-500">*</span></Label>
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
                    <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={onClose}>
                        Cancelar
                    </Button>
                    <Button
                        type="submit"
                        variant="outline"
                        size="sm"
                        disabled={mutation.isPending}
                        className="rounded-sm border-primary text-primary hover:bg-primary/5 shadow-sm"
                    >
                        {mutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={14} className="mr-2" />}
                        {mutation.isPending ? "Salvando..." : "Lançar Despesa"}
                    </Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}



export default function DespesasPage() {
    const { activeFazendaId, isVisaoGrupo, tenant, _hasHydrated: hasHydrated } = useAppStore();
    const queryClient = useQueryClient();
    const [showModal, setShowModal] = useState(false);
    const [selecionadas, setSelecionadas] = useState<Set<string>>(new Set());
    const [confirmarLiberacao, setConfirmarLiberacao] = useState(false);

    const { data: planos = [], isLoading: planosLoading, isError: planosErro } = useQuery({
        queryKey: ["planos-conta", "DESPESA"],
        queryFn: () => apiFetch<any[]>("/financeiro/planos-conta/?tipo=DESPESA"),
        enabled: hasHydrated && !!tenant?.id && !!activeFazendaId,
    });

    const hasCategoriasDespesa = planos.length > 0;

    const { data: despesas = [], isLoading } = useQuery({
        queryKey: ["despesas", activeFazendaId, isVisaoGrupo],
        queryFn: () => apiFetch<Despesa[]>(
            isVisaoGrupo ? "/financeiro/despesas/" : `/financeiro/despesas/?unidade_produtiva_id=${activeFazendaId}`
        ),
        enabled: hasHydrated && !!tenant?.id && (isVisaoGrupo || !!activeFazendaId),
    });

    const despesasSelecionadas = useMemo(
        () => despesas.filter(desp => selecionadas.has(desp.id)),
        [despesas, selecionadas],
    );
    const totalSelecionado = despesasSelecionadas.reduce((total, desp) => total + desp.valor_total, 0);
    const alternarSelecao = (id: string, marcado: boolean) => {
        setSelecionadas(atual => {
            const proxima = new Set(atual);
            if (marcado) proxima.add(id); else proxima.delete(id);
            return proxima;
        });
    };
    const liberarSelecionadas = async () => {
        await Promise.all(despesasSelecionadas.map(desp =>
            apiFetch(`/financeiro/despesas/${desp.id}`, { method: "PATCH", body: JSON.stringify({ status: "LIBERADO_PAGAMENTO" }) })
        ));
        setSelecionadas(new Set());
        setConfirmarLiberacao(false);
        toast.success("Títulos liberados para ordem de pagamento.");
        queryClient.invalidateQueries({ queryKey: ["despesas"] });
    };

    const columns: ColumnDef<Despesa>[] = [
        {
            id: "selecao", header: "", exportable: false, sortable: false, filterable: false,
            cell: (_, row) => {
                const elegivel = row.status === "A_PAGAR" || row.status === "ATRASADO";
                return <Checkbox checked={selecionadas.has(row.id)} disabled={!elegivel} onCheckedChange={checked => alternarSelecao(row.id, checked === true)} aria-label={`Selecionar ${row.descricao}`} />;
            },
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            cell: (value) => (
                <WorkflowStatusBadge status={value} className="shadow-sm" />
            ),
            sortable: true,
            filterable: true,
            exportFormat: (value) => value.replace("_", " "),
        },
        {
            id: "descricao",
            header: "Descrição e Fornecedor",
            accessorKey: "descricao",
            cell: (value, row) => (
                <div>
                    <p className="font-semibold text-foreground">{value}</p>
                    {row.fornecedor && (
                        <p className="text-xs text-foreground/60 font-medium mt-0.5">
                            Fornecedor: {row.fornecedor}
                        </p>
                    )}
                </div>
            ),
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar descrição...",
            exportFormat: (value, row) => row.fornecedor ? `${value} (Fornecedor: ${row.fornecedor})` : value,
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
                <span className="font-bold">
                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)}
                </span>
            ),
            sortable: true,
            exportFormat: (value) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value),
        },
    ];

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Minhas Despesas"
                description="Acompanhe boletos, faturas e controle o Custeio ABC da agricultura."
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Despesas" },
                ]}
                icon={<Wallet className="text-primary" size={22} />}
                actions={
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" disabled={despesasSelecionadas.length === 0} onClick={() => setConfirmarLiberacao(true)} className="rounded-sm">
                            <CheckCircle2 className="mr-1.5 size-3.5" />
                            Liberar selecionadas ({new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(totalSelecionado)})
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                                if (!activeFazendaId) return toast.error("Selecione uma fazenda.");
                                if (!hasCategoriasDespesa) return toast.error("Cadastre categorias de despesa no plano de contas antes de lançar despesas.");
                                setShowModal(true);
                            }}
                            disabled={!activeFazendaId || !hasCategoriasDespesa}
                            className="rounded-sm"
                        >
                            <Plus className="mr-1.5 size-3.5" />
                            Nova Despesa
                        </Button>
                    </div>
                }
            />

            {!planosLoading && !hasCategoriasDespesa ? (
                <Card className="border-amber-500/30 bg-amber-500/10">
                    <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="space-y-1">
                            <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">Sem categorias de despesa</p>
                            <p className="text-sm text-amber-900/80 dark:text-amber-100/80">
                                Cadastre um plano de conta do tipo despesa para liberar o lançamento.
                            </p>
                        </div>
                        <Button asChild variant="outline" className="border-amber-500/30 bg-background/80">
                            <Link href="/dashboard/financeiro/planos-conta">Abrir plano de contas</Link>
                        </Button>
                    </CardContent>
                </Card>
            ) : null}

            <DataTable
                data={despesas}
                columns={columns}
                searchable
                searchPlaceholder="Buscar nota ou fornecedor..."
                exportable
                exportFileName="despesas"
                emptyMessage="Sem despesas encontradas."
            />

            <Dialog open={showModal} onOpenChange={(v) => { if (!v) setShowModal(false); }}>
                {activeFazendaId && (
                    <NovaDespesaModal
                        fazendaId={activeFazendaId}
                        planos={planos}
                        planosLoading={planosLoading}
                        planosErro={planosErro}
                        onClose={() => setShowModal(false)}
                    />
                )}
            </Dialog>

            <Dialog open={confirmarLiberacao} onOpenChange={setConfirmarLiberacao}>
                <DialogContent className="max-w-md">
                    <DialogHeader><DialogTitle>Confirmar liberação para pagamento</DialogTitle></DialogHeader>
                    <DialogBody>Você liberará <strong>{despesasSelecionadas.length}</strong> título(s), no total de <strong>{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(totalSelecionado)}</strong>. Eles não serão marcados como pagos.</DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setConfirmarLiberacao(false)}>Cancelar</Button>
                        <Button variant="default" size="sm" className="rounded-sm" onClick={liberarSelecionadas}>Confirmar liberação</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
