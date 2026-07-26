"use client";

import { AlertTriangle, Clock, type LucideIcon } from "lucide-react";

type AlertSeverity = "urgent" | "warning" | "info";

interface PwaAlertItem {
  id: string;
  label: string;
  severity: AlertSeverity;
}

interface PwaAlertStripProps {
  items: PwaAlertItem[];
  onTap?: () => void;
}

const SEVERITY: Record<AlertSeverity, { icon: LucideIcon; bg: string; text: string; border: string }> = {
  urgent: {
    icon: AlertTriangle,
    bg: "bg-rose-50 dark:bg-rose-950/30",
    text: "text-rose-800 dark:text-rose-200",
    border: "border-rose-200 dark:border-rose-900/60",
  },
  warning: {
    icon: Clock,
    bg: "bg-amber-50 dark:bg-amber-950/30",
    text: "text-amber-800 dark:text-amber-200",
    border: "border-amber-200 dark:border-amber-900/60",
  },
  info: {
    icon: AlertTriangle,
    bg: "bg-sky-50 dark:bg-sky-950/30",
    text: "text-sky-800 dark:text-sky-200",
    border: "border-sky-200 dark:border-sky-900/60",
  },
};

export function PwaAlertStrip({ items, onTap }: PwaAlertStripProps) {
  if (items.length === 0) return null;

  // Mostra no máximo 2 alertas; agrupa o resto
  const visible = items.slice(0, 2);
  const extra = items.length - 2;

  const sharedClassName = (s: { bg: string; text: string; border: string }) =>
    [
      "flex w-full items-center gap-2.5 rounded-xl border px-3.5 py-2.5 text-left",
      "transition-all duration-150 active:scale-[0.99]",
      s.bg,
      s.text,
      s.border,
    ].join(" ");

  return (
    <div className="campo-pwa-banner flex flex-col gap-1.5">
      {visible.map((item) => {
        const s = SEVERITY[item.severity];
        const Icon = s.icon;
        const className = sharedClassName(s);

        return onTap ? (
          <button
            key={item.id}
            type="button"
            onClick={onTap}
            className={className}
          >
            <Icon className="size-4 shrink-0" strokeWidth={2} />
            <span className="text-[12px] font-medium leading-snug">{item.label}</span>
          </button>
        ) : (
          <div key={item.id} className={className}>
            <Icon className="size-4 shrink-0" strokeWidth={2} />
            <span className="text-[12px] font-medium leading-snug">{item.label}</span>
          </div>
        );
      })}

      {extra > 0 && (
        <p className="px-1 text-[11px] text-muted-foreground">
          +{extra} alerta{extra !== 1 ? "s" : ""} — toque para ver todos
        </p>
      )}
    </div>
  );
}
