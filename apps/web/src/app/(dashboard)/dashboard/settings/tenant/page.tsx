"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useRef, useState } from "react";
import Link from "next/link";
import {
    ShieldCheck,
    FileText, Info,
    Receipt, Landmark, Pencil, X, Check
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getModuleName } from "@/lib/constants/planos";
import { formatCurrency } from "@/lib/utils";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { toast } from "sonner";
import { ChangePlanDialog } from "@/components/billing/change-plan-dialog";
import { useAppStore } from "@/lib/stores/app-store";
import { getApiOrigin } from "@/lib/runtime-config";

interface TenantData {
    tenant: {
        id: string;
        nome: string;
        documento: string;
        modulos_ativos: string[];
        max_usuarios: number;
        created_at: string;
        email_responsavel: string | null;
        telefone_responsavel: string | null;
        idioma_padrao: string | null;
        logo_url_grupo: string | null;
    };
    assinatura: {
        plano: string;
        valor: number;
        status: string;
        data_inicio: string;
        proximo_vencimento: string | null;
    } | null;
}

interface TenantInvoice {
    id: string;
    plano_nome: string;
    valor: number;
    data_vencimento: string;
    status: string;
    url_comprovante: string | null;
    justificativa_rejeicao: string | null;
}

function getStatusBadgeClass(status?: string | null) {
    switch (status) {
        case "ATIVA":
            return "bg-emerald-600 text-white border-emerald-700";
        case "TRIAL":
            return "bg-sky-600 text-white border-sky-700";
        case "PENDENTE_PAGAMENTO":
            return "bg-amber-500 text-amber-950 border-amber-600";
        case "INATIVA":
            return "bg-slate-600 text-white border-slate-700";
        default:
            return "bg-slate-700 text-white border-slate-800";
    }
}

