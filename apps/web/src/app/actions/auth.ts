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
    cookieStore.delete("backoffice_return_token");
    cookieStore.delete("backoffice_return_path");
}

/**
 * Server Action para iniciar sessão de impersonação
 * Preserva o token de backoffice e define o token de impersonação no cliente.
 */
export async function startImpersonationCookies(
    impersonationToken: string,
    tenantId: string,
    fazendaId?: string,
    returnPath?: string
) {
    const cookieStore = await cookies();
    const cookieOptions = await buildCookieOptions();

    // Salva token atual do Backoffice se ainda não houver salvo
    const currentToken = cookieStore.get("token")?.value;
    if (currentToken && !cookieStore.get("backoffice_return_token")?.value) {
        cookieStore.set("backoffice_return_token", currentToken, cookieOptions);
    }

    if (returnPath) {
        cookieStore.set("backoffice_return_path", returnPath, cookieOptions);
    }

    // Aplica o token do tenant e contexto
    cookieStore.set("token", impersonationToken, cookieOptions);
    if (tenantId) {
        cookieStore.set("tenant_id", tenantId, cookieOptions);
    }
    if (fazendaId) {
        cookieStore.set("unidade_produtiva_id", fazendaId, cookieOptions);
    }
}

/**
 * Server Action para atualizar o token de impersonação (ex: ao trocar modo READ_ONLY / READ_WRITE)
 */
export async function updateImpersonationTokenCookie(newToken: string) {
    const cookieStore = await cookies();
    const cookieOptions = await buildCookieOptions();
    cookieStore.set("token", newToken, cookieOptions);
}

/**
 * Server Action para restaurar a sessão do Backoffice e limpar tokens temporários.
 */
export async function stopImpersonationCookies(): Promise<{ returnPath: string; returnToken?: string }> {
    const cookieStore = await cookies();
    const cookieOptions = await buildCookieOptions();

    const returnToken = cookieStore.get("backoffice_return_token")?.value;
    const returnPath = cookieStore.get("backoffice_return_path")?.value || "/dashboard/backoffice/dashboard";

    if (returnToken) {
        cookieStore.set("token", returnToken, cookieOptions);
    }

    cookieStore.delete("backoffice_return_token");
    cookieStore.delete("backoffice_return_path");
    cookieStore.delete("tenant_id");
    cookieStore.delete("unidade_produtiva_id");

    return { returnPath, returnToken };
}

/**
 * Retorna se o usuário está em sessão ativa de impersonação via cookies
 */
export async function getImpersonationStatus(): Promise<{ isImpersonating: boolean; returnPath: string | null }> {
    const cookieStore = await cookies();
    const returnToken = cookieStore.get("backoffice_return_token")?.value;
    const returnPath = cookieStore.get("backoffice_return_path")?.value || null;

    return {
        isImpersonating: Boolean(returnToken),
        returnPath,
    };
}
