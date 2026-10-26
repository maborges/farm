"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    Sprout, Users, ShieldCheck, UserX, UserCheck,
    Search, Mail, Calendar, KeyRound, Eye,
    LogOut, AlertTriangle, Key, Shield,
    Clock, Smartphone, User, RefreshCw, ChevronLeft, ChevronRight
} from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from "@/components/ui/avatar";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
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
import { resolveAssetUrl } from "@/lib/runtime-config";

// ==============================================================================
// TIPOS E CONTRATOS (TS STRICT)
// ==============================================================================

interface AgroByokMeta {
    id: string;
    provider_slug: string;
    mascara_chave: string;
    key_version: number;
    status: string;
    ultimo_uso: string | null;
    created_at: string;
}

interface AgroSessionItem {
    id: string;
    status: string;
    ip_address: string | null;
    user_agent: string | null;
    inicio: string;
    ultimo_heartbeat: string;
    expira_em: string;
}

interface AgroAuditLogItem {
    id: string;
    admin_email: string;
    acao: string;
    descricao: string | null;
    created_at: string;
}

interface AgroUserListItem {
    id: string;
    email: string;
    username: string;
    nome_completo: string | null;
    cpf: string | null;
    telefone: string | null;
    ativo: boolean;
    account_type: string;
    data_cadastro: string;
    ultimo_acesso: string | null;
    sessoes_ativas_count: number;
    byok_count: number;
    byok_providers: string[];
}

