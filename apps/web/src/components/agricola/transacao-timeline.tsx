"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

interface Operacao {
    id: string;
    tipo: string;
    descricao: string;
    data_realizada: string;
    custo_total: number;
    area_aplicada_ha: number;
}

interface Romaneio {
    id: string;
    data_colheita: string;
    sacas_60kg: number;
    receita_total: number;
}

function moeda(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface TransacaoTimelineProps {
    safraId: string;
}

export function TransacaoTimeline({ safraId }: TransacaoTimelineProps) {
    const { data: operacoes, isLoading: opLoading } = useQuery<Operacao[]>({
        queryKey: ["safra-operacoes", safraId],
        queryFn: () => apiFetch(`/operacoes?safra_id=${safraId}`),
    });

    const { data: romaneios, isLoading: romLoading } = useQuery<Romaneio[]>({
        queryKey: ["safra-romaneios", safraId],
        queryFn: () => apiFetch(`/romaneios?safra_id=${safraId}`),
    });

    const isLoading = opLoading || romLoading;

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
        );
    }

    // Combina e ordena por data
    const transacoes = [
        ...(operacoes || []).map((op) => ({
            id: op.id,
            date: new Date(op.data_realizada),
            type: "operacao" as const,
            descricao: op.descricao || op.tipo,
            titulo: op.tipo,
            valor: -op.custo_total,
            detalhes: `${op.area_aplicada_ha} ha`,
        })),
        ...(romaneios || []).map((rom) => ({
            id: rom.id,
            date: new Date(rom.data_colheita),
            type: "romaneio" as const,
            descricao: `${rom.sacas_60kg.toFixed(0)} sacas colhidas`,
            titulo: "Colheita",
            valor: rom.receita_total,
            detalhes: `${rom.sacas_60kg.toFixed(1)} sc`,
        })),
    ].sort((a, b) => a.date.getTime() - b.date.getTime());

    if (transacoes.length === 0) {
        return (
            <div className="text-center py-8">
                <p className="text-sm text-muted-foreground">Nenhuma transação registrada para esta safra.</p>
            </div>
        );
    }

    return (
        <div className="relative">
            <ol className="relative border-l border-border ml-3 space-y-4 py-2">
                {transacoes.map((transacao, idx) => (
                    <li key={`${transacao.type}-${transacao.id}`} className="ml-4">
                        <div className="absolute -left-1.5 mt-1.5 size-3 rounded-full bg-primary" />
                        <Card size="sm" className="hover:shadow-lg transition-shadow">
                            <CardContent className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 flex-wrap mb-1">
                                        <Badge
                                            variant="outline"
                                            className={transacao.type === "operacao"
                                                ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20"
                                                : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"}
                                        >
                                            {transacao.type === "operacao" ? "Despesa" : "Receita"}
                                        </Badge>
                                        <span className="text-sm font-medium">{transacao.titulo}</span>
                                    </div>
                                    <p className="text-sm text-muted-foreground mb-1">{transacao.descricao}</p>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span>{format(transacao.date, "dd MMM yyyy", { locale: ptBR })}</span>
                                        <span>•</span>
                                        <span>{transacao.detalhes}</span>
                                    </div>
                                </div>
                                <div className="text-right shrink-0">
                                    <p className={`font-bold text-sm ${transacao.valor < 0 ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                                        {transacao.valor < 0 ? "-" : "+"}{moeda(Math.abs(transacao.valor))}
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    </li>
                ))}
            </ol>
        </div>
    );
}
