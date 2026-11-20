"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useForm } from "react-hook-form";
import { Wrench, Plus, CheckCircle2, Clock, AlertTriangle, DollarSign } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export interface OrdemServico {
    id: string; numero_os: string; maquinario_id: string; tipo: string;
    descricao_problema: string; status: string; data_abertura: string;
    data_conclusao: string | null; custo_total_pecas: number;
    maquinario_nome?: string;
}
export interface Maquinario { id: string; nome: string; tipo: string; }


export function ManutencoesClient({ 
    initialOrdens, initialMaquinarios 
}: { 
    initialOrdens: OrdemServico[], initialMaquinarios: Maquinario[] 
}) {
    const qc = useQueryClient();
    const [showOsDialog, setShowOsDialog] = useState(false);

    const { data: ordens = [], isLoading: loadingOS } = useQuery<OrdemServico[]>({
        queryKey: ["oficina", "os"],
        queryFn: () => apiFetch("/oficina/os"),
        initialData: initialOrdens,
    });
    const { data: maquinarios = [] } = useQuery<Maquinario[]>({
        queryKey: ["frota", "maquinarios"],
        queryFn: () => apiFetch("/frota/"),
        initialData: initialMaquinarios,
    });

    const osMut = useMutation({
        mutationFn: (d: any) => apiFetch("/oficina/os", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["oficina"] }); setShowOsDialog(false); toast.success("OS aberta."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });
    const fecharMut = useMutation({
        mutationFn: (id: string) => apiFetch(`/oficina/os/${id}/fechar`, { method: "PATCH", body: JSON.stringify({}) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["oficina"] }); toast.success("OS concluída."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });
    const iniciarMut = useMutation({
        mutationFn: (id: string) => apiFetch(`/oficina/os/${id}/iniciar`, { method: "PATCH", body: JSON.stringify({}) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["oficina"] }); toast.success("OS iniciada."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });

    const abertas = ordens.filter(o => o.status === "ABERTA").length;
    const emAndamento = ordens.filter(o => o.status === "EM_ANDAMENTO").length;
    const concluidas = ordens.filter(o => o.status === "CONCLUIDA").length;
    const custoTotal = ordens.reduce((s, o) => s + (o.custo_total_pecas || 0), 0);

    const osCols: ColumnDef<OrdemServico>[] = [
        { id: "numero_os", header: "Nº OS", accessorKey: "numero_os" },
        { id: "tipo", header: "Tipo", accessorKey: "tipo" },
        { id: "problema", header: "Problema", accessorKey: "descricao_problema", cell: (_v, o) => <span className="text-xs truncate max-w-[200px] block">{o.descricao_problema}</span> },
        { id: "status", header: "Status", accessorKey: "status", cell: (_v, o) => <WorkflowStatusBadge status={o.status} /> },
        { id: "data_abertura", header: "Abertura", accessorKey: "data_abertura", cell: (_v, o) => new Date(o.data_abertura).toLocaleDateString("pt-BR") },
        { id: "custo", header: "Custo (R$)", accessorKey: "custo_total_pecas", cell: (_v, o) => (o.custo_total_pecas || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) },
        {
            id: "acoes", header: "", exportable: false, sortable: false, filterable: false, cell: (_v, o) => (
                <div className="flex items-center gap-0 justify-end">
                    {o.status === "ABERTA" && <Button size="sm" variant="ghost" onClick={() => iniciarMut.mutate(o.id)}><Clock className="size-3.5 mr-1" />Iniciar</Button>}
                    {(o.status === "ABERTA" || o.status === "EM_ANDAMENTO") && <Button size="sm" variant="ghost" onClick={() => fecharMut.mutate(o.id)}><CheckCircle2 className="size-3.5 mr-1" />Concluir</Button>}
                </div>
            ),
        },
    ];

    const abertas_list = ordens.filter(o => o.status === "ABERTA" || o.status === "EM_ANDAMENTO");
    const historico = ordens.filter(o => o.status === "CONCLUIDA" || o.status === "CANCELADA");

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Manutenções & Oficina"
                description="Gestão de ordens de serviço e histórico de manutenção da frota."
                icon={<Wrench className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Operacional", href: "/operacional" }, { label: "Frota", href: "/dashboard/operacional/frota" }, { label: "Manutenções" }]}
                actions={
                    <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setShowOsDialog(true)}>
                        <Plus className="size-3.5 mr-2" /> Nova OS
                    </Button>
                }
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: "OS em Aberto", value: abertas, warn: abertas > 0, icon: AlertTriangle, bg: "bg-alert-warning-bg border border-alert-warning-border", color: "text-alert-warning-icon" },
                    { label: "Em Andamento", value: emAndamento, warn: emAndamento > 0, icon: Clock, bg: "bg-alert-info-bg border border-alert-info-border", color: "text-alert-info-icon" },
                    { label: "OS Concluídas", value: concluidas, icon: CheckCircle2, bg: "bg-alert-success-bg border border-alert-success-border", color: "text-alert-success-icon" },
                    { label: "Investimento Total", value: custoTotal.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }), icon: DollarSign, bg: "bg-alert-success-bg border border-alert-success-border", color: "text-alert-success-icon" },
                ].map((k, i) => (
                    <Card key={i} className={cn("rounded-sm shadow-sm", k.warn && "border-alert-warning-border")}>
                        <CardContent className="p-5 flex items-start gap-4">
                            <div className={cn("size-10 rounded-sm flex items-center justify-center shrink-0", k.bg)}>
                                <k.icon className={cn("size-5", k.warn ? "text-alert-warning-icon" : k.color)} />
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">{k.label}</p>
                                <div className={cn("text-2xl font-black tabular-nums tracking-tight mt-0.5", k.warn && "text-alert-warning-icon")}>
                                    {loadingOS ? <Skeleton className="h-7 w-8" /> : k.value}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <Tabs defaultValue="abertas" className="w-full">
                <TabsList className="bg-transparent p-0 gap-4 h-auto border-b rounded-none w-full justify-start">
                    <TabsTrigger value="abertas" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent shadow-none px-1 pb-2">
                        <Wrench className="size-3.5 mr-2" />Em Aberto
                        {(abertas + emAndamento) > 0 && <Badge variant="secondary" className="ml-2 text-[10px] h-4 px-1 rounded-sm">{abertas + emAndamento}</Badge>}
                    </TabsTrigger>
                    <TabsTrigger value="historico" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent shadow-none px-1 pb-2">
                        <CheckCircle2 className="size-3.5 mr-2" />Histórico
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="abertas" className="mt-4">
                    {loadingOS ? <Skeleton className="h-40 w-full rounded-sm" /> :
                        abertas_list.length === 0
                            ? <div className="text-center py-12 text-sm text-muted-foreground rounded-sm border-2 border-dashed bg-muted/20">
                                <Wrench className="size-8 mx-auto mb-2 opacity-30 text-primary" />
                                <p>Nenhuma OS em aberto no momento. <button className="underline text-primary" onClick={() => setShowOsDialog(true)}>Abrir nova OS</button></p>
                              </div>
                            : <DataTable columns={osCols} data={abertas_list} searchable exportable />
                    }
                </TabsContent>

                <TabsContent value="historico" className="mt-4">
                    {loadingOS ? <Skeleton className="h-40 w-full rounded-sm" /> :
                        historico.length === 0
                            ? <div className="text-center py-12 text-sm text-muted-foreground rounded-sm border-2 border-dashed bg-muted/20">
                                <CheckCircle2 className="size-8 mx-auto mb-2 opacity-30 text-primary" />
                                <p>O histórico de manutenções está vazio.</p>
                              </div>
                            : <DataTable columns={osCols} data={historico} searchable exportable />
                    }
                </TabsContent>
            </Tabs>

            <Dialog open={showOsDialog} onOpenChange={v => { if (!v) setShowOsDialog(false); }}>
                <OSForm maquinarios={maquinarios} onClose={() => setShowOsDialog(false)} onSubmit={osMut.mutate} loading={osMut.isPending} />
            </Dialog>
        </div>
    );
}

