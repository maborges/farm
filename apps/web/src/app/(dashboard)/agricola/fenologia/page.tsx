"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { 
    CalendarCheck, 
    Plus, 
    Leaf,
    AlertCircle,
    Sprout
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FenologiaRegistroCreateSchema, type FenologiaRegistroCreate } from "@farm/zod-schemas";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface Safra {
    id: string;
    ano_safra: string;
    cultura: string;
    status: string;
    talhao_id: string;
}

interface EscalaBBCH {
    id: string;
    cultura: string;
    codigo: string;
    nome: string;
    descricao: string | null;
    ordem: number;
}

interface RegistroFenologia {
    id: string;
    safra_id: string;
    talhao_id: string;
    escala_id: string;
    data_observacao: string;
    observacao: string | null;
    escala: EscalaBBCH;
    created_at: string;
}

export default function FenologiaPage() {
    const queryClient = useQueryClient();
    const [selectedSafraId, setSelectedSafraId] = useState<string>("all");
    const [isAddOpen, setIsAddOpen] = useState(false);

    // Fetch safras ativas para o filtro e form
    const { data: safras = [], isLoading: isLoadingSafras } = useQuery<Safra[]>({
        queryKey: ["safras", "ativas"],
        queryFn: () => apiFetch("/safras/"),
    });

    const activeSafras = safras.filter(s => !["ENCERRADA", "CANCELADA"].includes(s.status));
    const safraSelecionadaParam = selectedSafraId === "all" ? (activeSafras[0]?.id || null) : selectedSafraId;
    const safraAtualObj = safras.find(s => s.id === safraSelecionadaParam);

    // Fetch registros fenológicos
    const { data: registros = [], isLoading: isLoadingRegistros } = useQuery<RegistroFenologia[]>({
        queryKey: ["fenologia", safraSelecionadaParam],
        queryFn: () => apiFetch(`/safras/${safraSelecionadaParam}/fenologia`),
        enabled: !!safraSelecionadaParam,
    });

    // Fetch escalas BBCH da cultura selecionada
    const { data: escalas = [] } = useQuery<EscalaBBCH[]>({
        queryKey: ["escalas", safraAtualObj?.cultura],
        queryFn: () => apiFetch(`/fenologia/escalas?cultura=${safraAtualObj?.cultura}`),
        enabled: !!safraAtualObj?.cultura,
    });

    const createMutation = useMutation({
        mutationFn: (data: FenologiaRegistroCreate) => 
            apiFetch(`/safras/${data.safra_id}/talhoes/${data.talhao_id}/fenologia`, {
                method: "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["fenologia", safraSelecionadaParam] });
            toast.success("Observação fenológica registrada com sucesso!");
            setIsAddOpen(false);
            reset();
        },
        onError: (err: any) => toast.error(err?.message ?? "Erro ao registrar observação"),
    });

    const { register, handleSubmit, reset, control, watch, setValue } = useForm<FenologiaRegistroCreate>({
        resolver: zodResolver(FenologiaRegistroCreateSchema),
        defaultValues: {
            safra_id: safraAtualObj?.id ?? "",
            talhao_id: safraAtualObj?.talhao_id ?? "",
            data_observacao: new Date().toISOString().split('T')[0],
        }
    });

    // Atualiza form se safra selecionada mudar externamente
    const formSafraId = watch("safra_id");
    const selectedFormSafra = safras.find(s => s.id === formSafraId);

    const columns: ColumnDef<RegistroFenologia>[] = [
        {
            id: "data",
            header: "Data",
            accessorKey: "data_observacao",
            sortable: true,
            exportFormat: (val) => format(new Date(val), "dd/MM/yyyy"),
            cell: (val: string) => (
                <span className="font-medium whitespace-nowrap">
                    {format(new Date(val), "dd MMM yyyy", { locale: ptBR })}
                </span>
            ),
        },
        {
            id: "estagio",
            header: "Estágio (BBCH)",
            accessorFn: (row) => `${row.escala.codigo} - ${row.escala.nome}`,
            sortable: true,
            filterable: true,
            cell: (_, row) => (
                <div>
                    <Badge variant="outline" className="mr-2 rounded-sm font-mono bg-emerald-50 text-emerald-700 border-emerald-200">
                        {row.escala.codigo}
                    </Badge>
                    <span className="font-medium">{row.escala.nome}</span>
                </div>
            )
        },
        {
            id: "cultura",
            header: "Cultura",
            accessorFn: () => safraAtualObj?.cultura ?? "N/A",
            sortable: true,
        },
        {
            id: "observacao",
            header: "Observação",
            accessorKey: "observacao",
            cell: (val: string | null) => (
                <span className="text-muted-foreground text-sm truncate max-w-[300px] block">
                    {val || "—"}
                </span>
            ),
        },
    ];

    if (isLoadingSafras) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-48 w-full" />
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }

    if (activeSafras.length === 0) {
        return (
            <div className="p-6 space-y-6">
                <PageHeader
                    title="Fenologia"
                    description="Acompanhamento fenológico das culturas"
                    icon={<Sprout className="text-primary" size={22} />}
                    breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Fenologia" }]}
                />
                <Alert variant="default" className="bg-amber-50 text-amber-900 border-amber-200">
                    <AlertCircle className="h-4 w-4 stroke-amber-600" />
                    <AlertTitle>Nenhuma safra ativa</AlertTitle>
                    <AlertDescription>
                        Para registrar estágios fenológicos, é necessário ter pelo menos uma safra em andamento.
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Fenologia"
                description="Registre e acompanhe o desenvolvimento (escala BBCH) das culturas no campo."
                icon={<Sprout className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Fenologia" }]}
                actions={
                    <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                        <DialogTrigger 
                            render={
                                <Button variant="outline" size="sm" onClick={() => {
                                    reset({ 
                                        safra_id: safraAtualObj?.id ?? "", 
                                        talhao_id: safraAtualObj?.talhao_id ?? "",
                                        data_observacao: new Date().toISOString().split('T')[0],
                                    });
                                }}>
                                    <Plus className="size-3.5 mr-1.5" /> Registrar BBCH
                                </Button>
                            }
                        />
                        <DialogContent className="sm:max-w-[500px]">
                            <form onSubmit={handleSubmit(d => createMutation.mutate(d))}>
                                <DialogHeader>
                                    <DialogTitle>Novo Registro Fenológico</DialogTitle>
                                    <DialogDescription>
                                        Registre o estágio de desenvolvimento atual da cultura no talhão.
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="grid gap-5 py-4">
                                    <div className="space-y-1.5">
                                        <Label>Safra</Label>
                                        <Controller
                                            name="safra_id"
                                            control={control}
                                            render={({ field }) => (
                                                <Select value={field.value} onValueChange={(val: string) => {
                                                    field.onChange(val);
                                                    const s = safras.find(x => x.id === val);
                                                    if (s) setValue("talhao_id", s.talhao_id);
                                                    setValue("escala_id", "");
                                                }}>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Selecione a safra atrelada" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {activeSafras.map(s => (
                                                            <SelectItem key={s.id} value={s.id}>
                                                                {s.cultura} - {s.ano_safra}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            )}
                                        />
                                    </div>
                                    
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-1.5">
                                            <Label>Data de Observação</Label>
                                            <Input type="date" {...register("data_observacao")} />
                                        </div>
                                        {/* Futuro: se o backend suportar dropdown interativo do talhão, faremos select. Hoje usamos o talhao_id da safra para simplificar. */}
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label>Estágio BBCH ({selectedFormSafra?.cultura || "N/A"})</Label>
                                        <Controller
                                            name="escala_id"
                                            control={control}
                                            render={({ field }) => (
                                                <Select value={field.value} onValueChange={field.onChange}>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Selecione a fase BBCH" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {escalas.length === 0 && (
                                                            <SelectItem value="empty" disabled>Carregando escalas...</SelectItem>
                                                        )}
                                                        {escalas.map(e => (
                                                            <SelectItem key={e.id} value={e.id}>
                                                                <span className="font-mono text-muted-foreground mr-1">[{e.codigo}]</span>
                                                                {e.nome}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            )}
                                        />
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label>Observações (Opcional)</Label>
                                        <Textarea placeholder="Descreva condição foliar, pragas aparentes, etc" className="resize-none" {...register("observacao")} />
                                    </div>
                                </div>
                                <DialogFooter>
                                    <Button variant="outline" size="sm" type="submit" disabled={createMutation.isPending}>Salvar Registro</Button>
                                </DialogFooter>
                            </form>
                        </DialogContent>
                    </Dialog>
                }
            />

            <div className="grid gap-4 md:grid-cols-4">
                <div className="col-span-1 md:col-span-1">
                    <Card className="shadow-sm border-none bg-emerald-700 text-white rounded-sm">
                        <CardContent className="p-6">
                            <Leaf className="size-8 opacity-50 mb-4" />
                            <p className="text-emerald-100 text-sm font-medium">Ciclos Monitorados</p>
                            <h2 className="text-3xl font-bold mt-1">{registros.length}</h2>
                        </CardContent>
                    </Card>
                </div>
                <div className="col-span-1 md:col-span-3">
                    <Card className="shadow-sm flex h-full items-center px-6">
                        <div className="flex flex-col gap-1 w-full max-w-sm">
                            <Label className="text-muted-foreground text-xs uppercase tracking-wider">Filtrar por Safra Ativa</Label>
                            <Select value={selectedSafraId} onValueChange={setSelectedSafraId}>
                                <SelectTrigger className="w-full">
                                    <SelectValue placeholder="Todas as safras..." />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Foco Automático (Destaque)</SelectItem>
                                    {activeSafras.map(s => (
                                        <SelectItem key={s.id} value={s.id}>{s.cultura} — {s.ano_safra}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </Card>
                </div>
            </div>

            {isLoadingRegistros ? (
                <Card className="shadow-sm rounded-sm">
                    <CardContent className="p-6">
                        <div className="space-y-2">
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                        </div>
                    </CardContent>
                </Card>
            ) : (
                <DataTable
                    data={registros}
                    columns={columns}
                    searchable
                    searchPlaceholder="Buscar por observações ou fases..."
                    exportable
                    exportFileName={`fenologia_${safraAtualObj?.cultura ?? "todas"}`}
                    emptyMessage="Nenhuma observação fenológica nesta safra."
                />
            )}
        </div>
    );
}
