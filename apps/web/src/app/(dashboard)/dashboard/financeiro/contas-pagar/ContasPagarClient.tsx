"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { useForm } from "react-hook-form";
import { Receipt, Plus, CheckCircle2, AlertTriangle, Loader2, Landmark } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

export interface Despesa {
    id: string;
    descricao: string;
    valor_total: number;
    valor_pago: number | null;
    data_vencimento: string;
    data_pagamento: string | null;
    status: string;
    fornecedor: string | null;
    conta_bancaria_pagamento_id: string | null;
}

interface ContaBancaria {
    id: string;
    nome: string;
    ativa: boolean;
    unidade_produtiva_id: string | null;
}

interface BaixaDespesaPayload {
    data_pagamento: string;
    valor_pago: number;
    forma_pagamento: "PIX" | "BOLETO" | "TRANSFERENCIA" | "DINHEIRO" | "CARTAO" | "CHEQUE" | "DEBITO_AUTOMATICO";
    conta_bancaria_pagamento_id: string;
}

export function ContasPagarClient({ 
    initialDespesas, initialVencendo 
}: { 
    initialDespesas: Despesa[], initialVencendo: Despesa[] 
}) {
    const qc = useQueryClient();
    const [showDialog, setShowDialog] = useState(false);
    const { activeFazendaId, _hasHydrated: hasHydrated } = useAppStore();

    const { data: planos = [], isLoading: planosLoading, isError: planosErro } = useQuery<any[]>({
        queryKey: ["financeiro", "planos-conta", "DESPESA", activeFazendaId],
        queryFn: () => apiFetch("/financeiro/planos-conta/?tipo=DESPESA"),
        enabled: hasHydrated && !!activeFazendaId,
    });

    const { data: despesas = [], isLoading } = useQuery<Despesa[]>({
        queryKey: ["financeiro", "despesas"],
        queryFn: () => apiFetch("/despesas/"),
        initialData: initialDespesas,
    });
    const { data: contasBancarias = [] } = useQuery<ContaBancaria[]>({
        queryKey: ["financeiro", "contas-bancarias"],
        queryFn: () => apiFetch("/financeiro/integracao/contas-bancarias"),
    });
    const { data: vencendo = [] } = useQuery<Despesa[]>({
        queryKey: ["financeiro", "despesas-vencendo"],
        queryFn: () => apiFetch("/despesas/vencendo"),
        initialData: initialVencendo,
    });

    const mut = useMutation({
        mutationFn: (d: any) => apiFetch("/despesas/", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["financeiro", "despesas"] }); setShowDialog(false); toast.success("Despesa lançada."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });
    const [despesaParaBaixa, setDespesaParaBaixa] = useState<Despesa | null>(null);
    const baixarMut = useMutation({
        mutationFn: ({ id, payload }: { id: string; payload: BaixaDespesaPayload }) =>
            apiFetch(`/despesas/${id}/baixar`, { method: "POST", body: JSON.stringify(payload) }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["financeiro", "despesas"] });
            setDespesaParaBaixa(null);
            toast.success("Pagamento registrado.");
        },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });

    const pendentes = despesas.filter(d => d.status === "A_PAGAR" || d.status === "PAGO_PARCIAL");
    const pagas = despesas.filter(d => d.status === "PAGO");
    const vencidas = despesas.filter(d => d.status === "ATRASADO");
    const totalPendente = pendentes.reduce((s, d) => s + d.valor_total, 0);

    const cols: ColumnDef<Despesa>[] = [
        { id: "descricao", header: "Descrição", accessorKey: "descricao" },
        { id: "fornecedor", header: "Fornecedor", accessorKey: "fornecedor", cell: (_v, d) => d.fornecedor || "—" },
        { id: "valor", header: "Valor", accessorKey: "valor_total", cell: (_v, d) => d.valor_total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) },
        { id: "vencimento", header: "Vencimento", accessorKey: "data_vencimento", cell: (_v, d) => new Date(d.data_vencimento).toLocaleDateString("pt-BR") },
        { id: "status", header: "Status", accessorKey: "status", cell: (_v, d) => <WorkflowStatusBadge status={d.status} /> },
        {
            id: "conta_pagamento", header: "Conta de pagamento", accessorKey: "conta_bancaria_pagamento_id",
            cell: (_v, d) => contasBancarias.find(c => c.id === d.conta_bancaria_pagamento_id)?.nome || "—",
        },
        {
            id: "acoes", header: "", exportable: false, sortable: false, filterable: false, cell: (_v, d) =>
                d.status === "A_PAGAR" || d.status === "PAGO_PARCIAL" || d.status === "ATRASADO"
                    ? <div className="flex items-center gap-0 justify-end"><Button size="sm" variant="ghost" onClick={() => setDespesaParaBaixa(d)}><CheckCircle2 className="size-3.5 mr-1 text-green-600" />Pagar</Button></div>
                    : null
        },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Contas a Pagar"
                description="Gestão de despesas, vencimentos e pagamentos"
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Contas a Pagar" },
                ]}
                icon={<Receipt className="h-8 w-8 text-primary" />}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowDialog(true)}
                        className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                    >
                        <Plus size={16} className="mr-2" />
                        Nova Despesa
                    </Button>
                }
            />

            {vencendo.length > 0 && (
                <Alert variant="destructive">
                    <AlertTriangle />
                    <AlertDescription>
                        <strong>{vencendo.length}</strong> despesa(s) vencendo nos próximos 7 dias.
                    </AlertDescription>
                </Alert>
            )}

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: "Total", value: despesas.length },
                    { label: "Pendentes", value: pendentes.length, warn: pendentes.length > 0 },
                    { label: "Vencidas", value: vencidas.length, danger: vencidas.length > 0 },
                    { label: "A pagar (R$)", value: totalPendente.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }), warn: totalPendente > 0 },
                ].map(k => (
                    <Card key={k.label} className={k.danger ? "border-alert-destructive-border" : k.warn ? "border-alert-warning-border" : ""}>
                        <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">{k.label}</CardTitle></CardHeader>
                        <CardContent><div className={`text-2xl font-bold ${k.danger ? "text-alert-destructive-icon" : k.warn ? "text-alert-warning-icon" : ""}`}>{isLoading ? <Skeleton className="h-7 w-8" /> : k.value}</div></CardContent>
                    </Card>
                ))}
            </div>

            <Tabs defaultValue="pendentes">
                <TabsList>
                    <TabsTrigger value="pendentes"><Receipt className="size-3.5 mr-1" />Pendentes {pendentes.length > 0 && <Badge className="ml-1 text-[10px] h-4">{pendentes.length}</Badge>}</TabsTrigger>
                    <TabsTrigger value="pagas"><CheckCircle2 className="size-3.5 mr-1" />Pagas</TabsTrigger>
                </TabsList>

                <TabsContent value="pendentes" className="mt-4">
                    {isLoading ? <Skeleton className="h-40 w-full" /> :
                        [...vencidas, ...pendentes].length === 0
                            ? <div className="text-center py-12 text-sm text-muted-foreground">Nenhuma despesa pendente. <button className="underline" onClick={() => setShowDialog(true)}>Lançar</button></div>
                            : <DataTable columns={cols} data={[...vencidas, ...pendentes]} />
                    }
                </TabsContent>
                <TabsContent value="pagas" className="mt-4">
                    {isLoading ? <Skeleton className="h-40 w-full" /> :
                        pagas.length === 0
                            ? <div className="text-center py-12 text-sm text-muted-foreground">Nenhuma despesa paga.</div>
                            : <DataTable columns={cols} data={pagas} />
                    }
                </TabsContent>
            </Tabs>

            <Dialog open={showDialog} onOpenChange={v => { if (!v) setShowDialog(false); }}>
                <DespesaForm
                    onClose={() => setShowDialog(false)}
                    onSubmit={mut.mutate}
                    loading={mut.isPending}
                    fazendaId={activeFazendaId || ""}
                    planos={planos}
                    planosLoading={planosLoading}
                    planosErro={planosErro}
                />
            </Dialog>
            <Dialog open={!!despesaParaBaixa} onOpenChange={v => { if (!v) setDespesaParaBaixa(null); }}>
                {despesaParaBaixa && (
                    <BaixaDespesaForm
                        despesa={despesaParaBaixa}
                        contas={contasBancarias.filter(conta =>
                            conta.ativa && (!conta.unidade_produtiva_id || conta.unidade_produtiva_id === activeFazendaId)
                        )}
                        loading={baixarMut.isPending}
                        onClose={() => setDespesaParaBaixa(null)}
                        onSubmit={payload => baixarMut.mutate({ id: despesaParaBaixa.id, payload })}
                    />
                )}
            </Dialog>
        </div>
    );
}

