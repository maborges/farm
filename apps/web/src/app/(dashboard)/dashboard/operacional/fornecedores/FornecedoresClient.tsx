"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useForm } from "react-hook-form";
import { Users, Plus, Star, Edit, XCircle, Save, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
    Dialog,
    DialogBody,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { toast } from "sonner";

function formatCnpjCpf(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 14);
    if (digits.length <= 11) {
        return digits
            .replace(/(\d{3})(\d)/, "$1.$2")
            .replace(/(\d{3})(\d)/, "$1.$2")
            .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
    }
    return digits
        .replace(/(\d{2})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d)/, "$1/$2")
        .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
}

function hasStatus(error: unknown, status: number): boolean {
    return typeof error === "object" && error !== null && "status" in error && error.status === status;
}

export interface Fornecedor {
    id: string; nome_fantasia: string; cnpj_cpf: string | null;
    email: string | null; telefone: string | null;
    condicoes_pagamento: string | null; prazo_entrega_dias: number | null;
    avaliacao: number | null;
}

interface FornecedorFormValues {
    nome_fantasia: string;
    cnpj_cpf: string;
    email: string;
    telefone: string;
    condicoes_pagamento: string;
    prazo_entrega_dias: string;
    avaliacao: string;
}

interface FornecedorPayload {
    nome_fantasia: string;
    cnpj_cpf: string;
    email: string;
    telefone: string;
    condicoes_pagamento: string;
    prazo_entrega_dias: number | null;
    avaliacao: number | null;
}

