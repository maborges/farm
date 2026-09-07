"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { useForm } from "react-hook-form";
import { Sprout, Plus, BookOpen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

interface EscalaFenologica { id: string; nome: string; cultura: string; descricao: string | null; estagios_count?: number; }
interface Safra { id: string; ano_safra: string; cultura: string; }
interface RegistroFenologia { id: string; talhao_id: string; estagio: string; data_observacao: string; observacoes: string | null; }

export default function FenologiaPage() {
    const qc = useQueryClient();
    const { activeFazendaId } = useAppStore();
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";
    const [showEscalaDialog, setShowEscalaDialog] = useState(false);
    const [showRegistroDialog, setShowRegistroDialog] = useState(false);
    const [safraId, setSafraId] = useState("");

    const { data: escalas = [], isLoading: loadingEscalas } = useQuery<EscalaFenologica[]>({
        queryKey: ["agricola", "fenologia", "escalas"],
        queryFn: () => apiFetch("/fenologia/escalas"),
    });
    const { data: safras = [] } = useQuery<Safra[]>({
        queryKey: ["agricola", "safras", activeFazendaId],
        queryFn: () => apiFetch(`/safras${qs}`),
    });
    const { data: registros = [], isLoading: loadingReg } = useQuery<RegistroFenologia[]>({
        queryKey: ["agricola", "fenologia", "registros", safraId],
        queryFn: () => apiFetch(`/fenologia/safras/${safraId}/registros`),
        enabled: !!safraId,
    });

    const escalaMut = useMutation({
        mutationFn: (d: any) => apiFetch("/fenologia/escalas", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["agricola", "fenologia", "escalas"] }); setShowEscalaDialog(false); toast.success("Escala criada."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });
    const registroMut = useMutation({
        mutationFn: (d: any) => apiFetch(`/fenologia/safras/${safraId}/talhoes/${d.talhao_id}/fenologia`, { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["agricola", "fenologia", "registros"] }); setShowRegistroDialog(false); toast.success("Fenologia registrada."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });

    const escalaCols: ColumnDef<EscalaFenologica>[] = [
        { id: "nome", header: "Nome", accessorKey: "nome" },
        { id: "cultura", header: "Cultura", accessorKey: "cultura" },
        { id: "descricao", header: "Descrição", accessorKey: "descricao", cell: (_v, e) => e.descricao || "—" },
    ];
    const registroCols: ColumnDef<RegistroFenologia>[] = [
        { id: "estagio", header: "Estágio", accessorKey: "estagio" },
        { id: "data_observacao", header: "Data", accessorKey: "data_observacao", cell: (_v, r) => new Date(r.data_observacao).toLocaleDateString("pt-BR") },
        { id: "observacoes", header: "Obs.", accessorKey: "observacoes", cell: (_v, r) => r.observacoes || "—" },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Fenologia"
                description="Estádios fenológicos e desenvolvimento das culturas"
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setShowEscalaDialog(true)}>
                            <BookOpen className="size-4 mr-1" /> Nova Escala
                        </Button>
                        <Button size="sm" onClick={() => setShowRegistroDialog(true)} disabled={!safraId}>
                            <Plus className="size-4 mr-1" /> Registrar
                        </Button>
                    </div>
                }
            />

            <Tabs defaultValue="registros">
                <TabsList>
                    <TabsTrigger value="registros"><Sprout className="size-3.5 mr-1" />Registros por Safra</TabsTrigger>
                    <TabsTrigger value="escalas"><BookOpen className="size-3.5 mr-1" />Escalas ({escalas.length})</TabsTrigger>
                </TabsList>

                <TabsContent value="registros" className="mt-4 space-y-4">
                    <div className="flex items-center gap-2">
                        <Label className="text-xs whitespace-nowrap">Safra</Label>
                        <Select onValueChange={setSafraId} value={safraId}>
                            <SelectTrigger className="h-8 text-xs w-52">
                                <SelectValue placeholder="Selecione..." />
                            </SelectTrigger>
                            <SelectContent>
                                {safras.map(s => <SelectItem key={s.id} value={s.id}>{s.ano_safra} — {s.cultura}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    {!safraId
                        ? <div className="text-center py-10 text-sm text-muted-foreground">Selecione uma safra.</div>
                        : loadingReg
                            ? <Skeleton className="h-40 w-full" />
                            : registros.length === 0
                                ? <div className="text-center py-10 text-sm text-muted-foreground">Nenhum registro. <button className="underline" onClick={() => setShowRegistroDialog(true)}>Registrar</button></div>
                                : <DataTable columns={registroCols} data={registros} />
                    }
                </TabsContent>

                <TabsContent value="escalas" className="mt-4">
                    {loadingEscalas ? <Skeleton className="h-40 w-full" /> :
                        escalas.length === 0
                            ? <div className="text-center py-10 text-sm text-muted-foreground">Nenhuma escala. <button className="underline" onClick={() => setShowEscalaDialog(true)}>Criar</button></div>
                            : <DataTable columns={escalaCols} data={escalas} />
                    }
                </TabsContent>
            </Tabs>

            <Dialog open={showEscalaDialog} onOpenChange={v => { if (!v) setShowEscalaDialog(false); }}>
                <EscalaForm onClose={() => setShowEscalaDialog(false)} onSubmit={escalaMut.mutate} loading={escalaMut.isPending} />
            </Dialog>
            <Dialog open={showRegistroDialog} onOpenChange={v => { if (!v) setShowRegistroDialog(false); }}>
                <RegistroForm onClose={() => setShowRegistroDialog(false)} onSubmit={registroMut.mutate} loading={registroMut.isPending} />
            </Dialog>
        </div>
    );
}

function EscalaForm({ onClose, onSubmit, loading }: { onClose: () => void; onSubmit: (d: any) => void; loading: boolean }) {
    const { register, handleSubmit, reset } = useForm<any>();
    return (
        <DialogContent className="max-w-md">
            <DialogHeader><DialogTitle>Nova Escala Fenológica</DialogTitle></DialogHeader>
            <form onSubmit={handleSubmit(d => { onSubmit(d); reset(); })} className="space-y-3">
                <div><Label>Nome *</Label><Input {...register("nome", { required: true })} placeholder="Ex: BBCH Soja" /></div>
                <div><Label>Cultura *</Label><Input {...register("cultura", { required: true })} placeholder="Ex: Soja" /></div>
                <div><Label>Descrição</Label><Input {...register("descricao")} /></div>
                <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => { onClose(); reset(); }}>Cancelar</Button>
                    <Button type="submit" disabled={loading}>{loading ? "Criando…" : "Criar"}</Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}

function RegistroForm({ onClose, onSubmit, loading }: { onClose: () => void; onSubmit: (d: any) => void; loading: boolean }) {
    const { register, handleSubmit, reset } = useForm<any>();
    return (
        <DialogContent className="max-w-md">
            <DialogHeader><DialogTitle>Registrar Fenologia</DialogTitle></DialogHeader>
            <form onSubmit={handleSubmit(d => { onSubmit(d); reset(); })} className="space-y-3">
                <div><Label>ID do Talhão *</Label><Input {...register("talhao_id", { required: true })} /></div>
                <div><Label>Estágio *</Label><Input {...register("estagio", { required: true })} placeholder="Ex: V3, R1, BBCH 13" /></div>
                <div><Label>Data *</Label><Input {...register("data_observacao", { required: true })} type="date" /></div>
                <div><Label>Observações</Label><Input {...register("observacoes")} /></div>
                <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => { onClose(); reset(); }}>Cancelar</Button>
                    <Button type="submit" disabled={loading}>{loading ? "Salvando…" : "Registrar"}</Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}
