"use server";

import { cookies, headers } from "next/headers";

async function buildCookieOptions() {
    const headerStore = await headers();
    const forwardedProto = headerStore.get("x-forwarded-proto");
    const isHttps = forwardedProto === "https";

    return {
        httpOnly: true,
        secure: isHttps,
        sameSite: "lax" as const,
        maxAge: 60 * 60 * 24 * 7,
        path: "/",
    };
}

/**
 * Server Action para salvar o token de autenticação em cookies
 * Necessário para que Server Components (RSC) possam acessar o token
 */
export async function setAuthCookies(token: string, tenantId?: string, fazendaId?: string) {
    const cookieStore = await cookies();
    const cookieOptions = await buildCookieOptions();

    // Token JWT - httpOnly para segurança
    cookieStore.set("token", token, cookieOptions);

    // Tenant ID - necessário para RSC
    if (tenantId) {
        cookieStore.set("tenant_id", tenantId, cookieOptions);
    }

    // Fazenda ID - necessário para RSC
    if (fazendaId) {
        cookieStore.set("unidade_produtiva_id", fazendaId, cookieOptions);
    }
}

export async function setContextCookies(tenantId?: string, fazendaId?: string | null) {
    const cookieStore = await cookies();
    const cookieOptions = await buildCookieOptions();

    if (tenantId) {
        cookieStore.set("tenant_id", tenantId, cookieOptions);
    } else {
        cookieStore.delete("tenant_id");
    }

    if (fazendaId) {
        cookieStore.set("unidade_produtiva_id", fazendaId, cookieOptions);
    } else {
        cookieStore.delete("unidade_produtiva_id");
    }
}

/**
 * Server Action para remover cookies de autenticação
 */
export async function clearAuthCookies() {
    const cookieStore = await cookies();
    cookieStore.delete("token");
    cookieStore.delete("tenant_id");
    cookieStore.delete("unidade_produtiva_id");
}
