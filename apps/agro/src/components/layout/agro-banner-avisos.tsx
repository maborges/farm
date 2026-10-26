"use client";

import React, { useState } from "react";
import { AlertTriangle, AlertCircle, Info, X, ExternalLink } from "lucide-react";
import { useAgroConfig, AgroMensagemFinalidade } from "@/lib/config/agro-config";

function getFinalidadeBadge(finalidade: AgroMensagemFinalidade) {
  switch (finalidade) {
    case "URGENTE":
      return {
        bg: "bg-red-500/15 border-red-500/30 text-red-700 dark:text-red-300",
        icon: AlertCircle,
        label: "Urgente",
      };
    case "REGULATORIO":
      return {
        bg: "bg-amber-500/15 border-amber-500/30 text-amber-800 dark:text-amber-300",
        icon: AlertTriangle,
        label: "Regulatório",
      };
    case "MANUTENCAO":
      return {
        bg: "bg-orange-500/15 border-orange-500/30 text-orange-800 dark:text-orange-300",
        icon: AlertTriangle,
        label: "Manutenção",
      };
    case "NOVIDADE":
      return {
        bg: "bg-emerald-500/15 border-emerald-500/30 text-emerald-800 dark:text-emerald-300",
        icon: Info,
        label: "Novidade",
      };
    default:
      return {
        bg: "bg-blue-500/15 border-blue-500/30 text-blue-800 dark:text-blue-300",
        icon: Info,
        label: "Comunicado",
      };
  }
}

export function AgroBannerAvisos() {
  const { config } = useAgroConfig();
  const [dismissed, setDismissed] = useState<Record<string, boolean>>({});

  const bannerUrgente = config.banner_urgente;
  const mensagensVigentes = config.mensagens_vigentes.filter(
    (m) => !dismissed[m.id]
  );

  if (!bannerUrgente && mensagensVigentes.length === 0) {
    return null;
  }

  return (
    <div className="w-full flex flex-col gap-1.5" role="region" aria-label="Avisos e comunicados institucionais">
      {/* Banner Urgente Global */}
      {bannerUrgente && !dismissed["global-banner"] && (
        <div className="bg-red-600 text-white px-4 py-2 text-xs font-semibold flex items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2 max-w-5xl mx-auto flex-1">
            <AlertCircle size={15} className="flex-shrink-0 text-white" />
            <span>{bannerUrgente}</span>
          </div>
          <button
            onClick={() => setDismissed((prev) => ({ ...prev, "global-banner": true }))}
            className="text-white/80 hover:text-white rounded-sm p-0.5 focus:outline-none focus:ring-1 focus:ring-white"
            title="Fechar aviso de topo"
            aria-label="Fechar aviso"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Mensagens Institucionais Vigentes */}
      {mensagensVigentes.length > 0 && (
        <div className="max-w-5xl mx-auto px-4 sm:px-6 w-full pt-2 flex flex-col gap-2">
          {mensagensVigentes.map((msg) => {
            const badge = getFinalidadeBadge(msg.finalidade);
            const Icon = badge.icon;

            return (
              <div
                key={msg.id}
                className={`border rounded-sm p-3 text-xs flex items-start justify-between gap-3 ${badge.bg} transition-all`}
              >
                <div className="flex items-start gap-2.5 flex-1">
                  <Icon size={16} className="flex-shrink-0 mt-0.5" />
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold tracking-tight">{msg.titulo}</span>
                      <span className="text-[10px] uppercase font-mono px-1 py-0.2 rounded-xs border border-current opacity-80">
                        {badge.label}
                      </span>
                    </div>
                    <p className="leading-relaxed opacity-90">{msg.conteudo}</p>
                    {msg.link_externo && (
                      <a
                        href={msg.link_externo}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-semibold underline underline-offset-2 mt-1 hover:opacity-100"
                      >
                        Mais detalhes <ExternalLink size={11} />
                      </a>
                    )}
                  </div>
                </div>

                {msg.finalidade !== "URGENTE" && (
                  <button
                    onClick={() => setDismissed((prev) => ({ ...prev, [msg.id]: true }))}
                    className="opacity-60 hover:opacity-100 rounded-sm p-0.5"
                    title="Dispensar comunicado"
                    aria-label="Dispensar comunicado"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
