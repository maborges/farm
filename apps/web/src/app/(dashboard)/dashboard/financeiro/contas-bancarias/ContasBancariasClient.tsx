"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useForm } from "react-hook-form";
import { Landmark, Plus, Upload, Loader2, Trash2, FileCheck2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Switch } from "@/components/ui/switch";

export interface ContaBancaria {
    id: string; nome: string; banco: string; agencia: string | null;
    conta: string | null; tipo: string; saldo_atual: number; ativa: boolean;
    convenio_pagamentos: string | null; layout_remessa: string | null;
    homologada_para_remessa: boolean;
}

interface ConfiguracaoRemessa {
    convenio_pagamentos: string;
    layout_remessa: "CNAB240";
    homologada_para_remessa: boolean;
}

const tipoLabel: Record<string, string> = {
    CORRENTE: "Corrente", POUPANCA: "Poupança", INVESTIMENTO: "Investimento", CAIXA: "Caixa"
};

const bancosDomino = [
    { codigo: "001", nome: "Banco do Brasil" },
    { codigo: "104", nome: "Caixa Econômica Federal" },
    { codigo: "237", nome: "Bradesco" },
    { codigo: "748", nome: "Sicredi" },
    { codigo: "756", nome: "Sicoob" },
    { codigo: "341", nome: "Itaú" },
    { codigo: "033", nome: "Santander" },
    { codigo: "745", nome: "Citibank" },
    { codigo: "399", nome: "HSBC" },
    { codigo: "260", nome: "NuPagamentos (Nubank)" },
    { codigo: "182", nome: "Banco Inter" },
] as const;

const bancoNomePorCodigo = Object.fromEntries(bancosDomino.map((b) => [b.codigo, b.nome]));

