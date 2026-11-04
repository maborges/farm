#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Valida se um objeto parsed de routes-manifest.json contém o rewrite necessário para a API.
 * @param {any} manifest - Objeto JSON lido do routes-manifest.json
 * @param {string} [customOrigin] - Origem customizada opcional (ex: AGRO_API_INTERNAL_ORIGIN)
 * @returns {{ source: string; destination: string; regex?: string }} O rewrite validado
 */
export function validateRoutesManifest(manifest, customOrigin) {
  if (!manifest || typeof manifest !== "object") {
    throw new Error("Manifest inválido ou não fornecido");
  }

  const rewrites = manifest.rewrites;
  if (!rewrites) {
    throw new Error("Campo 'rewrites' ausente em routes-manifest.json");
  }

  const allRewrites = [
    ...(Array.isArray(rewrites.beforeFiles) ? rewrites.beforeFiles : []),
    ...(Array.isArray(rewrites.afterFiles) ? rewrites.afterFiles : []),
    ...(Array.isArray(rewrites.fallback) ? rewrites.fallback : []),
    ...(Array.isArray(rewrites) ? rewrites : []),
  ];

  const apiRewrite = allRewrites.find((r) => r.source === "/api/v1/:path*");
  if (!apiRewrite) {
    throw new Error("Nenhum rewrite para '/api/v1/:path*' encontrado em routes-manifest.json");
  }

  const expectedDestinationSuffix = "/api/v1/:path*";
  if (!apiRewrite.destination || !apiRewrite.destination.endsWith(expectedDestinationSuffix)) {
    throw new Error(`Rewrite '/api/v1/:path*' possui destino inválido: '${apiRewrite.destination}'`);
  }

  const expectedOrigin = customOrigin && customOrigin.trim().length > 0
    ? customOrigin.trim().replace(/\/$/, "")
    : "http://api:8000";

  if (!apiRewrite.destination.startsWith(expectedOrigin)) {
    throw new Error(
      `Destino do rewrite '${apiRewrite.destination}' não inicia com a origem esperada '${expectedOrigin}'`
    );
  }

  return apiRewrite;
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);

if (isMain) {
  const manifestPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../.next/routes-manifest.json");
  if (!fs.existsSync(manifestPath)) {
    console.error(`[-] ERRO: routes-manifest.json não encontrado em ${manifestPath}`);
    process.exit(1);
  }
  try {
    const raw = fs.readFileSync(manifestPath, "utf-8");
    const manifest = JSON.parse(raw);
    const validated = validateRoutesManifest(manifest, process.env.AGRO_API_INTERNAL_ORIGIN);
    console.log(`[OK] routes-manifest.json validado com sucesso: rewrite '${validated.source}' -> '${validated.destination}'`);
    process.exit(0);
  } catch (err) {
    console.error(`[-] ERRO CRÍTICO: ${err.message}`);
    process.exit(1);
  }
}
