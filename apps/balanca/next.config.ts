import type { NextConfig } from "next";

const enablePwaInDev = process.env.ENABLE_PWA_DEV === "true";

const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development" && !enablePwaInDev,
  runtimeCaching: [
    // Rotas de API nunca são servidas do cache do Service Worker — a captura
    // de peso funciona sem internet via IndexedDB local; a API só existe
    // para sincronizar quando a conexão volta.
    {
      urlPattern: /\/api\/v1\/.*/,
      handler: "NetworkOnly",
    },
    {
      urlPattern: /^https?.*/,
      handler: "NetworkFirst",
      options: {
        cacheName: "balanca-api-cache",
        networkTimeoutSeconds: 10,
        expiration: { maxEntries: 200, maxAgeSeconds: 86400 },
      },
    },
  ],
});

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: {},
};

module.exports = withPWA(nextConfig);
