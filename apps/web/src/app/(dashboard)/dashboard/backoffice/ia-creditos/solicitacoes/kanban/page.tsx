"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    BrainCircuit, RefreshCw, LayoutList, CheckCircle2,
    Clock, XCircle, FileText, UserCircle, DollarSign,
    MoreHorizontal, CalendarClock, ArrowUpDown
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { apiFetch } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import Link from "next/link";

interface SolicitacaoItem {
    id: string;
    tenant_id: string;
    tenant_nome: string;
    usuario_id: string | null;
    tipo: string;
    quantidade_creditos: number | null;
    valor_estimado: number | null;
    status: string;
    status_pagamento: string | null;
    observacao_comercial: string | null;
    responsavel_usuario_id: string | null;
    responsavel_nome: string | null;
    proximo_followup_em: string | null;
    followup_observacao: string | null;
    created_at: string;
    prioridade: number;
}

function PrioridadeBadge({ score }: { score: number }) {
    if (score >= 80) return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/10 text-red-700 border border-red-500/30 dark:bg-red-500/20 dark:text-red-100 dark:border-red-400/30">
            {score}
        </span>
    );
    if (score >= 50) return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30">
            {score}
        </span>
    );
    return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-700 border border-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30">
            {score}
        </span>
    );
}

const KANBAN_COLUMNS = [
    { id: "ABERTA", label: "Abertas", borderColor: "border-blue-500", headerColor: "bg-blue-500/10 text-blue-700 dark:bg-blue-500/20 dark:text-blue-100" },
    { id: "EM_ANALISE", label: "Em Análise", borderColor: "border-amber-500", headerColor: "bg-amber-500/10 text-amber-700 dark:bg-amber-500/20 dark:text-amber-100" },
    { id: "CONCLUIDA", label: "Concluídas", borderColor: "border-emerald-500", headerColor: "bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-100" },
    { id: "CANCELADA", label: "Canceladas", borderColor: "border-muted-foreground", headerColor: "bg-muted/50 text-muted-foreground" },
];

const PGTO_CONFIG: Record<string, { label: string; className: string }> = {
    PAGO: { label: "Pago", className: "border-emerald-500/30 text-emerald-700 bg-emerald-500/5 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30" },
    PENDENTE: { label: "Pendente", className: "border-amber-500/30 text-amber-700 bg-amber-500/5 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30" },
    EXPIRADO: { label: "Expirado", className: "border-muted-foreground/30 text-muted-foreground bg-muted dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700" },
};

