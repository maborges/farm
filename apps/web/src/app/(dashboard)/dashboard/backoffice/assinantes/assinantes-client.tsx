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
    LogIn,
    Sparkles,
    Calculator,
    Check,
    Cpu,
    Share2,
    Layers,
    ChevronDown,
    ChevronUp,
    Tractor,
    Smartphone,
    Info,
} from "lucide-react";
import {
    FATORES_VOCACAO_HEQ,
    getPacotes,
    calcularOrcamentoLocal,
    obterPacotePorNome,
    mesclarStatusExtensoes,
    type CatalogoModulosStatus,
} from "@/lib/constants/pacotes";
import { ImpersonateTenantDialog } from "@/components/backoffice/impersonate-tenant-dialog";
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
import { Input, PasswordInput } from "@/components/ui/input";
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
    limite_usuarios_minimo?: number;
    limite_usuarios_maximo?: number | null;
    limite_hectares?: number | null;
    dias_trial?: number;
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
        usuarios_contratados?: number;
        ciclo_pagamento?: string;
        extensoes_contratadas?: string[];
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

                        <DialogFooter showCloseButton={false} className="p-6 border-t shrink-0">
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
    const [impersonateTarget, setImpersonateTarget] = useState<{ id: string; nome: string; documento?: string | null } | null>(null);
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
        usuarios_contratados: 1,
        ciclo_pagamento: "MENSAL" as "MENSAL" | "ANUAL",
        extensoes_contratadas: [] as string[],
        com_trial: true,
        dias_trial: 15,
    });

    // Helper state for optional HEq calculator
    const [mostrarCalculadoraHEq, setMostrarCalculadoraHEq] = useState(false);
    const [calcAreaTotal, setCalcAreaTotal] = useState<string>("");
    const [calcAreaAmbiental, setCalcAreaAmbiental] = useState<string>("");
    const [calcVocacao, setCalcVocacao] = useState<keyof typeof FATORES_VOCACAO_HEQ>("GRAOS");
    const [calcCabecasPecuaria, setCalcCabecasPecuaria] = useState<string>("");

    const { data: catalogoModulos } = useQuery<CatalogoModulosStatus>({
        queryKey: ["modulos-catalogo-status"],
        queryFn: async ({ signal }) =>
            await apiFetch<CatalogoModulosStatus>("/billing/modules/catalog", { signal, suppressErrorLog: true }),
        staleTime: 300_000,
        retry: 1,
    });

    const extensoesDisponiveis = useMemo(
        () => mesclarStatusExtensoes(catalogoModulos),
        [catalogoModulos]
    );

    const heqCalculado = useMemo(() => {
        const areaTotalNum = Math.max(0, Number(calcAreaTotal) || 0);
        const areaAmbientalNum = Math.min(areaTotalNum, Math.max(0, Number(calcAreaAmbiental) || 0));
        const areaProdutivaLiquida = Math.max(0, areaTotalNum - areaAmbientalNum);
        const fatorVocacao = FATORES_VOCACAO_HEQ[calcVocacao]?.fator ?? 1.0;

        const heqAgricolaBruto = areaProdutivaLiquida * fatorVocacao;
        const tetoProtecaoFamiliar =
            areaProdutivaLiquida <= 25 && fatorVocacao > 1.0 ? Math.min(heqAgricolaBruto, 100) : heqAgricolaBruto;
        const tetoProtecaoPequeno =
            areaProdutivaLiquida > 25 && areaProdutivaLiquida <= 120 && fatorVocacao > 1.0
                ? Math.min(tetoProtecaoFamiliar, 500)
                : tetoProtecaoFamiliar;

        const cabecasNum = Math.max(0, Math.floor(Number(calcCabecasPecuaria) || 0));
        const lotacaoInclusaCabecas = Math.floor(areaProdutivaLiquida * 2);
        const cabecasExcedentes = Math.max(0, cabecasNum - lotacaoInclusaCabecas);
        const heqPecuariaExcedente = cabecasExcedentes * 0.5;

        return Math.round((tetoProtecaoPequeno + heqPecuariaExcedente) * 100) / 100;
    }, [calcAreaTotal, calcAreaAmbiental, calcVocacao, calcCabecasPecuaria]);

    const planoSugeridoHEq = useMemo(() => {
        if (!heqCalculado || !initialPlans?.length) return null;
        const ativos = initialPlans.filter((p) => p.ativo);
        const pacotesOficiais = getPacotes();
        const pacoteMatch = pacotesOficiais.find(
            (p) => p.limiteHectares === null || p.limiteHectares >= heqCalculado
        );
        if (!pacoteMatch) return null;
        const planoDb = ativos.find((p) =>
            p.nome.toLowerCase().includes(pacoteMatch.nome.toLowerCase().split(" ")[0])
        );
        return planoDb || null;
    }, [heqCalculado, initialPlans]);

    const planoSelecionado = useMemo(() => {
        return initialPlans?.find((p) => p.id === createFormData.plano_id);
    }, [initialPlans, createFormData.plano_id]);

    const pacoteDefSelecionado = useMemo(() => {
        if (!planoSelecionado) return getPacotes()[0];
        return obterPacotePorNome(planoSelecionado.nome) || getPacotes()[0];
    }, [planoSelecionado]);

    const orcamentoCalculado = useMemo(() => {
        if (!pacoteDefSelecionado) return null;
        const extensoesEfetivas = createFormData.extensoes_contratadas.filter((id) =>
            extensoesDisponiveis.some((ext) => ext.id === id && ext.ativo !== false)
        );
        return calcularOrcamentoLocal(
            pacoteDefSelecionado,
            createFormData.usuarios_contratados,
            createFormData.ciclo_pagamento,
            extensoesEfetivas,
            extensoesDisponiveis
        );
    }, [
        pacoteDefSelecionado,
        createFormData.usuarios_contratados,
        createFormData.ciclo_pagamento,
        createFormData.extensoes_contratadas,
        extensoesDisponiveis,
    ]);

    const resetCreateForm = () => {
        const primeiroPlano = initialPlans?.find((p) => p.ativo);
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
            plano_id: primeiroPlano?.id || "",
            usuarios_contratados: primeiroPlano?.limite_usuarios_minimo || 1,
            ciclo_pagamento: "MENSAL",
            extensoes_contratadas: [],
            com_trial: true,
            dias_trial: 15,
        });
        setMostrarCalculadoraHEq(false);
        setCalcAreaTotal("");
        setCalcAreaAmbiental("");
        setCalcVocacao("GRAOS");
        setCalcCabecasPecuaria("");
    };

    const toggleExtensao = (extId: string) => {
        setCreateFormData((prev) => {
            const existe = prev.extensoes_contratadas.includes(extId);
            return {
                ...prev,
                extensoes_contratadas: existe
                    ? prev.extensoes_contratadas.filter((id) => id !== extId)
                    : [...prev.extensoes_contratadas, extId],
            };
        });
    };

    const { data: tenantsData, isLoading } = useQuery<Tenant[]>({
        queryKey: ["backoffice", "tenants"],
        queryFn: () => apiFetch<Tenant[]>("/backoffice/tenants"),
        initialData: initialTenants,
        refetchOnWindowFocus: false,
    });

    const tenants = useMemo(() => tenantsData ?? [], [tenantsData]);

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
            resetCreateForm();
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
            cell: (value, row) => (
                <div className="flex flex-col gap-1 items-start">
                    <Badge variant="secondary" className="text-[10px] font-medium">
                        {value as string}
                    </Badge>
                    {row.assinatura?.extensoes_contratadas && row.assinatura.extensoes_contratadas.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                            {row.assinatura.extensoes_contratadas.map((ext) => (
                                <Badge
                                    key={ext}
                                    variant="outline"
                                    className="text-[9px] h-3.5 px-1 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30"
                                >
                                    +{ext.replace("EXT_", "")}
                                </Badge>
                            ))}
                        </div>
                    )}
                </div>
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
                                className="text-muted-foreground hover:text-emerald-600 hover:bg-emerald-500/10"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setImpersonateTarget({ id: row.id, nome: row.nome, documento: row.documento });
                                }}
                            >
                                <LogIn size={14} />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>Acessar como Assinante (Suporte)</TooltipContent>
                    </Tooltip>

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
            <PageHeader
                title="Gestão de Assinantes"
                description="Gerencie os assinantes da plataforma: planos, status, ações comerciais e suporte."
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Assinantes" },
                ]}
                icon={<Users className="size-6 text-primary" />}
                actions={
                    <Button
                        size="sm"
                        variant="outline"
                        className="gap-2"
                        onClick={() => {
                            resetCreateForm();
                            setShowCreateDialog(true);
                        }}
                    >
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

            <ImpersonateTenantDialog
                open={!!impersonateTarget}
                onOpenChange={(open) => {
                    if (!open) setImpersonateTarget(null);
                }}
                tenant={impersonateTarget}
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
                <DialogContent className="w-[calc(100vw-1rem)] sm:max-w-4xl max-h-[92vh] overflow-hidden p-0 flex flex-col gap-0">
                    <DialogHeader className="px-5 py-3.5 pr-12 border-b bg-muted/10 shrink-0 gap-0">
                        <div className="flex items-center gap-2.5">
                            <div className="p-2 rounded-sm bg-primary/10 text-primary shrink-0">
                                <Building2 className="h-4 w-4" />
                            </div>
                            <div className="min-w-0">
                                <DialogTitle className="flex items-center gap-2 text-base font-semibold">
                                    Criar Novo Assinante
                                    <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30">
                                        Política All-In
                                    </Badge>
                                </DialogTitle>
                                <DialogDescription className="text-xs text-muted-foreground truncate">
                                    100% dos módulos nativos inclusos · Dimensionamento por HEq e usuários web simultâneos
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>

                    <div className="flex-1 overflow-y-auto px-5 py-4">
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
                            {/* COLUNA ESQUERDA: DADOS CADASTRAIS (6 COLS) */}
                            <div className="lg:col-span-6 space-y-3">
                                {/* DADOS DA EMPRESA */}
                                <div className="space-y-2.5 p-3.5 rounded-sm border bg-muted/20">
                                    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                                        <Building2 className="size-3.5 text-primary" />
                                        Dados da Empresa
                                    </h3>

                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-medium text-foreground/90">Razão Social / Nome Fantasia *</Label>
                                        <Input
                                            className="h-8 text-xs rounded-sm"
                                            placeholder="Ex: Fazendas Boa Vista Ltda"
                                            value={createFormData.nome_tenant}
                                            onChange={(e) => setCreateFormData({ ...createFormData, nome_tenant: e.target.value })}
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium text-foreground/90">CPF / CNPJ *</Label>
                                            <Input
                                                className="h-8 text-xs rounded-sm"
                                                placeholder="00.000.000/0000-00"
                                                value={createFormData.documento}
                                                onChange={(e) => setCreateFormData({ ...createFormData, documento: e.target.value })}
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium text-foreground/90">Telefone do Responsável</Label>
                                            <Input
                                                className="h-8 text-xs rounded-sm"
                                                placeholder="(11) 98765-4321"
                                                value={createFormData.telefone_responsavel}
                                                onChange={(e) => setCreateFormData({ ...createFormData, telefone_responsavel: e.target.value })}
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-medium text-foreground/90">Email da Empresa *</Label>
                                        <Input
                                            className="h-8 text-xs rounded-sm"
                                            type="email"
                                            placeholder="contato@empresa.com.br"
                                            value={createFormData.email_responsavel}
                                            onChange={(e) => setCreateFormData({ ...createFormData, email_responsavel: e.target.value })}
                                        />
                                    </div>
                                </div>

                                {/* PRIMEIRA FAZENDA */}
                                <div className="space-y-2.5 p-3.5 rounded-sm border bg-muted/20">
                                    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                                        <Tractor className="size-3.5 text-primary" />
                                        Primeira Fazenda (Unidade Produtiva)
                                    </h3>

                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-medium text-foreground/90">Nome da Propriedade / Fazenda *</Label>
                                        <Input
                                            className="h-8 text-xs rounded-sm"
                                            placeholder="Ex: Fazenda Santa Maria"
                                            value={createFormData.nome_fazenda}
                                            onChange={(e) => setCreateFormData({ ...createFormData, nome_fazenda: e.target.value })}
                                        />
                                    </div>
                                </div>

                                {/* DADOS DO USUÁRIO ADMINISTRADOR */}
                                <div className="space-y-2.5 p-3.5 rounded-sm border bg-muted/20">
                                    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                                        <ShieldCheck className="size-3.5 text-primary" />
                                        Usuário Administrador (Owner)
                                    </h3>

                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-medium text-foreground/90">Nome Completo *</Label>
                                        <Input
                                            className="h-8 text-xs rounded-sm"
                                            placeholder="João da Silva"
                                            value={createFormData.nome_completo}
                                            onChange={(e) => setCreateFormData({ ...createFormData, nome_completo: e.target.value })}
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium text-foreground/90">Username *</Label>
                                            <Input
                                                className="h-8 text-xs rounded-sm"
                                                placeholder="joao.silva"
                                                value={createFormData.username}
                                                onChange={(e) => setCreateFormData({ ...createFormData, username: e.target.value })}
                                            />
                                        </div>
                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium text-foreground/90">Email de Acesso *</Label>
                                            <Input
                                                className="h-8 text-xs rounded-sm"
                                                type="email"
                                                placeholder="joao@empresa.com"
                                                value={createFormData.email}
                                                onChange={(e) => setCreateFormData({ ...createFormData, email: e.target.value })}
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-medium text-foreground/90">Senha Provisória *</Label>
                                        <PasswordInput
                                            className="h-8 text-xs rounded-sm"
                                            placeholder="Mínimo 6 caracteres"
                                            value={createFormData.senha}
                                            onChange={(e) => setCreateFormData({ ...createFormData, senha: e.target.value })}
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* COLUNA DIREITA: CONFIGURAÇÃO COMERCIAL ALL-IN (6 COLS) */}
                            <div className="lg:col-span-6 space-y-3">
                                {/* AUXILIAR HEQ OPCIONAL */}
                                <div className="rounded-sm border bg-muted/20 overflow-hidden">
                                    <button
                                        type="button"
                                        onClick={() => setMostrarCalculadoraHEq(!mostrarCalculadoraHEq)}
                                        className="w-full flex items-center justify-between p-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:bg-muted/30 transition-colors"
                                    >
                                        <span className="flex items-center gap-1.5">
                                            <Calculator className="size-3.5 text-primary" />
                                            Auxiliar de Dimensionamento HEq (Opcional)
                                        </span>
                                        {mostrarCalculadoraHEq ? (
                                            <ChevronUp className="size-3.5" />
                                        ) : (
                                            <ChevronDown className="size-3.5" />
                                        )}
                                    </button>

                                    {mostrarCalculadoraHEq && (
                                        <div className="p-3.5 pt-2 space-y-2.5 border-t bg-card/50">
                                            <div className="grid grid-cols-2 gap-2.5">
                                                <div className="space-y-1.5">
                                                    <Label className="text-[11px] font-medium text-foreground/90">Área Total (ha)</Label>
                                                    <Input
                                                        className="h-8 text-xs rounded-sm"
                                                        type="number"
                                                        placeholder="0"
                                                        value={calcAreaTotal}
                                                        onChange={(e) => setCalcAreaTotal(e.target.value)}
                                                    />
                                                </div>
                                                <div className="space-y-1.5">
                                                    <Label className="text-[11px] font-medium text-foreground/90">APP / Reserva Legal (ha)</Label>
                                                    <Input
                                                        className="h-8 text-xs rounded-sm"
                                                        type="number"
                                                        placeholder="0"
                                                        value={calcAreaAmbiental}
                                                        onChange={(e) => setCalcAreaAmbiental(e.target.value)}
                                                    />
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-2 gap-2.5">
                                                <div className="space-y-1.5">
                                                    <Label className="text-[11px] font-medium text-foreground/90">Vocação Cultural</Label>
                                                    <Select
                                                        value={calcVocacao}
                                                        onValueChange={(val: keyof typeof FATORES_VOCACAO_HEQ) => setCalcVocacao(val)}
                                                    >
                                                        <SelectTrigger className="h-8 text-xs rounded-sm">
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="GRAOS" className="text-xs">Grãos / Anuais (1.0x)</SelectItem>
                                                            <SelectItem value="PASTAGEM" className="text-xs">Pastagem / Pecuária (0.5x)</SelectItem>
                                                            <SelectItem value="CAFE_PERENES" className="text-xs">Café / Perenes / Citros (2.5x)</SelectItem>
                                                            <SelectItem value="HORTIFRUTI" className="text-xs">Hortifrúti / HF (4.0x)</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div className="space-y-1.5">
                                                    <Label className="text-[11px] font-medium text-foreground/90">Rebanho ILP (cabeças)</Label>
                                                    <Input
                                                        className="h-8 text-xs rounded-sm"
                                                        type="number"
                                                        placeholder="0"
                                                        value={calcCabecasPecuaria}
                                                        onChange={(e) => setCalcCabecasPecuaria(e.target.value)}
                                                    />
                                                </div>
                                            </div>

                                            {heqCalculado > 0 && (
                                                <div className="mt-2 p-2.5 rounded-sm bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between gap-2">
                                                    <div className="text-xs min-w-0">
                                                        <span className="font-semibold text-emerald-700 dark:text-emerald-300">
                                                            {heqCalculado.toLocaleString("pt-BR")} ha eq.
                                                        </span>
                                                        {planoSugeridoHEq && (
                                                            <span className="text-muted-foreground ml-1.5">
                                                                → Sugestão: <strong>{planoSugeridoHEq.nome}</strong>
                                                            </span>
                                                        )}
                                                    </div>
                                                    {planoSugeridoHEq && planoSugeridoHEq.id !== createFormData.plano_id && (
                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            type="button"
                                                            className="h-7 text-[11px] px-2.5 rounded-sm shrink-0 border-emerald-500/50 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/20"
                                                            onClick={() => {
                                                                setCreateFormData((prev) => ({
                                                                    ...prev,
                                                                    plano_id: planoSugeridoHEq.id,
                                                                    usuarios_contratados: Math.max(
                                                                        planoSugeridoHEq.limite_usuarios_minimo || 1,
                                                                        prev.usuarios_contratados
                                                                    ),
                                                                }));
                                                            }}
                                                        >
                                                            Aplicar
                                                        </Button>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* PACOTE ALL-IN & ACESSOS */}
                                <div className="space-y-2.5 p-3.5 rounded-sm border bg-muted/20">
                                    <div className="flex items-center justify-between">
                                        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                                            <Layers className="size-3.5 text-primary" />
                                            Pacote All-In & Licenças Web
                                        </h3>
                                        <Badge variant="outline" className="text-[9px] h-4 px-1.5 bg-primary/5 text-primary border-primary/20">
                                            100% módulos nativos
                                        </Badge>
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-medium text-foreground/90">Pacote Comercial *</Label>
                                        <Select
                                            value={createFormData.plano_id}
                                            onValueChange={(val: string) => {
                                                const p = initialPlans?.find((x) => x.id === val);
                                                const minUsers = p?.limite_usuarios_minimo || 1;
                                                setCreateFormData((prev) => ({
                                                    ...prev,
                                                    plano_id: val,
                                                    usuarios_contratados: Math.max(minUsers, prev.usuarios_contratados),
                                                }));
                                            }}
                                        >
                                            <SelectTrigger className="h-8 text-xs rounded-sm">
                                                <SelectValue placeholder="Selecione um pacote" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {initialPlans?.filter((p) => p.ativo).map((plan) => (
                                                    <SelectItem key={plan.id} value={plan.id} className="text-xs">
                                                        {plan.nome} — {formatCurrency(createFormData.ciclo_pagamento === "ANUAL" ? plan.preco_anual : plan.preco_mensal)}/{createFormData.ciclo_pagamento === "ANUAL" ? "ano" : "mês"}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        {pacoteDefSelecionado?.descricaoMarketing && (
                                            <p className="text-[11px] text-muted-foreground">
                                                {pacoteDefSelecionado.descricaoMarketing}
                                            </p>
                                        )}
                                    </div>

                                    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 items-start pt-1">
                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between min-h-[18px]">
                                                <Label className="text-xs font-medium text-foreground/90">Acessos Web Simultâneos *</Label>
                                                {pacoteDefSelecionado && (
                                                    <span className="text-[10px] text-muted-foreground">
                                                        ({pacoteDefSelecionado.usuariosInclusos} inclusos)
                                                    </span>
                                                )}
                                            </div>
                                            <Input
                                                className="h-8 text-xs rounded-sm"
                                                type="number"
                                                min={pacoteDefSelecionado?.usuariosInclusos || 1}
                                                value={createFormData.usuarios_contratados}
                                                onChange={(e) => {
                                                    const val = Math.max(
                                                        pacoteDefSelecionado?.usuariosInclusos || 1,
                                                        parseInt(e.target.value) || 1
                                                    );
                                                    setCreateFormData({ ...createFormData, usuarios_contratados: val });
                                                }}
                                            />
                                            <div className="min-h-[16px]">
                                                {createFormData.usuarios_contratados > (pacoteDefSelecionado?.usuariosInclusos || 1) && (
                                                    <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                                                        +{createFormData.usuarios_contratados - pacoteDefSelecionado.usuariosInclusos} licenças adicionais
                                                    </p>
                                                )}
                                            </div>
                                        </div>

                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between min-h-[18px]">
                                                <Label className="text-xs font-medium text-foreground/90">Ciclo de Cobrança *</Label>
                                            </div>
                                            <Select
                                                value={createFormData.ciclo_pagamento}
                                                onValueChange={(value: "MENSAL" | "ANUAL") =>
                                                    setCreateFormData({ ...createFormData, ciclo_pagamento: value })
                                                }
                                            >
                                                <SelectTrigger className="h-8 text-xs rounded-sm">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="MENSAL" className="text-xs">Mensal</SelectItem>
                                                    <SelectItem value="ANUAL" className="text-xs">
                                                        Anual (2 meses grátis + 20% off adicionais)
                                                    </SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <div className="min-h-[16px]" />
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2 pt-0.5">
                                        <Checkbox
                                            id="com_trial_assinantes"
                                            checked={createFormData.com_trial}
                                            onCheckedChange={(checked) =>
                                                setCreateFormData({ ...createFormData, com_trial: checked as boolean })
                                            }
                                        />
                                        <Label htmlFor="com_trial_assinantes" className="text-xs cursor-pointer font-medium text-foreground/90">
                                            Iniciar com período de trial ({createFormData.dias_trial} dias grátis)
                                        </Label>
                                    </div>
                                    <p className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                                        <Smartphone className="size-3 text-primary shrink-0" />
                                        O aplicativo Campo (celular/offline) é 100% gratuito e não consome acessos simultâneos.
                                    </p>
                                </div>

                                {/* EXTENSÕES OPCIONAIS */}
                                <div className="space-y-2 p-3.5 rounded-sm border bg-muted/20">
                                    <div className="flex items-center justify-between">
                                        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                                            <Sparkles className="size-3.5 text-primary" />
                                            Extensões Opcionais
                                        </h3>
                                        <span className="text-[10px] text-muted-foreground">Contratadas à parte</span>
                                    </div>

                                    <div className="space-y-2">
                                        {extensoesDisponiveis.map((ext) => {
                                            const isAtivo = ext.ativo !== false;
                                            const isSelected = createFormData.extensoes_contratadas.includes(ext.id);
                                            const precoExt =
                                                createFormData.ciclo_pagamento === "ANUAL"
                                                    ? ext.precoAnual
                                                    : ext.precoMensal;

                                            return (
                                                <label
                                                    key={ext.id}
                                                    htmlFor={`ext-check-${ext.id}`}
                                                    className={`p-2.5 rounded-sm border transition-all flex items-start gap-2.5 select-none ${
                                                        !isAtivo
                                                            ? "opacity-60 bg-muted/30 cursor-not-allowed border-dashed"
                                                            : isSelected
                                                            ? "bg-primary/5 border-primary/40 shadow-xs cursor-pointer"
                                                            : "bg-card/50 hover:bg-card border-border cursor-pointer"
                                                    }`}
                                                >
                                                    <Checkbox
                                                        id={`ext-check-${ext.id}`}
                                                        checked={isSelected}
                                                        disabled={!isAtivo}
                                                        onCheckedChange={() => {
                                                            if (isAtivo) toggleExtensao(ext.id);
                                                        }}
                                                        className="mt-0.5 shrink-0"
                                                    />
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center justify-between gap-1.5">
                                                            <span className="text-xs font-semibold text-foreground flex items-center gap-1">
                                                                {ext.id === "EXT_IOT" ? (
                                                                    <Cpu className="size-3 text-primary shrink-0" />
                                                                ) : (
                                                                    <Share2 className="size-3 text-primary shrink-0" />
                                                                )}
                                                                {ext.nome}
                                                            </span>
                                                            {isAtivo ? (
                                                                <span className="text-xs font-bold text-foreground shrink-0">
                                                                    {formatCurrency(precoExt)}/{createFormData.ciclo_pagamento === "ANUAL" ? "ano" : "mês"}
                                                                </span>
                                                            ) : (
                                                                <Badge
                                                                    variant="outline"
                                                                    className="text-[9px] h-3.5 px-1 bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30 uppercase font-bold"
                                                                >
                                                                    Inativo no Catálogo
                                                                </Badge>
                                                            )}
                                                        </div>
                                                        <p className="text-[11px] text-muted-foreground mt-0.5">
                                                            {ext.descricaoCurta}
                                                        </p>
                                                    </div>
                                                </label>
                                            );
                                        })}
                                    </div>
                                </div>

                                {/* RESUMO FINANCEIRO DA CONTRATAÇÃO */}
                                {orcamentoCalculado && (
                                    <div className="space-y-2 p-3.5 rounded-sm border bg-card/80 text-xs shadow-xs">
                                        <div className="flex items-center justify-between text-muted-foreground">
                                            <span>Pacote Base ({pacoteDefSelecionado?.nome}):</span>
                                            <span className="font-medium text-foreground">
                                                {formatCurrency(orcamentoCalculado.valorPacoteBase)}
                                            </span>
                                        </div>

                                        {orcamentoCalculado.usuariosAdicionais > 0 && (
                                            <div className="flex items-center justify-between text-muted-foreground">
                                                <span>Licenças Web Adicionais ({orcamentoCalculado.usuariosAdicionais}x):</span>
                                                <span className="font-medium text-foreground">
                                                    +{formatCurrency(orcamentoCalculado.valorUsuariosAdicionais)}
                                                </span>
                                            </div>
                                        )}

                                        {orcamentoCalculado.valorExtensoes > 0 && (
                                            <div className="flex items-center justify-between text-muted-foreground">
                                                <span>Extensões ({orcamentoCalculado.extensoesSelecionadas.length}):</span>
                                                <span className="font-medium text-foreground">
                                                    +{formatCurrency(orcamentoCalculado.valorExtensoes)}
                                                </span>
                                            </div>
                                        )}

                                        <Separator className="my-1" />

                                        <div className="flex items-center justify-between font-bold text-sm">
                                            <span className="text-foreground">Total ({createFormData.ciclo_pagamento}):</span>
                                            <span className="text-primary text-base font-extrabold">
                                                {formatCurrency(orcamentoCalculado.valorTotal)}
                                            </span>
                                        </div>

                                        {createFormData.ciclo_pagamento === "ANUAL" && (
                                            <div className="text-[11px] text-muted-foreground text-right">
                                                Equivalente a {formatCurrency(orcamentoCalculado.equivalenteMensal)}/mês
                                            </div>
                                        )}

                                        {createFormData.com_trial && (
                                            <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1.5 pt-0.5">
                                                <Check className="size-3.5 shrink-0" />
                                                1ª Cobrança agendada para daqui a {createFormData.dias_trial} dias (após o trial)
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <DialogFooter showCloseButton={false} className="border-t px-5 py-3 bg-muted/10 shrink-0 gap-2 sm:justify-end">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowCreateDialog(false)}
                            disabled={createTenantMutation.isPending}
                            className="h-8 text-xs rounded-sm gap-1.5"
                        >
                            <X className="size-3.5" />
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
                            className="h-8 text-xs rounded-sm gap-1.5 border-primary/50 text-primary hover:bg-primary/10"
                        >
                            <Plus className="size-3.5" />
                            {createTenantMutation.isPending ? "Criando..." : "Criar Assinante"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
