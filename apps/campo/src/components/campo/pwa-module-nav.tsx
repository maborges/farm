"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { ArrowLeft } from "lucide-react";
import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";

type ModuleColor = "agro" | "pecuaria";

interface PwaModuleNavProps {
  title: string;
  color: ModuleColor;
  backHref?: string;
}

const COLOR: Record<ModuleColor, { text: string; dot: string; back: string }> = {
  agro: {
    text: "text-[var(--campo-pwa-agro-dark-text)] dark:text-[var(--campo-pwa-agro)]",
    dot: "bg-[var(--campo-pwa-agro)]",
    back: "hover:bg-[var(--campo-pwa-agro-light)]",
  },
  pecuaria: {
    text: "text-[var(--campo-pwa-pecuaria-dark-text)] dark:text-[var(--campo-pwa-pecuaria)]",
    dot: "bg-[var(--campo-pwa-pecuaria)]",
    back: "hover:bg-[var(--campo-pwa-pecuaria-light)]",
  },
};

export function PwaModuleNav({ title, color, backHref = "/home" }: PwaModuleNavProps) {
  const router = useRouter();
  const { session } = useSessionStore();
  const c = COLOR[color];

  const fazendas = useLiveQuery(async () => {
    const ids = session?.fazenda_ids ?? [];
    if (ids.length === 0) return [];
    const rows = await db.fazendas.bulkGet(ids);
    return rows.filter(Boolean);
  }, [session?.fazenda_ids?.join("|")]);

  const activeFazendaNome = useMemo(
    () => (fazendas ?? []).find((f) => f?.id === session?.active_fazenda_id)?.nome,
    [fazendas, session?.active_fazenda_id]
  );

  return (
    <div className="hidden md:flex items-center gap-2.5 pb-1">
      <button
        type="button"
        onClick={() => router.push(backHref)}
        className={[
          "flex size-9 shrink-0 items-center justify-center rounded-sm border border-border bg-card shadow-2xs",
          "transition-all duration-150 active:scale-95",
          c.back,
        ].join(" ")}
        aria-label="Voltar ao início"
      >
        <ArrowLeft className="size-4 text-muted-foreground" strokeWidth={2} />
      </button>

      <div className="flex min-w-0 flex-1 items-center gap-2">
        <span className={["campo-pwa-pulse-dot size-2 shrink-0 rounded-full", c.dot].join(" ")} />
        <div className="min-w-0">
          <p className={["text-[10px] font-bold uppercase tracking-[0.16em]", c.text].join(" ")}>
            {title}
          </p>
          {activeFazendaNome && (
            <p className="truncate text-xs text-muted-foreground">{activeFazendaNome}</p>
          )}
        </div>
      </div>
    </div>
  );
}
