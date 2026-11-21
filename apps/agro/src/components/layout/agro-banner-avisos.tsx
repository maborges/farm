"use client";

import React, { useState } from "react";
import { AlertTriangle, AlertCircle, Info, X, ExternalLink } from "lucide-react";
import { Alert, AlertDescription, AlertTitle, type AlertVariant } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAgroConfig, AgroMensagemFinalidade } from "@/lib/config/agro-config";

function getFinalidadeMeta(finalidade: AgroMensagemFinalidade): {
  alertVariant: AlertVariant;
  badgeVariant: "danger" | "warning" | "attention" | "success" | "info";
  icon: React.ComponentType<{ className?: string }>;
  label: string;
} {
  switch (finalidade) {
    case "URGENTE":
      return {
        alertVariant: "destructive",
        badgeVariant: "danger",
        icon: AlertCircle,
        label: "Urgente",
      };
    case "REGULATORIO":
      return {
        alertVariant: "warning",
        badgeVariant: "warning",
        icon: AlertTriangle,
        label: "Regulatório",
      };
    case "MANUTENCAO":
      return {
        alertVariant: "warning",
        badgeVariant: "attention",
        icon: AlertTriangle,
        label: "Manutenção",
      };
    case "NOVIDADE":
      return {
        alertVariant: "success",
        badgeVariant: "success",
        icon: Info,
        label: "Novidade",
      };
    default:
      return {
        alertVariant: "info",
        badgeVariant: "info",
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
            <AlertCircle className="size-4 shrink-0 text-white" />
            <span>{bannerUrgente}</span>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            onClick={() => setDismissed((prev) => ({ ...prev, "global-banner": true }))}
            className="text-white/80 hover:text-white hover:bg-white/10"
            title="Fechar aviso de topo"
            aria-label="Fechar aviso"
          >
            <X className="size-3.5" />
          </Button>
        </div>
      )}

      {/* Mensagens Institucionais Vigentes */}
      {mensagensVigentes.length > 0 && (
        <div className="max-w-5xl mx-auto px-4 sm:px-6 w-full pt-2 flex flex-col gap-2">
          {mensagensVigentes.map((msg) => {
            const meta = getFinalidadeMeta(msg.finalidade);
            const Icon = meta.icon;

            return (
              <Alert key={msg.id} variant={meta.alertVariant} className="pr-10">
                <Icon className="size-4" />
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-2">
                    <AlertTitle className="mb-0 text-xs">{msg.titulo}</AlertTitle>
                    <Badge variant={meta.badgeVariant} className="text-[10px]">
                      {meta.label}
                    </Badge>
                  </div>
                  <AlertDescription className="text-xs">
                    <p>{msg.conteudo}</p>
                    {msg.link_externo && (
                      <a
                        href={msg.link_externo}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-semibold underline underline-offset-2 mt-1"
                      >
                        Mais detalhes <ExternalLink className="size-3" />
                      </a>
                    )}
                  </AlertDescription>
                </div>

                {msg.finalidade !== "URGENTE" && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => setDismissed((prev) => ({ ...prev, [msg.id]: true }))}
                    className="absolute right-2 top-2"
                    title="Dispensar comunicado"
                    aria-label="Dispensar comunicado"
                  >
                    <X className="size-3.5" />
                  </Button>
                )}
              </Alert>
            );
          })}
        </div>
      )}
    </div>
  );
}
