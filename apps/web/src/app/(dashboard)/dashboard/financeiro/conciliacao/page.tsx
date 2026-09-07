"use client";

import Link from "next/link";
import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import {
    GitMerge, Plus, Upload, X, Loader2, CheckCircle2,
    EyeOff, Lightbulb, Building2, ChevronRight, ArrowUpCircle, ArrowDownCircle, Landmark, CircleAlert
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// ── Tipos ──────────────────────────────────────────────────────────────────

interface ContaBancaria {
    id: string;
    nome: string;
    banco: string | null;
    agencia: string | null;
    conta: string | null;
    tipo: string;
    ativa: boolean;
}

interface Lancamento {
    id: string;
    data: string;
    valor: number;
    descricao: string | null;
    tipo: string;
    status_conciliacao: string;
    id_ofx: string | null;
    despesa_id: string | null;
    receita_id: string | null;
}

interface Sugestao {
    lancamento_id: string;
    tipo: string;
    sugestao_id: string;
    descricao_lanc: string;
    descricao_fin: string;
    valor: number;
    data_lanc: string;
    confianca: string;
}

interface OrdemPagamento {
    id: string;
    status: string;
    ambiente: string;
    banco_codigo: string;
    conta_nome: string;
    data_pagamento: string;
    total_valor: number;
}

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const dataFormatada = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });

// ── Nova Conta Modal ──────────────────────────────────────────────────────

