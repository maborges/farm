import { describe, it, expect } from "vitest";
import { validateRoutesManifest } from "../../scripts/verify-routes-manifest.mjs";

describe("validateRoutesManifest", () => {
  it("aceita manifest com rewrite padrão para http://api:8000", () => {
    const manifest = {
      rewrites: {
        beforeFiles: [],
        afterFiles: [
          {
            source: "/api/v1/:path*",
            destination: "http://api:8000/api/v1/:path*",
          },
        ],
        fallback: [],
      },
    };

    const result = validateRoutesManifest(manifest);
    expect(result.source).toBe("/api/v1/:path*");
    expect(result.destination).toBe("http://api:8000/api/v1/:path*");
  });

  it("aceita manifest com origem customizada quando especificada", () => {
    const manifest = {
      rewrites: {
        afterFiles: [
          {
            source: "/api/v1/:path*",
            destination: "http://staging-api:8000/api/v1/:path*",
          },
        ],
      },
    };

    const result = validateRoutesManifest(manifest, "http://staging-api:8000");
    expect(result.destination).toBe("http://staging-api:8000/api/v1/:path*");
  });

  it("falha quando rewrites.afterFiles está vazio (cenário do bug do GHCR)", () => {
    const manifestComBug = {
      rewrites: {
        beforeFiles: [],
        afterFiles: [],
        fallback: [],
      },
    };

    expect(() => validateRoutesManifest(manifestComBug)).toThrow(
      "Nenhum rewrite para '/api/v1/:path*' encontrado em routes-manifest.json"
    );
  });

  it("falha quando o destino não aponta para a origem esperada", () => {
    const manifestInvalido = {
      rewrites: {
        afterFiles: [
          {
            source: "/api/v1/:path*",
            destination: "http://outra-url:9000/api/v1/:path*",
          },
        ],
      },
    };

    expect(() => validateRoutesManifest(manifestInvalido, "http://api:8000")).toThrow(
      "Destino do rewrite 'http://outra-url:9000/api/v1/:path*' não inicia com a origem esperada 'http://api:8000'"
    );
  });

  it("falha quando manifest é nulo ou não é objeto", () => {
    expect(() => validateRoutesManifest(null)).toThrow("Manifest inválido");
    expect(() => validateRoutesManifest(undefined)).toThrow("Manifest inválido");
  });

  it("falha quando campo rewrites está ausente", () => {
    expect(() => validateRoutesManifest({})).toThrow("Campo 'rewrites' ausente");
  });
});
