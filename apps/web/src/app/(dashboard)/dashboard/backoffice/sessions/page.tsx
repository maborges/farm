"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    MonitorSmartphone, Globe, Clock, XCircle, Users, Activity,
    RefreshCw, Wifi, WifiOff,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { formatDistanceToNow, format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, ColumnDef } from "@/components/ui/data-table";

interface Session {
    id: string;
    tenant_id: string;
    usuario_id: string;
    unidade_produtiva_id: string | null;
    ip_address: string | null;
    user_agent: string | null;
    inicio: string;
    ultimo_heartbeat: string;
    expira_em: string;
    status: string;
}

interface SessionStats {
    total_ativas: number;
    total_expiradas: number;
    por_status: Record<string, number>;
    por_tenant: Record<string, number>;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Wifi }> = {
    ATIVA: { label: "Ativa", color: "bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30", icon: Wifi },
    EXPIRADA: { label: "Expirada", color: "bg-amber-500/10 text-amber-700 border-amber-200 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30", icon: WifiOff },
    ENCERRADA: { label: "Encerrada", color: "bg-red-500/10 text-red-700 border-red-200 dark:bg-red-500/20 dark:text-red-100 dark:border-red-400/30", icon: XCircle },
};

function parseUserAgent(ua: string | null): string {
    if (!ua) return "Desconhecido";
    if (ua.includes("Chrome")) return "Chrome";
    if (ua.includes("Firefox")) return "Firefox";
    if (ua.includes("Safari")) return "Safari";
    if (ua.includes("Edge")) return "Edge";
    return ua.substring(0, 30) + "...";
}

