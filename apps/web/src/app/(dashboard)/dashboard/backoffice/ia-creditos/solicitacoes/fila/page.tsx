"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    BrainCircuit, UserCircle, DollarSign, CalendarClock,
    ArrowLeft, LayoutList, Zap, AlertTriangle, Send, CheckCheck,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { apiFetch } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import Link from "next/link";
import { PageHeader } from "@/components/shared/page-header";

interface SolicitacaoItem {
    id: string;
    tenant_id: string;
    tenant_nome: string;
    quantidade_creditos: number | null;
    valor_estimado: number | null;
    status: string;
    status_pagamento: string | null;
    responsavel_nome: string | null;
    proximo_followup_em: string | null;
    followup_observacao: string | null;
    created_at: string;
    prioridade: number;
    crm_sync_status: string;
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
    ABERTA: { label: "Aberta", className: "border-blue-500/30 text-blue-700 bg-blue-500/5 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30" },
    EM_ANALISE: { label: "Em análise", className: "border-amber-500/30 text-amber-700 bg-amber-500/5 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30" },
};

function PrioridadeBadge({ score }: { score: number }) {
    if (score >= 80) return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-red-500/10 text-red-700 border border-red-500/30 dark:bg-red-500/20 dark:text-red-100 dark:border-red-400/30">
            <AlertTriangle className="size-3" /> {score}
        </span>
    );
    if (score >= 50) return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30">
            <Zap className="size-3" /> {score}
        </span>
    );
    return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700 border border-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30">
            {score}
        </span>
    );
}

