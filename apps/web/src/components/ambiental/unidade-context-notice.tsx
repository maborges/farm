"use client";

import { AlertCircle, Info } from "lucide-react";
import { usePathname } from "next/navigation";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAppStore } from "@/lib/stores/app-store";

export function UnidadeContextNotice() {
  const pathname = usePathname();
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const unidades = useAppStore((state) => state.unidadesProdutivasAutorizadas);
  const unidade = unidades.find((item) => item.id === activeFazendaId);
  const isVisaoConsolidada = pathname === "/dashboard/ambiental"
    || pathname.includes("/ambiental/car/lista")
    || pathname.includes("/ambiental/car/areas")
    || pathname.includes("/ambiental/outorgas")
    || pathname.includes("/ambiental/monitoramento/")
    || pathname.includes("/ambiental/carbono");

  if (isVisaoConsolidada) {
    return (
      <div className="mx-6 mt-4">
        <Alert variant="info" role="status">
          <Info aria-hidden="true" />
          <AlertDescription>
            <strong>Visão consolidada:</strong> esta tela apresenta informações de todas as unidades produtivas autorizadas. Para registrar um novo item, selecione a unidade de destino no topbar.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!activeFazendaId) {
    return (
      <div className="mx-6 mt-4">
        <Alert variant="warning" role="status">
          <AlertCircle aria-hidden="true" />
          <AlertDescription>
            Selecione uma unidade produtiva no topbar para visualizar ou cadastrar dados ambientais.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="mx-6 mt-4">
      <Alert variant="info" role="status">
        <Info aria-hidden="true" />
        <AlertDescription>
          Unidade selecionada: <strong>{unidade?.nome ?? "Unidade produtiva"}</strong>. Os dados exibidos e os novos registros pertencem exclusivamente a esta unidade produtiva.
        </AlertDescription>
      </Alert>
    </div>
  );
}
