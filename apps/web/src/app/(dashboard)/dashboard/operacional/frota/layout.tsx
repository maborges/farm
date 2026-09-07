"use client";

import { ShieldAlert } from "lucide-react";

import { ModuleGate } from "@/components/shared/module-gate";

export default function FrotaLayout({ children }: { children: React.ReactNode }) {
  return (
    <ModuleGate
      moduleId="O1_FROTA"
      fallback={
        <div className="flex h-full w-full flex-col items-center justify-center p-24 text-center">
          <ShieldAlert className="mb-4 h-12 w-12 text-neutral-400" />
          <h2 className="text-xl font-bold">Módulo Bloqueado</h2>
          <p className="text-neutral-500">Você não possui licença para o módulo de Frota.</p>
        </div>
      }
    >
      <div className="flex w-full flex-1 flex-col">{children}</div>
    </ModuleGate>
  );
}
