"use client";

import * as React from "react";
import { Info } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export function AvisoAgronomicoCard(): React.ReactElement {
  return (
    <Card className="rounded-sm border-blue-500/25 bg-blue-500/5 text-xs text-blue-950 dark:text-blue-100" id="card-aviso-agronomico">
      <CardContent className="p-3.5 space-y-1.5">
        <div className="flex items-center gap-2 font-semibold text-xs text-blue-900 dark:text-blue-200">
          <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
          <span>Diretrizes Agrometeorológicas e Responsabilidade Técnica</span>
        </div>
        <p className="text-[11px] text-muted-foreground dark:text-blue-300/80 leading-relaxed">
          Os dados meteorológicos são estimativas probabilísticas para fins informativos e apoio ao planejamento. Podem não representar com precisão a localização ou o horário da sua propriedade, pois as condições locais variam conforme relevo, altitude e microclima.
        </p>
        <p className="text-[10px] text-muted-foreground/90 dark:text-blue-300/70">
          <strong>Aviso:</strong> Previsões são informativas e probabilísticas, podem conter imprecisões de localização e horário e não devem ser a única base para decisões críticas de segurança, emergência ou operação. Em situações críticas, consulte os serviços meteorológicos oficiais e um responsável técnico habilitado. Para pulverização ou colheita, observe também a bula e o receituário.
        </p>
      </CardContent>
    </Card>
  );
}
