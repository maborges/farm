import type { NextConfig } from "next";
import path from "node:path";

process.env.WATCHPACK_POLLING = process.env.WATCHPACK_POLLING || "1000";

const nextConfig: NextConfig = {
  skipTrailingSlashRedirect: true,
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "127.0.0.1" },
      { protocol: "http", hostname: "localhost" },
      { protocol: "https", hostname: "**" }
    ],
  },
  turbopack: {
    root: path.resolve(__dirname),
  },
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        ...config.watchOptions,
        poll: 1000,
        aggregateTimeout: 300,
        ignored: /[\\/](node_modules|\.git|\.next|\.venv)[\\/]/,
      };
    }
    return config;
  },
};

export default nextConfig;
