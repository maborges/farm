"use client";

import { differenceInDays, parseISO } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { Clock, AlertTriangle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface VigenciaBadgeProps {
    vigencia_inicio?: string | null;
    vigencia_fim?: string | null;
    className?: string;
}

export function VigenciaBadge({ vigencia_inicio, vigencia_fim, className }: VigenciaBadgeProps) {
    if (!vigencia_fim && !vigencia_inicio) return null;

    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);

    if (vigencia_inicio) {
        const inicio = parseISO(vigencia_inicio);
        if (inicio > hoje) {
            return (
                <Badge variant="outline" className={cn("gap-1 text-[10px] text-amber-600 border-amber-200 bg-amber-50", className)}>
                    <Clock className="size-3" />
                    Início em {differenceInDays(inicio, hoje)}d
                </Badge>
            );
        }
    }

    if (!vigencia_fim) return null;

    const fim = parseISO(vigencia_fim);
    const diasRestantes = differenceInDays(fim, hoje);

    if (diasRestantes < 0) {
        return (
            <Badge variant="destructive" className={cn("gap-1 text-[10px]", className)}>
                <AlertTriangle className="size-3" />
                Expirado
            </Badge>
        );
    }

    if (diasRestantes <= 30) {
        return (
            <Badge variant="outline" className={cn("gap-1 text-[10px] text-orange-600 border-orange-200 bg-orange-50", className)}>
                <AlertTriangle className="size-3" />
                Expira em {diasRestantes}d
            </Badge>
        );
    }

    return (
        <Badge variant="outline" className={cn("gap-1 text-[10px] text-green-600 border-green-200 bg-green-50", className)}>
            <CheckCircle2 className="size-3" />
            Até {fim.toLocaleDateString("pt-BR")}
        </Badge>
    );
}
