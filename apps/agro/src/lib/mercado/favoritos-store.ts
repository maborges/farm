"use client";

import { useSyncExternalStore } from "react";
import { PRODUTOS_CATALOGO, type ProdutoCatalogo } from "./catalogo";

export const FAVORITOS_STORAGE_KEY = "deepfarms_agro_mercado_favoritos_v1";

const IDS_CATALOGO_VALIDOS = new Set(PRODUTOS_CATALOGO.map((item) => item.id));

export interface FavoritosStoreState {
  favoritos: readonly string[];
  isLoaded: boolean;
}

const SERVER_SNAPSHOT: FavoritosStoreState = {
  favoritos: [],
  isLoaded: false,
};

let currentSnapshot: FavoritosStoreState = SERVER_SNAPSHOT;
let initialized = false;
const listeners = new Set<() => void>();

/**
 * Filtra e deduplica IDs contra a allow-list oficial do catálogo.
 */
export function parseFavoritosSalvos(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  const vistos = new Set<string>();
  const resultado: string[] = [];
  for (const item of raw) {
    if (typeof item === "string" && IDS_CATALOGO_VALIDOS.has(item) && !vistos.has(item)) {
      vistos.add(item);
      resultado.push(item);
    }
  }
  return resultado;
}

/**
 * Lê a lista de IDs favoritos persistida no Storage com tratamento de corrupção.
 */
export function readSavedFavoritos(
  storage: Pick<Storage, "getItem" | "removeItem">
): string[] {
  try {
    const raw = storage.getItem(FAVORITOS_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    const validos = parseFavoritosSalvos(parsed);
    if (validos.length === 0 && raw !== "[]") {
      storage.removeItem(FAVORITOS_STORAGE_KEY);
    }
    return validos;
  } catch {
    return [];
  }
}

/**
 * Grava a lista de IDs favoritos validados no Storage.
 */
export function saveFavoritos(
  storage: Pick<Storage, "setItem">,
  favoritos: readonly string[]
): boolean {
  const validos = parseFavoritosSalvos(favoritos);
  try {
    storage.setItem(FAVORITOS_STORAGE_KEY, JSON.stringify(validos));
    return true;
  } catch {
    return false;
  }
}

/**
 * Alterna um ID válido na lista de favoritos sem mutar o array de entrada.
 */
export function toggleFavoritoId(
  favoritos: readonly string[],
  commodityId: string
): string[] {
  if (!IDS_CATALOGO_VALIDOS.has(commodityId)) {
    return parseFavoritosSalvos(favoritos);
  }
  if (favoritos.includes(commodityId)) {
    return favoritos.filter((id) => id !== commodityId);
  }
  return [...favoritos, commodityId];
}

/**
 * Posiciona os itens favoritos no topo na ordem fixada, preservando os demais.
 */
export function ordenarProdutosComFavoritos(
  produtos: readonly ProdutoCatalogo[],
  favoritos: readonly string[]
): ProdutoCatalogo[] {
  if (favoritos.length === 0) {
    return [...produtos];
  }
  const porId = new Map(produtos.map((p) => [p.id, p]));
  const fixados: ProdutoCatalogo[] = [];
  const idsFixados = new Set<string>();
  for (const favId of favoritos) {
    const prod = porId.get(favId);
    if (prod && !idsFixados.has(favId)) {
      idsFixados.add(favId);
      fixados.push(prod);
    }
  }
  const restantes = produtos.filter((p) => !idsFixados.has(p.id));
  return [...fixados, ...restantes];
}

function notifyListeners(): void {
  for (const listener of listeners) {
    listener();
  }
}

function initStoreOnce(): void {
  if (initialized || typeof window === "undefined") return;
  initialized = true;
  currentSnapshot = {
    favoritos: readSavedFavoritos(window.localStorage),
    isLoaded: true,
  };
  window.addEventListener("storage", (event: StorageEvent) => {
    if (event.key === FAVORITOS_STORAGE_KEY) {
      currentSnapshot = {
        favoritos: readSavedFavoritos(window.localStorage),
        isLoaded: true,
      };
      notifyListeners();
    }
  });
}

/**
 * Alterna uma commodity nos favoritos globais persistidos em localStorage.
 */
export function toggleFavoritoMercado(commodityId: string): void {
  if (typeof window === "undefined") return;
  initStoreOnce();
  const proximos = toggleFavoritoId(currentSnapshot.favoritos, commodityId);
  saveFavoritos(window.localStorage, proximos);
  currentSnapshot = { favoritos: proximos, isLoaded: true };
  notifyListeners();
}

/**
 * Remove todos os favoritos salvos do módulo Mercado.
 */
export function limparFavoritosMercado(): void {
  if (typeof window === "undefined") return;
  initStoreOnce();
  saveFavoritos(window.localStorage, []);
  currentSnapshot = { favoritos: [], isLoaded: true };
  notifyListeners();
}

function getFavoritosSnapshot(): FavoritosStoreState {
  initStoreOnce();
  return currentSnapshot;
}

function getServerFavoritosSnapshot(): FavoritosStoreState {
  return SERVER_SNAPSHOT;
}

function subscribeFavoritos(callback: () => void): () => void {
  initStoreOnce();
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

/**
 * Hook reativo para fixar e consultar commodities favoritas do produtor.
 */
export function useFavoritosMercado(): FavoritosStoreState & {
  toggleFavorito: (_id: string) => void;
  limparFavoritos: () => void;
} {
  const state = useSyncExternalStore(
    subscribeFavoritos,
    getFavoritosSnapshot,
    getServerFavoritosSnapshot
  );

  return {
    ...state,
    toggleFavorito: toggleFavoritoMercado,
    limparFavoritos: limparFavoritosMercado,
  };
}
