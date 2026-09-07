import { TenantContext } from "@/types/global";

/** Decodifica o payload do JWT (sem verificar assinatura — apenas leitura client-side). */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
    try {
        const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
        return JSON.parse(atob(base64));
    } catch {
        return null;
    }
}

/** Extrai tenant_contexts[] do JWT. Retorna array vazio se o token não tiver contexto. */
export function extractTenantContextsFromToken(token: string): TenantContext[] {
    const payload = decodeJwtPayload(token);
    if (!payload?.tenant_contexts) return [];
    return payload.tenant_contexts as TenantContext[];
}
