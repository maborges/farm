"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MoreHorizontal, Eye, Pencil, Trash2, Fuel, MapPin, Loader2 } from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Card, CardContent } from "@/components/ui/card";
import { StatCard } from "@/components/shared/stat-card";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { toast } from "sonner";
import { AbastecimentoFormModal } from "./abastecimento-form-modal";

interface Abastecimento {
    id: string;
    data: string;
    equipamento_nome: string;
    litros: number;
    preco_litro: number;
    custo_total: number;
    local: "INTERNO" | "EXTERNO";
    tipo_combustivel: string;
}

export function AbastecimentoList() {
    const queryClient = useQueryClient();
    const [editData, setEditData] = useState<Abastecimento | null>(null);
    const [isFormOpen, setIsFormOpen] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null);

    const { data: abastecimentos, isLoading } = useQuery<Abastecimento[]>({
        queryKey: ["abastecimentos"],
        queryFn: () => apiFetch("/frota/abastecimentos"),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/frota/abastecimentos/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["abastecimentos"] });
            toast.success("Registro excluído com sucesso");
        },
        onError: (err: any) => toast.error(err.message || "Erro ao excluir registro"),
    });

    const handleEdit = (abastecimento: Abastecimento) => {
        setEditData(abastecimento);
        setIsFormOpen(true);
    };

    const handleDelete = (id: string) => {
        setDeleteId(id);
    };

    const columns: ColumnDef<Abastecimento>[] = [
        {
            id: "data",
            header: "Data",
            accessorKey: "data",
            cell: (value: string) => format(new Date(value), "dd/MM/yyyy", { locale: ptBR }),
        },
        {
            id: "equipamento",
            header: "Equipamento",
            accessorKey: "equipamento_nome",
            cell: (value: string) => <span className="font-medium text-emerald-700">{value}</span>,
        },
        {
            id: "tipo",
            header: "Combustível",
            accessorKey: "tipo_combustivel",
        },
        {
            id: "litros",
            header: "Litros",
            accessorKey: "litros",
            cell: (value: number) => <span className="tabular-nums font-mono">{value.toLocaleString("pt-BR")} L</span>,
        },
        {
            id: "custo",
            header: "Custo Total",
            accessorKey: "custo_total",
            cell: (value: number) => (
                <span className="font-semibold tabular-nums">
                    {value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                </span>
            ),
        },
        {
            id: "local",
            header: "Local",
            accessorKey: "local",
            cell: (value: string) => (
                <Badge variant="outline" className={
                    value === "INTERNO" 
                        ? "border-agro/30 bg-agro/5 text-agro" 
                        : "border-blue-500/30 bg-blue-500/5 text-blue-600"
                }>
                    {value === "INTERNO" ? "Silo Próprio" : "Posto Externo"}
                </Badge>
            ),
        },
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            accessorKey: "id",
            cell: (id: string, row: Abastecimento) => (
                <div className="flex items-center gap-0 justify-end">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="size-7">
                                <MoreHorizontal className="size-3.5" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem className="gap-2" onClick={() => handleEdit(row)}>
                                <Pencil className="size-4" /> Editar
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                                className="gap-2 text-destructive" 
                                onClick={() => handleDelete(id)}
                                disabled={deleteMutation.isPending}
                            >
                                {deleteMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
                                Excluir
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            ),
        },
    ];

    const stats = {
        totalLitros: abastecimentos?.reduce((acc, curr) => acc + curr.litros, 0) || 0,
        totalCusto: abastecimentos?.reduce((acc, curr) => acc + curr.custo_total, 0) || 0,
        qtdRegistros: abastecimentos?.length || 0,
    };

    return (
        <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
                <StatCard 
                    label="Volume Total" 
                    value={`${stats.totalLitros.toLocaleString("pt-BR")} L`} 
                    icon={Fuel}
                    color="agro" 
                />
                <StatCard 
                    label="Investimento" 
                    value={stats.totalCusto.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })} 
                    icon={Fuel}
                    color="operacional" 
                />
                <StatCard 
                    label="Registros" 
                    value={stats.qtdRegistros.toString()} 
                    icon={MapPin}
                    color="warning" 
                />
            </div>

            <Card className="border-none shadow-sm ring-1 ring-slate-200 overflow-hidden">
                <CardContent className="p-0">
                    <DataTable
                        data={abastecimentos || []}
                        columns={columns}
                        searchable={true}
                        searchPlaceholder="Filtrar por equipamento ou combustível..."
                    />
                </CardContent>
            </Card>

            <AbastecimentoFormModal
                open={isFormOpen}
                onOpenChange={(open) => {
                    setIsFormOpen(open);
                    if (!open) setEditData(null);
                }}
                initialData={editData}
            />

            <AlertDialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Excluir registro?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Esta ação não pode ser desfeita. O registro de abastecimento será removido permanentemente.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => deleteId && deleteMutation.mutate(deleteId)}
                        >
                            Excluir
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
