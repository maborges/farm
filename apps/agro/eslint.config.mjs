import js from "@eslint/js";
import nextPlugin from "eslint-config-next";
import globals from "globals";

const nextConfig = Array.isArray(nextPlugin) ? nextPlugin : [nextPlugin];

const config = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "public/sw.js",
    ],
  },
  js.configs.recommended,
  ...nextConfig,
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      "no-console": "off",
      "no-unused-vars": ["warn", { "argsIgnorePattern": "^_", "varsIgnorePattern": "^_" }],
    },
  },
];

export default config;
