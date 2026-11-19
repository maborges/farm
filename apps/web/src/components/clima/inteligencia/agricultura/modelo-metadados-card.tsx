import { BookOpen, ExternalLink } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { MetadadosModeloFitossanitario } from "@/lib/agricola/clima-api";

function getSafeHttpUrl(url?: string): string | null {
  if (!url) {
    return null;
  }
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "https:" || parsed.protocol === "http:") {
      return parsed.toString();
    }
    return null;
  } catch {
    return null;
  }
}

export function ModeloMetadadosCard({
  metadados,
}: {
  metadados?: MetadadosModeloFitossanitario;
}) {
  if (!metadados) {
    return null;
  }

  const safeUrl = getSafeHttpUrl(metadados.fonte_url);
  const hasContent = Boolean(
    metadados.agente_causal ||
      metadados.fonte_parametros ||
      safeUrl ||
      metadados.observacao
  );

  if (!hasContent) {
    return null;
  }

  return (
    <Card variant="info" size="sm" className="shadow-none">
      <CardContent className="flex items-start gap-2.5 text-xs">
        <BookOpen className="size-4 shrink-0 text-alert-info-icon mt-0.5" />
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-card-title">
              Base Técnica e Referência
            </span>
            {metadados.versao_regra && (
              <span className="rounded-sm border border-alert-info-border bg-card/70 px-1.5 py-0.5 text-[10px] font-medium text-card-title">
                v{metadados.versao_regra}
              </span>
            )}
          </div>

          {metadados.agente_causal && (
            <p className="text-card-description">
              <span className="font-medium text-card-title">Agente causal: </span>
              <em>{metadados.agente_causal}</em>
            </p>
          )}

          {metadados.fonte_parametros && (
            <p className="text-card-description">
              <span className="font-medium text-card-title">Fonte: </span>
              {safeUrl ? (
                <a
                  href={safeUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 underline underline-offset-2 text-card-title hover:opacity-80"
                >
                  {metadados.fonte_parametros}
                  <ExternalLink className="size-3 shrink-0" />
                </a>
              ) : (
                metadados.fonte_parametros
              )}
            </p>
          )}

          {!metadados.fonte_parametros && safeUrl && (
            <p>
              <a
                href={safeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 underline underline-offset-2 text-card-title hover:opacity-80"
              >
                Consultar referência técnica
                <ExternalLink className="size-3 shrink-0" />
              </a>
            </p>
          )}

          {metadados.observacao && (
            <p className="text-card-description leading-relaxed">
              {metadados.observacao}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
