import { describe, it, expect, beforeEach, afterEach } from "vitest";
import nextConfig from "../../next.config";

describe("apps/agro next.config rewrites", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("produces rewrite to http://api:8000 in production when AGRO_API_INTERNAL_ORIGIN is unset", async () => {
    process.env = { ...originalEnv, NODE_ENV: "production" };
    delete process.env.AGRO_API_INTERNAL_ORIGIN;
    const rewritesFn = nextConfig.rewrites;
    expect(rewritesFn).toBeDefined();
    if (!rewritesFn) return;
    const rewrites = await rewritesFn();
    expect(rewrites).toEqual([
      { source: "/api/v1/:path*", destination: "http://api:8000/api/v1/:path*" },
    ]);
  });

  it("produces rewrite to http://127.0.0.1:8000 in development when AGRO_API_INTERNAL_ORIGIN is unset", async () => {
    process.env = { ...originalEnv, NODE_ENV: "development" };
    delete process.env.AGRO_API_INTERNAL_ORIGIN;
    const rewritesFn = nextConfig.rewrites;
    expect(rewritesFn).toBeDefined();
    if (!rewritesFn) return;
    const rewrites = await rewritesFn();
    expect(rewrites).toEqual([
      { source: "/api/v1/:path*", destination: "http://127.0.0.1:8000/api/v1/:path*" },
    ]);
  });

  it("honors custom AGRO_API_INTERNAL_ORIGIN in production", async () => {
    process.env = {
      ...originalEnv,
      NODE_ENV: "production",
      AGRO_API_INTERNAL_ORIGIN: "http://staging-api:8000/",
    };
    const rewritesFn = nextConfig.rewrites;
    expect(rewritesFn).toBeDefined();
    if (!rewritesFn) return;
    const rewrites = await rewritesFn();
    expect(rewrites).toEqual([
      { source: "/api/v1/:path*", destination: "http://staging-api:8000/api/v1/:path*" },
    ]);
  });
});
