"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { format, formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    UserPlus, Mail, Users, UserCheck,
    Crown, Clock, Trash2, Pencil, Send, X,
    Lock, Unlock, Search
} from "lucide-react";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { StatCard } from "@/components/shared/stat-card";
import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { resolveAssetUrl } from "@/lib/runtime-config";
import {
    Dialog, DialogContent, DialogDescription,
    DialogHeader, DialogTitle, DialogTrigger, DialogBody, DialogFooter,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem,
    SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel,
    AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
    AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { PermissionGuard } from "@/components/auth/permission-guard";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import {
    useTenantLoginTentativas,
    useDesbloquearTenantUsuario,
} from "@/hooks/use-login-attempts";
import { VigenciaBadge, AcessoDrawer } from "@/components/shared";
import { useAppStore } from "@/lib/stores/app-store";
import type {
    TeamMember, TeamStats, TeamInvite,
    TenantRoleProfile, FazendaAccess, UnidadeProdutiva,
} from "@/types/global";
import {
    teamInviteSchema,
    type TeamInviteInput,
} from "@farm/zod-schemas";

type Fazenda = UnidadeProdutiva;

/* ─── Definição de Colunas ─── */

const createColumns = (
    onEdit: (member: TeamMember) => void,
    onRemove: (memberId: string) => void,
    onResend: (inviteId: string) => void,
    onCancel: (inviteId: string) => void,
    onManageAccess: (member: TeamMember) => void,
): ColumnDef<any>[] => [
        {
            id: "membro",
            header: "Membro",
            accessorFn: (row: any) => {
                if (!row) return "";
                return row.nome || row.email_convidado || row.email || "";
            },
            cell: (value, row) => {
                const item = row as any;
                if (!item) return null;
                const isInvite = !!item.email_convidado;
                const displayName = isInvite ? item.email_convidado : (item.nome || item.email || "Usuário");
                const initial = displayName ? displayName.charAt(0).toUpperCase() : "?";
                
                return (
                    <div className="flex items-center gap-3">
                        <Avatar className={`h-9 w-9 border-2 border-background shadow-sm ${isInvite ? "opacity-60" : ""}`}>
                            {item.foto_perfil_url ? (
                                <AvatarImage src={resolveAssetUrl(item.foto_perfil_url)} alt={displayName} />
                            ) : null}
                            <AvatarFallback className={`${isInvite ? "bg-amber-500/5 text-amber-500" : "bg-primary/5 text-primary"} text-xs font-bold`}>
                                {initial}
                            </AvatarFallback>
                        </Avatar>
                        <div className="flex flex-col">
                            <span className="font-bold text-foreground leading-none flex items-center gap-1.5">
                                {isInvite ? (
                                    <>
                                        <span className="text-muted-foreground">{item.email_convidado}</span>
                                        <Badge variant="outline" className="text-[9px] h-4 px-1 bg-amber-500/5 border-amber-500/20 text-amber-600 font-black uppercase tracking-tighter">
                                            Convite
                                        </Badge>
                                    </>
                                ) : (
                                    <>
                                        {item.nome || "—"}
                                        {item.is_owner && (
                                            <Crown size={12} className="text-amber-500" />
                                        )}
                                        <LoginLockBadge usuarioId={item.usuario_id} />
                                    </>
                                )}
                            </span>
                            {!isInvite && (
                                <span className="text-[11px] text-muted-foreground mt-1">
                                    {item.email}
                                </span>
                            )}
                            {isInvite && (
                                <span className="text-[10px] text-amber-500/60 mt-1 font-medium flex items-center gap-1">
                                    <Clock size={10} />
                                    Enviado {item.created_at ? formatDistanceToNow(new Date(item.created_at), { locale: ptBR, addSuffix: true }) : "-"}
                                </span>
                            )}
                        </div>
                    </div>
                );
            },
        },
        {
            id: "perfil",
            header: "Perfil",
            accessorFn: (row: any) => row?.perfil?.nome || "Membro",
            cell: (value, row) => {
                const item = row as any;
                return (
                    <Badge
                        variant="ghost"
                        className={`text-[10px] uppercase font-bold ${item?.perfil?.is_custom
                                ? "border-cyan-200 text-cyan-600 bg-cyan-500/5"
                                : ""
                            }`}
                    >
                        {value}
                    </Badge>
                );
            },
        },
        {
            id: "fazendas",
            header: "Fazendas",
            accessorFn: (row: any) => (row?.fazendas || []).map((f: any) => f.nome).join(", "),
            cell: (value, row) => {
                const item = row as any;
                const fazendas = item?.fazendas || [];
                return (
                    <div className="flex flex-wrap gap-1">
                        {fazendas.slice(0, 3).map((f: any) => (
                            <div key={f.id} className="flex items-center gap-1">
                                <Badge variant="secondary" className="text-[9px] px-1.5 py-0">
                                    {f.nome}
                                </Badge>
                                <VigenciaBadge vigencia_inicio={f.vigencia_inicio} vigencia_fim={f.vigencia_fim} />
                            </div>
                        ))}
                        {fazendas.length > 3 && (
                            <Badge variant="secondary" className="text-[9px] px-1.5 py-0">
                                +{fazendas.length - 3}
                            </Badge>
                        )}
                        {fazendas.length === 0 && (
                            <span className="text-[10px] text-muted-foreground italic">Todas</span>
                        )}
                    </div>
                );
            },
        },
        {
            id: "status",
            header: "Status",
            accessorFn: (row: any) => {
                if (!row) return "";
                if (row.email_convidado) {
                    const isExpired = row.data_expiracao ? new Date(row.data_expiracao) < new Date() : false;
                    return isExpired ? "EXPIRADO" : "PENDENTE";
                }
                return row.status || "";
            },
            cell: (value, row) => {
                const item = row as any;
                if (!item) return null;
                const isInvite = !!item.email_convidado;
                
                if (isInvite) {
                    const isExpired = item.data_expiracao ? new Date(item.data_expiracao) < new Date() : false;
                    return (
                        <StatusBadge
                            status={isExpired ? "expirado" : "pendente"}
                        />
                    );
                }

                return (
                    <StatusBadge
                        status={item.status === "ATIVO" ? "ativo" : item.status === "PENDENTE" ? "pendente" : "inativo"}
                    />
                );
            },
        },
        {
            id: "data",
            header: "Data",
            accessorFn: (row: any) => row?.data_cadastro || row?.created_at || "",
            cell: (value) => {
                if (!value) return <span className="text-xs text-muted-foreground">—</span>;
                return (
                    <span className="text-xs text-muted-foreground">
                        {format(new Date(value), "dd/MM/yy", { locale: ptBR })}
                    </span>
                );
            },
        },
        {
            id: "acoes",
            header: "",
            sortable: false,
            filterable: false,
            exportable: false,
            cell: (value, row) => {
                const item = row as any;
                const isInvite = !!item.email_convidado;

                if (item.is_owner) return null;

                if (isInvite) {
                    return (
                        <div className="flex items-center justify-end gap-0 px-1">
                            <PermissionGuard permission="tenant:users:invite">
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Button
                                            variant="ghost"
                                            size="icon-sm"
                                            className="text-muted-foreground hover:text-emerald-500 hover:bg-emerald-500/10"
                                            onClick={() => onResend(item.id)}
                                        >
                                            <Send size={14} />
                                        </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>Reenviar Convite</TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Button
                                            variant="ghost"
                                            size="icon-sm"
                                            className="text-muted-foreground hover:text-red-500 hover:bg-red-500/10"
                                            onClick={() => onCancel(item.id)}
                                        >
                                            <X size={14} />
                                        </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>Cancelar Convite</TooltipContent>
                                </Tooltip>
                            </PermissionGuard>
                        </div>
                    );
                }

                return (
                    <div className="flex items-center justify-end gap-0 px-1">
                        <DesbloquearTentativasButton usuarioId={item.usuario_id} email={item.email} />
                        <PermissionGuard permission="tenant:users:update">
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="icon-sm"
                                        className="text-muted-foreground hover:text-blue-500 hover:bg-blue-500/10 transition-all duration-200"
                                        onClick={() => onManageAccess(item)}
                                    >
                                        <Unlock size={14} />
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>Gerenciar Acessos</TooltipContent>
                            </Tooltip>
                        </PermissionGuard>
                        <PermissionGuard permission="tenant:users:update">
                            <Button
                                variant="ghost"
                                size="icon-sm"
                                className="text-muted-foreground hover:text-emerald-500 hover:bg-emerald-500/10 transition-all duration-200"
                                onClick={() => onEdit(item)}
                            >
                                <Pencil size={14} />
                            </Button>
                        </PermissionGuard>
                        <PermissionGuard permission="tenant:users:delete">
                            <AlertDialog>
                                <AlertDialogTrigger render={<Button variant="ghost" size="icon-sm" className="text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-all duration-200" />}>
                                    <Trash2 size={14} />
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                    <AlertDialogHeader>
                                        <AlertDialogTitle className="font-bold">Remover membro?</AlertDialogTitle>
                                        <AlertDialogDescription>
                                            {item.nome} perderá acesso a todas as fazendas.
                                            Esta ação não pode ser desfeita.
                                        </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                        <AlertDialogCancel className="text-xs uppercase font-bold tracking-wider">Cancelar</AlertDialogCancel>
                                        <AlertDialogAction
                                            onClick={() => onRemove(item.id)}
                                            className="bg-red-500 hover:bg-red-600 text-white text-xs uppercase font-bold tracking-wider"
                                        >
                                            Remover
                                        </AlertDialogAction>
                                    </AlertDialogFooter>
                                </AlertDialogContent>
                            </AlertDialog>
                        </PermissionGuard>
                    </div>
                );
            },
        },
    ];

/* ─── Página Principal ─── */

export function TeamClient({
    initialStats,
    initialMembers,
    initialInvites,
    initialRoles,
    initialFazendas
}: {
    initialStats: TeamStats | null;
    initialMembers: TeamMember[];
    initialInvites: TeamInvite[];
    initialRoles: TenantRoleProfile[];
    initialFazendas: Fazenda[];
}) {
    const queryClient = useQueryClient();
    const [inviteOpen, setInviteOpen] = useState(false);
    const [editMember, setEditMember] = useState<TeamMember | null>(null);
    const [acessoMember, setAcessoMember] = useState<TeamMember | null>(null);
    const tenantId = useAppStore((s) => s.tenant?.id);

    const { data: stats, isLoading: loadingStats } = useQuery<TeamStats>({
        queryKey: ["team", "stats"],
        queryFn: () => apiFetch("/team/stats"),
        initialData: initialStats || undefined,
    });

    const { data: members, isLoading: loadingMembers, error: membersError } = useQuery<TeamMember[]>({
        queryKey: ["team", "users"],
        queryFn: () => apiFetch("/team/users"),
        initialData: initialMembers,
    });

    const { data: invites, isLoading: loadingInvites, error: invitesError } = useQuery<TeamInvite[]>({
        queryKey: ["team", "invites"],
        queryFn: () => apiFetch("/team/invites"),
        initialData: initialInvites,
    });

    const { data: roles } = useQuery<TenantRoleProfile[]>({
        queryKey: ["team", "roles"],
        queryFn: () => apiFetch("/team/roles"),
        initialData: initialRoles,
    });

    const { data: fazendas } = useQuery<Fazenda[]>({
        queryKey: ["fazendas"],
        queryFn: () => apiFetch("/unidades-produtivas"),
        enabled: !!tenantId,
        initialData: initialFazendas,
    });

    const removeMutation = useMutation({
        mutationFn: (memberId: string) =>
            apiFetch(`/team/users/${memberId}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Membro removido com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["team"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const cancelInviteMutation = useMutation({
        mutationFn: (inviteId: string) =>
            apiFetch(`/team/invites/${inviteId}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Convite cancelado!");
            queryClient.invalidateQueries({ queryKey: ["team", "invites"] });
            queryClient.invalidateQueries({ queryKey: ["team", "stats"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const resendInviteMutation = useMutation({
        mutationFn: (inviteId: string) =>
            apiFetch(`/team/invites/${inviteId}/resend`, { method: "POST" }),
        onSuccess: () => {
            toast.success("Convite reenviado! Nova validade: 7 dias.");
            queryClient.invalidateQueries({ queryKey: ["team", "invites"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const columns = createColumns(
        setEditMember,
        (memberId) => removeMutation.mutate(memberId),
        (inviteId) => resendInviteMutation.mutate(inviteId),
        (inviteId) => cancelInviteMutation.mutate(inviteId),
        setAcessoMember,
    );

    // Unificar membros e convites
    const combinedData = [
        ...(Array.isArray(members) ? members : []),
        ...(Array.isArray(invites) ? invites : [])
    ]
    .filter(Boolean) // Garantir que não existam itens null/undefined
    .sort((a: any, b: any) => {
        const dateA = new Date(a.data_cadastro || a.created_at || 0).getTime();
        const dateB = new Date(b.data_cadastro || b.created_at || 0).getTime();
        return dateB - dateA;
    });

    if (loadingStats || loadingMembers || loadingInvites) {
        return (
            <div className="p-8 space-y-6">
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
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Equipe"
                description="Gerencie os membros e convites da sua organização."
                actions={
                    <div className="flex items-center gap-2">
                        <PermissionGuard permission="tenant:permissions:view">
                            <Button variant="outline" size="sm" className="gap-2" asChild>
                                <a href="/dashboard/backoffice/profiles">
                                    <Lock size={14} />
                                    Perfis de Acesso
                                </a>
                            </Button>
                        </PermissionGuard>
                        <PermissionGuard permission="tenant:users:invite">
                            <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                                <DialogTrigger render={<Button variant="outline" size="sm" className="gap-2 bg-primary/5 border-primary/20 hover:bg-primary/10" />}>
                                    <UserPlus size={14} />
                                    Convidar Membro
                                </DialogTrigger>
                                <DialogContent className="sm:max-w-xl overflow-hidden p-0">
                                    <DialogHeader className="border-b px-6 py-5">
                                        <div className="flex items-start gap-3">
                                            <div className="flex h-9 w-9 items-center justify-center rounded-sm border bg-primary/5 text-primary">
                                                <Mail size={16} className="text-primary" />
                                            </div>
                                            <div className="flex flex-col gap-1">
                                                <DialogTitle>Convidar para Equipe</DialogTitle>
                                                <DialogDescription>
                                                    Envie um convite por e-mail para um novo membro e configure seus acessos.
                                                </DialogDescription>
                                            </div>
                                        </div>
                                    </DialogHeader>
                                    <InviteForm
                                        roles={roles ?? []}
                                        fazendas={fazendas ?? []}
                                        onCancel={() => setInviteOpen(false)}
                                        onSuccess={() => {
                                            setInviteOpen(false);
                                            queryClient.invalidateQueries({ queryKey: ["team"] });
                                        }}
                                    />
                                </DialogContent>
                            </Dialog>
                        </PermissionGuard>
                    </div>
                }
            />

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard icon={Users} label="Total Membros" value={stats?.total_membros ?? 0} color="primary" />
                <StatCard icon={UserCheck} label="Ativos" value={stats?.ativos ?? 0} color="agro" />
                <StatCard icon={Crown} label="Owners" value={stats?.owners ?? 0} color="financeiro" />
                <StatCard icon={Clock} label="Convidados" value={stats?.convites_pendentes ?? 0} color="warning" />
            </div>
            
            
            {/* Tabela de Membros e Convidados */}
            <DataTable
                data={combinedData}
                columns={columns}
                searchable
                searchPlaceholder="Buscar por nome ou email..."
                exportable
                exportFileName="equipe"
                emptyMessage="Nenhum membro encontrado."
            />

            {/* Drawer de Gerenciar Acessos por Propriedade */}
            {acessoMember && (
                <AcessoDrawer
                    open={!!acessoMember}
                    onOpenChange={(v) => { if (!v) setAcessoMember(null); }}
                    usuarioId={acessoMember.usuario_id}
                    usuarioNome={acessoMember.nome}
                />
            )}

            {/* Dialog de Edição de Perfil */}
            <Dialog open={!!editMember} onOpenChange={(open) => !open && setEditMember(null)}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader className="border-b">
                        <DialogTitle>Alterar Perfil</DialogTitle>
                        <DialogDescription className="text-xs">
                            Altere o perfil de acesso de {editMember?.nome}.
                        </DialogDescription>
                    </DialogHeader>
                    {editMember && roles && (
                        <EditMemberRoleForm
                            member={editMember as any}
                            roles={roles || []}
                            onSuccess={() => {
                                setEditMember(null);
                                queryClient.invalidateQueries({ queryKey: ["team"] });
                            }}
                        />
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}

const formField = (label: string, id: string, input: React.ReactNode, required = false) => (
    <div className="flex flex-col gap-1.5 w-full">
        <Label htmlFor={id} className="text-[10px] font-semibold text-foreground/70 uppercase tracking-wider">
            {label} {required && <span className="text-red-500">*</span>}
        </Label>
        {input}
    </div>
);

/* ─── Form: Convite ─── */

function InviteForm({
    roles,
    fazendas,
    onCancel,
    onSuccess,
}: {
    roles: TenantRoleProfile[];
    fazendas: Fazenda[];
    onCancel: () => void;
    onSuccess: () => void;
}) {
    const [selectedFazendas, setSelectedFazendas] = useState<string[]>([]);
    const [farmSearch, setFarmSearch] = useState("");

    const {
        register, handleSubmit, setValue,
        formState: { errors, isSubmitting },
    } = useForm<TeamInviteInput>({
        resolver: zodResolver(teamInviteSchema),
        defaultValues: { fazenda_ids: [] },
    });

    const inviteMutation = useMutation({
        mutationFn: (data: TeamInviteInput) =>
            apiFetch("/team/invite", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Convite enviado com sucesso!");
            onSuccess();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    function toggleFazenda(fazendaId: string) {
        const updated = selectedFazendas.includes(fazendaId)
            ? selectedFazendas.filter((id) => id !== fazendaId)
            : [...selectedFazendas, fazendaId];
        setSelectedFazendas(updated);
        setValue("fazenda_ids", updated);
    }

    const filteredFazendas = fazendas.filter((f: Fazenda) =>
        f.nome.toLowerCase().includes(farmSearch.toLowerCase())
    );

    return (
        <form onSubmit={handleSubmit((data) => inviteMutation.mutate(data))} className="flex max-h-[calc(85dvh-8rem)] flex-col">
            <DialogBody className="space-y-5 overflow-y-auto px-6 py-5">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="col-span-2">
                        {formField("E-mail do Membro", "email", (
                            <div className="relative">
                                <Mail size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
                                <Input
                                    id="email"
                                    {...register("email")}
                                    type="email"
                                    placeholder="ex: usuario@email.com.br"
                                    className="pl-8 bg-surface border-border-subtle"
                                />
                            </div>
                        ), true)}
                        {errors.email && <p className="mt-1 text-[10px] font-bold text-red-500">{errors.email.message}</p>}
                    </div>

                    <div className="col-span-2">
                        {formField("Perfil Corporativo", "perfil_id", (
                            <div className="relative">
                                <Users size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
                                <Select onValueChange={(val: string) => setValue("perfil_id", val)}>
                                    <SelectTrigger className="pl-8 bg-surface border-border-subtle">
                                        <SelectValue placeholder="Defina as permissões" />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {roles.map((role) => (
                                            <SelectItem key={role.id} value={role.id} className="text-xs">
                                                {role.nome}
                                                {role.is_custom && " (Personalizado)"}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        ), true)}
                        {errors.perfil_id && <p className="mt-1 text-[10px] font-bold text-red-500">{errors.perfil_id.message}</p>}
                    </div>
                </div>

                <div className="space-y-3 border-t border-border-subtle pt-3">
                    <div className="flex items-center justify-between">
                        <Label className="text-[10px] font-semibold uppercase tracking-wider text-foreground/70">
                            Fazendas Permitidas
                        </Label>
                        <div className="flex gap-1.5">
                            <Button
                                type="button"
                                variant="ghost"
                                size="xs"
                                className="h-5 px-1 text-[9px] font-bold uppercase text-primary hover:bg-primary/5"
                                onClick={() => {
                                    const allIds = fazendas.map((f: Fazenda) => f.id);
                                    setSelectedFazendas(allIds);
                                    setValue("fazenda_ids", allIds);
                                }}
                            >
                                Marcar Todas
                            </Button>
                            <Button
                                type="button"
                                variant="ghost"
                                size="xs"
                                className="h-5 px-1 text-[9px] font-bold uppercase text-muted-foreground hover:bg-muted/5"
                                onClick={() => {
                                    setSelectedFazendas([]);
                                    setValue("fazenda_ids", []);
                                }}
                            >
                                Limpar
                            </Button>
                        </div>
                    </div>

                    <div className="relative">
                        <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground/40" />
                        <Input
                            placeholder="Filtrar por nome..."
                            className="h-8 bg-muted/5 pl-8 text-xs border-border-subtle"
                            value={farmSearch}
                            onChange={(e) => setFarmSearch(e.target.value)}
                        />
                    </div>

                    <div className="grid max-h-44 grid-cols-2 gap-1.5 overflow-y-auto rounded-sm border border-border-subtle bg-muted/5 p-2 shadow-inner">
                        {filteredFazendas.length > 0 ? (
                            filteredFazendas.map((f) => (
                                <label
                                    key={f.id}
                                    className={`flex cursor-pointer items-center gap-2 rounded-sm border px-2 py-1.5 text-[11px] transition-all ${selectedFazendas.includes(f.id)
                                            ? "bg-primary/5 border-primary/20 text-primary font-bold shadow-sm"
                                            : "bg-surface border-transparent hover:border-neutral-200"
                                        }`}
                                >
                                    <Checkbox
                                        checked={selectedFazendas.includes(f.id)}
                                        onCheckedChange={() => toggleFazenda(f.id)}
                                        className="size-3.5 rounded-sm border-border-subtle data-[state=checked]:bg-primary"
                                    />
                                    <span className="truncate">{f.nome}</span>
                                </label>
                            ))
                        ) : (
                            <div className="col-span-2 py-4 text-center text-[10px] italic text-muted-foreground">
                                Nenhuma fazenda encontrada.
                            </div>
                        )}
                    </div>
                    {errors.fazenda_ids && <p className="text-[10px] font-bold text-red-500">{errors.fazenda_ids.message}</p>}
                </div>
            </DialogBody>
            <DialogFooter className="gap-2 px-6 py-4">
                <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="text-xs font-bold uppercase tracking-widest"
                    onClick={onCancel}
                >
                    Cancelar
                </Button>
                <Button
                    type="submit"
                    variant="outline"
                    size="sm"
                    disabled={isSubmitting || inviteMutation.isPending}
                    className="bg-primary border-primary text-primary-foreground text-xs font-bold uppercase tracking-widest hover:bg-primary/90"
                >
                    {inviteMutation.isPending ? "Aguarde..." : "Enviar Convite"}
                </Button>
            </DialogFooter>
        </form>
    );
}

/* ─── Form: Alterar Perfil do Membro ─── */

function EditMemberRoleForm({
    member,
    roles,
    onSuccess,
}: {
    member: TeamMember;
    roles: TenantRoleProfile[];
    onSuccess: () => void;
}) {
    const [selectedRole, setSelectedRole] = useState(member.perfil.id);

    const updateMutation = useMutation({
        mutationFn: () =>
            apiFetch(`/team/users/${member.id}/role`, {
                method: "PATCH",
                body: JSON.stringify({ perfil_id: selectedRole }),
            }),
        onSuccess: () => {
            toast.success("Perfil atualizado com sucesso!");
            onSuccess();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    return (
        <>
            <DialogBody>
                <Label className="text-[10px] font-semibold text-foreground/70 uppercase tracking-wider">Perfil de Acesso</Label>
                <Select value={selectedRole} onValueChange={setSelectedRole}>
                    <SelectTrigger className="rounded-sm mt-1 w-full">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-sm">
                        {roles.map((role) => (
                            <SelectItem key={role.id} value={role.id} className="text-xs">
                                {role.nome}
                                {role.is_custom && " (Personalizado)"}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </DialogBody>

            <DialogFooter>
                <Button
                    variant="outline"
                    size="sm"
                    className="text-xs uppercase font-bold tracking-widest"
                    onClick={onSuccess}
                >
                    Cancelar
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    disabled={updateMutation.isPending || selectedRole === member.perfil.id}
                    onClick={() => updateMutation.mutate()}
                    className="bg-primary border-primary text-primary-foreground text-xs uppercase font-bold tracking-widest hover:bg-primary/90"
                >
                    {updateMutation.isPending ? "Salvando..." : "Salvar Alterações"}
                </Button>
            </DialogFooter>
        </>
    );
}

/* ─── Login Lock Badge (aparece se estiver bloqueado) ─── */

function LoginLockBadge({ usuarioId }: { usuarioId: string }) {
    const { data: tentativas } = useTenantLoginTentativas(usuarioId);

    if (!tentativas || !tentativas.bloqueado) return null;

    return (
        <Tooltip>
            <TooltipTrigger render={
                <span className="inline-flex items-center cursor-pointer">
                    <Lock size={12} className="text-amber-500" />
                </span>
            } />
            <TooltipContent side="top" className="text-xs">
                <div className="space-y-1">
                    <p className="font-semibold text-amber-500">Bloqueado por tentativas</p>
                    <p className="text-muted-foreground">{tentativas.tentativas_count} tentativas · {tentativas.motivo_falha || "—"}</p>
                </div>
            </TooltipContent>
        </Tooltip>
    );
}

/* ─── Botão de desbloquear por tentativas ─── */

function DesbloquearTentativasButton({ usuarioId, email }: { usuarioId: string; email: string }) {
    const { data: tentativas, isLoading } = useTenantLoginTentativas(usuarioId);
    const desbloquear = useDesbloquearTenantUsuario();

    if (isLoading || !tentativas || !tentativas.bloqueado) return null;

    return (
        <Tooltip>
            <TooltipTrigger render={
                <Button
                    variant="outline"
                    size="sm"
                    className="h-7 w-7 p-0 text-amber-500 hover:text-amber-600 hover:bg-amber-50"
                    disabled={desbloquear.isPending}
                    onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        desbloquear.mutate(usuarioId);
                    }}
                >
                    <Unlock size={16} />
                </Button>
            } />
            <TooltipContent side="left">
                Desbloquear login ({tentativas.tentativas_count} tentativas)
            </TooltipContent>
        </Tooltip>
    );
}
