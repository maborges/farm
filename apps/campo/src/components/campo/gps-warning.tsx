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
      <CampoSurface className="flex items-center gap-3 border-amber-400/20 bg-amber-400/12 px-4 py-3 text-sm text-amber-50">
        <span className="animate-spin text-base">⏳</span>
        <div className="flex-1">
          <p className="font-medium">Localizando GPS...</p>
          <p className="text-xs text-amber-100/70">A localização ajuda na rastreabilidade do registro.</p>
        </div>
      </CampoSurface>
    );
  }

  return (
    <CampoSurface className="flex items-center justify-between gap-3 px-4 py-3 text-sm text-white/75">
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
