"use client";

interface GpsWarningProps {
  status: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
  onRetry?: () => void;
}

export function GpsWarning({ status, onRetry }: GpsWarningProps) {
  if (status === "DISPONIVEL") return null;

  if (status === "AGUARDANDO") {
    return (
      <div className="bg-amber-950/60 border border-amber-800/50 rounded-xl px-3 py-2.5 flex items-center gap-2 text-sm">
        <span className="animate-spin text-base">⏳</span>
        <span className="text-amber-300">Localizando GPS...</span>
      </div>
    );
  }

  return (
    <div className="bg-neutral-800 border border-neutral-700 rounded-xl px-3 py-2.5 flex items-center justify-between text-sm">
      <div className="flex items-center gap-2">
        <span>📵</span>
        <span className="text-neutral-400">Sem GPS — registro será salvo sem localização</span>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="text-xs text-green-400 underline ml-2 shrink-0"
        >
          Tentar
        </button>
      )}
    </div>
  );
}
