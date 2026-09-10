import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - api (API routes)
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico, sitemap.xml, robots.txt (metadata files)
         */
        "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
    ],
};

function isLocalHost(hostname: string) {
    const hostWithoutPort = hostname.split(":")[0];
    const isIpv4 = /^(?:\d{1,3}\.){3}\d{1,3}$/.test(hostWithoutPort);

    return (
        hostname.includes("localhost") ||
        hostname.startsWith("127.0.0.1") ||
        hostname.startsWith("[::1]") ||
        hostname.startsWith("::1") ||
        hostname.includes("trycloudflare.com") ||
        isIpv4
    );
}

export async function proxy(req: NextRequest) {
    const url = req.nextUrl;
    const hostname = req.headers.get("host") || "";

    // Permitir chamadas internas de API ou assets Next.js sem bloquear
    if (url.pathname.startsWith("/_next") || url.pathname.startsWith("/api")) {
        return NextResponse.next();
    }

    // Hosts locais e domínios oficiais da plataforma seguem o fluxo padrão.
    const isOfficialDomain =
        hostname === "deepfarms.com.br" ||
        hostname.endsWith(".deepfarms.com.br") ||
        hostname === "agrosaas.com" ||
        hostname.endsWith(".agrosaas.com");

    const isCustomDomain = !isLocalHost(hostname) && !isOfficialDomain;

    if (isCustomDomain) {
        return NextResponse.rewrite(new URL(`/domain/${hostname}${url.pathname}`, req.url));
    }

    if (url.pathname.startsWith("/c/")) {
        const slug = url.pathname.split("/")[2];
        const requestHeaders = new Headers(req.headers);
        requestHeaders.set("x-tenant-slug", slug || "");

        return NextResponse.next({
            request: {
                headers: requestHeaders,
            },
        });
    }

    return NextResponse.next();
}
