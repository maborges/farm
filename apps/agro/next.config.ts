import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  typescript: {
    // Modo estrito: falhar build em erros de tipo
    ignoreBuildErrors: false,
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" }
    ],
  },
  async rewrites() {
    const isDev = process.env.NODE_ENV !== "production";
    const defaultOrigin = isDev ? "http://127.0.0.1:8000" : "http://api:8000";
    const apiOrigin =
      process.env.AGRO_API_INTERNAL_ORIGIN?.trim().replace(/\/$/, "") || defaultOrigin;
    if (!apiOrigin) return [];

    return [{ source: "/api/v1/:path*", destination: `${apiOrigin}/api/v1/:path*` }];
  },
};

export default nextConfig;
