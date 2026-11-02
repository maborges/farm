"use client";

import type { CSSProperties } from "react";
import { type LucideIcon } from "lucide-react";
import { formatInt } from "@/lib/format";

type ModuleColor = "agro" | "pecuaria";

interface PwaModuleCardProps {
  label: string;
  sublabel: string;
  icon: LucideIcon;
  taskCount: number;
  urgentCount: number;
  color: ModuleColor;
  onClick: () => void;
  disabled?: boolean;
  animDelay?: string;
}

const COLOR_MAP: Record<
  ModuleColor,
  {
    border: string;
    bg: string;
    iconBg: string;
    iconColor: string;
    badgeBg: string;
    badgeText: string;
    urgentBg: string;
    urgentText: string;
    pulse: string;
  }
> = {
  agro: {
    border: "border-[var(--campo-pwa-agro-light)] dark:border-[var(--campo-pwa-agro-mid)]",
    bg: "bg-[var(--campo-pwa-agro-bg)] dark:bg-[var(--campo-pwa-agro-bg)]",
    iconBg: "bg-[var(--campo-pwa-agro-light)] dark:bg-[var(--campo-pwa-agro-light)]",
    iconColor: "text-[var(--campo-pwa-agro-dark-text)] dark:text-[var(--campo-pwa-agro)]",
    badgeBg: "bg-[var(--campo-pwa-agro-light)] dark:bg-[var(--campo-pwa-agro-light)]",
    badgeText: "text-[var(--campo-pwa-agro-dark-text)] dark:text-[var(--campo-pwa-agro)]",
    urgentBg: "bg-rose-100 dark:bg-rose-950/40",
    urgentText: "text-rose-700 dark:text-rose-300",
    pulse: "bg-[var(--campo-pwa-agro)]",
  },
  pecuaria: {
    border: "border-[var(--campo-pwa-pecuaria-light)] dark:border-[var(--campo-pwa-pecuaria-mid)]",
    bg: "bg-[var(--campo-pwa-pecuaria-bg)] dark:bg-[var(--campo-pwa-pecuaria-bg)]",
    iconBg: "bg-[var(--campo-pwa-pecuaria-light)] dark:bg-[var(--campo-pwa-pecuaria-light)]",
    iconColor: "text-[var(--campo-pwa-pecuaria-dark-text)] dark:text-[var(--campo-pwa-pecuaria)]",
    badgeBg: "bg-[var(--campo-pwa-pecuaria-light)] dark:bg-[var(--campo-pwa-pecuaria-light)]",
    badgeText: "text-[var(--campo-pwa-pecuaria-dark-text)] dark:text-[var(--campo-pwa-pecuaria)]",
    urgentBg: "bg-rose-100 dark:bg-rose-950/40",
    urgentText: "text-rose-700 dark:text-rose-300",
    pulse: "bg-[var(--campo-pwa-pecuaria)]",
  },
};

export function PwaModuleCard({
  label,
  sublabel,
  icon: Icon,
  taskCount,
  urgentCount,
  color,
  onClick,
  disabled = false,
  animDelay = "0ms",
}: PwaModuleCardProps) {
  const c = COLOR_MAP[color];

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{ "--campo-pwa-delay": animDelay } as CSSProperties}
      className={[
        "campo-pwa-card-stagger",
        "relative flex w-full flex-col rounded-sm border p-4 text-left shadow-xs",
        "transition-all duration-150 ease-out",
        "active:scale-[0.97] active:shadow-none",
        "hover-lift",
        "disabled:pointer-events-none disabled:opacity-40",
        c.border,
        c.bg,
      ].join(" ")}
    >
      {/* Dot de status ativo */}
      <span
        className={[
          "campo-pwa-pulse-dot absolute right-3.5 top-3.5 size-2 rounded-full",
          taskCount > 0 ? c.pulse : "bg-muted-foreground/30",
        ].join(" ")}
      />

      {/* Ícone */}
      <span
        className={[
          "flex size-11 items-center justify-center rounded-sm",
          c.iconBg,
          c.iconColor,
        ].join(" ")}
      >
        <Icon className="size-6" strokeWidth={1.85} />
      </span>

      {/* Título e subtítulo */}
      <p className="mt-3 text-sm sm:text-base font-bold tracking-tight text-foreground">
        {label}
      </p>
      <p className="mt-0.5 text-[11px] text-muted-foreground">{sublabel}</p>

      {/* Badges de contagem */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        <span
          className={[
            "inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-[10px] font-semibold",
            c.badgeBg,
            c.badgeText,
          ].join(" ")}
        >
          {formatInt(taskCount)} tarefa{taskCount !== 1 ? "s" : ""}
        </span>

        {urgentCount > 0 && (
          <span
            className={[
              "inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-[10px] font-semibold",
              c.urgentBg,
              c.urgentText,
            ].join(" ")}
          >
            {formatInt(urgentCount)} urgente{urgentCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Seta de acesso */}
      <div className="mt-3 flex items-center justify-end">
        <span className={["text-[11px] font-semibold", c.badgeText].join(" ")}>
          Acessar →
        </span>
      </div>
    </button>
  );
}
