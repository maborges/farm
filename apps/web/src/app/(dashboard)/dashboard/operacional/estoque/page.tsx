"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { useForm } from "react-hook-form";
import {
    Package, Plus, AlertTriangle, ArrowDown, ArrowUp, RefreshCw, Warehouse, BarChart3, DollarSign,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface Deposito { id: string; nome: string; tipo: string; localizacao_desc: string | null; ativo: boolean; }
interface Saldo { id: string; deposito_id: string; produto_id: string; produto_nome: string; deposito_nome: string; quantidade_atual: number; quantidade_reservada: number; quantidade_disponivel: number; unidade_medida: string; estoque_minimo: number | null; custo_medio: number | null; }
interface Movimentacao { id: string; tipo: string; quantidade: number; custo_unitario: number | null; custo_total: number | null; created_at: string; observacao: string | null; }
interface Alerta { produto_id: string; produto_nome: string; deposito_nome: string; quantidade_atual: number; estoque_minimo: number; unidade_medida: string; deficit: number; }

const fmtQtd = (n: number | null | undefined, u?: string) => `${(n ?? 0).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}${u ? ` ${u}` : ""}`;
const fmtBRL = (n: number | null | undefined) => (n ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function EstoquePage() {
    const qc = useQueryClient();
    const { activeFazendaId } = useAppStore();
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

    const [showMovDialog, setShowMovDialog] = useState(false);
    const [movTipo, setMovTipo] = useState<"entrada" | "saida" | "ajuste">("entrada");
    const [showDepDialog, setShowDepDialog] = useState(false);

    const { data: depositos = [], isLoading: loadingDep } = useQuery<Deposito[]>({
        queryKey: ["estoque", "depositos", activeFazendaId],
        queryFn: () => apiFetch(`/estoque/depositos${qs}`),
    });
    const { data: saldos = [], isLoading: loadingSaldos } = useQuery<Saldo[]>({
        queryKey: ["estoque", "saldos", activeFazendaId],
        queryFn: () => apiFetch(`/estoque/saldos${qs}`),
    });
    const { data: movimentacoes = [], isLoading: loadingMov } = useQuery<Movimentacao[]>({
        queryKey: ["estoque", "movimentacoes", activeFazendaId],
        queryFn: () => apiFetch(`/estoque/movimentacoes${qs}`),
    });
    const { data: alertas = [] } = useQuery<Alerta[]>({
        queryKey: ["estoque", "alertas", activeFazendaId],
        queryFn: () => apiFetch(`/estoque/alertas${qs}`),
    });

    const movMut = useMutation({
        mutationFn: (d: any) => apiFetch(`/estoque/movimentacoes/${movTipo}`, { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["estoque"] }); setShowMovDialog(false); toast.success("Movimentação registrada."); },
        onError: (e: any) => toast.error(e.message || "Erro ao registrar."),
    });
    const depMut = useMutation({
        mutationFn: (d: any) => apiFetch("/estoque/depositos", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["estoque", "depositos"] }); setShowDepDialog(false); toast.success("Depósito criado."); },
        onError: (e: any) => toast.error(e.message || "Erro ao criar depósito."),
    });

    const valorTotal = saldos.reduce((acc, s) => acc + s.quantidade_atual * (s.custo_medio || 0), 0);

    const saldoCols: ColumnDef<Saldo>[] = [
        { id: "produto_nome", header: "Produto", accessorKey: "produto_nome" },
        { id: "deposito_nome", header: "Depósito", accessorKey: "deposito_nome" },
        { id: "disponivel", header: "Disponível", accessorKey: "quantidade_disponivel", cell: (_v, s) => fmtQtd(s.quantidade_disponivel, s.unidade_medida) },
        { id: "reservado", header: "Reservado", accessorKey: "quantidade_reservada", cell: (_v, s) => fmtQtd(s.quantidade_reservada, s.unidade_medida) },
        { id: "custo_medio", header: "Custo Médio", accessorKey: "custo_medio", cell: (_v, s) => s.custo_medio ? fmtBRL(s.custo_medio) : "—" },
        {
            id: "status", header: "Status", cell: (_v, s) =>
                s.estoque_minimo && s.quantidade_disponivel < s.estoque_minimo
                    ? <Badge variant="destructive">Abaixo mínimo</Badge>
                    : <Badge variant="secondary">OK</Badge>,
        },
    ];

    const movCols: ColumnDef<Movimentacao>[] = [
        {
            id: "tipo", header: "Tipo", accessorKey: "tipo", cell: (_v, m) => {
                const c: Record<string, string> = { ENTRADA: "bg-green-100 text-green-800", SAIDA: "bg-red-100 text-red-800", AJUSTE: "bg-blue-100 text-blue-800", TRANSFERENCIA: "bg-yellow-100 text-yellow-800" };
                return <span className={`text-xs font-medium px-2 py-0.5 rounded ${c[m.tipo] || "bg-muted"}`}>{m.tipo}</span>;
            },
        },
        { id: "quantidade", header: "Quantidade", accessorKey: "quantidade", cell: (_v, m) => fmtQtd(m.quantidade) },
        { id: "custo_total", header: "Custo Total", accessorKey: "custo_total", cell: (_v, m) => m.custo_total ? fmtBRL(m.custo_total) : "—" },
        { id: "data", header: "Data", accessorKey: "created_at", cell: (_v, m) => new Date(m.created_at).toLocaleDateString("pt-BR") },
        { id: "obs", header: "Obs.", accessorKey: "observacao", cell: (_v, m) => m.observacao || "—" },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Estoque"
                description="Saldos, movimentações e alertas de estoque"
                icon={<Package className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Operacional", href: "/dashboard/operacional" }, { label: "Estoque" }]}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setShowDepDialog(true)}>
                            <Warehouse className="size-3.5 mr-2" /> Depósito
                        </Button>
                        <Button variant="outline" size="sm" className="rounded-sm" onClick={() => { setMovTipo("entrada"); setShowMovDialog(true); }}>
                            <Plus className="size-3.5 mr-2" /> Movimentação
                        </Button>
                    </div>
                }
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: "Itens em Estoque", value: loadingSaldos ? null : saldos.length, icon: Package, bg: "bg-primary/10", color: "text-primary" },
                    { label: "Valor Total", value: loadingSaldos ? null : fmtBRL(valorTotal), icon: DollarSign, bg: "bg-emerald-100 dark:bg-emerald-900/30", color: "text-emerald-600" },
                    { label: "Depósitos Ativos", value: loadingDep ? null : depositos.filter(d => d.ativo).length, icon: Warehouse, bg: "bg-blue-100 dark:bg-blue-900/30", color: "text-blue-600" },
                    { label: "Alertas", value: alertas.length, warn: alertas.length > 0, icon: AlertTriangle, bg: "bg-amber-100 dark:bg-amber-900/30", color: "text-amber-600" },
                ].map(k => (
                    <Card key={k.label} className="rounded-sm shadow-sm">
                        <CardContent className="p-5 flex items-start gap-4">
                            <div className={cn("size-10 rounded-sm flex items-center justify-center shrink-0", k.bg)}>
                                <k.icon className={cn("size-5", k.color)} />
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">{k.label}</p>
                                <div className={cn("text-2xl font-black tabular-nums tracking-tight mt-0.5", k.warn && "text-destructive")}>
                                    {k.value === null ? <Skeleton className="h-7 w-16" /> : k.value}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {alertas.length > 0 && (
                <Card className="rounded-sm border-destructive/20 bg-destructive/5 shadow-none">
                    <CardHeader className="pb-2"><CardTitle className="text-[10px] font-bold uppercase tracking-wider flex items-center gap-2 text-destructive"><AlertTriangle className="size-4" />Itens Abaixo do Estoque Mínimo</CardTitle></CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-2">
                            {alertas.map(a => (
                                <div key={a.produto_id} className="text-[10px] uppercase font-bold tracking-tight border border-destructive/20 rounded-sm bg-white/50 px-2 py-1 flex items-center gap-2">
                                    <span className="text-muted-foreground">{a.produto_nome}</span>
                                    <span className="text-[9px] opacity-50">({a.deposito_nome})</span>
                                    <span className="text-destructive">DÉFICIT: {fmtQtd(a.deficit, a.unidade_medida)}</span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            <Tabs defaultValue="saldos" className="w-full">
                <TabsList className="bg-transparent p-0 gap-4 h-auto border-b rounded-none w-full justify-start">
                    <TabsTrigger value="saldos" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent shadow-none px-1 pb-2">
                        <Package className="size-3.5 mr-2" />Saldos
                    </TabsTrigger>
                    <TabsTrigger value="movimentacoes" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent shadow-none px-1 pb-2">
                        <BarChart3 className="size-3.5 mr-2" />Movimentações
                    </TabsTrigger>
                    <TabsTrigger value="depositos" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent shadow-none px-1 pb-2">
                        <Warehouse className="size-3.5 mr-2" />Depósitos
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="saldos" className="mt-4">
                    {loadingSaldos ? <Skeleton className="h-40 w-full rounded-sm" /> : <DataTable columns={saldoCols} data={saldos} searchable exportable />}
                </TabsContent>

                <TabsContent value="movimentacoes" className="mt-4">
                    <div className="flex gap-2 mb-3">
                        {(["entrada", "saida", "ajuste"] as const).map(t => (
                            <Button key={t} size="sm" variant="outline" className="rounded-sm" onClick={() => { setMovTipo(t); setShowMovDialog(true); }}>
                                {t === "entrada" ? <ArrowDown className="size-3.5 mr-2 text-green-600" /> : t === "saida" ? <ArrowUp className="size-3.5 mr-2 text-red-600" /> : <RefreshCw className="size-3.5 mr-2 text-blue-600" />}
                                <span className="uppercase text-[10px] font-bold">{t}</span>
                            </Button>
                        ))}
                    </div>
                    {loadingMov ? <Skeleton className="h-40 w-full rounded-sm" /> : <DataTable columns={movCols} data={movimentacoes} searchable exportable />}
                </TabsContent>

                <TabsContent value="depositos" className="mt-4">
                    {loadingDep ? <Skeleton className="h-40 w-full rounded-sm" /> : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {depositos.map(d => (
                                <Card key={d.id} className={cn("rounded-sm shadow-sm", !d.ativo && "opacity-50")}>
                                    <CardContent className="pt-4">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="font-bold text-xs text-primary uppercase">{d.nome}</p>
                                                <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">{d.tipo}{d.localizacao_desc ? ` · ${d.localizacao_desc}` : ""}</p>
                                            </div>
                                            <StatusBadge status={d.ativo ? "ativo" : "inativo"} />
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                            {depositos.length === 0 && (
                                <div className="col-span-full text-center py-12 rounded-sm border-2 border-dashed bg-muted/20">
                                    <Warehouse className="size-8 mx-auto mb-2 opacity-30 text-primary" />
                                    <p className="text-sm text-muted-foreground mb-4">Nenhum depósito cadastrado</p>
                                    <Button size="sm" variant="outline" className="rounded-sm" onClick={() => setShowDepDialog(true)}><Plus className="size-3.5 mr-2" /> Cadastrar Depósito</Button>
                                </div>
                            )}
                        </div>
                    )}
                </TabsContent>
            </Tabs>

            {/* Dialogs */}
            <Dialog open={showMovDialog} onOpenChange={(v: boolean) => { if (!v) setShowMovDialog(false); }}>
                <MovimentacaoForm tipo={movTipo} depositos={depositos} onClose={() => setShowMovDialog(false)} onSubmit={movMut.mutate} loading={movMut.isPending} />
            </Dialog>

            <Dialog open={showDepDialog} onOpenChange={(v: boolean) => { if (!v) setShowDepDialog(false); }}>
                <DepositoForm fazendaId={activeFazendaId} onClose={() => setShowDepDialog(false)} onSubmit={depMut.mutate} loading={depMut.isPending} />
            </Dialog>
        </div>
    );
}

function MovimentacaoForm({ tipo, depositos, onClose, onSubmit, loading }: { tipo: "entrada" | "saida" | "ajuste"; depositos: Deposito[]; onClose: () => void; onSubmit: (d: any) => void; loading: boolean }) {
    const { register, handleSubmit, reset, setValue } = useForm();
    const label = { entrada: "Entrada", saida: "Saída", ajuste: "Ajuste" }[tipo];
    return (
        <DialogContent className="max-w-md rounded-sm">
            <DialogHeader><DialogTitle className="font-bold text-primary">Registrar {label}</DialogTitle></DialogHeader>
            <form onSubmit={handleSubmit(d => { onSubmit({ ...d, quantidade: Number(d.quantidade), custo_unitario: d.custo_unitario ? Number(d.custo_unitario) : undefined }); reset(); })} className="space-y-4 pt-4">
                <div className="space-y-2">
                    <Label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Depósito</Label>
                    <Select onValueChange={(v: string) => setValue("deposito_id", v as any)}>
                        <SelectTrigger className="h-8 rounded-sm text-xs">
                            <SelectValue placeholder="Selecione..." />
                        </SelectTrigger>
                        <SelectContent className="rounded-sm text-xs">
                            {depositos.filter(d => d.ativo).map(d => (
                                <SelectItem key={d.id} value={d.id}>{d.nome}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-2"><Label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Produto ID</Label><Input {...register("produto_id", { required: true })} className="h-8 rounded-sm text-xs" placeholder="UUID do produto" /></div>
                <div className="space-y-2"><Label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Quantidade</Label><Input {...register("quantidade", { required: true })} className="h-8 rounded-sm text-xs" type="number" step="0.01" min="0.01" /></div>
                {tipo !== "ajuste" && <div className="space-y-2"><Label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Custo Unitário (R$)</Label><Input {...register("custo_unitario")} className="h-8 rounded-sm text-xs" type="number" step="0.01" /></div>}
                <div className="space-y-2"><Label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Observação</Label><Input {...register("observacao")} className="h-8 rounded-sm text-xs" placeholder="Opcional" /></div>
                <DialogFooter className="gap-2 pt-2">
                    <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => { onClose(); reset(); }}>Cancelar</Button>
                    <Button type="submit" size="sm" className="rounded-sm" disabled={loading}>{loading ? "Salvando…" : `Registrar ${label}`}</Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}

function DepositoForm({ fazendaId, onClose, onSubmit, loading }: { fazendaId: string | null; onClose: () => void; onSubmit: (d: any) => void; loading: boolean }) {
    const { register, handleSubmit, reset, setValue } = useForm<any>({ defaultValues: { tipo: "GERAL" } });
    return (
        <DialogContent className="max-w-md rounded-sm">
            <DialogHeader><DialogTitle className="font-bold text-primary italic border-b pb-2">Novo Depósito</DialogTitle></DialogHeader>
            <form onSubmit={handleSubmit(d => { onSubmit({ ...d, unidade_produtiva_id: fazendaId }); reset(); })} className="space-y-4 pt-4">
                <div className="space-y-2"><Label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Nome</Label><Input {...register("nome", { required: true })} className="h-8 rounded-sm text-xs" placeholder="Ex: Almoxarifado Principal" /></div>
                <div className="space-y-2"><Label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Tipo</Label>
                    <Select onValueChange={(v: string) => setValue("tipo", v as any)} defaultValue="GERAL">
                        <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger>
                        <SelectContent className="rounded-sm text-xs">
                            {[
                                ["GERAL", "Geral / Almoxarifado"],
                                ["COMBUSTIVEL", "Combustível"],
                                ["DEFENSIVOS", "Defensivos"],
                                ["PECAS", "Peças"],
                                ["GRAOS", "Grãos"],
                                ["OUTROS", "Outros"],
                            ].map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-2"><Label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Localização</Label><Input {...register("localizacao_desc")} className="h-8 rounded-sm text-xs" placeholder="Ex: Sede principal" /></div>
                <DialogFooter className="gap-2 pt-2">
                    <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => { onClose(); reset(); }}>Cancelar</Button>
                    <Button type="submit" size="sm" className="rounded-sm" disabled={loading}>{loading ? "Criando…" : "Criar Depósito"}</Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}
