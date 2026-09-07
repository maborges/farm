"use client";

import { useIAProgresso } from "@/hooks";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
    TrendingUp, TrendingDown, Minus,
    Timer, Zap, DollarSign, Brain,
    Sparkles,
} from "lucide-react";
import { IAUpgradeCTA } from "./ia-upgrade-cta";

function MetricaItem({
    icon: Icon,
    label,
    valor,
    melhoria,
    status,
    iconClass,
}: {
    icon: React.ElementType;
    label: string;
    valor: string;
    melhoria: number;
    status: string;
    iconClass: string;
}) {
    const evoluindo = status === "EVOLUINDO" || status === "CRESCENTE";
    const estavel = melhoria === 0 || status === "ESTÁVEL";

    return (
        <div className="rounded-sm border border-border bg-muted/10 px-4 py-3 space-y-2">
            <div className="flex items-center gap-2">
                <span className={cn("size-6 rounded-sm flex items-center justify-center shrink-0", iconClass)}>
                    <Icon className="size-3" />
                </span>
                <p className="text-[10px] font-black uppercase tracking-[0.15em] text-muted-foreground leading-none">{label}</p>
            </div>
            <p className="text-2xl font-black tabular-nums text-foreground leading-none">{valor}</p>
            <div className="flex items-center gap-1.5">
                {estavel ? (
                    <Minus className="size-3 text-muted-foreground" />
                ) : evoluindo ? (
                    <TrendingUp className="size-3 text-emerald-500" />
                ) : (
                    <TrendingDown className="size-3 text-rose-500" />
                )}
                <span className={cn(
                    "text-[10px] font-bold",
                    estavel ? "text-muted-foreground" : evoluindo ? "text-emerald-600" : "text-rose-500"
                )}>
                    {estavel
                        ? "Estável"
                        : `${evoluindo ? "+" : ""}${melhoria.toFixed(1)}% vs semana anterior`}
                </span>
            </div>
        </div>
    );
}

const PERFIL_CONFIG: Record<string, { label: string; cls: string }> = {
    CONFIANTE: { label: "Confiante", cls: "border-emerald-500/30 text-emerald-700 bg-emerald-500/5" },
    "ANALÍTICO": { label: "Analítico", cls: "border-blue-500/30 text-blue-700 bg-blue-500/5" },
    INSEGURO: { label: "Iniciante", cls: "border-amber-500/30 text-amber-700 bg-amber-500/5" },
    NEUTRO: { label: "Neutro", cls: "border-border text-muted-foreground" },
};

export function IAProgressoCard() {
    const { data, isLoading } = useIAProgresso();

    if (isLoading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-12 w-2/3 rounded-sm" />
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-24 rounded-sm" />
                    ))}
                </div>
            </div>
        );
    }

    if (!data) return null;

    const { progresso, mensagem_destaque, periodo } = data;
    const perfilAtual = PERFIL_CONFIG[progresso.perfil.atual] ?? PERFIL_CONFIG.NEUTRO;
    const perfilAnterior = PERFIL_CONFIG[progresso.perfil.anterior] ?? PERFIL_CONFIG.NEUTRO;

    return (
        <div className="space-y-5">
            {/* CTA de upgrade contextual */}
            <IAUpgradeCTA contexto="progresso" compact />

            {/* Mensagem destaque */}
            <div className="flex items-start gap-3 rounded-sm border border-primary/20 bg-primary/5 p-4">
                <Sparkles className="size-4 text-primary shrink-0 mt-0.5 animate-pulse" />
                <div className="space-y-0.5">
                    <p className="text-sm font-semibold text-foreground leading-snug">{mensagem_destaque}</p>
                    <p className="text-[11px] text-muted-foreground">{periodo}</p>
                </div>
            </div>

            {/* Métricas */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <MetricaItem
                    icon={Timer}
                    label="Tempo de decisão"
                    valor={progresso.tempo_decisao.atual}
                    melhoria={progresso.tempo_decisao.melhoria}
                    status={progresso.tempo_decisao.status}
                    iconClass="bg-blue-500/10 border border-blue-500/15 text-blue-600"
                />
                <MetricaItem
                    icon={Zap}
                    label="Taxa de execução"
                    valor={progresso.taxa_execucao.atual}
                    melhoria={progresso.taxa_execucao.melhoria}
                    status={progresso.taxa_execucao.status}
                    iconClass="bg-emerald-500/10 border border-emerald-500/15 text-emerald-600"
                />
                <MetricaItem
                    icon={DollarSign}
                    label="ROI acumulado"
                    valor={progresso.roi.total}
                    melhoria={progresso.roi.melhoria}
                    status={progresso.roi.status}
                    iconClass="bg-amber-500/10 border border-amber-500/15 text-amber-600"
                />
                <div className="rounded-sm border border-border bg-muted/10 px-4 py-3 space-y-2">
                    <div className="flex items-center gap-2">
                        <span className="size-6 rounded-sm flex items-center justify-center shrink-0 bg-violet-500/10 border border-violet-500/15 text-violet-600">
                            <Brain className="size-3" />
                        </span>
                        <p className="text-[10px] font-black uppercase tracking-[0.15em] text-muted-foreground leading-none">Perfil</p>
                    </div>
                    <div className="flex flex-col gap-1.5">
                        <Badge variant="outline" className={cn("text-[10px] w-fit", perfilAtual.cls)}>
                            {perfilAtual.label}
                        </Badge>
                        {progresso.perfil.evoluiu && (
                            <p className="text-[10px] text-emerald-600 font-bold flex items-center gap-1">
                                <TrendingUp className="size-3" />
                                Era: {perfilAnterior.label}
                            </p>
                        )}
                        {!progresso.perfil.evoluiu && (
                            <p className="text-[10px] text-muted-foreground">Consistente</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
