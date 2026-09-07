/**
 * Hooks para verificar o tier do plano do tenant.
 * Espelha require_tier() do backend (dependencies.py).
 *
 * Uso combinado com useHasModule():
 *   const pode = useHasModule(Modulos.AGRICOLA_PLANEJAMENTO) && useHasTier("PROFISSIONAL");
 */

import { useAppStore } from "@/lib/stores/app-store";
import { tierAtLeast } from "@/lib/constants/planos";
import type { PlanTierId } from "@/types/global";

/**
 * Retorna o tier atual do plano do tenant (ex: "BASICO", "PROFISSIONAL", "ENTERPRISE").
 */
export function usePlanTier(): PlanTierId | null {
  return useAppStore((s) => s.activePlanTier());
}

/**
 * Retorna true se o grupo ativo tem o tier mínimo exigido.
 *
 * @example
 * const podeRateio = useHasTier("PROFISSIONAL");
 * if (!podeRateio) return <UpgradePrompt tier="PROFISSIONAL" />;
 */
export function useHasTier(minimum: PlanTierId): boolean {
  const planTier = useAppStore((s) => s.activePlanTier());
  return tierAtLeast(planTier, minimum);
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
