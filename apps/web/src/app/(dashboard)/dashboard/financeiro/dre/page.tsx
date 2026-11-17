"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { 
    FileText, 
    TrendingUp, 
    TrendingDown, 
    Target,
    Calculator,
    PieChart,
    ArrowUpRight,
    ArrowDownRight,
    Info,
    LayoutDashboard,
    Sparkles,
    CheckCircle2,
    AlertCircle,
    Lightbulb,
    Zap,
    Save,
    Trash2,
    Plus,
    History,
    MoreHorizontal,
    Copy,
    ArrowLeftRight
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

// ── Types ─────────────────────────────────────────────────────────────────────

interface CategoriaBreakdown {
    nome: string;
    valor: number;
}

interface DREOperacional {
    receita_bruta: number;
    custos_operacionais: number;
    resultado_operacional: number;
    margem_percentual: number;
    breakdown_custos: CategoriaBreakdown[];
    breakdown_receitas: CategoriaBreakdown[];
}

interface DRESourceItem {
    natureza: string;
    fonte_oficial: string;
    origem_tipo: string | null;
    valor: number;
    meta: Record<string, unknown>;
}

interface DREAgricolaSection {
    valor: number;
    itens: DRESourceItem[];
}

interface DREAgricolaV1 {
    receita_bruta: number;
    custos_diretos: number;
    custos_operacionais: number;
    despesas_operacionais: number;
    resultado_operacional: number;
    kpis: { margem_pct: number | null };
    receita: DREAgricolaSection;
    custos_diretos_detalhe: DREAgricolaSection;
    custos_operacionais_detalhe: DREAgricolaSection;
    despesas_operacionais_detalhe: DREAgricolaSection;
}

interface Safra {
    id: string;
    ano_safra: string;
    cultura: string;
}

interface CenarioSafra {
    id: string;
    nome: string;
    receita_percentual: number;
    custos_percentual: number;
    resultado_simulado: number;
    margem_simulada: number;
    escolhido: boolean;
    escolhido_at: string | null;
    created_at: string;
}

interface DREAnalysisResponse {
    resumo: string;
    pontos_positivos: string[];
    pontos_atencao: string[];
    recomendacoes: string[];
    nivel_confianca: number;
    fonte: "IA" | "DETERMINISTICO";
    ia_disponivel: boolean;
    limite_atingido: boolean;
}

interface SimulacaoDREResponse {
    receita_real: number;
    custos_real: number;
    resultado_real: number;
    margem_real: number;
    receita_simulada: number;
    custos_simulados: number;
    resultado_simulado: number;
    margem_simulada: number;
    variacao_resultado: number;
    variacao_resultado_percentual: number;
}

interface AnaliseSimulacaoIA {
    impacto: string;
    riscos: string[];
    recomendacoes: string[];
    nivel_confianca: number;
    fonte: "IA" | "DETERMINISTICO";
    ia_disponivel: boolean;
    limite_atingido: boolean;
}
interface RecomendacaoCenarioResponse {
    cenario_recomendado_id: string | null;
    resumo: string;
    justificativas: string[];
    pontos_risco: string[];
    nivel_confianca: number;
    fonte: "IA" | "DETERMINISTICO";
    ia_disponivel: boolean;
    limite_atingido: boolean;
    motivo_fallback: string | null;
}

