import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const appRoot = resolve(import.meta.dirname, "../..");
const layoutSource = readFileSync(resolve(appRoot, "src/app/layout.tsx"), "utf8");
const accountSource = readFileSync(resolve(appRoot, "src/components/auth/painel-conta.tsx"), "utf8");

describe("montagem do heartbeat de sessão", () => {
  it("não monta heartbeat no layout usado pelas páginas públicas", () => {
    expect(layoutSource).not.toMatch(/SessionHeartbeat/);
  });

  it("monta heartbeat somente no ramo que já confirmou usuário autenticado", () => {
    expect(accountSource).toMatch(/import\s+\{\s*SessionHeartbeat\s*\}\s+from\s+["']@\/components\/auth\/session-heartbeat["']/);
    expect(accountSource).toMatch(/if\s*\(user\)\s*\{\s*return\s*\(\s*<div[^>]*>\s*<SessionHeartbeat\s*\/>/);
  });
});
