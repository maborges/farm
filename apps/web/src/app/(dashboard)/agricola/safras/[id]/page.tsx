"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { use } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SafraTimeline } from "@/components/agricola/safra-timeline";
import { SafraChecklist } from "@/components/agricola/safra-checklist";
import { SafraCreateDialog } from "@/components/agricola/safra-create-dialog";
import { QuickActionGrid } from "@/components/ui/quick-action-grid";
import {
    ClipboardList, Bug, Leaf, CheckSquare, FlaskConical, Wheat, Coffee,
    Calculator, Satellite, BookOpen, Sprout, Pencil,
    History, ListTodo, BarChart2, ArrowRight, Layers, Gauge,
    Package, DollarSign, AlertTriangle, Rocket, Wallet, BarChart3,
} from "lucide-react";
import { getSafraLabel } from "@/lib/safra-label";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";
import { useHasTier } from "@/hooks/use-has-tier";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Safra {
    id: string;
    tenant_id: string;
    ano_safra: string;
    cultura: string | null;
    status: string;
    observacoes: string | null;
    created_at: string;
    updated_at: string;
}

interface CultivoArea {
    id: string;
    area_id: string;
    area_ha: number;
    area_nome?: string;
    analise_solo_id?: string | null;
    analise_status?: string;
    regiao_analise?: string | null;
}

interface Cultivo {
    id: string;
    cultura: string;
    cultivar_id?: string | null;
    cultivar_nome: string | null;
    areas: CultivoArea[];
    sistema_plantio?: string | null;
    produtividade_meta_sc_ha?: number | null;
    consorciado: boolean;
    data_inicio: string | null;
    data_fim: string | null;
    status?: string;
}

interface AreaRural {
    id: string;
    nome: string;
    area_hectares: number | null;
    area_hectares_manual?: number | null;
}

interface CenarioListItem {
    id: string;
    nome: string;
    tipo: string;
    eh_base: boolean;
    status: string;
    area_total_ha: number | null;
    receita_bruta_total: number | null;
    custo_total: number | null;
    margem_contribuicao_total: number | null;
    resultado_liquido_total: number | null;
    ponto_equilibrio_sc_ha: number | null;
    calculado_em: string | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TAREFA_STATUS_ABERTOS = new Set(["PENDENTE_APROVACAO", "APROVADA", "EM_EXECUCAO"]);

const FASE_LABEL: Record<string, string> = {
    PLANEJADA: "Planejamento",
    PREPARO_SOLO: "Preparo Solo",
    PLANTIO: "Plantio",
    DESENVOLVIMENTO: "Desenvolvimento",
    COLHEITA: "Colheita",
    POS_COLHEITA: "Pós-Colheita",
    ENCERRADA: "Encerrada",
    CANCELADA: "Cancelada",
};

const FASE_COLOR: Record<string, string> = {
    PLANEJADA: "bg-slate-500/10 text-slate-700 dark:text-slate-300 border-slate-500/20",
    PREPARO_SOLO: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
    PLANTIO: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
    DESENVOLVIMENTO: "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20",
    COLHEITA: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20",
    POS_COLHEITA: "bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20",
    ENCERRADA: "bg-muted text-muted-foreground border-border",
    CANCELADA: "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20",
};

function fmt(d: string | null) {
    if (!d) return "—";
    return format(new Date(d), "dd/MM/yyyy", { locale: ptBR });
}

// ---------------------------------------------------------------------------
// Module groups config (mega menu)
// ---------------------------------------------------------------------------

interface NavItem {
    href: string;
    icon: React.ElementType;
    label: string;
    desc: string;
    color: string;
}

interface NavGroup {
    key: string;
    label: string;
    items: NavItem[];
}

// ---------------------------------------------------------------------------
// KPI Strip — cenário BASE
// ---------------------------------------------------------------------------

function fmtBRL(v: number | null): string {
    if (v === null || v === undefined) return "—";
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(receita: number | null, margem: number | null): string {
    if (!receita || !margem || receita === 0) return "—";
    return (margem / receita * 100).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
}

function fmtSc(v: number | null): string {
    if (v === null || v === undefined) return "—";
    return v.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 }) + " sc/ha";
}

interface CenarioBaseStripProps {
    cenario: CenarioListItem;
    safraId: string;
}

