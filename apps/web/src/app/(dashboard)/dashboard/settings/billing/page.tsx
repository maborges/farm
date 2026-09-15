"use client";

import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { PageHeader } from "@/components/shared/page-header";
import { IACommercialAssistantWidget } from "@/components/ia/ia-commercial-assistant-widget";
import { IncentivoGrowthCard } from "@/components/ia/incentivo-growth-card";
import { apiFetch } from "@/lib/api";
import { getCommercialPlanName, normalizePlanTier, getModuleName } from "@/lib/constants/planos";
import { cn, formatCurrency } from "@/lib/utils";
import type { PlanTierId } from "@/types/global";
import {
    ArrowRight,
    Check,
    CreditCard,
    Crown,
    ExternalLink,
    FileText,
    History,
    LifeBuoy,
    Loader2,
    BrainCircuit,
    ShieldCheck,
    Sparkles,
    UploadCloud,
    Zap,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useIAGrowthPlanoRecomendado, useIAGrowthEngineConfig } from "@/hooks";

// ─── Types ─────────────────────────────────────────────────────────────────

interface Plan {
    id: string;
    nome: string;
    descricao: string;
    plan_tier: string;
    modulos_inclusos: string[];
    max_categorias_plano: number;
    preco_mensal: number;
    preco_anual: number;
    limite_usuarios_minimo: number;
    limite_usuarios_maximo: number | null;
    limite_hectares: number | null;
}

interface MyAccount {
    tenant: {
        id: string;
        nome: string;
        modulos_ativos: string[];
        max_usuarios?: number;
        max_categorias_plano?: number;
    };
    assinatura: {
        plano: string;
        valor: number;
        status: string;
        data_inicio: string;
        proximo_vencimento: string | null;
        max_usuarios?: number;
        max_categorias_plano?: number;
    } | null;
}

interface Invoice {
    id: string;
    plano_nome: string;
    valor: number;
    data_vencimento: string;
    status: string;
    created_at: string;
    url_comprovante?: string | null;
    justificativa_rejeicao?: string | null;
}

interface UpgradeResponse {
    message?: string;
    instructions?: string;
    url_pagamento?: string | null;
}

type BillingCycle = "MENSAL" | "ANUAL";
type TierKey = "BASICO" | "PROFISSIONAL" | "ENTERPRISE";

interface FeatureComparisonRow {
    feature: string;
    a1: string;
    profissional: string;
    enterprise: string;
}

// ─── Constants ─────────────────────────────────────────────────────────────

const TIER_ORDER: TierKey[] = ["BASICO", "PROFISSIONAL", "ENTERPRISE"];

const TIER_LABELS: Record<TierKey, string> = {
    BASICO: "Planejamento",
    PROFISSIONAL: "Profissional",
    ENTERPRISE: "Enterprise",
};

const TIER_SUBTITLE: Record<TierKey, string> = {
    BASICO: "Operação agrícola base e leitura.",
    PROFISSIONAL: "Copiloto IA, inteligência executiva, cenários e automação.",
    ENTERPRISE: "Rastreabilidade, assinatura e vendas assistidas.",
};

const FEATURE_COMPARISON: FeatureComparisonRow[] = [
    {
        feature: "Cenários econômicos",
        a1: "Listagem, leitura e cenário base",
        profissional: "Criação, duplicação e comparativo",
        enterprise: "Inclui tudo do PROFISSIONAL",
    },
    {
        feature: "Dashboard executivo",
        a1: "Painel operacional",
        profissional: "KPIs clicáveis e alertas",
        enterprise: "Inclui drill-down e análises avançadas",
    },
    {
        feature: "Templates e automações",
        a1: "Uso manual",
        profissional: "Templates e tarefas guiadas",
        enterprise: "Automação completa com suporte comercial",
    },
    {
        feature: "IA de solo, previsões e relatórios",
        a1: "Consulta básica",
        profissional: "Recomendações, previsões e relatórios",
        enterprise: "Inclui inteligência agrícola do PROFISSIONAL",
    },
    {
        feature: "NDVI e beneficiamento",
        a1: "Não incluso",
        profissional: "Acesso completo",
        enterprise: "Acesso completo",
    },
    {
        feature: "Caderno de campo",
        a1: "Registro operacional",
        profissional: "Registro operacional",
        enterprise: "Exportação e assinatura",
    },
    {
        feature: "Rastreabilidade e VRA",
        a1: "Não incluso",
        profissional: "Não incluso",
        enterprise: "Lotes auditáveis e prescrições",
    },
];

