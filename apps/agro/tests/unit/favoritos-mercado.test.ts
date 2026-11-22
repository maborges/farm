import { describe, it, expect } from "vitest";
import { PRODUTOS_CATALOGO } from "../../src/lib/mercado/catalogo";
import {
  FAVORITOS_STORAGE_KEY,
  ordenarProdutosComFavoritos,
  parseFavoritosSalvos,
  readSavedFavoritos,
  saveFavoritos,
  toggleFavoritoId,
} from "../../src/lib/mercado/favoritos-store";

function criarStorageMock(inicial: Record<string, string> = {}) {
  const dados = new Map<string, string>(Object.entries(inicial));
  return {
    getItem(key: string): string | null {
      return dados.get(key) ?? null;
    },
    setItem(key: string, value: string): void {
      dados.set(key, value);
    },
    removeItem(key: string): void {
      dados.delete(key);
    },
  };
}

describe("Store de Favoritos de Mercado (apps/agro)", () => {
  it("parseFavoritosSalvos aceita somente IDs válidos do catálogo e descarta inválidos/duplicatas", () => {
    const validos = parseFavoritosSalvos([
      "boi-gordo",
      "<script>alert(1)</script>",
      "soja",
      "boi-gordo",
      "commodity-inexistente",
      123,
      "",
    ]);
    expect(validos).toEqual(["boi-gordo", "soja"]);
    expect(parseFavoritosSalvos(null)).toEqual([]);
    expect(parseFavoritosSalvos("soja")).toEqual([]);
    expect(parseFavoritosSalvos({ id: "soja" })).toEqual([]);
  });

  it("toggleFavoritoId adiciona e remove sem mutar o array original", () => {
    const inicial = ["soja"];
    const adicionado = toggleFavoritoId(inicial, "boi-gordo");
    expect(adicionado).toEqual(["soja", "boi-gordo"]);
    expect(inicial).toEqual(["soja"]);

    const removido = toggleFavoritoId(adicionado, "soja");
    expect(removido).toEqual(["boi-gordo"]);

    const invalido = toggleFavoritoId(inicial, "invalido-xyz");
    expect(invalido).toEqual(["soja"]);
  });

  it("ordenarProdutosComFavoritos fixa favoritos no topo preservando a ordem dos demais", () => {
    const semFavs = ordenarProdutosComFavoritos(PRODUTOS_CATALOGO, []);
    expect(semFavs.map((p) => p.id)).toEqual(PRODUTOS_CATALOGO.map((p) => p.id));

    const ordenados = ordenarProdutosComFavoritos(PRODUTOS_CATALOGO, ["leite", "boi-gordo"]);
    expect(ordenados[0].id).toBe("leite");
    expect(ordenados[1].id).toBe("boi-gordo");
    expect(ordenados).toHaveLength(PRODUTOS_CATALOGO.length);

    const restante = ordenados.slice(2).map((p) => p.id);
    expect(restante).not.toContain("leite");
    expect(restante).not.toContain("boi-gordo");
    expect(restante[0]).toBe("soja");
  });

  it("persiste e recupera favoritos com resiliência contra JSON corrompido no Storage", () => {
    const storage = criarStorageMock({
      [FAVORITOS_STORAGE_KEY]: "{json-quebrado",
    });
    expect(readSavedFavoritos(storage)).toEqual([]);

    expect(saveFavoritos(storage, ["milho", "inexistente", "cafe-arabica"])).toBe(true);
    expect(readSavedFavoritos(storage)).toEqual(["milho", "cafe-arabica"]);
  });
});
