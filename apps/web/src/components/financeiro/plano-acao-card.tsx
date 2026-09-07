"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ClipboardList, ChevronRight, CircleDot, CheckCheck, EyeOff } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface PlanoAcaoItem {
    id: string;
    tipo: string;
    titulo: string;
    descricao: string;
    prioridade: string;
    status: string;
    rota: string;
}

const PRIORIDADE_CLASS: Record<string, string> = {
    ALTA: "text-destructive",
    MEDIA: "text-amber-600",
    BAIXA: "text-muted-foreground",
};

const planoAcaoButtonClass = "h-8 rounded-sm px-3 text-xs font-semibold";

interface Props {
    safraId: string;
}

export function PlanoAcaoCard({ safraId }: Props) {
    const queryClient = useQueryClient();
    const [mostrarIgnoradas, setMostrarIgnoradas] = useState(false);

    const { data: itens = [] } = useQuery<PlanoAcaoItem[]>({
        queryKey: ["plano-acoes", safraId],
        queryFn: () => apiFetch(`/financeiro/plano-acoes/?safra_id=${safraId}`),
        staleTime: 30_000,
        enabled: !!safraId,
    });

    const mutation = useMutation({
        mutationFn: ({ id, status }: { id: string; status: string }) =>
            apiFetch(`/financeiro/plano-acoes/${id}/status`, {
                method: "PATCH",
                body: JSON.stringify({ status }),
            }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["plano-acoes", safraId] }),
    });

    const visiveis = itens.filter((i) =>
        mostrarIgnoradas ? true : i.status !== "IGNORADA"
    );

    if (itens.length === 0) return null;

    const pendentes = itens.filter((i) => i.status === "PENDENTE").length;

    return (
        <section className="rounded-sm border border-border bg-card shadow-sm overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-border bg-muted/30">
                <div className="flex items-center gap-3">
                    <span className="size-8 rounded-sm bg-primary/10 border border-primary/15 flex items-center justify-center shrink-0">
                        <ClipboardList className="size-4 text-primary" />
                    </span>
                    <div>
                        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                            Plano de Ação
                        </p>
                        <p className="text-sm font-semibold text-foreground leading-tight">
                            {pendentes > 0
                                ? `${pendentes} ação${pendentes !== 1 ? "ões" : ""} pendente${pendentes !== 1 ? "s" : ""}`
                                : "Todas as ações concluídas"}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    <Switch
                        id="mostrar-ignoradas"
                        checked={mostrarIgnoradas}
                        onCheckedChange={setMostrarIgnoradas}
                        className="scale-75"
                    />
                    <Label htmlFor="mostrar-ignoradas" className="text-xs text-muted-foreground cursor-pointer">
                        Ver ignoradas
                    </Label>
                </div>
            </div>

            {/* Lista */}
            <ul className="divide-y divide-border">
                {visiveis.map((item) => {
                    const isPendente = item.status === "PENDENTE";
                    const isConcluida = item.status === "CONCLUIDA";
                    const isIgnorada = item.status === "IGNORADA";
                    const isLoading = mutation.isPending;

                    return (
                        <li
                            key={item.id}
                            className={`flex items-start gap-4 px-5 py-4 transition-colors ${isIgnorada ? "opacity-50" : "hover:bg-muted/20"}`}
                        >
                            <CircleDot
                                className={`size-4 mt-0.5 shrink-0 ${isConcluida ? "text-emerald-500" : isIgnorada ? "text-muted-foreground" : "text-primary"}`}
                            />
                            <div className="flex-1 min-w-0 space-y-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <p className={`text-sm font-semibold leading-snug ${isConcluida ? "line-through text-muted-foreground" : "text-foreground"}`}>
                                        {item.titulo}
                                    </p>
                                    <WorkflowStatusBadge status={item.status} />
                                    <span className={`text-[10px] font-bold uppercase ${PRIORIDADE_CLASS[item.prioridade] ?? "text-muted-foreground"}`}>
                                        {item.prioridade}
                                    </span>
                                </div>
                                <p className="text-xs text-muted-foreground leading-snug">
                                    {item.descricao}
                                </p>
                            </div>

                            {/* Ações */}
                            <div className="flex items-center gap-1 shrink-0">
                                {isPendente && (
                                    <>
                                        <Button
                                            size="icon"
                                            variant="ghost"
                                            className="size-7 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                                            title="Concluir"
                                            disabled={isLoading}
                                            onClick={() => mutation.mutate({ id: item.id, status: "CONCLUIDA" })}
                                        >
                                            <CheckCheck className="size-3.5" />
                                        </Button>
                                        <Button
                                            size="icon"
                                            variant="ghost"
                                            className="size-7 text-muted-foreground hover:text-foreground"
                                            title="Ignorar"
                                            disabled={isLoading}
                                            onClick={() => mutation.mutate({ id: item.id, status: "IGNORADA" })}
                                        >
                                            <EyeOff className="size-3.5" />
                                        </Button>
                                    </>
                                )}
                                {isPendente && (
                                    <>
                                        <Separator orientation="vertical" className="h-4 mx-1" />
                                        <Button
                                            asChild
                                            size="sm"
                                            variant="outline"
                                            className={cn(planoAcaoButtonClass, "text-primary hover:text-primary")}
                                        >
                                            <Link href={item.rota}>
                                                Executar
                                                <ChevronRight data-icon="inline-end" />
                                            </Link>
                                        </Button>
                                    </>
                                )}
                            </div>
                        </li>
                    );
                })}
            </ul>
        </section>
    );
}
