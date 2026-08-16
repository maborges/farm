import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const backendUrl = getBackendOrigin();

function getBackendOrigin() {
  const raw = (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");
  const value = raw.startsWith("http://") || raw.startsWith("https://") ? raw : "http://127.0.0.1:8000";

  if (value.endsWith("/api/v1")) {
    return value.replace(/\/api\/v1$/, "");
  }

  return value;
}

function buildTargetUrl(request: NextRequest, path: string[]) {
  const joinedPath = path.join("/");
  const target = new URL(`${backendUrl}/api/v1/${joinedPath}`);
  target.search = request.nextUrl.search;
  return target;
}

function withNoStoreHeaders(headers: Headers) {
  const nextHeaders = new Headers(headers);
  nextHeaders.set("cache-control", "no-store, no-cache, must-revalidate, proxy-revalidate");
  nextHeaders.set("pragma", "no-cache");
  nextHeaders.set("expires", "0");
  nextHeaders.delete("etag");
  return nextHeaders;
}

async function proxy(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const targetUrl = buildTargetUrl(request, path);
  const method = request.method;
  const body = method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();
  const headers = new Headers(request.headers);

  headers.set("host", new URL(backendUrl).host);

  try {
    const response = await fetch(targetUrl, {
      method,
      headers,
      body: body && body.byteLength > 0 ? body : undefined,
      cache: "no-store",
      redirect: "follow",
    });

    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: withNoStoreHeaders(response.headers),
    });
  } catch {
    return NextResponse.json(
      {
        detail: "Não foi possível contatar o backend. Verifique a conexão da estação.",
        source: "balanca-next-proxy",
      },
      { status: 502 },
    );
  }
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
