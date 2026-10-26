"use client";

import { useSyncExternalStore } from "react";
import {
  CURRENCIES,
  fetchCurrencyQuote,
  readSavedCurrency,
  readSavedCurrencyQuote,
  saveCurrencyQuote,
  saveSelectedCurrency,
  type CurrencyCode,
  type EstadoDisponibilidadePtax,
  type PtaxPublicaV1,
} from "./ptax";

/**
 * Estado reativo compartilhado do subsistema cambial do Mercado.
 */
export interface MoedaMercadoState {
  currency: CurrencyCode;
  quote: PtaxPublicaV1 | null;
  loading: boolean;
  state: EstadoDisponibilidadePtax;
}

const DEFAULT_SNAPSHOT: MoedaMercadoState = {
  currency: "USD",
  quote: null,
  loading: false,
  state: "INDISPONIVEL",
};

let currentSnapshot: MoedaMercadoState = DEFAULT_SNAPSHOT;
let initialized = false;
let activeController: AbortController | null = null;
const listeners = new Set<() => void>();

function notifyListeners(): void {
  for (const listener of listeners) {
    listener();
  }
}

function updateSnapshot(partial: Partial<MoedaMercadoState>): void {
  const nextSnapshot = { ...currentSnapshot, ...partial };
  // Prevenção de re-renders desnecessários se os campos forem idênticos
  if (
    currentSnapshot.currency === nextSnapshot.currency &&
    currentSnapshot.quote === nextSnapshot.quote &&
    currentSnapshot.loading === nextSnapshot.loading &&
    currentSnapshot.state === nextSnapshot.state
  ) {
    return;
  }
  currentSnapshot = nextSnapshot;
  notifyListeners();
}

/**
 * Busca a cotação oficial da moeda fornecida (ou atual) sem inconsistências de corrida.
 */
async function fetchQuoteForCurrency(targetCurrency: CurrencyCode): Promise<void> {
  if (typeof window === "undefined") return;

  activeController?.abort();
  const controller = new AbortController();
  activeController = controller;

  const isOnline = navigator.onLine;
  const saved = readSavedCurrencyQuote(window.localStorage, targetCurrency);

  if (!isOnline) {
    updateSnapshot({
      quote: saved,
      loading: false,
      state: saved ? "OFFLINE" : "INDISPONIVEL",
    });
    return;
  }

  // Se estiver online, define estado de carregamento mantendo dado salvo (se existir)
  updateSnapshot({
    loading: true,
    state: saved ? saved.estadoDisponibilidade : "INDISPONIVEL",
  });

  try {
    const result = await fetchCurrencyQuote(
      targetCurrency,
      window.location,
      controller.signal
    );

    // Evita aplicar resposta atrasada se a moeda foi alterada ou requisição abortada
    if (controller.signal.aborted || currentSnapshot.currency !== targetCurrency) {
      return;
    }

    if (result && result.moeda === targetCurrency) {
      saveCurrencyQuote(window.localStorage, targetCurrency, result);
      const isCurrentlyOffline =
        currentSnapshot.state === "OFFLINE" ||
        (typeof navigator !== "undefined" && !navigator.onLine);
      updateSnapshot({
        quote: result,
        loading: false,
        state: isCurrentlyOffline ? "OFFLINE" : result.estadoDisponibilidade,
      });
    } else {
      updateSnapshot({
        loading: false,
        state: saved ? "FONTE_INDISPONIVEL" : "INDISPONIVEL",
      });
    }
  } catch {
    if (!controller.signal.aborted && currentSnapshot.currency === targetCurrency) {
      const isCurrentlyOffline =
        currentSnapshot.state === "OFFLINE" ||
        (typeof navigator !== "undefined" && !navigator.onLine);
      updateSnapshot({
        loading: false,
        state: isCurrentlyOffline
          ? (saved ? "OFFLINE" : "INDISPONIVEL")
          : (saved ? "FONTE_INDISPONIVEL" : "INDISPONIVEL"),
      });
    }
  }
}

/**
 * Inicializa a store no cliente lendo do localStorage e sincronizando eventos de janela.
 */
