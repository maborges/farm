"use client";

import { Info } from "lucide-react";
import { usePathname } from "next/navigation";
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
      <div
        role="status"
        className="mx-6 mt-4 flex items-start gap-2 rounded-sm border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-sm text-violet-800 dark:text-violet-200"
      >
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <span><strong>Visão consolidada:</strong> esta tela apresenta informações de todas as unidades produtivas autorizadas. Para registrar um novo item, selecione a unidade de destino no topbar.</span>
      </div>
    );
  }

  if (!activeFazendaId) {
    return (
      <div
        role="status"
        className="mx-6 mt-4 flex items-start gap-2 rounded-sm border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200"
      >
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <span>Selecione uma unidade produtiva no topbar para visualizar ou cadastrar dados ambientais.</span>
      </div>
    );
  }

  return (
    <div
      role="status"
      className="mx-6 mt-4 flex items-start gap-2 rounded-sm border border-blue-500/20 bg-blue-500/10 px-3 py-2 text-sm text-blue-800 dark:text-blue-200"
    >
      <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <span>
        Unidade selecionada: <strong>{unidade?.nome ?? "Unidade produtiva"}</strong>. Os dados exibidos e os novos registros pertencem exclusivamente a esta unidade produtiva.
      </span>
    </div>
  );
}
