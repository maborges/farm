"use client";

import { RefreshCw, X } from "lucide-react";

import { CampoButton } from "@/components/campo/ui";

import { usePwaUpdateStore } from "@/lib/stores/pwa-update-store";
import { useSyncStore } from "@/lib/stores/sync-store";

/**
 * Banner não destrutivo exibido quando há nova versão do PWA Campo pronta para ativação.
 *
 * Args:
 *   className (string, opcional): Classes CSS adicionais para posicionamento no layout.
 *
 * Return:
 *   JSX.Element | null: Banner compacto com ação explícita de atualização ou null.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function CampoPwaUpdateBanner({ className }: { className?: string }) {
  const { hasUpdate, dismissed, isApplying, applyUpdate, dismiss } = usePwaUpdateStore();
  const pendingCount = useSyncStore((state) => state.pendingCount);

  if (!hasUpdate || dismissed) {
    return null;
  }

  const description =
    pendingCount > 0
      ? `Seus registros pendentes permanecem salvos no dispositivo (${pendingCount} na fila).`
      : "Toque em Atualizar para carregar as melhorias mais recentes.";

  return (
    <div
      role="status"
      aria-live="polite"
      className={[
        "rounded-sm border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs text-emerald-950 shadow-2xs dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="flex items-center justify-between gap-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-sm bg-emerald-600 text-white dark:bg-emerald-700">
            <RefreshCw className={`size-3.5 ${isApplying ? "animate-spin" : ""}`} />
          </span>
          <div className="min-w-0">
            <p className="truncate font-bold">Nova versão disponível</p>
            <p className="text-[11px] leading-snug text-emerald-900/80 dark:text-emerald-200/85">
              {description}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          <CampoButton
            type="button"
            variant="primary"
            size="sm"
            disabled={isApplying}
            onClick={() => void applyUpdate()}
            className="min-h-[32px] px-2.5 py-1 text-[11px]"
          >
            <RefreshCw className={`size-3.5 ${isApplying ? "animate-spin" : ""}`} />
            {isApplying ? "Atualizando..." : "Atualizar"}
          </CampoButton>
          <button
            type="button"
            onClick={dismiss}
            disabled={isApplying}
            aria-label="Dispensar aviso de atualização"
            className="inline-flex size-7 items-center justify-center rounded-sm text-emerald-900/70 hover:bg-emerald-200/60 hover:text-emerald-950 disabled:opacity-40 dark:text-emerald-200/75 dark:hover:bg-emerald-900/60 dark:hover:text-emerald-50"
          >
            <X className="size-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
