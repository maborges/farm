"use client";

import { useQuery } from "@tanstack/react-query";
import {
    HandCoins, CheckCheck, PackageMinus, Activity,
    TrendingUp,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { apiFetch } from "@/lib/api";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

interface AtividadeItem {
    id: string;
    tipo: string;
    descricao: string;
    data: string;
    origem: string;
    origem_id: string | null;
    meta: Record<string, unknown>;
}

const TIPO_CONFIG: Record<string, {
    icon: React.ComponentType<{ className?: string }>;
    iconClass: string;
    wrapClass: string;
}> = {
    CUSTO_LANCADO:   { icon: HandCoins,    iconClass: "text-destructive",  wrapClass: "bg-destructive/10 border-destructive/20" },
    RECEITA_LANCADA: { icon: TrendingUp,   iconClass: "text-emerald-600",  wrapClass: "bg-emerald-500/10 border-emerald-500/20" },
    ACAO_CONCLUIDA:  { icon: CheckCheck,   iconClass: "text-emerald-600",  wrapClass: "bg-emerald-500/10 border-emerald-500/20" },
    SAIDA_ESTOQUE:   { icon: PackageMinus, iconClass: "text-amber-600",    wrapClass: "bg-amber-500/10 border-amber-500/20" },
};

const DEFAULT_CONFIG = {
    icon: Activity,
    iconClass: "text-muted-foreground",
    wrapClass: "bg-muted border-border",
};

function getConfig(tipo: string) {
    return TIPO_CONFIG[tipo] ?? DEFAULT_CONFIG;
}

interface Props {
    safraId: string;
}

export function AtividadesFeed({ safraId }: Props) {
    const { data: itens = [], isLoading } = useQuery<AtividadeItem[]>({
        queryKey: ["atividades", safraId],
        queryFn: () => apiFetch(`/atividades/?safra_id=${safraId}&limit=20`),
        staleTime: 60_000,
        enabled: !!safraId,
    });

    if (!isLoading && itens.length === 0) return null;

    return (
        <section className="rounded-sm border border-border bg-card shadow-sm overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-border bg-muted/30">
                <span className="size-8 rounded-sm bg-primary/10 border border-primary/15 flex items-center justify-center shrink-0">
                    <Activity className="size-4 text-primary" />
                </span>
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                        Atividades
                    </p>
                    <p className="text-sm font-semibold text-foreground leading-tight">
                        Histórico da safra
                    </p>
                </div>
            </div>

            {/* Lista */}
            <ul className="divide-y divide-border/60 px-5">
                {isLoading
                    ? Array.from({ length: 5 }).map((_, i) => (
                        <li key={i} className="flex items-start gap-3 py-3">
                            <Skeleton className="size-7 rounded-sm shrink-0" />
                            <div className="flex-1 space-y-1.5">
                                <Skeleton className="h-3 w-3/4" />
                                <Skeleton className="h-3 w-1/3" />
                            </div>
                        </li>
                    ))
                    : itens.map((item, idx) => {
                        const cfg = getConfig(item.tipo);
                        const Icon = cfg.icon;
                        const timeAgo = formatDistanceToNow(new Date(item.data), {
                            addSuffix: true,
                            locale: ptBR,
                        });

                        return (
                            <li key={item.id} className="flex items-start gap-3 py-3">
                                {/* Ícone com linha vertical */}
                                <div className="flex flex-col items-center shrink-0">
                                    <span className={`size-7 rounded-sm border flex items-center justify-center ${cfg.wrapClass}`}>
                                        <Icon className={`size-3.5 ${cfg.iconClass}`} />
                                    </span>
                                    {idx < itens.length - 1 && (
                                        <div className="w-px flex-1 bg-border/60 mt-1 min-h-[12px]" />
                                    )}
                                </div>

                                {/* Conteúdo */}
                                <div className="flex-1 min-w-0 pb-2">
                                    <p className="text-sm text-foreground leading-snug">
                                        {item.descricao}
                                    </p>
                                    <p className="text-[11px] text-muted-foreground mt-0.5">
                                        {timeAgo}
                                    </p>
                                </div>
                            </li>
                        );
                    })}
            </ul>
        </section>
    );
}