const TIER_FEATURES: Record<TierKey, string[]> = {
    BASICO: [
        "Leitura e operação base da safra",
        "Cenários base e acompanhamento operacional",
        "Checklist, talhões e caderno operacional",
    ],
    PROFISSIONAL: [
        "Copiloto IA com decisão essencial — mostra o que exige atenção agora",
        "Resumo diário inteligente — briefing gerado pela IA toda manhã",
        "Ações assistidas — IA prepara a execução, você só confirma",
        "IA adaptada ao seu perfil — aprende com seu comportamento de decisão",
        "Cenários customizados, comparativos e simulações what-if",
        "IA de solo, previsões, relatórios e alertas",
        "NDVI, templates e beneficiamento",
    ],
    ENTERPRISE: [
        "Exportação e assinatura do caderno",
        "Rastreabilidade e cadeia auditável",
        "VRA e fluxos comerciais assistidos",
    ],
};

const SUPPORT_HREF = "/dashboard/settings/support";

// Deprecated local normalizeTier – using shared normalizePlanTier from constants
// function normalizeTier(value: string | null | undefined): TierKey {
//     if (value === "PROFISSIONAL" || value === "ENTERPRISE") return value;
//     return "BASICO";
// }

function tierPrice(plan: Plan | undefined, cycle: BillingCycle): string {
    if (!plan) return "Sob consulta";
    const price = cycle === "MENSAL" ? plan.preco_mensal : plan.preco_anual / 12;
    return formatCurrency(price);
}

function nextTier(tier: TierKey): TierKey | null {
    if (tier === "BASICO") return "PROFISSIONAL";
    if (tier === "PROFISSIONAL") return "ENTERPRISE";
    return null;
}

function getDisplayedPlanName(plan: Plan | null | undefined, fallbackTier: TierKey): string {
    const rawName = plan?.nome?.trim().toLowerCase() ?? "";
    if (rawName.includes("a1") || rawName.includes("básico") || rawName.includes("basico") || rawName.includes("essencial") || rawName.includes("bronze") || rawName.includes("planejamento")) {
        return "Planejamento";
    }
    if (rawName.includes("pro") || rawName.includes("profissional")) {
        return "Profissional";
    }
    if (rawName.includes("enterprise") || rawName.includes("premium") || rawName.includes("empresa")) {
        return "Enterprise";
    }
    return TIER_LABELS[fallbackTier] || plan?.nome || "Plano";
}

function getDisplayedInvoicePlanName(rawName: string | null | undefined): string {
    const normalized = rawName?.trim().toLowerCase() ?? "";
    if (normalized.includes("enterprise") || normalized.includes("premium") || normalized.includes("empresa") || normalized.includes("empresarial")) {
        return "Enterprise";
    }
    if (normalized.includes("profissional") || normalized === "pro") {
        return "Profissional";
    }
    if (normalized.includes("a1") || normalized.includes("básico") || normalized.includes("basico") || normalized.includes("essencial") || normalized.includes("bronze") || normalized.includes("planejamento")) {
        return "Planejamento";
    }
    return rawName || "Planejamento";
}

