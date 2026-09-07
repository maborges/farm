"use client";

import { ModuleGate } from "@/components/shared/module-gate";
import { ShieldAlert } from "lucide-react";

export default function AgricolaLayout({ children }: { children: React.ReactNode }) {
    return (
        <ModuleGate moduleId="A1_PLANEJAMENTO" fallback={
            <div className="flex flex-col items-center justify-center p-24 text-center w-full h-full">
                <ShieldAlert className="h-12 w-12 text-neutral-400 mb-4" />
                <h2 className="text-xl font-bold">Módulo Bloqueado</h2>
                <p className="text-neutral-500">Você não possui licença para o Módulo de Agricultura.</p>
            </div>
        }>
            <div className="flex-1 flex flex-col w-full">
                {children}
            </div>
        </ModuleGate>
    );
}