interface AnaliseDesvio {
    cenario_escolhido: string;
    resultado_real: number;
    resultado_planejado: number;
    desvio: number;
    desvio_percentual: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

function nomeCategoria(item: DRESourceItem): string {
    const categoria = item.meta.cost_category;
    if (typeof categoria === "string" && categoria.trim()) return categoria;
    return item.origem_tipo || item.fonte_oficial || item.natureza;
}

function consolidarCategorias(itens: DRESourceItem[]): CategoriaBreakdown[] {
    const totais = new Map<string, number>();
    for (const item of itens) {
        const categoria = nomeCategoria(item);
        totais.set(categoria, (totais.get(categoria) ?? 0) + item.valor);
    }
    return [...totais.entries()]
        .map(([nome, valor]) => ({ nome, valor }))
        .sort((a, b) => b.valor - a.valor);
}

function adaptarDreOficial(dre: DREAgricolaV1): DREOperacional {
    const itensCusto = [
        ...dre.custos_diretos_detalhe.itens,
        ...dre.custos_operacionais_detalhe.itens,
        ...dre.despesas_operacionais_detalhe.itens,
    ];
    return {
        receita_bruta: dre.receita_bruta,
        custos_operacionais: dre.custos_diretos + dre.custos_operacionais + dre.despesas_operacionais,
        resultado_operacional: dre.resultado_operacional,
        margem_percentual: dre.kpis.margem_pct ?? 0,
        breakdown_receitas: consolidarCategorias(dre.receita.itens),
        breakdown_custos: consolidarCategorias(itensCusto),
    };
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DREOperacionalPage() {
    const { activeFazendaId } = useAppStore();
    const searchParams = useSearchParams();
    const [selectedSafraId, setSelectedSafraId] = useState<string>("");

    // ── Simulation State ──
    const [simulacaoAberta, setSimulacaoAberta] = useState(false);
    const [ajusteReceita, setAjusteReceita] = useState(0);
    const [ajusteCustos, setAjusteCustos] = useState(0);

    // Deep link integration from Alertas Inteligentes (Step 193)
    useEffect(() => {
        const safraIdParam = searchParams.get("safra_id");
        const receitaParam = searchParams.get("receita");
        const custosParam = searchParams.get("custos");

        const autoSimularParam = searchParams.get("auto_simular");

        if (safraIdParam) {
            setSelectedSafraId(safraIdParam);
        }

        if (receitaParam !== null || custosParam !== null) {
            setSimulacaoAberta(true);
            if (receitaParam !== null) setAjusteReceita(parseInt(receitaParam));
            if (custosParam !== null) setAjusteCustos(parseInt(custosParam));

            if (autoSimularParam === "true") {
                toast("Copiloto: Simulação pré-configurada", {
                    description: "Os parâmetros foram ajustados conforme recomendação da IA para sua análise.",
                    icon: <Sparkles className="size-4 text-primary" />,
                });
            }
        }
    }, [searchParams]);

    // Fetch Safras
    const { data: safras = [] } = useQuery<Safra[]>({
        queryKey: ["safras", activeFazendaId],
        queryFn: () => apiFetch(`/safras/${activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : ""}`),
        enabled: !!activeFazendaId,
    });

    // Fetch DRE
    const { data: dreOficial, isLoading: loadingDRE } = useQuery<DREAgricolaV1>({
        queryKey: ["agricola-dre-v1", selectedSafraId],
        queryFn: () => apiFetch("/agricola/dre/v1", { params: { safra_id: selectedSafraId } }),
        enabled: !!selectedSafraId,
    });
    const dre = useMemo(
        () => (dreOficial ? adaptarDreOficial(dreOficial) : undefined),
        [dreOficial],
    );

    // Fetch IA Analysis
    const { data: iaAnalise, isLoading: loadingIA } = useQuery<DREAnalysisResponse>({
        queryKey: ["ia-dre-analise", selectedSafraId],
        queryFn: () => apiFetch(`/ia/financeiro/analise-dre`, { 
            method: "POST", 
            body: { safra_id: selectedSafraId } 
        }),
        enabled: !!selectedSafraId && !!dre,
        staleTime: 1000 * 60 * 5, // 5 min
    });

    const inputClass = "h-9 text-sm rounded-sm border border-border bg-background px-3 py-1 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all w-64 shadow-sm font-medium";

    const { data: simulacao, isLoading: loadingSimulacao } = useQuery<SimulacaoDREResponse>({
        queryKey: ["simulacao-dre", selectedSafraId, ajusteReceita, ajusteCustos],
        queryFn: () => apiFetch(`/financeiro/lancamentos/dre/simular`, {
            method: "POST",
            body: {
                safra_id: selectedSafraId,
                ajustes: {
                    receita_percentual: ajusteReceita,
                    custos_percentual: ajusteCustos
                }
            }
        }),
        enabled: simulacaoAberta && !!selectedSafraId,
    });

    const [simulacaoIA, setSimulacaoIA] = useState<AnaliseSimulacaoIA | null>(null);

    // Fetch Simulation IA Analysis
    const { isLoading: loadingSimulacaoIA } = useQuery<AnaliseSimulacaoIA>({
        queryKey: ["simulacao-ia", selectedSafraId, ajusteReceita, ajusteCustos],
        queryFn: () => apiFetch(`/ia/financeiro/simulacao`, {
            method: "POST",
            body: {
                safra_id: selectedSafraId,
                ajustes: {
                    receita_percentual: ajusteReceita,
                    custos_percentual: ajusteCustos
                }
            }
        }),
        enabled: simulacaoAberta && !!selectedSafraId && !!simulacao,
        staleTime: 1000 * 30, // 30s
    });

    // ── Scenarios State & Handlers ──
    const [nomeCenario, setNomeCenario] = useState("");
    const [salvandoCenario, setSalvandoCenario] = useState(false);
    const [idsCenariosParaComparar, setIdsCenariosParaComparar] = useState<string[]>([]);

    // Listar Cenários
    const { data: cenarios = [], refetch: refetchCenarios } = useQuery<CenarioSafra[]>({
        queryKey: ["financeiro-cenarios", selectedSafraId],
        queryFn: () => apiFetch(`/financeiro/lancamentos/dre/cenarios`, { params: { safra_id: selectedSafraId } }),
        enabled: !!selectedSafraId,
    });

    const handleSalvarCenario = async () => {
        if (!nomeCenario || !simulacao) {
            toast.error("Informe um nome para o cenário e ajuste os valores.");
            return;
        }
        setSalvandoCenario(true);
        try {
            await apiFetch(`/financeiro/lancamentos/dre/cenarios`, {
                method: "POST",
                body: {
                    safra_id: selectedSafraId,
                    nome: nomeCenario,
                    receita_percentual: ajusteReceita,
                    custos_percentual: ajusteCustos,
                    resultado_simulado: simulacao.resultado_simulado,
                    margem_simulada: simulacao.margem_simulada
                }
            });

            // Step 201: Concluir ação assistida se houver
            const actionId = searchParams.get("action_id");
            if (actionId) {
                apiFetch(`/ia/acoes-assistidas/${actionId}/concluir`, { method: "PATCH" }).catch(() => {});
            }

            setNomeCenario("");
            refetchCenarios();
            toast.success("Cenário salvo com sucesso!");
        } catch (error) {
            console.error(error);
            toast.error("Erro ao salvar cenário.");
        } finally {
            setSalvandoCenario(false);
        }
    };

    const handleDeletarCenario = async (id: string) => {
        try {
            await apiFetch(`/financeiro/lancamentos/dre/cenarios/${id}`, { method: "DELETE" });
            refetchCenarios();
            toast.success("Cenário removido.");
        } catch (error) {
            console.error(error);
            toast.error("Erro ao remover cenário.");
        }
    };

    const toggleComparacao = (id: string) => {
        setIdsCenariosParaComparar(prev => 
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        );
    };

    const cenariosParaComparar = cenarios.filter(c => idsCenariosParaComparar.includes(c.id));
    const melhorCenario = [...cenarios].sort((a, b) => b.resultado_simulado - a.resultado_simulado)[0];
    const cenarioEscolhido = cenarios.find(c => c.escolhido);

    // Buscar Análise de Desvio (Real vs Planejado)
    const { data: analiseDesvio, refetch: refetchAnalise } = useQuery<AnaliseDesvio>({
        queryKey: ["analise-desvio", selectedSafraId, cenarioEscolhido?.id],
        queryFn: () => apiFetch(`/financeiro/lancamentos/dre/cenarios/analise`, { params: { safra_id: selectedSafraId } }),
        enabled: !!selectedSafraId && !!cenarioEscolhido,
    });

    const handleEscolherCenario = async (id: string) => {
        try {
            await apiFetch(`/financeiro/lancamentos/dre/cenarios/${id}/escolher`, { method: "PATCH" });
            
            // Step 201: Concluir ação assistida se houver
            const actionId = searchParams.get("action_id");
            if (actionId) {
                apiFetch(`/ia/acoes-assistidas/${actionId}/concluir`, { method: "PATCH" }).catch(() => {});
            }

            refetchCenarios();
            refetchAnalise();
            toast.success("Cenário marcado como decisão oficial!");
        } catch (error) {
            console.error(error);
            toast.error("Erro ao escolher cenário.");
        }
    };

    const [iaRecomendacao, setIaRecomendacao] = useState<RecomendacaoCenarioResponse | null>(null);
    const [loadingRecomendacao, setLoadingRecomendacao] = useState(false);

    const handleIaRecomendar = async () => {
        if (!selectedSafraId) return;
        setLoadingRecomendacao(true);
        try {
            const res = await apiFetch<RecomendacaoCenarioResponse>(`/ia/financeiro/recomendar-cenario`, {
                method: "POST",
                body: { safra_id: selectedSafraId }
            });
            setIaRecomendacao(res);
            toast.success("Recomendação gerada pela IA!");
        } catch (error) {
            console.error(error);
            toast.error("Erro ao gerar recomendação da IA.");
        } finally {
            setLoadingRecomendacao(false);
        }
    };

    return (
        <div className="flex flex-col gap-6 p-6">
            <PageHeader
                title="DRE Operacional"
                description="Resultado consolidado por safra, com custos apropriados e despesas sem dupla contagem financeira."
                icon={<FileText size={22} className="text-primary" />}
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro/lancamentos" },
                    { label: "DRE Operacional" }
                ]}
                actions={
                    <div className="flex items-center gap-4">
                        <Button 
                            variant="outline"
                            size="sm"
                            onClick={handleIaRecomendar}
                            disabled={loadingRecomendacao || cenarios.length === 0}
                            className="flex items-center gap-2 rounded-sm"
                        >
                            {loadingRecomendacao ? <History size={14} className="animate-spin" /> : <Sparkles size={14} />}
                            IA Recomendar
                        </Button>
                        <Button 
                            variant="outline"
                            size="sm"
                            onClick={() => setSimulacaoAberta(!simulacaoAberta)}
                            className="flex items-center gap-2 rounded-sm"
                        >
                            <Calculator size={14} />
                            {simulacaoAberta ? "Fechar Simulação" : "Simular Cenário"}
                        </Button>
                        <div className="flex items-center gap-2 w-64">
                            <Select value={selectedSafraId} onValueChange={setSelectedSafraId}>
                                <SelectTrigger className="h-9 rounded-sm">
                                    <SelectValue placeholder="Selecione uma safra..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {safras.map((s) => (
                                        <SelectItem key={s.id} value={s.id}>
                                            {s.ano_safra} - {s.cultura}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                }
            />

            {!selectedSafraId ? (
                <div className="flex flex-col items-center justify-center py-20 bg-muted/20 rounded-sm border border-dashed border-border">
                    <LayoutDashboard size={48} className="text-muted-foreground/30 mb-4" />
                    <h3 className="text-lg font-bold text-muted-foreground">Selecione uma safra para visualizar o DRE</h3>
                    <p className="text-sm text-muted-foreground/60">Os dados operacionais serão consolidados automaticamente.</p>
                </div>
            ) : loadingDRE ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[1,2,3,4].map(i => <Skeleton key={i} className="h-24 w-full rounded-sm" />)}
                </div>
            ) : (
                <>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <CheckCircle2 className="size-4 text-primary" />
                        Fonte econômica: DRE Agrícola v1. Pagamentos e extratos bancários são usados apenas na conciliação.
                    </div>
                    {/* ── IA Recommendation Card ── */}
                    {iaRecomendacao && (
                        <Card className="rounded-sm border border-primary/25 bg-card shadow-sm animate-in slide-in-from-top duration-300 mb-6 overflow-hidden">
                            <div className="h-1 w-full bg-primary" />
                            <CardHeader className="pb-3 flex flex-row items-start justify-between gap-4 border-b bg-muted/20">
                                <div className="flex items-start gap-2.5">
                                    <div className="p-2 rounded-sm bg-primary/10 text-primary border border-primary/20 shrink-0">
                                        <Sparkles size={16} />
                                    </div>
                                    <div className="space-y-0.5">
                                        <CardTitle className="text-sm font-semibold text-foreground">
                                            Recomendação de Cenário DeepFarmIA
                                        </CardTitle>
                                        <CardDescription className="text-xs text-muted-foreground">
                                            Análise comparativa de cenários simulados
                                        </CardDescription>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                    <Badge
                                        variant="outline"
                                        className={`rounded-sm text-[11px] font-medium ${
                                            iaRecomendacao.fonte === "IA"
                                                ? "bg-primary/10 text-primary border-primary/25"
                                                : "bg-muted text-muted-foreground border-border"
                                        }`}
                                    >
                                        Fonte: {iaRecomendacao.fonte}
                                    </Badge>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-7 px-2 rounded-sm text-xs"
                                        onClick={() => setIaRecomendacao(null)}
                                    >
                                        Fechar
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent className="pt-4 space-y-4">
                                {iaRecomendacao.fonte === "DETERMINISTICO" && (
                                    <div className="bg-amber-500/10 border border-amber-500/25 p-3 rounded-sm flex items-start gap-3">
                                        <AlertCircle size={16} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                                        <div className="text-xs text-foreground space-y-1">
                                            <p className="font-semibold text-amber-800 dark:text-amber-300">Análise Matemática (Fallback)</p>
                                            <p className="text-muted-foreground">
                                                A recomendação foi baseada estritamente na maior margem projetada.
                                                {iaRecomendacao.limite_atingido
                                                    ? " A sua cota mensal de requisições de Inteligência Artificial foi atingida."
                                                    : iaRecomendacao.motivo_fallback === "SISTEMA_OFFLINE"
                                                        ? " O serviço de Inteligência Artificial está temporariamente indisponível no sistema."
                                                        : iaRecomendacao.motivo_fallback === "PLANO_INADEQUADO"
                                                            ? " O serviço avançado de Inteligência Artificial não está disponível no seu plano atual."
                                                            : ""}
                                            </p>
                                        </div>
                                    </div>
                                )}

                                <div className="p-3.5 bg-muted/30 rounded-sm border border-border/70">
                                    <p className="text-sm font-medium text-foreground leading-relaxed">
                                        {iaRecomendacao.resumo}
                                    </p>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="rounded-sm border border-border/70 p-3.5 space-y-2.5 bg-background/60">
                                        <h4 className="text-xs font-semibold uppercase text-emerald-700 dark:text-emerald-400 tracking-wide flex items-center gap-1.5">
                                            <CheckCircle2 size={14} /> Justificativas da Escolha
                                        </h4>
                                        <ul className="space-y-1.5">
                                            {iaRecomendacao.justificativas.map((j, i) => (
                                                <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                                                    <span>{j}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div className="rounded-sm border border-border/70 p-3.5 space-y-2.5 bg-background/60">
                                        <h4 className="text-xs font-semibold uppercase text-destructive tracking-wide flex items-center gap-1.5">
                                            <AlertCircle size={14} /> Pontos de Risco
                                        </h4>
                                        <ul className="space-y-1.5">
                                            {iaRecomendacao.pontos_risco.map((r, i) => (
                                                <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                                    <span className="h-1.5 w-1.5 rounded-full bg-destructive mt-1.5 shrink-0" />
                                                    <span>{r}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>

                                {iaRecomendacao.cenario_recomendado_id && (
                                    <div className="pt-3 border-t border-border/70 flex flex-wrap items-center justify-between gap-2">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-medium text-muted-foreground">Cenário Sugerido:</span>
                                            <Badge className="bg-primary text-primary-foreground border-none rounded-sm px-2.5 py-0.5 font-semibold text-xs">
                                                {cenarios.find(c => c.id === iaRecomendacao.cenario_recomendado_id)?.nome || "Cenário Selecionado"}
                                            </Badge>
                                        </div>
                                        <span className="text-xs font-medium text-muted-foreground">
                                            Confiança da Análise: <strong className="text-foreground">{(iaRecomendacao.nivel_confianca * 100).toFixed(0)}%</strong>
                                        </span>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    {/* ── Simulation Panel ── */}
                    {simulacaoAberta && (
                        <Card className="rounded-sm border border-border bg-card shadow-sm animate-in slide-in-from-top duration-300 mb-6 overflow-hidden">
                            <div className="h-1 w-full bg-amber-500" />
                            <CardHeader className="pb-3 border-b bg-muted/20">
                                <div className="flex flex-wrap items-center justify-between gap-4">
                                    <div className="flex items-start gap-2.5">
                                        <div className="p-2 rounded-sm bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 shrink-0">
                                            <Calculator size={16} />
                                        </div>
                                        <div className="space-y-0.5">
                                            <CardTitle className="text-sm font-semibold text-foreground">
                                                Simulador de Resultados (What-If)
                                            </CardTitle>
                                            <CardDescription className="text-xs text-muted-foreground">
                                                Ajuste as variáveis para projetar novos cenários
                                            </CardDescription>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end text-right">
                                        <span className="text-[11px] font-medium text-muted-foreground">Impacto Projetado</span>
                                        <span
                                            className={`text-lg font-bold tabular-nums ${
                                                (simulacao?.variacao_resultado ?? 0) >= 0
                                                    ? "text-emerald-700 dark:text-emerald-400"
                                                    : "text-destructive"
                                            }`}
                                        >
                                            {simulacao ? (simulacao.variacao_resultado >= 0 ? "+" : "") + fmt(simulacao.variacao_resultado) : "—"}
                                        </span>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="pt-4 space-y-5">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {/* Controles */}
                                    <div className="space-y-5 rounded-sm border border-border/70 p-4 bg-background/60">
                                        <div className="space-y-2.5">
                                            <div className="flex items-center justify-between">
                                                <label className="text-xs font-medium text-foreground flex items-center gap-2">
                                                    <TrendingUp size={14} className="text-emerald-600 dark:text-emerald-400" />
                                                    Variação na Receita (%)
                                                </label>
                                                <span
                                                    className={`text-xs font-bold tabular-nums ${
                                                        ajusteReceita >= 0
                                                            ? "text-emerald-700 dark:text-emerald-400"
                                                            : "text-destructive"
                                                    }`}
                                                >
                                                    {ajusteReceita > 0 ? "+" : ""}
                                                    {ajusteReceita}%
                                                </span>
                                            </div>
                                            <input
                                                type="range"
                                                min="-50"
                                                max="100"
                                                step="1"
                                                value={ajusteReceita}
                                                onChange={(e) => setAjusteReceita(parseInt(e.target.value))}
                                                className="w-full h-1.5 bg-muted rounded-sm appearance-none cursor-pointer accent-emerald-600"
                                            />
                                            <div className="flex justify-between text-[10px] text-muted-foreground font-medium">
                                                <span>-50%</span>
                                                <span>0%</span>
                                                <span>+100%</span>
                                            </div>
                                        </div>

                                        <div className="space-y-2.5">
                                            <div className="flex items-center justify-between">
                                                <label className="text-xs font-medium text-foreground flex items-center gap-2">
                                                    <TrendingDown size={14} className="text-destructive" />
                                                    Variação nos Custos (%)
                                                </label>
                                                <span
                                                    className={`text-xs font-bold tabular-nums ${
                                                        ajusteCustos <= 0
                                                            ? "text-emerald-700 dark:text-emerald-400"
                                                            : "text-destructive"
                                                    }`}
                                                >
                                                    {ajusteCustos > 0 ? "+" : ""}
                                                    {ajusteCustos}%
                                                </span>
                                            </div>
                                            <input
                                                type="range"
                                                min="-50"
                                                max="50"
                                                step="1"
                                                value={ajusteCustos}
                                                onChange={(e) => setAjusteCustos(parseInt(e.target.value))}
                                                className="w-full h-1.5 bg-muted rounded-sm appearance-none cursor-pointer accent-destructive"
                                            />
                                            <div className="flex justify-between text-[10px] text-muted-foreground font-medium">
                                                <span>-50%</span>
                                                <span>0%</span>
                                                <span>+50%</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Resumo Comparativo */}
                                    <div className="bg-muted/30 rounded-sm border border-border/70 p-4 space-y-4">
                                        <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wide">
                                            Projeção Comparativa
                                        </h4>

                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-1">
                                                <p className="text-[11px] font-medium text-muted-foreground">Resultado Real</p>
                                                <p className="text-base font-bold text-foreground tabular-nums">
                                                    {fmt(simulacao?.resultado_real ?? 0)}
                                                </p>
                                                <p className="text-[11px] text-muted-foreground">
                                                    Margem: {(simulacao?.margem_real ?? 0).toFixed(1)}%
                                                </p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-[11px] font-medium text-muted-foreground">Resultado Simulado</p>
                                                <p className="text-base font-bold text-foreground tabular-nums">
                                                    {fmt(simulacao?.resultado_simulado ?? 0)}
                                                </p>
                                                <p
                                                    className={`text-[11px] font-semibold ${
                                                        (simulacao?.margem_simulada ?? 0) >= (simulacao?.margem_real ?? 0)
                                                            ? "text-emerald-700 dark:text-emerald-400"
                                                            : "text-destructive"
                                                    }`}
                                                >
                                                    Margem: {(simulacao?.margem_simulada ?? 0).toFixed(1)}%
                                                </p>
                                            </div>
                                        </div>

                                        <div className="pt-3 border-t border-border/70">
                                            <div className="flex items-center justify-between mb-1.5">
                                                <span className="text-xs font-medium text-muted-foreground">
                                                    Variação de Lucratividade
                                                </span>
                                                <span
                                                    className={`text-xs font-bold tabular-nums ${
                                                        (simulacao?.variacao_resultado_percentual ?? 0) >= 0
                                                            ? "text-emerald-700 dark:text-emerald-400"
                                                            : "text-destructive"
                                                    }`}
                                                >
                                                    {(simulacao?.variacao_resultado_percentual ?? 0) > 0 ? "+" : ""}
                                                    {(simulacao?.variacao_resultado_percentual ?? 0).toFixed(1)}%
                                                </span>
                                            </div>
                                            <Progress
                                                value={Math.min(100, Math.abs(simulacao?.variacao_resultado_percentual ?? 0))}
                                                className="h-1.5"
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Save Scenario Controls */}
                                <div className="pt-3 border-t border-border/70 flex flex-col md:flex-row items-center justify-between gap-3">
                                    <div className="flex items-center gap-3 w-full md:w-auto">
                                        <label className="text-xs font-medium text-muted-foreground whitespace-nowrap">
                                            Nome do Cenário:
                                        </label>
                                        <Input
                                            placeholder="Ex: Otimista 2026, Redução de Custos..."
                                            className="h-8 text-xs rounded-sm w-full md:w-64"
                                            value={nomeCenario}
                                            onChange={(e) => setNomeCenario(e.target.value)}
                                        />
                                    </div>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleSalvarCenario}
                                        disabled={salvandoCenario || !nomeCenario || !simulacao}
                                        className="w-full md:w-auto flex items-center justify-center gap-2 rounded-sm"
                                    >
                                        {salvandoCenario ? <Plus size={14} className="animate-spin" /> : <Save size={14} />}
                                        Salvar Cenário
                                    </Button>
                                </div>

                                {/* IA Simulation Feedback */}
                                {simulacaoIA && (
                                    <div className="p-4 bg-muted/30 rounded-sm border border-border/70 space-y-3 animate-in fade-in duration-300">
                                        <div className="flex items-center gap-2 text-primary">
                                            <Sparkles size={15} />
                                            <h5 className="text-xs font-semibold uppercase tracking-wide">
                                                Análise Estratégica do Cenário
                                            </h5>
                                        </div>

                                        <p className="text-xs text-foreground leading-relaxed">
                                            {simulacaoIA.impacto}
                                        </p>

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                                            <div className="rounded-sm border border-border/70 p-3 bg-background/60 space-y-2">
                                                <h6 className="text-xs font-semibold text-destructive uppercase flex items-center gap-1.5">
                                                    <AlertCircle size={12} /> Riscos Identificados
                                                </h6>
                                                <ul className="space-y-1">
                                                    {(simulacaoIA.riscos || []).map((r, i) => (
                                                        <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                                            <span className="h-1.5 w-1.5 rounded-full bg-destructive mt-1.5 shrink-0" />
                                                            <span>{r}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                            <div className="rounded-sm border border-border/70 p-3 bg-background/60 space-y-2">
                                                <h6 className="text-xs font-semibold text-primary uppercase flex items-center gap-1.5">
                                                    <Lightbulb size={12} /> Recomendações
                                                </h6>
                                                <ul className="space-y-1">
                                                    {(simulacaoIA.recomendacoes || []).map((r, i) => (
                                                        <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                                            <span className="h-1.5 w-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
                                                            <span>{r}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    {/* ── Summary Cards ── */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-5">
                                <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider mb-1">Receita Bruta</p>
                                <div className="flex items-baseline gap-2">
                                    <h2 className="text-2xl font-black text-green-700 tabular-nums">{fmt(dre?.receita_bruta ?? 0)}</h2>
                                    <ArrowUpRight size={16} className="text-green-500" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-5">
                                <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider mb-1">Custos e Despesas</p>
                                <div className="flex items-baseline gap-2">
                                    <h2 className="text-2xl font-black text-red-700 tabular-nums">{fmt(dre?.custos_operacionais ?? 0)}</h2>
                                    <ArrowDownRight size={16} className="text-red-500" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="rounded-sm shadow-sm bg-primary/[0.02]">
                            <CardContent className="p-5">
                                <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider mb-1">Resultado Operacional</p>
                                <h2 className={`text-2xl font-black tabular-nums ${(dre?.resultado_operacional ?? 0) >= 0 ? "text-primary" : "text-destructive"}`}>
                                    {fmt(dre?.resultado_operacional ?? 0)}
                                </h2>
                            </CardContent>
                        </Card>

                        <Card className="rounded-sm shadow-sm">
                            <CardContent className="p-5">
                                <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider mb-1">Margem Operacional</p>
                                <div className="flex items-center gap-2">
                                    <h2 className="text-2xl font-black tabular-nums text-amber-700">
                                        {(dre?.margem_percentual ?? 0).toFixed(1)}%
                                    </h2>
                                    <Progress value={Math.max(0, Math.min(100, dre?.margem_percentual ?? 0))} className="h-2 w-16" />
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* ── Decision Tracking: Real vs Planned ── */}
                    {analiseDesvio && (
                        <Card className="rounded-sm shadow-md bg-indigo-50/20 border animate-in slide-in-from-right duration-500">
                            <CardHeader className="pb-2">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-1">
                                        <CardTitle className="text-sm font-bold flex items-center gap-2 text-indigo-900">
                                            <Target size={18} className="text-indigo-600" />
                                            Acompanhamento de Decisão: {analiseDesvio.cenario_escolhido}
                                        </CardTitle>
                                        <CardDescription className="text-[10px] uppercase font-bold text-indigo-700/60">Comparação entre planejamento oficial e execução real</CardDescription>
                                    </div>
                                    <Badge className="bg-indigo-600 text-white border-none rounded-sm px-2 py-0.5 font-bold text-[10px] uppercase">
                                        Cenário Oficial
                                    </Badge>
                                </div>
                            </CardHeader>
                            <CardContent className="py-4">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    <div className="space-y-1">
                                        <p className="text-[10px] font-bold text-muted-foreground uppercase">Resultado Planejado</p>
                                        <p className="text-lg font-black text-indigo-900 tabular-nums">{fmt(analiseDesvio.resultado_planejado)}</p>
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-[10px] font-bold text-muted-foreground uppercase">Resultado Real (Executado)</p>
                                        <p className="text-lg font-black text-foreground tabular-nums">{fmt(analiseDesvio.resultado_real)}</p>
                                    </div>
                                    <div className="p-3 rounded-sm bg-white border border-indigo-100 flex flex-col justify-center">
                                        <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Desvio da Meta</p>
                                        <div className="flex items-center gap-2">
                                            <span className={`text-xl font-black tabular-nums ${analiseDesvio.desvio >= 0 ? "text-green-600" : "text-red-600"}`}>
                                                {analiseDesvio.desvio >= 0 ? "+" : ""}{analiseDesvio.desvio_percentual.toFixed(1)}%
                                            </span>
                                            {analiseDesvio.desvio >= 0 ? <ArrowUpRight className="text-green-600" /> : <ArrowDownRight className="text-red-600" />}
                                        </div>
                                        <p className="text-[9px] font-bold text-muted-foreground">{fmt(Math.abs(analiseDesvio.desvio))} de diferença</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* ── Saved Scenarios Section ── */}
                    {cenarios.length > 0 && (
                        <Card className="rounded-sm shadow-sm border bg-muted/10">
                            <CardHeader className="pb-3 border-b border-border/50">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-1">
                                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                                            <History size={18} className="text-muted-foreground" />
                                            Cenários Salvos e Simulações
                                        </CardTitle>
                                        <CardDescription className="text-[10px] uppercase font-medium">Histórico de projeções realizadas para esta safra</CardDescription>
                                    </div>
                                    {cenarios.length > 1 && (
                                        <Badge variant="outline" className="text-[9px] font-bold uppercase">
                                            {cenarios.length} Cenários
                                        </Badge>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="p-0">
                                <div className="divide-y divide-border/50">
                                    {cenarios.map((c) => (
                                        <div key={c.id} className={`p-4 flex items-center justify-between transition-colors hover:bg-muted/30 ${c.escolhido ? "bg-indigo-50/40" : ""}`}>
                                            <div className="flex items-center gap-4">
                                                <div className={`h-8 w-8 rounded-sm flex items-center justify-center ${c.escolhido ? "bg-indigo-600 text-white" : "bg-muted text-muted-foreground"}`}>
                                                    {c.escolhido ? <CheckCircle2 size={16} /> : <PieChart size={16} />}
                                                </div>
                                                <div className="space-y-0.5">
                                                    <div className="flex items-center gap-2">
                                                        <h4 className="text-xs font-bold text-foreground">{c.nome}</h4>
                                                        {c.escolhido && <Badge className="text-[8px] h-4 bg-indigo-600 border-none font-black uppercase">Decisão</Badge>}
                                                        {c.id === melhorCenario?.id && !c.escolhido && <Badge variant="outline" className="text-[8px] h-4 border-green-200 bg-green-50 text-green-700 font-black uppercase">Mais Lucrativo</Badge>}
                                                    </div>
                                                    <div className="flex items-center gap-3 text-[10px] text-muted-foreground font-medium uppercase tracking-tighter">
                                                        <span>Receita: {c.receita_percentual > 0 ? "+" : ""}{c.receita_percentual}%</span>
                                                        <span>Custos: {c.custos_percentual > 0 ? "+" : ""}{c.custos_percentual}%</span>
                                                        <span className="text-border">|</span>
                                                        <span>{new Date(c.created_at).toLocaleDateString()}</span>
                                                    </div>
                                                </div>
                                            </div>
                                            
                                            <div className="flex items-center gap-6">
                                                <div className="text-right">
                                                    <p className="text-xs font-black text-foreground tabular-nums">{fmt(c.resultado_simulado)}</p>
                                                    <p className="text-[10px] font-bold text-muted-foreground uppercase">Margem: {c.margem_simulada.toFixed(1)}%</p>
                                                </div>
                                                
                                                <div className="flex items-center gap-1">
                                                    {!c.escolhido && (
                                                        <Button 
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-8 w-8 rounded-sm text-indigo-600 hover:bg-indigo-100 hover:text-indigo-700"
                                                            onClick={() => handleEscolherCenario(c.id)}
                                                            title="Marcar como escolhido"
                                                        >
                                                            <Target size={14} />
                                                        </Button>
                                                    )}
                                                    <Button 
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-8 w-8 rounded-sm text-red-500 hover:bg-red-100 hover:text-red-600"
                                                        onClick={() => handleDeletarCenario(c.id)}
                                                    >
                                                        <Trash2 size={14} />
                                                    </Button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* ── IA Analysis Card ── */}
                    <Card className="rounded-sm shadow-md overflow-hidden bg-gradient-to-br from-primary/[0.03] to-background border">
                        <CardHeader className="pb-3 flex flex-row items-center justify-between">
                            <div className="space-y-1">
                                <CardTitle className="text-sm font-bold flex items-center gap-2 text-primary">
                                    <Sparkles size={18} className="text-primary animate-pulse" />
                                    Análise Inteligente da Safra
                                </CardTitle>
                                <CardDescription className="text-[10px] uppercase font-medium">Interpretação estratégica dos resultados financeiros</CardDescription>
                            </div>
                            {iaAnalise?.fonte === "IA" && (
                                <Badge variant="outline" className="text-[9px] bg-primary/10 text-primary border-primary/20 rounded-full px-2 py-0">
                                    PROCESSADO POR IA
                                </Badge>
                            )}
                        </CardHeader>
                        <CardContent>
                            {loadingIA ? (
                                <div className="space-y-3 py-4">
                                    <Skeleton className="h-4 w-3/4 rounded-sm" />
                                    <Skeleton className="h-20 w-full rounded-sm" />
                                    <div className="grid grid-cols-3 gap-4">
                                        <Skeleton className="h-16 rounded-sm" />
                                        <Skeleton className="h-16 rounded-sm" />
                                        <Skeleton className="h-16 rounded-sm" />
                                    </div>
                                </div>
                            ) : iaAnalise ? (
                                <div className="space-y-6">
                                    <div className="p-4 bg-primary/5 rounded-sm border border-primary/10">
                                        <p className="text-sm font-medium text-foreground leading-relaxed italic">
                                            "{iaAnalise.resumo}"
                                        </p>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                        {/* Pontos Positivos */}
                                        <div className="space-y-3">
                                            <h4 className="text-[10px] font-black uppercase text-green-700 tracking-wider flex items-center gap-1.5">
                                                <CheckCircle2 size={12} /> Pontos Positivos
                                            </h4>
                                            <ul className="space-y-2">
                                                {iaAnalise.pontos_positivos.map((p, i) => (
                                                    <li key={i} className="text-[11px] text-muted-foreground flex items-start gap-2">
                                                        <span className="h-1.5 w-1.5 rounded-full bg-green-500 mt-1 shrink-0" />
                                                        {p}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>

                                        {/* Pontos de Atenção */}
                                        <div className="space-y-3">
                                            <h4 className="text-[10px] font-black uppercase text-amber-700 tracking-wider flex items-center gap-1.5">
                                                <AlertCircle size={12} /> Pontos de Atenção
                                            </h4>
                                            <ul className="space-y-2">
                                                {iaAnalise.pontos_atencao.map((p, i) => (
                                                    <li key={i} className="text-[11px] text-muted-foreground flex items-start gap-2">
                                                        <span className="h-1.5 w-1.5 rounded-full bg-amber-500 mt-1 shrink-0" />
                                                        {p}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>

                                        {/* Recomendações */}
                                        <div className="space-y-3">
                                            <h4 className="text-[10px] font-black uppercase text-primary tracking-wider flex items-center gap-1.5">
                                                <Lightbulb size={12} /> Recomendações
                                            </h4>
                                            <ul className="space-y-2">
                                                {iaAnalise.recomendacoes.map((p, i) => (
                                                    <li key={i} className="text-[11px] text-muted-foreground flex items-start gap-2">
                                                        <span className="h-1.5 w-1.5 rounded-full bg-primary mt-1 shrink-0" />
                                                        {p}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>
                                    
                                    <div className="flex items-center justify-between pt-2 border-t border-border/50">
                                        <div className="flex items-center gap-4 text-[9px] text-muted-foreground font-medium uppercase tracking-tighter">
                                            <span className="flex items-center gap-1">
                                                Confiança: <span className={iaAnalise.nivel_confianca > 0.8 ? "text-green-600" : "text-amber-600"}>{(iaAnalise.nivel_confianca * 100).toFixed(0)}%</span>
                                            </span>
                                            <span className="flex items-center gap-1">
                                                Modelo: <span className="text-foreground">CLAUDE-HAIKU</span>
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1 text-[9px] font-bold text-primary italic">
                                            <Zap size={10} /> Powered by DeepFarmIA
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="py-10 text-center text-muted-foreground text-xs italic">
                                    Não foi possível gerar a análise inteligente neste momento.
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* ── Breakdown Receitas ── */}
                        <Card className="rounded-sm shadow-sm border">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                                <div className="space-y-1">
                                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                                        <TrendingUp size={16} className="text-green-600" />
                                        Estrutura de Receitas
                                    </CardTitle>
                                    <CardDescription className="text-[10px] uppercase">Distribuição por categoria de entrada</CardDescription>
                                </div>
                                <Badge variant="secondary" className="rounded-sm bg-green-100 text-green-700 border-green-200">
                                    {dre?.breakdown_receitas.length} CATEGORIAS
                                </Badge>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {dre?.breakdown_receitas.length === 0 ? (
                                    <p className="text-xs text-center py-10 text-muted-foreground italic">Nenhuma receita registrada.</p>
                                ) : (
                                    dre?.breakdown_receitas.map((item, idx) => (
                                        <div key={idx} className="space-y-1.5">
                                            <div className="flex items-center justify-between text-xs">
                                                <span className="font-bold text-muted-foreground">{item.nome.replace("_", " ")}</span>
                                                <span className="font-black tabular-nums text-foreground">{fmt(item.valor)}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Progress 
                                                    value={(item.valor / (dre.receita_bruta || 1)) * 100} 
                                                    className="h-1.5 bg-green-100 [&>div]:bg-green-600" 
                                                />
                                                <span className="text-[10px] font-bold text-muted-foreground w-10 text-right">
                                                    {((item.valor / (dre.receita_bruta || 1)) * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </CardContent>
                        </Card>

                        {/* ── Breakdown Custos ── */}
                        <Card className="rounded-sm shadow-sm border">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                                <div className="space-y-1">
                                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                                        <TrendingDown size={16} className="text-red-600" />
                                        Estrutura de Custos
                                    </CardTitle>
                                    <CardDescription className="text-[10px] uppercase">Distribuição por categoria de saída</CardDescription>
                                </div>
                                <Badge variant="secondary" className="rounded-sm bg-red-100 text-red-700 border-red-200">
                                    {dre?.breakdown_custos.length} CATEGORIAS
                                </Badge>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {dre?.breakdown_custos.length === 0 ? (
                                    <p className="text-xs text-center py-10 text-muted-foreground italic">Nenhum custo registrado.</p>
                                ) : (
                                    dre?.breakdown_custos.map((item, idx) => (
                                        <div key={idx} className="space-y-1.5">
                                            <div className="flex items-center justify-between text-xs">
                                                <span className="font-bold text-muted-foreground">{item.nome.replace("_", " ")}</span>
                                                <span className="font-black tabular-nums text-foreground">{fmt(item.valor)}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Progress 
                                                    value={(item.valor / (dre.custos_operacionais || 1)) * 100} 
                                                    className="h-1.5 bg-red-100 [&>div]:bg-red-600" 
                                                />
                                                <span className="text-[10px] font-bold text-muted-foreground w-10 text-right">
                                                    {((item.valor / (dre.custos_operacionais || 1)) * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    <Card className="rounded-sm shadow-sm border bg-muted/5">
                        <CardContent className="p-4 flex items-center justify-between">
                            <div className="flex items-center gap-2 text-muted-foreground">
                                <Info size={14} />
                                <span className="text-[10px] font-medium uppercase tracking-wider">
                                    Os valores apresentados são baseados em lançamentos confirmados e projeções de safra.
                                </span>
                            </div>
                            <Badge variant="outline" className="text-[9px] font-bold text-muted-foreground uppercase">
                                Última Atualização: {new Date().toLocaleTimeString()}
                            </Badge>
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
}
