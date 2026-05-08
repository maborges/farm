import type { NextConfig } from "next";

const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
  runtimeCaching: [
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

const nextConfig: NextConfig = {
  reactStrictMode: true,
};

module.exports = withPWA(nextConfig);
