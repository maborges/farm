import { create } from "zustand";

const AUTO_CHECK_THROTTLE_MS = 60_000;
const PERIODIC_CHECK_INTERVAL_MS = 10 * 60_000;
const APPLY_FALLBACK_RELOAD_MS = 3_000;
const INSTALL_WAIT_TIMEOUT_MS = 4_000;

/**
 * Adaptador de runtime para recarregar a página de forma isolada e testável em jsdom.
 */
export const pwaUpdateRuntime = {
  reload: (): void => {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  },
};

interface PwaUpdateState {
  hasUpdate: boolean;
  isChecking: boolean;
  isApplying: boolean;
  dismissed: boolean;
  lastCheckedAt: string | null;
  feedbackMessage: string | null;
  waitingWorker: ServiceWorker | null;
  controllerChangedExternally: boolean;
  markUpdateAvailable: (worker: ServiceWorker | null) => void;
  markControllerChanged: () => void;
  dismiss: () => void;
  reset: () => void;
  checkForUpdate: () => Promise<boolean>;
  applyUpdate: () => Promise<void>;
}

let lastAutoCheckMs = 0;
let didReload = false;
let fallbackReloadTimer: ReturnType<typeof setTimeout> | null = null;

function clearFallbackReloadTimer(): void {
  if (fallbackReloadTimer !== null) {
    clearTimeout(fallbackReloadTimer);
    fallbackReloadTimer = null;
  }
}

function triggerReloadOnce(): void {
  if (didReload) return;
  didReload = true;
  clearFallbackReloadTimer();
  pwaUpdateRuntime.reload();
}

function isServiceWorkerAvailable(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof navigator !== "undefined" &&
    "serviceWorker" in navigator
  );
}

async function getActiveRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!isServiceWorkerAvailable()) return null;
  try {
    const registration = await navigator.serviceWorker.getRegistration();
    return registration ?? null;
  } catch {
    return null;
  }
}

function waitForInstallingWorker(worker: ServiceWorker): Promise<ServiceWorker | null> {
  if (worker.state === "installed") {
    return Promise.resolve(navigator.serviceWorker.controller ? worker : null);
  }
  if (worker.state === "redundant" || worker.state === "activated") {
    return Promise.resolve(null);
  }

  return new Promise((resolve) => {
    let settled = false;
    const finish = (result: ServiceWorker | null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeoutId);
      worker.removeEventListener("statechange", onStateChange);
      resolve(result);
    };

    const onStateChange = () => {
      if (worker.state === "installed") {
        finish(navigator.serviceWorker.controller ? worker : null);
      } else if (worker.state === "redundant" || worker.state === "activated") {
        finish(null);
      }
    };

    const timeoutId = setTimeout(() => finish(null), INSTALL_WAIT_TIMEOUT_MS);
    worker.addEventListener("statechange", onStateChange);
  });
}

/**
 * Store Zustand responsável pelo ciclo de vida controlado de atualização do PWA Campo.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   Store hook com estado de atualização disponível e ações seguras sem perda de dados offline.
 *
 * Raises:
 *   Nenhuma exceção não tratada é lançada.
 */
export const usePwaUpdateStore = create<PwaUpdateState>((set, get) => ({
  hasUpdate: false,
  isChecking: false,
  isApplying: false,
  dismissed: false,
  lastCheckedAt: null,
  feedbackMessage: null,
  waitingWorker: null,
  controllerChangedExternally: false,

  markUpdateAvailable: (worker) =>
    set({
      hasUpdate: true,
      dismissed: false,
      waitingWorker: worker,
      feedbackMessage: "Nova versão encontrada e pronta para instalar.",
    }),

  markControllerChanged: () =>
    set({
      hasUpdate: true,
      dismissed: false,
      controllerChangedExternally: true,
      feedbackMessage: "Nova versão pronta para aplicar nesta janela.",
    }),

  dismiss: () => set({ dismissed: true }),

  reset: () => {
    lastAutoCheckMs = 0;
    didReload = false;
    clearFallbackReloadTimer();
    set({
      hasUpdate: false,
      isChecking: false,
      isApplying: false,
      dismissed: false,
      lastCheckedAt: null,
      feedbackMessage: null,
      waitingWorker: null,
      controllerChangedExternally: false,
    });
  },

  checkForUpdate: async () => {
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      set({ feedbackMessage: "Sem conexão para verificar atualizações." });
      return false;
    }

    const registration = await getActiveRegistration();
    if (!registration) {
      set({ feedbackMessage: "Verificação disponível após ativação do modo offline." });
      return false;
    }

    set({ isChecking: true, feedbackMessage: null });
    try {
      await registration.update();
      const nowIso = new Date().toISOString();

      let pendingWorker = registration.waiting;
      if (!pendingWorker && registration.installing) {
        pendingWorker = await waitForInstallingWorker(registration.installing);
      }

      if (pendingWorker && navigator.serviceWorker.controller) {
        set({
          hasUpdate: true,
          dismissed: false,
          waitingWorker: pendingWorker,
          lastCheckedAt: nowIso,
          feedbackMessage: "Nova versão encontrada e pronta para instalar.",
        });
        return true;
      }

      set({
        lastCheckedAt: nowIso,
        feedbackMessage: "Você já está na versão mais recente.",
      });
      return false;
    } catch {
      set({ feedbackMessage: "Não foi possível verificar atualizações agora." });
      return false;
    } finally {
      set({ isChecking: false });
    }
  },

  applyUpdate: async () => {
    const state = get();
    set({ isApplying: true });

    let worker = state.waitingWorker;
    if (!worker) {
      const registration = await getActiveRegistration();
      worker = registration?.waiting ?? null;
    }

    if (worker) {
      worker.postMessage({ type: "SKIP_WAITING" });
      clearFallbackReloadTimer();
      fallbackReloadTimer = setTimeout(() => {
        triggerReloadOnce();
      }, APPLY_FALLBACK_RELOAD_MS);
      return;
    }

    triggerReloadOnce();
  },
}));

