import { apiFetchServer } from "@/lib/api-server";
import { ExposicaoConsolidada } from "../types";
import { ExposicaoDashboardClient } from "./ExposicaoDashboardClient";
import { cookies } from "next/headers";
import { extractTenantContextsFromToken } from "@/lib/jwt";
import { normalizePlanTier } from "@/lib/constants/planos";
import { PlanTierId } from "@/types/global";

export default async function ExposicaoPage() {
    let consolidado: ExposicaoConsolidada | null = null;
    let planTier: PlanTierId = "BASICO";

    try {
        const cookieStore = await cookies();
        const token = cookieStore.get("token")?.value;
        const tenantId = cookieStore.get("tenant_id")?.value;

        if (token && tenantId) {
            const contexts = extractTenantContextsFromToken(token);
            const context = contexts.find(c => String(c.id) === String(tenantId));
            if (context) {
                const normalizedTier = normalizePlanTier(context.plan_tier);
                if (normalizedTier) {
                    planTier = normalizedTier;
                }
            }
        }

        consolidado = await apiFetchServer<ExposicaoConsolidada>(
            "/financeiro/hedge/exposicao/consolidado"
        );
    } catch {
        // Dados carregados no client-side como fallback
    }

    return <ExposicaoDashboardClient initialConsolidado={consolidado} planTier={planTier} />;
}
