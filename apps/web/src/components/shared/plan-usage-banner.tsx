"use client";

import { AlertTriangle, CheckCircle2, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface PlanUsageBannerProps {
    label: string;
    atual: number;
    limite: number | null;
    atingido: boolean;
    hint?: string;
    className?: string;
}

export function PlanUsageBanner({ label, atual, limite, atingido, hint, className }: PlanUsageBannerProps) {
    const ilimitado = limite === null || limite === -1;
    const pct = ilimitado ? 0 : Math.round((atual / limite!) * 100);
    const alerta = !ilimitado && pct >= 80 && !atingido;

    return (
        <div className={cn(
            "flex items-center gap-3 text-sm px-4 py-2.5 rounded-sm border",
            atingido && "border-alert-destructive-border bg-alert-destructive-bg text-alert-destructive-title",
            alerta && "border-alert-warning-border bg-alert-warning-bg text-alert-warning-title",
            !atingido && !alerta && "border-alert-default-border bg-alert-default-bg text-alert-default-description",
            className,
        )}>
            {atingido
                ? <AlertTriangle className="size-4 shrink-0 text-alert-destructive-icon" />
                : alerta
                    ? <TrendingUp className="size-4 shrink-0 text-alert-warning-icon" />
                    : <CheckCircle2 className="size-4 shrink-0 text-alert-default-icon" />}

            <div className="flex-1 min-w-0">
                <span>
                    {ilimitado
                        ? `${atual} ${label} cadastrada(s) — ilimitado`
                        : `${atual} de ${limite} ${label}`}
                </span>
                {!ilimitado && (
                    <Progress
                        value={pct}
                        className={cn(
                            "h-1.5 mt-1",
                            atingido && "[&>div]:bg-alert-destructive-icon",
                            alerta && "[&>div]:bg-alert-warning-icon",
                        )}
                    />
                )}
                {hint && (
                    <p className="text-xs opacity-80 mt-1">{hint}</p>
                )}
            </div>

            {(atingido || alerta) && (
                <Button
                    variant="link"
                    size="sm"
                    className={cn(
                        "ml-auto h-auto p-0 shrink-0",
                        atingido ? "text-alert-destructive-title" : "text-alert-warning-title",
                    )}
                    asChild
                >
                    <Link href="/dashboard/settings/billing">Upgrade</Link>
                </Button>
            )}
        </div>
    );
}
