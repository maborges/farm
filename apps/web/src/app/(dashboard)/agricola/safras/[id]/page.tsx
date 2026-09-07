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
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { SafraTimeline } from "@/components/agricola/safra-timeline";
import { SafraChecklist } from "@/components/agricola/safra-checklist";
import { SafraFenologia } from "@/components/agricola/safra-fenologia";
import { SafraTarefas } from "@/components/agricola/safra-tarefas";
import { CultivoCard } from "@/components/agricola/cultivo-card";
import { CultivoAnaliseSoloDrawer, type CultivoAreaInfo } from "@/components/agricola/cultivo-analise-drawer";
import { SafraCreateDialog } from "@/components/agricola/safra-create-dialog";
import {
    ClipboardList, Bug, Leaf, CheckSquare, FlaskConical, Wheat, Coffee,
    Calculator, Satellite, BookOpen, Sprout, Pencil,
    ChevronDown, History, ListTodo, BarChart2, ArrowRight, Layers, Gauge,
    Package, DollarSign, AlertTriangle, Rocket, CalendarDays, Wallet, BarChart3,
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

interface SafraFaseHistorico {
    id: string;
    fase_anterior: string | null;
    fase_nova: string;
    usuario_id: string | null;
    observacao: string | null;
    created_at: string;
}

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

interface GrupoFenologia {
    id: string;
    nome: string;
    cor: string | null;
    itens: { talhao_id: string }[];
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
    PLANEJADA: "bg-slate-100 text-slate-700 border-slate-200",
    PREPARO_SOLO: "bg-amber-50 text-amber-700 border-amber-200",
    PLANTIO: "bg-emerald-50 text-emerald-700 border-emerald-200",
    DESENVOLVIMENTO: "bg-green-50 text-green-700 border-green-200",
    COLHEITA: "bg-yellow-50 text-yellow-700 border-yellow-200",
    POS_COLHEITA: "bg-orange-50 text-orange-700 border-orange-200",
    ENCERRADA: "bg-gray-100 text-gray-600 border-gray-200",
    CANCELADA: "bg-red-50 text-red-600 border-red-200",
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
    const [historicoOpen, setHistoricoOpen] = useState(false);
    const [analiseDrawerArea, setAnaliseDrawerArea] = useState<CultivoAreaInfo | null>(null);
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

    const { data: historico } = useQuery<SafraFaseHistorico[]>({
        queryKey: ["safra-historico", id],
        queryFn: () => apiFetch(`/safras/${id}/historico-fases`),
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

    const { data: gruposFenologia = [] } = useQuery<GrupoFenologia[]>({
        queryKey: ["grupos-talhoes", id],
        queryFn: () => apiFetch(`/safras/${id}/grupos-talhoes`),
    });

    const { data: tarefasSafra = [] } = useQuery<{ cultivo_area_id: string | null; origem: string; status: string }[]>({
        queryKey: ["safras", id, "tarefas"],
        queryFn: () => apiFetch(`/safras/${id}/tarefas`),
        enabled: !!safra,
    });
    // Status da correção de solo por talhão: distingue "tarefa gerada mas ainda
    // não executada" de "correção já concluída" — não basta saber que existe
    // uma tarefa, é preciso saber se ela já terminou.
    const cultivoAreaCorrecaoStatus = useMemo(() => {
        const ativos = new Set(["PENDENTE_APROVACAO", "APROVADA", "EM_EXECUCAO", "CONCLUIDA"]);
        const status = new Map<string, "PENDENTE" | "CONCLUIDA">();
        for (const t of tarefasSafra) {
            if (t.origem !== "SOLO" || !t.cultivo_area_id || !ativos.has(t.status)) continue;
            if (t.status === "CONCLUIDA") {
                status.set(t.cultivo_area_id, "CONCLUIDA");
            } else if (!status.has(t.cultivo_area_id)) {
                status.set(t.cultivo_area_id, "PENDENTE");
            }
        }
        return status;
    }, [tarefasSafra]);

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
    }, [cultivos, todasAreas]);

    const talhoesDaSafra = useMemo(
        () => {
            const map = new Map<string, { id: string; nome: string }>();

            for (const cultivo of cultivos) {
                for (const area of cultivo.areas) {
                    const areaRural = todasAreas.find((a) => a.id === area.area_id);
                    if (!areaRural || map.has(areaRural.id)) continue;
                    map.set(areaRural.id, {
                        id: areaRural.id,
                        nome: areaRural.nome,
                    });
                }
            }

            return Array.from(map.values());
        },
        [cultivos, todasAreas],
    );

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

    const faseColorClass = FASE_COLOR[safra.status] ?? "bg-slate-100 text-slate-700 border-slate-200";

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

            {/* AÇÕES RÁPIDAS (Top Horizontal) */}
            <div className="flex flex-col gap-3">
                <h3 className="text-sm font-semibold tracking-tight text-muted-foreground uppercase">Ações Rápidas</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <Button asChild variant="outline" className="justify-start gap-3 h-14 rounded-sm shadow-sm hover:border-primary/50 transition-colors">
                        <Link href={`/agricola/safras/${id}/operacoes`}>
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                                <ClipboardList className="size-4.5 text-primary" />
                            </div>
                            <div className="flex flex-col items-start text-left min-w-0">
                                <span className="font-semibold text-sm truncate w-full">Operações</span>
                                <span className="text-[10px] text-muted-foreground font-normal truncate w-full">Registrar diário</span>
                            </div>
                        </Link>
                    </Button>
                    <Button asChild variant="outline" className="justify-start gap-3 h-14 rounded-sm shadow-sm hover:border-amber-500/50 transition-colors">
                        <Link href={`/agricola/safras/${id}/planejamento-operacional`}>
                            <div className="size-8 rounded-sm bg-amber-500/10 flex items-center justify-center shrink-0">
                                <CalendarDays className="size-4.5 text-amber-600" />
                            </div>
                            <div className="flex flex-col items-start text-left min-w-0">
                                <span className="font-semibold text-sm truncate w-full">Planejamento</span>
                                <span className="text-[10px] text-muted-foreground font-normal truncate w-full">Visão operacional</span>
                            </div>
                        </Link>
                    </Button>
                    <Button asChild variant="outline" className="justify-start gap-3 h-14 rounded-sm shadow-sm hover:border-purple-500/50 transition-colors">
                        <Link href={`/agricola/safras/${id}/orcamento`}>
                            <div className="size-8 rounded-sm bg-purple-500/10 flex items-center justify-center shrink-0">
                                <Wallet className="size-4.5 text-purple-600" />
                            </div>
                            <div className="flex flex-col items-start text-left min-w-0">
                                <span className="font-semibold text-sm truncate w-full">Orçamento</span>
                                <span className="text-[10px] text-muted-foreground font-normal truncate w-full">Custos previstos</span>
                            </div>
                        </Link>
                    </Button>
                    {hasProfessionalTier ? (
                        <Button asChild variant="outline" className="justify-start gap-3 h-14 rounded-sm shadow-sm hover:border-emerald-500/50 transition-colors">
                            <Link href={`/agricola/safras/${id}/dashboard`}>
                                <div className="size-8 rounded-sm bg-emerald-500/10 flex items-center justify-center shrink-0">
                                    <BarChart3 className="size-4.5 text-emerald-600" />
                                </div>
                                <div className="flex flex-col items-start text-left min-w-0">
                                    <span className="font-semibold text-sm truncate w-full">Dashboard</span>
                                    <span className="text-[10px] text-muted-foreground font-normal truncate w-full">Análise avançada</span>
                                </div>
                            </Link>
                        </Button>
                    ) : (
                        <div /> /* Placeholder for grid alignment if tier is not professional */
                    )}
                </div>
            </div>

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
                    <Card className="border-amber-200/60 shadow-sm">
                        <CardHeader className="pb-0 pt-4 px-4">
                            <CardTitle className="text-sm font-medium flex items-center gap-2 text-amber-700">
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

                {/* Tarefas */}
                <Card className="shadow-sm">
                    <CardHeader className="pb-0 pt-4 px-4">
                        <CardTitle className="text-sm font-medium flex items-center gap-2 text-foreground">
                            <ListTodo className="size-4 text-muted-foreground" />
                            Próximas atividades
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="px-4 pb-4 pt-4">
                        <SafraTarefas 
                            safraId={id} 
                            fase={safra.status} 
                            cultura={culturaAtual || ""} 
                        />
                    </CardContent>
                </Card>
            </div>

            {/* JORNADA & CONTEXTO COMPLEMENTAR */}
            <div className="mt-8 pt-8 space-y-6 border-t">

                {/* Cultivos */}
                {initialCultivos.length > 0 && (
                    <div className="space-y-2 mt-4">
                        <div className="flex items-center gap-2">
                            <Sprout className="size-4 text-muted-foreground" />
                            <h2 className="text-sm font-semibold">
                                {initialCultivos.length === 1 ? "Cultivo" : `Cultivos (${initialCultivos.length})`}
                            </h2>
                        </div>
                        <div className={cn("grid gap-3", initialCultivos.length === 1 ? "grid-cols-1" : "sm:grid-cols-2")}>
                            {initialCultivos.map((c) => (
                                <CultivoCard
                                    key={c.id}
                                    cultivo={c}
                                    areas={todasAreas}
                                    readOnly
                                    cultivoAreaCorrecaoStatus={cultivoAreaCorrecaoStatus}
                                    onAnaliseSolo={(area) => setAnaliseDrawerArea({
                                        id: area.id,
                                        area_id: area.area_id,
                                        area_ha: areaRuralMap.get(area.area_id)?.area_hectares ?? areaRuralMap.get(area.area_id)?.area_hectares_manual ?? area.area_ha,
                                        area_nome: todasAreas.find(a => a.id === area.area_id)?.nome,
                                        analise_solo_id: area.analise_solo_id,
                                        analise_status: area.analise_status ?? "NAO_SELECIONADA",
                                        regiao_analise: area.regiao_analise,
                                        cultivo_id: c.id,
                                        safra_id: id,
                                        cultivar_id: c.cultivar_id ?? null,
                                        cultura: c.cultura,
                                    })}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {/* Fenologia */}
                {!["CANCELADA"].includes(safra.status) && culturaAtual && (
                    <Card>
                        <CardHeader className="pb-2 pt-4 px-4">
                            <div className="flex items-center gap-2">
                                <Leaf className="size-4 text-muted-foreground" />
                                <CardTitle className="text-sm font-medium text-muted-foreground">Fenologia</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent className="px-4 pb-4 pt-1">
                            <SafraFenologia safraId={id} cultura={culturaAtual} grupos={gruposFenologia} talhoes={talhoesDaSafra} />
                        </CardContent>
                    </Card>
                )}

                {/* Histórico de fases — colapsível */}
                {historico && historico.length > 0 && (
                    <Collapsible open={historicoOpen} onOpenChange={setHistoricoOpen}>
                        <Card>
                            <CardHeader className="pb-3 pt-4 px-4">
                                <CollapsibleTrigger className="w-full">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <History className="size-4 text-muted-foreground" />
                                            <CardTitle className="text-sm font-medium text-muted-foreground">
                                                Histórico de Fases
                                            </CardTitle>
                                            <Badge variant="secondary" className="text-xs">{historico.length}</Badge>
                                        </div>
                                        <ChevronDown className={cn("size-4 text-muted-foreground transition-transform", historicoOpen && "rotate-180")} />
                                    </div>
                                </CollapsibleTrigger>
                            </CardHeader>
                            <CollapsibleContent>
                                <CardContent className="px-4 pb-4 pt-0">
                                    <ol className="relative border-l border-border ml-3 space-y-4 py-2">
                                        {historico.map((h) => (
                                            <li key={h.id} className="ml-4">
                                                <div className="absolute -left-1.5 mt-1 size-3 rounded-full bg-primary" />
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    {h.fase_anterior && (
                                                        <>
                                                            <Badge variant="outline" className="text-xs">{FASE_LABEL[h.fase_anterior] ?? h.fase_anterior}</Badge>
                                                            <span className="text-muted-foreground text-xs">→</span>
                                                        </>
                                                    )}
                                                    <Badge className="text-xs">{FASE_LABEL[h.fase_nova] ?? h.fase_nova}</Badge>
                                                    <span className="text-xs text-muted-foreground ml-auto">{fmt(h.created_at)}</span>
                                                </div>
                                                {h.observacao && (
                                                    <p className="text-sm text-muted-foreground mt-1">{h.observacao}</p>
                                                )}
                                            </li>
                                        ))}
                                    </ol>
                                </CardContent>
                            </CollapsibleContent>
                        </Card>
                    </Collapsible>
                )}

                {/* Observações */}
                {safra.observacoes && (
                    <Card>
                        <CardContent className="p-4">
                            <p className="text-xs font-medium text-muted-foreground mb-1.5">Observações</p>
                            <p className="text-sm">{safra.observacoes}</p>
                        </CardContent>
                    </Card>
                )}
            </div>

            {isEditOpen && (
                <SafraCreateDialog
                    open={isEditOpen}
                    onOpenChange={setIsEditOpen}
                    safraId={id}
                    initialSafra={{ ano_safra: safra.ano_safra }}
                    initialCultivos={initialCultivos}
                />
            )}

            {analiseDrawerArea && (
                <CultivoAnaliseSoloDrawer
                    area={analiseDrawerArea}
                    open={!!analiseDrawerArea}
                    onClose={() => setAnaliseDrawerArea(null)}
                    onSuccess={() => {
                        setAnaliseDrawerArea(null);
                    }}
                />
            )}
        </div>
    );
}