interface AgroUserListResponse {
    items: AgroUserListItem[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

interface AgroUserDetailResponse {
    id: string;
    email: string;
    username: string;
    nome_completo: string | null;
    cpf: string | null;
    telefone: string | null;
    apelido: string | null;
    foto_perfil_url: string | null;
    ativo: boolean;
    account_type: string;
    is_superuser: boolean;
    data_cadastro: string;
    updated_at: string | null;
    sessoes_ativas: AgroSessionItem[];
    credenciais_byok: AgroByokMeta[];
    acoes_auditoria: AgroAuditLogItem[];
}
// ==============================================================================
// COMPONENTE PRINCIPAL
// ==============================================================================

export default function AgroUsuariosPage() {
    const queryClient = useQueryClient();

    // Filtros e paginação
    const [page, setPage] = useState<number>(1);
    const [pageSize] = useState<number>(15);
    const [searchTerm, setSearchTerm] = useState<string>("");
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [byokFilter, setByokFilter] = useState<string>("all");

    // Diálogos de ação e detalhes
    const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
    const [toggleUserTarget, setToggleUserTarget] = useState<AgroUserListItem | null>(null);
    const [revokeSessionsTarget, setRevokeSessionsTarget] = useState<AgroUserListItem | null>(null);

    // Consulta paginada de produtores
    const {
        data: listResponse,
        isLoading,
        isFetching,
        refetch,
    } = useQuery<AgroUserListResponse>({
        queryKey: ["backoffice", "agro", "usuarios", page, pageSize, searchTerm, statusFilter, byokFilter],
        queryFn: () => {
            const params: Record<string, string | number | boolean> = {
                page,
                page_size: pageSize,
            };
            if (searchTerm.trim()) params.search = searchTerm.trim();
            if (statusFilter !== "all") params.status = statusFilter;
            if (byokFilter === "true") params.has_byok = true;
            if (byokFilter === "false") params.has_byok = false;
            return apiFetch<AgroUserListResponse>("/backoffice/agro/usuarios", { params });
        },
    });

    // Consulta de detalhes do produtor selecionado
    const {
        data: userDetails,
        isLoading: isLoadingDetails,
    } = useQuery<AgroUserDetailResponse>({
        queryKey: ["backoffice", "agro", "usuario", selectedUserId],
        queryFn: () => apiFetch<AgroUserDetailResponse>(`/backoffice/agro/usuarios/${selectedUserId}`),
        enabled: !!selectedUserId,
    });

    // Mutação: Alternar status (Bloquear/Desbloquear)
    const toggleStatusMutation = useMutation({
        mutationFn: (userId: string) =>
            apiFetch<{ id: string; novo_status: boolean; sessoes_encerradas: number; mensagem: string }>(
                `/backoffice/agro/usuarios/${userId}/toggle-status`,
                { method: "POST" }
            ),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "agro", "usuarios"] });
            if (selectedUserId) {
                queryClient.invalidateQueries({ queryKey: ["backoffice", "agro", "usuario", selectedUserId] });
            }
            toast.success(data.mensagem || "Status atualizado com sucesso.");
            setToggleUserTarget(null);
        },
        onError: (err: Error) => {
            toast.error(err.message || "Erro ao alterar status do produtor.");
        },
    });



    // Mutação: Revogar todas as sessões ativas
    const revokeSessionsMutation = useMutation({
        mutationFn: (userId: string) =>
            apiFetch<{ id: string; sessoes_encerradas: number; mensagem: string }>(
                `/backoffice/agro/usuarios/${userId}/sessions`,
                { method: "DELETE" }
            ),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "agro", "usuarios"] });
            if (selectedUserId) {
                queryClient.invalidateQueries({ queryKey: ["backoffice", "agro", "usuario", selectedUserId] });
            }
            toast.success(data.mensagem || "Sessões revogadas com sucesso.");
            setRevokeSessionsTarget(null);
        },
        onError: (err: Error) => {
            toast.error(err.message || "Erro ao revogar sessões ativas.");
        },
    });

    // Definição das colunas da tabela
    const columns: ColumnDef<AgroUserListItem>[] = [
        {
            id: "produtor",
            header: "Produtor Rural",
            accessorKey: "nome_completo",
            cell: (_value, user) => (
                <div className="flex items-center gap-3">
                    <Avatar className="h-9 w-9 border border-emerald-500/20 shadow-xs">
                        <AvatarImage
                            src={resolveAssetUrl(null)}
                            alt={user.nome_completo || user.username}
                        />
                        <AvatarFallback className="bg-emerald-500/10 text-emerald-800 text-xs font-bold dark:bg-emerald-500/20 dark:text-emerald-100">
                            {user.nome_completo?.charAt(0) || user.username.charAt(0).toUpperCase()}
                        </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col min-w-0">
                        <span className="font-semibold text-foreground text-xs leading-tight truncate">
                            {user.nome_completo || user.username}
                        </span>
                        <span className="text-[11px] text-muted-foreground flex items-center gap-1 mt-0.5">
                            <Mail size={11} className="text-muted-foreground/70" /> {user.email}
                        </span>
                        <span className="text-[10px] text-muted-foreground/80">
                            @{user.username}
                        </span>
                    </div>
                </div>
            ),
            sortable: true,
        },
        {
            id: "status",
            header: "Situação",
            accessorKey: "ativo",
            cell: (_value, user) => (
                <Badge
                    variant={user.ativo ? "outline" : "destructive"}
                    className={`text-[10px] uppercase font-black px-2 py-0.5 rounded-sm ${
                        user.ativo
                            ? "border-emerald-300 text-emerald-700 bg-emerald-50 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-500/40"
                            : "border-red-300 text-red-700 bg-red-50 dark:bg-red-500/20 dark:text-red-100 dark:border-red-500/40"
                    }`}
                >
                    {user.ativo ? "Ativo" : "Bloqueado"}
                </Badge>
            ),
        },
        {
            id: "cadastro",
            header: "Cadastro",
            accessorKey: "data_cadastro",
            cell: (_value, user) => (
                <div className="flex items-center gap-1 text-muted-foreground text-xs font-medium">
                    <Calendar size={12} className="text-muted-foreground/70" />
                    {format(new Date(user.data_cadastro), "dd/MM/yyyy", { locale: ptBR })}
                </div>
            ),
        },
        {
            id: "atividade",
            header: "Último Acesso",
            accessorKey: "ultimo_acesso",
            cell: (_value, user) => (
                user.ultimo_acesso ? (
                    <div className="flex items-center gap-1 text-muted-foreground text-xs font-medium">
                        <Clock size={12} className="text-emerald-600 dark:text-emerald-400" />
                        {format(new Date(user.ultimo_acesso), "dd/MM/yy HH:mm", { locale: ptBR })}
                    </div>
                ) : (
                    <span className="text-[11px] text-muted-foreground italic">Sem registros</span>
                )
            ),
        },
        {
            id: "sessoes",
            header: "Sessões Ativas",
            accessorKey: "sessoes_ativas_count",
            cell: (_value, user) => (
                user.sessoes_ativas_count > 0 ? (
                    <Badge variant="outline" className="text-[10px] font-semibold border-emerald-500/30 text-emerald-800 bg-emerald-50/50 dark:bg-emerald-500/10 dark:text-emerald-200">
                        {user.sessoes_ativas_count} ativa(s)
                    </Badge>
                ) : (
                    <span className="text-[11px] text-muted-foreground/70">Nenhuma</span>
                )
            ),
        },
        {
            id: "byok",
            header: "Cofre BYOK",
            accessorKey: "byok_count",
            cell: (_value, user) => (
                user.byok_count > 0 ? (
                    <div className="flex items-center gap-1 flex-wrap">
                        {user.byok_providers.map((p) => (
                            <Badge key={p} variant="secondary" className="text-[9px] uppercase font-mono px-1.5 py-0 border border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-100">
                                {p}
                            </Badge>
                        ))}
                    </div>
                ) : (
                    <span className="text-[10px] text-muted-foreground italic">Sem chaves</span>
                )
            ),
        },
        {
            id: "acoes",
            header: "",
            accessorKey: "id",
            sortable: false,
            filterable: false,
            exportable: false,
            cell: (_value, user) => (
                <div className="flex items-center justify-end gap-1">
                    {/* Botão Ver Detalhes */}
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="outline"
                                size="sm"
                                className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                                onClick={() => setSelectedUserId(user.id)}
                            >
                                <Eye size={13} />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent side="top">Ver perfil e cofre BYOK</TooltipContent>
                    </Tooltip>

                    {/* Botão Revogar Sessões */}
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={user.sessoes_ativas_count === 0}
                                className="h-7 w-7 p-0 text-amber-600 hover:text-amber-700 hover:bg-amber-50 dark:hover:bg-amber-950/20 disabled:opacity-30"
                                onClick={() => setRevokeSessionsTarget(user)}
                            >
                                <LogOut size={13} />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent side="top">Derrubar todas as sessões</TooltipContent>
                    </Tooltip>

                    {/* Botão Bloquear / Desbloquear */}
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="outline"
                                size="sm"
                                className={`h-7 w-7 p-0 ${
                                    user.ativo
                                        ? "text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20"
                                        : "text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/20"
                                }`}
                                onClick={() => setToggleUserTarget(user)}
                            >
                                {user.ativo ? <UserX size={13} /> : <UserCheck size={13} />}
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent side="top">
                            {user.ativo ? "Bloquear produtor" : "Desbloquear produtor"}
                        </TooltipContent>
                    </Tooltip>

                </div>
            ),
        },
    ];

    const users = listResponse?.items || [];
    const totalCount = listResponse?.total || 0;
    const totalPages = listResponse?.total_pages || 1;

    return (
        <div className="p-8 space-y-6 w-full max-w-full">
            <PageHeader
                title="Produtores DeepFarms Agro"
                description="Governança operacional de produtores rurais gratuitos, sessões ativas e cofre BYOK."
                icon={<Sprout className="text-emerald-600 dark:text-emerald-400" size={24} />}
            />

            {/* Cards de Resumo */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card className="border-l-[3px] border-l-emerald-600 shadow-xs">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">
                            <Users size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                Total de Produtores
                            </p>
                            <p className="text-xl font-black text-foreground">{totalCount}</p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-emerald-500 shadow-xs">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300">
                            <ShieldCheck size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                Contas Ativas
                            </p>
                            <p className="text-xl font-black text-foreground">
                                {users.filter((u) => u.ativo).length}
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-amber-500 shadow-xs">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-600 dark:bg-amber-500/20 dark:text-amber-300">
                            <Key size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                Com Cofre BYOK
                            </p>
                            <p className="text-xl font-black text-foreground">
                                {users.filter((u) => u.byok_count > 0).length}
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-red-500 shadow-xs">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-red-500/10 flex items-center justify-center text-red-600 dark:bg-red-500/20 dark:text-red-300">
                            <UserX size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                Bloqueados
                            </p>
                            <p className="text-xl font-black text-foreground">
                                {users.filter((u) => !u.ativo).length}
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Barra de Filtros e Busca */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-muted/20 p-3 rounded-sm border">
                <div className="flex items-center gap-2 flex-1 max-w-md">
                    <div className="relative w-full">
                        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            placeholder="Buscar por nome, e-mail, username ou CPF..."
                            value={searchTerm}
                            onChange={(e) => {
                                setSearchTerm(e.target.value);
                                setPage(1);
                            }}
                            className="pl-8 h-8 text-xs rounded-sm"
                        />
                    </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                    {/* Filtro de Status */}
                    <div className="flex items-center gap-1 bg-background p-0.5 rounded-sm border">
                        <Button
                            variant={statusFilter === "all" ? "outline" : "ghost"}
                            size="sm"
                            className={`h-7 text-xs px-2.5 rounded-sm ${statusFilter === "all" ? "bg-muted font-bold" : ""}`}
                            onClick={() => { setStatusFilter("all"); setPage(1); }}
                        >
                            Todos
                        </Button>
                        <Button
                            variant={statusFilter === "ativo" ? "outline" : "ghost"}
                            size="sm"
                            className={`h-7 text-xs px-2.5 rounded-sm ${statusFilter === "ativo" ? "bg-muted font-bold text-emerald-700 dark:text-emerald-300" : ""}`}
                            onClick={() => { setStatusFilter("ativo"); setPage(1); }}
                        >
                            Ativos
                        </Button>
                        <Button
                            variant={statusFilter === "bloqueado" ? "outline" : "ghost"}
                            size="sm"
                            className={`h-7 text-xs px-2.5 rounded-sm ${statusFilter === "bloqueado" ? "bg-muted font-bold text-red-700 dark:text-red-300" : ""}`}
                            onClick={() => { setStatusFilter("bloqueado"); setPage(1); }}
                        >
                            Bloqueados
                        </Button>
                    </div>

                    {/* Filtro BYOK */}
                    <div className="flex items-center gap-1 bg-background p-0.5 rounded-sm border">
                        <Button
                            variant={byokFilter === "all" ? "outline" : "ghost"}
                            size="sm"
                            className={`h-7 text-xs px-2 rounded-sm ${byokFilter === "all" ? "bg-muted font-bold" : ""}`}
                            onClick={() => { setByokFilter("all"); setPage(1); }}
                        >
                            BYOK: Todos
                        </Button>
                        <Button
                            variant={byokFilter === "true" ? "outline" : "ghost"}
                            size="sm"
                            className={`h-7 text-xs px-2 rounded-sm ${byokFilter === "true" ? "bg-muted font-bold text-emerald-700" : ""}`}
                            onClick={() => { setByokFilter("true"); setPage(1); }}
                        >
                            Com Chaves
                        </Button>
                    </div>

                    <Button
                        variant="outline"
                        size="sm"
                        className="h-8 w-8 p-0 rounded-sm"
                        disabled={isFetching}
                        onClick={() => refetch()}
                    >
                        <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
                    </Button>
                </div>
            </div>

            {/* Tabela de Produtores */}
            {isLoading ? (
                <div className="space-y-2">
                    <Skeleton className="h-10 w-full rounded-sm" />
                    <Skeleton className="h-64 w-full rounded-sm" />
                </div>
            ) : (
                <div className="space-y-4">
                    <DataTable
                        data={users}
                        columns={columns}
                        searchable={false}
                        exportable={true}
                        exportFileName="produtores-agro"
                        emptyMessage="Nenhum produtor rural encontrado com os filtros informados."
                    />

                    {/* Controles de Paginação Server-Side */}
                    <div className="flex items-center justify-between px-2 text-xs text-muted-foreground">
                        <div>
                            Exibindo {users.length} de {totalCount} produtores
                        </div>
                        <div className="flex items-center gap-2">
                            <span>
                                Página <strong>{page}</strong> de <strong>{totalPages}</strong>
                            </span>
                            <div className="flex items-center gap-1">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 w-7 p-0"
                                    disabled={page <= 1 || isFetching}
                                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                                >
                                    <ChevronLeft size={14} />
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 w-7 p-0"
                                    disabled={page >= totalPages || isFetching}
                                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                >
                                    <ChevronRight size={14} />
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal: Detalhes do Produtor Agro e Cofre BYOK */}
            <Dialog open={!!selectedUserId} onOpenChange={(open) => !open && setSelectedUserId(null)}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-base font-bold">
                            <Sprout className="text-emerald-600" size={18} />
                            Perfil do Produtor Agro
                        </DialogTitle>
                    </DialogHeader>

                    {isLoadingDetails || !userDetails ? (
                        <div className="p-6 space-y-4">
                            <Skeleton className="h-12 w-full" />
                            <Skeleton className="h-32 w-full" />
                        </div>
                    ) : (
                        <div className="space-y-6 py-2">
                            {/* Identificação Principal */}
                            <div className="flex items-center justify-between p-3 rounded-sm bg-muted/30 border">
                                <div className="flex items-center gap-3">
                                    <Avatar className="h-12 w-12 border">
                                        <AvatarFallback className="bg-emerald-600/10 text-emerald-800 text-base font-bold">
                                            {userDetails.nome_completo?.charAt(0) || userDetails.username.charAt(0).toUpperCase()}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div>
                                        <p className="font-bold text-sm text-foreground">
                                            {userDetails.nome_completo || userDetails.username}
                                        </p>
                                        <p className="text-xs text-muted-foreground">{userDetails.email}</p>
                                        <p className="text-[11px] text-muted-foreground/80">@{userDetails.username}</p>
                                    </div>
                                </div>
                                <div className="flex flex-col items-end gap-1">
                                    <Badge variant="outline" className="text-[10px] font-black uppercase border-emerald-500/40 text-emerald-800 bg-emerald-50/50">
                                        INDIVIDUAL_FREE
                                    </Badge>
                                    <Badge
                                        variant={userDetails.ativo ? "outline" : "destructive"}
                                        className="text-[9px] uppercase font-bold"
                                    >
                                        {userDetails.ativo ? "Ativo" : "Bloqueado"}
                                    </Badge>
                                </div>
                            </div>

                            {/* Informações de Contato e Cadastro */}
                            <div className="grid grid-cols-2 gap-3 text-xs">
                                <div className="p-2.5 rounded-sm border bg-card">
                                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">CPF</span>
                                    <span className="font-mono">{userDetails.cpf || "Não informado"}</span>
                                </div>
                                <div className="p-2.5 rounded-sm border bg-card">
                                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">Telefone</span>
                                    <span>{userDetails.telefone || "Não informado"}</span>
                                </div>
                                <div className="p-2.5 rounded-sm border bg-card">
                                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">Data de Cadastro</span>
                                    <span>{format(new Date(userDetails.data_cadastro), "dd/MM/yyyy HH:mm", { locale: ptBR })}</span>
                                </div>
                                <div className="p-2.5 rounded-sm border bg-card">
                                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">Última Atualização</span>
                                    <span>{userDetails.updated_at ? format(new Date(userDetails.updated_at), "dd/MM/yyyy HH:mm", { locale: ptBR }) : "—"}</span>
                                </div>
                            </div>

                            {/* Cofre BYOK (Bring Your Own Key) */}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                        <Key size={13} className="text-amber-500" /> Cofre BYOK (Credenciais do Usuário)
                                    </h4>
                                    <Badge variant="secondary" className="text-[10px]">
                                        {userDetails.credenciais_byok.length} configurada(s)
                                    </Badge>
                                </div>

                                {userDetails.credenciais_byok.length > 0 ? (
                                    <div className="border rounded-sm divide-y text-xs">
                                        {userDetails.credenciais_byok.map((byok) => (
                                            <div key={byok.id} className="p-2.5 flex items-center justify-between">
                                                <div>
                                                    <span className="font-bold text-foreground uppercase tracking-wide">
                                                        {byok.provider_slug}
                                                    </span>
                                                    <span className="text-[11px] font-mono text-muted-foreground block">
                                                        Máscara: {byok.mascara_chave}
                                                    </span>
                                                </div>
                                                <div className="text-right">
                                                    <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-700">
                                                        {byok.status}
                                                    </Badge>
                                                    <span className="text-[10px] text-muted-foreground block mt-0.5">
                                                        Último uso: {byok.ultimo_uso ? format(new Date(byok.ultimo_uso), "dd/MM/yy HH:mm", { locale: ptBR }) : "Nunca"}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="p-3 border rounded-sm text-center text-xs text-muted-foreground italic bg-muted/10">
                                        Nenhuma chave de cotação pessoal configurada no cofre BYOK.
                                    </div>
                                )}
                                <p className="text-[10px] text-muted-foreground/80 flex items-center gap-1">
                                    <Shield size={11} className="text-emerald-600" />
                                    Chaves cifradas com Envelope Encryption (AES-256-GCM). Segredos nunca expostos na interface.
                                </p>
                            </div>

                            {/* Sessões Ativas */}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                        <Smartphone size={13} className="text-emerald-600" /> Sessões Ativas
                                    </h4>
                                    {userDetails.sessoes_ativas.length > 0 && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="h-6 text-[10px] text-amber-600 hover:text-amber-700"
                                            onClick={() => setRevokeSessionsTarget(userDetails as unknown as AgroUserListItem)}
                                        >
                                            <LogOut size={11} className="mr-1" /> Revogar Todas
                                        </Button>
                                    )}
                                </div>

                                {userDetails.sessoes_ativas.length > 0 ? (
                                    <div className="border rounded-sm divide-y text-xs max-h-40 overflow-y-auto">
                                        {userDetails.sessoes_ativas.map((s) => (
                                            <div key={s.id} className="p-2 flex items-center justify-between">
                                                <div>
                                                    <span className="font-mono text-[11px] block text-foreground">
                                                        IP: {s.ip_address || "Não identificado"}
                                                    </span>
                                                    <span className="text-[10px] text-muted-foreground truncate max-w-xs block">
                                                        {s.user_agent || "Navegador Web"}
                                                    </span>
                                                </div>
                                                <div className="text-right text-[10px] text-muted-foreground">
                                                    <span>Heartbeat: {format(new Date(s.ultimo_heartbeat), "HH:mm:ss", { locale: ptBR })}</span>
                                                    <span className="block text-emerald-600 font-semibold uppercase">{s.status}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="p-3 border rounded-sm text-center text-xs text-muted-foreground italic bg-muted/10">
                                        Nenhuma sessão ativa neste momento.
                                    </div>
                                )}
                            </div>

                            {/* Trilha de Auditoria Recente */}
                            {userDetails.acoes_auditoria.length > 0 && (
                                <div className="space-y-2">
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                        <Clock size={13} /> Histórico de Ações Administrativas
                                    </h4>
                                    <div className="border rounded-sm divide-y text-xs">
                                        {userDetails.acoes_auditoria.map((a) => (
                                            <div key={a.id} className="p-2 flex items-center justify-between">
                                                <div>
                                                    <span className="font-mono text-[11px] font-bold text-foreground">
                                                        {a.acao}
                                                    </span>
                                                    <span className="text-[10px] text-muted-foreground block">
                                                        {a.descricao || "Ação operacional"}
                                                    </span>
                                                </div>
                                                <div className="text-right text-[10px] text-muted-foreground">
                                                    <span>Por: {a.admin_email}</span>
                                                    <span className="block">{format(new Date(a.created_at), "dd/MM/yy HH:mm", { locale: ptBR })}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    <DialogFooter className="flex items-center justify-end w-full">
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            onClick={() => setSelectedUserId(null)}
                        >
                            Fechar
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Confirmação: Bloquear / Desbloquear Usuário */}
            <AlertDialog open={!!toggleUserTarget} onOpenChange={(open) => !open && setToggleUserTarget(null)}>
                <AlertDialogContent className="max-w-md">
                    <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2">
                            <AlertTriangle className={toggleUserTarget?.ativo ? "text-red-500" : "text-emerald-500"} size={18} />
                            {toggleUserTarget?.ativo ? "Bloquear Produtor Rural?" : "Desbloquear Produtor Rural?"}
                        </AlertDialogTitle>
                        <AlertDialogDescription className="text-xs">
                            {toggleUserTarget?.ativo ? (
                                <>
                                    Ao bloquear <strong>{toggleUserTarget.nome_completo || toggleUserTarget.email}</strong>, o produtor
                                    perderá imediatamente o acesso ao DeepFarms Agro e todas as suas sessões ativas serão encerradas.
                                </>
                            ) : (
                                <>
                                    Ao desbloquear <strong>{toggleUserTarget?.nome_completo || toggleUserTarget?.email}</strong>, o produtor
                                    poderá efetuar login normalmente na plataforma com suas credenciais.
                                </>
                            )}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={toggleStatusMutation.isPending}>Cancelar</AlertDialogCancel>
                        <AlertDialogAction asChild>
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={toggleStatusMutation.isPending}
                                className={toggleUserTarget?.ativo ? "bg-red-600 text-white hover:bg-red-700" : "bg-emerald-600 text-white hover:bg-emerald-700"}
                                onClick={() => {
                                    if (toggleUserTarget) toggleStatusMutation.mutate(toggleUserTarget.id);
                                }}
                            >
                                {toggleStatusMutation.isPending ? "Processando..." : (toggleUserTarget?.ativo ? "Confirmar Bloqueio" : "Confirmar Desbloqueio")}
                            </Button>
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Confirmação: Revogar Todas as Sessões */}
            <AlertDialog open={!!revokeSessionsTarget} onOpenChange={(open) => !open && setRevokeSessionsTarget(null)}>
                <AlertDialogContent className="max-w-md">
                    <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2 text-amber-600">
                            <LogOut size={18} />
                            Revogar Sessões Ativas?
                        </AlertDialogTitle>
                        <AlertDialogDescription className="text-xs">
                            Todas as sessões ativas de <strong>{revokeSessionsTarget?.nome_completo || revokeSessionsTarget?.email}</strong> serão
                            imediatamente invalidadas. O produtor precisará realizar login novamente em seus dispositivos.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={revokeSessionsMutation.isPending}>Cancelar</AlertDialogCancel>
                        <AlertDialogAction asChild>
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={revokeSessionsMutation.isPending}
                                className="bg-amber-600 text-white hover:bg-amber-700"
                                onClick={() => {
                                    if (revokeSessionsTarget) revokeSessionsMutation.mutate(revokeSessionsTarget.id);
                                }}
                            >
                                {revokeSessionsMutation.isPending ? "Revogando..." : "Revogar Sessões"}
                            </Button>
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>


        </div>
    );
}
