import js from "@eslint/js";
import nextPlugin from "eslint-config-next";
import globals from "globals";

const nextConfig = Array.isArray(nextPlugin) ? nextPlugin : [nextPlugin];

const config = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "docs/**",
      "services/**",
      "tests/**",
      "scripts/**",
      "database.db",
      "agrosaas.db_old",
      "tsconfig.tsbuildinfo",
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
      "no-unused-vars": "off",
      "no-undef": "off",
    },
  },
];

export default config;