function NovaContaForm({ onClose }: { onClose: () => void }) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState({ nome: "", banco: "", agencia: "", conta: "", tipo: "CORRENTE", saldo_inicial: 0 });

    const mutation = useMutation({
        mutationFn: (payload: any) =>
            apiFetch("/financeiro/integracao/contas-bancarias", {
                method: "POST",
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            toast.success("Conta bancária criada!");
            queryClient.invalidateQueries({ queryKey: ["contas-bancarias"] });
            onClose();
        },
        onError: (err: Error) => toast.error(err.message || "Erro."),
    });

    return (
        <DialogContent className="max-w-md p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
            <DialogHeader className="px-6 pt-6 pb-2">
                <div className="flex items-center gap-2.5">
                    <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                        <Building2 className="size-4 text-primary" />
                    </div>
                    <DialogTitle>Nova Conta Bancária</DialogTitle>
                </div>
            </DialogHeader>
            <form onSubmit={e => { e.preventDefault(); mutation.mutate(form); }} className="flex flex-col">
                <DialogBody className="px-6 py-6 space-y-4">
                    <div className="space-y-2">
                        <Label className="text-sm font-medium">Nome da Conta <span className="text-red-500">*</span></Label>
                        <Input required className="h-8 rounded-sm" placeholder="Ex: Bradesco Conta Corrente"
                            value={form.nome} onChange={e => setForm(f => ({ ...f, nome: e.target.value }))} />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Banco</Label>
                            <Input className="h-8 rounded-sm" placeholder="Ex: 237" value={form.banco}
                                onChange={e => setForm(f => ({ ...f, banco: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Tipo <span className="text-red-500">*</span></Label>
                            <Select value={form.tipo} onValueChange={v => setForm(f => ({ ...f, tipo: v }))}>
                                <SelectTrigger className="h-8 rounded-sm"><SelectValue /></SelectTrigger>
                                <SelectContent className="rounded-sm">
                                    <SelectItem value="CORRENTE">Conta Corrente</SelectItem>
                                    <SelectItem value="POUPANCA">Poupança</SelectItem>
                                    <SelectItem value="INVESTIMENTO">Investimento</SelectItem>
                                    <SelectItem value="CAIXA">Caixa</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Agência</Label>
                            <Input className="h-8 rounded-sm" placeholder="Ex: 1234-5" value={form.agencia}
                                onChange={e => setForm(f => ({ ...f, agencia: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium">Conta</Label>
                            <Input className="h-8 rounded-sm" placeholder="Ex: 12345-6" value={form.conta}
                                onChange={e => setForm(f => ({ ...f, conta: e.target.value }))} />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label className="text-sm font-medium">Saldo Inicial (R$)</Label>
                        <Input className="h-8 rounded-sm" type="number" step="0.01" value={form.saldo_inicial}
                                onChange={e => setForm(f => ({ ...f, saldo_inicial: parseFloat(e.target.value) || 0 }))} />
                    </div>
                </DialogBody>
                <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                    <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={onClose}>
                        Cancelar
                    </Button>
                    <Button type="submit" variant="default" size="sm" disabled={mutation.isPending} className="rounded-sm">
                        {mutation.isPending ? <Loader2 size={14} className="animate-spin mr-1.5" /> : <Plus size={14} className="mr-1.5" />}
                        {mutation.isPending ? "Criando..." : "Criar Conta"}
                    </Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}

// ── Status badge ──────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
    if (status === "CONCILIADO") return <Badge variant="default" className="bg-green-600 hover:bg-green-700">Conciliado</Badge>;
    if (status === "IGNORADO") return <Badge variant="secondary">Ignorado</Badge>;
    return <Badge variant="outline" className="border-amber-500 text-amber-600">Pendente</Badge>;
}

// ── Página principal ──────────────────────────────────────────────────────

export default function ConciliacaoPage() {
    const queryClient = useQueryClient();
    const [showNovaConta, setShowNovaConta] = useState(false);
    const [selectedConta, setSelectedConta] = useState<string | null>(null);
    const [tab, setTab] = useState<"lancamentos" | "sugestoes">("lancamentos");
    const [statusFiltro, setStatusFiltro] = useState<string>("todos_fake");
    const fileRef = useRef<HTMLInputElement>(null);

    // Contas
    const { data: contas = [], isLoading: loadingContas } = useQuery({
        queryKey: ["contas-bancarias"],
        queryFn: () => apiFetch<ContaBancaria[]>("/financeiro/integracao/contas-bancarias"),
    });

    // Lançamentos
    const { data: lancamentos = [], isLoading: loadingLanc } = useQuery({
        queryKey: ["lancamentos", selectedConta, statusFiltro],
        queryFn: () => {
            const params = new URLSearchParams();
            if (statusFiltro && statusFiltro !== "todos_fake") params.set("status", statusFiltro);
            return apiFetch<Lancamento[]>(
                `/financeiro/integracao/contas-bancarias/${selectedConta}/lancamentos?${params}`
            );
        },
        enabled: !!selectedConta,
    });

    // Sugestões
    const { data: sugestoes = [], isLoading: loadingSug } = useQuery({
        queryKey: ["sugestoes-conciliacao", selectedConta],
        queryFn: () =>
            apiFetch<Sugestao[]>(`/financeiro/integracao/contas-bancarias/${selectedConta}/sugestoes`),
        enabled: !!selectedConta && tab === "sugestoes",
    });

    const { data: ordens = [], isLoading: loadingOrdens } = useQuery({
        queryKey: ["financeiro", "ordens-pagamento"],
        queryFn: () => apiFetch<OrdemPagamento[]>("/financeiro/integracao/ordens-pagamento"),
    });

    // Upload OFX
    const uploadMutation = useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append("arquivo", file);
            return apiFetch<{ importados: number; duplicados: number; total_ofx: number }>(
                `/financeiro/integracao/contas-bancarias/${selectedConta}/importar-ofx`,
                { method: "POST", body: formData }
            );
        },
        onSuccess: (data) => {
            toast.success(`Importado: ${data.importados} novo(s), ${data.duplicados} duplicado(s).`);
            queryClient.invalidateQueries({ queryKey: ["lancamentos", selectedConta] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    // Conciliar (aceitar sugestão)
    const conciliarMutation = useMutation({
        mutationFn: ({ lancId, tipo, sugestaoId }: { lancId: string; tipo: string; sugestaoId: string }) =>
            apiFetch(`/financeiro/integracao/lancamentos/${lancId}/conciliar`, {
                method: "PATCH",
                body: JSON.stringify(
                    tipo === "DESPESA" ? { despesa_id: sugestaoId } : { receita_id: sugestaoId }
                ),
            }),
        onSuccess: () => {
            toast.success("Lançamento conciliado!");
            queryClient.invalidateQueries({ queryKey: ["lancamentos", selectedConta] });
            queryClient.invalidateQueries({ queryKey: ["sugestoes-conciliacao", selectedConta] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    // Ignorar
    const ignorarMutation = useMutation({
        mutationFn: (lancId: string) =>
            apiFetch(`/financeiro/integracao/lancamentos/${lancId}/ignorar`, { method: "PATCH" }),
        onSuccess: () => {
            toast.success("Lançamento ignorado.");
            queryClient.invalidateQueries({ queryKey: ["lancamentos", selectedConta] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const retornoMutation = useMutation({
        mutationFn: ({ ordemId, aprovado }: { ordemId: string; aprovado: boolean }) =>
            apiFetch<{ id: string; status: string }>(`/financeiro/integracao/ordens-pagamento/${ordemId}/simular-retorno`, {
                method: "POST",
                body: { aprovado },
            }),
        onSuccess: (resultado) => {
            queryClient.invalidateQueries({ queryKey: ["financeiro", "ordens-pagamento"] });
            queryClient.invalidateQueries({ queryKey: ["financeiro", "despesas"] });
            queryClient.invalidateQueries({ queryKey: ["lancamentos"] });
            toast.success(
                resultado.status === "LIQUIDADA_SIMULADA"
                    ? "Retorno aprovado e pagamentos liquidados no ambiente de teste."
                    : "Retorno rejeitado: os títulos voltaram para a fila de pagamento.",
            );
        },
        onError: (err: Error) => toast.error(err.message || "Não foi possível processar o retorno."),
    });

    const pendentes = lancamentos.filter(l => l.status_conciliacao === "NAO_CONCILIADO").length;

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Conciliação Bancária"
                description="Importe extratos OFX e vincule lançamentos bancários às suas despesas e receitas."
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Conciliação Bancária" },
                ]}
                icon={<CheckCircle2 className="text-primary" size={22} />}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowNovaConta(true)}
                        className="rounded-sm"
                    >
                        <Plus className="mr-1.5 size-3.5" />
                        Nova Conta
                    </Button>
                }
            />

            <Card>
                <CardHeader>
                    <CardTitle>Retornos de pagamento</CardTitle>
                    <CardDescription>Confirme o resultado do banco para efetivar ou devolver os títulos de uma ordem de homologação.</CardDescription>
                </CardHeader>
                <CardContent>
                    {loadingOrdens ? (
                        <p className="text-sm text-muted-foreground">Carregando ordens de pagamento…</p>
                    ) : ordens.length === 0 ? (
                        <p className="text-sm text-muted-foreground">Nenhuma ordem criada. <Link href="/dashboard/financeiro/ordens-pagamento" className="text-primary underline-offset-4 hover:underline">Criar ordem de pagamento</Link>.</p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Conta</TableHead>
                                    <TableHead>Data</TableHead>
                                    <TableHead>Valor</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead className="text-right">Retorno de teste</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {ordens.map((ordem) => {
                                    const pendente = ordem.status === "PRONTA_PARA_REMESSA";
                                    const processando = retornoMutation.isPending && retornoMutation.variables?.ordemId === ordem.id;
                                    const status = ordem.status === "LIQUIDADA_SIMULADA"
                                        ? <Badge variant="success">Liquidada (simulada)</Badge>
                                        : ordem.status === "REJEITADA_SIMULADA"
                                            ? <Badge variant="danger">Rejeitada (simulada)</Badge>
                                            : <Badge variant="warning">Aguardando retorno</Badge>;
                                    return (
                                        <TableRow key={ordem.id}>
                                            <TableCell><p className="font-medium">{ordem.conta_nome}</p><p className="text-xs text-muted-foreground">Banco {ordem.banco_codigo}</p></TableCell>
                                            <TableCell>{dataFormatada.format(new Date(`${ordem.data_pagamento}T00:00:00Z`))}</TableCell>
                                            <TableCell className="font-medium">{moeda.format(ordem.total_valor)}</TableCell>
                                            <TableCell>{status}</TableCell>
                                            <TableCell>
                                                <div className="flex justify-end gap-2">
                                                    <Button variant="outline" size="sm" disabled={!pendente || processando} onClick={() => retornoMutation.mutate({ ordemId: ordem.id, aprovado: false })}>
                                                        <CircleAlert data-icon="inline-start" />
                                                        Rejeitar teste
                                                    </Button>
                                                    <Button size="sm" disabled={!pendente || processando} onClick={() => retornoMutation.mutate({ ordemId: ordem.id, aprovado: true })}>
                                                        <CheckCircle2 data-icon="inline-start" />
                                                        Aprovar teste
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {/* Sidebar contas */}
                <div className="lg:col-span-1">
                    <Card className="rounded-sm h-full flex flex-col min-h-[400px]">
                        <CardHeader className="py-3 px-4 border-b border-border-subtle bg-muted/30">
                            <CardTitle className="text-xs text-muted-foreground uppercase">Contas Bancárias</CardTitle>
                        </CardHeader>
                        <CardContent className="p-0 flex-1 overflow-y-auto">
                            {loadingContas ? (
                                <div className="p-4 space-y-2">
                                    {[1, 2].map(i => <div key={i} className="h-12 bg-muted rounded animate-pulse" />)}
                                </div>
                            ) : contas.length === 0 ? (
                                <div className="p-6 text-center text-sm text-muted-foreground">
                                    Nenhuma conta. <button onClick={() => setShowNovaConta(true)} className="text-primary hover:underline">Criar</button>
                                </div>
                            ) : (
                                <div className="flex flex-col">
                                    {contas.map(c => (
                                        <button
                                            key={c.id}
                                            onClick={() => setSelectedConta(c.id)}
                                            className={`w-full text-left px-4 py-3 flex items-center justify-between border-b border-border-subtle hover:bg-muted/50 transition-colors ${selectedConta === c.id ? "bg-primary/5 border-l-2 border-l-primary" : ""}`}
                                        >
                                            <div>
                                                <p className="text-sm font-semibold">{c.nome}</p>
                                                <p className="text-xs text-muted-foreground">{c.tipo}{c.banco ? ` · Banco ${c.banco}` : ""}</p>
                                            </div>
                                            <ChevronRight size={14} className="text-muted-foreground/40" />
                                        </button>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Main area */}
                <div className="lg:col-span-3">
                    {!selectedConta ? (
                        <Card className="rounded-sm h-full flex items-center justify-center min-h-[400px]">
                            <CardContent className="text-center text-muted-foreground p-16">
                                <GitMerge className="mx-auto mb-3 h-10 w-10 opacity-30" />
                                <p className="font-medium">Selecione uma conta bancária para ver os lançamentos.</p>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between gap-3 flex-wrap">
                                <Tabs value={tab} onValueChange={(v) => setTab(v as any)} className="w-auto">
                                    <TabsList className="h-9 rounded-sm">
                                        <TabsTrigger value="lancamentos" className="rounded-sm text-sm">
                                            Extrato {pendentes > 0 && <span className="ml-1.5 bg-amber-500 text-white text-[10px] px-1.5 py-0.5 rounded-full leading-none flex items-center">{pendentes}</span>}
                                        </TabsTrigger>
                                        <TabsTrigger value="sugestoes" className="rounded-sm text-sm">
                                            <Lightbulb size={14} className="mr-1.5" />
                                            Sugestões Automáticas
                                        </TabsTrigger>
                                    </TabsList>
                                </Tabs>

                                <div className="flex items-center gap-2">
                                    {tab === "lancamentos" && (
                                        <Select value={statusFiltro} onValueChange={setStatusFiltro}>
                                            <SelectTrigger className="h-9 w-[150px] rounded-sm">
                                                <SelectValue placeholder="Todos" />
                                            </SelectTrigger>
                                            <SelectContent className="rounded-sm">
                                                <SelectItem value="todos_fake">Todos</SelectItem>
                                                <SelectItem value="NAO_CONCILIADO">Pendentes</SelectItem>
                                                <SelectItem value="CONCILIADO">Conciliados</SelectItem>
                                                <SelectItem value="IGNORADO">Ignorados</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    )}

                                    <input
                                        ref={fileRef}
                                        type="file"
                                        accept=".ofx,.qfx"
                                        className="hidden"
                                        onChange={e => {
                                            const file = e.target.files?.[0];
                                            if (file) uploadMutation.mutate(file);
                                            e.target.value = "";
                                        }}
                                    />
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => fileRef.current?.click()}
                                        disabled={uploadMutation.isPending}
                                        className="h-9 rounded-sm font-semibold border-primary text-primary hover:bg-primary/5"
                                    >
                                        {uploadMutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <Upload size={14} className="mr-2" />}
                                        Importar OFX
                                    </Button>
                                </div>
                            </div>

                            <Card className="rounded-sm">
                                <CardContent className="p-0">
                                    {tab === "lancamentos" && (
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-left text-sm">
                                                <thead className="bg-muted/50 border-b border-border/50">
                                                    <tr className="text-muted-foreground font-semibold">
                                                        <th className="h-10 px-4 align-middle font-medium">Data</th>
                                                        <th className="h-10 px-4 align-middle font-medium">Descrição</th>
                                                        <th className="h-10 px-4 align-middle font-medium text-right">Valor</th>
                                                        <th className="h-10 px-4 align-middle font-medium">Status</th>
                                                        <th className="h-10 px-4 align-middle w-[60px]"></th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-border/50">
                                                    {loadingLanc ? (
                                                        Array(5).fill(0).map((_, i) => (
                                                            <tr key={i} className="animate-pulse">
                                                                <td colSpan={5} className="px-4 py-3"><div className="h-5 bg-muted rounded-sm" /></td>
                                                            </tr>
                                                        ))
                                                    ) : lancamentos.length === 0 ? (
                                                        <tr>
                                                            <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">
                                                                <Upload className="mx-auto mb-2 h-8 w-8 opacity-30" />
                                                                <p>Nenhum lançamento encontrado.</p>
                                                            </td>
                                                        </tr>
                                                    ) : (
                                                        lancamentos.filter(l => statusFiltro && statusFiltro !== "todos_fake" ? l.status_conciliacao === statusFiltro : true).map((l) => (
                                                            <tr key={l.id} className="hover:bg-muted/30 group">
                                                                <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground">
                                                                    {new Date(l.data).toLocaleDateString("pt-BR", { timeZone: "UTC" })}
                                                                </td>
                                                                <td className="px-4 py-2.5 max-w-[250px]">
                                                                    <div className="flex items-center gap-2">
                                                                        {l.valor >= 0 ? <ArrowUpCircle size={14} className="text-green-500 shrink-0" /> : <ArrowDownCircle size={14} className="text-red-500 shrink-0" />}
                                                                        <span className="truncate font-medium" title={l.descricao || ""}>{l.descricao ?? "—"}</span>
                                                                    </div>
                                                                </td>
                                                                <td className={`px-4 py-2.5 text-right font-bold tabular-nums whitespace-nowrap ${l.valor >= 0 ? "text-green-600 dark:text-green-500" : "text-red-600 dark:text-red-500"}`}>
                                                                    {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(l.valor)}
                                                                </td>
                                                                <td className="px-4 py-2.5 whitespace-nowrap">
                                                                    <StatusBadge status={l.status_conciliacao} />
                                                                </td>
                                                                <td className="px-4 py-2.5 whitespace-nowrap">
                                                                    {l.status_conciliacao === "NAO_CONCILIADO" && (
                                                                        <Button
                                                                            variant="ghost"
                                                                            size="icon"
                                                                            onClick={() => ignorarMutation.mutate(l.id)}
                                                                            disabled={ignorarMutation.isPending}
                                                                            title="Ignorar lançamento"
                                                                            className="h-7 w-7 text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                                                                        >
                                                                            <EyeOff size={14} />
                                                                        </Button>
                                                                    )}
                                                                </td>
                                                            </tr>
                                                        ))
                                                    )}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}

                                    {tab === "sugestoes" && (
                                        <div className="flex flex-col">
                                            {loadingSug ? (
                                                <div className="p-8 text-center">
                                                    <Loader2 className="mx-auto animate-spin text-primary" size={24} />
                                                </div>
                                            ) : sugestoes.length === 0 ? (
                                                <div className="p-12 text-center text-muted-foreground">
                                                    <Lightbulb className="mx-auto mb-2 h-8 w-8 opacity-30" />
                                                    <p>Sem sugestões automáticas no momento.</p>
                                                    <p className="text-xs mt-1">As sugestões cruzam lançamentos não conciliados com despesas/receitas por valor e data (±3 dias).</p>
                                                </div>
                                            ) : (
                                                <div className="divide-y divide-border/50">
                                                    {sugestoes.map((s) => (
                                                        <div key={`${s.lancamento_id}-${s.sugestao_id}`} className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-muted/30">
                                                            <div className="flex-1 min-w-0">
                                                                <div className="flex items-center gap-2 mb-1">
                                                                    <Badge variant={s.confianca === "ALTA" ? "default" : "secondary"} className={s.confianca === "ALTA" ? "bg-green-600 hover:bg-green-700 text-[10px] px-1 py-0 h-4" : "text-[10px] px-1 py-0 h-4"}>
                                                                        {s.confianca}
                                                                    </Badge>
                                                                    <span className="text-xs text-muted-foreground">
                                                                        {new Date(s.data_lanc).toLocaleDateString("pt-BR", { timeZone: "UTC" })} · {s.tipo}
                                                                    </span>
                                                                </div>
                                                                <div className="flex items-center gap-2 text-sm">
                                                                    <span className="text-muted-foreground truncate max-w-[200px]">{s.descricao_lanc}</span>
                                                                    <ChevronRight size={12} className="text-muted-foreground/40 shrink-0" />
                                                                    <span className="font-medium truncate max-w-[200px]">{s.descricao_fin}</span>
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-3 shrink-0">
                                                                <span className="font-bold tabular-nums text-sm">
                                                                    {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(s.valor)}
                                                                </span>
                                                                <Button
                                                                    variant="default"
                                                                    size="sm"
                                                                    onClick={() => conciliarMutation.mutate({
                                                                        lancId: s.lancamento_id,
                                                                        tipo: s.tipo,
                                                                        sugestaoId: s.sugestao_id,
                                                                    })}
                                                                    disabled={conciliarMutation.isPending}
                                                                    className="h-7 text-xs bg-green-600 hover:bg-green-700"
                                                                >
                                                                    <CheckCircle2 size={12} className="mr-1.5" />
                                                                    Conciliar
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </div>
            </div>

            <Dialog open={showNovaConta} onOpenChange={v => { if (!v) setShowNovaConta(false); }}>
                <NovaContaForm onClose={() => setShowNovaConta(false)} />
            </Dialog>
        </div>
    );
}