export function ContasBancariasClient({ initialContas }: { initialContas: ContaBancaria[] }) {
    const qc = useQueryClient();
    const [showDialog, setShowDialog] = useState(false);
    const [contaParaExcluir, setContaParaExcluir] = useState<string | null>(null);
    const [contaParaRemessa, setContaParaRemessa] = useState<ContaBancaria | null>(null);

    const { data: contas = [], isLoading } = useQuery<ContaBancaria[]>({
        queryKey: ["financeiro", "contas-bancarias"],
        queryFn: () => apiFetch("/financeiro/integracao/contas-bancarias"),
        initialData: initialContas,
    });

    const mut = useMutation({
        mutationFn: (d: any) => apiFetch("/financeiro/integracao/contas-bancarias", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["financeiro", "contas-bancarias"] }); setShowDialog(false); toast.success("Conta cadastrada."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });

    const deleteMut = useMutation({
        mutationFn: (id: string) => apiFetch(`/financeiro/integracao/contas-bancarias/${id}`, { method: "DELETE" }),
        onSuccess: () => { 
            qc.invalidateQueries({ queryKey: ["financeiro", "contas-bancarias"] }); 
            toast.success("Conta excluída."); 
            setContaParaExcluir(null);
        },
        onError: (e: any) => {
            toast.error(e.message || "Erro ao excluir conta.");
            setContaParaExcluir(null);
        },
    });
    const remessaMut = useMutation({
        mutationFn: ({ id, dados }: { id: string; dados: ConfiguracaoRemessa }) =>
            apiFetch(`/financeiro/integracao/contas-bancarias/${id}/remessa`, { method: "PATCH", body: JSON.stringify(dados) }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["financeiro", "contas-bancarias"] });
            setContaParaRemessa(null);
            toast.success("Configuração de remessa atualizada.");
        },
        onError: (error: Error) => toast.error(error.message || "Não foi possível atualizar a remessa."),
    });

    const saldoTotal = contas.filter(c => c.ativa).reduce((s, c) => s + (c.saldo_atual || 0), 0);

    const columns: ColumnDef<ContaBancaria>[] = [
        { id: "nome", header: "Nome", accessorKey: "nome" },
        {
            id: "banco",
            header: "Banco",
            accessorKey: "banco",
            cell: (_v, c) => bancoNomePorCodigo[c.banco] ?? c.banco,
        },
        { id: "tipo", header: "Tipo", accessorKey: "tipo", cell: (_v, c) => tipoLabel[c.tipo] || c.tipo },
        { id: "agencia_conta", header: "Ag / Conta", accessorKey: "agencia", cell: (_v, c) => [c.agencia, c.conta].filter(Boolean).join(" / ") || "—" },
        {
            id: "saldo_atual", header: "Saldo", accessorKey: "saldo_atual",
            cell: (_v, c) => <span className={c.saldo_atual < 0 ? "text-red-600" : ""}>{(c.saldo_atual || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</span>
        },
        {
            id: "ativa", header: "Status", accessorKey: "ativa",
            cell: (_v, c) => <Badge variant={c.ativa ? "default" : "secondary"}>{c.ativa ? "Ativa" : "Inativa"}</Badge>
        },
        {
            id: "remessa", header: "Remessa", accessorKey: "homologada_para_remessa",
            cell: (_v, c) => <Badge variant={c.homologada_para_remessa ? "default" : "secondary"}>{c.homologada_para_remessa ? "Homologada" : "Bloqueada"}</Badge>
        },
        {
            id: "acoes", header: "", accessorKey: "id",
            cell: (_v, c) => (
                <div className="flex justify-end gap-1">
                    <Button variant="ghost" size="sm" onClick={() => setContaParaRemessa(c)} className="p-2 h-8" title="Configurar remessa">
                        <FileCheck2 size={16} />
                    </Button>
                    <Button
                        variant="ghost" size="sm" onClick={() => setContaParaExcluir(c.id)}
                        className="text-red-500 hover:text-red-700 hover:bg-red-50 p-2 h-8"
                        title="Excluir conta (apenas se não houver movimentos)"
                    >
                        <Trash2 size={16} />
                    </Button>
                </div>
            )
        },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Contas Bancárias"
                description="Gestão de contas bancárias e saldos"
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Contas Bancárias" },
                ]}
                icon={<Landmark className="text-primary" size={22} />}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowDialog(true)}
                        className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                    >
                        <Plus size={16} className="mr-2" />
                        Nova Conta
                    </Button>
                }
            />

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <Card>
                    <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Contas Ativas</CardTitle></CardHeader>
                    <CardContent><div className="text-2xl font-bold">{isLoading ? <Skeleton className="h-7 w-8" /> : contas.filter(c => c.ativa).length}</div></CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Saldo Total</CardTitle></CardHeader>
                    <CardContent><div className={`text-2xl font-bold ${saldoTotal < 0 ? "text-red-600" : "text-green-600"}`}>{isLoading ? <Skeleton className="h-7 w-24" /> : saldoTotal.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</div></CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Total de Contas</CardTitle></CardHeader>
                    <CardContent><div className="text-2xl font-bold">{isLoading ? <Skeleton className="h-7 w-8" /> : contas.length}</div></CardContent>
                </Card>
            </div>

            {isLoading ? <Skeleton className="h-40 w-full" /> :
                contas.length === 0
                    ? <div className="text-center py-12 text-sm text-muted-foreground"><Landmark className="size-8 mx-auto mb-2 opacity-30" />Nenhuma conta cadastrada. <button className="underline" onClick={() => setShowDialog(true)}>Cadastrar</button></div>
                    : <DataTable columns={columns} data={contas} />
            }

            <Dialog open={showDialog} onOpenChange={v => { if (!v) setShowDialog(false); }}>
                <ContaForm onClose={() => setShowDialog(false)} onSubmit={mut.mutate} loading={mut.isPending} />
            </Dialog>
            <Dialog open={!!contaParaRemessa} onOpenChange={open => { if (!open) setContaParaRemessa(null); }}>
                {contaParaRemessa && <ConfiguracaoRemessaForm
                    conta={contaParaRemessa}
                    loading={remessaMut.isPending}
                    onClose={() => setContaParaRemessa(null)}
                    onSubmit={dados => remessaMut.mutate({ id: contaParaRemessa.id, dados })}
                />}
            </Dialog>

            <ConfirmDialog
                open={!!contaParaExcluir}
                title="Excluir Conta Bancária"
                description="Tem certeza que deseja excluir esta conta? Esta ação não poderá ser desfeita. A conta só será excluída se não houver lançamentos vinculados a ela."
                onConfirm={() => contaParaExcluir && deleteMut.mutate(contaParaExcluir)}
                onCancel={() => setContaParaExcluir(null)}
                confirmText={deleteMut.isPending ? "Excluindo..." : "Excluir Conta"}
                destructive
            />
        </div>
    );
}

