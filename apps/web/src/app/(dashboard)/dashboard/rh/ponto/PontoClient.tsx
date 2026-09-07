"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { useForm } from "react-hook-form";
import { Clock, Plus, CheckCircle2, DollarSign } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";

export interface Diaria {
    id: string; colaborador_id: string; data: string; horas_trabalhadas: number;
    atividade: string; valor_diaria: number; status: string; data_pagamento: string | null;
}
export interface Colaborador { id: string; nome: string; valor_diaria: number | null; }


export function PontoClient({ 
    initialDiarias, initialColaboradores, initialActiveFazendaId 
}: { 
    initialDiarias: Diaria[], initialColaboradores: Colaborador[], initialActiveFazendaId?: string 
}) {
    const qc = useQueryClient();
    const { activeFazendaId } = useAppStore();
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";
    const [showDialog, setShowDialog] = useState(false);

    const { data: diarias = [], isLoading } = useQuery<Diaria[]>({
        queryKey: ["rh", "diarias", activeFazendaId],
        queryFn: () => apiFetch(`/rh/diarias${qs}`),
        initialData: activeFazendaId === initialActiveFazendaId ? initialDiarias : undefined,
    });
    const { data: colaboradores = [] } = useQuery<Colaborador[]>({
        queryKey: ["rh", "colaboradores", activeFazendaId],
        queryFn: () => apiFetch(`/rh/colaboradores${qs}`),
        initialData: activeFazendaId === initialActiveFazendaId ? initialColaboradores : undefined,
    });

    const mut = useMutation({
        mutationFn: (d: any) => apiFetch("/rh/diarias", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["rh", "diarias"] }); setShowDialog(false); toast.success("Diária lançada."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });
    const pagarMut = useMutation({
        mutationFn: (ids: string[]) => apiFetch("/rh/diarias/pagar-lote", { method: "POST", body: JSON.stringify({ ids }) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["rh", "diarias"] }); toast.success("Diárias pagas."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });

    const pendentes = diarias.filter(d => d.status === "PENDENTE");
    const pagas = diarias.filter(d => d.status === "PAGO");
    const totalPendente = pendentes.reduce((s, d) => s + d.valor_diaria, 0);

    const cols: ColumnDef<Diaria>[] = [
        { id: "colaborador", header: "Colaborador", accessorKey: "colaborador_id", cell: (_v, d) => colaboradores.find(c => c.id === d.colaborador_id)?.nome || d.colaborador_id },
        { id: "data", header: "Data", accessorKey: "data", cell: (_v, d) => new Date(d.data).toLocaleDateString("pt-BR") },
        { id: "atividade", header: "Atividade", accessorKey: "atividade" },
        { id: "horas", header: "Horas", accessorKey: "horas_trabalhadas", cell: (_v, d) => `${d.horas_trabalhadas}h` },
        { id: "valor", header: "Valor", accessorKey: "valor_diaria", cell: (_v, d) => d.valor_diaria.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) },
        { id: "status", header: "Status", accessorKey: "status", cell: (_v, d) => <WorkflowStatusBadge status={d.status} /> },
        {
            id: "acoes", header: "", exportable: false, sortable: false, filterable: false,
            cell: (_v, d) => (
                <div className="flex items-center gap-0 justify-end">
                    {d.status === "PENDENTE" && (
                        <Button size="icon" variant="ghost" className="size-7 text-green-600 hover:text-green-600" aria-label="Pagar diária" onClick={() => pagarMut.mutate([d.id])}>
                            <DollarSign className="size-3.5" />
                        </Button>
                    )}
                </div>
            ),
        },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Apontamento de Diárias"
                description="Registro de ponto e controle de frequência de diaristas"
                icon={<Clock className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Pessoas & RH", href: "/dashboard/rh" },
                    { label: "Registro de Ponto" }
                ]}
                actions={
                    <div className="flex gap-2">
                        {pendentes.length > 0 && (
                            <Button variant="outline" size="sm" onClick={() => pagarMut.mutate(pendentes.map(d => d.id))} className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold">
                                <DollarSign className="size-4 mr-1" />Pagar Todas ({pendentes.length})
                            </Button>
                        )}
                        <Button size="sm" onClick={() => setShowDialog(true)} className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold" variant="outline">
                            <Plus className="size-4 mr-1.5" /> Lançar Diária
                        </Button>
                    </div>
                }
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: "Total de Registros", value: diarias.length, color: "text-foreground", border: "border-l-primary/60" },
                    { label: "Pendentes", value: pendentes.length, color: pendentes.length > 0 ? "text-yellow-600" : "text-foreground", border: pendentes.length > 0 ? "border-l-yellow-500/60" : "border-l-primary/60" },
                    { label: "Pagas", value: pagas.length, color: "text-green-600", border: "border-l-green-500/60" },
                    { label: "A Pagar (R$)", value: totalPendente.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }), color: totalPendente > 0 ? "text-yellow-600" : "text-foreground", border: totalPendente > 0 ? "border-l-yellow-500/60" : "border-l-primary/60" },
                ].map(k => (
                    <Card key={k.label} className={`rounded-sm border-l-[3px] ${k.border} shadow-sm transition-all hover:shadow-md`}>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">{k.label}</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className={`text-2xl font-black tabular-nums ${k.color}`}>
                                {isLoading ? <Skeleton className="h-6 w-14" /> : k.value}
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <Tabs defaultValue="pendentes">
                <TabsList>
                    <TabsTrigger value="pendentes"><Clock className="size-3.5 mr-1" />Pendentes {pendentes.length > 0 && <Badge className="ml-1 text-[10px] h-4">{pendentes.length}</Badge>}</TabsTrigger>
                    <TabsTrigger value="pagas"><CheckCircle2 className="size-3.5 mr-1" />Pagas</TabsTrigger>
                </TabsList>
                <TabsContent value="pendentes" className="mt-4">
                    {isLoading ? <Skeleton className="h-40 w-full" /> :
                        pendentes.length === 0
                            ? <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-muted/10 rounded-lg border border-dashed"><div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4"><Clock className="size-6 text-primary" /></div><h3 className="text-lg font-semibold mb-1">Nenhuma diária pendente</h3><p className="text-sm text-muted-foreground max-w-sm mb-5">Não há diárias aguardando pagamento.</p><Button size="sm" variant="outline" onClick={() => setShowDialog(true)} className="rounded-sm"><Plus className="size-4 mr-1.5" /> Lançar Diária</Button></div>
                            : <DataTable columns={cols} data={pendentes} />}
                </TabsContent>
                <TabsContent value="pagas" className="mt-4">
                    {isLoading ? <Skeleton className="h-40 w-full" /> :
                        pagas.length === 0
                            ? <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-muted/10 rounded-lg border border-dashed"><div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4"><CheckCircle2 className="size-6 text-primary" /></div><h3 className="text-lg font-semibold mb-1">Nenhuma diária paga</h3><p className="text-sm text-muted-foreground max-w-sm">Nenhum registro de pagamento finalizado.</p></div>
                            : <DataTable columns={cols} data={pagas} />}
                </TabsContent>
            </Tabs>

            <Dialog open={showDialog} onOpenChange={v => { if (!v) setShowDialog(false); }}>
                <DiariaForm colaboradores={colaboradores} fazendaId={activeFazendaId} onClose={() => setShowDialog(false)} onSubmit={mut.mutate} loading={mut.isPending} />
            </Dialog>
        </div>
    );
}

