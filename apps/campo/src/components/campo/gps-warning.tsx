"use client";

import { CampoButton, CampoSurface } from "./ui";

interface GpsWarningProps {
  status: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
  onRetry?: () => void;
}

export function GpsWarning({ status, onRetry }: GpsWarningProps) {
  if (status === "DISPONIVEL") return null;

  if (status === "AGUARDANDO") {
    return (
      <CampoSurface className="flex items-center gap-2.5 border-amber-200 bg-amber-50 px-3.5 py-2.5 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
        <span className="animate-spin text-sm">⏳</span>
        <div className="flex-1">
          <p className="font-medium">Localizando GPS...</p>
          <p className="text-xs opacity-70">A localização ajuda na rastreabilidade do registro.</p>
        </div>
      </CampoSurface>
    );
  }

  return (
    <CampoSurface className="flex items-center justify-between gap-2.5 px-3.5 py-2.5 text-sm text-muted-foreground">
      <div className="flex items-center gap-2">
        <span>📵</span>
        <span>Sem GPS - o registro será salvo sem localização.</span>
      </div>
      {onRetry && (
        <CampoButton
          type="button"
          onClick={onRetry}
          variant="secondary"
          size="sm"
          className="shrink-0"
        >
          Tentar
        </CampoButton>
      )}
    </CampoSurface>
  );
}