function inspectExistingRegistration(registration: ServiceWorkerRegistration): void {
  if (registration.waiting && navigator.serviceWorker.controller) {
    usePwaUpdateStore.getState().markUpdateAvailable(registration.waiting);
  }
}

async function runThrottledAutoCheck(force = false): Promise<void> {
  if (typeof navigator !== "undefined" && !navigator.onLine) return;
  const now = Date.now();
  if (!force && now - lastAutoCheckMs < AUTO_CHECK_THROTTLE_MS) return;

  const registration = await getActiveRegistration();
  if (!registration) return;

  lastAutoCheckMs = now;
  try {
    await registration.update();
    inspectExistingRegistration(registration);
  } catch {
    // Falhas transitórias de rede não devem interromper operação offline
  }
}

/**
 * Inicializa os listeners de detecção de novas versões do Service Worker no cliente.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   () => void: Função de limpeza que remove todos os listeners e timers registrados.
 *
 * Raises:
 *   Nenhuma exceção é lançada caso Service Worker não seja suportado.
 */
export function initPwaUpdateListeners(): () => void {
  if (!isServiceWorkerAvailable()) {
    return () => {};
  }

  let disposed = false;
  const observedRegistrations = new WeakSet<ServiceWorkerRegistration>();
  const regCleanupCallbacks: Array<() => void> = [];

  const bindRegistration = (registration: ServiceWorkerRegistration | undefined) => {
    if (disposed || !registration || observedRegistrations.has(registration)) return;
    observedRegistrations.add(registration);
    inspectExistingRegistration(registration);

    const watchWorker = (worker: ServiceWorker | null) => {
      if (!worker) return;
      const onStateChange = () => {
        if (worker.state === "installed" && navigator.serviceWorker.controller) {
          usePwaUpdateStore.getState().markUpdateAvailable(worker);
        }
      };
      worker.addEventListener("statechange", onStateChange);
      regCleanupCallbacks.push(() => worker.removeEventListener("statechange", onStateChange));
    };

    const onUpdateFound = () => watchWorker(registration.installing);
    registration.addEventListener("updatefound", onUpdateFound);
    regCleanupCallbacks.push(() =>
      registration.removeEventListener("updatefound", onUpdateFound)
    );
    if (registration.installing) {
      watchWorker(registration.installing);
    }
  };

  const onControllerChange = () => {
    if (usePwaUpdateStore.getState().isApplying) {
      triggerReloadOnce();
    } else {
      usePwaUpdateStore.getState().markControllerChanged();
    }
  };

  const onVisibilityChange = () => {
    if (document.visibilityState === "visible") {
      void runThrottledAutoCheck();
    }
  };

  const onOnline = () => {
    void runThrottledAutoCheck();
  };

  navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);
  document.addEventListener("visibilitychange", onVisibilityChange);
  window.addEventListener("online", onOnline);

  const periodicInterval = setInterval(() => {
    if (document.visibilityState === "visible") {
      void runThrottledAutoCheck();
    }
  }, PERIODIC_CHECK_INTERVAL_MS);

  void getActiveRegistration().then((reg) => {
    if (reg) bindRegistration(reg);
    void runThrottledAutoCheck(true);
  });

  if (navigator.serviceWorker.ready) {
    void navigator.serviceWorker.ready
      .then((reg) => bindRegistration(reg))
      .catch(() => {});
  }

  return () => {
    disposed = true;
    navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
    document.removeEventListener("visibilitychange", onVisibilityChange);
    window.removeEventListener("online", onOnline);
    clearInterval(periodicInterval);
    clearFallbackReloadTimer();
    for (const unregister of regCleanupCallbacks) {
      unregister();
    }
  };
}