function DiariaForm({ colaboradores, fazendaId, onClose, onSubmit, loading }: { colaboradores: Colaborador[]; fazendaId: string | null; onClose: () => void; onSubmit: (d: any) => void; loading: boolean }) {
    const { register, handleSubmit, reset, setValue } = useForm<any>({ defaultValues: { horas_trabalhadas: 8, atividade: "GERAL" } });
    return (
        <DialogContent className="max-w-md">
            <DialogHeader><DialogTitle>Lançar Diária</DialogTitle></DialogHeader>
            <form onSubmit={handleSubmit(d => { onSubmit({ ...d, unidade_produtiva_id: fazendaId, horas_trabalhadas: Number(d.horas_trabalhadas), valor_diaria: Number(d.valor_diaria) }); reset(); })} className="space-y-3">
                <div><Label>Colaborador *</Label>
                    <Select onValueChange={(v: string) => { setValue("colaborador_id", v); const c = colaboradores.find(x => x.id === v); if (c?.valor_diaria) setValue("valor_diaria", c.valor_diaria); }}>
                        <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
                        <SelectContent>{colaboradores.filter(c => (c as any).ativo !== false).map(c => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}</SelectContent>
                    </Select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                    <div><Label>Data *</Label><Input {...register("data", { required: true })} type="date" /></div>
                    <div><Label>Horas</Label><Input {...register("horas_trabalhadas")} type="number" step="0.5" /></div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                    <div><Label>Atividade</Label><Input {...register("atividade")} placeholder="Ex: PLANTIO" /></div>
                    <div><Label>Valor (R$) *</Label><Input {...register("valor_diaria", { required: true })} type="number" step="0.01" /></div>
                </div>
                <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => { onClose(); reset(); }}>Cancelar</Button>
                    <Button type="submit" disabled={loading}>{loading ? "Lançando…" : "Lançar"}</Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}