export function FornecedoresClient({ initialData }: { initialData: Fornecedor[] }) {
    const qc = useQueryClient();
    const [showDialog, setShowDialog] = useState(false);
    const [selectedFornecedor, setSelectedFornecedor] = useState<Fornecedor | null>(null);

    const { data: fornecedores = [], isLoading, error } = useQuery<Fornecedor[]>({
        queryKey: ["compras", "fornecedores"],
        queryFn: () => apiFetch("/compras/fornecedores"),
        initialData,
    });

    const mut = useMutation({
        mutationFn: (d: FornecedorFormValues) => {
            const payload: FornecedorPayload = {
                ...d,
                prazo_entrega_dias: d.prazo_entrega_dias !== "" && d.prazo_entrega_dias != null ? Number(d.prazo_entrega_dias) : null,
                avaliacao: d.avaliacao !== "" && d.avaliacao != null ? Number(d.avaliacao) : null,
            };
            if (selectedFornecedor) {
                return apiFetch(`/compras/fornecedores/${selectedFornecedor.id}`, { method: "PUT", body: JSON.stringify(payload) });
            }
            return apiFetch("/compras/fornecedores", { method: "POST", body: JSON.stringify(payload) });
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["compras", "fornecedores"] });
            setShowDialog(false);
            setSelectedFornecedor(null);
            toast.success(selectedFornecedor ? "Fornecedor atualizado." : "Fornecedor cadastrado.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro."),
    });

    const columns: ColumnDef<Fornecedor>[] = [
        { id: "nome_fantasia", header: "Nome / Razão Social", accessorKey: "nome_fantasia" },
        { id: "cnpj_cpf", header: "CNPJ / CPF", accessorKey: "cnpj_cpf", cell: (_v, f) => f.cnpj_cpf ? formatCnpjCpf(f.cnpj_cpf) : "—" },
        { id: "email", header: "E-mail", accessorKey: "email", cell: (_v, f) => f.email || "—" },
        { id: "telefone", header: "Telefone", accessorKey: "telefone", cell: (_v, f) => f.telefone || "—" },
        { id: "condicoes_pagamento", header: "Pagamento", accessorKey: "condicoes_pagamento", cell: (_v, f) => f.condicoes_pagamento || "—" },
        { id: "prazo_entrega_dias", header: "Prazo (dias)", accessorKey: "prazo_entrega_dias", cell: (_v, f) => f.prazo_entrega_dias ?? "—" },
        {
            id: "avaliacao", header: "Avaliação", accessorKey: "avaliacao", cell: (_v, f) =>
                f.avaliacao ? <span className="flex items-center gap-0.5 text-yellow-500 tabular-nums"><Star className="size-3 fill-current" />{f.avaliacao}</span> : "—"
        },
        {
            id: "actions",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            cell: (_v, row) => (
                <div className="flex items-center gap-0 justify-end">
                    <Button size="icon" variant="ghost" className="size-7" aria-label="Editar fornecedor" onClick={() => { setSelectedFornecedor(row); setShowDialog(true); }}>
                        <Edit className="size-3.5 text-primary hover:text-primary" />
                    </Button>
                </div>
            ),
        },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Fornecedores"
                description="Cadastro de fornecedores e parceiros comerciais."
                icon={<Users className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Operacional", href: "/operacional" }, { label: "Fornecedores" }]}
                actions={
                    <Button variant="outline" size="sm" onClick={() => setShowDialog(true)} aria-label="Adicionar novo fornecedor">
                        <Plus data-icon="inline-start" className="size-3.5" /> Novo fornecedor
                    </Button>
                }
            />

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <Card className="rounded-sm shadow-sm">
                    <CardContent className="p-5 flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                            <Users className="size-5 text-primary" />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Total</p>
                            <div className="text-2xl font-black tabular-nums tracking-tight mt-0.5">{isLoading ? <Skeleton className="h-7 w-8" /> : fornecedores.length}</div>
                        </div>
                    </CardContent>
                </Card>
                <Card className="rounded-sm shadow-sm">
                    <CardContent className="p-5 flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center shrink-0">
                            <Users className="size-5 text-emerald-600" />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Com Prazo</p>
                            <div className="text-2xl font-black tabular-nums tracking-tight mt-0.5">{isLoading ? <Skeleton className="h-7 w-8" /> : fornecedores.filter(f => f.prazo_entrega_dias).length}</div>
                        </div>
                    </CardContent>
                </Card>
                <Card className="rounded-sm shadow-sm">
                    <CardContent className="p-5 flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0">
                            <Star className="size-5 text-amber-600" />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Avaliados</p>
                            <div className="text-2xl font-black tabular-nums tracking-tight mt-0.5">{isLoading ? <Skeleton className="h-7 w-8" /> : fornecedores.filter(f => f.avaliacao).length}</div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {isLoading ? <Skeleton className="h-40 w-full rounded-sm" /> :
                hasStatus(error, 402)
                    ? <Card variant="warning" className="shadow-none"><CardContent className="pt-6 text-center"><p className="text-sm font-medium text-card-title mb-3">Módulo &quot;Compras&quot; não contratado</p><Button size="sm" variant="outline" onClick={() => window.location.href = '/dashboard/configuracoes'}>Contratar</Button></CardContent></Card>
                    : fornecedores.length === 0
                    ? <div className="text-center py-12 rounded-sm border-2 border-dashed bg-muted/20"><Users className="size-8 mx-auto mb-2 opacity-30 text-primary" /><p className="text-sm text-muted-foreground mb-4">Nenhum fornecedor cadastrado</p><Button size="sm" variant="outline" onClick={() => setShowDialog(true)}><Plus data-icon="inline-start" className="size-3.5" /> Cadastrar</Button></div>
                    : <DataTable columns={columns} data={fornecedores} searchable exportable />
            }

            <Dialog open={showDialog} onOpenChange={v => { if (!v) { setShowDialog(false); setSelectedFornecedor(null); } }}>
                <FornecedorForm fornecedor={selectedFornecedor} onClose={() => { setShowDialog(false); setSelectedFornecedor(null); }} onSubmit={mut.mutate} loading={mut.isPending} />
            </Dialog>
        </div>
    );
}

