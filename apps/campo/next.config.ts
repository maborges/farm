import type { NextConfig } from "next";

const enablePwaInDev = process.env.ENABLE_PWA_DEV === "true";

const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development" && !enablePwaInDev,
  runtimeCaching: [
    // Regra específica avaliada antes da genérica abaixo: rotas de API
    // (same-origin, via proxy Next em src/app/api/v1/[...path]/route.ts) nunca
    // devem ser servidas do cache do Service Worker — respostas carregam
    // dados de negócio autenticados (tarefas, safras, talhões, etc.) que não
    // podem sobreviver a uma troca de sessão/tenant no mesmo dispositivo.
    {
      urlPattern: /\/api\/v1\/.*/,
      handler: "NetworkOnly",
    },
    // Fallback para os demais recursos (assets estáticos, fontes, ícones).
    {
      urlPattern: /^https?.*/,
      handler: "NetworkFirst",
      options: {
        cacheName: "campo-api-cache",
        networkTimeoutSeconds: 10,
        expiration: { maxEntries: 200, maxAgeSeconds: 86400 },
      },
    },
  ],
});

function getBackendOrigin() {
  const raw = (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");

  if (raw.endsWith("/api/v1")) return raw.replace(/\/api\/v1$/, "");
  return raw.startsWith("http://") || raw.startsWith("https://")
    ? raw
    : "http://127.0.0.1:8000";
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: {},
  // As URLs de avatar/logo são retornadas pelo backend como /static/...
  // e precisam funcionar também quando o PWA está servido em outra porta.
  async rewrites() {
    return [
      {
        source: "/static/:path*",
        destination: `${getBackendOrigin()}/static/:path*`,
      },
    ];
  },
};

module.exports = withPWA(nextConfig);
