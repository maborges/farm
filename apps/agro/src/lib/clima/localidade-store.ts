"use client";

import { useSyncExternalStore } from "react";
import {
  clearSavedLocalidade,
  LOCALIDADE_STORAGE_KEY,
  readSavedLocalidade,
  saveLocalidade,
  type LocalidadeClima,
} from "./localidade";

export interface LocalidadeStoreState {
  localidade: LocalidadeClima | null;
  isLoaded: boolean;
}

const DEFAULT_STATE: LocalidadeStoreState = {
  localidade: null,
  isLoaded: false,
};

let currentSnapshot: LocalidadeStoreState = DEFAULT_STATE;
let initialized = false;
const listeners = new Set<() => void>();

function notifyListeners(): void {
  for (const listener of listeners) {
    listener();
  }
}

function updateSnapshot(partial: Partial<LocalidadeStoreState>): void {
  currentSnapshot = { ...currentSnapshot, ...partial };
  notifyListeners();
}

function initStoreOnce(): void {
  if (initialized || typeof window === "undefined") return;
  initialized = true;

  const saved = readSavedLocalidade(window.localStorage);
  currentSnapshot = {
    localidade: saved,
    isLoaded: true,
  };

  // Sincronização multi-aba
  window.addEventListener("storage", (event: StorageEvent) => {
    if (event.key === LOCALIDADE_STORAGE_KEY) {
      const updated = readSavedLocalidade(window.localStorage);
      updateSnapshot({ localidade: updated });
    }
  });
}

/**
 * Define e persiste a localidade selecionada pelo usuário.
 */
export function setLocalidade(loc: LocalidadeClima): void {
  if (typeof window === "undefined") return;
  initStoreOnce();
  saveLocalidade(window.localStorage, loc);
  updateSnapshot({ localidade: loc });
}

/**
 * Limpa a localidade persistida.
 */
export function clearLocalidade(): void {
  if (typeof window === "undefined") return;
  initStoreOnce();
  clearSavedLocalidade(window.localStorage);
  updateSnapshot({ localidade: null });
}

/**
 * Obtém o snapshot atual para o cliente.
 */
export function getLocalidadeSnapshot(): LocalidadeStoreState {
  initStoreOnce();
  return currentSnapshot;
}

/**
 * Snapshot para SSR/RSC.
 */
export function getServerLocalidadeSnapshot(): LocalidadeStoreState {
  return DEFAULT_STATE;
}

/**
 * Inscrição reativa para useSyncExternalStore.
 */
export function subscribeLocalidade(callback: () => void): () => void {
  initStoreOnce();
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

/**
 * Hook reativo principal para consumo da localidade selecionada no PWA.
 */
export function useLocalidadeClima(): LocalidadeStoreState & {
  setLocalidade: (_loc: LocalidadeClima) => void;
  clearLocalidade: () => void;
} {
  const state = useSyncExternalStore(
    subscribeLocalidade,
    getLocalidadeSnapshot,
    getServerLocalidadeSnapshot
  );

  return {
    ...state,
    setLocalidade,
    clearLocalidade,
  };
}

/**
 * Reseta a store para testes unitários.
 */
export function _resetLocalidadeStoreForTesting(): void {
  currentSnapshot = DEFAULT_STATE;
  initialized = false;
  listeners.clear();
}
