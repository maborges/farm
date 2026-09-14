import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getApiOriginFromEnv() {
    const raw = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    if (raw.endsWith("/api/v1")) {
        return raw.replace(/\/api\/v1$/, "");
    }
    return raw;
}

function getBackendOrigins() {
    const configured = getApiOriginFromEnv();
    const fallbacks = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://host.docker.internal:8000",
    ];

    return Array.from(new Set([configured, ...fallbacks].map((origin) => origin.replace(/\/$/, ""))));
}

function buildTargetUrl(request: NextRequest, path: string[], backendOrigin: string) {
    const joinedPath = path.join("/");
    const hasTrailingSlash = request.nextUrl.pathname.endsWith("/");
    const shouldForceCollectionSlash =
        request.method === "POST" &&
        path.length === 1 &&
        !hasTrailingSlash;
    const normalizedPath = (hasTrailingSlash || shouldForceCollectionSlash)
        ? `${joinedPath}/`
        : joinedPath;
    const target = new URL(`${backendOrigin}/api/v1/${normalizedPath}`);
    target.search = request.nextUrl.search;
    return target;
}

async function forwardRequest(
    targetUrl: URL,
    headers: Headers,
    method: string,
    body?: ArrayBuffer,
) {
    return fetch(targetUrl, {
        method,
        headers,
        body: body && body.byteLength > 0 ? body : undefined,
        redirect: "follow",
    });
}

async function proxy(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    const { path } = await ctx.params;
    const method = request.method;
    const body =
        method === "GET" || method === "HEAD"
            ? undefined
            : await request.arrayBuffer();

    const headers = new Headers(request.headers);
    const pathString = `/${path.join("/")}`;
    const tokenFromForwardedHeader = headers.get("x-access-token");
    const tokenFromCookie = request.cookies.get("token")?.value;
    const tenantIdFromCookie = request.cookies.get("tenant_id")?.value;
    const fazendaIdFromCookie = request.cookies.get("unidade_produtiva_id")?.value;
    const isGrupoScope = headers.get("x-context-scope") === "grupo";
    const shouldPreferCookieContext =
        pathString !== "/auth/login" &&
        pathString !== "/auth/switch-tenant";

    // O cliente pode ter acabado de trocar de tenant. Nesse caso, o token
    // explícito da requisição é a fonte de verdade; o cookie fica apenas como
    // fallback para chamadas que não carregam Authorization.
    if (tokenFromForwardedHeader) {
        headers.set("authorization", `Bearer ${tokenFromForwardedHeader}`);
    } else if (!headers.get("authorization") && tokenFromCookie) {
        headers.set("authorization", `Bearer ${tokenFromCookie}`);
    }

    if (!headers.get("x-tenant-id") && shouldPreferCookieContext && tenantIdFromCookie) {
        headers.set("x-tenant-id", tenantIdFromCookie);
    } else if (!headers.get("x-tenant-id") && tenantIdFromCookie) {
        headers.set("x-tenant-id", tenantIdFromCookie);
    }

    if (isGrupoScope) {
        headers.delete("x-fazenda-id");
    } else if (!headers.get("x-fazenda-id") && shouldPreferCookieContext && fazendaIdFromCookie) {
        headers.set("x-fazenda-id", fazendaIdFromCookie);
    } else if (!headers.get("x-fazenda-id") && fazendaIdFromCookie) {
        headers.set("x-fazenda-id", fazendaIdFromCookie);
    }

    headers.delete("x-access-token");
    headers.delete("x-context-scope");
    headers.delete("host");
    headers.delete("connection");
    headers.delete("content-length");
    headers.delete("transfer-encoding");
    headers.delete("accept-encoding");
    // O FastAPI recebe HTTP na rede interna. Repassar o protocolo externo
    // (https) faz o middleware de HTTPS redirecionar o fetch para TLS na
    // porta HTTP interna, resultando em "fetch failed" atrás do Nginx.
    headers.delete("forwarded");
    headers.delete("x-forwarded-host");
    headers.delete("x-forwarded-port");
    headers.delete("x-forwarded-proto");

    let response: Response | null = null;
    let lastError: unknown = null;
    let usedTargetUrl: URL | null = null;

    for (const backendOrigin of getBackendOrigins()) {
        const targetUrl = buildTargetUrl(request, path, backendOrigin);
        try {
            response = await forwardRequest(targetUrl, headers, method, body);
            usedTargetUrl = targetUrl;
            break;
        } catch (error) {
            lastError = error;
        }
    }

    if (!response) {
        const message = lastError instanceof Error ? lastError.message : "Proxy fetch failed";
        return NextResponse.json(
            {
                message,
                targetUrl: usedTargetUrl?.toString() ?? null,
                method,
                path: pathString,
                source: "next-proxy-fetch",
            },
            { status: 500 },
        );
    }

    const cookieAuthValue = tokenFromCookie ? `Bearer ${tokenFromCookie}` : null;
    const forwardedAuthValue = tokenFromForwardedHeader
        ? `Bearer ${tokenFromForwardedHeader}`
        : (request.headers.get("authorization") ?? null);
    const canRetryWithAlternateToken =
        shouldPreferCookieContext &&
        response.status === 401 &&
        cookieAuthValue &&
        forwardedAuthValue &&
        cookieAuthValue !== forwardedAuthValue;

    if (canRetryWithAlternateToken) {
        const retryHeaders = new Headers(headers);
        retryHeaders.set("authorization", forwardedAuthValue);
        try {
            response = await forwardRequest(usedTargetUrl!, retryHeaders, method, body);
        } catch (error) {
            const message = error instanceof Error ? error.message : "Proxy retry failed";
            return NextResponse.json(
                {
                    message,
                    targetUrl: usedTargetUrl?.toString() ?? null,
                    method,
                    path: pathString,
                    source: "next-proxy-retry",
                },
                { status: 500 },
            );
        }
    }

    if (!response.ok && pathString.startsWith("/operacoes")) {
        const errorText = await response.text();
        return new NextResponse(
            errorText || JSON.stringify({
                message: "Empty error response from backend",
                targetUrl: usedTargetUrl?.toString() ?? null,
                method,
                path: pathString,
                status: response.status,
                source: "backend-empty-response",
            }),
            {
                status: response.status,
                statusText: response.statusText,
                headers: {
                    "content-type": response.headers.get("content-type") || "application/json",
                },
            },
        );
    }

    return new NextResponse(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
    });
}

export async function GET(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    return proxy(request, ctx);
}

export async function POST(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    return proxy(request, ctx);
}

export async function PUT(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    return proxy(request, ctx);
}

export async function PATCH(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    return proxy(request, ctx);
}

export async function DELETE(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    return proxy(request, ctx);
}

export async function OPTIONS(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    return proxy(request, ctx);
}
