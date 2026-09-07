import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getBackendOrigins() {
    const configured = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    const fallbacks = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://host.docker.internal:8000",
    ];

    return Array.from(new Set([configured, ...fallbacks].map((origin) => origin.replace(/\/$/, ""))));
}

async function proxy(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    const { path } = await ctx.params;
    const targetPath = `/static/${path.join("/")}`;
    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("connection");
    headers.delete("content-length");
    headers.delete("transfer-encoding");
    headers.delete("accept-encoding");

    let response: Response | null = null;
    let lastError: unknown = null;

    for (const backendOrigin of getBackendOrigins()) {
        try {
            response = await fetch(`${backendOrigin}${targetPath}`, {
                method: request.method,
                headers,
                redirect: "follow",
            });
            break;
        } catch (error) {
            lastError = error;
        }
    }

    if (!response) {
        const message = lastError instanceof Error ? lastError.message : "Static asset fetch failed";
        return NextResponse.json({ message, path: targetPath }, { status: 500 });
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

export async function HEAD(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    return proxy(request, ctx);
}