function initStoreOnce(): void {
  if (initialized || typeof window === "undefined") return;
  initialized = true;

  const savedCurrency = readSavedCurrency(window.localStorage);
  const savedQuote = readSavedCurrencyQuote(window.localStorage, savedCurrency);
  const isOnline = navigator.onLine;

  currentSnapshot = {
    currency: savedCurrency,
    quote: savedQuote,
    loading: isOnline,
    state: isOnline
      ? (savedQuote?.estadoDisponibilidade ?? "INDISPONIVEL")
      : (savedQuote ? "OFFLINE" : "INDISPONIVEL"),
  };

  // Sincronização entre abas do navegador
  window.addEventListener("storage", (event: StorageEvent) => {
    if (event.key === "deepfarms_agro_mercado_moeda_v1" && event.newValue) {
      const code = CURRENCIES.find((c) => c.code === event.newValue)?.code;
      if (code && code !== currentSnapshot.currency) {
        void mudarMoeda(code);
      }
    }
  });

  // Sincronização de conectividade
  window.addEventListener("online", () => {
    void fetchQuoteForCurrency(currentSnapshot.currency);
  });

  window.addEventListener("offline", () => {
    activeController?.abort();
    updateSnapshot({
      loading: false,
      state: currentSnapshot.quote ? "OFFLINE" : "INDISPONIVEL",
    });
  });

  // Dispara busca inicial online
  if (isOnline) {
    void fetchQuoteForCurrency(savedCurrency);
  }
}

/**
 * Altera a moeda ativa no sistema de forma atômica e reativa para todos os componentes.
 */
export async function mudarMoeda(newCurrency: CurrencyCode): Promise<void> {
  if (typeof window === "undefined") return;
  initStoreOnce();

  saveSelectedCurrency(window.localStorage, newCurrency);
  const savedQuote = readSavedCurrencyQuote(window.localStorage, newCurrency);
  const isOnline = navigator.onLine;

  // Atualização otimista imediata para os cards (0ms com cache)
  updateSnapshot({
    currency: newCurrency,
    quote: savedQuote,
    loading: isOnline,
    state: isOnline
      ? (savedQuote?.estadoDisponibilidade ?? "INDISPONIVEL")
      : (savedQuote ? "OFFLINE" : "INDISPONIVEL"),
  });

  if (isOnline) {
    await fetchQuoteForCurrency(newCurrency);
  }
}

/**
 * Força a atualização da cotação atual a partir da fonte oficial do BCB.
 */
export async function recarregarCotacao(): Promise<void> {
  initStoreOnce();
  await fetchQuoteForCurrency(currentSnapshot.currency);
}

/**
 * Obtém o snapshot atual do estado cambial.
 */
export function getMoedaSnapshot(): MoedaMercadoState {
  initStoreOnce();
  return currentSnapshot;
}

/**
 * Snapshot estático para SSR/RSC.
 */
export function getServerMoedaSnapshot(): MoedaMercadoState {
  return DEFAULT_SNAPSHOT;
}

/**
 * Subscrição reativa para useSyncExternalStore.
 */
export function subscribeMoeda(callback: () => void): () => void {
  initStoreOnce();
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

/**
 * Hook reativo principal do subsistema de moedas do Mercado.
 * Garante que qualquer alteração de moeda no PtaxCard seja propagada
 * instantaneamente para os cards do catálogo e vice-versa sem reload.
 */
export function useMoedaMercado(): MoedaMercadoState & {
  setCurrency: (_currency: CurrencyCode) => void;
  refresh: () => void;
} {
  const state = useSyncExternalStore(
    subscribeMoeda,
    getMoedaSnapshot,
    getServerMoedaSnapshot
  );

  return {
    ...state,
    setCurrency: (c: CurrencyCode) => {
      void mudarMoeda(c);
    },
    refresh: () => {
      void recarregarCotacao();
    },
  };
}

/**
 * Reseta o estado da store para uso exclusivo em testes unitários.
 */
export function _resetMoedaStoreForTesting(): void {
  currentSnapshot = DEFAULT_SNAPSHOT;
  initialized = false;
  activeController?.abort();
  activeController = null;
  listeners.clear();
}