function FornecedorForm({
    fornecedor,
    onClose,
    onSubmit,
    loading,
}: {
    fornecedor?: Fornecedor | null;
    onClose: () => void;
    onSubmit: (d: FornecedorFormValues) => void;
    loading: boolean;
}) {
    const form = useForm<FornecedorFormValues>({
        defaultValues: {
            nome_fantasia: "",
            cnpj_cpf: "",
            email: "",
            telefone: "",
            condicoes_pagamento: "",
            prazo_entrega_dias: "",
            avaliacao: "",
        },
    });

    useEffect(() => {
        if (fornecedor) {
            form.reset({
                nome_fantasia: fornecedor.nome_fantasia,
                cnpj_cpf: fornecedor.cnpj_cpf || "",
                email: fornecedor.email || "",
                telefone: fornecedor.telefone || "",
                condicoes_pagamento: fornecedor.condicoes_pagamento || "",
                prazo_entrega_dias: fornecedor.prazo_entrega_dias != null ? String(fornecedor.prazo_entrega_dias) : "",
                avaliacao: fornecedor.avaliacao != null ? String(fornecedor.avaliacao) : "",
            });
        } else {
            form.reset({
                nome_fantasia: "",
                cnpj_cpf: "",
                email: "",
                telefone: "",
                condicoes_pagamento: "",
                prazo_entrega_dias: "",
                avaliacao: "",
            });
        }
    }, [fornecedor, form]);

    return (
        <DialogContent className="sm:max-w-[640px] rounded-sm p-0">
            <DialogHeader className="border-b px-4 py-2.5">
                <div className="flex items-center gap-3">
                    <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                        <Users className="size-4" />
                    </div>
                    <div className="min-w-0">
                        <DialogTitle>{fornecedor ? "Editar Fornecedor" : "Novo Fornecedor"}</DialogTitle>
                        <DialogDescription className="truncate text-xs leading-tight">
                            Cadastre dados comerciais, prazo de entrega e avaliação do fornecedor.
                        </DialogDescription>
                    </div>
                </div>
            </DialogHeader>
            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
                    <DialogBody className="grid min-h-0 flex-1 gap-4 overflow-y-auto px-4 py-3">
                        <FormField
                            control={form.control}
                            name="nome_fantasia"
                            rules={{ required: "Nome é obrigatório" }}
                            render={({ field }) => (
                                <FormItem className="space-y-1.5">
                                    <FormLabel className="text-xs font-medium">Nome / Razão Social *</FormLabel>
                                    <FormControl>
                                        <Input {...field} className="h-8 text-xs rounded-sm" placeholder="Ex: Agroquímica Brasil LTDA" />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            <FormField
                                control={form.control}
                                name="cnpj_cpf"
                                render={({ field }) => (
                                    <FormItem className="space-y-1.5">
                                        <FormLabel className="text-xs font-medium">CNPJ / CPF</FormLabel>
                                        <FormControl>
                                            <Input
                                                {...field}
                                                className="h-8 text-xs rounded-sm"
                                                placeholder="000.000.000-00"
                                                inputMode="numeric"
                                                value={field.value ?? ""}
                                                onChange={e => field.onChange(formatCnpjCpf(e.target.value))}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="email"
                                render={({ field }) => (
                                    <FormItem className="space-y-1.5">
                                        <FormLabel className="text-xs font-medium">E-mail</FormLabel>
                                        <FormControl>
                                            <Input {...field} className="h-8 text-xs rounded-sm" type="email" placeholder="compras@fornecedor.com" />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            <FormField
                                control={form.control}
                                name="telefone"
                                render={({ field }) => (
                                    <FormItem className="space-y-1.5">
                                        <FormLabel className="text-xs font-medium">Telefone</FormLabel>
                                        <FormControl>
                                            <Input {...field} className="h-8 text-xs rounded-sm" placeholder="(00) 00000-0000" />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="prazo_entrega_dias"
                                render={({ field }) => (
                                    <FormItem className="space-y-1.5">
                                        <FormLabel className="text-xs font-medium">Prazo de Entrega (dias)</FormLabel>
                                        <FormControl>
                                            <Input {...field} className="h-8 text-xs rounded-sm" type="number" min="0" placeholder="Ex: 7" />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            <FormField
                                control={form.control}
                                name="condicoes_pagamento"
                                render={({ field }) => (
                                    <FormItem className="space-y-1.5">
                                        <FormLabel className="text-xs font-medium">Condições de Pagamento</FormLabel>
                                        <FormControl>
                                            <Input {...field} className="h-8 text-xs rounded-sm" placeholder="Ex: 30 dias" />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="avaliacao"
                                render={({ field }) => (
                                    <FormItem className="space-y-1.5">
                                        <FormLabel className="text-xs font-medium">Avaliação</FormLabel>
                                        <FormControl>
                                            <Input {...field} className="h-8 text-xs rounded-sm" type="number" min="0" max="5" step="0.5" placeholder="0 a 5" />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>
                    </DialogBody>

                    <DialogFooter className="border-t px-4 py-2.5">
                        <Button type="button" variant="outline" size="sm" onClick={() => { onClose(); form.reset(); }}>
                            <XCircle data-icon="inline-start" className="size-3.5" />
                            Cancelar
                        </Button>
                        <Button type="submit" size="sm" disabled={loading}>
                            {loading ? (
                                <Loader2 data-icon="inline-start" className="size-3.5 animate-spin" />
                            ) : (
                                <Save data-icon="inline-start" className="size-3.5" />
                            )}
                            {loading ? "Salvando..." : fornecedor ? "Atualizar" : "Salvar"}
                        </Button>
                    </DialogFooter>
                </form>
            </Form>
        </DialogContent>
    );
}