function formatBRL(v: number | null | undefined) {
    if (v == null) return "—";
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function FilaPrioritariaPage() {
    const queryClient = useQueryClient();

    const crmMutation = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/backoffice/ia/creditos/solicitacoes/${id}/enviar-crm`, { method: "POST" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["ia-fila-prioritaria"] });
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes"] });
        },
    });

    const { data: itens = [], isLoading } = useQuery<SolicitacaoItem[]>({
        queryKey: ["ia-fila-prioritaria"],
        queryFn: () => apiFetch("/backoffice/ia/creditos/solicitacoes/fila-prioritaria?limit=20"),
        staleTime: 30_000,
    });

    const criticas = itens.filter((i) => i.prioridade >= 80);

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Fila Prioritária — Créditos de IA"
                description="Solicitações acionáveis ordenadas por prioridade. Ataque primeiro as vermelhas."
                icon={<BrainCircuit className="size-[22px] text-primary" />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "IA", href: "/dashboard/backoffice/ia-creditos" },
                    { label: "Solicitações", href: "/dashboard/backoffice/ia-creditos/solicitacoes" },
                    { label: "Fila Prioritária" },
                ]}
                actions={
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" asChild className="rounded-sm">
                            <Link href="/dashboard/backoffice/ia-creditos/solicitacoes">
                                <LayoutList className="size-3.5 mr-1.5" />
                                Ver lista
                            </Link>
                        </Button>
                        <Button variant="outline" size="sm" asChild className="rounded-sm">
                            <Link href="/dashboard/backoffice/ia-creditos/solicitacoes/kanban">
                                <ArrowLeft className="size-3.5 mr-1.5" />
                                Kanban
                            </Link>
                        </Button>
                    </div>
                }
            />

            <Separator />

            {/* Alerta críticos */}
            {!isLoading && criticas.length > 0 && (
                <div className="flex items-center gap-2.5 rounded-sm border border-red-500/30 bg-red-500/5 px-4 py-2.5 text-sm text-red-700">
                    <AlertTriangle className="size-4 shrink-0" />
                    <span>
                        <strong>{criticas.length}</strong> solicitação{criticas.length > 1 ? "ões" : ""} com prioridade crítica (≥ 80) requer{criticas.length > 1 ? "em" : ""} atenção imediata.
                    </span>
                </div>
            )}

            {/* Lista de cards */}
            {isLoading ? (
                <div className="space-y-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <Skeleton key={i} className="h-24 w-full rounded-sm" />
                    ))}
                </div>
            ) : itens.length === 0 ? (
                <div className="rounded-sm border border-border bg-card px-6 py-12 text-center text-sm text-muted-foreground">
                    Nenhuma solicitação acionável no momento.
                </div>
            ) : (
                <div className="space-y-2">
                    {itens.map((item, idx) => {
                        const sCfg = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.ABERTA;
                        const isCritica = item.prioridade >= 80;
                        return (
                            <div
                                key={item.id}
                                className={`rounded-sm border bg-card p-4 flex items-center gap-4 transition-colors ${
                                    isCritica
                                        ? "border-red-500/40 bg-red-500/5 ring-1 ring-red-500/20"
                                        : "border-border hover:bg-muted/20"
                                }`}
                            >
                                {/* Posição */}
                                <div className="text-2xl font-black tabular-nums text-muted-foreground/40 w-7 text-center shrink-0">
                                    {idx + 1}
                                </div>

                                {/* Conteúdo principal */}
                                <div className="flex-1 min-w-0 space-y-1.5">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <span className="text-sm font-semibold text-foreground truncate">
                                            {item.tenant_nome}
                                        </span>
                                        <Badge variant="outline" className={`text-[10px] shrink-0 ${sCfg.className}`}>
                                            {sCfg.label}
                                        </Badge>
                                    </div>

                                    <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
                                        <span className="flex items-center gap-1">
                                            <DollarSign className="size-3" />
                                            <span className="text-green-700 font-medium">{formatBRL(item.valor_estimado)}</span>
                                        </span>
                                        {item.quantidade_creditos != null && (
                                            <span>{item.quantidade_creditos.toLocaleString("pt-BR")} créditos</span>
                                        )}
                                        <span className="flex items-center gap-1">
                                            <UserCircle className={`size-3 ${item.responsavel_nome ? "text-primary" : ""}`} />
                                            <span className={item.responsavel_nome ? "text-foreground font-medium" : "italic"}>
                                                {item.responsavel_nome ?? "Sem responsável"}
                                            </span>
                                        </span>
                                        {item.proximo_followup_em && (
                                            <span className="flex items-center gap-1 text-purple-600">
                                                <CalendarClock className="size-3" />
                                                {format(parseISO(item.proximo_followup_em), "dd/MM HH:mm", { locale: ptBR })}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                {/* Score + ações */}
                                <div className="flex flex-col items-end gap-2 shrink-0">
                                    <PrioridadeBadge score={item.prioridade} />
                                    <div className="flex gap-1.5">
                                        {item.crm_sync_status === "ENVIADO" ? (
                                            <span className="flex items-center gap-1 text-[10px] text-green-700 font-semibold px-2 py-1 rounded border border-green-500/30 bg-green-500/5">
                                                <CheckCheck className="size-3" /> CRM
                                            </span>
                                        ) : (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className={`h-7 text-xs gap-1 ${item.crm_sync_status === "ERRO" ? "text-destructive border-destructive/40" : ""}`}
                                                disabled={crmMutation.isPending}
                                                onClick={() => crmMutation.mutate(item.id)}
                                                title="Enviar para CRM"
                                            >
                                                <Send className="size-3" />
                                                CRM
                                            </Button>
                                        )}
                                        <Button
                                            size="sm"
                                            variant={isCritica ? "default" : "outline"}
                                            className="h-7 text-xs"
                                            asChild
                                        >
                                            <Link href={`/dashboard/backoffice/ia-creditos/solicitacoes?id=${item.id}`}>
                                                Abrir
                                            </Link>
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {!isLoading && itens.length > 0 && (
                <p className="text-xs text-muted-foreground text-center">
                    Exibindo as {itens.length} solicitações mais prioritárias
                </p>
            )}
        </div>
    );
}
