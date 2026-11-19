"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type KPICardTone =
    | "default"
    | "primary"
    | "info"
    | "warning"
    | "success"
    | "destructive";

const KPI_TONE_STYLES: Record<
    KPICardTone,
    { iconBox: string; value: string; border: string }
> = {
    default: {
        iconBox: "bg-muted text-muted-foreground",
        value: "text-foreground",
        border: "",
    },
    primary: {
        iconBox: "bg-primary/10 text-primary",
        value: "text-primary",
        border: "border-primary/40",
    },
    info: {
        iconBox: "bg-alert-info-bg text-alert-info-icon border border-alert-info-border",
        value: "text-alert-info-icon",
        border: "border-alert-info-border",
    },
    warning: {
        iconBox: "bg-alert-warning-bg text-alert-warning-icon border border-alert-warning-border",
        value: "text-alert-warning-icon",
        border: "border-alert-warning-border",
    },
    success: {
        iconBox: "bg-alert-success-bg text-alert-success-icon border border-alert-success-border",
        value: "text-alert-success-icon",
        border: "border-alert-success-border",
    },
    destructive: {
        iconBox: "bg-alert-destructive-bg text-alert-destructive-icon border border-alert-destructive-border",
        value: "text-alert-destructive-icon",
        border: "border-alert-destructive-border",
    },
};

export interface KPICardProps {
    label: string;
    value: string | number;
    subtitle?: string;
    icon: React.ElementType;
    tone?: KPICardTone;
    valueTone?: KPICardTone;
    highlightBorder?: boolean;
    iconBg?: string;
    iconColor?: string;
    valueSize?: "base" | "2xl";
    valueColor?: string;
    cardClassName?: string;
}

export function KPICard({
    label,
    value,
    subtitle,
    icon: Icon,
    tone = "default",
    valueTone,
    highlightBorder = false,
    iconBg,
    iconColor,
    valueSize = "2xl",
    valueColor,
    cardClassName,
}: KPICardProps) {
    const toneStyle = KPI_TONE_STYLES[tone];

    return (
        <Card className={cn("shadow-sm", highlightBorder && toneStyle.border, cardClassName)}>
            <CardContent className="p-4 flex gap-3 items-start">
                <div className={cn("p-2 rounded-sm shrink-0", toneStyle.iconBox, iconBg)}>
                    <Icon className={cn("size-5", iconColor)} />
                </div>
                <div>
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className={cn(
                        "font-bold tabular-nums leading-tight",
                        valueSize === "2xl" ? "text-2xl" : "text-base",
                        valueTone && KPI_TONE_STYLES[valueTone].value,
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
