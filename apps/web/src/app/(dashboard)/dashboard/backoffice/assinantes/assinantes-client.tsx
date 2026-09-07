"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import {
    Users,
    TrendingUp,
    AlertTriangle,
    CreditCard,
    Eye,
    Power,
    PowerOff,
    CalendarPlus,
    ArrowUpDown,
    Building2,
    ShieldCheck,
    UserX,
    Search,
    X,
    Phone,
    Mail,
    Plus,
} from "lucide-react";
import { toast } from "sonner";
import { format, addDays, differenceInDays } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/ui/status-badge";
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
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

/* ─── TYPES ─── */

interface Plan {
    id: string;
    nome: string;
    preco_mensal: number;
    preco_anual: number;
    ativo: boolean;
}

interface Tenant {
    id: string;
    nome: string;
    documento: string;
    data_cadastro: string;
    ativo: boolean;
    assinatura: {
        plano: string;
        plano_id: string;
        status: string;
    };
    contato_email?: string;
    contato_telefone?: string;
    data_expiracao?: string;
}

interface AssinanteStats {
    total_assinantes: number;
    ativos: number;
    inativos: number;
    vencendo_30d: number;
    receita_mensal: number;
    por_plano: Record<string, number>;
    por_status: Record<string, number>;
}

interface TenantDetail {
    tenant: {
        id: string;
        nome: string;
        documento: string;
        ativo: boolean;
        modulos_ativos: string[];
        created_at: string;
    };
    assinaturas: any[];
    usuarios: any[];
    estrutura: { grupos: any[]; fazendas_sem_grupo: any[] };
}

interface AssinantesClientProps {
    initialTenants: Tenant[];
    initialPlans: Plan[];
    initialStats: AssinanteStats | null;
}

/* ─── FORMATTERS ─── */

const formatCurrency = (value: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);

const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return "-";
    try {
        return format(new Date(dateStr), "dd/MM/yyyy", { locale: ptBR });
    } catch {
        return "-";
    }
};

const getStatusColor = (status: string) => {
    const map: Record<string, { bg: string; text: string; border: string }> = {
        ATIVA: { bg: "bg-emerald-500/10 dark:bg-emerald-500/20", text: "text-emerald-700 dark:text-emerald-100", border: "border-emerald-200 dark:border-emerald-400/30" },
        PENDENTE: { bg: "bg-amber-500/10 dark:bg-amber-500/20", text: "text-amber-700 dark:text-amber-100", border: "border-amber-200 dark:border-amber-400/30" },
        CANCELADA: { bg: "bg-red-500/10 dark:bg-red-500/20", text: "text-red-700 dark:text-red-100", border: "border-red-200 dark:border-red-400/30" },
        VENCIDA: { bg: "bg-orange-500/10 dark:bg-orange-500/20", text: "text-orange-700 dark:text-orange-100", border: "border-orange-200 dark:border-orange-400/30" },
        TESTE: { bg: "bg-blue-500/10 dark:bg-blue-500/20", text: "text-blue-700 dark:text-blue-100", border: "border-blue-200 dark:border-blue-400/30" },
    };
    return map[status] || { bg: "bg-muted dark:bg-zinc-800", text: "text-muted-foreground dark:text-zinc-300", border: "border-muted dark:border-zinc-700" };
};

/* ─── MODALS ─── */

