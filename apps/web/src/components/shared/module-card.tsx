"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

// ─── Variants ───────────────────────────────────────────────
const moduleCardVariants = cva(
  "group relative overflow-hidden border transition-shadow hover:shadow-md focus-within:ring-2 focus-within:ring-ring",
  {
    variants: {
      module: {
        agro:        "border-l-[3px] border-l-[var(--module-agro)]",
        pecuaria:    "border-l-[3px] border-l-[var(--module-pecuaria)]",
        financeiro:  "border-l-[3px] border-l-[var(--module-financeiro)]",
        operacional: "border-l-[3px] border-l-[var(--module-operacional)]",
        backoffice:  "border-l-[3px] border-l-[var(--module-backoffice)]",
        neutral:     "border-l-[3px] border-l-muted-foreground/30",
      },
      size: {
        sm: "",
        md: "",
      },
    },
    defaultVariants: {
      module: "neutral",
      size: "md",
    },
  }
);

const moduleIconVariants = cva(
  "flex items-center justify-center rounded-sm",
  {
    variants: {
      module: {
        agro:        "bg-[var(--module-agro-bg)] text-[var(--module-agro)]",
        pecuaria:    "bg-[var(--module-pecuaria-bg)] text-[var(--module-pecuaria)]",
        financeiro:  "bg-[var(--module-financeiro-bg)] text-[var(--module-financeiro)]",
        operacional: "bg-[var(--module-operacional-bg)] text-[var(--module-operacional)]",
        backoffice:  "bg-[var(--module-backoffice-bg)] text-[var(--module-backoffice)]",
        neutral:     "bg-muted text-muted-foreground",
      },
      size: {
        sm: "size-9 [&>svg]:size-4",
        md: "size-11 [&>svg]:size-5",
      },
    },
    defaultVariants: {
      module: "neutral",
      size: "md",
    },
  }
);

// ─── Types ───────────────────────────────────────────────────
export interface ModuleCardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof moduleCardVariants> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  headerAction?: React.ReactNode;
  /** Wrap em Link externo: passar o wrapper como children ou usar asChild pattern */
  disabled?: boolean;
}

// ─── Component ───────────────────────────────────────────────
export function ModuleCard({
  module,
  size,
  icon,
  title,
  description,
  headerAction,
  disabled = false,
  className,
  children,
  ...props
}: ModuleCardProps) {
  return (
    <Card
      className={cn(
        moduleCardVariants({ module, size }),
        disabled && "opacity-60 grayscale pointer-events-none",
        className
      )}
      {...props}
    >
      {(icon || size === "md") && (
        <CardHeader className="pb-2 pt-4 px-4">
          {icon && (
            <div className={moduleIconVariants({ module, size })}>
              {icon}
            </div>
          )}
        </CardHeader>
      )}
      <CardContent className={cn("px-4 pb-4", !icon && "pt-4", "space-y-1")}>
        <div className="flex items-start justify-between gap-2">
          <p className="min-w-0 font-semibold text-sm text-foreground text-balance">{title}</p>
          {headerAction && <div className="-mr-2 -mt-2 shrink-0">{headerAction}</div>}
        </div>
        {description && (
          <p className="text-xs text-muted-foreground text-pretty leading-relaxed">
            {description}
          </p>
        )}
        {children}
      </CardContent>
    </Card>
  );
}

// ─── Compact horizontal variant ──────────────────────────────
export interface ModuleCardRowProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof moduleCardVariants> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
}

export function ModuleCardRow({
  module,
  size: _size,
  icon,
  title,
  description,
  className,
  ...props
}: ModuleCardRowProps) {
  void _size;
  return (
    <Card
      className={cn(
        moduleCardVariants({ module }),
        "hover:shadow-md transition-shadow",
        className
      )}
      {...props}
    >
      <CardContent className="flex items-center gap-4 p-4">
        {icon && (
          <div className={cn(moduleIconVariants({ module, size: "sm" }), "shrink-0")}>
            {icon}
          </div>
        )}
        <div className="min-w-0">
          <p className="font-semibold text-sm text-foreground text-balance truncate">{title}</p>
          {description && (
            <p className="text-xs text-muted-foreground text-pretty mt-0.5">{description}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
