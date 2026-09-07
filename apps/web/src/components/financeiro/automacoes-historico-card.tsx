"use client";

import { useQuery } from "@tanstack/react-query";
import { Zap } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { apiFetch } from "@/lib/api";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface ExecucaoItem {
    id: string;
    status: string;
    acoes_criadas: number;
    notificacoes_criadas: number;
    regras_disparadas: string[];
    mensagem: string;
    created_at: string;
}

const REGRA_LABEL: Record<string, string> = {
    MARGEM_NEGATIVA: "Margem negativa",
    INSUMOS_DOMINANTE: "Insumos dominantes",
    AUMENTO_CUSTO: "Aumento de custos",
};

interface Props {
    safraId: string;
}

export function AutomacoesHistoricoCard({ safraId }: Props) {
    const { data: execucoes = [], isLoading } = useQuery<ExecucaoItem[]>({
        queryKey: ["automacoes-execucoes", safraId],
        queryFn: () => apiFetch(`/automacoes/execucoes?safra_id=${safraId}&limit=10`),
        staleTime: 30_000,
        enabled: !!safraId,
    });

    if (!isLoading && execucoes.length === 0) return null;

    return (
        <section className="rounded-sm border border-border bg-card shadow-sm overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-border bg-muted/30">
                <span className="size-8 rounded-sm bg-primary/10 border border-primary/15 flex items-center justify-center shrink-0">
                    <Zap className="size-4 text-primary" />
                </span>
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                        Automações
                    </p>
                    <p className="text-sm font-semibold text-foreground leading-tight">
                        Histórico de execuções
                    </p>
                </div>
            </div>

            {/* Lista */}
            <ul className="divide-y divide-border">
                {isLoading
                    ? Array.from({ length: 3 }).map((_, i) => (
                        <li key={i} className="flex items-start gap-3 px-5 py-3">
                            <Skeleton className="h-4 w-16 rounded-sm shrink-0 mt-0.5" />
                            <div className="flex-1 space-y-1.5">
                                <Skeleton className="h-3 w-1/2" />
                                <Skeleton className="h-3 w-1/3" />
                            </div>
                        </li>
                    ))
                    : execucoes.map((exec) => {
                        const timeAgo = formatDistanceToNow(new Date(exec.created_at), {
                            addSuffix: true,
                            locale: ptBR,
                        });
                        const totalGerado = exec.acoes_criadas + exec.notificacoes_criadas;

                        return (
                            <li key={exec.id} className="flex items-start gap-3 px-5 py-3 hover:bg-muted/20 transition-colors">
                                {/* Status */}
                                <WorkflowStatusBadge
                                    status={exec.status === "SUCESSO" ? "CONCLUIDA" : "CANCELADA"}
                                    label={exec.status}
                                    className="shrink-0 mt-0.5 text-[10px]"
                                />

                                {/* Conteúdo */}
                                <div className="flex-1 min-w-0 space-y-1.5">
                                    {/* Regras disparadas */}
                                    {exec.regras_disparadas.length > 0 ? (
                                        <div className="flex flex-wrap gap-1">
                                            {exec.regras_disparadas.map((r) => (
                                                <Badge
                                                    key={r}
                                                    variant="outline"
                                                    className="text-[10px] px-1.5 py-0 border-primary/20 text-primary"
                                                >
                                                    {REGRA_LABEL[r] ?? r}
                                                </Badge>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-xs text-muted-foreground">Nenhuma regra disparada</p>
                                    )}

                                    {/* Contadores + tempo */}
                                    <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                                        {totalGerado > 0 && (
                                            <span>
                                                {exec.acoes_criadas > 0 && `${exec.acoes_criadas} ação${exec.acoes_criadas !== 1 ? "ões" : ""}`}
                                                {exec.acoes_criadas > 0 && exec.notificacoes_criadas > 0 && " · "}
                                                {exec.notificacoes_criadas > 0 && `${exec.notificacoes_criadas} notificação${exec.notificacoes_criadas !== 1 ? "ões" : ""}`}
                                            </span>
                                        )}
                                        <span>{timeAgo}</span>
                                    </div>
                                </div>
                            </li>
                        );
                    })}
            </ul>
        </section>
    );
}
