"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Users, ShieldCheck,
    UserX, UserCheck, Search, Mail,
    Calendar, Shield, Lock, Unlock, KeyRound, AlertTriangle
} from "lucide-react";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { useState } from "react";
import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { resolveAssetUrl } from "@/lib/runtime-config";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
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
import {
    useDesbloquearUsuario,
    useLoginTentativas,
    useResetUserPassword,
    type LoginTentativasInfo,
} from "@/hooks/use-login-attempts";

interface GlobalUser {
    id: string;
    nome: string | null;
    email: string;
    username: string;
    foto_perfil_url?: string | null;
    is_superuser: boolean;
    is_owner: boolean;
    ativo: boolean;
    data_cadastro: string;
    tenants: string[];
}

/* ─── Badge de bloqueio por tentativas (inline) ─── */

function LoginLockBadge({ email }: { email: string }) {
    const { data: tentativas } = useLoginTentativas(email);
    const desbloquear = useDesbloquearUsuario();

    if (!tentativas || !tentativas.bloqueado) return null;

    return (
        <Tooltip>
            <TooltipTrigger asChild>
                <span className="inline-flex items-center gap-1 ml-1.5 cursor-pointer"
                    onClick={(e) => {
                        e.stopPropagation();
                        desbloquear.mutate(email);
                    }}
                >
                    <Lock size={11} className="text-amber-500" />
                </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="text-xs">
                <div className="space-y-1">
                    <p className="font-semibold text-amber-500">Bloqueado por tentativas</p>
                    <p className="text-muted-foreground">{tentativas.tentativas_count} tentativas · Motivo: {tentativas.motivo_falha || "—"}</p>
                    <p className="text-muted-foreground">Desbloqueio: {tentativas.data_desbloqueio ? format(new Date(tentativas.data_desbloqueio), "HH:mm") : "—"}</p>
                    <p className="text-primary font-medium">Clique para desbloquear</p>
                </div>
            </TooltipContent>
        </Tooltip>
    );
}

