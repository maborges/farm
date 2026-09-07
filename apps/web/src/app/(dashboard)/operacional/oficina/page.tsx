"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Wrench, Plus, Search, ClipboardList, Clock, CheckCircle2, AlertCircle, User, Tractor } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useForm, Controller } from "react-hook-form";
import { toast } from "sonner";
import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

interface OS {
    id: string;
    numero_os: string;
    status: string;
    tipo: string;
    descricao_problema: string;
    data_abertura: string;
    tecnico_responsavel?: string;
}

const createOSColumns = (iniciarMutation: any, fecharMutation: any): ColumnDef<OS>[] => [
    {
        id: "numero_os",
        header: "Número O.S.",
        accessorKey: "numero_os",
        sortable: true,
        cell: (value) => <span className="font-mono font-bold text-primary">{value}</span>,
    },
    {
        id: "data_abertura",
        header: "Data Abertura",
        accessorKey: "data_abertura",
        sortable: true,
        cell: (value: string) => (
            <span className="text-xs">
                {format(new Date(value), "dd/MM/yyyy HH:mm", { locale: ptBR })}
            </span>
        ),
    },
    {
        id: "tipo",
        header: "Tipo",
        accessorKey: "tipo",
        sortable: true,
        cell: (value) => <Badge variant="secondary" className="text-[10px]">{value}</Badge>,
    },
    {
        id: "descricao_problema",
        header: "Descrição",
        accessorKey: "descricao_problema",
        sortable: false,
        cell: (value: string) => (
            <span className="max-w-[300px] truncate text-xs" title={value}>
                {value}
            </span>
        ),
    },
    {
        id: "status",
        header: "Status",
        accessorKey: "status",
        sortable: true,
        cell: (value: string) => (
            <Badge variant="ghost" className={
                value === 'ABERTA' ? 'bg-blue-500/5 text-blue-600 border-blue-200' :
                    value === 'EM_EXECUCAO' ? 'bg-amber-500/5 text-amber-600 border-amber-200' :
                        'bg-green-500/5 text-green-600 border-green-200'
            }>
                {value === 'ABERTA' && <AlertCircle size={10} className="mr-1" />}
                {value === 'EM_EXECUCAO' && <Clock size={10} className="mr-1" />}
                {value === 'CONCLUIDA' && <CheckCircle2 size={10} className="mr-1" />}
                {value}
            </Badge>
        ),
    },
    {
        id: "acoes",
        header: "",
        accessorKey: "id",
        sortable: false,
        filterable: false,
        exportable: false,
        cell: (id: string, row: OS) => (
            <div className="flex items-center gap-0 justify-end">
                {row.status === "ABERTA" && (
                    <Button
                        variant="ghost" size="sm"
                        className="text-amber-600 hover:bg-amber-50"
                        disabled={iniciarMutation.isPending}
                        onClick={() => iniciarMutation.mutate(id)}
                    >
                        Iniciar
                    </Button>
                )}
                {(row.status === "ABERTA" || row.status === "EM_EXECUCAO") && (
                    <Button
                        variant="ghost" size="sm"
                        className="text-green-600 hover:bg-green-50"
                        disabled={fecharMutation.isPending}
                        onClick={() => fecharMutation.mutate(id)}
                    >
                        Fechar
                    </Button>
                )}
            </div>
        ),
    },
];