function TenantDetailsDialog({
    tenantId,
    onClose,
}: {
    tenantId: string | null;
    onClose: () => void;
}) {
    const { data: details, isLoading } = useQuery({
        queryKey: ["backoffice", "tenant-details", tenantId],
        queryFn: () =>
            apiFetch<TenantDetail>(`/backoffice/tenants/${tenantId}/details`),
        enabled: !!tenantId,
        retry: 1,
    });

    return (
        <Dialog open={!!tenantId} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[900px] h-[70vh] flex flex-col p-0 gap-0">
                <DialogHeader className="p-6 pb-4 border-b">
                    <div className="flex items-center justify-between">
                        <div className="space-y-1">
                            <DialogTitle className="flex items-center gap-2 text-xl">
                                <Building2 className="size-5 text-primary" />
                                Detalhes do Assinante
                            </DialogTitle>
                            <DialogDescription className="text-xs">
                                Informações completas do tenant e sua estrutura
                            </DialogDescription>
                        </div>
                        {details && (
                            <StatusBadge status={details.tenant.ativo ? "ativo" : "inativo"} />
                        )}
                    </div>
                </DialogHeader>

                {isLoading ? (
                    <div className="p-8 space-y-4">
                        <Skeleton className="h-20 w-full" />
                        <Skeleton className="h-40 w-full" />
                    </div>
                ) : details ? (
                    <Tabs defaultValue="geral" className="flex-1 flex flex-col min-h-0">
                        <div className="px-6 border-b bg-muted/5">
                            <TabsList className="bg-transparent h-10 w-full justify-start gap-4 p-0">
                                <TabsTrigger
                                    value="geral"
                                    className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                                >
                                    Dados Gerais
                                </TabsTrigger>
                                <TabsTrigger
                                    value="assinaturas"
                                    className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                                >
                                    <CreditCard className="size-3.5" />
                                    Assinaturas ({details.assinaturas.length})
                                </TabsTrigger>
                                <TabsTrigger
                                    value="usuarios"
                                    className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                                >
                                    <Users className="size-3.5" />
                                    Usuários ({details.usuarios.length})
                                </TabsTrigger>
                            </TabsList>
                        </div>

                        <ScrollArea className="flex-1">
                            <TabsContent value="geral" className="p-6 focus-visible:ring-0">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-3 rounded-sm border p-4 bg-muted/20">
                                        <Label className="text-[10px] text-muted-foreground uppercase">
                                            Nome / Razão Social
                                        </Label>
                                        <p className="text-sm font-medium">{details.tenant.nome}</p>
                                        <Separator />
                                        <Label className="text-[10px] text-muted-foreground uppercase">
                                            Documento
                                        </Label>
                                        <p className="text-sm font-medium">{details.tenant.documento}</p>
                                    </div>
                                    <div className="space-y-3 rounded-sm border p-4 bg-muted/20">
                                        <Label className="text-[10px] text-muted-foreground uppercase">
                                            Data de Cadastro
                                        </Label>
                                        <p className="text-sm font-medium">
                                            {formatDate(details.tenant.created_at)}
                                        </p>
                                        <Separator />
                                        <Label className="text-[10px] text-muted-foreground uppercase">
                                            Módulos Ativos
                                        </Label>
                                        <div className="flex flex-wrap gap-1.5">
                                            {details.tenant.modulos_ativos.map((m) => (
                                                <Badge key={m} variant="outline" className="text-[10px]">
                                                    {m}
                                                </Badge>
                                            ))}
                                            {!details.tenant.modulos_ativos.length && (
                                                <span className="text-xs text-muted-foreground italic">
                                                    Nenhum módulo contratado
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </TabsContent>

                            <TabsContent value="assinaturas" className="p-6 focus-visible:ring-0">
                                <div className="space-y-4">
                                    {details.assinaturas.length === 0 ? (
                                        <p className="text-sm text-muted-foreground text-center py-8">
                                            Nenhuma assinatura registrada.
                                        </p>
                                    ) : (
                                        details.assinaturas.map((ass: any) => {
                                            const sc = getStatusColor(ass.status);
                                            return (
                                                <Card
                                                    key={ass.id}
                                                    className="rounded-sm border-l-4 border-l-primary"
                                                >
                                                    <CardContent className="p-4">
                                                        <div className="flex items-center justify-between">
                                                            <div>
                                                                <span className="font-bold text-base capitalize">
                                                                    {ass.plano?.nome?.toLowerCase() || "Plano"}
                                                                </span>
                                                                <Badge variant="secondary" className="text-[9px] ml-2 font-bold">
                                                                    {ass.tipo}
                                                                </Badge>
                                                            </div>
                                                            <div className={`px-3 py-1 rounded-sm border text-center ${sc.bg} ${sc.text} ${sc.border}`}>
                                                                <p className="text-[9px] uppercase font-bold">Status</p>
                                                                <p className="text-[10px] font-black">{ass.status}</p>
                                                            </div>
                                                        </div>
                                                        <Separator className="my-3" />
                                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                                                            <div>
                                                                <p className="text-[10px] text-muted-foreground uppercase">Início</p>
                                                                <p className="font-medium">{formatDate(ass.data_inicio)}</p>
                                                            </div>
                                                            <div>
                                                                <p className="text-[10px] text-muted-foreground uppercase">
                                                                    Próx. Renovação
                                                                </p>
                                                                <p className="font-bold text-blue-600">
                                                                    {formatDate(ass.data_proxima_renovacao)}
                                                                </p>
                                                            </div>
                                                            <div>
                                                                <p className="text-[10px] text-muted-foreground uppercase">Ciclo</p>
                                                                <p className="font-medium">{ass.ciclo_pagamento}</p>
                                                            </div>
                                                            <div className="text-right">
                                                                <p className="text-[10px] text-muted-foreground uppercase">Valor</p>
                                                                <p className="font-black text-lg">
                                                                    {formatCurrency(
                                                                        ass.ciclo_pagamento === "MENSAL"
                                                                            ? ass.plano?.preco_mensal
                                                                            : ass.plano?.preco_anual
                                                                    )}
                                                                </p>
                                                            </div>
                                                        </div>
                                                    </CardContent>
                                                </Card>
                                            );
                                        })
                                    )}
                                </div>
                            </TabsContent>

                            <TabsContent value="usuarios" className="p-0 focus-visible:ring-0">
                                <div className="flex flex-col h-full">
                                    <div className="px-6 py-3 border-b bg-muted/10 flex items-center justify-between">
                                        <h4 className="text-sm font-semibold flex items-center gap-2">
                                            <Users className="size-4 text-primary" />
                                            Colaboradores
                                        </h4>
                                        <Badge variant="outline">
                                            {details.usuarios.length}
                                        </Badge>
                                    </div>
                                    <ScrollArea className="flex-1 px-6 pb-4">
                                        {details.usuarios.length === 0 ? (
                                            <p className="text-sm text-muted-foreground text-center py-8">
                                                Nenhum usuário cadastrado.
                                            </p>
                                        ) : (
                                            <div className="space-y-2 py-2">
                                                {details.usuarios.map((u: any) => (
                                                    <div
                                                        key={u.id}
                                                        className="flex items-center justify-between p-3 rounded-sm border bg-background"
                                                    >
                                                        <div className="flex items-center gap-3">
                                                            <Avatar className="size-8 border">
                                                                <AvatarFallback className="text-[10px] bg-primary/5 text-primary">
                                                                    {u.nome_completo?.charAt(0) || "?"}
                                                                </AvatarFallback>
                                                            </Avatar>
                                                            <div>
                                                                <p className="text-sm font-medium flex items-center gap-1.5">
                                                                    {u.is_owner && (
                                                                        <ShieldCheck className="size-3 text-amber-500" />
                                                                    )}
                                                                    {u.nome_completo}
                                                                </p>
                                                                <p className="text-[11px] text-muted-foreground">{u.email}</p>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <Badge variant="outline" className="text-[10px]">
                                                                {u.perfil?.nome || "Membro"}
                                                            </Badge>
                                                            <div
                                                                className={`size-2 rounded-full ${
                                                                    u.ativo
                                                                        ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]"
                                                                        : "bg-red-500"
                                                                }`}
                                                            />
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </ScrollArea>
                                </div>
                            </TabsContent>
                        </ScrollArea>

                        <DialogFooter className="p-6 border-t shrink-0">
                            <Button variant="outline" onClick={onClose}>
                                Fechar
                            </Button>
                        </DialogFooter>
                    </Tabs>
                ) : null}
            </DialogContent>
        </Dialog>
    );
}

function AcaoRapidaDialog({
    tenant,
    action,
    plans,
    onClose,
    onSuccess,
}: {
    tenant: Tenant | null;
    action: "toggle_status" | "trocar_plano" | "add_dias" | null;
    plans: Plan[];
    onClose: () => void;
    onSuccess: () => void;
}) {
    const queryClient = useQueryClient();
    const [selectedPlanoId, setSelectedPlanoId] = useState("");
    const [diasToAdd, setDiasToAdd] = useState("7");

    const isOpen = !!tenant && !!action;

    // Safe access — tenant is guaranteed non-null after this
    const t = tenant!;

    const toggleMutation = useMutation({
        mutationFn: () =>
            apiFetch(`/backoffice/tenants/${t.id}/toggle-status`, {
                method: "PATCH",
            }),
        onSuccess: () => {
            toast.success(`Assinante ${t.ativo ? "bloqueado" : "ativado"} com sucesso!`);
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tenants"] });
            onSuccess();
            onClose();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const trocarPlanoMutation = useMutation({
        mutationFn: () =>
            apiFetch(`/backoffice/tenants/${t.id}/trocar-plano`, {
                method: "PATCH",
                body: JSON.stringify({ plano_id: selectedPlanoId }),
            }),
        onSuccess: () => {
            toast.success("Plano alterado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tenants"] });
            onSuccess();
            onClose();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const addDiasMutation = useMutation({
        mutationFn: () =>
            apiFetch(`/backoffice/tenants/${t.id}/add-dias`, {
                method: "PATCH",
                body: JSON.stringify({ dias: parseInt(diasToAdd) }),
            }),
        onSuccess: () => {
            toast.success(`${diasToAdd} dias adicionados à assinatura!`);
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tenants"] });
            onSuccess();
            onClose();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const handleConfirm = () => {
        if (!tenant) return;
        if (action === "toggle_status") toggleMutation.mutate();
        else if (action === "trocar_plano") trocarPlanoMutation.mutate();
        else if (action === "add_dias") addDiasMutation.mutate();
    };

    const titles: Record<string, string> = {
        toggle_status: tenant?.ativo ? "Bloquear Assinante" : "Ativar Assinante",
        trocar_plano: "Trocar Plano",
        add_dias: "Adicionar Dias de Cortesia",
    };

    const descriptions: Record<string, string> = {
        toggle_status: t?.ativo
            ? `Tem certeza que deseja bloquear o acesso de "${t?.nome}"? O assinante perderá acesso imediato ao sistema.`
            : `Deseja reativar o acesso de "${t?.nome}"? O assinante poderá voltar a usar o sistema normalmente.`,
        trocar_plano: `Selecione o novo plano para "${t?.nome}". A alteração será aplicada imediatamente.`,
        add_dias: `Adicionar dias de cortesia à assinatura de "${t?.nome}". Útil para compensar indisponibilidades.`,
    };

    return (
        <AlertDialog open={isOpen} onOpenChange={onClose}>
            <AlertDialogContent className="w-[calc(100vw-1rem)] sm:max-w-md">
                <AlertDialogHeader>
                    <AlertDialogTitle className="flex items-center gap-2">
                        {action === "toggle_status" &&
                            (tenant?.ativo ? (
                                <PowerOff className="size-5 text-red-500" />
                            ) : (
                                <Power className="size-5 text-green-500" />
                            ))}
                        {action === "trocar_plano" && <ArrowUpDown className="size-5 text-blue-500" />}
                        {action === "add_dias" && <CalendarPlus className="size-5 text-amber-500" />}
                        {titles[action ?? ""] || "Ação"}
                    </AlertDialogTitle>
                    <AlertDialogDescription className="text-sm">
                        {descriptions[action ?? ""]}
                    </AlertDialogDescription>
                </AlertDialogHeader>

                {action === "trocar_plano" && (
                    <div className="space-y-2">
                        <Label className="text-[10px] text-muted-foreground uppercase">
                            Novo Plano
                        </Label>
                        <Select value={selectedPlanoId} onValueChange={setSelectedPlanoId}>
                            <SelectTrigger>
                                <SelectValue placeholder="Selecione um plano..." />
                            </SelectTrigger>
                            <SelectContent>
                                {plans
                                    .filter((p) => p.ativo)
                                    .map((p) => (
                                        <SelectItem key={p.id} value={p.id}>
                                            {p.nome} — {formatCurrency(p.preco_mensal)}/mês
                                        </SelectItem>
                                    ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}

                {action === "add_dias" && (
                    <div className="space-y-2">
                        <Label className="text-[10px] text-muted-foreground uppercase">
                            Quantidade de Dias
                        </Label>
                        <Select value={diasToAdd} onValueChange={setDiasToAdd}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {["3", "7", "15", "30"].map((d) => (
                                    <SelectItem key={d} value={d}>
                                        {d} dias
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}

                <AlertDialogFooter>
                    <AlertDialogCancel>Cancelar</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={handleConfirm}
                        disabled={
                            (action === "trocar_plano" && !selectedPlanoId) ||
                            toggleMutation.isPending ||
                            trocarPlanoMutation.isPending ||
                            addDiasMutation.isPending
                        }
                        className={
                            action === "toggle_status" && tenant?.ativo
                                ? "bg-red-500 hover:bg-red-600"
                                : ""
                        }
                    >
                        {toggleMutation.isPending ||
                        trocarPlanoMutation.isPending ||
                        addDiasMutation.isPending
                            ? "Processando..."
                            : "Confirmar"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}

/* ─── MAIN COMPONENT ─── */

export default function AssinantesClient({
    initialTenants,
    initialPlans,
    initialStats,
}: AssinantesClientProps) {
    const queryClient = useQueryClient();
    const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
    const [selectedTenantDetail, setSelectedTenantDetail] = useState<string | null>(null);
    const [acaoRapida, setAcaoRapida] = useState<
        "toggle_status" | "trocar_plano" | "add_dias" | null
    >(null);
    const [filterPlano, setFilterPlano] = useState<string>("todos");
    const [filterStatus, setFilterStatus] = useState<string>("todos");
    const [showCreateDialog, setShowCreateDialog] = useState(false);
    const [createFormData, setCreateFormData] = useState({
        nome_tenant: "",
        documento: "",
        email_responsavel: "",
        telefone_responsavel: "",
        nome_completo: "",
        username: "",
        email: "",
        senha: "",
        nome_fazenda: "",
        plano_id: "",
        usuarios_contratados: 5,
        ciclo_pagamento: "MENSAL",
        com_trial: true,
        dias_trial: 15,
    });

    const { data: tenantsData, isLoading } = useQuery<Tenant[]>({
        queryKey: ["backoffice", "tenants"],
        queryFn: () => apiFetch<Tenant[]>("/backoffice/tenants"),
        initialData: initialTenants,
        refetchOnWindowFocus: false,
    });

    const tenants = tenantsData ?? [];

    // Computed stats from data if no server stats
    const computedStats = useMemo<AssinanteStats>(() => {
        if (initialStats) return initialStats;
        const ativos = tenants.filter((t) => t.ativo).length;
        return {
            total_assinantes: tenants.length,
            ativos,
            inativos: tenants.length - ativos,
            vencendo_30d: 0,
            receita_mensal: tenants.reduce((acc, t) => {
                const plan = initialPlans?.find((p) => p.id === t.assinatura?.plano_id);
                return acc + (plan?.preco_mensal ?? 0);
            }, 0),
            por_plano: {},
            por_status: {},
        };
    }, [tenants, initialPlans, initialStats]);

    const filteredTenants = useMemo(() => {
        return tenants.filter((t) => {
            if (filterPlano !== "todos" && t.assinatura?.plano_id !== filterPlano)
                return false;
            if (filterStatus !== "todos") {
                const isActive = t.ativo ? "ATIVO" : "INATIVO";
                if (filterStatus !== isActive) return false;
            }
            return true;
        });
    }, [tenants, filterPlano, filterStatus]);

    const createTenantMutation = useMutation({
        mutationFn: (data: typeof createFormData) =>
            apiFetch("/backoffice/tenants", {
                method: "POST",
                body: JSON.stringify(data),
                headers: { "Content-Type": "application/json" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tenants"] });
            toast.success("Assinante criado com sucesso!");
            setShowCreateDialog(false);
            setCreateFormData({
                nome_tenant: "",
                documento: "",
                email_responsavel: "",
                telefone_responsavel: "",
                nome_completo: "",
                username: "",
                email: "",
                senha: "",
                nome_fazenda: "",
                plano_id: "",
                usuarios_contratados: 5,
                ciclo_pagamento: "MENSAL",
                com_trial: true,
                dias_trial: 15,
            });
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao criar assinante"),
    });

    const columns: ColumnDef<Tenant>[] = [
        {
            id: "assinante",
            header: "Assinante",
            accessorFn: (row) => row.nome,
            cell: (value, row) => {
                const initial = row.nome?.charAt(0) || "?";
                const sc = getStatusColor(row.assinatura?.status || "");
                return (
                    <div className="flex items-center gap-3">
                        <Avatar className="size-9 border-2 border-background shadow-sm">
                            <AvatarFallback className="bg-primary/5 text-primary text-xs font-bold">
                                {initial}
                            </AvatarFallback>
                        </Avatar>
                        <div className="flex flex-col">
                            <span className="font-bold text-foreground leading-none flex items-center gap-1.5">
                                {row.nome}
                                {!row.ativo && (
                                    <Badge
                                        variant="outline"
                                        className="text-[9px] h-4 px-1 bg-red-500/5 border-red-500/20 text-red-600 font-black uppercase"
                                    >
                                        Bloqueado
                                    </Badge>
                                )}
                            </span>
                            <span className="text-[11px] text-muted-foreground mt-1">
                                {row.documento}
                            </span>
                        </div>
                    </div>
                );
            },
        },
        {
            id: "plano",
            header: "Plano",
            accessorFn: (row) => row.assinatura?.plano || "-",
            cell: (value) => (
                <Badge variant="secondary" className="text-[10px] font-medium">
                    {value as string}
                </Badge>
            ),
            filterable: true,
            filterPlaceholder: "Filtrar por plano...",
        },
        {
            id: "status",
            header: "Status",
            accessorFn: (row) => (row.ativo ? "ATIVO" : "INATIVO"),
            cell: (value) => (
                <StatusBadge
                    status={(value as string) === "ATIVO" ? "ativo" : "inativo"}
                />
            ),
            filterable: true,
            filterPlaceholder: "Filtrar por status...",
        },
        {
            id: "cadastro",
            header: "Cadastro",
            accessorFn: (row) => row.data_cadastro,
            cell: (value) => (
                <span className="text-xs text-muted-foreground">
                    {formatDate(value as string)}
                </span>
            ),
            sortable: true,
        },
        {
            id: "contato",
            header: "Contato",
            sortable: false,
            filterable: false,
            exportable: false,
            cell: (_, row) => (
                <div className="flex items-center gap-1">
                    {row.contato_email && (
                        <Tooltip>
                            <TooltipTrigger>
                                <Button
                                    variant="ghost"
                                    size="icon-sm"
                                    className="text-muted-foreground hover:text-primary"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        navigator.clipboard.writeText(row.contato_email!);
                                        toast.success("E-mail copiado!");
                                    }}
                                >
                                    <Mail size={14} />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Copiar e-mail</TooltipContent>
                        </Tooltip>
                    )}
                    {row.contato_telefone && (
                        <Tooltip>
                            <TooltipTrigger>
                                <Button
                                    variant="ghost"
                                    size="icon-sm"
                                    className="text-muted-foreground hover:text-primary"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        navigator.clipboard.writeText(row.contato_telefone!);
                                        toast.success("Telefone copiado!");
                                    }}
                                >
                                    <Phone size={14} />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Copiar telefone</TooltipContent>
                        </Tooltip>
                    )}
                </div>
            ),
        },
        {
            id: "acoes",
            header: "",
            sortable: false,
            filterable: false,
            exportable: false,
            cell: (_, row) => (
                <div className="flex items-center gap-1 justify-end">
                    <Tooltip>
                        <TooltipTrigger>
                            <Button
                                variant="ghost"
                                size="icon-sm"
                                className="text-muted-foreground hover:text-primary hover:bg-primary/10"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedTenantDetail(row.id);
                                }}
                            >
                                <Eye size={14} />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>Ver detalhes</TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger>
                            <Button
                                variant="ghost"
                                size="icon-sm"
                                className={`transition-all duration-200 ${
                                    row.ativo
                                        ? "text-muted-foreground hover:text-red-500 hover:bg-red-500/10"
                                        : "text-muted-foreground hover:text-green-500 hover:bg-green-500/10"
                                }`}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedTenant(row);
                                    setAcaoRapida("toggle_status");
                                }}
                            >
                                {row.ativo ? <PowerOff size={14} /> : <Power size={14} />}
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            {row.ativo ? "Bloquear assinante" : "Ativar assinante"}
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger>
                            <Button
                                variant="ghost"
                                size="icon-sm"
                                className="text-muted-foreground hover:text-blue-500 hover:bg-blue-500/10"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedTenant(row);
                                    setAcaoRapida("trocar_plano");
                                }}
                            >
                                <ArrowUpDown size={14} />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>Trocar plano</TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger>
                            <Button
                                variant="ghost"
                                size="icon-sm"
                                className="text-muted-foreground hover:text-amber-500 hover:bg-amber-500/10"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedTenant(row);
                                    setAcaoRapida("add_dias");
                                }}
                            >
                                <CalendarPlus size={14} />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>Adicionar dias de cortesia</TooltipContent>
                    </Tooltip>
                </div>
            ),
        },
    ];

    if (isLoading) {
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
                title="Gestão de Assinantes"
                description="Gerencie os assinantes da plataforma: planos, status, ações comerciais e suporte."
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Comercial", href: "/dashboard/backoffice/assinantes" },
                    { label: "Gestão de Assinantes" },
                ]}
                icon={<Users className="size-6 text-primary" />}
                actions={
                    <Button size="sm" variant="outline" className="gap-2" onClick={() => setShowCreateDialog(true)}>
                        <Plus className="h-4 w-4" />
                        Novo Assinante
                    </Button>
                }
            />

            {/* KPI Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard
                    icon={Users}
                    label="Total Assinantes"
                    value={computedStats.total_assinantes}
                    color="backoffice"
                />
                <StatCard
                    icon={TrendingUp}
                    label="Ativos"
                    value={computedStats.ativos}
                    color="success"
                    subtitle={`${
                        computedStats.total_assinantes > 0
                            ? Math.round(
                                  (computedStats.ativos / computedStats.total_assinantes) * 100
                              )
                            : 0
                    }% do total`}
                />
                <StatCard
                    icon={AlertTriangle}
                    label="Inativos"
                    value={computedStats.inativos}
                    color="warning"
                />
                <StatCard
                    icon={CreditCard}
                    label="Receita Mensal"
                    value={formatCurrency(computedStats.receita_mensal)}
                    color="financeiro"
                    subtitle="MRR estimado"
                />
            </div>

            {/* Filters */}
            <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                    <Label className="text-[10px] text-muted-foreground uppercase font-bold">
                        Plano:
                    </Label>
                    <Select value={filterPlano} onValueChange={setFilterPlano}>
                        <SelectTrigger className="w-[200px] h-8 text-xs">
                            <SelectValue placeholder="Todos os planos" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="todos">Todos os planos</SelectItem>
                            {initialPlans
                                ?.filter((p) => p.ativo)
                                .map((p) => (
                                    <SelectItem key={p.id} value={p.id}>
                                        {p.nome}
                                    </SelectItem>
                                ))}
                        </SelectContent>
                    </Select>
                </div>

                <div className="flex items-center gap-2">
                    <Label className="text-[10px] text-muted-foreground uppercase font-bold">
                        Status:
                    </Label>
                    <Select value={filterStatus} onValueChange={setFilterStatus}>
                        <SelectTrigger className="w-[160px] h-8 text-xs">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="todos">Todos</SelectItem>
                            <SelectItem value="ATIVO">Ativos</SelectItem>
                            <SelectItem value="INATIVO">Inativos</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {(filterPlano !== "todos" || filterStatus !== "todos") && (
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 gap-1 text-xs"
                        onClick={() => {
                            setFilterPlano("todos");
                            setFilterStatus("todos");
                        }}
                    >
                        <X size={12} />
                        Limpar filtros
                    </Button>
                )}
            </div>

            {/* Data Table */}
            <DataTable
                data={filteredTenants}
                columns={columns}
                searchable
                searchPlaceholder="Buscar assinante por nome ou documento..."
                exportable
                exportFileName="assinantes"
                emptyMessage="Nenhum assinante encontrado com os filtros selecionados."
            />

            {/* Dialogs */}
            <TenantDetailsDialog
                tenantId={selectedTenantDetail}
                onClose={() => setSelectedTenantDetail(null)}
            />

            <AcaoRapidaDialog
                tenant={selectedTenant}
                action={acaoRapida}
                plans={initialPlans ?? []}
                onClose={() => {
                    setSelectedTenant(null);
                    setAcaoRapida(null);
                }}
                onSuccess={() => {}}
            />

            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                <DialogContent className="w-[calc(100vw-1rem)] sm:max-w-3xl max-h-[90vh] overflow-hidden p-0">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-lg">
                            <Building2 className="h-4 w-4 text-primary" />
                            Criar Novo Assinante
                        </DialogTitle>
                        <DialogDescription className="text-xs">
                            Preencha os dados para criar um novo assinante no sistema
                        </DialogDescription>
                    </DialogHeader>

                    <div className="max-h-[calc(90vh-6rem)] space-y-3 overflow-y-auto px-4 py-3">
                        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                            <div className="space-y-2 p-3 rounded-sm border bg-muted/20">
                                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Dados da Empresa</h3>

                                <div className="space-y-1.5">
                                    <Label className="text-xs">Nome/Razão Social *</Label>
                                    <Input
                                        placeholder="Ex: Fazendas Boa Vista Ltda"
                                        value={createFormData.nome_tenant}
                                        onChange={(e) => setCreateFormData({ ...createFormData, nome_tenant: e.target.value })}
                                    />
                                </div>

                                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                    <div className="space-y-1.5">
                                        <Label className="text-xs">CPF/CNPJ *</Label>
                                        <Input
                                            placeholder="00.000.000/0000-00"
                                            value={createFormData.documento}
                                            onChange={(e) => setCreateFormData({ ...createFormData, documento: e.target.value })}
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label className="text-xs">Telefone</Label>
                                        <Input
                                            placeholder="(11) 98765-4321"
                                            value={createFormData.telefone_responsavel}
                                            onChange={(e) => setCreateFormData({ ...createFormData, telefone_responsavel: e.target.value })}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <Label className="text-xs">Email da Empresa *</Label>
                                    <Input
                                        type="email"
                                        placeholder="contato@empresa.com.br"
                                        value={createFormData.email_responsavel}
                                        onChange={(e) => setCreateFormData({ ...createFormData, email_responsavel: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2 p-3 rounded-sm border bg-muted/20">
                                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Usuário Proprietário</h3>

                                <div className="space-y-1.5">
                                    <Label className="text-xs">Nome Completo *</Label>
                                    <Input
                                        placeholder="João da Silva"
                                        value={createFormData.nome_completo}
                                        onChange={(e) => setCreateFormData({ ...createFormData, nome_completo: e.target.value })}
                                    />
                                </div>

                                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                    <div className="space-y-1.5">
                                        <Label className="text-xs">Username *</Label>
                                        <Input
                                            placeholder="joao.silva"
                                            value={createFormData.username}
                                            onChange={(e) => setCreateFormData({ ...createFormData, username: e.target.value })}
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label className="text-xs">Email *</Label>
                                        <Input
                                            type="email"
                                            placeholder="joao@empresa.com"
                                            value={createFormData.email}
                                            onChange={(e) => setCreateFormData({ ...createFormData, email: e.target.value })}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <Label className="text-xs">Senha *</Label>
                                    <Input
                                        type="password"
                                        placeholder="Mínimo 6 caracteres"
                                        value={createFormData.senha}
                                        onChange={(e) => setCreateFormData({ ...createFormData, senha: e.target.value })}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                            <div className="space-y-2 p-3 rounded-sm border bg-muted/20">
                                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Primeira Fazenda</h3>
                                <div className="space-y-1.5">
                                    <Label className="text-xs">Nome da Fazenda *</Label>
                                    <Input
                                        placeholder="Fazenda Boa Vista"
                                        value={createFormData.nome_fazenda}
                                        onChange={(e) => setCreateFormData({ ...createFormData, nome_fazenda: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2 p-3 rounded-sm border bg-muted/20">
                                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Assinatura</h3>

                                <div className="space-y-1.5">
                                    <Label className="text-xs">Plano *</Label>
                                    <Select
                                        value={createFormData.plano_id}
                                        onValueChange={(value: string) => setCreateFormData({ ...createFormData, plano_id: value })}
                                    >
                                        <SelectTrigger className="h-7 text-xs">
                                            <SelectValue placeholder="Selecione um plano" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {initialPlans?.filter((p) => p.ativo).map((plan) => (
                                                <SelectItem key={plan.id} value={plan.id} className="text-sm">
                                                    {plan.nome} - {new Intl.NumberFormat("pt-BR", {
                                                        style: "currency",
                                                        currency: "BRL",
                                                    }).format(plan.preco_mensal)}/mês
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                    <div className="space-y-1.5">
                                        <Label className="text-xs">Usuários *</Label>
                                        <Input
                                            type="number"
                                            min="1"
                                            value={createFormData.usuarios_contratados}
                                            onChange={(e) => setCreateFormData({ ...createFormData, usuarios_contratados: parseInt(e.target.value) })}
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label className="text-xs">Ciclo *</Label>
                                        <Select
                                            value={createFormData.ciclo_pagamento}
                                            onValueChange={(value: string) => setCreateFormData({ ...createFormData, ciclo_pagamento: value })}
                                        >
                                            <SelectTrigger className="h-7 text-xs">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="MENSAL" className="text-sm">Mensal</SelectItem>
                                                <SelectItem value="ANUAL" className="text-sm">Anual</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 pt-1">
                                    <Checkbox
                                        id="com_trial_assinantes"
                                        checked={createFormData.com_trial}
                                        onCheckedChange={(checked) => setCreateFormData({ ...createFormData, com_trial: checked as boolean })}
                                    />
                                    <Label htmlFor="com_trial_assinantes" className="text-xs">
                                        Iniciar com período de trial ({createFormData.dias_trial} dias)
                                    </Label>
                                </div>
                            </div>
                        </div>
                    </div>

                    <DialogFooter className="border-t px-4 py-4">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowCreateDialog(false)}
                            disabled={createTenantMutation.isPending}
                        >
                            Cancelar
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => createTenantMutation.mutate(createFormData)}
                            disabled={
                                createTenantMutation.isPending ||
                                !createFormData.nome_tenant ||
                                !createFormData.documento ||
                                !createFormData.email_responsavel ||
                                !createFormData.nome_completo ||
                                !createFormData.username ||
                                !createFormData.email ||
                                !createFormData.senha ||
                                !createFormData.nome_fazenda ||
                                !createFormData.plano_id
                            }
                        >
                            {createTenantMutation.isPending ? "Criando..." : "Criar Assinante"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
