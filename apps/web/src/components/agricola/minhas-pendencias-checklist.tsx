"use client";

import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { ClipboardCheck, UserPlus, Clock, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { toast } from "sonner";

interface PendenciaItem {
    id: string;
    safra_id: string;
    fase: string;
    titulo: string;
    tipo_resultado: "TAREFA_CAMPO" | "SOLICITACAO_ESTOQUE" | "MANUAL";
    status_verificacao: "PENDENTE" | "OK" | "OK_PARCIAL" | "BLOQUEANTE";
    prazo_resposta: string | null;
}

const TIPO_LABEL: Record<PendenciaItem["tipo_resultado"], string> = {
    TAREFA_CAMPO: "Tarefa de campo",
    SOLICITACAO_ESTOQUE: "Verificação de estoque",
    MANUAL: "Manual",
};

function formatPrazo(prazo: string | null): { label: string; vencido: boolean } | null {
    if (!prazo) return null;
    const data = new Date(prazo + "T00:00:00");
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    const vencido = data.getTime() < hoje.getTime();
    return { label: data.toLocaleDateString("pt-BR"), vencido };
}

function PendenciaCard({
    item,
    safraId,
    action,
}: {
    item: PendenciaItem;
    safraId: string;
    action?: React.ReactNode;
}) {
    const prazo = formatPrazo(item.prazo_resposta);
    return (
        <Card className="border shadow-sm">
            <CardContent className="p-4 flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                    <Link
                        href={`/agricola/safras/${safraId}/checklist`}
                        className="text-sm font-semibold text-foreground hover:underline"
                    >
                        {item.titulo}
                    </Link>
                    {item.status_verificacao === "BLOQUEANTE" && (
                        <Badge variant="outline" className="rounded-sm text-destructive border-destructive/30 bg-destructive/5 gap-1 shrink-0">
                            <AlertTriangle className="size-3" />
                            Bloqueante
                        </Badge>
                    )}
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline" className="rounded-sm">{TIPO_LABEL[item.tipo_resultado]}</Badge>
                    <span>Fase: {item.fase}</span>
                    {prazo && (
                        <span className={`flex items-center gap-1 ${prazo.vencido ? "text-destructive font-semibold" : ""}`}>
                            <Clock className="size-3" />
                            Prazo: {prazo.label}{prazo.vencido ? " (vencido)" : ""}
                        </span>
                    )}
                </div>
                {action}
            </CardContent>
        </Card>
    );
}

export function MinhasPendenciasChecklist() {
    const queryClient = useQueryClient();

    const minhas = useQuery<PendenciaItem[]>({
        queryKey: ["checklist-minhas-pendencias"],
        queryFn: () => apiFetch("/checklist/minhas-pendencias"),
        staleTime: 30_000,
    });

    const semResponsavel = useQuery<PendenciaItem[]>({
        queryKey: ["checklist-sem-responsavel"],
        queryFn: () => apiFetch("/checklist/sem-responsavel"),
        staleTime: 30_000,
    });

    const assumirMutation = useMutation({
        mutationFn: ({ safraId, itemId }: { safraId: string; itemId: string }) =>
            apiFetch(`/safras/${safraId}/checklist/itens/${itemId}/assumir`, { method: "POST" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["checklist-minhas-pendencias"] });
            queryClient.invalidateQueries({ queryKey: ["checklist-sem-responsavel"] });
            toast.success("Item assumido!");
        },
        onError: (e: Error) => toast.error(e?.message || "Erro ao assumir item"),
    });

    const isLoading = minhas.isLoading || semResponsavel.isLoading;

    if (isLoading) {
        return (
            <Card className="rounded-sm shadow-sm border overflow-hidden">
                <CardContent className="p-5 space-y-3">
                    <Skeleton className="h-5 w-48" />
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-16 w-full" />
                </CardContent>
            </Card>
        );
    }

    const minhasItens = minhas.data ?? [];
    const semResponsavelItens = semResponsavel.data ?? [];

    if (minhasItens.length === 0 && semResponsavelItens.length === 0) {
        return null;
    }

    return (
        <Card className="rounded-sm shadow-sm border overflow-hidden">
            <CardContent className="p-5 space-y-5">
                <div className="flex items-center gap-2">
                    <ClipboardCheck className="size-4 text-primary" />
                    <h2 className="text-sm font-black uppercase tracking-wider">Minhas Pendências de Checklist</h2>
                </div>

                {minhasItens.length > 0 && (
                    <div className="space-y-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                            Atribuídas a mim ({minhasItens.length})
                        </p>
                        <div className="grid gap-2 md:grid-cols-2">
                            {minhasItens.map((item) => (
                                <PendenciaCard key={item.id} item={item} safraId={item.safra_id} />
                            ))}
                        </div>
                    </div>
                )}

                {semResponsavelItens.length > 0 && (
                    <div className="space-y-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                            Sem responsável — disponíveis para assumir ({semResponsavelItens.length})
                        </p>
                        <div className="grid gap-2 md:grid-cols-2">
                            {semResponsavelItens.map((item) => (
                                <PendenciaCard
                                    key={item.id}
                                    item={item}
                                    safraId={item.safra_id}
                                    action={
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="self-start mt-1"
                                            onClick={() => assumirMutation.mutate({ safraId: item.safra_id, itemId: item.id })}
                                            disabled={assumirMutation.isPending}
                                        >
                                            <UserPlus className="size-3.5" />
                                            Assumir
                                        </Button>
                                    }
                                />
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
