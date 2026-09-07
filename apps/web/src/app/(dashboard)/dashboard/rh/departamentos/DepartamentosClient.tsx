"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Building2, Pencil, Plus, Trash2, UserRoundCheck, Users, Landmark } from "lucide-react";
import { cn } from "@/lib/utils";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogBody } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Textarea } from "@/components/ui/textarea";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";

export interface Departamento {
    id: string;
    nome: string;
    descricao?: string | null;
    responsavel_nome?: string | null;
    ativo: boolean;
    total_colaboradores: number;
    created_at: string;
}

const departamentoSchema = z.object({
    nome: z.string().min(1, "O nome é obrigatório"),
    descricao: z.string().optional(),
    responsavel_nome: z.string().optional(),
});
type DepartamentoForm = z.infer<typeof departamentoSchema>;

interface DepartamentoPayload {
    nome: string;
    descricao?: string;
    responsavel_nome?: string;
}

const EMPTY_FORM: DepartamentoForm = {
    nome: "",
    descricao: "",
    responsavel_nome: "",
};

export function DepartamentosClient({ initialData }: { initialData: Departamento[] }) {
    const qc = useQueryClient();
    const [showForm, setShowForm] = useState(false);
    const [editando, setEditando] = useState<Departamento | null>(null);
    const [excluindo, setExcluindo] = useState<Departamento | null>(null);

    const formMethods = useForm<DepartamentoForm>({
        resolver: zodResolver(departamentoSchema),
        defaultValues: EMPTY_FORM,
    });

    const { data: departamentos = [], isLoading, isFetching } = useQuery<Departamento[]>({
        queryKey: ["rh", "departamentos"],
        queryFn: () => apiFetch<Departamento[]>("/rh/departamentos"),
        initialData,
    });

    const criarMut = useMutation({
        mutationFn: (payload: DepartamentoPayload) =>
            apiFetch<Departamento>("/rh/departamentos", { method: "POST", body: payload }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["rh", "departamentos"] });
            fecharForm();
            toast.success("Departamento criado.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao criar departamento."),
    });

    const editarMut = useMutation({
        mutationFn: ({ id, payload }: { id: string; payload: DepartamentoPayload }) =>
            apiFetch<Departamento>(`/rh/departamentos/${id}`, { method: "PATCH", body: payload }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["rh", "departamentos"] });
            fecharForm();
            toast.success("Departamento atualizado.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao atualizar departamento."),
    });

    const desativarMut = useMutation({
        mutationFn: (id: string) => apiFetch<{ message: string }>(`/rh/departamentos/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["rh", "departamentos"] });
            setExcluindo(null);
            toast.success("Departamento desativado.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao desativar departamento."),
    });

    const ativos = departamentos.filter((departamento) => departamento.ativo);
    const inativos = departamentos.filter((departamento) => !departamento.ativo);
    const colaboradoresAlocados = ativos.reduce((sum, departamento) => sum + departamento.total_colaboradores, 0);
    const comResponsavel = ativos.filter((departamento) => !!departamento.responsavel_nome).length;
    const isPending = criarMut.isPending || editarMut.isPending;

    const columns: ColumnDef<Departamento>[] = useMemo(() => [
        {
            id: "nome",
            header: "Departamento",
            accessorKey: "nome",
            cell: (_value, row) => (
                <div className="min-w-[180px]">
                    <div className="font-medium leading-tight">{row.nome}</div>
                    <div className="line-clamp-1 text-[11px] text-muted-foreground">
                        {row.descricao || "Sem descrição"}
                    </div>
                </div>
            ),
        },
        {
            id: "responsavel_nome",
            header: "Responsável",
            accessorKey: "responsavel_nome",
            cell: (_value, row) => row.responsavel_nome || <span className="text-muted-foreground">—</span>,
        },
        {
            id: "total_colaboradores",
            header: "Colaboradores",
            accessorKey: "total_colaboradores",
            cell: (_value, row) => (
                <Badge variant="secondary" className="text-[10px]">
                    <Users className="size-3" />
                    {row.total_colaboradores}
                </Badge>
            ),
            exportFormat: (_value, row) => String(row.total_colaboradores),
        },
        {
            id: "ativo",
            header: "Status",
            accessorKey: "ativo",
            filterOptions: [
                { value: "true", label: "Ativo" },
                { value: "false", label: "Inativo" },
            ],
            cell: (_value, row) => <StatusBadge status={row.ativo ? "ativo" : "inativo"} />,
            exportFormat: (_value, row) => row.ativo ? "Ativo" : "Inativo",
        },
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            isActionColumn: true,
            cell: (_value, row) => (
                <div className="flex items-center justify-end gap-1">
                    <Button
                        size="icon-sm"
                        variant="ghost"
                        title="Editar departamento"
                        onClick={() => abrirEditar(row)}
                    >
                        <Pencil className="size-3.5" />
                    </Button>
                    {row.ativo && (
                        <Button
                            size="icon-sm"
                            variant="ghost"
                            title="Desativar departamento"
                            className="text-destructive hover:text-destructive"
                            onClick={() => setExcluindo(row)}
                        >
                            <Trash2 className="size-3.5" />
                        </Button>
                    )}
                </div>
            ),
        },
    ], []);

    function abrirNovo() {
        setEditando(null);
        formMethods.reset(EMPTY_FORM);
        setShowForm(true);
    }

    function abrirEditar(departamento: Departamento) {
        setEditando(departamento);
        formMethods.reset({
            nome: departamento.nome,
            descricao: departamento.descricao ?? "",
            responsavel_nome: departamento.responsavel_nome ?? "",
        });
        setShowForm(true);
    }

    function fecharForm() {
        setShowForm(false);
        setEditando(null);
        formMethods.reset(EMPTY_FORM);
    }

    function salvar(values: DepartamentoForm) {
        const payload: DepartamentoPayload = {
            nome: values.nome.trim(),
            descricao: values.descricao?.trim() || undefined,
            responsavel_nome: values.responsavel_nome?.trim() || undefined,
        };

        if (editando) {
            editarMut.mutate({ id: editando.id, payload });
            return;
        }

        criarMut.mutate(payload);
    }

    return (
        <div className="p-6 space-y-8">
            <PageHeader
                title="Departamentos"
                description="Organização departamental da propriedade."
                icon={<Landmark className="text-primary size-6" />}
                breadcrumbs={[{ label: "RH", href: "/dashboard/rh" }, { label: "Departamentos" }]}
                actions={
                    <div className="flex gap-2">
                        <Button size="sm" onClick={abrirNovo}>
                            <Plus className="size-4 mr-1.5" /> Novo Departamento
                        </Button>
                    </div>
                }
            />

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard icon={<Building2 className="size-5" />} label="Ativos" value={ativos.length} loading={isLoading} color="text-emerald-700 dark:text-emerald-400" bg="bg-emerald-100 dark:bg-emerald-900/30" />
                <MetricCard icon={<Building2 className="size-5" />} label="Inativos" value={inativos.length} loading={isLoading} color="text-muted-foreground" bg="bg-muted" />
                <MetricCard icon={<Users className="size-5" />} label="Colaboradores" value={colaboradoresAlocados} loading={isLoading} color="text-blue-700 dark:text-blue-400" bg="bg-blue-100 dark:bg-blue-900/30" />
                <MetricCard icon={<UserRoundCheck className="size-5" />} label="Com responsável" value={comResponsavel} loading={isLoading} color="text-purple-700 dark:text-purple-400" bg="bg-purple-100 dark:bg-purple-900/30" />
            </div>

            {isLoading ? (
                <div className="space-y-3">
                    <Skeleton className="h-12 w-full rounded-sm" />
                    <Skeleton className="h-64 w-full rounded-sm" />
                </div>
            ) : departamentos.length === 0 ? (
                <Card>
                    <CardContent className="flex min-h-64 flex-col items-center justify-center gap-3 py-12 text-center">
                        <div className="flex size-11 items-center justify-center rounded-sm bg-primary/10 text-primary">
                            <Building2 className="size-5" />
                        </div>
                        <div>
                            <p className="text-sm font-medium">Nenhum departamento ativo.</p>
                            <p className="text-xs text-muted-foreground">
                                Crie departamentos para organizar a equipe e os responsáveis.
                            </p>
                        </div>
                        <Button size="sm" variant="outline" onClick={abrirNovo}>
                            <Plus className="size-4" /> Criar departamento
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <DataTable
                    columns={columns}
                    data={departamentos}
                    searchPlaceholder="Buscar por departamento, responsável ou descrição..."
                    exportFileName="rh-departamentos"
                    emptyMessage="Nenhum departamento encontrado."
                    isLoading={isFetching && departamentos.length === 0}
                />
            )}

            <Dialog open={showForm || !!editando} onOpenChange={(open) => { if (!open) fecharForm(); }}>
                <DialogContent className="max-w-screen-sm">
                    <DialogHeader>
                        <DialogTitle>{editando ? "Editar departamento" : "Novo departamento"}</DialogTitle>
                        <DialogDescription>
                            Informe nome, responsável e escopo operacional do departamento.
                        </DialogDescription>
                    </DialogHeader>

                    <Form {...formMethods}>
                        <form onSubmit={formMethods.handleSubmit(salvar)}>
                            <DialogBody className="space-y-4">
                                <FormField
                                    control={formMethods.control}
                                    name="nome"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Nome <span className="text-destructive">*</span></FormLabel>
                                            <FormControl>
                                                <Input placeholder="Ex: Operações agrícolas" {...field} value={field.value || ""} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={formMethods.control}
                                    name="responsavel_nome"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Responsável</FormLabel>
                                            <FormControl>
                                                <Input placeholder="Nome do responsável" {...field} value={field.value || ""} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={formMethods.control}
                                    name="descricao"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Descrição</FormLabel>
                                            <FormControl>
                                                <Textarea placeholder="Responsabilidades, turnos..." rows={4} {...field} value={field.value || ""} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </DialogBody>

                            <DialogFooter>
                                <Button type="button" variant="outline" onClick={fecharForm}>
                                    Cancelar
                                </Button>
                                <Button type="submit" disabled={isPending}>
                                    {isPending ? "Salvando..." : editando ? "Salvar alterações" : "Criar"}
                                </Button>
                            </DialogFooter>
                        </form>
                    </Form>
                </DialogContent>
            </Dialog>

            <AlertDialog open={!!excluindo} onOpenChange={(open) => { if (!open) setExcluindo(null); }}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Desativar departamento?</AlertDialogTitle>
                        <AlertDialogDescription>
                            O departamento <strong>{excluindo?.nome}</strong> será desativado.
                            {excluindo && excluindo.total_colaboradores > 0 && (
                                <> Os {excluindo.total_colaboradores} colaboradores vinculados perderão a associação.</>
                            )}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            disabled={desativarMut.isPending}
                            onClick={() => excluindo && desativarMut.mutate(excluindo.id)}
                        >
                            Desativar
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}

function MetricCard({
    icon,
    label,
    value,
    loading,
    color,
    bg,
}: {
    icon: React.ReactNode;
    label: string;
    value: string | number;
    loading: boolean;
    color: string;
    bg: string;
}) {
    return (
        <Card className="shadow-md hover:shadow-lg transition-all duration-200 rounded-lg">
            <CardContent className="p-5 flex items-center gap-4">
                <div className={cn("size-12 rounded-lg flex items-center justify-center shrink-0", bg)}>
                    <span className={color}>{icon}</span>
                </div>
                <div className="min-w-0 flex-1">
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">{label}</p>
                    <div className="text-3xl font-black tabular-nums tracking-tight mt-1">
                        {loading ? <Skeleton className="h-9 w-16" /> : value}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