export default function OficinaPage() {
    const queryClient = useQueryClient();
    const [isAddOpen, setIsAddOpen] = useState(false);

    const { data: ordens, isLoading } = useQuery<OS[]>({
        queryKey: ["ordens-servico"],
        queryFn: () => apiFetch("/oficina/os")
    });

    const { data: maquinas } = useQuery<any[]>({
        queryKey: ["maquinas"],
        queryFn: () => apiFetch("/frota/"),
        enabled: isAddOpen,
    });

    const iniciarMutation = useMutation({
        mutationFn: (osId: string) => apiFetch(`/oficina/os/${osId}/iniciar`, { method: "PATCH" }),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["ordens-servico"] }); toast.success("OS em execução!"); },
        onError: (err: any) => toast.error(err.message),
    });

    const fecharMutation = useMutation({
        mutationFn: (osId: string) => apiFetch(`/oficina/os/${osId}/fechar`, { method: "PATCH", body: JSON.stringify({}) }),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["ordens-servico"] }); toast.success("OS concluída e estoque baixado!"); },
        onError: (err: any) => toast.error(err.message),
    });

    const createMutation = useMutation({
        mutationFn: (data: any) => apiFetch("/oficina/os", {
            method: "POST",
            body: JSON.stringify(data)
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["ordens-servico"] });
            queryClient.invalidateQueries({ queryKey: ["maquinas"] });
            toast.success("Ordem de Serviço aberta com sucesso!");
            setIsAddOpen(false);
            reset();
        }
    });

    const { register, handleSubmit, control, reset } = useForm();

    const onSubmit = (data: any) => {
        createMutation.mutate(data);
    };

    if (isLoading) {
        return <div className="p-8 space-y-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-64 w-full" /></div>;
    }

    return (
        <div className="p-4 md:p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto w-full overflow-hidden">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <Wrench className="text-primary" /> Oficina e Manutenções
                    </h1>
                    <p className="text-muted-foreground mt-1">Gerenciamento de reparos, revisões e ordens de serviço da frota.</p>
                </div>

                <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                    <DialogTrigger>
                        <Button size="sm" variant="outline" className="gap-2">
                            <Plus size={16} /> Abrir O.S.
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[600px]">
                        <form onSubmit={handleSubmit(onSubmit)}>
                            <DialogHeader>
                                <DialogTitle>Abertura de Ordem de Serviço</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Equipamento</Label>
                                        <Controller
                                            name="maquinario_id"
                                            control={control}
                                            rules={{ required: true }}
                                            render={({ field }) => (
                                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Selecione a máquina" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {maquinas?.map(m => (
                                                            <SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            )}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Tipo de Serviço</Label>
                                        <Controller
                                            name="tipo"
                                            control={control}
                                            defaultValue="CORRETIVA"
                                            render={({ field }) => (
                                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="PREVENTIVA">Preventiva (Revisão)</SelectItem>
                                                        <SelectItem value="CORRETIVA">Corretiva (Quebra)</SelectItem>
                                                        <SelectItem value="REVISAO">Revisão Periódica</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            )}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label>Descrição do Problema / Solicitação</Label>
                                    <Textarea
                                        placeholder="Descreva o que precisa ser feito ou o defeito apresentado..."
                                        {...register("descricao_problema", { required: true })}
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Horímetro Atual</Label>
                                        <Input type="number" step="0.1" {...register("horimetro_na_abertura", { required: true })} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Técnico Responsável</Label>
                                        <Input placeholder="Nome do mecânico" {...register("tecnico_responsavel")} />
                                    </div>
                                </div>
                            </div>
                            <DialogFooter>
                                <Button type="submit" disabled={createMutation.isPending} className="w-full">Abrir Ordem de Serviço</Button>
                            </DialogFooter>
                        </form>
                    </DialogContent>
                </Dialog>
            </div>

            <div className="grid gap-6 md:grid-cols-4">
                <Card className="bg-primary/5 border-none shadow-none">
                    <CardHeader className="pb-2">
                        <CardDescription className="text-xs font-bold uppercase">Ordens Abertas</CardDescription>
                        <CardTitle className="text-2xl">{ordens?.filter(o => o.status === 'ABERTA').length || 0}</CardTitle>
                    </CardHeader>
                </Card>
                <Card className="bg-amber-500/5 border-none shadow-none">
                    <CardHeader className="pb-2">
                        <CardDescription className="text-xs font-bold uppercase text-amber-700">Em Execução</CardDescription>
                        <CardTitle className="text-2xl">{ordens?.filter(o => o.status === 'EM_EXECUCAO').length || 0}</CardTitle>
                    </CardHeader>
                </Card>
                <Card className="bg-green-500/5 border-none shadow-none">
                    <CardHeader className="pb-2">
                        <CardDescription className="text-xs font-bold uppercase text-green-700">Concluídas (7d)</CardDescription>
                        <CardTitle className="text-2xl">{ordens?.filter(o => o.status === 'CONCLUIDA').length || 0}</CardTitle>
                    </CardHeader>
                </Card>
            </div>

            <Card className="border-none shadow-sm bg-surface">
                <CardHeader>
                    <CardTitle className="text-xl">Histórico de Manutenções</CardTitle>
                </CardHeader>
                <CardContent>
                    <DataTable
                        data={ordens || []}
                        columns={createOSColumns(iniciarMutation, fecharMutation)}
                        searchable={true}
                        searchPlaceholder="Buscar por O.S. ou máquina..."
                        exportable={true}
                        exportFileName="ordens-servico"
                        emptyMessage="Nenhuma ordem de serviço registrada"
                    />
                </CardContent>
            </Card>
        </div>
    );
}