function OSForm({ maquinarios, onClose, onSubmit, loading }: { maquinarios: Maquinario[]; onClose: () => void; onSubmit: (d: any) => void; loading: boolean }) {
    const { register, handleSubmit, reset, setValue } = useForm<any>();
    return (
        <DialogContent className="max-h-[calc(100dvh-2rem)] w-[calc(100vw-2rem)] max-w-2xl gap-0 rounded-sm p-0">
            <DialogHeader className="border-b px-4 py-4 pr-12 sm:px-6">
                <DialogTitle>Abertura de OS</DialogTitle>
                <DialogDescription>
                    Registre a solicitação de manutenção e o estado atual do equipamento.
                </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit(d => { onSubmit(d); reset(); })} className="flex min-h-0 flex-1 flex-col">
                <DialogBody className="flex flex-col gap-4 px-4 py-4 sm:px-6">
                <div className="flex flex-col gap-2">
                    <Label htmlFor="os-maquinario" className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Máquina / Equipamento *</Label>
                    <Select onValueChange={(v: string) => setValue("maquinario_id", v)}>
                        <SelectTrigger id="os-maquinario" className="h-9 rounded-sm text-xs"><SelectValue placeholder="Selecione o maquinário..." /></SelectTrigger>
                        <SelectContent className="rounded-sm text-xs">
                            <SelectGroup>{maquinarios.map(m => <SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>)}</SelectGroup>
                        </SelectContent>
                    </Select>
                </div>
                <div className="flex flex-col gap-2">
                    <Label htmlFor="os-tipo" className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Tipo de Serviço *</Label>
                    <Select onValueChange={(v: string) => setValue("tipo", v)}>
                        <SelectTrigger id="os-tipo" className="h-9 rounded-sm text-xs"><SelectValue placeholder="Selecione o tipo..." /></SelectTrigger>
                        <SelectContent className="rounded-sm text-xs">
                            <SelectGroup>{["CORRETIVA", "PREVENTIVA", "REVISAO", "EMERGENCIAL"].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectGroup>
                        </SelectContent>
                    </Select>
                </div>
                <div className="flex flex-col gap-2">
                    <Label htmlFor="os-descricao" className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Descrição do Problema *</Label>
                    <Textarea id="os-descricao" {...register("descricao_problema", { required: true })} className="min-h-24 resize-y text-xs" placeholder="Descreva o sintoma, a urgência e qualquer observação relevante..." />
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="flex min-w-0 flex-col gap-2"><Label htmlFor="os-horas" className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Horas Atuais</Label><Input id="os-horas" {...register("horas_uso_atual")} className="h-9 rounded-sm text-xs" type="number" step="0.1" /></div>
                    <div className="flex min-w-0 flex-col gap-2"><Label htmlFor="os-km" className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">KM/Hodômetro</Label><Input id="os-km" {...register("km_atual")} className="h-9 rounded-sm text-xs" type="number" /></div>
                </div>
                </DialogBody>
                <DialogFooter className="shrink-0 px-4 sm:px-6">
                    <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => { onClose(); reset(); }}>Cancelar</Button>
                    <Button type="submit" size="sm" className="rounded-sm" disabled={loading}>{loading ? "Abrindo…" : "Abrir OS"}</Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}
