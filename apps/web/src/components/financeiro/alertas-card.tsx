"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Info, XOctagon, BellDot } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AlertaSafra {
    tipo: string;
    nivel: "info" | "warning" | "danger";
    mensagem: string;
}

const NIVEL_CONFIG: Record<
    "info" | "warning" | "danger",
    {
        icon: React.ReactNode;
        containerClass: string;
        iconWrapClass: string;
        badgeClass: string;
        label: string;
    }
> = {
    info: {
        icon: <Info className="size-3.5" />,
        containerClass:
            "border-blue-200/70 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-800/40",
        iconWrapClass:
            "bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400",
        badgeClass:
            "border-blue-300 text-blue-700 dark:text-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-950/40",
        label: "Info",
    },
    warning: {
        icon: <AlertTriangle className="size-3.5" />,
        containerClass:
            "border-amber-200/70 bg-amber-50/50 dark:bg-amber-950/20 dark:border-amber-800/40",
        iconWrapClass:
            "bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400",
        badgeClass:
            "border-amber-300 text-amber-700 dark:text-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40",
        label: "Atenção",
    },
    danger: {
        icon: <XOctagon className="size-3.5" />,
        containerClass: "border-destructive/30 bg-destructive/5 dark:bg-destructive/10",
        iconWrapClass: "bg-destructive/10 text-destructive",
        badgeClass:
            "border-destructive/40 text-destructive bg-destructive/5",
        label: "Crítico",
    },
};

interface Props {
    safraId: string;
}

/**
 * Exibe alertas financeiros automáticos baseados em regras de negócio.
 * Os alertas são gerados em runtime pelo backend — sem persistência.
 * Revalida automaticamente a cada 60 segundos.
 */
export function AlertasCard({ safraId }: Props) {
    const { data: alertas } = useQuery<AlertaSafra[]>({
        queryKey: ["financeiro-alertas", safraId],
        queryFn: () =>
            apiFetch(`/financeiro/lancamentos/alertas?safra_id=${safraId}`),
        staleTime: 60_000,
        refetchInterval: 60_000,
        enabled: !!safraId,
    });

    if (!alertas || alertas.length === 0) return null;

    const dangerCount = alertas.filter((a) => a.nivel === "danger").length;
    const warningCount = alertas.filter((a) => a.nivel === "warning").length;

    return (
        <section
            className="rounded-sm border border-amber-200/60 dark:border-amber-800/30 bg-card shadow-sm"
            aria-label="Alertas financeiros da safra"
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-border/60">
                <div className="flex items-center gap-2">
                    <span className="size-8 rounded-sm bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
                        <BellDot className="size-4 text-amber-600 dark:text-amber-400" />
                    </span>
                    <div>
                        <p className="text-sm font-bold tracking-tight">
                            Alertas da Safra
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                            {alertas.length} ocorrência{alertas.length !== 1 ? "s" : ""} ativa{alertas.length !== 1 ? "s" : ""}
                        </p>
                    </div>
                </div>
                <div className="flex gap-1.5">
                    {dangerCount > 0 && (
                        <Badge
                            variant="outline"
                            className="h-5 px-2 text-[10px] font-black border-destructive/40 text-destructive bg-destructive/5"
                        >
                            {dangerCount} crítico{dangerCount !== 1 ? "s" : ""}
                        </Badge>
                    )}
                    {warningCount > 0 && (
                        <Badge
                            variant="outline"
                            className="h-5 px-2 text-[10px] font-black border-amber-300 text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40"
                        >
                            {warningCount} aviso{warningCount !== 1 ? "s" : ""}
                        </Badge>
                    )}
                </div>
            </div>

            {/* Alert list */}
            <div className="flex flex-col gap-2 p-3">
                {alertas.map((alerta, i) => {
                    const cfg =
                        NIVEL_CONFIG[alerta.nivel] ?? NIVEL_CONFIG.info;
                    return (
                        <div
                            key={i}
                            className={cn(
                                "flex items-start gap-3 rounded-sm border px-3 py-2.5 transition-colors",
                                cfg.containerClass,
                            )}
                        >
                            <span
                                className={cn(
                                    "size-6 rounded flex items-center justify-center shrink-0 mt-0.5",
                                    cfg.iconWrapClass,
                                )}
                            >
                                {cfg.icon}
                            </span>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium leading-snug text-foreground">
                                    {alerta.mensagem}
                                </p>
                            </div>
                            <Badge
                                variant="outline"
                                className={cn(
                                    "h-5 px-2 text-[10px] font-black shrink-0 rounded-sm",
                                    cfg.badgeClass,
                                )}
                            >
                                {cfg.label}
                            </Badge>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}
