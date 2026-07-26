"use client";

import { type LucideIcon } from "lucide-react";

type QuickActionColor = "agro" | "pecuaria" | "neutral";

interface PwaQuickActionProps {
  label: string;
  icon: LucideIcon;
  onClick: () => void;
  color?: QuickActionColor;
  badge?: string;
}

const COLOR_CLASSES: Record<QuickActionColor, { bg: string; icon: string; text: string }> = {
  agro: {
    bg: "bg-[var(--campo-pwa-agro-bg)] border-[var(--campo-pwa-agro-light)] dark:border-[var(--campo-pwa-agro-mid)] hover:bg-[var(--campo-pwa-agro-light)]",
    icon: "text-[var(--campo-pwa-agro-dark-text)] dark:text-[var(--campo-pwa-agro)]",
    text: "text-foreground",
  },
  pecuaria: {
    bg: "bg-[var(--campo-pwa-pecuaria-bg)] border-[var(--campo-pwa-pecuaria-light)] dark:border-[var(--campo-pwa-pecuaria-mid)] hover:bg-[var(--campo-pwa-pecuaria-light)]",
    icon: "text-[var(--campo-pwa-pecuaria-dark-text)] dark:text-[var(--campo-pwa-pecuaria)]",
    text: "text-foreground",
  },
  neutral: {
    bg: "bg-card border-border hover:bg-muted",
    icon: "text-muted-foreground",
    text: "text-foreground",
  },
};

export function PwaQuickAction({
  label,
  icon: Icon,
  onClick,
  color = "neutral",
  badge,
}: PwaQuickActionProps) {
  const c = COLOR_CLASSES[color];

  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "relative flex flex-col items-center justify-center gap-2 rounded-2xl border px-3 py-4 text-center shadow-sm",
        "transition-all duration-150 ease-out",
        "active:scale-[0.95] active:shadow-none",
        c.bg,
      ].join(" ")}
    >
      {badge && (
        <span className="absolute -right-1.5 -top-1.5 flex size-4 items-center justify-center rounded-full bg-rose-500 text-[9px] font-bold text-white shadow-sm">
          {badge}
        </span>
      )}

      <span
        className={[
          "flex size-11 items-center justify-center rounded-xl",
          "bg-white/60 dark:bg-black/20",
          c.icon,
        ].join(" ")}
      >
        <Icon className="size-5" strokeWidth={2} />
      </span>

      <span className={["text-[11px] font-semibold leading-tight", c.text].join(" ")}>
        {label}
      </span>
    </button>
  );
}
