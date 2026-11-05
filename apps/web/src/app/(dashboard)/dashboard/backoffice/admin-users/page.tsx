"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    ShieldCheck, ShieldAlert, UserPlus, Mail,
    KeyRound, Pencil, Users, Clock, MoreHorizontal,
} from "lucide-react";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
    Dialog, DialogContent, DialogDescription,
    DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem,
    SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    DropdownMenu, DropdownMenuContent,
    DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { PermissionGuard } from "@/components/auth/permission-guard";
import { BACKOFFICE_ROLE_LABELS } from "@/lib/permissions";
import type { Admin, AdminStats, BackofficeRole } from "@/types/global";
import { PageHeader } from "@/components/shared/page-header";

import {
    createAdminSchema, updateAdminSchema, resetPasswordSchema,
    type CreateAdminInput, type UpdateAdminInput, type ResetPasswordInput,
    backofficeRoleValues,
} from "@farm/zod-schemas";

/* ─── Página Principal ─── */

export default function AdminUsersPage() {
    const queryClient = useQueryClient();
    const [roleFilter, setRoleFilter] = useState<string>("all");
    const [createOpen, setCreateOpen] = useState(false);
    const [editTarget, setEditTarget] = useState<Admin | null>(null);
    const [resetTarget, setResetTarget] = useState<Admin | null>(null);

    const { data: stats, isLoading: loadingStats } = useQuery<AdminStats>({
        queryKey: ["backoffice", "admins", "stats"],
        queryFn: () => apiFetch("/backoffice/admins/stats"),
    });

    const { data: admins, isLoading: loadingAdmins } = useQuery<Admin[]>({
        queryKey: ["backoffice", "admins"],
        queryFn: () => apiFetch("/backoffice/admins"),
    });

    const filteredAdmins = admins?.filter((admin) => {
        const matchRole = roleFilter === "all" || admin.role === roleFilter;
        return matchRole;
    });

    const columns: ColumnDef<Admin>[] = [
        {
            id: "identidade",
            header: "Identidade",
            accessorKey: "nome",
            cell: (value, admin) => (
                <div className="flex items-center gap-3">
                    <Avatar className="h-9 w-9 border-2 border-background shadow-sm">
                        <AvatarFallback className="bg-primary/5 text-primary text-xs font-bold">
                            {admin.nome.charAt(0).toUpperCase()}
                        </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col">
                        <span className="font-bold text-foreground leading-none">{admin.nome}</span>
                        <span className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1">
                            <Mail size={10} /> {admin.email}
                        </span>
                    </div>
                </div>
            ),
            filterPlaceholder: "Filtrar por nome...",
            exportFormat: (value, admin) => `${admin.nome} (${admin.email})`
        },
        {
            id: "role",
            header: "Role",
            accessorKey: "role",
            cell: (value, admin) => <RoleBadge role={admin.role} />,
            filterPlaceholder: "Filtrar por função...",
            exportFormat: (value, admin) => BACKOFFICE_ROLE_LABELS[admin.role]
        },
        {
            id: "status",
            header: "Status",
            accessorFn: (admin) => admin.ativo ? "ativo" : "inativo",
            cell: (value, admin) => <StatusBadge status={admin.ativo ? "ativo" : "inativo"} />,
            filterPlaceholder: "Filtrar por status...",
            exportFormat: (value, admin) => admin.ativo ? "Ativo" : "Inativo"
        },
        {
            id: "ultimo_acesso",
            header: "Último Acesso",
            accessorKey: "ultimo_acesso",
            cell: (value, admin) => (
                <span className="text-xs text-muted-foreground">
                    {admin.ultimo_acesso
                        ? format(new Date(admin.ultimo_acesso), "dd/MM/yy HH:mm", { locale: ptBR })
                        : "Nunca"}
                </span>
            ),
            filterPlaceholder: "Filtrar por data...",
            exportFormat: (value, admin) => admin.ultimo_acesso
                ? format(new Date(admin.ultimo_acesso), "dd/MM/yyyy HH:mm", { locale: ptBR })
                : "Nunca"
        },
        {
            id: "cadastro",
            header: "Cadastro",
            accessorKey: "created_at",
            cell: (value, admin) => (
                <span className="text-xs text-muted-foreground">
                    {format(new Date(admin.created_at), "dd/MM/yy", { locale: ptBR })}
                </span>
            ),
            filterPlaceholder: "Filtrar por data...",
            exportFormat: (value, admin) => format(new Date(admin.created_at), "dd/MM/yyyy", { locale: ptBR })
        },
        {
            id: "acoes",
            header: "",
            accessorKey: "id",
            sortable: false,
            filterable: false,
            exportable: false,
            cell: (value, admin) => (
                <div className="flex items-center gap-1 justify-end">
                    <PermissionGuard permission="backoffice:admin_users:update">
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="size-7">
                                    <MoreHorizontal className="size-3.5" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => setEditTarget(admin)}>
                                    <Pencil size={14} className="mr-2" />
                                    Editar
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => setResetTarget(admin)}>
                                    <KeyRound size={14} className="mr-2" />
                                    Resetar Senha
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </PermissionGuard>
                </div>
            )
        }
    ];

    if (loadingStats || loadingAdmins) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-10 w-64" />
                <div className="grid gap-4 md:grid-cols-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-24 rounded-sm" />
                    ))}
                </div>
                <Skeleton className="h-96 w-full rounded-sm" />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <PageHeader
                title="Gestão de Admins"
                description="Gerencie administradores da plataforma SaaS."
                icon={<ShieldCheck className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Administradores" },
                ]}
                actions={
                    <PermissionGuard permission="backoffice:admin_users:create">
                        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                            <DialogTrigger asChild>
                                <Button variant="outline" size="sm" className="gap-2 rounded-sm">
                                    <UserPlus size={14} />
                                    Novo Admin
                                </Button>
                            </DialogTrigger>
                            <DialogContent>
                                <DialogHeader>
                                    <DialogTitle>Criar Administrador</DialogTitle>
                                    <DialogDescription>
                                        Preencha os dados para adicionar um novo admin à plataforma.
                                    </DialogDescription>
                                </DialogHeader>
                                <CreateAdminForm
                                    onSuccess={() => {
                                        setCreateOpen(false);
                                        queryClient.invalidateQueries({ queryKey: ["backoffice", "admins"] });
                                        queryClient.invalidateQueries({ queryKey: ["backoffice", "admins", "stats"] });
                                    }}
                                />
                            </DialogContent>
                        </Dialog>
                    </PermissionGuard>
                }
            />

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard icon={Users} label="Total" value={stats?.total ?? 0} color="primary" />
                <StatCard icon={ShieldCheck} label="Ativos" value={stats?.ativos ?? 0} color="primary" />
                <StatCard icon={ShieldAlert} label="Super Admins" value={stats?.super_admins ?? 0} color="primary" />
                <StatCard icon={Clock} label="Último Acesso" value="Hoje" color="primary" isText />
            </div>

            {/* Filtros Customizados */}
            <div className="flex flex-col sm:flex-row gap-3">
                <Select value={roleFilter} onValueChange={setRoleFilter}>
                    <SelectTrigger className="w-full sm:w-48">
                        <SelectValue placeholder="Filtrar por função" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Todas as funções</SelectItem>
                        {backofficeRoleValues.map((role) => (
                            <SelectItem key={role} value={role}>
                                {BACKOFFICE_ROLE_LABELS[role]}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            {/* DataTable */}
            <DataTable
                data={filteredAdmins || []}
                columns={columns}
                searchable={true}
                searchPlaceholder="Buscar por nome ou e-mail..."
                exportable={true}
                exportFileName="admins-backoffice"
                emptyMessage="Nenhum admin encontrado."
                rowClassName={(admin) => "group transition-colors hover:bg-muted/10"}
            />

            {/* Dialog de Edição */}
            <Dialog open={!!editTarget} onOpenChange={(open) => !open && setEditTarget(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Editar Admin</DialogTitle>
                        <DialogDescription>
                            Atualize os dados de {editTarget?.nome}.
                        </DialogDescription>
                    </DialogHeader>
                    {editTarget && (
                        <EditAdminForm
                            admin={editTarget}
                            onSuccess={() => {
                                setEditTarget(null);
                                queryClient.invalidateQueries({ queryKey: ["backoffice", "admins"] });
                                queryClient.invalidateQueries({ queryKey: ["backoffice", "admins", "stats"] });
                            }}
                        />
                    )}
                </DialogContent>
            </Dialog>

            {/* Dialog de Reset de Senha */}
            <Dialog open={!!resetTarget} onOpenChange={(open) => !open && setResetTarget(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Resetar Senha</DialogTitle>
                        <DialogDescription>
                            Defina uma nova senha para {resetTarget?.nome}.
                        </DialogDescription>
                    </DialogHeader>
                    {resetTarget && (
                        <ResetPasswordForm
                            admin={resetTarget}
                            onSuccess={() => {
                                setResetTarget(null);
                            }}
                        />
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}

/* ─── Componentes Internos ─── */

interface StatCardProps {
    icon: React.ComponentType<{ size: number }>;
    label: string;
    value: number | string;
    color: "primary" | "primary" | "primary" | "primary";
    isText?: boolean;
}

const COLOR_MAP = {
    primary: "bg-primary/10 text-primary",
    green: "bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-100",
    purple: "bg-violet-500/10 text-violet-700 dark:bg-violet-500/20 dark:text-violet-100",
    blue: "bg-blue-500/10 text-blue-700 dark:bg-blue-500/20 dark:text-blue-100",
};

const BORDER_MAP: Record<string, string> = {
    primary: "border-l-primary",
    green: "border-l-emerald-500",
    purple: "border-l-violet-500",
    blue: "border-l-blue-500",
};

function StatCard({ icon: Icon, label, value, color, isText }: StatCardProps) {
    return (
        <Card className={`border-l-[3px] ${BORDER_MAP[color]}`}>
            <CardContent className="pt-6 flex items-center gap-4">
                <div className={`h-12 w-12 rounded-sm flex items-center justify-center shrink-0 ${COLOR_MAP[color]}`}>
                    <Icon size={24} />
                </div>
                <div>
                    <p className={`font-black ${isText ? "text-lg" : "text-2xl"}`}>{value}</p>
                    <p className="text-[10px] uppercase font-bold text-muted-foreground">{label}</p>
                </div>
            </CardContent>
        </Card>
    );
}

function RoleBadge({ role }: { role: BackofficeRole }) {
    const styles: Record<BackofficeRole, string> = {
        super_admin: "bg-violet-500/10 text-violet-700 border-violet-200 dark:bg-violet-500/20 dark:text-violet-100 dark:border-violet-400/30",
        admin: "bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30",
        suporte: "bg-amber-500/10 text-amber-700 border-amber-200 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30",
        financeiro: "bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30",
        comercial: "bg-cyan-500/10 text-cyan-700 border-cyan-200 dark:bg-cyan-500/20 dark:text-cyan-100 dark:border-cyan-400/30",
    };

    return (
        <Badge className={`text-[10px] uppercase font-black ${styles[role]}`}>
            {BACKOFFICE_ROLE_LABELS[role]}
        </Badge>
    );
}

/* ─── Form: Criar Admin ─── */

function CreateAdminForm({ onSuccess }: { onSuccess: () => void }) {
    const {
        register, handleSubmit, setValue,
        formState: { errors, isSubmitting },
    } = useForm<CreateAdminInput>({
        resolver: zodResolver(createAdminSchema),
    });

    const createMutation = useMutation({
        mutationFn: (data: CreateAdminInput) =>
            apiFetch("/backoffice/admins", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Admin criado com sucesso!");
            onSuccess();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    return (
        <form onSubmit={handleSubmit((data) => createMutation.mutate(data))} className="space-y-4">
            <div className="space-y-1.5">
                <Label htmlFor="admin-nome">Nome</Label>
                <Input id="admin-nome" {...register("nome")} placeholder="Nome completo" />
                {errors.nome && <p className="text-xs text-red-500">{errors.nome.message}</p>}
            </div>

            <div className="space-y-1.5">
                <Label htmlFor="admin-email">E-mail</Label>
                <Input id="admin-email" {...register("email")} type="email" placeholder="admin@empresa.com" />
                {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
            </div>

            <div className="space-y-1.5">
                <Label htmlFor="admin-password">Senha</Label>
                <Input id="admin-password" {...register("password")} type="password" placeholder="••••••••" />
                {errors.password && <p className="text-xs text-red-500">{errors.password.message}</p>}
            </div>

            <div className="space-y-1.5">
                <Label>Role</Label>
                <Select onValueChange={(val) => setValue("role", val as BackofficeRole)}>
                    <SelectTrigger>
                        <SelectValue placeholder="Selecione uma role" />
                    </SelectTrigger>
                    <SelectContent>
                        {backofficeRoleValues.map((role) => (
                            <SelectItem key={role} value={role}>
                                {BACKOFFICE_ROLE_LABELS[role]}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                {errors.role && <p className="text-xs text-red-500">{errors.role.message}</p>}
            </div>

            <Button
                type="submit"
                variant="ghost"
                size="sm"
                disabled={isSubmitting || createMutation.isPending}
                className="w-full mt-2"
            >
                {createMutation.isPending ? "Criando..." : "Criar Admin"}
            </Button>
        </form>
    );
}

/* ─── Form: Editar Admin ─── */

function EditAdminForm({ admin, onSuccess }: { admin: Admin; onSuccess: () => void }) {
    const {
        register, handleSubmit, setValue,
        formState: { errors, isSubmitting },
    } = useForm<UpdateAdminInput>({
        resolver: zodResolver(updateAdminSchema),
        defaultValues: {
            nome: admin.nome,
            role: admin.role,
            ativo: admin.ativo,
        },
    });

    const updateMutation = useMutation({
        mutationFn: (data: UpdateAdminInput) =>
            apiFetch(`/backoffice/admins/${admin.id}`, {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Admin atualizado com sucesso!");
            onSuccess();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    return (
        <form onSubmit={handleSubmit((data) => updateMutation.mutate(data))} className="space-y-4">
            <div className="space-y-1.5">
                <Label htmlFor="edit-nome">Nome</Label>
                <Input id="edit-nome" {...register("nome")} />
                {errors.nome && <p className="text-xs text-red-500">{errors.nome.message}</p>}
            </div>

            <div className="space-y-1.5">
                <Label>Role</Label>
                <Select
                    defaultValue={admin.role}
                    onValueChange={(val) => setValue("role", val as BackofficeRole)}
                >
                    <SelectTrigger>
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {backofficeRoleValues.map((role) => (
                            <SelectItem key={role} value={role}>
                                {BACKOFFICE_ROLE_LABELS[role]}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                {errors.role && <p className="text-xs text-red-500">{errors.role.message}</p>}
            </div>

            <div className="flex items-center gap-2">
                <Checkbox
                    id="edit-ativo"
                    defaultChecked={admin.ativo}
                    onCheckedChange={(checked) => setValue("ativo", !!checked)}
                />
                <Label htmlFor="edit-ativo">Ativo</Label>
            </div>

            <Button
                type="submit"
                variant="ghost"
                size="sm"
                disabled={isSubmitting || updateMutation.isPending}
                className="w-full mt-2"
            >
                {updateMutation.isPending ? "Salvando..." : "Salvar Alterações"}
            </Button>
        </form>
    );
}

/* ─── Form: Reset de Senha ─── */

function ResetPasswordForm({ admin, onSuccess }: { admin: Admin; onSuccess: () => void }) {
    const {
        register, handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<ResetPasswordInput>({
        resolver: zodResolver(resetPasswordSchema),
    });

    const resetMutation = useMutation({
        mutationFn: (data: ResetPasswordInput) =>
            apiFetch(`/backoffice/admins/${admin.id}/reset-password`, {
                method: "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Senha resetada com sucesso!");
            onSuccess();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    return (
        <form onSubmit={handleSubmit((data) => resetMutation.mutate(data))} className="space-y-4">
            <div className="space-y-1.5">
                <Label htmlFor="nova-senha">Nova Senha</Label>
                <Input id="nova-senha" {...register("nova_senha")} type="password" placeholder="••••••••" />
                {errors.nova_senha && <p className="text-xs text-red-500">{errors.nova_senha.message}</p>}
            </div>

            <Button
                type="submit"
                variant="ghost"
                size="sm"
                disabled={isSubmitting || resetMutation.isPending}
                className="w-full mt-2"
            >
                {resetMutation.isPending ? "Resetando..." : "Resetar Senha"}
            </Button>
        </form>
    );
}
