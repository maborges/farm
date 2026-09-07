"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useRef, useState } from "react";
import {
    ShieldCheck,
    FileText, UploadCloud, Info,
    Receipt, Landmark, Pencil, X, Check
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ModuloMetadata } from "@/lib/constants/modulos";
import { formatCurrency } from "@/lib/utils";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { toast } from "sonner";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { ChangePlanDialog } from "@/components/billing/change-plan-dialog";
import { useAppStore } from "@/lib/stores/app-store";
import { getModuleName } from "@/lib/constants/planos";

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

interface Props {
    initialTenant: TenantData;
    initialInvoices: TenantInvoice[];
}

function getModuloLabel(moduloId: string) {
    return getModuleName(moduloId);
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

export function TenantSettingsClient({ initialTenant, initialInvoices }: Props) {
    const queryClient = useQueryClient();
    const tenantStore = useAppStore((s) => s.tenant);
    const [editingField, setEditingField] = useState<string | null>(null);
    const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
    const [showChangePlan, setShowChangePlan] = useState(false);

    // Usar initialData para hidratação imediata via TanStack Query
    // Assim respeitamos o Rule 03 (Page RSC -> Client hydrate)
    const [tenant, setTenant] = useState(initialTenant);
    const [invoices] = useState(initialInvoices);

    const updateTenantMutation = useMutation({
        mutationFn: (data: Record<string, string | null>) =>
            apiFetch("/billing/my-account", { method: "PATCH", body: JSON.stringify(data) }) as Promise<TenantData>,
        onSuccess: (updatedData: TenantData) => {
            // Atualiza o estado local e o cache do TanStack Query
            setTenant(updatedData);
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

    const sendProofMutation = useMutation({
        mutationFn: ({ invoiceId, file }: { invoiceId: string; file: File }) => {
            const formData = new FormData();
            formData.append("arquivo", file);
            return apiFetch(`/billing/invoices/${invoiceId}/pay`, {
                method: "POST",
                body: formData,
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenant-invoices"] });
            toast.success("Comprovante enviado para análise!");
        },
        onError: (error: Error) => {
            toast.error(error.message || "Erro ao enviar comprovante.");
        }
    });

    const proofFileInputRef = useRef<HTMLInputElement>(null);
    const [pendingProofInvoiceId, setPendingProofInvoiceId] = useState<string | null>(null);

    function handleProofFileChange(event: React.ChangeEvent<HTMLInputElement>) {
        const file = event.target.files?.[0];
        event.target.value = "";
        if (!file || !pendingProofInvoiceId) return;
        sendProofMutation.mutate({ invoiceId: pendingProofInvoiceId, file });
    }

    function triggerProofUpload(invoiceId: string) {
        setPendingProofInvoiceId(invoiceId);
        proofFileInputRef.current?.click();
    }

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Meu Produtor"
                description="Gerencie o plano, módulos e histórico de pagamentos da sua assinatura."
            />

            <div className="grid gap-6 md:grid-cols-3">
                {/* Informações do Produtor */}
                <Card className="md:col-span-2 overflow-hidden relative border-none shadow-sm">
                    <div className="absolute top-0 right-0 p-8 opacity-5">
                        <Landmark size={120} className="text-primary" />
                    </div>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <Badge variant="outline" className={`rounded-sm uppercase text-[10px] font-bold tracking-wider ${getStatusBadgeClass(tenant?.assinatura?.status)}`}>
                                {tenant?.assinatura?.status || "INATIVA"}
                            </Badge>
                            <span className="text-xs text-muted-foreground font-medium flex items-center gap-1">
                                <ShieldCheck size={14} className="text-emerald-500" /> Conta Verificada
                            </span>
                        </div>
                        <CardTitle className="text-3xl mt-4 font-black">
                            {tenant?.tenant.nome || "Sem Produtor"}
                        </CardTitle>
                        <CardDescription className="text-base font-medium">
                            Plano {tenant?.assinatura?.plano || "Nenhum Ativo"} • {formatCurrency(tenant?.assinatura?.valor || 0)}/mês
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* Campos editáveis */}
                        <div className="space-y-3 pb-4 border-b border-dashed">
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-4">Dados de Identificação</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                                {(["nome", "documento", "email_responsavel", "telefone_responsavel", "idioma_padrao", "logo_url_grupo"] as const).map((field) => {
                                    const labels: Record<string, string> = {
                                        nome: "Nome / Razão Social",
                                        documento: "CPF / CNPJ",
                                        email_responsavel: "E-mail responsável",
                                        telefone_responsavel: "Telefone responsável",
                                        idioma_padrao: "Idioma padrão",
                                        logo_url_grupo: "Logo marca do grupo",
                                    };
                                    // @ts-ignore
                                    const value = tenant?.tenant[field];
                                    const isEditing = editingField === field;
                                    return (
                                        <div key={field} className="flex items-center gap-2 group min-h-[50px]">
                                            <div className="flex-1">
                                                <Label className="text-[10px] uppercase font-bold text-muted-foreground">{labels[field]}</Label>
                                                {isEditing ? (
                                                    <Input
                                                        autoFocus
                                                        value={fieldValues[field] ?? ""}
                                                        onChange={(e) => setFieldValues({ ...fieldValues, [field]: e.target.value })}
                                                        onKeyDown={(e) => { if (e.key === "Enter") saveField(field); if (e.key === "Escape") cancelEdit(); }}
                                                        className="h-8 text-sm mt-1 rounded-sm"
                                                        placeholder={labels[field]}
                                                        type={field === "email_responsavel" ? "email" : field === "logo_url_grupo" ? "url" : "text"}
                                                    />
                                                ) : (
                                                    <p className="text-sm font-semibold text-foreground mt-0.5 break-all">{value || <span className="text-muted-foreground font-normal italic">Não informado</span>}</p>
                                                )}
                                            </div>
                                            {isEditing ? (
                                                <div className="flex gap-1 mt-4">
                                                    <Button size="icon" variant="ghost" className="h-7 w-7 text-emerald-600 hover:bg-emerald-50" onClick={() => saveField(field)} disabled={updateTenantMutation.isPending}>
                                                        <Check size={14} />
                                                    </Button>
                                                    <Button size="icon" variant="ghost" className="h-7 w-7 text-muted-foreground" onClick={cancelEdit}>
                                                        <X size={14} />
                                                    </Button>
                                                </div>
                                            ) : (
                                                <Button size="icon" variant="ghost" className="h-7 w-7 opacity-0 group-hover:opacity-100 mt-4 transition-opacity" onClick={() => startEdit(field, value ?? null)}>
                                                    <Pencil size={13} className="text-primary" />
                                                </Button>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-3 gap-8 py-4 border-y border-dashed">
                            <div>
                                <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Início do Ciclo</p>
                                <p className="text-sm font-bold text-foreground">{tenant?.assinatura ? format(new Date(tenant.assinatura.data_inicio), "dd 'de' MMM, yyyy", { locale: ptBR }) : "--"}</p>
                            </div>
                            <div>
                                <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Próximo Vencimento</p>
                                <p className="text-sm font-black text-primary">
                                    {tenant?.assinatura?.proximo_vencimento ? format(new Date(tenant.assinatura.proximo_vencimento), "dd/MM/yyyy") : "Pendente"}
                                </p>
                            </div>
                            <div>
                                <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Capacidade Usuários</p>
                                <p className="text-sm font-bold">{tenant?.tenant.max_usuarios} Contas Inclusas</p>
                            </div>
                        </div>

                        <div className="space-y-3">
                            <p className="text-xs font-bold uppercase text-muted-foreground tracking-widest">Módulos Licenciados Ativos:</p>
                            <div className="flex flex-wrap gap-2">
                                {tenant?.tenant.modulos_ativos?.map(mod => (
                                    <Badge key={mod} variant="ghost" className="bg-emerald-500/5 border border-emerald-500/10 text-emerald-700 font-bold px-3 py-1 text-[10px] rounded-sm">
                                        {getModuloLabel(mod)}
                                    </Badge>
                                ))}
                            </div>
                        </div>

                        <div className="flex gap-4 pt-4">
                            <Button variant="outline" size="sm" className="gap-2 rounded-sm border-primary/20 hover:bg-primary/5" onClick={() => setShowChangePlan(true)}>
                                Alterar Plano Atual
                            </Button>
                            <Button variant="outline" size="sm" className="rounded-sm text-destructive border-destructive/20 hover:bg-destructive/5">Encerrar Assinatura</Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Info Card */}
                <div className="space-y-6">
                    <Card className="border-l-[4px] border-l-emerald-500 shadow-sm border-none">
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2 font-black">
                                <Info size={18} className="text-emerald-500" /> Notas Financeiras
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="text-sm space-y-4 text-muted-foreground font-medium leading-relaxed">
                            <p>O AgroSaaS utiliza o modelo de pós-pagamento. Suas faturas são geradas no dia 05 de cada mês com base no uso do período anterior.</p>
                            <p>Para manter o acesso liberado, certifique-se de enviar o comprovante de PIX até a data de vencimento.</p>
                            <div className="p-4 bg-muted/30 rounded-sm border border-dashed border-primary/10">
                                <p className="text-[10px] font-black text-primary uppercase mb-1 tracking-tighter">Dados de Pagamento (PIX)</p>
                                <p className="font-mono text-xs font-bold text-foreground">CNPJ: 44.555.666/0001-99</p>
                                <p className="font-mono text-xs mt-1 text-muted-foreground">Banco Cooperativo Agro S.A.</p>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-primary/5 border-none shadow-none">
                        <CardContent className="p-6 flex items-center gap-4">
                            <div className="h-12 w-12 rounded-sm bg-primary/10 flex items-center justify-center text-primary">
                                <Landmark size={24} />
                            </div>
                            <div>
                                <p className="text-xs font-bold uppercase tracking-tight text-primary">Suporte Prioritário</p>
                                <p className="text-[10px] text-muted-foreground">Gerente de Conta disponível.</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Histórico de Faturas */}
            <Card className="border-none shadow-sm overflow-hidden">
                <CardHeader className="bg-muted/10">
                    <CardTitle className="text-xl flex items-center gap-2 font-black">
                        <Receipt className="text-muted-foreground" /> Histórico de Pagamentos
                    </CardTitle>
                    <CardDescription>Consulte suas faturas e envie comprovantes de quitação.</CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                    <input
                        ref={proofFileInputRef}
                        type="file"
                        accept="application/pdf,image/jpeg,image/png"
                        className="hidden"
                        onChange={handleProofFileChange}
                    />
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-muted/5 group-hover:bg-transparent">
                                <TableHead className="font-bold text-[10px] uppercase tracking-wider">Referência</TableHead>
                                <TableHead className="font-bold text-[10px] uppercase tracking-wider">Valor Líquido</TableHead>
                                <TableHead className="font-bold text-[10px] uppercase tracking-wider">Vencimento</TableHead>
                                <TableHead className="font-bold text-[10px] uppercase tracking-wider">Status</TableHead>
                                <TableHead className="text-right font-bold text-[10px] uppercase tracking-wider pr-8">Ação</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {invoices?.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={5} className="text-center py-12 text-muted-foreground italic">
                                        Nenhum registro de faturamento encontrado até o momento.
                                    </TableCell>
                                </TableRow>
                            )}
                            {invoices?.map((inv) => (
                                <TableRow key={inv.id} className="hover:bg-muted/5 transition-colors">
                                    <TableCell className="font-bold text-foreground py-4">{inv.plano_nome}</TableCell>
                                    <TableCell className="font-mono">{formatCurrency(inv.valor)}</TableCell>
                                    <TableCell>{format(new Date(inv.data_vencimento), "dd/MM/yyyy")}</TableCell>
                                    <TableCell>
                                        <Badge variant="outline" className={`
                                            rounded-sm text-[10px] font-black
                                            ${inv.status === 'PAGA' ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20' : ''}
                                            ${inv.status === 'ABERTA' ? 'bg-amber-500/10 text-amber-700 border-amber-500/20' : ''}
                                            ${inv.status === 'EM_ANALISE' ? 'bg-blue-500/10 text-blue-700 border-blue-500/20' : ''}
                                            ${inv.status === 'REJEITADA' ? 'bg-red-500/10 text-red-700 border-red-500/20' : ''}
                                        `}>
                                            {inv.status}
                                        </Badge>
                                        {inv.justificativa_rejeicao && (
                                            <p className="text-[10px] text-red-500 mt-1 italic font-medium max-w-[200px]"> Motivo: {inv.justificativa_rejeicao}</p>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-right pr-8">
                                        {inv.status === "ABERTA" || inv.status === "REJEITADA" ? (
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="gap-2 rounded-sm border-primary/20 h-8"
                                                onClick={() => triggerProofUpload(inv.id)}
                                                disabled={sendProofMutation.isPending}
                                            >
                                                <UploadCloud size={14} /> Enviar Comprovante
                                            </Button>
                                        ) : (
                                            inv.url_comprovante && (
                                                <a
                                                    href={inv.url_comprovante}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors font-medium"
                                                >
                                                    <FileText size={14} /> Ver Recibo
                                                </a>
                                            )
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
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