function BaixaDespesaForm({
    despesa,
    contas,
    loading,
    onClose,
    onSubmit,
}: {
    despesa: Despesa;
    contas: ContaBancaria[];
    loading: boolean;
    onClose: () => void;
    onSubmit: (payload: BaixaDespesaPayload) => void;
}) {
    const { register, handleSubmit } = useForm<BaixaDespesaPayload>({
        defaultValues: {
            data_pagamento: new Date().toISOString().slice(0, 10),
            valor_pago: despesa.valor_total - (despesa.valor_pago || 0),
            forma_pagamento: "PIX",
            conta_bancaria_pagamento_id: "",
        },
    });
    const [contaId, setContaId] = useState("");
    const [formaPagamento, setFormaPagamento] = useState<BaixaDespesaPayload["forma_pagamento"]>("PIX");

    return (
        <DialogContent className="max-w-md p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
            <DialogHeader className="px-6 pt-6 pb-2">
                <div className="flex items-center gap-2.5">
                    <div className="size-8 rounded-sm bg-emerald-500/10 flex items-center justify-center">
                        <Landmark className="size-4 text-emerald-600" />
                    </div>
                    <DialogTitle>Registrar pagamento</DialogTitle>
                </div>
            </DialogHeader>
            <form onSubmit={handleSubmit(data => onSubmit({ ...data, conta_bancaria_pagamento_id: contaId, forma_pagamento: formaPagamento }))} className="flex flex-col">
                <DialogBody className="px-6 py-6 space-y-4">
                    <p className="text-sm text-muted-foreground">{despesa.descricao}</p>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="data_pagamento">Data do pagamento</Label>
                            <Input id="data_pagamento" className="h-8 rounded-sm" type="date" {...register("data_pagamento", { required: true })} />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="valor_pago">Valor pago</Label>
                            <Input id="valor_pago" className="h-8 rounded-sm" type="number" step="0.01" min="0.01" {...register("valor_pago", { required: true, valueAsNumber: true })} />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label>Forma de pagamento</Label>
                        <Select value={formaPagamento} onValueChange={value => setFormaPagamento(value as BaixaDespesaPayload["forma_pagamento"])}>
                            <SelectTrigger className="h-8 rounded-sm"><SelectValue /></SelectTrigger>
                            <SelectContent className="rounded-sm">
                                <SelectItem value="PIX">PIX</SelectItem><SelectItem value="BOLETO">Boleto</SelectItem>
                                <SelectItem value="TRANSFERENCIA">Transferência</SelectItem><SelectItem value="DINHEIRO">Dinheiro</SelectItem>
                                <SelectItem value="CARTAO">Cartão</SelectItem><SelectItem value="CHEQUE">Cheque</SelectItem>
                                <SelectItem value="DEBITO_AUTOMATICO">Débito automático</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-2">
                        <Label>Conta bancária de origem <span className="text-red-500">*</span></Label>
                        <Select value={contaId} onValueChange={setContaId}>
                            <SelectTrigger className="h-8 rounded-sm"><SelectValue placeholder="Selecione a conta..." /></SelectTrigger>
                            <SelectContent className="rounded-sm">
                                {contas.map(conta => <SelectItem key={conta.id} value={conta.id}>{conta.nome}</SelectItem>)}
                            </SelectContent>
                        </Select>
                        {contas.length === 0 && <p className="text-xs text-destructive">Cadastre uma conta bancária ativa antes de registrar o pagamento.</p>}
                    </div>
                </DialogBody>
                <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                    <Button type="button" variant="outline" size="sm" onClick={onClose}>Cancelar</Button>
                    <Button type="submit" variant="outline" size="sm" disabled={loading || !contaId || contas.length === 0} className="border-primary text-primary hover:bg-primary/5">
                        {loading ? <Loader2 size={14} className="animate-spin mr-2" /> : <CheckCircle2 size={14} className="mr-2" />}Confirmar pagamento
                    </Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}

function DespesaForm({
    onClose,
    onSubmit,
    loading,
    fazendaId,
    planos,
    planosLoading,
    planosErro,
}: {
    onClose: () => void;
    onSubmit: (d: any) => void;
    loading: boolean;
    fazendaId: string;
    planos: any[];
    planosLoading: boolean;
    planosErro: boolean;
}) {
    const { register, handleSubmit, reset } = useForm<any>();
    const [planoContaId, setPlanoContaId] = useState("");

    const hoje = new Date().toISOString().split("T")[0];

    return (
        <DialogContent className="max-w-md p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
            <DialogHeader className="px-6 pt-6 pb-2">
                <div className="flex items-center gap-2.5">
                    <div className="size-8 rounded-sm bg-orange-500/10 flex items-center justify-center">
                        <Receipt className="size-4 text-orange-600" />
                    </div>
                    <DialogTitle>Lançar despesa</DialogTitle>
                </div>
            </DialogHeader>
            <form
                onSubmit={handleSubmit(d => {
                    if (!fazendaId) {
                        toast.error("Selecione uma fazenda.");
                        return;
                    }
                    if (!planoContaId) {
                        toast.error("Selecione a categoria.");
                        return;
                    }
                    onSubmit({
                        unidade_produtiva_id: fazendaId,
                        plano_conta_id: planoContaId,
                        descricao: d.descricao,
                        valor_total: Number(d.valor),
                        data_emissao: hoje,
                        data_vencimento: d.data_vencimento,
                        status: "A_PAGAR",
                        fornecedor: d.fornecedor || undefined,
                        nota_fiscal: d.nota_fiscal || undefined,
                    });
                    reset();
                    setPlanoContaId("");
                })}
                className="flex flex-col"
            >
                <DialogBody className="px-6 py-6 space-y-4">
                    <div className="space-y-2">
                        <Label className="text-sm font-medium">Descrição <span className="text-red-500">*</span></Label>
                        <Input className="h-8 rounded-sm" {...register("descricao", { required: true })} placeholder="Ex: Compra de fertilizante" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Valor (R$) <span className="text-red-500">*</span></Label>
                            <Input className="h-8 rounded-sm" {...register("valor", { required: true })} type="number" step="0.01" min="0" />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Vencimento <span className="text-red-500">*</span></Label>
                            <Input className="h-8 rounded-sm" {...register("data_vencimento", { required: true })} type="date" />
                        </div>
                    </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Categoria <span className="text-red-500">*</span></Label>
                            <Select value={planoContaId} onValueChange={setPlanoContaId}>
                                <SelectTrigger className="h-8 rounded-sm">
                                    <SelectValue placeholder="Selecione..." />
                                </SelectTrigger>
                                <SelectContent className="rounded-sm">
                                    {planosLoading ? (
                                        <SelectItem value="loading" disabled>Carregando...</SelectItem>
                                    ) : planosErro ? (
                                        <SelectItem value="error" disabled>Erro ao carregar categorias</SelectItem>
                                    ) : planos.length === 0 ? (
                                        <SelectItem value="empty" disabled>Nenhuma categoria de despesa encontrada.</SelectItem>
                                    ) : (
                                        planos.map((p) => (
                                            <SelectItem key={p.id} value={String(p.id)}>
                                                {p.codigo} - {p.nome}
                                            </SelectItem>
                                        ))
                                    )}
                                </SelectContent>
                            </Select>
                        </div>
                    </DialogBody>
                <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                    <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => { onClose(); reset(); }}>
                        Cancelar
                    </Button>
                    <Button type="submit" variant="outline" size="sm" disabled={loading} className="rounded-sm border-primary text-primary hover:bg-primary/5 shadow-sm">
                        {loading ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={14} className="mr-2" />}
                        {loading ? "Salvando…" : "Lançar"}
                    </Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}