function CenarioBaseStrip({ cenario, safraId }: CenarioBaseStripProps) {
    const margemPositiva = (cenario.margem_contribuicao_total ?? 0) >= 0;

    return (
        <div className="rounded-sm border bg-card">
            <div className="flex items-center justify-between px-4 py-2.5 border-b">
                <div className="flex items-center gap-2">
                    <BarChart2 className="size-3.5 text-purple-600" />
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Projeção BASE</span>
                </div>
                <Link
                    href={`/agricola/safras/${safraId}/cenarios`}
                    className="flex items-center gap-1 text-xs text-primary hover:underline"
                >
                    Ver cenários <ArrowRight className="size-3" />
                </Link>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-y sm:divide-y-0">
                <div className="px-4 py-3">
                    <p className="text-xs text-muted-foreground">Receita Bruta</p>
                    <p className="text-sm font-semibold mt-0.5 tabular-nums">
                        {fmtBRL(cenario.receita_bruta_total)}
                    </p>
                </div>
                <div className="px-4 py-3">
                    <p className="text-xs text-muted-foreground">Custo Total</p>
                    <p className="text-sm font-semibold mt-0.5 tabular-nums">
                        {fmtBRL(cenario.custo_total)}
                    </p>
                </div>
                <div className="px-4 py-3">
                    <p className="text-xs text-muted-foreground">Margem</p>
                    <div className="flex items-baseline gap-1.5 mt-0.5">
                        <p className={cn("text-sm font-semibold tabular-nums", margemPositiva ? "text-emerald-600" : "text-destructive")}>
                            {fmtBRL(cenario.margem_contribuicao_total)}
                        </p>
                        <span className={cn("text-xs tabular-nums", margemPositiva ? "text-emerald-500" : "text-destructive/80")}>
                            {fmtPct(cenario.receita_bruta_total, cenario.margem_contribuicao_total)}
                        </span>
                    </div>
                </div>
                <div className="px-4 py-3">
                    <p className="text-xs text-muted-foreground">Ponto de Equilíbrio</p>
                    <p className="text-sm font-semibold mt-0.5 tabular-nums">
                        {fmtSc(cenario.ponto_equilibrio_sc_ha)}
                    </p>
                </div>
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SafraDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const pathname = usePathname();
    const queryKey = ["safra", id];
    const [isEditOpen, setIsEditOpen] = useState(false);
    const hasProfessionalTier = useHasTier("PROFISSIONAL");

    const { data: safra, isLoading } = useQuery<Safra>({
        queryKey,
        queryFn: () => apiFetch(`/safras/${id}`),
    });

    const { data: cultivos = [], isLoading: isLoadingCultivos } = useQuery<Cultivo[]>({
        queryKey: ["safra-cultivos", id],
        queryFn: () => apiFetch(`/safras/${id}/cultivos`),
        enabled: !!safra,
    });

    const { data: todasAreas = [] } = useQuery<AreaRural[]>({
        queryKey: ["areas-rurais-talhoes"],
        queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
    });
    const areaRuralMap = useMemo(
        () => new Map(todasAreas.map((area) => [area.id, area])),
        [todasAreas],
    );

    const { data: tarefasSafra = [] } = useQuery<{ cultivo_area_id: string | null; origem: string; status: string }[]>({
        queryKey: ["safras", id, "tarefas"],
        queryFn: () => apiFetch(`/safras/${id}/tarefas`),
        enabled: !!safra,
    });
    const tarefasAbertas = tarefasSafra.filter((t) => TAREFA_STATUS_ABERTOS.has(t.status)).length;

    const { data: cenarios = [] } = useQuery<CenarioListItem[]>({
        queryKey: ["safra-cenarios-strip", id],
        queryFn: () => apiFetch(`/safras/${id}/cenarios`),
        enabled: !!safra && !["CANCELADA"].includes(safra.status),
        staleTime: 2 * 60 * 1000, // 2 min
    });

    const cenarioBase = cenarios.find((c) => c.eh_base && c.status === "ATIVO") ?? null;

    const initialCultivos = useMemo(() => {
        return (cultivos ?? []).map(c => ({
            id: c.id,
            cultura: c.cultura,
            cultivar_id: c.cultivar_id ?? null,
            cultivar_nome: c.cultivar_nome,
            consorciado: c.consorciado ?? false,
            data_inicio: c.data_inicio,
            data_fim: c.data_fim,
            produtividade_meta_sc_ha: c.produtividade_meta_sc_ha ?? null,
            areas: c.areas
                .map((a) => ({
                    id: a.id,
                    area_id: a.area_id,
                    area_ha: a.area_ha,
                    analise_solo_id: a.analise_solo_id ?? null,
                    analise_status: a.analise_status ?? "NAO_SELECIONADA",
                    regiao_analise: a.regiao_analise ?? null,
                })),
        }));
    }, [cultivos]);

    if (isLoading || !safra) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-10 w-72" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-48 w-full" />
            </div>
        );
    }

    const culturaAtual = initialCultivos[0]?.cultura ?? safra.cultura ?? null;
    const temCafe = initialCultivos.some(c => c.cultura?.toLowerCase().includes("caf")) ||
        safra.cultura?.toLowerCase().includes("caf");
    const areaTotal = initialCultivos.reduce((sum, c) =>
        sum + c.areas.reduce((s, a) => {
            const areaRural = areaRuralMap.get(a.area_id);
            return s + (areaRural?.area_hectares ?? areaRural?.area_hectares_manual ?? a.area_ha ?? 0);
        }, 0), 0);

    const titulo = initialCultivos.length === 1
        ? `${initialCultivos[0].cultura} — Safra ${safra.ano_safra}`
        : initialCultivos.length > 1
            ? `Multi-cultivo — Safra ${safra.ano_safra}`
            : `Safra ${safra.ano_safra}`;
    const safraLabel = getSafraLabel(safra);

    const faseColorClass = FASE_COLOR[safra.status] ?? "bg-muted text-muted-foreground border-border";

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <PageHeader
                title={titulo}
                icon={<ClipboardList className="text-primary" size={22} />}
                description={
                    initialCultivos.length === 1
                        ? (initialCultivos[0].cultivar_nome ?? "")
                        : initialCultivos.length > 1
                            ? `${initialCultivos.length} cultivos`
                            : "Nenhum cultivo cadastrado"
                }
                actions={
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                        <span className={cn("text-xs font-medium px-2.5 py-1 rounded-full border", faseColorClass)}>
                            {FASE_LABEL[safra.status] ?? safra.status}
                        </span>
                        {safra.status === "PLANEJADA" && (
                            <Button size="sm" variant="outline" onClick={() => setIsEditOpen(true)} disabled={isLoadingCultivos}>
                                <Pencil className="size-3.5 mr-1.5" /> Editar
                            </Button>
                        )}
                    </div>
                }
            />

            {/* Timeline (At the very top) */}
            <SafraTimeline
                safraId={id}
                statusAtual={safra.status}
                queryKey={queryKey}
            />

            {/* AÇÕES RÁPIDAS
                Linha 1: 1. Cultivos | 2. Orçamento | 3. Estoque & Insumos | 4. Tarefas | 5. Operações | 6. Caderno de Campo
                Linha 2: 7. Fenologia | 8. Monitoramento | 9. Histórico de Fases | 10. Romaneios | 11. Dashboard
            */}
            <QuickActionGrid
                label="Ações Rápidas da Safra"
                layout="centered"
                actions={[
                    {
                        title: "Cultivos",
                        description: "Cultivos, talhões e unidades operacionais da safra",
                        icon: Sprout,
                        href: `/agricola/safras/${id}/production-units`,
                        badge: initialCultivos.length > 0 ? initialCultivos.length : null,
                    },
                    {
                        title: "Orçamento",
                        description: "Custos previstos e controle orçamentário",
                        icon: Wallet,
                        href: `/agricola/safras/${id}/orcamento`,
                    },
                    {
                        title: "Estoque & Insumos",
                        description: "Aplicações de insumos e saldo de estoque da safra",
                        icon: Package,
                        href: `/agricola/safras/${id}/estoque`,
                    },
                    {
                        title: "Tarefas",
                        description: "Planejamento, aprovação e execução das atividades da safra",
                        icon: ListTodo,
                        href: `/agricola/safras/${id}/tarefas`,
                        badge: tarefasAbertas > 0 ? tarefasAbertas : null,
                    },
                    {
                        title: "Operações",
                        description: "Registro de tratos culturais, plantio e colheita",
                        icon: ClipboardList,
                        href: `/agricola/safras/${id}/operacoes`,
                    },
                    {
                        title: "Caderno de Campo",
                        description: "Anotações diárias, fotos e ocorrências da safra",
                        icon: BookOpen,
                        href: `/agricola/safras/${id}/caderno`,
                    },
                    {
                        title: "Fenologia",
                        description: "Estágios de desenvolvimento da cultura por talhão",
                        icon: Leaf,
                        href: `/agricola/safras/${id}/fenologia`,
                    },
                    {
                        title: "Monitoramento",
                        description: "Controle de pragas, doenças e armadilhas fitossanitárias",
                        icon: Bug,
                        href: `/agricola/safras/${id}/monitoramento`,
                    },
                    {
                        title: "Histórico de Fases",
                        description: "Linha do tempo das mudanças de fase da safra",
                        icon: History,
                        href: `/agricola/safras/${id}/historico`,
                    },
                    {
                        title: "Romaneios",
                        description: "Controle de pesagens, cargas e entrega de colheita",
                        icon: Wheat,
                        href: `/agricola/safras/${id}/romaneios`,
                    },
                    {
                        title: "Dashboard",
                        description: "Análise avançada, produtividade e DRE da safra",
                        icon: BarChart3,
                        href: `/agricola/safras/${id}/dashboard`,
                        badge: !hasProfessionalTier ? "PRO" : undefined,
                    },
                ]}
            />

            <div className="flex flex-col gap-6 mt-2">
                {/* Resumo - KPIs Compactos */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card className="rounded-sm shadow-sm bg-card p-4 flex items-center justify-between gap-3">
                        <div className="min-w-0">
                            <p className="text-xs font-medium text-muted-foreground">Cultivos</p>
                            <p className="mt-1 text-2xl font-bold leading-tight">{initialCultivos.length}</p>
                        </div>
                        <div className="size-10 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                            <Sprout className="size-5 text-primary" />
                        </div>
                    </Card>

                    <Card className="rounded-sm shadow-sm bg-card p-4 flex items-center justify-between gap-3">
                        <div className="min-w-0">
                            <p className="text-xs font-medium text-muted-foreground">Área total</p>
                            <p className="mt-1 text-2xl font-bold leading-tight">
                                {areaTotal > 0 ? `${areaTotal.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha` : "—"}
                            </p>
                        </div>
                        <div className="size-10 rounded-sm bg-emerald-500/10 flex items-center justify-center shrink-0">
                            <Layers className="size-5 text-emerald-600" />
                        </div>
                    </Card>

                    <Card className="rounded-sm shadow-sm bg-card p-4 flex items-center justify-between gap-3">
                        <div className="min-w-0">
                            <p className="text-xs font-medium text-muted-foreground">Fase atual</p>
                            <p className="mt-1 text-xl font-bold leading-tight truncate text-amber-600">
                                {FASE_LABEL[safra.status] ?? safra.status}
                            </p>
                        </div>
                        <div className="size-10 rounded-sm bg-amber-500/10 flex items-center justify-center shrink-0">
                            <ClipboardList className="size-5 text-amber-600" />
                        </div>
                    </Card>

                    <Card className="rounded-sm shadow-sm bg-card p-4 flex items-center justify-between gap-3">
                        <div className="min-w-0">
                            <p className="text-xs font-medium text-muted-foreground">Atualização</p>
                            <p className="mt-1 text-xl font-bold leading-tight truncate">
                                {fmt(safra.updated_at)}
                            </p>
                        </div>
                        <div className="size-10 rounded-sm bg-slate-500/10 flex items-center justify-center shrink-0">
                            <History className="size-5 text-slate-600" />
                        </div>
                    </Card>
                </div>

                {/* KPI Strip — cenário BASE */}
                {cenarioBase && (
                    <div className="shadow-sm rounded-sm">
                        <CenarioBaseStrip cenario={cenarioBase} safraId={id} />
                    </div>
                )}

                {/* Checklist da fase atual */}
                {!["ENCERRADA", "CANCELADA"].includes(safra.status) && culturaAtual && (
                    <Card className="border-alert-warning-border shadow-sm">
                        <CardHeader className="pb-0 pt-4 px-4">
                            <CardTitle className="text-sm font-medium flex items-center gap-2 text-alert-warning-icon">
                                <AlertTriangle className="size-4" />
                                Precisa de atenção
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="px-4 pb-4 pt-4">
                            <SafraChecklist
                                safraId={id}
                                cultura={culturaAtual}
                                fase={safra.status}
                            />
                        </CardContent>
                    </Card>
                )}

            </div>

            {/* Observações */}
            {safra.observacoes && (
                <Card className="mt-6 rounded-sm shadow-xs border border-border/70">
                    <CardContent className="p-4">
                        <p className="text-xs font-medium text-muted-foreground mb-1.5">Observações</p>
                        <p className="text-sm">{safra.observacoes}</p>
                    </CardContent>
                </Card>
            )}

            {isEditOpen && (
                <SafraCreateDialog
                    open={isEditOpen}
                    onOpenChange={setIsEditOpen}
                    safraId={id}
                    initialSafra={{ ano_safra: safra.ano_safra }}
                    initialCultivos={initialCultivos}
                />
            )}
        </div>
    );
}
