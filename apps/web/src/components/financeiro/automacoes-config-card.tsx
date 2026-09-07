"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Settings2, CalendarClock } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

interface Configuracao {
    regra: string;
    titulo: string;
    descricao: string;
    ativa: boolean;
    frequencia: string;
    proxima_execucao: string | null;
}

interface Props {
    safraId: string;
}

const FREQUENCIAS = [
    { value: "MANUAL", label: "Manual" },
    { value: "DIARIA", label: "Diária" },
    { value: "SEMANAL", label: "Semanal" },
    { value: "MENSAL", label: "Mensal" },
];

export function AutomacoesConfigCard({ safraId }: Props) {
    const queryClient = useQueryClient();

    const { data: configs = [], isLoading } = useQuery<Configuracao[]>({
        queryKey: ["automacoes-config", safraId],
        queryFn: () => apiFetch(`/automacoes/configuracoes?safra_id=${safraId}`),
        staleTime: 60_000,
        enabled: !!safraId,
    });

    const mutation = useMutation({
        mutationFn: ({ regra, ativa, frequencia }: { regra: string; ativa: boolean; frequencia: string }) =>
            apiFetch(`/automacoes/configuracoes/${regra}?safra_id=${safraId}`, {
                method: "PATCH",
                body: JSON.stringify({ ativa, frequencia }),
            }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["automacoes-config", safraId] }),
    });

    const handleToggle = (cfg: Configuracao, checked: boolean) =>
        mutation.mutate({ regra: cfg.regra, ativa: checked, frequencia: cfg.frequencia });

    const handleFrequencia = (cfg: Configuracao, frequencia: string) =>
        mutation.mutate({ regra: cfg.regra, ativa: cfg.ativa, frequencia });

    return (
        <section className="rounded-sm border border-border bg-card shadow-sm overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-border bg-muted/30">
                <span className="size-8 rounded-sm bg-primary/10 border border-primary/15 flex items-center justify-center shrink-0">
                    <Settings2 className="size-4 text-primary" />
                </span>
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                        Automações
                    </p>
                    <p className="text-sm font-semibold text-foreground leading-tight">
                        Configurar regras ativas
                    </p>
                </div>
            </div>

            {/* Lista de regras */}
            <ul className="divide-y divide-border">
                {isLoading
                    ? Array.from({ length: 3 }).map((_, i) => (
                        <li key={i} className="flex items-center justify-between gap-4 px-5 py-4">
                            <div className="space-y-1.5 flex-1">
                                <Skeleton className="h-3.5 w-40" />
                                <Skeleton className="h-3 w-60" />
                            </div>
                            <Skeleton className="h-8 w-28 rounded-sm" />
                            <Skeleton className="h-5 w-9 rounded-full shrink-0" />
                        </li>
                    ))
                    : configs.map((cfg) => {
                        const switchId = `regra-${cfg.regra}`;
                        const proximaFormatada = cfg.proxima_execucao
                            ? format(new Date(cfg.proxima_execucao), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })
                            : null;

                        return (
                            <li key={cfg.regra} className="flex items-start justify-between gap-4 px-5 py-4 hover:bg-muted/20 transition-colors">
                                <div className="flex-1 min-w-0 space-y-0.5">
                                    <Label
                                        htmlFor={switchId}
                                        className={`text-sm font-semibold cursor-pointer leading-snug ${!cfg.ativa ? "text-muted-foreground" : "text-foreground"}`}
                                    >
                                        {cfg.titulo}
                                    </Label>
                                    <p className="text-xs text-muted-foreground leading-snug">
                                        {cfg.descricao}
                                    </p>
                                    {proximaFormatada && (
                                        <p className="flex items-center gap-1 text-[11px] text-primary/70 pt-0.5">
                                            <CalendarClock className="size-3 shrink-0" />
                                            Próxima: {proximaFormatada}
                                        </p>
                                    )}
                                </div>

                                <div className="flex items-center gap-3 shrink-0 mt-0.5">
                                    <Select
                                        value={cfg.frequencia}
                                        onValueChange={(val) => handleFrequencia(cfg, val)}
                                        disabled={mutation.isPending}
                                    >
                                        <SelectTrigger className="h-7 w-28 text-xs">
                                            <span className="truncate">
                                                {FREQUENCIAS.find((f) => f.value === cfg.frequencia)?.label ?? "Selecione"}
                                            </span>
                                        </SelectTrigger>
                                        <SelectContent>
                                            {FREQUENCIAS.map((f) => (
                                                <SelectItem key={f.value} value={f.value} className="text-xs">
                                                    {f.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>

                                    <Switch
                                        id={switchId}
                                        checked={cfg.ativa}
                                        disabled={mutation.isPending}
                                        onCheckedChange={(checked) => handleToggle(cfg, checked)}
                                    />
                                </div>
                            </li>
                        );
                    })}
            </ul>
        </section>
    );
}
