/**
 * Hooks para verificar o tier do plano do tenant.
 * Espelha require_tier() do backend (dependencies.py).
 *
 * Uso combinado com useHasModule():
 *   const pode = useHasModule(Modulos.AGRICOLA_PLANEJAMENTO) && useHasTier("PROFISSIONAL");
 */

import { useAppStore } from "@/lib/stores/app-store";
import type { PlanTierId } from "@/types/global";

/**
 * Retorna o tier atual do plano do tenant (ex: "BASICO", "PROFISSIONAL", "ENTERPRISE").
 */
export function usePlanTier(): PlanTierId | null {
  return useAppStore((s) => s.activePlanTier());
}

/**
 * Política All-In por tamanho de propriedade (Hectares Equivalentes):
 * todos os pacotes liberam 100% das funcionalidades dos módulos contratados.
 * Mantido como hook para compatibilidade com componentes existentes.
 */
export function useHasTier(_minimum: PlanTierId): boolean {
  return true;
}

/**
 * Retorna o limite de fazendas do grupo ativo. -1 = ilimitado.
 */
export function useMaxFazendas(): number {
  return useAppStore((s) => {
    const grupo = s.grupos.find(g => g.id === s.activeGrupoId) ?? s.grupos[0];
    return grupo?.max_fazendas ?? 1;
  });
}

/**
 * Retorna o limite de usuários do grupo ativo. -1 = ilimitado.
 */
export function useMaxUsuarios(): number {
  return useAppStore((s) => {
    const grupo = s.grupos.find(g => g.id === s.activeGrupoId) ?? s.grupos[0];
    return grupo?.max_usuarios ?? 2;
  });
}