export default function UsersBackofficePage() {
    const queryClient = useQueryClient();
    const [resetUserId, setResetUserId] = useState<string | null>(null);
    const resetPassword = useResetUserPassword();

    const { data: users, isLoading } = useQuery<GlobalUser[]>({
        queryKey: ["backoffice", "users"],
        queryFn: () => apiFetch("/backoffice/users")
    });

    const toggleStatusMutation = useMutation({
        mutationFn: (userId: string) =>
            apiFetch(`/backoffice/users/${userId}/toggle-status`, { method: "POST" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "users"] });
            toast.success("Status do usuário atualizado!");
        },
        onError: (err: any) => toast.error(err.message || "Erro ao atualizar status.")
    });

    const selectedUser = users?.find(u => u.id === resetUserId);

    const columns: ColumnDef<GlobalUser>[] = [
        {
            id: "identidade",
            header: "Identidade",
            accessorKey: "nome",
            cell: (value, user) => (
                <div className="flex items-center gap-3">
                    <Avatar className="h-9 w-9 border-2 border-background shadow-sm">
                        <AvatarImage
                            src={resolveAssetUrl(user.foto_perfil_url)}
                            alt={user.nome || user.username}
                            onError={(e) => {
                                (e.target as HTMLImageElement).style.display = "none";
                            }}
                        />
                        <AvatarFallback className="bg-primary/5 text-primary text-xs font-bold">
                            {user.nome?.charAt(0) || user.username.charAt(0).toUpperCase()}
                        </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col">
                        <span className="font-bold text-foreground leading-none flex items-center gap-1">
                            {user.nome || user.username}
                            <LoginLockBadge email={user.email} />
                        </span>
                        <span className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1">
                            <Mail size={10} /> {user.email}
                        </span>
                    </div>
                </div>
            ),
            filterPlaceholder: "Filtrar por nome...",
            exportFormat: (value, user) => user.nome || user.username
        },
        {
            id: "vinculos",
            header: "Vínculos (Tenants)",
            accessorFn: (user) => user.tenants.join(", "),
            cell: (value, user) => (
                <div className="flex flex-wrap gap-1">
                    {user.tenants.length > 0 ? (
                        user.tenants.map(t => (
                            <Badge key={t} variant="secondary" className="bg-blue-500/10 text-blue-700 text-[9px] border border-blue-200 px-1.5 py-0 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30">
                                {t}
                            </Badge>
                        ))
                    ) : (
                        <span className="text-[10px] text-muted-foreground italic">Sem vínculos</span>
                    )}
                </div>
            ),
            filterPlaceholder: "Filtrar por tenant...",
            exportFormat: (value, user) => user.tenants.join(", ")
        },
        {
            id: "cadastro",
            header: "Cadastro",
            accessorKey: "data_cadastro",
            cell: (value, user) => (
                <div className="flex items-center gap-1.5 text-muted-foreground text-xs font-medium">
                    <Calendar size={12} />
                    {format(new Date(user.data_cadastro), "dd/MM/yy", { locale: ptBR })}
                </div>
            ),
            filterPlaceholder: "Filtrar por data...",
            exportFormat: (value) => format(new Date(value), "dd/MM/yyyy", { locale: ptBR })
        },
        {
            id: "tipo",
            header: "Tipo",
            accessorFn: (user) => user.is_superuser ? "Admin SaaS" : "Usuário",
            cell: (value, user) => (
                user.is_superuser ? (
                    <Badge className="bg-violet-500/10 text-violet-700 border-violet-200 text-[10px] font-black uppercase dark:bg-violet-500/20 dark:text-violet-100 dark:border-violet-400/30">Admin SaaS</Badge>
                ) : (
                    <Badge variant="ghost" className="text-[10px] uppercase font-bold text-muted-foreground">Usuário</Badge>
                )
            ),
            filterPlaceholder: "Filtrar por tipo...",
            exportFormat: (value, user) => user.is_superuser ? "Admin SaaS" : "Usuário"
        },
        {
            id: "status",
            header: "Status",
            accessorFn: (user) => user.ativo ? "Ativo" : "Bloqueado",
            cell: (value, user) => (
                <Badge
                    variant={user.ativo ? "outline" : "destructive"}
                    className={`text-[10px] uppercase font-black px-2 py-0 ${user.ativo ? 'border-emerald-200 text-emerald-700 bg-emerald-50 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30' : ''}`}
                >
                    {user.ativo ? "Ativo" : "Bloqueado"}
                </Badge>
            ),
            filterPlaceholder: "Filtrar por status...",
            exportFormat: (value, user) => user.ativo ? "Ativo" : "Bloqueado"
        },
        {
            id: "acao",
            header: "Ação",
            accessorKey: "id",
            sortable: false,
            filterable: false,
            exportable: false,
            cell: (value, user) => (
                <div className="text-right flex items-center justify-end gap-1">
                    {/* Desbloquear por tentativas */}
                    <DesbloquearTentativasButton email={user.email} />

                    {/* Reset de senha */}
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <span className="inline-block">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className={`h-8 w-8 p-0 ${
                                        user.is_superuser
                                            ? 'text-muted-foreground opacity-40 cursor-not-allowed'
                                            : 'text-amber-600 hover:text-amber-700 hover:bg-amber-50'
                                    }`}
                                    disabled={user.is_superuser || resetPassword.isPending}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setResetUserId(user.id);
                                    }}
                                >
                                    <KeyRound size={16} />
                                </Button>
                            </span>
                        </TooltipTrigger>
                        <TooltipContent side="left">
                            {user.is_superuser
                                ? "Não disponível para Admin SaaS"
                                : "Resetar senha"}
                        </TooltipContent>
                    </Tooltip>

                    {/* Bloquear/Ativar administrativo */}
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <span className="inline-block">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className={`h-8 w-8 p-0 ${
                                        user.is_superuser
                                            ? 'text-muted-foreground opacity-40 cursor-not-allowed'
                                            : user.ativo
                                                ? 'text-red-500 hover:text-red-600 hover:bg-red-50'
                                                : 'text-green-600 hover:text-green-700 hover:bg-green-50'
                                    }`}
                                    disabled={user.is_superuser || toggleStatusMutation.isPending}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        toggleStatusMutation.mutate(user.id);
                                    }}
                                >
                                    {user.ativo ? <UserX size={16} /> : <UserCheck size={16} />}
                                </Button>
                            </span>
                        </TooltipTrigger>
                        <TooltipContent side="left">
                            {user.is_superuser
                                ? "Não é possível bloquear Admin SaaS"
                                : user.ativo ? "Bloquear" : "Ativar"}
                        </TooltipContent>
                    </Tooltip>
                </div>
            )
        }
    ];

    if (isLoading) {
        return (
            <div className="p-8 space-y-6">
                <Skeleton className="h-10 w-48" />
                <Skeleton className="h-96 w-full rounded-sm" />
            </div>
        );
    }

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Usuários Globais"
                description="Gerencie identidades e acessos em toda a plataforma."
                icon={<Users className="text-primary" size={22} />}
            />

            <div className="grid gap-4 md:grid-cols-3">
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                            <Users size={24} />
                        </div>
                        <div>
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Total no sistema</p>
                            <p className="text-2xl font-black">{users?.length || 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-100">
                            <ShieldCheck size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Ativos</p>
                            <p className="text-2xl font-black">{users?.filter(u => u.ativo).length || 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-700 dark:bg-blue-500/20 dark:text-blue-100">
                            <Shield size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Admins SaaS</p>
                            <p className="text-2xl font-black">{users?.filter(u => u.is_superuser).length || 0}</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <DataTable
                data={users || []}
                columns={columns}
                searchable={true}
                searchPlaceholder="Buscar por nome, e-mail, username..."
                exportable={true}
                exportFileName="usuarios-globais"
                emptyMessage="Nenhum usuário encontrado."
                rowClassName={(user) => "group transition-colors hover:bg-muted/10"}
            />

            {/* ─── Dialog de confirmação de reset de senha ─── */}
            <AlertDialog open={!!resetUserId} onOpenChange={(open) => !open && setResetUserId(null)}>
                <AlertDialogContent className="w-[calc(100vw-1rem)] sm:max-w-md">
                    <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2">
                            <KeyRound className="size-4" />
                            Resetar senha do usuário?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            {selectedUser && (
                                <>
                                    A senha de <strong>{selectedUser.nome || selectedUser.email}</strong> será
                                    substituída por uma senha temporária gerada automaticamente e enviada por e-mail.
                                </>
                            )}
                        </AlertDialogDescription>
                    </AlertDialogHeader>

                    {selectedUser?.is_owner && (
                        <div className="rounded-md bg-amber-500/10 border border-amber-500/20 p-3 flex gap-2">
                            <AlertTriangle className="size-4 text-amber-500 flex-shrink-0 mt-0.5" />
                            <p className="text-xs text-amber-600 dark:text-amber-400">
                                Este usuário é proprietário de um tenant. O reset de senha pode afetar o acesso dele à plataforma.
                            </p>
                        </div>
                    )}

                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={resetPassword.isPending}>Cancelar</AlertDialogCancel>
                        <AlertDialogAction asChild>
                            <Button
                                onClick={() => {
                                    if (resetUserId) {
                                        resetPassword.mutate({ userId: resetUserId, enviarEmail: true });
                                        setResetUserId(null);
                                    }
                                }}
                                disabled={resetPassword.isPending}
                                className="bg-amber-600 text-white hover:bg-amber-700"
                            >
                                {resetPassword.isPending ? "Resetando..." : "Resetar e enviar por e-mail"}
                            </Button>
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}

/* ─── Botão de desbloquear por tentativas ─── */

function DesbloquearTentativasButton({ email }: { email: string }) {
    const { data: tentativas, isLoading } = useLoginTentativas(email);
    const desbloquear = useDesbloquearUsuario();

    if (isLoading || !tentativas || !tentativas.bloqueado) return null;

    return (
        <Tooltip>
            <TooltipTrigger asChild>
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-amber-500 hover:text-amber-600 hover:bg-amber-50"
                    disabled={desbloquear.isPending}
                    onClick={(e) => {
                        e.stopPropagation();
                        desbloquear.mutate(email);
                    }}
                >
                    <Unlock size={16} />
                </Button>
            </TooltipTrigger>
            <TooltipContent side="left">
                Desbloquear login ({tentativas.tentativas_count} tentativas)
            </TooltipContent>
        </Tooltip>
    );
}
