"use client";

import { formatInt } from "@/lib/format";

interface PwaProgressRingProps {
  done: number;
  total: number;
  label?: string;
}

export function PwaProgressRing({ done, total, label }: PwaProgressRingProps) {
  if (total === 0) return null;

  const pct = Math.min(100, Math.round((done / total) * 100));
  const dots = Math.max(5, Math.min(10, total));
  const doneDots = Math.round((done / total) * dots);

  return (
    <div className="campo-pwa-card-stagger flex flex-col gap-2 rounded-sm border border-border bg-card px-4 py-3.5 shadow-xs"
         style={{ "--campo-pwa-delay": "200ms" } as React.CSSProperties}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          {label ?? "Progresso de hoje"}
        </p>
        <p className="text-[11px] font-semibold text-foreground">
          {formatInt(done)}/{formatInt(total)} <span className="font-normal text-muted-foreground">tarefas</span>
        </p>
      </div>

      {/* Barra de progresso */}
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="campo-pwa-progress-bar absolute left-0 top-0 h-full rounded-full bg-[var(--campo-pwa-agro)]"
          style={{ "--campo-pwa-progress-target": `${pct}%` } as React.CSSProperties}
        />
      </div>

      {/* Dots indicadores */}
      <div className="flex items-center gap-1">
        {Array.from({ length: dots }).map((_, i) => (
          <span
            key={i}
            className={[
              "h-1.5 flex-1 rounded-full transition-colors duration-300",
              i < doneDots
                ? "bg-[var(--campo-pwa-agro)] dark:bg-[var(--campo-pwa-agro)]"
                : "bg-muted",
            ].join(" ")}
          />
        ))}
      </div>
    </div>
  );
}
