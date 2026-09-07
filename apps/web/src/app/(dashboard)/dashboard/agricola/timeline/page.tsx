"use client";

import { useState, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
    Tooltip, TooltipContent, TooltipProvider, TooltipTrigger
} from "@/components/ui/tooltip";
import { CalendarDays, Tractor, ChevronLeft, ChevronRight } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { format, addMonths, subMonths, startOfMonth, endOfMonth, differenceInDays, parseISO, isValid, addDays } from "date-fns";
import { ptBR } from "date-fns/locale";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Safra {
    id: string;
    ano_safra: string;
    cultura: string;
    status: string;
    area_plantada_ha?: number;
    data_plantio_prevista?: string;
    data_plantio_real?: string;
    data_colheita_prevista?: string;
    data_colheita_real?: string;
    talhao_id?: string;
    talhao_nome?: string;
}

interface Operacao {
    id: string;
    tipo_operacao: string;
    data_operacao: string;
    safra_id?: string;
    talhao_id?: string;
    area_ha?: number;
    status: string;
    descricao?: string;
    responsavel?: string;
}

interface TipoOperacao {
    id: string;
    tipo_operacao: string;
    fases_permitidas: string[];
    descricao?: string | null;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const TIPO_CONFIG: Record<string, { color: string; label: string }> = {
    PLANTIO:      { color: "#22c55e", label: "Plantio" },
    COLHEITA:     { color: "#f59e0b", label: "Colheita" },
    PULVERIZACAO: { color: "#ef4444", label: "Pulverização" },
    ADUBACAO:     { color: "#3b82f6", label: "Adubação" },
    IRRIGACAO:    { color: "#06b6d4", label: "Irrigação" },
    PREPARO_SOLO: { color: "#92400e", label: "Preparo Solo" },
    MONITORAMENTO:{ color: "#8b5cf6", label: "Monitoramento" },
    DESSECACAO:   { color: "#f97316", label: "Dessecação" },
    APLICACAO:    { color: "#ec4899", label: "Aplicação" },
    CALAGEM:      { color: "#84cc16", label: "Calagem" },
};

const STATUS_BAR: Record<string, { bg: string; text: string }> = {
    PLANEJADA:     { bg: "rgba(59,130,246,0.25)", text: "#2563eb" },
    PLANTADA:      { bg: "rgba(34,197,94,0.25)",  text: "#16a34a" },
    EM_ANDAMENTO:  { bg: "rgba(16,185,129,0.3)",  text: "#059669" },
    COLHIDA:       { bg: "rgba(245,158,11,0.25)", text: "#d97706" },
    CANCELADA:     { bg: "rgba(239,68,68,0.2)",   text: "#dc2626" },
};

const MONTHS_WINDOW = 12;

// ── Helpers ───────────────────────────────────────────────────────────────────

function parseDate(s?: string): Date | null {
    if (!s) return null;
    const d = parseISO(s);
    return isValid(d) ? d : null;
}

function pct(date: Date, rangeStart: Date, totalDays: number): number {
    const days = differenceInDays(date, rangeStart);
    return Math.max(0, Math.min(100, (days / totalDays) * 100));
}

function getTipoColor(tipo: string): string {
    return TIPO_CONFIG[tipo]?.color ?? "#6b7280";
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function TimelineSafrasPage() {
    const { activeFazendaId } = useAppStore();
    const [windowStart, setWindowStart] = useState(() => startOfMonth(subMonths(new Date(), 2)));
    const [statusFilter, setStatusFilter] = useState("TODAS");

    const windowEnd = endOfMonth(addMonths(windowStart, MONTHS_WINDOW - 1));
    const totalDays = differenceInDays(windowEnd, windowStart) + 1;

    // ── Queries ──────────────────────────────────────────────────────────────
    const { data: safras = [], isLoading: loadingSafras } = useQuery<Safra[]>({
        queryKey: ["safras", activeFazendaId],
        queryFn: () => apiFetch<Safra[]>(`/safras/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    const { data: operacoes = [] } = useQuery<Operacao[]>({
        queryKey: ["operacoes", activeFazendaId],
        queryFn: () => apiFetch<Operacao[]>(`/operacoes/?unidade_produtiva_id=${activeFazendaId}&limit=500`),
        enabled: !!activeFazendaId
    });

    const { data: tiposOperacao = [] } = useQuery<TipoOperacao[]>({
        queryKey: ["operacoes-tipos"],
        queryFn: () => apiFetch("/operacoes/tipos"),
        staleTime: 5 * 60 * 1000,
    });

    const getTipoLabel = (tipo: string) =>
        tiposOperacao.find((item) => item.tipo_operacao === tipo)?.descricao
        || TIPO_CONFIG[tipo]?.label
        || tipo;

    // ── Derived data ─────────────────────────────────────────────────────────
    const filteredSafras = useMemo(() => {
        const base = statusFilter === "TODAS" ? safras : safras.filter(s => s.status === statusFilter);
        // Only show safras that have at least one date
        return base.filter(s => s.data_plantio_prevista || s.data_plantio_real);
    }, [safras, statusFilter]);

    const operacoesBySafra = useMemo(() => {
        const map = new Map<string, Operacao[]>();
        for (const op of operacoes) {
            if (!op.safra_id) continue;
            if (!map.has(op.safra_id)) map.set(op.safra_id, []);
            map.get(op.safra_id)!.push(op);
        }
        return map;
    }, [operacoes]);

    // Month columns
    const months = useMemo(() => {
        const result: Date[] = [];
        let cur = startOfMonth(windowStart);
        while (cur <= windowEnd) {
            result.push(cur);
            cur = addMonths(cur, 1);
        }
        return result;
    }, [windowStart, windowEnd]);

    // Today marker position
    const todayPct = useMemo(() => {
        const today = new Date();
        if (today < windowStart || today > windowEnd) return null;
        return pct(today, windowStart, totalDays);
    }, [windowStart, windowEnd, totalDays]);

    // ── KPIs ─────────────────────────────────────────────────────────────────
    const kpis = useMemo(() => {
        const ativas = safras.filter(s => ["PLANTADA", "EM_ANDAMENTO"].includes(s.status)).length;
        const colhidas = safras.filter(s => s.status === "COLHIDA").length;
        const totalOps = operacoes.length;
        const culturas = [...new Set(safras.map(s => s.cultura))].length;
        return { ativas, colhidas, totalOps, culturas };
    }, [safras, operacoes]);

    // ── Render helpers ────────────────────────────────────────────────────────
    const renderSafraRow = (safra: Safra) => {
        const plantio = parseDate(safra?.data_plantio_real) ?? parseDate(safra?.data_plantio_prevista);
        const colheita = parseDate(safra?.data_colheita_real) ?? parseDate(safra?.data_colheita_prevista);

        if (!plantio) return null;

        const barEnd = colheita ?? addDays(plantio, 180);
        const clampedStart = plantio < windowStart ? windowStart : plantio;
        const clampedEnd = barEnd > windowEnd ? windowEnd : barEnd;

        if (clampedStart > windowEnd || clampedEnd < windowStart) return null;

        const left = pct(clampedStart, windowStart, totalDays);
        const width = pct(clampedEnd, windowStart, totalDays) - left;
        const barStyle = STATUS_BAR[safra.status] ?? STATUS_BAR["PLANEJADA"];
        const ops = (operacoesBySafra.get(safra.id) ?? []).filter(op => {
            const d = parseDate(op.data_operacao);
            return d && d >= windowStart && d <= windowEnd;
        });

        const isPrevisto = !safra?.data_plantio_real;

        return (
            <div key={safra.id} className="flex items-center border-b border-border/40 hover:bg-muted/30 transition-colors group" style={{ minHeight: 56 }}>
                {/* Left label */}
                <div className="w-52 flex-shrink-0 px-3 py-2 border-r border-border/40">
                    <div className="font-medium text-sm truncate leading-tight">{safra.cultura ?? "—"}</div>
                    <div className="text-xs text-muted-foreground truncate flex items-center gap-1 mt-0.5">
                        <span>{safra.ano_safra}</span>
                        {safra.talhao_nome && <><span>·</span><span>{safra.talhao_nome}</span></>}
                        {safra?.area_plantada_ha && <><span>·</span><span>{safra?.area_plantada_ha.toFixed(0)}ha</span></>}
                    </div>
                </div>

                {/* Timeline bar area */}
                <div className="flex-1 relative" style={{ height: 56 }}>
                    {/* Safra bar */}
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger
                                    className="absolute top-1/2 -translate-y-1/2 rounded-full border cursor-pointer p-0 bg-transparent"
                                    style={{
                                        left: `${left}%`,
                                        width: `${Math.max(width, 0.5)}%`,
                                        height: 28,
                                        backgroundColor: barStyle.bg,
                                        borderColor: barStyle.text,
                                        borderWidth: isPrevisto ? "1px" : "2px",
                                        borderStyle: isPrevisto ? "dashed" : "solid",
                                    }}
                            />
                            <TooltipContent side="top" className="text-xs max-w-xs">
                                <div className="font-semibold">{(safra.cultura ?? "Safra")} — {safra.ano_safra}</div>
                                <div className="text-muted-foreground">
                                    Plantio: {plantio ? format(plantio, "dd/MM/yyyy") : "—"} {isPrevisto && "(previsto)"}<br />
                                    Colheita: {colheita ? format(colheita, "dd/MM/yyyy") : "—"}<br />
                                    Status: {safra.status}
                                </div>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>

                    {/* Operation markers */}
                    {ops.map(op => {
                        const d = parseDate(op.data_operacao);
                        if (!d) return null;
                        const opLeft = pct(d, windowStart, totalDays);
                        const color = getTipoColor(op.tipo_operacao);
                        return (
                            <TooltipProvider key={op.id}>
                                <Tooltip>
                                    <TooltipTrigger
                                        className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 rounded-full border-2 border-white dark:border-background z-10 cursor-pointer hover:scale-125 transition-transform shadow p-0"
                                        style={{
                                            left: `${opLeft}%`,
                                            width: 14,
                                            height: 14,
                                            backgroundColor: color,
                                        }}
                                    />
                                    <TooltipContent side="top" className="text-xs max-w-xs">
                                        <div className="font-semibold">{getTipoLabel(op.tipo_operacao)}</div>
                                        <div className="text-muted-foreground space-y-0.5">
                                            <div>{format(d, "dd/MM/yyyy")}</div>
                                            {op.area_ha && <div>Área: {op.area_ha} ha</div>}
                                            {op.responsavel && <div>Resp.: {op.responsavel}</div>}
                                            {op.descricao && <div className="italic">{op.descricao}</div>}
                                        </div>
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        );
                    })}
                </div>

                {/* Status badge */}
                <div className="w-28 flex-shrink-0 px-3 flex justify-end">
                    <Badge
                        variant="outline"
                        className="text-xs"
                        style={{ color: barStyle.text, borderColor: barStyle.text }}
                    >
                        {safra.status}
                    </Badge>
                </div>
            </div>
        );
    };

    // ── Render ────────────────────────────────────────────────────────────────
    return (
        <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden">

            {/* Header */}
            <div className="border-b px-6 py-4 flex-shrink-0">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                    <PageHeader
                        title="Timeline de Safras"
                        description="Linha do tempo de safras e operações agrícolas"
                        icon={<CalendarDays className="size-5" />}
                    />

                    {/* Controls */}
                    <div className="flex items-center gap-3 flex-wrap">
                        <Select value={statusFilter} onValueChange={setStatusFilter}>
                            <SelectTrigger className="h-8 w-40 text-xs">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="TODAS">Todos os status</SelectItem>
                                <SelectItem value="PLANEJADA">Planejada</SelectItem>
                                <SelectItem value="PLANTADA">Plantada</SelectItem>
                                <SelectItem value="EM_ANDAMENTO">Em andamento</SelectItem>
                                <SelectItem value="COLHIDA">Colhida</SelectItem>
                            </SelectContent>
                        </Select>

                        <div className="flex items-center gap-1 border rounded-sm p-1">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6"
                                onClick={() => setWindowStart(w => subMonths(w, 3))}
                            >
                                <ChevronLeft className="size-4" />
                            </Button>
                            <span className="text-xs px-2 min-w-36 text-center">
                                {format(windowStart, "MMM yyyy", { locale: ptBR })} – {format(windowEnd, "MMM yyyy", { locale: ptBR })}
                            </span>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6"
                                onClick={() => setWindowStart(w => addMonths(w, 3))}
                            >
                                <ChevronRight className="size-4" />
                            </Button>
                        </div>

                        <Button
                            variant="outline"
                            size="sm"
                            className="h-8 text-xs"
                            onClick={() => setWindowStart(startOfMonth(subMonths(new Date(), 2)))}
                        >
                            Hoje
                        </Button>
                    </div>
                </div>

                {/* KPIs */}
                <div className="flex gap-6 mt-4">
                    {[
                        { label: "Safras ativas", value: kpis.ativas },
                        { label: "Colhidas", value: kpis.colhidas },
                        { label: "Operações", value: kpis.totalOps },
                        { label: "Culturas", value: kpis.culturas },
                    ].map(k => (
                        <div key={k.label} className="text-center">
                            <div className="text-2xl font-bold leading-none">{k.value}</div>
                            <div className="text-xs text-muted-foreground mt-1">{k.label}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-4 px-6 py-2 border-b bg-muted/30 flex-wrap flex-shrink-0">
                <span className="text-xs text-muted-foreground font-medium">Operações:</span>
                {Object.entries(TIPO_CONFIG).slice(0, 7).map(([tipo, { color, label }]) => (
                    <div key={tipo} className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-full border-2 border-white shadow-sm" style={{ backgroundColor: color }} />
                        <span className="text-xs text-muted-foreground">{label}</span>
                    </div>
                ))}
                <div className="ml-4 flex items-center gap-3 border-l pl-4">
                    <div className="flex items-center gap-1.5">
                        <div className="w-8 h-3 rounded-full border-2" style={{ borderColor: "#2563eb", backgroundColor: "rgba(59,130,246,0.25)" }} />
                        <span className="text-xs text-muted-foreground">Planejada</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-8 h-3 rounded-full border-2" style={{ borderColor: "#16a34a", backgroundColor: "rgba(34,197,94,0.25)" }} />
                        <span className="text-xs text-muted-foreground">Plantada</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-8 h-3 rounded-full border-dashed border-2" style={{ borderColor: "#2563eb" }} />
                        <span className="text-xs text-muted-foreground">Previsto</span>
                    </div>
                </div>
            </div>

            {/* Timeline grid */}
            <div className="flex-1 overflow-auto">
                <div style={{ minWidth: 900 }}>

                    {/* Month header row */}
                    <div className="flex sticky top-0 z-20 bg-background border-b">
                        <div className="w-52 flex-shrink-0 border-r border-border/40 px-3 py-2">
                            <span className="text-xs font-medium text-muted-foreground">Safra / Talhão</span>
                        </div>
                        <div className="flex-1 relative flex">
                            {months.map((m, i) => {
                                const monthStart = m < windowStart ? windowStart : m;
                                const monthEnd = endOfMonth(m) > windowEnd ? windowEnd : endOfMonth(m);
                                const w = ((differenceInDays(monthEnd, monthStart) + 1) / totalDays) * 100;
                                return (
                                    <div
                                        key={i}
                                        className="border-r border-border/30 px-2 py-2 text-xs text-muted-foreground font-medium flex-shrink-0"
                                        style={{ width: `${w}%` }}
                                    >
                                        {format(m, "MMM yy", { locale: ptBR })}
                                    </div>
                                );
                            })}
                        </div>
                        <div className="w-28 flex-shrink-0 border-l border-border/40 px-3 py-2">
                            <span className="text-xs font-medium text-muted-foreground">Status</span>
                        </div>
                    </div>

                    {/* Rows */}
                    <div className="relative">
                        {/* Month vertical gridlines */}
                        <div className="absolute inset-0 flex pointer-events-none" style={{ left: 208, right: 112 }}>
                            {months.map((m, i) => {
                                const monthStart = m < windowStart ? windowStart : m;
                                const monthEnd = endOfMonth(m) > windowEnd ? windowEnd : endOfMonth(m);
                                const w = ((differenceInDays(monthEnd, monthStart) + 1) / totalDays) * 100;
                                return (
                                    <div
                                        key={i}
                                        className="border-r border-border/20 flex-shrink-0"
                                        style={{ width: `${w}%` }}
                                    />
                                );
                            })}
                        </div>

                        {/* Today line */}
                        {todayPct !== null && (
                            <div
                                className="absolute top-0 bottom-0 w-px bg-red-500/70 z-10 pointer-events-none"
                                style={{ left: `calc(208px + ${todayPct}% * (100% - 320px) / 100)` }}
                            >
                                <div className="bg-red-500 text-white text-[10px] px-1 rounded absolute -top-0 left-1 whitespace-nowrap">
                                    Hoje
                                </div>
                            </div>
                        )}

                        {/* Safra rows */}
                        {loadingSafras ? (
                            <div className="p-12 text-center text-muted-foreground text-sm">
                                Carregando safras...
                            </div>
                        ) : filteredSafras.length === 0 ? (
                            <div className="p-12 text-center text-muted-foreground">
                                <Tractor className="h-10 w-10 mx-auto mb-3 opacity-40" />
                                <p className="font-medium">Nenhuma safra encontrada</p>
                                <p className="text-sm mt-1">Cadastre safras com datas de plantio para visualizar a timeline</p>
                            </div>
                        ) : (
                            filteredSafras.map(s => renderSafraRow(s))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
