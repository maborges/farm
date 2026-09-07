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
    className?: string;
}

export function PlanUsageBanner({ label, atual, limite, atingido, className }: PlanUsageBannerProps) {
    const ilimitado = limite === null || limite === -1;
    const pct = ilimitado ? 0 : Math.round((atual / limite!) * 100);
    const alerta = !ilimitado && pct >= 80 && !atingido;

    return (
        <div className={cn(
            "flex items-center gap-3 text-sm px-4 py-2.5 rounded-lg border",
            atingido && "bg-destructive/10 border-destructive/30 text-destructive",
            alerta && "bg-amber-50 border-amber-200 text-amber-700",
            !atingido && !alerta && "bg-muted/30 border-muted text-muted-foreground",
            className,
        )}>
            {atingido
                ? <AlertTriangle className="size-4 shrink-0" />
                : alerta
                    ? <TrendingUp className="size-4 shrink-0" />
                    : <CheckCircle2 className="size-4 shrink-0" />}

            <div className="flex-1 min-w-0">
                <span>
                    {ilimitado
                        ? `${atual} ${label} cadastrada(s) — ilimitado`
                        : `${atual} de ${limite} ${label}`}
                </span>
                {!ilimitado && (
                    <Progress
                        value={pct}
                        className={cn("h-1.5 mt-1", atingido && "[&>div]:bg-destructive", alerta && "[&>div]:bg-amber-500")}
                    />
                )}
            </div>

            {(atingido || alerta) && (
                <Button variant="link" size="sm" className={cn("ml-auto h-auto p-0 shrink-0", atingido ? "text-destructive" : "text-amber-700")} asChild>
                    <Link href="/dashboard/settings/billing">Upgrade</Link>
                </Button>
            )}
        </div>
    );
}