export default function TenantSettingsPage() {
    const queryClient = useQueryClient();
    const tenantStore = useAppStore((s) => s.tenant);
    const [editingField, setEditingField] = useState<string | null>(null);
    const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
    const [showChangePlan, setShowChangePlan] = useState(false);
    const logoInputRef = useRef<HTMLInputElement | null>(null);

    const { data: tenant, isLoading: isLoadingTenant } = useQuery<TenantData>({
        queryKey: ["tenant-data"],
        queryFn: () => apiFetch("/billing/my-account")
    });

    const { data: invoices, isLoading: isLoadingInvoices } = useQuery<TenantInvoice[]>({
        queryKey: ["tenant-invoices"],
        queryFn: () => apiFetch("/billing/invoices")
    });

    const updateTenantMutation = useMutation({
        mutationFn: (data: Record<string, string | null>) =>
            apiFetch("/billing/my-account", { method: "PATCH", body: JSON.stringify(data) }) as Promise<TenantData>,
        onSuccess: (updatedData: TenantData) => {
            // Atualiza o cache do TanStack Query com os dados completos retornados
            queryClient.setQueryData(["tenant-data"], updatedData);
            if (tenantStore) {
                const branding = { ...(tenantStore.branding ?? {}) };
                if (updatedData.tenant.logo_url_grupo) branding.logoUrl = updatedData.tenant.logo_url_grupo;
                else delete branding.logoUrl;
                useAppStore.setState({
                    tenant: {
                        ...tenantStore,
                        nome: updatedData.tenant.nome,
                        documento: updatedData.tenant.documento,
                        branding: Object.keys(branding).length ? branding : null,
                    },
                });
            }
            setEditingField(null);
            toast.success("Dados atualizados com sucesso!");
        },
        onError: () => toast.error("Erro ao atualizar dados.")
    });

    const uploadLogoMutation = useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append("arquivo", file);
            return apiFetch<{ logo_url_grupo: string }>("/billing/my-account/logo", {
                method: "POST",
                body: formData,
            });
        },
        onSuccess: ({ logo_url_grupo }) => {
            queryClient.setQueryData<TenantData>(["tenant-data"], (current) => {
                if (!current) return current;
                return {
                    ...current,
                    tenant: {
                        ...current.tenant,
                        logo_url_grupo,
                    },
                };
            });
            if (tenantStore) {
                useAppStore.setState({
                    tenant: {
                        ...tenantStore,
                        branding: {
                            ...(tenantStore.branding ?? {}),
                            logoUrl: logo_url_grupo,
                        },
                    },
                });
            }
            toast.success("Logo do grupo atualizada com sucesso!");
        },
        onError: (error: Error) => {
            toast.error(error.message || "Erro ao enviar logo do grupo.");
        },
    });

    function startEdit(field: string, currentValue: string | null) {
        setEditingField(field);
        setFieldValues({ ...fieldValues, [field]: currentValue ?? "" });
    }

    function cancelEdit() {
        setEditingField(null);
    }

    function saveField(field: string) {
        updateTenantMutation.mutate({ [field]: fieldValues[field] || null });
    }

    function resolveLogoUrl(url?: string | null) {
        if (!url) return null;
        if (/^https?:\/\//i.test(url)) return url;
        const origin = getApiOrigin();
        return `${origin}${url.startsWith("/") ? url : `/${url}`}`;
    }

    async function handleLogoFileChange(event: React.ChangeEvent<HTMLInputElement>) {
        const file = event.target.files?.[0];
        event.target.value = "";
        if (!file) return;
        await uploadLogoMutation.mutateAsync(file);
    }

    const groupLogoUrl = resolveLogoUrl(tenant?.tenant.logo_url_grupo);
    const pendingInvoicesCount = (invoices ?? []).filter((inv) => inv.status === "ABERTA" || inv.status === "REJEITADA").length;

    if (isLoadingTenant || isLoadingInvoices) {
        return <div className="p-8 space-y-6"><Skeleton className="h-64 w-full" /><Skeleton className="h-64 w-full" /></div>;
    }

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Meu Produtor"
                description="Gerencie o plano, módulos e histórico de pagamentos da sua assinatura."
            />

            <div className="grid gap-6 md:grid-cols-3">
                {/* Informações do Produtor */}
                <Card className="md:col-span-2 overflow-hidden relative">
                    <div className="absolute top-0 right-0 p-8 opacity-5">
                        <Landmark size={120} className="text-primary" />
                    </div>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <Badge className={`text-xs ${getStatusBadgeClass(tenant?.assinatura?.status)}`}>{tenant?.assinatura?.status || "INATIVA"}</Badge>
                            <span className="text-xs text-muted-foreground font-medium flex items-center gap-1">
                                <ShieldCheck size={14} className="text-green-500" /> Assinatura Ativa
                            </span>
                        </div>
                        <CardTitle className="text-2xl mt-4">
                            {tenant?.tenant.nome || "Sem Produtor"}
                        </CardTitle>
                        <CardDescription>Plano {tenant?.assinatura?.plano || "Nenhum Ativo"} • {formatCurrency(tenant?.assinatura?.valor || 0)}/mês</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* Campos editáveis em grid */}
                        <div className="space-y-4 pb-4 border-b border-dashed">
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Dados do Produtor</p>
                            
                            {/* Linha 1: Nome e Documento */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {(["nome", "documento"] as const).map((field) => {
                                    const labels: Record<string, string> = {
                                        nome: "Nome / Razão Social",
                                        documento: "CPF / CNPJ",
                                    };
                                    const value = tenant?.tenant[field];
                                    const isEditing = editingField === field;
                                    return (
                                        <div key={field} className="space-y-2 group">
                                            <Label className="text-[10px] uppercase font-bold text-muted-foreground">{labels[field]}</Label>
                                            {isEditing ? (
                                                <div className="flex gap-2">
                                                    <Input
                                                        autoFocus
                                                        value={fieldValues[field] ?? ""}
                                                        onChange={(e) => setFieldValues({ ...fieldValues, [field]: e.target.value })}
                                                        onKeyDown={(e) => { if (e.key === "Enter") saveField(field); if (e.key === "Escape") cancelEdit(); }}
                                                        className="h-9 text-sm"
                                                        placeholder={labels[field]}
                                                    />
                                                    <Button size="icon" variant="ghost" className="h-9 w-9 text-emerald-600 hover:bg-emerald-50 shrink-0" onClick={() => saveField(field)} disabled={updateTenantMutation.isPending}>
                                                        <Check size={16} />
                                                    </Button>
                                                    <Button size="icon" variant="ghost" className="h-9 w-9 text-muted-foreground shrink-0" onClick={cancelEdit}>
                                                        <X size={16} />
                                                    </Button>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-2">
                                                    <p className="text-sm font-medium flex-1">{value || <span className="text-muted-foreground italic">Não informado</span>}</p>
                                                    <Button size="icon" variant="ghost" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" onClick={() => startEdit(field, value ?? null)}>
                                                        <Pencil size={13} />
                                                    </Button>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Linha 2: Email e Telefone */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {(["email_responsavel", "telefone_responsavel"] as const).map((field) => {
                                    const labels: Record<string, string> = {
                                        email_responsavel: "E-mail responsável",
                                        telefone_responsavel: "Telefone responsável",
                                    };
                                    const value = tenant?.tenant[field];
                                    const isEditing = editingField === field;
                                    return (
                                        <div key={field} className="space-y-2 group">
                                            <Label className="text-[10px] uppercase font-bold text-muted-foreground">{labels[field]}</Label>
                                            {isEditing ? (
                                                <div className="flex gap-2">
                                                    <Input
                                                        autoFocus
                                                        type={field === "email_responsavel" ? "email" : "tel"}
                                                        value={fieldValues[field] ?? ""}
                                                        onChange={(e) => setFieldValues({ ...fieldValues, [field]: e.target.value })}
                                                        onKeyDown={(e) => { if (e.key === "Enter") saveField(field); if (e.key === "Escape") cancelEdit(); }}
                                                        className="h-9 text-sm"
                                                        placeholder={labels[field]}
                                                    />
                                                    <Button size="icon" variant="ghost" className="h-9 w-9 text-emerald-600 hover:bg-emerald-50 shrink-0" onClick={() => saveField(field)} disabled={updateTenantMutation.isPending}>
                                                        <Check size={16} />
                                                    </Button>
                                                    <Button size="icon" variant="ghost" className="h-9 w-9 text-muted-foreground shrink-0" onClick={cancelEdit}>
                                                        <X size={16} />
                                                    </Button>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-2">
                                                    <p className="text-sm font-medium flex-1">{value || <span className="text-muted-foreground italic">Não informado</span>}</p>
                                                    <Button size="icon" variant="ghost" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" onClick={() => startEdit(field, value ?? null)}>
                                                        <Pencil size={13} />
                                                    </Button>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Linha 3: Idioma + Logo */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2 group">
                                    <Label className="text-[10px] uppercase font-bold text-muted-foreground">Idioma padrão</Label>
                                    {editingField === "idioma_padrao" ? (
                                        <div className="flex gap-2">
                                            <Input
                                                autoFocus
                                                value={fieldValues["idioma_padrao"] ?? ""}
                                                onChange={(e) => setFieldValues({ ...fieldValues, "idioma_padrao": e.target.value })}
                                                onKeyDown={(e) => { if (e.key === "Enter") saveField("idioma_padrao"); if (e.key === "Escape") cancelEdit(); }}
                                                className="h-9 text-sm"
                                                placeholder="Idioma padrão"
                                            />
                                            <Button size="icon" variant="ghost" className="h-9 w-9 text-emerald-600 hover:bg-emerald-50 shrink-0" onClick={() => saveField("idioma_padrao")} disabled={updateTenantMutation.isPending}>
                                                <Check size={16} />
                                            </Button>
                                            <Button size="icon" variant="ghost" className="h-9 w-9 text-muted-foreground shrink-0" onClick={cancelEdit}>
                                                <X size={16} />
                                            </Button>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2">
                                            <p className="text-sm font-medium flex-1">{tenant?.tenant.idioma_padrao || <span className="text-muted-foreground italic">Não informado</span>}</p>
                                            <Button size="icon" variant="ghost" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" onClick={() => startEdit("idioma_padrao", tenant?.tenant.idioma_padrao ?? null)}>
                                                <Pencil size={13} />
                                            </Button>
                                        </div>
                                    )}
                                </div>
                                <div className="space-y-2 group">
                                    <Label className="text-[10px] uppercase font-bold text-muted-foreground">Logo marca do grupo</Label>
                                    <input
                                        ref={logoInputRef}
                                        type="file"
                                        accept="image/png,image/jpeg,image/webp"
                                        className="hidden"
                                        onChange={handleLogoFileChange}
                                    />
                                    <div className="flex items-center gap-3 rounded-lg border border-dashed border-border bg-muted/20 p-3">
                                        <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-background">
                                            {groupLogoUrl ? (
                                                <img
                                                    src={groupLogoUrl}
                                                    alt="Logo do grupo"
                                                    className="h-full w-full object-contain"
                                                />
                                            ) : (
                                                <Landmark size={22} className="text-muted-foreground" />
                                            )}
                                        </div>
                                        <div className="min-w-0 flex-1 space-y-1">
                                            <p className="text-sm font-medium">
                                                {tenant?.tenant.logo_url_grupo ? "Logo carregada" : "Nenhuma logo enviada"}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                PNG, JPG ou WebP com at&eacute; 2MB.
                                            </p>
                                        </div>
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="sm"
                                            className="shrink-0"
                                            onClick={() => logoInputRef.current?.click()}
                                            disabled={uploadLogoMutation.isPending}
                                        >
                                            {uploadLogoMutation.isPending ? "Enviando..." : "Enviar logo"}
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4 border-y border-dashed">
                            <div>
                                <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Início</p>
                                <p className="text-sm font-semibold">{tenant?.assinatura ? format(new Date(tenant.assinatura.data_inicio), "dd MMM yyyy", { locale: ptBR }) : "--"}</p>
                            </div>
                            <div>
                                <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Próximo Vencimento</p>
                                <p className="text-sm font-semibold text-primary">
                                    {tenant?.assinatura?.proximo_vencimento ? format(new Date(tenant.assinatura.proximo_vencimento), "dd/MM/yy") : "Pendente"}
                                </p>
                            </div>
                            <div>
                                <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Usuários</p>
                                <p className="text-sm font-semibold">{tenant?.tenant.max_usuarios} Inclusos</p>
                            </div>
                            <div>
                                <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Status</p>
                                <Badge className={`text-xs ${getStatusBadgeClass(tenant?.assinatura?.status)}`}>{tenant?.assinatura?.status || "INATIVA"}</Badge>
                            </div>
                        </div>

                        <div className="space-y-3">
                            <p className="text-xs font-bold uppercase text-muted-foreground">Módulos Ativos:</p>
                            <div className="flex flex-wrap gap-2">
                                {tenant?.tenant.modulos_ativos?.map(mod => (
                                    <Badge key={mod} variant="ghost" className="bg-primary/5 border-primary/10 text-primary font-medium px-3 py-1">
                                        {getModuleName(mod)}
                                    </Badge>
                                ))}
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <Button variant="outline" size="sm" className="gap-2 rounded-sm" onClick={() => setShowChangePlan(true)}>
                                Alterar Plano
                            </Button>
                            <Button variant="outline" size="sm" className="rounded-sm text-destructive border-destructive/30 hover:bg-destructive/5">Cancelar Assinatura</Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Info Card */}
                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Info size={18} className="text-blue-500" /> Informações de Pagamento
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-4 text-muted-foreground leading-relaxed">
                        <p>O AgroSaaS utiliza o modelo de pós-pagamento. Suas faturas são geradas no dia 05 de cada mês.</p>
                        <p>Para manter o acesso liberado, certifique-se de enviar o comprovante de PIX/Doc até a data de vencimento.</p>
                        <div className="p-4 bg-background rounded-sm border border-primary/5">
                            <p className="text-[10px] font-bold text-primary uppercase mb-1">Dados para Pagamento</p>
                            <p className="font-mono text-xs">PIX CNPJ: 44.555.666/0001-99</p>
                            <p className="font-mono text-xs mt-1 text-foreground">Banco Cooperativo Agro S.A.</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Resumo de Faturamento */}
            <Card className="border-none shadow-sm bg-surface">
                <CardHeader>
                    <CardTitle className="text-xl flex items-center gap-2">
                        <Receipt className="text-muted-foreground" /> Faturamento
                    </CardTitle>
                    <CardDescription>
                        {pendingInvoicesCount > 0
                            ? `Você tem ${pendingInvoicesCount} fatura(s) pendente(s).`
                            : "Nenhuma fatura pendente no momento."}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Button asChild variant="outline" size="sm" className="gap-2 rounded-sm">
                        <Link href="/dashboard/settings/billing">
                            <FileText size={14} /> Ver histórico e enviar comprovantes
                        </Link>
                    </Button>
                </CardContent>
            </Card>

            {/* Diálogo de Alteração de Plano */}
            <ChangePlanDialog
                open={showChangePlan}
                onOpenChange={setShowChangePlan}
                currentTenant={tenant}
            />
        </div>
    );
}
