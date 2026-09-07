"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Activity, ChevronRight, User, Globe, Monitor, Filter, X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, ColumnDef } from "@/components/ui/data-table";

interface AuditLog {
    id: string;
    admin_user_id: string;
    admin_email: string;
    acao: string;
    entidade: string;
    entidade_id: string | null;
    descricao: string | null;
    dados_anteriores: Record<string, any> | null;
    dados_novos: Record<string, any> | null;
    ip_address: string | null;
    user_agent: string | null;
    created_at: string;
}

interface AuditStats {
    total: number;
    por_acao: Record<string, number>;
    por_entidade: Record<string, number>;
    por_admin: Record<string, number>;
}

const ACAO_COLORS: Record<string, string> = {
    CREATED: "bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30",
    UPDATED: "bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30",
    DELETED: "bg-red-500/10 text-red-700 border-red-200 dark:bg-red-500/20 dark:text-red-100 dark:border-red-400/30",
    DEACTIVATED: "bg-amber-500/10 text-amber-700 border-amber-200 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30",
    IMPERSONATE: "bg-violet-500/10 text-violet-700 border-violet-200 dark:bg-violet-500/20 dark:text-violet-100 dark:border-violet-400/30",
    PASSWORD_RESET: "bg-orange-500/10 text-orange-700 border-orange-200 dark:bg-orange-500/20 dark:text-orange-100 dark:border-orange-400/30",
};

function getAcaoColor(acao: string): string {
    const key = Object.keys(ACAO_COLORS).find((k) => acao.toUpperCase().includes(k));
    return key ? ACAO_COLORS[key] : "bg-muted text-muted-foreground";
}

