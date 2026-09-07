/**
 * Hooks para verificar se o tenant/grupo ativo tem um módulo contratado.
 * Lê de useAppStore().activeModules() — derivado do grupo ativo.
 */

import { useAppStore } from "@/lib/stores/app-store";
import { useShallow } from "zustand/react/shallow";
import { ModuleId } from "@/types/global";
import { normalizeModuleId } from "@/lib/constants/modulos";

/** Verifica se o grupo ativo tem um módulo específico contratado. */
export function useHasModule(moduleId: ModuleId | string): boolean {
  const requestedModuleId = normalizeModuleId(moduleId);
  return useAppStore((s) =>
    s.activeModules().some(
      (activeModuleId) => normalizeModuleId(activeModuleId) === requestedModuleId
    )
  );
}

/** Verifica se o grupo ativo tem QUALQUER UM dos módulos listados. */
export function useHasAnyModule(...moduleIds: (ModuleId | string)[]): boolean {
  return useAppStore((s) => {
    const active = s.activeModules();
    return moduleIds.some((id) => active.includes(id as ModuleId));
  });
}

/** Verifica se o grupo ativo tem TODOS os módulos listados. */
export function useHasAllModules(...moduleIds: (ModuleId | string)[]): boolean {
  return useAppStore((s) => {
    const active = s.activeModules();
    return moduleIds.every((id) => active.includes(id as ModuleId));
  });
}

/** Retorna a lista completa de módulos do grupo ativo. */
export function useModules(): ModuleId[] {
  return useAppStore(useShallow((s) => s.activeModules()));
}

/** Verifica se o grupo ativo tem algum módulo além do CORE. */
export function useHasAnyPaidModule(): boolean {
  return useAppStore((s) => s.activeModules().some((m) => m !== "CORE"));
}
