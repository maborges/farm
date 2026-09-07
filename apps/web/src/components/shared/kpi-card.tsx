"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface KPICardProps {
    label: string;
    value: string | number;
    subtitle?: string;
    icon: React.ElementType;
    iconBg: string;
    iconColor: string;
    valueSize?: "base" | "2xl";
    valueColor?: string;
    cardClassName?: string;
}

export function KPICard({
    label,
    value,
    subtitle,
    icon: Icon,
    iconBg,
    iconColor,
    valueSize = "2xl",
    valueColor,
    cardClassName,
}: KPICardProps) {
    return (
        <Card className={cn("shadow-sm", cardClassName)}>
            <CardContent className="p-4 flex gap-3 items-start">
                <div className={cn("p-2 rounded-lg shrink-0", iconBg)}>
                    <Icon className={cn("size-5", iconColor)} />
                </div>
                <div>
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className={cn(
                        "font-bold tabular-nums leading-tight",
                        valueSize === "2xl" ? "text-2xl" : "text-base",
                        valueColor,
                    )}>
                        {value}
                    </p>
                    {subtitle && (
                        <p className="text-xs text-muted-foreground">{subtitle}</p>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

// Formatadores compartilhados
export function moeda(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function num(v: number, dec = 0) {
    return v.toLocaleString("pt-BR", { maximumFractionDigits: dec });
}