export default function AuditBackofficePage() {
    const [filters, setFilters] = useState({
        acao: "",
        entidade: "",
        admin_email: "",
        data_inicio: "",
        data_fim: "",
    });
    const [showFilters, setShowFilters] = useState(false);
    const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

    const queryParams = new URLSearchParams();
    if (filters.acao) queryParams.set("acao", filters.acao);
    if (filters.entidade) queryParams.set("entidade", filters.entidade);
    if (filters.admin_email) queryParams.set("admin_email", filters.admin_email);
    if (filters.data_inicio) queryParams.set("data_inicio", filters.data_inicio);
    if (filters.data_fim) queryParams.set("data_fim", filters.data_fim);

    const { data: logs, isLoading } = useQuery<AuditLog[]>({
        queryKey: ["backoffice", "audit", filters],
        queryFn: async () => {
            const response = await apiFetch<{ items?: AuditLog[] }>(`/backoffice/audit?${queryParams.toString()}`);
            return response.items || [];
        },
    });

    const { data: stats } = useQuery<AuditStats>({
        queryKey: ["backoffice", "audit", "stats"],
        queryFn: () => apiFetch("/backoffice/audit/stats"),
    });

    const hasActiveFilters = Object.values(filters).some((v) => v !== "");

    const clearFilters = () => {
        setFilters({ acao: "", entidade: "", admin_email: "", data_inicio: "", data_fim: "" });
    };

    // Extrair valores únicos para os selects de filtro
    const acoesUnicas = stats ? Object.keys(stats.por_acao).sort() : [];
    const entidadesUnicas = stats ? Object.keys(stats.por_entidade).sort() : [];

    // Definição das colunas para o DataTable
    const columns: ColumnDef<AuditLog>[] = [
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            cell: (_, row) => (
                <div className="flex items-center gap-1 justify-end">
                    <Button variant="ghost" size="icon" className="size-7">
                        <ChevronRight className="size-3.5 text-muted-foreground" />
                    </Button>
                </div>
            ),
        },
        {
            id: "created_at",
            header: "Data/Hora",
            accessorKey: "created_at",
            cell: (value) => (
                <div className="flex flex-col">
                    <span className="text-xs font-bold text-foreground">
                        {format(new Date(value), "dd/MM/yy", { locale: ptBR })}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                        {format(new Date(value), "HH:mm:ss")}
                    </span>
                </div>
            ),
            exportFormat: (value) => format(new Date(value), "dd/MM/yyyy HH:mm:ss", { locale: ptBR }),
            sortable: true,
        },
        {
            id: "admin_email",
            header: "Admin",
            accessorKey: "admin_email",
            cell: (value) => <span className="text-xs font-medium text-foreground">{value}</span>,
            sortable: true,
        },
        {
            id: "acao",
            header: "Ação",
            accessorKey: "acao",
            cell: (value) => (
                <Badge className={`text-[9px] font-black uppercase border ${getAcaoColor(value)}`}>
                    {value}
                </Badge>
            ),
            exportFormat: (value) => value,
            sortable: true,
        },
        {
            id: "entidade",
            header: "Entidade",
            accessorKey: "entidade",
            cell: (value) => (
                <Badge variant="outline" className="text-[10px] uppercase font-bold">
                    {value}
                </Badge>
            ),
            sortable: true,
        },
        {
            id: "descricao",
            header: "Descrição",
            accessorKey: "descricao",
            cell: (value) => (
                <span className="text-xs text-muted-foreground line-clamp-1 max-w-xs">
                    {value || "—"}
                </span>
            ),
            sortable: false,
        },
        {
            id: "ip_address",
            header: "IP",
            accessorKey: "ip_address",
            cell: (value) => (
                <span className="text-[10px] font-mono text-muted-foreground">
                    {value || "—"}
                </span>
            ),
            sortable: true,
        },
    ];

    if (isLoading) {
        return (
            <div className="p-8 space-y-6 w-full max-w-full">
                <Skeleton className="h-16 w-full" />
                <div className="grid gap-4 md:grid-cols-3">
                    {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
                </div>
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Logs de Auditoria"
                description="Histórico de todas as ações administrativas na plataforma."
                breadcrumbs={[{ label: "Backoffice" }, { label: "Sistema" }, { label: "Auditoria" }]}
                actions={
                    <Button
                        variant={showFilters ? "secondary" : "outline"}
                        size="sm"
                        onClick={() => setShowFilters(!showFilters)}
                    >
                        <Filter className="size-4 mr-2" />
                        Filtros
                        {hasActiveFilters && (
                            <Badge className="ml-2 bg-primary text-primary-foreground text-[9px] px-1.5">
                                {Object.values(filters).filter((v) => v !== "").length}
                            </Badge>
                        )}
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                            <Activity size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Total de Registros</p>
                            <p className="text-2xl font-black">{stats?.total ?? 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-blue-500">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-600">
                            <User size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Admins Ativos</p>
                            <p className="text-2xl font-black">{stats ? Object.keys(stats.por_admin).length : 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-amber-500">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-600">
                            <Globe size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Tipos de Ação</p>
                            <p className="text-2xl font-black">{stats ? Object.keys(stats.por_acao).length : 0}</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Filters */}
            {showFilters && (
                <Card>
                    <CardContent className="p-4">
                        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
                            <div>
                                <label className="text-xs font-bold text-muted-foreground uppercase mb-1 block">Ação</label>
                                <Select value={filters.acao} onValueChange={(v) => setFilters({ ...filters, acao: v === "all" ? "" : v })}>
                                    <SelectTrigger className="h-9"><SelectValue placeholder="Todas" /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">Todas</SelectItem>
                                        {acoesUnicas.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <label className="text-xs font-bold text-muted-foreground uppercase mb-1 block">Entidade</label>
                                <Select value={filters.entidade} onValueChange={(v) => setFilters({ ...filters, entidade: v === "all" ? "" : v })}>
                                    <SelectTrigger className="h-9"><SelectValue placeholder="Todas" /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">Todas</SelectItem>
                                        {entidadesUnicas.map((e) => <SelectItem key={e} value={e}>{e}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <label className="text-xs font-bold text-muted-foreground uppercase mb-1 block">Admin Email</label>
                                <Input
                                    className="h-9 text-sm"
                                    placeholder="Digite o email..."
                                    value={filters.admin_email}
                                    onChange={(e) => setFilters({ ...filters, admin_email: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="text-xs font-bold text-muted-foreground uppercase mb-1 block">De</label>
                                <Input
                                    type="date"
                                    className="h-9 text-sm"
                                    value={filters.data_inicio}
                                    onChange={(e) => setFilters({ ...filters, data_inicio: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="text-xs font-bold text-muted-foreground uppercase mb-1 block">Até</label>
                                <Input
                                    type="date"
                                    className="h-9 text-sm"
                                    value={filters.data_fim}
                                    onChange={(e) => setFilters({ ...filters, data_fim: e.target.value })}
                                />
                            </div>
                        </div>
                        {hasActiveFilters && (
                            <div className="mt-3 flex justify-end">
                                <Button variant="ghost" size="sm" onClick={clearFilters}>
                                    <X className="size-3.5 mr-1" /> Limpar Filtros
                                </Button>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* DataTable */}
            <DataTable
                data={logs || []}
                columns={columns}
                searchable={true}
                searchPlaceholder="Buscar em logs de auditoria..."
                exportable={true}
                exportFileName="auditoria-backoffice"
                onRowClick={(log) => setSelectedLog(log)}
                rowClassName={() => "group transition-colors hover:bg-muted/10 cursor-pointer"}
                emptyMessage="Nenhum log encontrado."
            />

            {/* Detail Dialog */}
            <Dialog open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
                <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Activity className="size-5" /> Detalhes do Log
                        </DialogTitle>
                    </DialogHeader>

                    {selectedLog && (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase">Data/Hora</p>
                                    <p className="text-sm font-medium">
                                        {format(new Date(selectedLog.created_at), "dd/MM/yyyy 'às' HH:mm:ss", { locale: ptBR })}
                                    </p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase">Admin</p>
                                    <p className="text-sm font-medium">{selectedLog.admin_email}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase">Ação</p>
                                    <Badge className={`text-[10px] font-black uppercase border ${getAcaoColor(selectedLog.acao)}`}>
                                        {selectedLog.acao}
                                    </Badge>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase">Entidade</p>
                                    <Badge variant="outline" className="text-[10px] uppercase font-bold">
                                        {selectedLog.entidade}
                                    </Badge>
                                </div>
                            </div>

                            {selectedLog.descricao && (
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase">Descrição</p>
                                    <p className="text-sm bg-muted/50 p-3 rounded-md">{selectedLog.descricao}</p>
                                </div>
                            )}

                            {selectedLog.entidade_id && (
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase">ID da Entidade</p>
                                    <code className="text-xs font-mono bg-muted px-2 py-1 rounded break-all">
                                        {selectedLog.entidade_id}
                                    </code>
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase flex items-center gap-1">
                                        <Globe className="size-3" /> IP
                                    </p>
                                    <p className="text-sm font-mono">{selectedLog.ip_address || "—"}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase flex items-center gap-1">
                                        <Monitor className="size-3" /> User Agent
                                    </p>
                                    <p className="text-[10px] text-muted-foreground line-clamp-2">{selectedLog.user_agent || "—"}</p>
                                </div>
                            </div>

                            {selectedLog.dados_anteriores && (
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase">Dados Anteriores</p>
                                    <pre className="text-xs bg-red-500/5 border border-red-200 p-3 rounded-sm overflow-x-auto max-h-48">
                                        {JSON.stringify(selectedLog.dados_anteriores, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {selectedLog.dados_novos && (
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-muted-foreground uppercase">Dados Novos</p>
                                    <pre className="text-xs bg-green-500/5 border border-green-200 p-3 rounded-sm overflow-x-auto max-h-48">
                                        {JSON.stringify(selectedLog.dados_novos, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
