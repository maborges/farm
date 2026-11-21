"use client";

import { cn } from "@/lib/utils";

type StatusVariant = "ativo" | "inativo" | "pendente" | "expirado" | "trial";

const VARIANT_STYLES: Record<StatusVariant, string> = {
    ativo: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-400/30",
    inativo: "bg-muted text-muted-foreground border-muted dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700",
    pendente: "bg-amber-500/10 text-amber-700 border-amber-500/20 dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-400/30",
    expirado: "bg-red-500/10 text-red-700 border-red-500/20 dark:bg-red-500/20 dark:text-red-300 dark:border-red-400/30",
    trial: "bg-blue-500/10 text-blue-700 border-blue-500/20 dark:bg-blue-500/20 dark:text-blue-300 dark:border-blue-400/30",
};

const VARIANT_LABELS: Record<StatusVariant, string> = {
    ativo: "Ativo",
    inativo: "Inativo",
    pendente: "Pendente",
    expirado: "Expirado",
    trial: "Trial",
};

interface StatusBadgeProps {
    status: StatusVariant;
    label?: string;
    className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
    return (
        <span
            data-slot="status-badge"
            className={cn(
                "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium",
                VARIANT_STYLES[status],
                className
            )}
        >
            {label ?? VARIANT_LABELS[status]}
        </span>
    );
}
