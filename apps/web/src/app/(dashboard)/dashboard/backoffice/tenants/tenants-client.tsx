"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import {
    Users,
    Building2,
    ShieldCheck,
    Eye,
    Settings2,
    ChevronRight, ChevronDown,
    Calendar,
    CreditCard,
    MapPin,
    User,
    UserX,
    UserCheck,
    Plus,
    LogIn,
} from "lucide-react";
import { ImpersonateTenantDialog } from "@/components/backoffice/impersonate-tenant-dialog";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter
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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PageHeader } from "@/components/shared/page-header";
import { getModuleName } from "@/lib/constants/planos";
import { ModuloMetadata } from "@/lib/constants/modulos";

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
}

interface FazendaUsuarioDetail {
    id: string;
    nome_completo: string;
    perfil_fazenda?: { nome: string };
}

interface FazendaDetail {
    id: string;
    nome: string;
    cpf_cnpj?: string;
    area_total_ha?: number;
    usuarios: FazendaUsuarioDetail[];
}

interface UsuarioTenantDetail {
    id: string;
    nome_completo: string;
    email: string;
    is_owner: boolean;
    ativo: boolean;
    perfil: { nome: string };
}

interface AssinaturaDetail {
    id: string;
    tipo: string;
    status: string;
    ciclo_pagamento: string;
    data_inicio?: string;
    data_proxima_renovacao?: string;
    plano: { nome: string; preco_mensal: number; preco_anual: number };
    grupo_fazendas?: { nome: string };
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
    assinaturas: AssinaturaDetail[];
    usuarios: UsuarioTenantDetail[];
    estrutura: {
        fazendas_sem_grupo: FazendaDetail[];
    };
}

interface TenantDetailsDialogProps {
    tenantId: string | null;
    onClose: () => void;
    expandedFazendas: Set<string>;
    setExpandedFazendas: (fazendas: Set<string>) => void;
    onImpersonate?: (tenant: { id: string; nome: string; documento?: string | null }) => void;
}

const getModuloLabel = (moduloId: string) => getModuleName(moduloId);