export default function SessionsBackofficePage() {
    const queryClient = useQueryClient();
    const [statusFilter, setStatusFilter] = useState("ATIVA");
    const [killTarget, setKillTarget] = useState<string | null>(null);

    const { data: sessions, isLoading } = useQuery<Session[]>({
        queryKey: ["backoffice", "sessions", statusFilter],
        queryFn: () => {
            const params = new URLSearchParams();
            if (statusFilter) params.set("status_filtro", statusFilter);
            return apiFetch(`/backoffice/sessions?${params.toString()}`);
        },
        refetchInterval: 30000,
    });

    const { data: stats } = useQuery<SessionStats>({
        queryKey: ["backoffice", "sessions", "stats"],
        queryFn: () => apiFetch("/backoffice/sessions/stats"),
        refetchInterval: 30000,
    });

    const killMutation = useMutation({
        mutationFn: (sessionId: string) =>
            apiFetch(`/backoffice/sessions/${sessionId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "sessions"] });
            toast.success("Sessão encerrada!");
            setKillTarget(null);
        },
        onError: (err: any) => toast.error(err.message || "Erro ao encerrar sessão"),
    });

    // Definição das colunas para o DataTable
    const columns: ColumnDef<Session>[] = [
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            cell: (value, row) => {
                const config = STATUS_CONFIG[value] ?? STATUS_CONFIG.ENCERRADA;
                const StatusIcon = config.icon;
                return (
                    <Badge className={`text-[9px] font-black uppercase border ${config.color}`}>
                        <StatusIcon className="size-3 mr-1" />
                        {config.label}
                    </Badge>
                );
            },
            exportFormat: (value) => STATUS_CONFIG[value]?.label || value,
            sortable: true,
        },
        {
            id: "tenant_id",
            header: "Tenant ID",
            accessorKey: "tenant_id",
            cell: (value) => (
                <code className="text-[10px] font-mono text-muted-foreground">
                    {value.substring(0, 8)}...
                </code>
            ),
            exportFormat: (value) => value,
            sortable: true,
        },
        {
            id: "usuario_id",
            header: "Usuário ID",
            accessorKey: "usuario_id",
            cell: (value) => (
                <code className="text-[10px] font-mono text-muted-foreground">
                    {value.substring(0, 8)}...
                </code>
            ),
            exportFormat: (value) => value,
            sortable: true,
        },
        {
            id: "ip_address",
            header: "IP",
            accessorKey: "ip_address",
            cell: (value) => (
                <div className="flex items-center gap-1">
                    <Globe className="size-3 text-muted-foreground" />
                    <span className="text-xs font-mono">{value || "—"}</span>
                </div>
            ),
            exportFormat: (value) => value || "N/A",
            sortable: true,
        },
        {
            id: "user_agent",
            header: "Navegador",
            accessorKey: "user_agent",
            cell: (value) => (
                <div className="flex items-center gap-1">
                    <MonitorSmartphone className="size-3 text-muted-foreground" />
                    <span className="text-xs">{parseUserAgent(value)}</span>
                </div>
            ),
            exportFormat: (value) => parseUserAgent(value),
            sortable: false,
        },
        {
            id: "inicio",
            header: "Início",
            accessorKey: "inicio",
            cell: (value) => (
                <div className="flex flex-col">
                    <span className="text-xs font-medium">
                        {format(new Date(value), "dd/MM HH:mm", { locale: ptBR })}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                        {formatDistanceToNow(new Date(value), { addSuffix: true, locale: ptBR })}
                    </span>
                </div>
            ),
            exportFormat: (value) => format(new Date(value), "dd/MM/yyyy HH:mm", { locale: ptBR }),
            sortable: true,
        },
        {
            id: "ultimo_heartbeat",
            header: "Último Heartbeat",
            accessorKey: "ultimo_heartbeat",
            cell: (value) => (
                <div className="flex items-center gap-1">
                    <Activity className="size-3 text-muted-foreground" />
                    <span className="text-xs">
                        {formatDistanceToNow(new Date(value), { addSuffix: true, locale: ptBR })}
                    </span>
                </div>
            ),
            exportFormat: (value) => format(new Date(value), "dd/MM/yyyy HH:mm", { locale: ptBR }),
            sortable: true,
        },
        {
            id: "acoes",
            header: "",
            cell: (_, row) => {
                if (row.status !== "ATIVA") return null;
                return (
                    <div className="flex items-center gap-1 justify-end">
                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-700 hover:bg-red-50 h-7 px-2"
                            onClick={(e) => {
                                e.stopPropagation();
                                setKillTarget(row.id);
                            }}
                        >
                            <XCircle className="size-4 mr-1" /> Encerrar
                        </Button>
                    </div>
                );
            },
            exportable: false,
            sortable: false,
            filterable: false,
        },
    ];

    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-16 w-full" />
                <div className="grid gap-4 md:grid-cols-3">
                    {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
                </div>
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Sessões Ativas"
                description="Monitore e gerencie sessões de usuários em tempo real."
                icon={<Clock className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Sessões Ativas" },
                ]}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => queryClient.invalidateQueries({ queryKey: ["backoffice", "sessions"] })}
                    >
                        <RefreshCw className="size-4 mr-2" /> Atualizar
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card className="border-l-[3px] border-l-green-500">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-green-500/10 flex items-center justify-center text-green-600">
                            <Wifi size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Ativas Agora</p>
                            <p className="text-2xl font-black">{stats?.total_ativas ?? 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-amber-500">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-600">
                            <WifiOff size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Expiradas</p>
                            <p className="text-2xl font-black">{stats?.total_expiradas ?? 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-blue-500">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-600">
                            <Users size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Produtores com sessão</p>
                            <p className="text-2xl font-black">{stats ? Object.keys(stats.por_tenant).length : 0}</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Filter */}
            <div className="flex gap-3">
                <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
                    <SelectTrigger className="w-48"><SelectValue placeholder="Filtrar por status" /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Todos os status</SelectItem>
                        <SelectItem value="ATIVA">Ativas</SelectItem>
                        <SelectItem value="EXPIRADA">Expiradas</SelectItem>
                        <SelectItem value="ENCERRADA">Encerradas</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* DataTable */}
            <DataTable
                data={sessions || []}
                columns={columns}
                searchable={true}
                searchPlaceholder="Buscar por tenant, usuário, IP..."
                exportable={true}
                exportFileName="sessoes"
                emptyMessage="Nenhuma sessão encontrada."
            />

            {/* Auto-refresh indicator */}
            <p className="text-[10px] text-muted-foreground text-center">
                Atualização automática a cada 30 segundos
            </p>

            {/* Kill Confirmation */}
            <AlertDialog open={!!killTarget} onOpenChange={() => setKillTarget(null)}>
                <AlertDialogContent className="w-[calc(100vw-1rem)] sm:max-w-md">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Encerrar sessão?</AlertDialogTitle>
                        <AlertDialogDescription>
                            O usuário será desconectado imediatamente e precisará fazer login novamente.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            className="bg-red-600 hover:bg-red-700"
                            onClick={() => killTarget && killMutation.mutate(killTarget)}
                        >
                            Encerrar Sessão
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
