"use client";

import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

type SurfaceProps = HTMLAttributes<HTMLDivElement>;

export function CampoShell({ className, children }: SurfaceProps) {
  return (
    <div className={cn("flex min-h-dvh w-full flex-col px-4 pb-8 pt-4 sm:px-6 lg:px-8", className)}>
      {children}
    </div>
  );
}

export function CampoSurface({ className, children }: SurfaceProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-sm border border-border bg-card p-5 text-card-foreground shadow-sm",
        className
      )}
    >
      {children}
    </div>
  );
}

export function CampoSectionTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
            {eyebrow}
          </p>
        )}
        <h2 className="mt-1 text-sm font-semibold text-foreground">{title}</h2>
        {description && <p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function CampoButton({
  className,
  variant = "primary",
  size = "md",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}) {
  const sizeClasses =
    size === "sm"
      ? "px-3 py-2 text-xs"
      : size === "lg"
      ? "px-5 py-4 text-base"
      : "px-4 py-3 text-sm";

  const variantClasses = {
    primary:
      "border border-primary bg-primary text-primary-foreground shadow-sm hover:bg-primary/90",
    secondary:
      "border border-border bg-card text-foreground shadow-sm hover:bg-muted",
    ghost:
      "bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground",
    danger:
      "border border-destructive bg-destructive text-white shadow-sm hover:bg-destructive/90",
  }[variant];

  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-sm font-semibold active:scale-[0.98] disabled:pointer-events-none disabled:opacity-45",
        sizeClasses,
        variantClasses,
        className
      )}
    >
      {children}
    </button>
  );
}

export function CampoPill({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-border bg-muted px-3 py-1 text-xs font-medium text-muted-foreground",
        className
      )}
    >
      {children}
    </span>
  );
}

export function CampoMetric({
  label,
  value,
  tone = "emerald",
  compact = false,
}: {
  label: string;
  value: string | number;
  tone?: "emerald" | "amber" | "sky" | "rose";
  compact?: boolean;
}) {
  const toneClasses = {
    emerald: "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200",
    amber: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200",
    sky: "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200",
    rose: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200",
  }[tone];

  return (
    <div className={cn("rounded-sm border shadow-sm", compact ? "p-3" : "p-4", toneClasses)}>
      <p className={cn("uppercase tracking-[0.16em] opacity-70", compact ? "text-[10px]" : "text-[11px]")}>
        {label}
      </p>
      <p className={cn("font-semibold tabular-nums", compact ? "mt-1.5 text-xl" : "mt-2 text-2xl")}>
        {value}
      </p>
    </div>
  );
}
