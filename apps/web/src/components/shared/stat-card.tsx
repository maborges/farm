"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const statCardVariants = cva(
  "transition-shadow hover:shadow-md border-l-[3px]",
  {
    variants: {
      color: {
        primary:     "border-l-primary",
        agro:        "border-l-[var(--module-agro)]",
        pecuaria:    "border-l-[var(--module-pecuaria)]",
        financeiro:  "border-l-[var(--module-financeiro)]",
        operacional: "border-l-[var(--module-operacional)]",
        backoffice:  "border-l-[var(--module-backoffice)]",
        info:        "border-l-alert-info-icon",
        success:     "border-l-[var(--module-agro)]",
        warning:     "border-l-alert-warning-icon",
        destructive: "border-l-alert-destructive-icon",
        muted:       "border-l-muted-foreground/40",
      },
    },
    defaultVariants: { color: "primary" },
  }
);

const statIconVariants = cva(
  "size-11 rounded-full flex items-center justify-center [&>svg]:size-5 shrink-0",
  {
    variants: {
      color: {
        primary:     "bg-primary/10 text-primary",
        agro:        "bg-[var(--module-agro-bg)] text-[var(--module-agro)]",
        pecuaria:    "bg-[var(--module-pecuaria-bg)] text-[var(--module-pecuaria)]",
        financeiro:  "bg-[var(--module-financeiro-bg)] text-[var(--module-financeiro)]",
        operacional: "bg-[var(--module-operacional-bg)] text-[var(--module-operacional)]",
        backoffice:  "bg-[var(--module-backoffice-bg)] text-[var(--module-backoffice)]",
        info:        "bg-alert-info-bg text-alert-info-icon",
        success:     "bg-[var(--module-agro-bg)] text-[var(--module-agro)]",
        warning:     "bg-alert-warning-bg text-alert-warning-icon",
        destructive: "bg-alert-destructive-bg text-alert-destructive-icon",
        muted:       "bg-muted text-muted-foreground",
      },
    },
    defaultVariants: { color: "primary" },
  }
);

interface StatCardProps extends VariantProps<typeof statCardVariants> {
  icon?: React.ComponentType<{ className?: string }>;
  label: string;
  value: number | string;
  subtitle?: string;
  onClick?: () => void;
  className?: string;
}

export function StatCard({
  icon: Icon,
  label,
  value,
  subtitle,
  color,
  onClick,
  className,
}: StatCardProps) {
  return (
    <Card
      className={cn(statCardVariants({ color }), onClick && "cursor-pointer", className)}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (event) => {
        if (event.key !== "Enter" && event.key !== " ") return
        event.preventDefault()
        onClick()
      } : undefined}
    >
      <CardContent className="p-4 flex items-center gap-4">
        {Icon && (
          <div className={statIconVariants({ color })}>
            <Icon className="size-5" />
          </div>
        )}
        <div className={cn("min-w-0", Icon ? "flex-1" : "w-full")}>
          <p className="text-xs font-semibold text-muted-foreground uppercase">
            {label}
          </p>
          <p className="text-2xl font-black tabular-nums leading-tight">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-0.5 text-pretty">{subtitle}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