function GrowthEngineSection({ config, currentTier }: { config: ReturnType<typeof useIAGrowthEngineConfig>["data"]; currentTier: TierKey }) {
    if (!config) return null;

    const nextTier = currentTier === "BASICO" ? "PROFISSIONAL" : currentTier === "PROFISSIONAL" ? "ENTERPRISE" : null;
    const activeBadge = config.growth_engine_enabled
        ? { label: "Ativo", className: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300" }
        : { label: "Bloqueado", className: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-900/30 dark:text-slate-300" };

    const packageCards = [
        {
            tier: "BASICO" as const,
            title: "Growth Básico",
            subtitle: "Métricas básicas e CTAs simples.",
            icon: ShieldCheck,
            features: ["Métricas básicas", "CTAs simples", "Fallback seguro"],
        },
        {
            tier: "PROFISSIONAL" as const,
            title: "Growth Inteligente",
            subtitle: "Personas, timing e recomendação de plano.",
            icon: BrainCircuit,
            features: ["Personas", "Timing inteligente", "Recomendação de plano", "ROI básico"],
        },
        {
            tier: "ENTERPRISE" as const,
            title: "Growth Autopilot",
            subtitle: "Automação, LLM, incentivos e learning.",
            icon: Zap,
            features: ["Autopilot", "LLM copy", "Incentivos controlados", "Approval flow", "Learning weights", "ROI avançado"],
        },
    ];

    return (
        <div className="space-y-4">
            <Card className="overflow-hidden border border-border/60 rounded-sm shadow-sm">
                <CardHeader className="pb-3 border-b bg-muted/20">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                        <div className="flex items-center gap-2">
                            <Sparkles className="text-primary" />
                            <CardTitle className="text-base font-black uppercase tracking-tight">
                                Configurações do Growth Engine
                            </CardTitle>
                        </div>
                        <Badge variant="outline" className={`rounded-sm text-[10px] font-black uppercase tracking-widest ${activeBadge.className}`}>
                            {activeBadge.label}
                        </Badge>
                    </div>
                    <CardDescription className="text-xs font-medium">
                        Camada comercial controlada por plano e limites por tenant.
                    </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr] p-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-sm border border-border/60 bg-background p-3">
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Plano atual</p>
                            <p className="mt-1 text-sm font-bold">{config.plano_atual_label}</p>
                        </div>
                        <div className="rounded-sm border border-border/60 bg-background p-3">
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Modo</p>
                            <p className="mt-1 text-sm font-bold">{config.growth_modo}</p>
                        </div>
                        <div className="rounded-sm border border-border/60 bg-background p-3">
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Ações por dia</p>
                            <p className="mt-1 text-sm font-bold">{config.growth_max_acoes_dia}</p>
                        </div>
                        <div className="rounded-sm border border-border/60 bg-background p-3">
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Incentivos/mês</p>
                            <p className="mt-1 text-sm font-bold">{config.growth_max_incentivos_mes}</p>
                        </div>
                    </div>
                    <div className="space-y-3">
                        <div className="rounded-sm border border-border/60 bg-muted/20 p-3">
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Recursos disponíveis</p>
                            <div className="mt-2 flex flex-wrap gap-1.5">
                                {config.recursos_disponiveis.map((item) => (
                                    <Badge key={item.chave} variant="secondary" className="rounded-sm text-[10px] font-normal">
                                        {item.label}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                        <div className="rounded-sm border border-border/60 bg-muted/20 p-3">
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Bloqueados no plano atual</p>
                            <div className="mt-2 flex flex-wrap gap-1.5">
                                {config.recursos_bloqueados.map((item) => (
                                    <Badge key={item.chave} variant="outline" className="rounded-sm text-[10px] font-normal">
                                        {item.label}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    </div>
                </CardContent>
                <CardFooter className="flex flex-wrap gap-2 border-t bg-background/50 p-4">
                    <Button asChild variant="outline" size="sm" className="gap-2 rounded-sm font-black uppercase text-[10px]">
                        <Link href={config.cta_upgrade_url}>
                            <ArrowRight size={14} />
                            {nextTier ? `Ver Growth ${TIER_LABELS[nextTier]}` : config.cta_upgrade_label}
                        </Link>
                    </Button>
                    <Button asChild variant="ghost" size="sm" className="gap-2 rounded-sm font-black uppercase text-[10px] text-muted-foreground">
                        <Link href={SUPPORT_HREF}>
                            <LifeBuoy size={14} />
                            Falar com vendas
                        </Link>
                    </Button>
                </CardFooter>
            </Card>

            <div className="grid gap-4 lg:grid-cols-3">
                {packageCards.map((pkg) => {
                    const isCurrent = normalizePlanTier(currentTier) === pkg.tier;
                    const isNext = nextTier === pkg.tier;
                    const Icon = pkg.icon;
                    return (
                        <Card
                            key={pkg.tier}
                            className={cn(
                                "rounded-sm shadow-sm border",
                                isCurrent && "border-primary/40 bg-primary/5",
                                isNext && !isCurrent && "border-primary/30"
                            )}
                        >
                            <CardHeader className="pb-3 border-b bg-muted/15">
                                <div className="flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-2">
                                        <Icon className="text-primary" />
                                        <CardTitle className="text-sm font-black uppercase tracking-tight">{pkg.title}</CardTitle>
                                    </div>
                                    {isCurrent ? <Badge variant="secondary" className="rounded-sm text-[10px] font-black uppercase">Atual</Badge> : null}
                                </div>
                                <CardDescription className="text-xs font-medium">{pkg.subtitle}</CardDescription>
                            </CardHeader>
                            <CardContent className="p-4 space-y-2">
                                {pkg.features.map((feature) => (
                                    <div key={feature} className="flex items-start gap-2 text-[11px] font-medium leading-tight">
                                        <Check className="mt-0.5 size-3 text-emerald-600 shrink-0" />
                                        <span>{feature}</span>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
}

// ─── Page ──────────────────────────────────────────────────────────────────

export default function BillingPage() {
    const queryClient = useQueryClient();
    const [cycle, setCycle] = useState<BillingCycle>("MENSAL");

    // -- Data Fetching
    const { data: account, isLoading: isLoadingAccount } = useQuery<MyAccount>({
        queryKey: ["billing", "account"],
        queryFn: () => apiFetch("/billing/my-account")
    });

    const { data: plans, isLoading: isLoadingPlans } = useQuery<Plan[]>({
        queryKey: ["billing", "plans"],
        queryFn: () => apiFetch("/billing/plans")
    });
    const { data: growthPlano } = useIAGrowthPlanoRecomendado();
    const { data: growthEngineConfig } = useIAGrowthEngineConfig();

    const { data: invoices } = useQuery<Invoice[]>({
        queryKey: ["billing", "invoices"],
        queryFn: () => apiFetch("/billing/invoices")
    });

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
            queryClient.invalidateQueries({ queryKey: ["billing", "invoices"] });
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

    const upgradeMutation = useMutation<UpgradeResponse, Error, string>({
        mutationFn: (planId: string) => apiFetch("/billing/upgrade", {
            method: "POST",
            body: JSON.stringify({ plan_id: planId })
        }),
        onSuccess: (data) => {
            toast.success(data.message ?? "Solicitação criada com sucesso.", {
                description: data.instructions,
            });
            if (data.url_pagamento) {
                window.open(data.url_pagamento, "_blank");
            }
            queryClient.invalidateQueries({ queryKey: ["billing"] });
        },
        onError: (e) => toast.error(e.message)
    });

    if (isLoadingAccount || isLoadingPlans) {
        return (
            <div className="p-6 flex flex-col gap-6">
                <Skeleton className="h-10 w-64 rounded-sm" />
                <Skeleton className="h-36 w-full rounded-sm" />
                <Skeleton className="h-72 w-full rounded-sm" />
            </div>
        );
    }

    const currentPlanName = account?.assinatura?.plano || "Planejamento";
    const currentPlan = plans?.find((plan) => plan.nome === currentPlanName) ?? null;
    const currentTier = (account?.assinatura ? normalizePlanTier(currentPlan?.plan_tier as PlanTierId) : "BASICO") as TierKey;
    const upgradeTier = nextTier(currentTier as TierKey);
    const upgradePlan = upgradeTier
        ? plans?.find((plan) => normalizePlanTier(plan.plan_tier as PlanTierId) === upgradeTier)
        : undefined;
    const currentPlanLabel = TIER_LABELS[currentTier];

    return (
        <div className="p-6 flex flex-col gap-6 animate-in fade-in duration-500">
            <PageHeader
                title="Assinatura e Pagamentos"
                description="Gerencie sua assinatura, histórico de pagamentos e compare os recursos disponíveis nos tiers DeepFarms."
                icon={<CreditCard className="text-primary" size={24} />}
                actions={<IACommercialAssistantWidget surface="billing" compact triggerLabel="Assistente IA" />}
                breadcrumbs={[
                    { label: "Configurações", href: "/dashboard/settings" },
                    { label: "Assinatura e Pagamentos" }
                ]}
            />

            <Card className="overflow-hidden border-primary/15 bg-gradient-to-br from-background to-primary/5 rounded-sm">
                <CardHeader className="gap-2 pb-4">
                    <div className="flex items-center justify-between">
                        <Badge variant="secondary" className="rounded-sm text-[10px] uppercase font-black tracking-wider">
                            Assinatura Atual
                        </Badge>
                        <Badge variant="outline" className={cn(
                            "rounded-sm border-primary/20 text-primary font-black uppercase text-[10px]",
                            (account?.assinatura?.status === 'TRIAL') && "text-red-600 border-red-500/30 bg-red-50 dark:bg-red-950/20"
                        )}>
                            {account?.assinatura?.status || "ATIVO"}
                        </Badge>
                    </div>
                    <CardTitle className="text-2xl font-black uppercase tracking-tight">
                        Plano {currentPlanLabel}
                    </CardTitle>
                    <CardDescription className="max-w-3xl font-medium">
                        {account?.assinatura
                            ? `Próximo vencimento: ${account.assinatura.proximo_vencimento ? format(new Date(account.assinatura.proximo_vencimento), "dd/MM/yyyy", { locale: ptBR }) : "N/A"}`
                            : "Conta sem assinatura ativa. Solicite upgrade ou fale com vendas."}
                    </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-6 lg:grid-cols-[1fr_auto]">
                    <div className="flex flex-wrap gap-2">
                        {(account?.tenant.modulos_ativos ?? []).map((mod) => (
                            <Badge key={mod} variant="outline" className="gap-1.5 rounded-sm text-[10px] font-bold border-primary/10 bg-background/50">
                                <Check size={12} className="text-emerald-500" />
                                {getModuleName(mod)}
                            </Badge>
                        ))}
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-sm border border-border/60 bg-background/70 p-3">
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Usuários contratados</p>
                            <p className="mt-1 text-sm font-bold">{account?.tenant.max_usuarios ?? account?.assinatura?.max_usuarios ?? 0}</p>
                        </div>
                        <div className="rounded-sm border border-border/60 bg-background/70 p-3">
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Categorias do plano</p>
                            <p className="mt-1 text-sm font-bold">
                                {account?.tenant.max_categorias_plano ?? account?.assinatura?.max_categorias_plano ?? 0}
                            </p>
                        </div>
                    </div>
                </CardContent>
                <CardFooter className="flex flex-wrap gap-2 border-t bg-background/50 p-4">
                    {upgradePlan ? (
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => upgradeMutation.mutate(upgradePlan.id)}
                            disabled={upgradeMutation.isPending}
                            className="gap-2 rounded-sm font-black uppercase text-[10px]"
                        >
                            {upgradeMutation.isPending ? (
                                <Loader2 className="animate-spin size-3" />
                            ) : (
                                <ArrowRight size={14} />
                            )}
                            Upgrade para {TIER_LABELS[normalizePlanTier(upgradePlan.plan_tier as PlanTierId) as TierKey]}
                        </Button>
                    ) : (
                        <Button asChild variant="outline" size="sm" className="gap-2 rounded-sm font-black uppercase text-[10px]">
                            <Link href={SUPPORT_HREF}>
                                <ExternalLink size={14} />
                                Falar com vendas
                            </Link>
                        </Button>
                    )}
                    <Button variant="outline" size="sm" asChild className="gap-2 rounded-sm font-black uppercase text-[10px]">
                        <Link href={SUPPORT_HREF}>
                            <LifeBuoy size={14} />
                            Suporte Comercial
                        </Link>
                    </Button>
                </CardFooter>
            </Card>

            <IncentivoGrowthCard incentivo={growthPlano?.incentivo} />

            <GrowthEngineSection config={growthEngineConfig} currentTier={currentTier} />

            <div className="grid gap-6 lg:grid-cols-[1.5fr_0.9fr]">
                <Card className="border shadow-sm rounded-sm overflow-hidden">
                    <CardHeader className="pb-3 border-b bg-muted/20">
                        <Badge variant="outline" className="w-fit rounded-sm text-[9px] uppercase font-black">
                            Matriz de Recursos
                        </Badge>
                        <CardTitle className="text-base font-black uppercase tracking-tight">O que cada tier libera</CardTitle>
                    </CardHeader>
                    <CardContent className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="min-w-[220px]">Funcionalidade</TableHead>
                                    <TableHead>{TIER_LABELS.BASICO}</TableHead>
                                    <TableHead>{TIER_LABELS.PROFISSIONAL}</TableHead>
                                    <TableHead>{TIER_LABELS.ENTERPRISE}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {FEATURE_COMPARISON.map((row) => (
                                    <TableRow key={row.feature} className="hover:bg-muted/30">
                                        <TableCell className="font-bold text-xs uppercase tracking-tighter">{row.feature}</TableCell>
                                        <TableCell className="text-[11px] font-medium text-muted-foreground">{row.a1}</TableCell>
                                        <TableCell className="text-[11px] font-medium text-muted-foreground">{row.profissional}</TableCell>
                                        <TableCell className="text-[11px] font-medium text-muted-foreground">{row.enterprise}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                <Card className="border shadow-sm rounded-sm flex flex-col">
                    <CardHeader className="pb-4">
                        <Badge variant="secondary" className="w-fit rounded-sm text-[10px] font-black uppercase">
                            Recomendação IA
                        </Badge>
                        <CardTitle className="text-base font-black uppercase tracking-tight leading-tight">
                            {currentTier === "ENTERPRISE"
                                ? "Cobertura Total"
                                : `Próximo: ${TIER_LABELS[upgradeTier ?? "PROFISSIONAL"]}`}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-3">
                        {(TIER_FEATURES[currentTier as TierKey] || []).map((feature) => (
                            <div key={feature} className="flex items-start gap-2 text-sm">
                                <Check className="mt-0.5 size-4 text-emerald-600" data-icon="inline-start" />
                                <span>{feature}</span>
                            </div>
                        ))}
                    </CardContent>
                    <CardFooter className="flex flex-col items-stretch gap-2 border-t pt-4 mt-auto bg-muted/10 p-4">
                        {upgradePlan ? (
                            <Button
                                variant="outline"
                                size="sm"
                                className="gap-2 rounded-sm font-black uppercase text-[10px]"
                                onClick={() => upgradeMutation.mutate(upgradePlan.id)}
                                disabled={upgradeMutation.isPending}
                            >
                                {upgradeMutation.isPending ? (
                                    <Loader2 className="animate-spin size-3" />
                                ) : (
                                    <ArrowRight size={14} />
                                )}
                                Solicitar upgrade
                            </Button>
                        ) : (
                            <Button asChild variant="outline" size="sm" className="gap-2 rounded-sm font-black uppercase text-[10px]">
                                <Link href={SUPPORT_HREF}>
                                    <ExternalLink size={14} />
                                    Falar com vendas
                                </Link>
                            </Button>
                        )}
                        <Button variant="ghost" size="sm" asChild className="gap-2 rounded-sm font-black uppercase text-[10px] text-muted-foreground">
                            <Link href={SUPPORT_HREF}>
                                <FileText size={14} />
                                Abrir chamado comercial
                            </Link>
                        </Button>
                    </CardFooter>
                </Card>
            </div>

            <Card className="shadow-sm rounded-sm">
                <CardHeader className="pb-4">
                    <CardTitle className="text-xl font-black uppercase tracking-tight">Tabela de Preços</CardTitle>
                    <CardDescription className="text-xs font-medium">
                        Transparência total nos tiers DeepFarms.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-center gap-4 mb-6 bg-muted/30 p-2 rounded-sm w-fit mx-auto border border-border/50">
                        <span className={`text-[10px] font-black uppercase tracking-wider ${cycle === "MENSAL" ? "text-foreground" : "text-muted-foreground"}`}>
                            Mensal
                        </span>
                        <Tabs value={cycle} onValueChange={(v) => setCycle(v as BillingCycle)}>
                            <TabsList className="grid w-[120px] grid-cols-2 h-7 rounded-sm p-0.5 bg-background border">
                                <TabsTrigger value="MENSAL" className="text-[9px] font-black uppercase h-6 rounded-sm">Mês</TabsTrigger>
                                <TabsTrigger value="ANUAL" className="text-[9px] font-black uppercase h-6 rounded-sm">Ano</TabsTrigger>
                            </TabsList>
                        </Tabs>
                        <span className={`text-[10px] font-black uppercase tracking-wider ${cycle === "ANUAL" ? "text-emerald-600" : "text-muted-foreground"}`}>
                            Anual
                        </span>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-3">
                        {TIER_ORDER.map((tier) => {
                            const plan = plans?.find((item) => normalizePlanTier(item.plan_tier as PlanTierId) === tier);
                            const isCurrent = currentTier === tier;
                            const isRecommended = upgradeTier === tier;
                            const price = tierPrice(plan, cycle);

                            return (
                                <Card
                                    key={tier}
                                    className={cn(
                                        "flex flex-col border shadow-sm rounded-sm transition-all duration-300",
                                        isCurrent && "border-primary/40 bg-primary/5 ring-1 ring-primary/20",
                                        isRecommended && !isCurrent && "border-primary/30"
                                    )}
                                >
                                    <CardHeader className="gap-3">
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex flex-col gap-1">
                                                <Badge variant={isCurrent ? "default" : "outline"} className="w-fit rounded-sm text-[9px] font-black uppercase tracking-widest px-1.5 h-4">
                                                    {TIER_LABELS[tier]}
                                                </Badge>
                                                <CardTitle className="text-base font-black uppercase tracking-tight">{getDisplayedPlanName(plan, tier)}</CardTitle>
                                                <CardDescription className="text-[10px] leading-tight font-medium uppercase text-muted-foreground/80">{TIER_SUBTITLE[tier]}</CardDescription>
                                            </div>
                                            {tier === "ENTERPRISE" ? <Crown className="text-amber-500 size-5" /> : null}
                                        </div>
                                        <div className="flex items-end gap-1">
                                            <span className="text-2xl font-black tracking-tighter">{price}</span>
                                            <span className="pb-1 text-[10px] font-black uppercase text-muted-foreground">/mês</span>
                                        </div>
                                        {cycle === "ANUAL" && plan && (
                                            <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-tighter">
                                                Cobrado anualmente: {formatCurrency(plan.preco_anual)}
                                            </p>
                                        )}
                                    </CardHeader>
                                    <CardContent className="flex flex-1 flex-col gap-4">
                                        <div className="flex flex-wrap gap-1.5">
                                            {(plan?.modulos_inclusos ?? []).map((mod) => (
                                                <Badge key={mod} variant="outline" className="gap-1 rounded-sm text-[8px] font-black uppercase py-0 border-primary/5 bg-background/50">
                                                    <Check size={8} className="text-emerald-500" />
                                                    {getModuleName(mod)}
                                                </Badge>
                                            ))}
                                        </div>
                                        <Separator className="bg-border/50" />
                                        <div className="flex flex-col gap-2">
                                            {(TIER_FEATURES[tier] || []).map((feature) => (
                                                <div key={feature} className="flex items-start gap-2 text-[11px] font-medium leading-tight">
                                                    <Check className="mt-0.5 size-3 text-emerald-600 shrink-0" />
                                                    <span>{feature}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                    <CardFooter className="mt-auto border-t bg-muted/5 p-4">
                                        {isCurrent ? (
                                            <Button className="w-full text-[10px] font-black uppercase rounded-sm h-8" variant="outline" disabled>
                                                Plano atual
                                            </Button>
                                        ) : tier === "ENTERPRISE" ? (
                                            <Button asChild variant="outline" className="w-full gap-2 text-[10px] font-black uppercase rounded-sm h-8 border-amber-500/30 text-amber-600 hover:bg-amber-50">
                                                <Link href={SUPPORT_HREF}>
                                                    <ExternalLink size={12} />
                                                    Falar com vendas
                                                </Link>
                                            </Button>
                                        ) : plan ? (
                                            <Button
                                                variant="outline"
                                                className="w-full gap-2 text-[10px] font-black uppercase rounded-sm h-8"
                                                onClick={() => upgradeMutation.mutate(plan.id)}
                                                disabled={upgradeMutation.isPending}
                                            >
                                                {upgradeMutation.isPending ? (
                                                    <Loader2 className="animate-spin size-3" />
                                                ) : (
                                                    <ArrowRight size={12} />
                                                )}
                                                Solicitar upgrade
                                            </Button>
                                        ) : (
                                            <Button variant="outline" className="w-full text-[10px] font-black uppercase rounded-sm h-8" disabled>
                                                Indisponível
                                            </Button>
                                        )}
                                    </CardFooter>
                                </Card>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* IA Usage Link */}
            <div className="flex items-center justify-between rounded-sm border border-primary/15 bg-primary/5 px-5 py-4">
                <div className="flex items-center gap-3">
                    <span className="size-8 rounded-sm bg-primary/10 border border-primary/15 flex items-center justify-center shrink-0">
                        <FileText className="size-4 text-primary" />
                    </span>
                    <div>
                        <p className="text-sm font-semibold text-foreground">Uso de IA</p>
                        <p className="text-xs text-muted-foreground">Veja o consumo de análises inteligentes do seu plano.</p>
                    </div>
                </div>
                <Link href="/dashboard/settings/ia" className="text-xs text-primary font-medium flex items-center gap-1 hover:underline">
                    Ver consumo <ExternalLink className="size-3" />
                </Link>
            </div>

            {/* History Section */}
            <div className="flex flex-col gap-4">
                <div className="flex items-center gap-2">
                    <History className="size-5 text-primary" />
                    <h3 className="text-base font-black uppercase tracking-tight">Histórico de faturamentos</h3>
                </div>
                <Card className="rounded-sm border bg-card shadow-sm overflow-hidden">
                    <input
                        ref={proofFileInputRef}
                        type="file"
                        accept="application/pdf,image/jpeg,image/png"
                        className="hidden"
                        onChange={handleProofFileChange}
                    />
                    <Table>
                        <TableHeader className="bg-muted/40">
                            <TableRow>
                                <TableHead className="text-[10px] font-black uppercase tracking-widest h-10">Data</TableHead>
                                <TableHead className="text-[10px] font-black uppercase tracking-widest h-10">Plano</TableHead>
                                <TableHead className="text-[10px] font-black uppercase tracking-widest h-10">Status</TableHead>
                                <TableHead className="text-right text-[10px] font-black uppercase tracking-widest h-10">Valor</TableHead>
                                <TableHead className="text-right text-[10px] font-black uppercase tracking-widest h-10 px-6">Ação</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {invoices?.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="text-center py-10 text-[11px] font-bold text-muted-foreground uppercase italic">
                                        Nenhuma fatura encontrada.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                invoices?.map((inv) => (
                                    <TableRow key={inv.id} className="group hover:bg-muted/30">
                                        <TableCell className="text-[11px] font-bold">
                                            {format(new Date(inv.data_vencimento), "dd/MM/yyyy")}
                                        </TableCell>
                                        <TableCell className="text-[11px] font-black uppercase tracking-tighter">{getDisplayedInvoicePlanName(inv.plano_nome)}</TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className={`
                                                text-[9px] uppercase font-black rounded-sm h-5 border-none
                                                ${inv.status === 'PAGA' ? 'bg-emerald-500/10 text-emerald-600' : ''}
                                                ${inv.status === 'ABERTA' ? 'bg-amber-500/10 text-amber-600' : ''}
                                                ${inv.status === 'VENCIDA' ? 'bg-red-500/10 text-red-600' : ''}
                                                ${inv.status === 'EM_ANALISE' ? 'bg-blue-500/10 text-blue-600' : ''}
                                                ${inv.status === 'REJEITADA' ? 'bg-red-500/10 text-red-600' : ''}
                                            `}>
                                                {inv.status}
                                            </Badge>
                                            {inv.justificativa_rejeicao && (
                                                <p className="text-[10px] text-red-500 mt-1 italic font-medium max-w-[200px]">Motivo: {inv.justificativa_rejeicao}</p>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right font-mono text-xs font-bold">
                                            {inv.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                                        </TableCell>
                                        <TableCell className="text-right px-6">
                                            {inv.status === "ABERTA" || inv.status === "REJEITADA" ? (
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    className="gap-2 rounded-sm h-7 text-[10px] font-black uppercase"
                                                    onClick={() => triggerProofUpload(inv.id)}
                                                    disabled={sendProofMutation.isPending}
                                                >
                                                    <UploadCloud size={12} />
                                                    {sendProofMutation.isPending && pendingProofInvoiceId === inv.id ? "Enviando..." : "Enviar Comprovante"}
                                                </Button>
                                            ) : inv.url_comprovante ? (
                                                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 rounded-sm text-primary hover:bg-primary/5" title="Ver comprovante" asChild>
                                                    <a href={inv.url_comprovante} target="_blank" rel="noreferrer">
                                                        <FileText size={14} />
                                                    </a>
                                                </Button>
                                            ) : null}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </Card>
            </div>

            <div className="flex flex-col items-center gap-4 py-8 bg-muted/10 rounded-sm border border-dashed border-border/60 text-center">
                <div className="p-2.5 rounded-full bg-emerald-500/10 text-emerald-600">
                    <LifeBuoy size={20} />
                </div>
                <div>
                    <h4 className="text-sm font-black uppercase tracking-tight">Dúvidas sobre assinaturas?</h4>
                    <p className="text-[11px] text-muted-foreground mt-1 max-w-sm font-medium">
                        Nossa equipe está pronta para te ajudar a escolher o melhor plano para sua fazenda.
                    </p>
                </div>
                <Button asChild variant="outline" size="sm" className="gap-2 rounded-sm font-black uppercase text-[10px] h-8">
                    <Link href={SUPPORT_HREF}>
                        Abrir chamado comercial <ExternalLink size={12} />
                    </Link>
                </Button>
            </div>
        </div>
    );
}