function TenantDetailsDialog({
    tenantId,
    onClose,
    expandedFazendas,
    setExpandedFazendas,
    onImpersonate,
}: TenantDetailsDialogProps) {
    const queryClient = useQueryClient();
    const { data: details, isLoading, error: detailsError } = useQuery({
        queryKey: ["backoffice", "tenant-details", tenantId],
        queryFn: () => apiFetch<TenantDetail>(`/backoffice/tenants/${tenantId}/details`),
        enabled: !!tenantId,
        retry: 1,
    });

    const { data: moduleUsage, error: moduleUsageError } = useQuery<Array<{ module_id: string; total_requests: number; ultimo_acesso: string }>>({
        queryKey: ["backoffice", "module-usage", tenantId],
        queryFn: () => apiFetch(`/backoffice/tenants/${tenantId}/module-usage?days=30`),
        enabled: !!tenantId,
        retry: 1,
    });

    // Log de erros para debug
    if (detailsError) {
        console.error("❌ Erro ao carregar detalhes do tenant:", detailsError);
    }
    if (moduleUsageError) {
        console.error("❌ Erro ao carregar uso de módulos:", moduleUsageError);
    }

    const toggleFazenda = (fazendaId: string) => {
        const newSet = new Set(expandedFazendas);
        if (newSet.has(fazendaId)) {
            newSet.delete(fazendaId);
        } else {
            newSet.add(fazendaId);
        }
        setExpandedFazendas(newSet);
    };

    return (
        <Dialog open={!!tenantId} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[1180px] max-h-[88vh] flex flex-col p-0 gap-0 overflow-hidden bg-background">
                <DialogHeader className="p-6 pb-5 pr-14 border-b bg-muted/20">
                    <div className="flex flex-col gap-4">
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                            <div className="flex flex-col gap-2">
                                <DialogTitle className="flex items-center gap-2 text-xl">
                                    <Building2 className="size-5 text-primary" />
                                    Detalhes do Tenant
                                </DialogTitle>
                                <DialogDescription className="text-xs max-w-2xl">
                                    Visão consolidada da conta, assinaturas, colaboradores e estrutura operacional do tenant.
                                </DialogDescription>
                            </div>
                            {details && (
                                <div className="flex flex-wrap items-center gap-2">
                                    <Badge variant={details.tenant.ativo ? "outline" : "destructive"} className="text-xs">
                                        {details.tenant.ativo ? "CONTA ATIVA" : "CONTA BLOQUEADA"}
                                    </Badge>
                                    <Badge variant="secondary" className="text-xs">
                                        {details.assinaturas.length} assinatura(s)
                                    </Badge>
                                    <Badge variant="secondary" className="text-xs">
                                        {details.usuarios.length} usuário(s)
                                    </Badge>
                                </div>
                            )}
                        </div>

                        {details && (
                            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                                <Card className="rounded-sm border bg-background">
                                    <CardContent className="p-3">
                                        <p className="text-[10px] uppercase text-muted-foreground">Produtor</p>
                                        <p className="truncate text-sm font-semibold">{details.tenant.nome}</p>
                                    </CardContent>
                                </Card>
                                <Card className="rounded-sm border bg-background">
                                    <CardContent className="p-3">
                                        <p className="text-[10px] uppercase text-muted-foreground">Documento</p>
                                        <p className="text-sm font-semibold">{details.tenant.documento}</p>
                                    </CardContent>
                                </Card>
                                <Card className="rounded-sm border bg-background">
                                    <CardContent className="p-3">
                                        <p className="text-[10px] uppercase text-muted-foreground">Fazendas</p>
                                        <p className="text-sm font-semibold">{details.estrutura.fazendas_sem_grupo.length}</p>
                                    </CardContent>
                                </Card>
                                <Card className="rounded-sm border bg-background">
                                    <CardContent className="p-3">
                                        <p className="text-[10px] uppercase text-muted-foreground">Usuários</p>
                                        <p className="text-sm font-semibold">{details.usuarios.length}</p>
                                    </CardContent>
                                </Card>
                            </div>
                        )}
                    </div>
                </DialogHeader>

                {isLoading ? (
                    <div className="p-6 space-y-4">
                        <Skeleton className="h-20 w-full" />
                        <Skeleton className="h-40 w-full" />
                    </div>
                ) : detailsError ? (
                    <div className="p-6 flex flex-col items-center justify-center h-full text-center space-y-4">
                        <div className="h-16 w-16 rounded-full bg-red-500/10 flex items-center justify-center">
                            <UserX className="h-8 w-8 text-red-500" />
                        </div>
                        <div className="space-y-2">
                            <h3 className="text-lg font-semibold">Erro ao carregar detalhes</h3>
                            <p className="text-sm text-muted-foreground max-w-md">
                                {detailsError instanceof Error ? detailsError.message : "Não foi possível carregar os detalhes do tenant. Verifique suas permissões ou tente novamente."}
                            </p>
                            <Button 
                                variant="outline" 
                                className="mt-2"
                                onClick={() => {
                                    queryClient.invalidateQueries({ queryKey: ["backoffice", "tenant-details", tenantId] });
                                    queryClient.invalidateQueries({ queryKey: ["backoffice", "module-usage", tenantId] });
                                }}
                            >
                                Tentar novamente
                            </Button>
                        </div>
                    </div>
                ) : details ? (
                    <Tabs defaultValue="geral" className="flex-1 flex flex-col min-h-0 overflow-hidden">
                        <div className="px-6 border-b bg-background">
                            <TabsList className="bg-transparent h-10 w-full justify-start gap-4 p-0">
                                <TabsTrigger
                                    value="geral"
                                    className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                                >
                                    <Eye className="size-3.5" />
                                    Dados Gerais
                                </TabsTrigger>
                                <TabsTrigger
                                    value="assinaturas"
                                    className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                                >
                                    <CreditCard className="size-3.5" />
                                    Assinaturas ({details?.assinaturas.length || 0})
                                </TabsTrigger>
                                <TabsTrigger
                                    value="usuarios"
                                    className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                                >
                                    <Users className="size-3.5" />
                                    Usuários ({details?.usuarios.length || 0})
                                </TabsTrigger>
                            <TabsTrigger
                                value="estrutura"
                                className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                            >
                                <MapPin className="size-3.5" />
                                Estrutura do Tenant
                            </TabsTrigger>
                                <TabsTrigger
                                    value="modulos"
                                    className="data-[selected]:bg-transparent data-[selected]:border-b-2 data-[selected]:border-primary rounded-none shadow-none h-full px-1 gap-1.5 text-xs"
                                >
                                    <ShieldCheck className="size-3.5" />
                                    Módulos ({details?.tenant.modulos_ativos?.length || 0})
                                </TabsTrigger>
                            </TabsList>
                        </div>

                        <div className="flex-1 overflow-hidden">
                            <TabsContent value="geral" className="h-full m-0 p-6 focus-visible:ring-0">
                                <ScrollArea className="h-full pr-4">
                                    <div className="grid gap-6 pb-10 lg:grid-cols-2">
                                        <Card className="rounded-sm">
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2">
                                                    <User className="size-4 text-primary" />
                                                    Identificação Comercial
                                                </CardTitle>
                                                <CardDescription className="text-xs">
                                                    Dados cadastrais da conta.
                                                </CardDescription>
                                            </CardHeader>
                                            <CardContent className="grid gap-3">
                                                <div className="rounded-sm border bg-muted/20 p-3">
                                                    <Label className="text-[10px] text-muted-foreground uppercase">Nome/Razão Social</Label>
                                                    <p className="text-sm font-medium">{details?.tenant.nome}</p>
                                                </div>
                                                <div className="rounded-sm border bg-muted/20 p-3">
                                                    <Label className="text-[10px] text-muted-foreground uppercase">Documento (CPF/CNPJ)</Label>
                                                    <p className="text-sm font-medium">{details?.tenant.documento}</p>
                                                </div>
                                            </CardContent>
                                        </Card>

                                        <Card className="rounded-sm">
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2">
                                                    <Calendar className="size-4 text-primary" />
                                                    Registro e Controle
                                                </CardTitle>
                                                <CardDescription className="text-xs">
                                                    Datas e identificadores internos.
                                                </CardDescription>
                                            </CardHeader>
                                            <CardContent className="grid gap-3">
                                                <div className="rounded-sm border bg-muted/20 p-3">
                                                    <Label className="text-[10px] text-muted-foreground uppercase">Data de Cadastro</Label>
                                                    <p className="text-sm font-medium">
                                                        {details?.tenant.created_at ? format(new Date(details.tenant.created_at), "dd 'de' MMMM 'de' yyyy", { locale: ptBR }) : '-'}
                                                    </p>
                                                </div>
                                                <div className="rounded-sm border bg-muted/20 p-3">
                                                    <Label className="text-[10px] text-muted-foreground uppercase">ID Interno (UID)</Label>
                                                    <p className="text-[10px] font-mono break-all bg-background p-2 rounded-sm border">
                                                        {details?.tenant.id}
                                                    </p>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    </div>
                                </ScrollArea>
                            </TabsContent>

                            <TabsContent value="assinaturas" className="h-full m-0 p-6 focus-visible:ring-0">
                                <ScrollArea className="h-full pr-4">
                                    <div className="flex flex-col gap-4 pb-10">
                                        {details?.assinaturas.map((assinatura) => (
                                            <Card key={assinatura.id} className="rounded-sm border-l-4 border-l-primary">
                                                <CardContent className="p-4">
                                                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                                                        <div className="flex flex-col gap-2">
                                                            <div className="flex items-center gap-2">
                                                                <Badge variant="secondary" className="text-[9px] font-bold py-0 h-4">
                                                                    {assinatura.tipo}
                                                                </Badge>
                                                                <span className="font-bold text-base capitalize">{assinatura.plano.nome.toLowerCase()}</span>
                                                            </div>
                                                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                                                                <Building2 className="size-3" />
                                                                Escopo: <span className="font-medium text-foreground">Produtor raiz</span>
                                                            </p>
                                                        </div>

                                                        <div className="flex items-start gap-3">
                                                            <div className="rounded-sm border bg-muted/10 px-3 py-2 text-right min-w-[130px]">
                                                                <p className="text-[10px] text-muted-foreground uppercase">Ciclo {assinatura.ciclo_pagamento}</p>
                                                                <p className="font-black text-lg">
                                                                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
                                                                        assinatura.ciclo_pagamento === "MENSAL"
                                                                            ? assinatura.plano.preco_mensal
                                                                            : assinatura.plano.preco_anual
                                                                    )}
                                                                </p>
                                                            </div>
                                                            <div className="px-3 py-2 rounded-sm border bg-muted/10 text-center min-w-[112px]">
                                                                <p className="text-[9px] text-muted-foreground uppercase font-bold">Status</p>
                        <p className={`text-[10px] font-black ${assinatura.status === "ATIVA" ? "text-emerald-700 dark:text-emerald-100" : "text-amber-700 dark:text-amber-100"
                                                                    }`}>{assinatura.status}</p>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <Separator className="my-3" />

                                                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                                        <div>
                                                            <p className="text-[10px] text-muted-foreground font-medium uppercase">Data de Início</p>
                                                            <p className="text-xs font-medium">
                                                                {assinatura.data_inicio ? format(new Date(assinatura.data_inicio), "dd/MM/yyyy") : "N/A"}
                                                            </p>
                                                        </div>
                                                        <div>
                                                            <p className="text-[10px] text-muted-foreground font-medium uppercase">Próxima Renovação</p>
                                                            <p className="text-xs font-black text-blue-700 dark:text-blue-100">
                                                                {assinatura.data_proxima_renovacao ? format(new Date(assinatura.data_proxima_renovacao), "dd/MM/yyyy") : "N/A"}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        ))}
                                    </div>
                                </ScrollArea>
                            </TabsContent>

                            <TabsContent value="usuarios" className="h-full m-0 p-0 focus-visible:ring-0">
                                <div className="flex flex-col h-full">
                                    <div className="px-6 py-4 border-b bg-muted/10 flex items-center justify-between">
                                        <h4 className="text-sm font-semibold flex items-center gap-2">
                                            <Users className="size-4 text-primary" />
                                            Colaboradores da Conta
                                        </h4>
                                        <Badge variant="outline">{details?.usuarios.length || 0} Usuários</Badge>
                                    </div>
                                    <ScrollArea className="flex-1 px-6 pb-10">
                                        <Table>
                                            <TableHeader className="bg-muted/50">
                                                <TableRow>
                                                    <TableHead className="py-2 h-9 text-[10px] uppercase font-bold">Usuário</TableHead>
                                                    <TableHead className="py-2 h-9 text-[10px] uppercase font-bold">Cargo / Perfil</TableHead>
                                                    <TableHead className="py-2 h-9 text-[10px] uppercase font-bold text-center">Status</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {details?.usuarios.map((usuario) => (
                                                    <TableRow key={usuario.id} className="hover:bg-muted/30">
                                                        <TableCell className="py-2">
                                                            <div className="flex flex-col">
                                                                <span className="font-medium text-sm flex items-center gap-2">
                                                                    {usuario.is_owner && <ShieldCheck className="size-3 text-amber-600" />}
                                                                    {usuario.nome_completo}
                                                                </span>
                                                                <span className="text-xs text-muted-foreground">{usuario.email}</span>
                                                            </div>
                                                        </TableCell>
                                                        <TableCell className="py-2">
                                                            <Badge variant="outline" className="text-[10px] font-medium py-0 bg-violet-500/10 text-violet-700 border-violet-200 dark:bg-violet-500/20 dark:text-violet-100 dark:border-violet-400/30">
                                                                {usuario.perfil.nome}
                                                            </Badge>
                                                        </TableCell>
                                                        <TableCell className="py-2 text-center">
                                                            <div className={`size-2 rounded-full mx-auto ${usuario.ativo ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]" : "bg-red-500"
                                                                }`} />
                                                        </TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </ScrollArea>
                                </div>
                            </TabsContent>

                            <TabsContent value="estrutura" className="h-full m-0 p-0 focus-visible:ring-0">
                                <div className="flex flex-col h-full">
                                    <div className="px-6 py-4 border-b bg-muted/10">
                                        <h4 className="text-sm font-semibold flex items-center gap-2">
                                            <MapPin className="size-4 text-primary" />
                                            Tenant como raiz da estrutura
                                        </h4>
                                    </div>
                                    <ScrollArea className="flex-1 p-6">
                                        <div className="space-y-6 pb-10">
                                            <Card className="rounded-sm border-l-4 border-l-primary">
                                                <CardContent className="p-4">
                                                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                                                        <div className="space-y-1">
                                                            <div className="flex items-center gap-2">
                                                                <Building2 className="size-4 text-primary" />
                                                                <p className="text-sm font-semibold">{details?.tenant.nome}</p>
                                                            </div>
                                                            <p className="text-xs text-muted-foreground">
                                                                Tenant raiz da conta • {details?.tenant.documento}
                                                            </p>
                                                        </div>
                                                        <div className="grid grid-cols-3 gap-2 text-center">
                                                            <div className="rounded-sm border bg-muted/10 px-3 py-2">
                                                                <p className="text-[10px] uppercase text-muted-foreground">Fazendas</p>
                                                                <p className="text-sm font-bold text-blue-700 dark:text-blue-100">{details?.estrutura.fazendas_sem_grupo.length || 0}</p>
                                                            </div>
                                                            <div className="rounded-sm border bg-muted/10 px-3 py-2">
                                                                <p className="text-[10px] uppercase text-muted-foreground">Usuários</p>
                                                                <p className="text-sm font-bold text-emerald-700 dark:text-emerald-100">{details?.usuarios.length || 0}</p>
                                                            </div>
                                                            <div className="rounded-sm border bg-muted/10 px-3 py-2">
                                                                <p className="text-[10px] uppercase text-muted-foreground">Assinaturas</p>
                                                                <p className="text-sm font-bold text-amber-700 dark:text-amber-100">{details?.assinaturas.length || 0}</p>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </CardContent>
                                            </Card>

                                            <div className="space-y-3">
                                                <div className="flex items-center justify-between">
                                                    <h4 className="text-sm font-semibold flex items-center gap-2">
                                                        <MapPin className="size-4 text-primary" />
                                                        Fazendas do Tenant
                                                    </h4>
                                                    <Badge variant="outline" className="text-[10px]">
                                                        {details?.estrutura.fazendas_sem_grupo.length || 0}
                                                    </Badge>
                                                </div>
                                                {(details?.estrutura.fazendas_sem_grupo?.length || 0) > 0 ? (
                                                    <div className="space-y-3">
                                                        {details!.estrutura.fazendas_sem_grupo.map((fazenda) => (
                                                            <div key={fazenda.id} className="border rounded-sm overflow-hidden bg-background">
                                                                <button
                                                                    onClick={() => toggleFazenda(fazenda.id)}
                                                                    className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition-colors"
                                                                >
                                                                    <div className="flex items-center gap-3">
                                                <div className="p-1.5 rounded-sm bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-100">
                                                                            <MapPin className="h-4 w-4" />
                                                                        </div>
                                                                        <div className="text-left">
                                                                            <p className="font-bold text-sm">{fazenda.nome}</p>
                                                                            <p className="text-[10px] text-muted-foreground">
                                                                                {fazenda.cpf_cnpj || "Sem CPF/CNPJ"} • {fazenda.area_total_ha?.toFixed(2) || "0"} ha
                                                                            </p>
                                                                        </div>
                                                                    </div>
                                                                    <div className="flex items-center gap-2">
                                                                        <span className="px-2 py-0.5 rounded-sm border text-[9px] font-bold uppercase bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30">
                                                                            {fazenda.usuarios.length} usuários
                                                                        </span>
                                                                        {expandedFazendas.has(fazenda.id) ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                                                                    </div>
                                                                </button>
                                                                {expandedFazendas.has(fazenda.id) && (
                                                                    <div className="px-6 pb-4 pt-2 space-y-2 border-t bg-muted/5">
                                                                        {fazenda.usuarios.length > 0 ? (
                                                                            fazenda.usuarios.map((usu) => (
                                                                                <div key={usu.id} className="flex items-center gap-2 text-xs py-2 bg-background px-3 rounded-sm border">
                                                                                    <User className="h-3.5 w-3.5 text-muted-foreground" />
                                                                                    <span className="font-medium flex-1">{usu.nome_completo}</span>
                                                                                    <Badge variant="secondary" className="text-[9px] py-0 bg-amber-500/10 text-amber-700 border border-amber-200 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30">{usu.perfil_fazenda?.nome || "Operacional"}</Badge>
                                                                                </div>
                                                                            ))
                                                                        ) : (
                                                                            <p className="text-xs text-muted-foreground px-1 py-2">Nenhum usuário vinculado a esta fazenda.</p>
                                                                        )}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div className="rounded-sm border border-dashed p-4 text-sm text-muted-foreground">
                                                        Nenhuma fazenda vinculada a este tenant.
                                                    </div>
                                                )}
                                            </div>

                                            <div className="space-y-3">
                                                <div className="flex items-center justify-between">
                                                    <h4 className="text-sm font-semibold flex items-center gap-2">
                                                        <Users className="size-4 text-primary" />
                                                        Usuários do Tenant
                                                    </h4>
                                                    <Badge variant="outline" className="text-[10px]">
                                                        {details?.usuarios.length || 0}
                                                    </Badge>
                                                </div>
                                                {details?.usuarios.length ? (
                                                    <div className="space-y-2">
                                                        {details.usuarios.map((usuario) => (
                                                            <div key={usuario.id} className="flex items-center justify-between rounded-sm border bg-background px-3 py-2">
                                                                <div className="flex items-center gap-2">
                                                                    <User className="h-3.5 w-3.5 text-muted-foreground" />
                                                                    <div>
                                                                        <p className="text-sm font-medium">{usuario.nome_completo}</p>
                                                                        <p className="text-[10px] text-muted-foreground">{usuario.email}</p>
                                                                    </div>
                                                                </div>
                                                                <div className="flex items-center gap-2">
                                                                    {usuario.is_owner && <Badge variant="secondary" className="text-[9px] py-0 bg-violet-500/10 text-violet-700 border border-violet-200 dark:bg-violet-500/20 dark:text-violet-100 dark:border-violet-400/30">Owner</Badge>}
                                                                    <Badge variant="outline" className="text-[9px] py-0 bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30">{usuario.perfil.nome}</Badge>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div className="rounded-sm border border-dashed p-4 text-sm text-muted-foreground">
                                                        Nenhum usuário ativo neste tenant.
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </ScrollArea>
                                </div>
                            </TabsContent>

                            <TabsContent value="modulos" className="h-full m-0 p-6 focus-visible:ring-0">
                                <ScrollArea className="h-full pr-4">
                                    <div className="space-y-6 pb-10">
                                        {/* Módulos contratados */}
                                        <div>
                                            <div className="flex items-center gap-2 pb-3">
                                                <ShieldCheck className="size-4 text-primary" />
                                                <h4 className="text-sm font-semibold">Módulos Contratados</h4>
                                                <Badge variant="secondary" className="text-[10px]">
                                                    {details?.tenant.modulos_ativos?.length || 0}
                                                </Badge>
                                            </div>
                                            {!details?.tenant.modulos_ativos?.length ? (
                                                <p className="text-sm text-muted-foreground">Nenhum módulo ativo.</p>
                                            ) : (
                                                <div className="flex flex-wrap gap-2">
                                                    {details.tenant.modulos_ativos.map((modId) => {
                                                        const usage = moduleUsage?.find(u => u.module_id === modId);
                                                        return (
                                                            <span
                                                                key={modId}
                                                                title={usage ? `${usage.total_requests} requests (30d) · último: ${usage.ultimo_acesso}` : "Sem uso registrado"}
                                                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-sm border bg-primary/5 text-xs font-medium text-primary border-primary/20 cursor-default"
                                                            >
                                                                <ShieldCheck className={`size-3 ${usage ? "text-emerald-500" : "text-muted-foreground"}`} />
                                                                {getModuloLabel(modId)}
                                                                {usage && (
                                                                    <span className="text-[10px] text-muted-foreground ml-1">{usage.total_requests}r</span>
                                                                )}
                                                            </span>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>

                                        {/* Telemetria de uso — últimos 30 dias */}
                                        {moduleUsage && moduleUsage.length > 0 && (
                                            <div>
                                                <div className="flex items-center gap-2 pb-3">
                                                    <h4 className="text-sm font-semibold">Uso dos Módulos</h4>
                                                    <span className="text-[11px] text-muted-foreground">(últimos 30 dias)</span>
                                                </div>
                                                <div className="space-y-2">
                                                    {moduleUsage.map((u) => {
                                                        const max = moduleUsage[0].total_requests;
                                                        const pct = Math.round((u.total_requests / max) * 100);
                                                        return (
                                                            <div key={u.module_id} className="space-y-1">
                                                                <div className="flex justify-between text-xs">
                                                                    <span className="font-medium">{getModuloLabel(u.module_id)}</span>
                                                                    <span className="text-muted-foreground">{u.total_requests.toLocaleString()} req · {u.ultimo_acesso}</span>
                                                                </div>
                                                                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                                                                    <div className="h-full bg-primary rounded-full" style={{ width: `${pct}%` }} />
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </ScrollArea>
                            </TabsContent>
                        </div>
                    </Tabs>
                ) : null}

                <DialogFooter className="p-6 border-t shrink-0 flex items-center justify-between sm:justify-between">
                    <div>
                        {onImpersonate && details?.tenant && (
                            <Button
                                variant="outline"
                                size="sm"
                                className="gap-1.5 border-emerald-600/50 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/10"
                                onClick={() => {
                                    onImpersonate({
                                        id: details.tenant.id,
                                        nome: details.tenant.nome,
                                        documento: details.tenant.documento,
                                    });
                                    onClose();
                                }}
                            >
                                <LogIn className="h-4 w-4" />
                                Acessar como Assinante
                            </Button>
                        )}
                    </div>
                    <Button variant="outline" size="sm" onClick={onClose}>
                        Fechar Detalhes
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

interface TenantsClientProps {
    initialTenants: Tenant[];
    initialPlans: Plan[];
}

export default function TenantsClient({ initialTenants, initialPlans }: TenantsClientProps) {
    const queryClient = useQueryClient();
    const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
    const [selectedPlanId, setSelectedPlanId] = useState<string>("");
    const [viewTenantId, setViewTenantId] = useState<string | null>(null);
    const [impersonateTarget, setImpersonateTarget] = useState<{ id: string; nome: string; documento?: string | null } | null>(null);
    const [expandedFazendas, setExpandedFazendas] = useState<Set<string>>(new Set());
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
        dias_trial: 15
    });


    const { data: tenants = initialTenants, refetch } = useQuery({
        queryKey: ["backoffice", "tenants"],
        queryFn: () => apiFetch<Tenant[]>("/backoffice/tenants"),
        initialData: initialTenants
    });

    const { data: plans = initialPlans } = useQuery<Plan[]>({
        queryKey: ["backoffice", "plans"],
        queryFn: () => apiFetch<Plan[]>("/backoffice/plans"),
        initialData: initialPlans
    });

    const createTenantMutation = useMutation({
        mutationFn: (data: typeof createFormData) =>
            apiFetch("/backoffice/tenants", {
                method: "POST",
                body: JSON.stringify(data),
                headers: { "Content-Type": "application/json" }
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tenants"] });
            toast.success("Produtor criado com sucesso!");
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
                dias_trial: 15
            });
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao criar produtor")
    });

    const assignPlanMutation = useMutation({
        mutationFn: ({ tenantId, planId }: { tenantId: string; planId: string }) =>
            apiFetch(`/backoffice/tenants/${tenantId}/assign-plan/${planId}`, { method: "POST" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tenants"] });
            toast.success("Plano atualizado com sucesso!");
            setSelectedTenant(null);
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao trocar plano.")
    });

    const toggleStatus = async (id: string) => {
        try {
            await apiFetch(`/backoffice/tenants/${id}/toggle-status`, { method: "POST" });
            toast.success("Status atualizado com sucesso!");
            refetch();
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Erro ao atualizar status.");
        }
    };

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Gestão de Assinantes"
                description="Controle de produtores, assinaturas e acesso do DeepFarms."
                icon={<Building2 className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Assinantes & Tenants" },
                ]}
                actions={
                    <Button size="sm" variant="outline" className="gap-2" onClick={() => setShowCreateDialog(true)}>
                        <Plus className="h-4 w-4" />
                        Novo Assinante
                    </Button>
                }
            />

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="pt-6 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-sm bg-primary/10 flex items-center justify-center text-primary shrink-0">
                            <Building2 size={24} />
                        </div>
                        <div>
                            <p className="text-2xl font-black">{tenants?.length || 0}</p>
                            <p className="text-[10px] uppercase font-bold text-muted-foreground">Total de Contas</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="pt-6 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-sm bg-emerald-500/10 flex items-center justify-center text-emerald-700 shrink-0 dark:bg-emerald-500/20 dark:text-emerald-100">
                            <ShieldCheck size={24} />
                        </div>
                        <div>
                            <p className="text-2xl font-black">{tenants?.filter(t => t.assinatura?.status === "ATIVA").length || 0}</p>
                            <p className="text-[10px] uppercase font-bold text-muted-foreground">Assinaturas Ativas</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="pt-6 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-sm bg-yellow-500/10 flex items-center justify-center text-yellow-600 shrink-0">
                            <Users size={24} />
                        </div>
                        <div>
                            <p className="text-2xl font-black">{tenants?.filter(t => t.assinatura?.status === "PENDENTE").length || 0}</p>
                            <p className="text-[10px] uppercase font-bold text-muted-foreground">Acessos Pendentes</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <DataTable<Tenant>
                data={tenants ?? []}
                searchable
                searchPlaceholder="Buscar por nome, documento, plano..."
                exportable
                exportFileName="assinantes"
                columns={[
                    {
                        id: "nome",
                        header: "Produtor / Empresa",
                        accessorKey: "nome",
                        sortable: true,
                        cell: (_, tenant) => (
                            <div className="flex flex-col">
                                <span className="font-medium">{tenant.nome}</span>
                            </div>
                        ),
                        exportFormat: (_, tenant) => tenant.nome,
                    },
                    {
                        id: "documento",
                        header: "Documento",
                        accessorKey: "documento",
                        sortable: true,
                        cell: (v) => <span className="text-xs">{v}</span>,
                    },
                    {
                        id: "data_cadastro",
                        header: "Cadastro",
                        accessorKey: "data_cadastro",
                        sortable: true,
                        cell: (v) => (
                            <span className="text-xs">
                                {format(new Date(v), "dd/MM/yyyy HH:mm", { locale: ptBR })}
                            </span>
                        ),
                        exportFormat: (v) => format(new Date(v), "dd/MM/yyyy HH:mm", { locale: ptBR }),
                    },
                    {
                        id: "ativo",
                        header: "Status",
                        accessorKey: "ativo",
                        cell: (v) => (
                            <Badge variant={v ? "outline" : "destructive"} className="text-[10px] py-0">
                                {v ? "ATIVO" : "BLOQUEADO"}
                            </Badge>
                        ),
                        exportFormat: (v) => (v ? "ATIVO" : "BLOQUEADO"),
                    },
                    {
                        id: "assinatura",
                        header: "Assinatura",
                        accessorFn: (t) => t.assinatura?.plano ?? "",
                        cell: (_, tenant) => (
                            <Badge variant="secondary" className="w-fit text-[10px] py-0 bg-blue-500/10 text-blue-700 border border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30">
                                {tenant.assinatura?.plano}
                            </Badge>
                        ),
                        exportFormat: (_, tenant) => tenant.assinatura?.plano ?? "",
                    },
                    {
                        id: "acoes",
                        header: "",
                        accessorKey: "id",
                        sortable: false,
                        filterable: false,
                        exportable: false,
                        cell: (_, tenant) => (
                            <div className="flex items-center gap-0 justify-end">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                                    title="Acessar como Assinante (Suporte)"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setImpersonateTarget({ id: tenant.id, nome: tenant.nome, documento: tenant.documento });
                                    }}
                                >
                                    <LogIn className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0"
                                    title="Visualizar"
                                    onClick={(e) => { e.stopPropagation(); setViewTenantId(tenant.id); }}
                                >
                                    <Eye className="h-3.5 w-3.5 text-blue-600" />
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className={`h-7 w-7 p-0 ${tenant.ativo ? "text-red-500" : "text-green-600"}`}
                                    title={tenant.ativo ? "Bloquear" : "Ativar"}
                                    onClick={(e) => { e.stopPropagation(); toggleStatus(tenant.id); }}
                                >
                                    {tenant.ativo ? <UserX className="h-3.5 w-3.5" /> : <UserCheck className="h-3.5 w-3.5" />}
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0"
                                    title="Gerenciar assinatura"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setSelectedTenant(tenant);
                                        setSelectedPlanId(tenant.assinatura?.plano_id || "");
                                    }}
                                >
                                    <Settings2 className="h-3.5 w-3.5 text-muted-foreground" />
                                </Button>
                            </div>
                        ),
                    },
                ] satisfies ColumnDef<Tenant>[]}
            />

            <TenantDetailsDialog
                tenantId={viewTenantId}
                onClose={() => setViewTenantId(null)}
                expandedFazendas={expandedFazendas}
                setExpandedFazendas={setExpandedFazendas}
                onImpersonate={setImpersonateTarget}
            />

            <ImpersonateTenantDialog
                open={!!impersonateTarget}
                onOpenChange={(open) => {
                    if (!open) setImpersonateTarget(null);
                }}
                tenant={impersonateTarget}
            />

            <Dialog open={!!selectedTenant} onOpenChange={() => setSelectedTenant(null)}>
                <DialogContent className="sm:max-w-[760px] max-h-[88vh] overflow-hidden p-0 flex flex-col">
                    <DialogHeader className="border-b p-6 pb-5 pr-14 bg-muted/20">
                        <DialogTitle className="flex items-center gap-2 text-lg">
                            <CreditCard className="size-4 text-primary" />
                            Gestão da Assinatura
                        </DialogTitle>
                        <DialogDescription className="max-w-2xl text-xs">
                            Ajuste o plano comercial do produtor <strong>{selectedTenant?.nome}</strong> e revise o contrato ativo antes de salvar.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 overflow-hidden p-6">
                        <ScrollArea className="h-full pr-4">
                            <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                                <Card className="rounded-sm">
                                    <CardHeader className="pb-3">
                                        <CardTitle className="text-sm">Plano atual</CardTitle>
                                        <CardDescription className="text-xs">
                                            Situação contratual já associada ao produtor.
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="grid gap-3">
                                        <div className="rounded-sm border bg-muted/20 p-3">
                                            <p className="text-[10px] uppercase text-muted-foreground">Plano</p>
                                            <p className="text-sm font-semibold">{selectedTenant?.assinatura?.plano || "Sem plano"}</p>
                                        </div>
                                        <div className="grid gap-3 sm:grid-cols-2">
                                            <div className="rounded-sm border bg-muted/20 p-3">
                                                <p className="text-[10px] uppercase text-muted-foreground">Status</p>
                                                <Badge variant="secondary" className="mt-2 text-[10px]">
                                                    {selectedTenant?.assinatura?.status || "N/A"}
                                                </Badge>
                                            </div>
                                            <div className="rounded-sm border bg-muted/20 p-3">
                                                <p className="text-[10px] uppercase text-muted-foreground">Produtor</p>
                                                <p className="text-sm font-medium">{selectedTenant?.nome}</p>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>

                                <Card className="rounded-sm">
                                    <CardHeader className="pb-3">
                                        <CardTitle className="text-sm">Novo plano</CardTitle>
                                        <CardDescription className="text-xs">
                                            Escolha um novo pacote para aplicar ao produtor.
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="grid gap-3">
                                        <div className="space-y-2">
                                            <Label className="text-xs font-medium">Alterar para</Label>
                                            <Select value={selectedPlanId} onValueChange={setSelectedPlanId}>
                                                <SelectTrigger className="h-10">
                                                    <SelectValue placeholder={selectedPlanId && plans?.find(p => p.id === selectedPlanId)
                                                        ? `${plans.find(p => p.id === selectedPlanId)?.nome} - ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(plans.find(p => p.id === selectedPlanId)?.preco_mensal || 0)}/mês`
                                                        : "Selecione um novo plano"} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {plans?.filter(p => p.ativo).map((plan) => (
                                                        <SelectItem key={plan.id} value={plan.id} className="text-sm">
                                                            {plan.nome} - {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(plan.preco_mensal)}/mês
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        <div className="rounded-sm border border-dashed bg-muted/10 p-3 text-xs text-muted-foreground">
                                            Ao mudar o plano, módulos, limites e telemetria do produtor passam a seguir o contrato selecionado.
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                        </ScrollArea>
                    </div>

                    <DialogFooter className="border-t p-6">
                        <Button variant="outline" onClick={() => setSelectedTenant(null)}>
                            Cancelar
                        </Button>
                        <Button
                            disabled={!selectedPlanId || assignPlanMutation.isPending}
                            onClick={() => assignPlanMutation.mutate({
                                tenantId: selectedTenant!.id,
                                planId: selectedPlanId
                            })}
                        >
                            {assignPlanMutation.isPending ? "Salvando..." : "Salvar Alterações"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogContent className="w-[calc(100vw-1rem)] sm:max-w-5xl max-h-[90vh] overflow-hidden p-0 flex flex-col">
                <DialogHeader className="border-b px-6 py-5">
                    <DialogTitle className="flex items-center gap-2 text-lg">
                        <Building2 className="h-4 w-4 text-primary" />
                        Criar Novo Assinante
                    </DialogTitle>
                    <DialogDescription className="text-xs">
                            Preencha os dados para criar um novo assinante no sistema
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 overflow-y-auto px-6 py-5">
                        <div className="space-y-3">
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
                                            {plans?.filter(p => p.ativo).map((plan) => (
                                                <SelectItem key={plan.id} value={plan.id} className="text-sm">
                                                    {plan.nome} - {new Intl.NumberFormat('pt-BR', {
                                                        style: 'currency',
                                                        currency: 'BRL'
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
                                        id="com_trial"
                                        checked={createFormData.com_trial}
                                        onCheckedChange={(checked) => setCreateFormData({ ...createFormData, com_trial: checked as boolean })}
                                    />
                                    <Label htmlFor="com_trial" className="text-xs">
                                        Iniciar com período de trial ({createFormData.dias_trial} dias)
                                    </Label>
                                </div>
                            </div>
                        </div>
                        </div>
                    </div>

                    <DialogFooter className="border-t px-6 py-5">
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
                            {createTenantMutation.isPending ? "Criando..." : "Criar produtor"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