function formatBRL(v: number | null | undefined) {
    if (v == null) return "—";
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function SolicitacoesKanbanPage() {
    const queryClient = useQueryClient();

    const { data: itens = [], isLoading } = useQuery<SolicitacaoItem[]>({
        queryKey: ["ia-solicitacoes-kanban"],
        queryFn: () => apiFetch(`/backoffice/ia/creditos/solicitacoes?limit=500`),
        staleTime: 20_000,
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, status }: { id: string; status: string }) =>
            apiFetch(`/backoffice/ia/creditos/solicitacoes/${id}/status`, {
                method: "PATCH",
                body: JSON.stringify({ status }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes-kanban"] });
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes"] });
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes-resumo"] });
        },
    });

    function handleStatusChange(id: string, novoStatus: string) {
        updateMutation.mutate({ id, status: novoStatus });
    }

    const cardsPorColuna = KANBAN_COLUMNS.reduce((acc, col) => {
        acc[col.id] = itens.filter(item => item.status === col.id);
        return acc;
    }, {} as Record<string, SolicitacaoItem[]>);

    return (
        <div className="space-y-6 max-w-[1600px]">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-lg font-bold text-foreground flex items-center gap-2">
                        <BrainCircuit className="size-5 text-primary" />
                        Kanban — Créditos de IA
                    </h1>
                    <p className="text-sm text-muted-foreground mt-0.5">
                        Acompanhamento visual das solicitações comerciais.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/dashboard/backoffice/ia-creditos/solicitacoes/fila">
                            <ArrowUpDown className="size-3.5 mr-1.5" />
                            Fila prioritária
                        </Link>
                    </Button>
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/dashboard/backoffice/ia-creditos/solicitacoes">
                            <LayoutList className="size-4 mr-2" />
                            Ver em Lista
                        </Link>
                    </Button>
                </div>
            </div>

            <Separator />

            {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-start">
                    {KANBAN_COLUMNS.map((col) => (
                        <div key={col.id} className="rounded-md border border-border bg-muted/20 p-3 min-h-[500px]">
                            <Skeleton className="h-8 w-full mb-4" />
                            <div className="space-y-3">
                                <Skeleton className="h-28 w-full" />
                                <Skeleton className="h-28 w-full" />
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 items-start overflow-x-auto pb-4">
                    {KANBAN_COLUMNS.map((col) => {
                        const itemsInCol = cardsPorColuna[col.id] || [];
                        return (
                            <div key={col.id} className="rounded-md border border-border bg-card/50 flex flex-col min-h-[500px] max-h-[80vh]">
                                <div className={`px-3 py-2 border-b border-border font-semibold text-sm flex items-center justify-between ${col.headerColor}`}>
                                    <span>{col.label}</span>
                                    <Badge variant="secondary" className="bg-background/50">{itemsInCol.length}</Badge>
                                </div>
                                <div className="p-2 space-y-3 flex-1 overflow-y-auto">
                                    {itemsInCol.length === 0 ? (
                                        <p className="text-xs text-muted-foreground text-center py-6 italic">
                                            Nenhuma solicitação
                                        </p>
                                    ) : (
                                        itemsInCol.map((item) => {
                                            const pCfg = PGTO_CONFIG[item.status_pagamento ?? ""] ?? PGTO_CONFIG.PENDENTE;
                                            return (
                                                <div key={item.id} className={`rounded border bg-card p-3 shadow-sm flex flex-col gap-2 border-l-4 ${col.borderColor} ${item.prioridade >= 80 ? "ring-1 ring-red-500/40 bg-red-500/5" : ""}`}>
                                                    <div className="flex justify-between items-start gap-2">
                                                        <div className="space-y-1 overflow-hidden">
                                                            <p className="text-sm font-semibold text-foreground truncate" title={item.tenant_nome}>
                                                                {item.tenant_nome}
                                                            </p>
                                                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                                                <Clock className="size-3" />
                                                                {format(new Date(item.created_at), "dd/MM/yy HH:mm", { locale: ptBR })}
                                                            </div>
                                                        </div>
                                                        <div className="flex flex-col items-end gap-1 shrink-0">
                                                            <PrioridadeBadge score={item.prioridade} />
                                                            <Badge variant="outline" className={`text-[10px] ${pCfg.className}`}>
                                                                {pCfg.label}
                                                            </Badge>
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-2 my-1">
                                                        <div className="bg-muted/30 rounded p-1.5 text-center">
                                                            <p className="text-[10px] text-muted-foreground uppercase">Créditos</p>
                                                            <p className="text-xs font-medium">{item.quantidade_creditos ?? "—"}</p>
                                                        </div>
                                                        <div className="bg-muted/30 rounded p-1.5 text-center">
                                                            <p className="text-[10px] text-muted-foreground uppercase">Valor</p>
                                                            <p className="text-xs font-medium text-green-700">{formatBRL(item.valor_estimado)}</p>
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center gap-1.5 text-xs">
                                                        <UserCircle className={`size-3.5 shrink-0 ${item.responsavel_nome ? "text-primary" : "text-muted-foreground"}`} />
                                                        <span className={`truncate ${item.responsavel_nome ? "text-foreground font-medium" : "text-muted-foreground italic"}`}>
                                                            {item.responsavel_nome ?? "Sem responsável"}
                                                        </span>
                                                    </div>

                                                    {item.proximo_followup_em && (
                                                        <div className="flex items-start gap-1.5 text-xs mt-1 bg-purple-500/10 text-purple-700 p-1.5 rounded border border-purple-500/20">
                                                            <CalendarClock className="size-3.5 shrink-0 mt-0.5" />
                                                            <div className="flex flex-col">
                                                                <span className="font-semibold">FUP: {format(parseISO(item.proximo_followup_em), "dd/MM HH:mm")}</span>
                                                                {item.followup_observacao && (
                                                                    <span className="text-[10px] leading-tight line-clamp-2" title={item.followup_observacao}>
                                                                        {item.followup_observacao}
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}

                                                    <div className="mt-2 pt-2 border-t border-border flex justify-between items-center">
                                                        <span className="text-[10px] text-muted-foreground uppercase">Mover para:</span>
                                                        <Select
                                                            value={item.status}
                                                            onValueChange={(v) => handleStatusChange(item.id, v)}
                                                            disabled={updateMutation.isPending}
                                                        >
                                                            <SelectTrigger className="h-6 w-28 text-[10px]">
                                                                <SelectValue />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                {KANBAN_COLUMNS.map((o) => (
                                                                    <SelectItem key={o.id} value={o.id} className="text-[10px]">
                                                                        {o.label}
                                                                    </SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
