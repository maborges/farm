"use client";

import * as React from "react";
import { Info } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function AvisoAgronomicoCard(): React.ReactElement {
  return (
    <Alert variant="info" id="card-aviso-agronomico">
      <Info className="size-4" />
      <AlertTitle className="text-xs">
        Diretrizes Agrometeorológicas e Responsabilidade Técnica
      </AlertTitle>
      <AlertDescription className="text-xs flex flex-col gap-1.5">
        <p>
          Os dados meteorológicos são estimativas probabilísticas para fins informativos e apoio ao planejamento. Podem não representar com precisão a localização ou o horário da sua propriedade, pois as condições locais variam conforme relevo, altitude e microclima.
        </p>
        <p className="text-[11px] opacity-90">
          <strong>Aviso:</strong> Previsões são informativas e probabilísticas, podem conter imprecisões de localização e horário e não devem ser a única base para decisões críticas de segurança, emergência ou operação. Em situações críticas, consulte os serviços meteorológicos oficiais e um responsável técnico habilitado. Para pulverização ou colheita, observe também a bula e o receituário.
        </p>
      </AlertDescription>
    </Alert>
  );
}
