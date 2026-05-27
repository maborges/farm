"use client";

import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

type SurfaceProps = HTMLAttributes<HTMLDivElement>;

export function CampoShell({ className, children }: SurfaceProps) {
  return (
    <div className={cn("mx-auto flex min-h-dvh w-full max-w-[1080px] flex-col px-4 pb-8 pt-4 sm:px-6 lg:px-8", className)}>
      {children}
    </div>
  );
}

export function CampoSurface({ className, children }: SurfaceProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[28px] border border-white/10 bg-white/[0.04] p-5 shadow-[0_20px_60px_rgba(0,0,0,0.35)] backdrop-blur-xl",
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
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-300/80">
            {eyebrow}
          </p>
        )}
        <h2 className="mt-1 text-sm font-semibold text-white">{title}</h2>
        {description && <p className="mt-1 text-xs leading-5 text-white/55">{description}</p>}
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
      "bg-gradient-to-r from-emerald-500 via-emerald-400 to-lime-300 text-emerald-950 shadow-[0_10px_25px_rgba(16,185,129,0.28)] hover:brightness-105",
    secondary:
      "border border-white/10 bg-white/[0.06] text-white hover:bg-white/[0.1]",
    ghost:
      "bg-transparent text-white/75 hover:bg-white/6 hover:text-white",
    danger:
      "bg-rose-500/90 text-white hover:bg-rose-500",
  }[variant];

  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-2xl font-semibold transition-all active:scale-[0.98] disabled:pointer-events-none disabled:opacity-45",
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
        "inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs font-medium text-white/82",
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
}: {
  label: string;
  value: string | number;
  tone?: "emerald" | "amber" | "sky" | "rose";
}) {
  const toneClasses = {
    emerald: "from-emerald-400/18 to-emerald-500/6 text-emerald-100",
    amber: "from-amber-400/18 to-amber-500/6 text-amber-100",
    sky: "from-sky-400/18 to-sky-500/6 text-sky-100",
    rose: "from-rose-400/18 to-rose-500/6 text-rose-100",
  }[tone];

  return (
    <div className={cn("rounded-3xl border border-white/10 bg-gradient-to-br p-4", toneClasses)}>
      <p className="text-[11px] uppercase tracking-[0.18em] text-white/55">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
