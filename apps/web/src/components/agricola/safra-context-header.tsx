"use client";

import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useHasTier } from "@/hooks/use-has-tier";
import { useAppStore } from "@/lib/stores/app-store";
import { getSafraLabel } from "@/lib/safra-label";
import {
    BarChart2,
    BookOpen,
    Bug,
    CheckSquare,
    ClipboardCheck,
    ClipboardList,
    Coffee,
    DollarSign,
    FlaskConical,
    Gauge,
    Layers,
    Leaf,
    ListTodo,
    Package,
    Satellite,
    Sprout,
    Wheat,
    ChevronDown,
    ChevronRight,
    Grid,
    ArrowLeft,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";

interface SafraContextHeaderProps {
    safraId: string;
}

interface NavItem {
    href: string;
    label: string;
    icon: React.ElementType;
    desc: string;
    color: string;
}

interface NavGroup {
    key: string;
    label: string;
    items: NavItem[];
}

interface Cultivo {
    id: string;
    cultura: string;
}

interface Safra {
    id: string;
    ano_safra: string;
    cultura: string | null;
    status: string;
}

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

export function SafraContextHeader({ safraId }: SafraContextHeaderProps) {
    const pathname = usePathname();
    const router = useRouter();
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    const { tenant, activeFazendaId, unidadesProdutivasAutorizadas } = useAppStore();

    const { data: safra, isLoading: isLoadingSafra } = useQuery<Safra>({
        queryKey: ["safra", safraId],
        queryFn: () => apiFetch(`/safras/${safraId}`),
        staleTime: 60000,
    });

    const { data: cultivos = [] } = useQuery<Cultivo[]>({
        queryKey: ["safra-cultivos", safraId],
        queryFn: () => apiFetch(`/safras/${safraId}/cultivos`),
    });

    const temCafe = cultivos.some(c => c.cultura?.toLowerCase().includes("caf"));
    const safraLabel = getSafraLabel(safra);
    const fazendaAtual = unidadesProdutivasAutorizadas.find((fazenda) => fazenda.id === activeFazendaId);
    const contextoLabel = fazendaAtual?.nome ?? tenant?.nome ?? "Propriedade";
    
    // Se for a página principal (hub da safra) não expandimos o bloco de contexto (já tem lá)
    const isMainHub = pathname === `/agricola/safras/${safraId}`;

    const groups: NavGroup[] = [
        {
            key: "resumo",
            label: "Resumo",
            items: [
                { href: `/agricola/safras/${safraId}`, label: "Visão Geral", icon: Sprout, desc: "Resumo operacional da safra", color: "text-primary bg-primary/10" },
                ...(hasProfessionalTier ? [{ href: `/agricola/safras/${safraId}/dashboard`, label: "Dashboard", icon: Gauge, desc: "KPIs, riscos e cenários", color: "text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950/40" }] : []),
            ],
        },
        {
            key: "planejamento",
            label: "Planejamento",
            items: [
                { href: `/agricola/safras/${safraId}/orcamento`, label: "Orçamento", icon: BarChart2, desc: "Planejamento de custos e investimentos", color: "text-violet-600 bg-violet-50 dark:text-violet-400 dark:bg-violet-950/40" },
                { href: `/agricola/safras/${safraId}/production-units`, label: "Unidades", icon: Layers, desc: "Cultivo × área × participação", color: "text-cyan-600 bg-cyan-50 dark:text-cyan-400 dark:bg-cyan-950/40" },
                { href: `/agricola/safras/${safraId}/analises-solo`, label: "Solo", icon: FlaskConical, desc: "Análises e recomendações de adubação", color: "text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-950/40" },
                { href: `/agricola/safras/${safraId}/cenarios`, label: "Cenários", icon: BarChart2, desc: "Simulação econômica e projeções", color: "text-purple-600 bg-purple-50 dark:text-purple-400 dark:bg-purple-950/40" },
                { href: `/agricola/safras/${safraId}/planejamento-operacional`, label: "Planejamento Operacional", icon: ClipboardCheck, desc: "Insumos, mão de obra e compras em lote", color: "text-fuchsia-600 bg-fuchsia-50 dark:text-fuchsia-400 dark:bg-fuchsia-950/40" },
            ],
        },
        {
            key: "execucao",
            label: "Execução",
            items: [
                { href: `/agricola/safras/${safraId}/operacoes`, label: "Execução", icon: ClipboardList, desc: "Registro de operações de campo", color: "text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-950/40" },
                { href: `/agricola/safras/${safraId}/tarefas`, label: "Tarefas", icon: ListTodo, desc: "Planejamento e acompanhamento de tarefas", color: "text-indigo-600 bg-indigo-50 dark:text-indigo-400 dark:bg-indigo-950/40" },
                { href: `/agricola/safras/${safraId}/checklist`, label: "Checklist", icon: CheckSquare, desc: "Verificações da fase atual", color: "text-teal-600 bg-teal-50 dark:text-teal-400 dark:bg-teal-950/40" },
                { href: `/agricola/safras/${safraId}/estoque`, label: "Estoque", icon: Package, desc: "Controle de insumos e produtos", color: "text-orange-600 bg-orange-50 dark:text-orange-400 dark:bg-orange-950/40" },
            ],
        },
        {
            key: "monitoramento",
            label: "Monitoramento",
            items: [
                { href: `/agricola/safras/${safraId}/monitoramento`, label: "Sanidade", icon: Bug, desc: "Pragas, doenças e plantas daninhas", color: "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950/40" },
                { href: `/agricola/safras/${safraId}/fenologia`, label: "Fenologia", icon: Leaf, desc: "Estágios de desenvolvimento", color: "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-950/40" },
                ...(hasProfessionalTier ? [{ href: `/agricola/safras/${safraId}/ndvi`, label: "NDVI", icon: Satellite, desc: "Mapas de vigor vegetativo", color: "text-sky-600 bg-sky-50 dark:text-sky-400 dark:bg-sky-950/40" }] : []),
            ],
        },
        {
            key: "colheita",
            label: "Colheita",
            items: [
                { href: `/agricola/safras/${safraId}/romaneios`, label: "Romaneios", icon: Wheat, desc: "Registro de carga e pesagem", color: "text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-950/40" },
                ...(hasProfessionalTier && temCafe ? [{ href: `/agricola/safras/${safraId}/beneficiamento`, label: "Beneficiamento", icon: Coffee, desc: "Processamento pós-colheita", color: "text-orange-600 bg-orange-50 dark:text-orange-400 dark:bg-orange-950/40" }] : []),
            ],
        },
        {
            key: "gestao",
            label: "Gestão",
            items: [
                { href: `/agricola/safras/${safraId}/financeiro`, label: "Financeiro", icon: DollarSign, desc: "Fluxo de caixa, DRE e resultados", color: "text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950/40" },
                { href: `/agricola/safras/${safraId}/caderno`, label: "Caderno", icon: BookOpen, desc: "Anotações e diário de campo", color: "text-slate-600 bg-slate-50 dark:text-slate-400 dark:bg-slate-950/40" },
            ],
        },
    ];

    const isActive = (href: string) => {
        if (href === `/agricola/safras/${safraId}`) {
            return pathname === href;
        }
        return pathname === href || pathname.startsWith(`${href}/`);
    };

    const activeItem = groups
        .flatMap((g) => g.items)
        .find((item) => isActive(item.href));

    const activeGroup = groups.find((group) =>
        group.items.some((item) => isActive(item.href))
    );

    return (
        <div className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 flex flex-col">
            
            {/* Top row: Breadcrumbs & Mega Menu */}
            <div className="hidden md:flex items-center justify-between gap-4 px-6 py-2.5">
                <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground hidden lg:inline">Agricultura</span>
                    <ChevronRight className="size-3.5 text-muted-foreground hidden lg:inline" />
                    <Link href="/agricola/safras" className="text-sm text-muted-foreground hover:text-foreground hidden sm:inline">Safras</Link>
                    <ChevronRight className="size-3.5 text-muted-foreground hidden sm:inline" />
                    
                    <Link href={`/agricola/safras/${safraId}`} className="flex items-center gap-1.5 hover:opacity-80">
                        <Sprout className="size-4 text-emerald-600 dark:text-emerald-400" />
                        <span className="text-sm font-semibold tracking-tight text-foreground truncate max-w-[150px] lg:max-w-xs">{safraLabel}</span>
                    </Link>
                    
                    <ChevronRight className="size-3.5 text-muted-foreground" />
                    
                    {activeItem ? (
                        <span className="font-semibold text-xs text-primary bg-primary/10 px-2 py-0.5 rounded-sm border border-primary/20">
                            {activeItem.label}
                        </span>
                    ) : (
                        <span className="font-semibold text-xs text-primary bg-primary/10 px-2 py-0.5 rounded-sm border border-primary/20">
                            Visão Geral
                        </span>
                    )}
                </div>

                {/* Mega Menu */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="sm" className="gap-1.5">
                            <Grid className="size-3.5 text-muted-foreground" />
                            <span className="text-xs font-semibold">Módulos da Safra</span>
                            <ChevronDown className="size-3 text-muted-foreground" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-[650px] md:w-[750px] p-5 max-h-[85vh] overflow-y-auto rounded-sm border bg-popover shadow-md" align="end">
                        <div className="flex items-center gap-2 pb-3 mb-4 border-b">
                            <Grid className="size-4 text-emerald-600 dark:text-emerald-400" />
                            <span className="text-sm font-semibold text-foreground">Módulos de Gestão da Safra</span>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {groups.map((group) => (
                                <div key={group.key} className="space-y-2">
                                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                                        {group.label}
                                    </h3>
                                    <div className="space-y-1">
                                        {group.items.map((item) => {
                                            const Icon = item.icon;
                                            const active = isActive(item.href);
                                            return (
                                                <DropdownMenuItem
                                                    key={item.href}
                                                    onClick={() => router.push(item.href)}
                                                    className={cn(
                                                        "flex items-start gap-3 rounded-sm p-2 transition-colors cursor-pointer w-full text-left hover:bg-sidebar-accent",
                                                        active && "bg-primary/5 text-primary border-l-2 border-primary"
                                                    )}
                                                >
                                                    <div className={cn("size-7 rounded-sm flex items-center justify-center shrink-0", item.color)}>
                                                        <Icon className="size-3.5" />
                                                    </div>
                                                    <div className="min-w-0">
                                                        <p className={cn("text-xs font-semibold leading-tight", active ? "text-primary" : "text-foreground")}>
                                                            {item.label}
                                                        </p>
                                                        <p className="text-[10px] text-muted-foreground mt-0.5 leading-snug">
                                                            {item.desc}
                                                        </p>
                                                    </div>
                                                </DropdownMenuItem>
                                            );
                                        })}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            {/* Context Strip (Desktop) - Appears only when NOT on main hub */}
            {!isMainHub && (
                <div className="hidden md:flex items-center justify-between px-6 py-2 bg-muted/20 border-t">
                    {isLoadingSafra ? (
                        <div className="flex items-center gap-4">
                            <Skeleton className="h-6 w-32" />
                            <Skeleton className="h-6 w-24" />
                        </div>
                    ) : !safra ? (
                        <p className="text-sm text-muted-foreground">Safra não encontrada.</p>
                    ) : (
                        <div className="flex items-center gap-4 text-sm">
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold uppercase text-muted-foreground">{contextoLabel}</span>
                                <span className="font-semibold text-foreground">{safraLabel}</span>
                            </div>
                            <div className="w-px h-6 bg-border mx-2" />
                            <div className="flex items-center gap-2">
                                <Badge variant="outline" className="rounded-sm font-normal">Fase: <span className="font-semibold ml-1">{FASE_LABEL[safra.status] ?? safra.status}</span></Badge>
                                <span className={cn("text-[10px] uppercase font-bold px-1.5 py-0.5 rounded-sm border", FASE_COLOR[safra.status] || "bg-muted")}>
                                    {safra.status}
                                </span>
                            </div>
                        </div>
                    )}
                    <Button asChild size="sm" variant="ghost" className="h-8 gap-1.5 text-muted-foreground hover:text-foreground">
                        <Link href={`/agricola/safras/${safraId}`}>
                            <ArrowLeft className="size-3.5" /> Voltar ao Painel
                        </Link>
                    </Button>
                </div>
            )}

            {/* Mobile Navigation & Context */}
            <div className="flex flex-col md:hidden w-full border-b">
                <div className="flex items-center px-4 py-2 w-full">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm" className="w-full h-9 justify-between rounded-sm border-border/70 bg-background text-foreground">
                                <div className="flex items-center gap-2 text-left min-w-0">
                                    <Grid className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                                    <span className="font-semibold text-xs truncate">
                                        Módulo: {activeGroup?.label || "Geral"} &rsaquo; {activeItem?.label || "Visão Geral"}
                                    </span>
                                </div>
                                <ChevronDown className="size-4 shrink-0 text-muted-foreground ml-2" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-[calc(100vw-2rem)] max-h-[75vh] overflow-y-auto p-2" align="start">
                            {groups.map((group, idx) => {
                                const isGroupActive = group.items.some((item) => isActive(item.href));
                                return (
                                    <div key={group.key} className="space-y-1">
                                        {idx > 0 && <DropdownMenuSeparator className="my-1.5" />}
                                        <div className="px-2 py-1 flex items-center justify-between">
                                            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{group.label}</span>
                                            {isGroupActive && <Badge variant="secondary" className="h-4 px-1 text-[9px] bg-emerald-50 text-emerald-700">ativo</Badge>}
                                        </div>
                                        <div className="grid grid-cols-2 gap-1">
                                            {group.items.map((item) => {
                                                const Icon = item.icon;
                                                const itemActive = isActive(item.href);
                                                return (
                                                    <DropdownMenuItem
                                                        key={item.href}
                                                        onClick={() => router.push(item.href)}
                                                        className={cn(
                                                            "flex items-center gap-2 px-2 py-1.5 rounded-sm text-xs transition-colors w-full text-left",
                                                            itemActive && "bg-primary/5 text-primary font-semibold border-primary/20"
                                                        )}
                                                    >
                                                        <Icon className={cn("size-3.5 shrink-0", itemActive ? "text-primary" : "text-muted-foreground")} />
                                                        <span className="truncate">{item.label}</span>
                                                    </DropdownMenuItem>
                                                );
                                            })}
                                        </div>
                                    </div>
                                );
                            })}
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>

                {!isMainHub && safra && (
                    <div className="flex items-center justify-between px-4 py-2 bg-muted/20 text-xs">
                        <div className="flex flex-col truncate pr-2">
                            <span className="font-semibold text-foreground truncate">{safraLabel}</span>
                            <span className="text-muted-foreground truncate">{FASE_LABEL[safra.status] ?? safra.status}</span>
                        </div>
                        <Button asChild size="sm" variant="outline" className="h-7 px-2 shrink-0">
                            <Link href={`/agricola/safras/${safraId}`}>Voltar</Link>
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );
}