function ConfiguracaoRemessaForm({ conta, loading, onClose, onSubmit }: {
    conta: ContaBancaria;
    loading: boolean;
    onClose: () => void;
    onSubmit: (dados: ConfiguracaoRemessa) => void;
}) {
    const { register, handleSubmit, setValue } = useForm<ConfiguracaoRemessa>({
        defaultValues: {
            convenio_pagamentos: conta.convenio_pagamentos || "",
            layout_remessa: "CNAB240",
            homologada_para_remessa: conta.homologada_para_remessa,
        },
    });
    const [homologada, setHomologada] = useState(conta.homologada_para_remessa);
    const bancoSuportado = ["001", "237", "748", "756"].includes(conta.banco);

    return (
        <DialogContent className="max-w-md p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
            <DialogHeader className="px-6 pt-6 pb-2">
                <DialogTitle>Remessa bancária — {conta.nome}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col">
                <DialogBody className="px-6 py-6 space-y-4">
                    {!bancoSuportado && <p className="rounded-sm bg-amber-50 p-3 text-sm text-amber-800">Este banco ainda não possui conector CNAB 240 habilitado.</p>}
                    <div className="space-y-2">
                        <Label htmlFor="convenio_pagamentos">Contrato/convênio de pagamentos</Label>
                        <Input id="convenio_pagamentos" className="h-8 rounded-sm" disabled={!bancoSuportado} {...register("convenio_pagamentos")} />
                    </div>
                    <div className="space-y-2">
                        <Label>Layout contratado</Label>
                        <Input className="h-8 rounded-sm" value="CNAB 240" disabled />
                    </div>
                    <div className="flex items-center justify-between rounded-sm border p-3">
                        <div><Label htmlFor="homologada">Conta homologada para remessa</Label><p className="text-xs text-muted-foreground">Libera a geração de remessas após a homologação bancária.</p></div>
                        <Switch id="homologada" checked={homologada} disabled={!bancoSuportado} onCheckedChange={checked => { setHomologada(checked); setValue("homologada_para_remessa", checked); }} />
                    </div>
                    <input type="hidden" {...register("layout_remessa")} />
                    <input type="hidden" {...register("homologada_para_remessa")} />
                </DialogBody>
                <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                    <Button type="button" variant="outline" size="sm" onClick={onClose}>Cancelar</Button>
                    <Button type="submit" variant="outline" size="sm" disabled={loading || !bancoSuportado} className="border-primary text-primary hover:bg-primary/5">
                        {loading && <Loader2 size={14} className="animate-spin mr-2" />}Salvar configuração
                    </Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}

function ContaForm({ onClose, onSubmit, loading }: { onClose: () => void; onSubmit: (d: any) => void; loading: boolean }) {
    const { register, handleSubmit, reset, setValue } = useForm<any>({ defaultValues: { tipo: "CORRENTE" } });
    const [bancoSelecionado, setBancoSelecionado] = useState("");

    const limparFormulario = () => {
        reset({ tipo: "CORRENTE" });
        setBancoSelecionado("");
    };

    return (
        <DialogContent className="max-w-md p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
            <DialogHeader className="px-6 pt-6 pb-2">
                <div className="flex items-center gap-2.5">
                    <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                        <Landmark className="size-4 text-primary" />
                    </div>
                    <DialogTitle>Nova Conta Bancária</DialogTitle>
                </div>
            </DialogHeader>
            <form onSubmit={handleSubmit(d => { onSubmit(d); limparFormulario(); })} className="flex flex-col">
                <DialogBody className="px-6 py-6 space-y-4">
                    <div className="space-y-2">
                        <Label className="text-sm font-medium">Nome <span className="text-red-500">*</span></Label>
                        <Input className="h-8 rounded-sm" {...register("nome", { required: true })} placeholder="Ex: Banco do Brasil Principal" />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Banco <span className="text-red-500">*</span></Label>
                            <Select
                                value={bancoSelecionado}
                                onValueChange={(v) => {
                                    setBancoSelecionado(v);
                                    setValue("banco", v, { shouldDirty: true, shouldValidate: true });
                                }}
                            >
                                <SelectTrigger className="h-8 rounded-sm">
                                    <SelectValue placeholder="Selecione..." />
                                </SelectTrigger>
                                <SelectContent className="rounded-sm">
                                    {bancosDomino.map((b) => (
                                        <SelectItem key={b.codigo} value={b.codigo}>
                                            {b.codigo} - {b.nome}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <input type="hidden" {...register("banco", { required: true })} />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Tipo <span className="text-red-500">*</span></Label>
                            <Select defaultValue="CORRENTE" onValueChange={(v: string) => setValue("tipo", v)}>
                                <SelectTrigger className="h-8 rounded-sm"><SelectValue /></SelectTrigger>
                                <SelectContent className="rounded-sm">
                                    {Object.entries(tipoLabel).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Agência</Label>
                            <Input className="h-8 rounded-sm" {...register("agencia")} />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Conta</Label>
                            <Input className="h-8 rounded-sm" {...register("conta")} />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label className="text-sm font-medium">Saldo Inicial (R$)</Label>
                        <Input className="h-8 rounded-sm" {...register("saldo_inicial")} type="number" step="0.01" defaultValue="0" />
                    </div>
                </DialogBody>
                <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                    <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => { onClose(); limparFormulario(); }}>
                        Cancelar
                    </Button>
                    <Button type="submit" variant="outline" size="sm" disabled={loading} className="rounded-sm border-primary text-primary hover:bg-primary/5 shadow-sm">
                        {loading ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={14} className="mr-2" />}
                        {loading ? "Salvando…" : "Cadastrar"}
                    </Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}
