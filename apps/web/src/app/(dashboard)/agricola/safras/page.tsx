"use client";

import { useState, useEffect, Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter, CardAction } from "@/components/ui/card";

import {
    AlertTriangle,
    Sprout, Plus, Calendar,
    TrendingUp, Target, ClipboardList,
    ChevronRight
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { SafraCreateDialog } from "@/components/agricola/safra-create-dialog";


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

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
    PLANEJADA: { label: "Planejada", color: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20", dot: "bg-blue-500" },
    PREPARO_SOLO: { label: "Preparo Solo", color: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20", dot: "bg-amber-500" },
    PLANTIO: { label: "Plantio", color: "bg-lime-500/10 text-lime-700 dark:text-lime-400 border-lime-500/20", dot: "bg-lime-500" },
    DESENVOLVIMENTO: { label: "Desenvolvimento", color: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20", dot: "bg-emerald-500" },
    COLHEITA: { label: "Colheita", color: "bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20", dot: "bg-orange-500" },
    POS_COLHEITA: { label: "Pós-Colheita", color: "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20", dot: "bg-purple-500" },
    ENCERRADA: { label: "Encerrada", color: "bg-muted text-muted-foreground border-border", dot: "bg-muted-foreground" },
    CANCELADA: { label: "Cancelada", color: "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20", dot: "bg-red-500" },
};

const PHASES_ORDER = [
    "PLANEJADA",
    "PREPARO_SOLO",
    "PLANTIO",
    "DESENVOLVIMENTO",
    "COLHEITA",
    "POS_COLHEITA",
    "ENCERRADA"
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
    const cfg = STATUS_CONFIG[status] ?? { label: status, color: "bg-muted", dot: "bg-muted-foreground" };
    return (
        <Badge variant="outline" className={cn("gap-1.5 font-normal text-xs", cfg.color)}>
            <span className={cn("size-1.5 rounded-full", cfg.dot)} />
            {cfg.label}
        </Badge>
    );
}

function StatusSummary({ safras }: { safras: Safra[] }) {
    const counts: Record<string, number> = {};
    safras.forEach((s) => { counts[s.status] = (counts[s.status] || 0) + 1; });

    const active = safras.filter((s) => !["ENCERRADA", "CANCELADA"].includes(s.status));
    const planejadas = counts["PLANEJADA"] ?? 0;

    const kpis = [
        {
            label: "Total Cadastradas",
            value: safras.length.toString(),
            sub: "todas as safras",
            icon: Sprout,
            color: "text-slate-600",
            bg: "bg-slate-100 dark:bg-slate-900/30",
        },
        {
            label: "Em Andamento",
            value: active.length.toString(),
            sub: "safras ativas",
            icon: Calendar,
            color: "text-emerald-600",
            bg: "bg-emerald-100 dark:bg-emerald-900/30",
        },
        {
            label: "Planejadas",
            value: planejadas.toString(),
            sub: "aguardando início",
            icon: Target,
            color: "text-blue-600",
            bg: "bg-blue-100 dark:bg-blue-900/30",
        },
        {
            label: "Encerradas",
            value: (counts["ENCERRADA"] ?? 0).toString(),
            sub: "safra(s) concluída(s)",
            icon: TrendingUp,
            color: "text-purple-600",
            bg: "bg-purple-100 dark:bg-purple-900/30",
        },
    ];

    return (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((k) => (
                <Card key={k.label} className="shadow-sm">
                    <CardContent className="p-5 flex items-start gap-4">
                        <div className={cn("size-10 rounded-sm flex items-center justify-center shrink-0", k.bg)}>
                            <k.icon className={cn("size-5", k.color)} />
                        </div>
                        <div className="min-w-0">
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">{k.label}</p>
                            <p className="text-2xl font-bold tabular-nums leading-tight mt-0.5">{k.value}</p>
                            <p className="text-xs text-muted-foreground mt-1">{k.sub}</p>
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}

function SafraCard({ safra, redirect }: { safra: Safra; redirect: string | null }) {
    const router = useRouter();
    const cfg = STATUS_CONFIG[safra.status] ?? { label: safra.status, color: "bg-muted", dot: "bg-muted-foreground" };

    const currentIndex = PHASES_ORDER.indexOf(safra.status);
    const progress = currentIndex >= 0 ? ((currentIndex + 1) / PHASES_ORDER.length) * 100 : 0;
    const destino = `/agricola/safras/${safra.id}${redirect ? `/${redirect}` : ""}`;

    return (
        <Card className="hover:border-primary/50 transition-colors cursor-pointer group flex flex-col" onClick={() => router.push(destino)}>
            <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                    <div className="size-10 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                        <Sprout className="size-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                        <CardTitle className="text-lg leading-none">
                            {safra.ano_safra}
                        </CardTitle>
                        <CardDescription className="mt-1 truncate">
                            {safra.cultura ?? "Multi-cultivo"}
                        </CardDescription>
                    </div>
                    <CardAction className="ml-auto">
                        <Badge variant="outline" className={cn("gap-1.5 font-normal text-xs", cfg.color)}>
                            <span className={cn("size-1.5 rounded-full", cfg.dot)} />
                            {cfg.label}
                        </Badge>
                    </CardAction>
                </div>
            </CardHeader>
            <CardContent className="pt-0 flex-1">
                <div className="space-y-1.5">
                    <div className="flex justify-between text-xs text-muted-foreground font-medium">
                        <span>Progresso do Ciclo</span>
                        <span>{Math.round(progress)}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-primary rounded-full transition-all duration-500"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                </div>
            </CardContent>
            <CardFooter className="justify-between">
                <span className="text-xs text-muted-foreground">
                    Criada em {new Date(safra.created_at).toLocaleDateString("pt-BR")}
                </span>
                <Button variant="outline" size="sm">
                    Acessar Painel <ChevronRight className="size-3" />
                </Button>
            </CardFooter>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const REDIRECTS_PERMITIDOS = new Set(["orcamento", "planejamento-operacional", "beneficiamento"]);

export default function SafrasPage() {
    return (
        <Suspense fallback={<div className="space-y-6 p-6"><Skeleton className="h-10 w-64" /><Skeleton className="h-64 w-full rounded-sm" /></div>}>
            <SafrasPageContent />
        </Suspense>
    );
}

function SafrasPageContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const redirectParam = searchParams.get("redirect");
    const redirect = redirectParam && REDIRECTS_PERMITIDOS.has(redirectParam) ? redirectParam : null;
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [selectedFase, setSelectedFase] = useState<string>("todas");
    const [loadTimeout, setLoadTimeout] = useState(false);

    const { data: safras = [], isLoading, error } = useQuery<Safra[]>({
        queryKey: ["safras"],
        queryFn: () => apiFetch<Safra[]>("/safras/"),
        retry: 1,
        staleTime: 1000 * 60 * 5, // 5 minutos
    });

    useEffect(() => {
        if (!isLoading) return;
        const timer = setTimeout(() => setLoadTimeout(true), 5000);
        return () => {
            clearTimeout(timer);
            setLoadTimeout(false);
        };
    }, [isLoading]);

    const filteredSafras = safras.filter(s => selectedFase === "todas" || s.status === selectedFase);

    if (isLoading) {
        return (
            <div className="space-y-6 p-6">
                {loadTimeout && (
                    <Alert variant="warning">
                        <AlertTriangle />
                        <AlertTitle>Carregamento demorando...</AlertTitle>
                        <AlertDescription>
                            O servidor está demorando para responder. Verifique sua conexão.
                        </AlertDescription>
                    </Alert>
                )}
                <Skeleton className="h-10 w-64" />
                <div className="grid grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map((i) => (
                        <Skeleton key={i} className="h-28 rounded-sm" />
                    ))}
                </div>
                <Skeleton className="h-64 w-full rounded-sm" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-6 p-6">
                <PageHeader title="Safras" />
                <Alert variant="destructive">
                    <AlertTriangle />
                    <AlertTitle>Erro ao carregar safras:</AlertTitle>
                    <AlertDescription>
                        {error instanceof Error ? error.message : String(error)}
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <PageHeader
                title="Safras"
                description="Gerencie o ciclo de vida das suas culturas por talhão."
                icon={<ClipboardList className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Safras" }]}
                actions={
                    <Button variant="outline" size="sm" onClick={() => setIsAddOpen(true)}>
                        <Plus className="size-3.5 mr-1.5" /> Nova Safra
                    </Button>
                }
            />

            {/* KPIs */}
            <StatusSummary safras={safras} />

            {/* Filtros e Tabela */}
            <div className="space-y-4">
                <div className="flex items-center justify-between gap-4 bg-card p-4 border rounded-sm shadow-sm">
                    <div>
                        <h3 className="text-sm font-semibold">Listagem de Safras</h3>
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mt-0.5">
                            {safras.filter(s => selectedFase === "todas" || s.status === selectedFase).length} registros encontrados
                        </p>
                    </div>
                    <Select value={selectedFase} onValueChange={setSelectedFase}>
                        <SelectTrigger className="w-44 h-8 text-xs rounded-sm">
                            <SelectValue placeholder={selectedFase === "todas" ? "Todas as fases" : STATUS_CONFIG[selectedFase]?.label || "Todas as fases"} />
                        </SelectTrigger>
                        <SelectContent className="rounded-sm">
                            <SelectItem value="todas">Todas as fases</SelectItem>
                            {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
                                <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {filteredSafras.length === 0 ? (
                    <Card className="border-dashed shadow-none bg-transparent">
                        <CardContent className="flex flex-col items-center justify-center p-12 text-center">
                            <div className="size-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-4">
                                <Sprout className="size-6 text-slate-400" />
                            </div>
                            <p className="text-base font-medium">Nenhuma safra encontrada</p>
                            <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                                {selectedFase === "todas"
                                    ? "Você ainda não possui nenhuma safra cadastrada. Clique em Nova Safra para começar."
                                    : "Nenhuma safra encontrada para a fase selecionada."}
                            </p>
                            {selectedFase === "todas" && (
                                <Button variant="outline" onClick={() => setIsAddOpen(true)} className="mt-6">
                                    <Plus className="size-4 mr-2" />
                                    Cadastrar Primeira Safra
                                </Button>
                            )}
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        {filteredSafras.map(safra => (
                            <SafraCard key={safra.id} safra={safra} redirect={redirect} />
                        ))}
                    </div>
                )}
            </div>

            {/* Dialog */}
            <SafraCreateDialog open={isAddOpen} onOpenChange={setIsAddOpen} />
        </div>
    );
}
