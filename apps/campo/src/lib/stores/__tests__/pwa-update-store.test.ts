import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  initPwaUpdateListeners,
  pwaUpdateRuntime,
  usePwaUpdateStore,
} from "../pwa-update-store";

type EventListenerFn = (event: Event) => void;

interface MockWorkerController {
  worker: ServiceWorker;
  postMessage: ReturnType<typeof vi.fn>;
  setState: (state: ServiceWorkerState) => void;
}

function createMockServiceWorker(initialState: ServiceWorkerState = "installed"): MockWorkerController {
  const listeners = new Map<string, Set<EventListenerFn>>();
  const postMessage = vi.fn();
  let currentState = initialState;

  const worker = {
    get state() {
      return currentState;
    },
    scriptURL: "/sw.js",
    onstatechange: null,
    onerror: null,
    postMessage,
    addEventListener(type: string, cb: EventListenerOrEventListenerObject) {
      const fn = typeof cb === "function" ? cb : cb.handleEvent.bind(cb);
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type)?.add(fn);
    },
    removeEventListener(type: string, cb: EventListenerOrEventListenerObject) {
      const fn = typeof cb === "function" ? cb : cb.handleEvent.bind(cb);
      listeners.get(type)?.delete(fn);
    },
    dispatchEvent(event: Event) {
      for (const fn of listeners.get(event.type) ?? []) {
        fn(event);
      }
      return true;
    },
  } as unknown as ServiceWorker;

  return {
    worker,
    postMessage,
    setState: (nextState: ServiceWorkerState) => {
      currentState = nextState;
      worker.dispatchEvent(new Event("statechange"));
    },
  };
}

interface MockRegistrationController {
  registration: ServiceWorkerRegistration;
  updateSpy: ReturnType<typeof vi.fn>;
  setWaiting: (worker: ServiceWorker | null) => void;
  setInstalling: (worker: ServiceWorker | null) => void;
  triggerUpdateFound: () => void;
}

function createMockRegistration(): MockRegistrationController {
  const listeners = new Map<string, Set<EventListenerFn>>();
  let waiting: ServiceWorker | null = null;
  let installing: ServiceWorker | null = null;
  const updateSpy = vi.fn(async () => {});

  const registration = {
    scope: "/",
    active: null,
    get waiting() {
      return waiting;
    },
    get installing() {
      return installing;
    },
    navigationPreload: {} as NavigationPreloadManager,
    pushManager: {} as PushManager,
    updateViaCache: "imports",
    onupdatefound: null,
    update: updateSpy,
    unregister: vi.fn(async () => true),
    showNotification: vi.fn(async () => {}),
    getNotifications: vi.fn(async () => []),
    addEventListener(type: string, cb: EventListenerOrEventListenerObject) {
      const fn = typeof cb === "function" ? cb : cb.handleEvent.bind(cb);
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type)?.add(fn);
    },
    removeEventListener(type: string, cb: EventListenerOrEventListenerObject) {
      const fn = typeof cb === "function" ? cb : cb.handleEvent.bind(cb);
      listeners.get(type)?.delete(fn);
    },
    dispatchEvent(event: Event) {
      for (const fn of listeners.get(event.type) ?? []) {
        fn(event);
      }
      return true;
    },
  } as unknown as ServiceWorkerRegistration;

  return {
    registration,
    updateSpy,
    setWaiting: (worker) => {
      waiting = worker;
    },
    setInstalling: (worker) => {
      installing = worker;
    },
    triggerUpdateFound: () => {
      registration.dispatchEvent(new Event("updatefound"));
    },
  };
}

interface MockContainerController {
  container: ServiceWorkerContainer;
  setController: (worker: ServiceWorker | null) => void;
  triggerControllerChange: () => void;
}

function installMockServiceWorker(
  registration: ServiceWorkerRegistration | undefined,
  initialController: ServiceWorker | null
): MockContainerController {
  const listeners = new Map<string, Set<EventListenerFn>>();
  let controller: ServiceWorker | null = initialController;

  const container = {
    get controller() {
      return controller;
    },
    ready: registration
      ? Promise.resolve(registration)
      : new Promise<ServiceWorkerRegistration>(() => {}),
    getRegistration: vi.fn(async () => registration),
    getRegistrations: vi.fn(async () => (registration ? [registration] : [])),
    register: vi.fn(async () => registration as ServiceWorkerRegistration),
    startMessages: vi.fn(),
    oncontrollerchange: null,
    onmessage: null,
    onmessageerror: null,
    addEventListener(type: string, cb: EventListenerOrEventListenerObject) {
      const fn = typeof cb === "function" ? cb : cb.handleEvent.bind(cb);
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type)?.add(fn);
    },
    removeEventListener(type: string, cb: EventListenerOrEventListenerObject) {
      const fn = typeof cb === "function" ? cb : cb.handleEvent.bind(cb);
      listeners.get(type)?.delete(fn);
    },
    dispatchEvent(event: Event) {
      for (const fn of listeners.get(event.type) ?? []) {
        fn(event);
      }
      return true;
    },
  } as unknown as ServiceWorkerContainer;

  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: container,
  });

  return {
    container,
    setController: (nextController) => {
      controller = nextController;
    },
    triggerControllerChange: () => {
      container.dispatchEvent(new Event("controllerchange"));
    },
  };
}

async function flushMicrotasks(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

describe("pwa-update-store", () => {
  let online = true;
  let visibility: DocumentVisibilityState = "visible";
  let cleanupListeners: (() => void) | null = null;
  let reloadSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-21T10:00:00Z"));
    online = true;
    visibility = "visible";
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      get: () => online,
    });
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => visibility,
    });
    usePwaUpdateStore.getState().reset();
    reloadSpy = vi.spyOn(pwaUpdateRuntime, "reload").mockImplementation(() => {});
  });

  afterEach(() => {
    cleanupListeners?.();
    cleanupListeners = null;
    reloadSpy.mockRestore();
    vi.useRealTimers();
  });

  it("detecta waiting worker existente quando já há controller ativo", async () => {
    const active = createMockServiceWorker("activated");
    const waiting = createMockServiceWorker("installed");
    const regCtrl = createMockRegistration();
    regCtrl.setWaiting(waiting.worker);
    installMockServiceWorker(regCtrl.registration, active.worker);

    cleanupListeners = initPwaUpdateListeners();
    await flushMicrotasks();

    const state = usePwaUpdateStore.getState();
    expect(state.hasUpdate).toBe(true);
    expect(state.waitingWorker).toBe(waiting.worker);
    expect(state.dismissed).toBe(false);
  });

  it("detecta updatefound -> installed apenas quando existe controller ativo", async () => {
    const active = createMockServiceWorker("activated");
    const next = createMockServiceWorker("installing");
    const regCtrl = createMockRegistration();
    const containerCtrl = installMockServiceWorker(regCtrl.registration, null);

    cleanupListeners = initPwaUpdateListeners();
    await flushMicrotasks();

    regCtrl.setInstalling(next.worker);
    regCtrl.triggerUpdateFound();
    next.setState("installed");
    await flushMicrotasks();

    expect(usePwaUpdateStore.getState().hasUpdate).toBe(false);

    containerCtrl.setController(active.worker);
    const newer = createMockServiceWorker("installing");
    regCtrl.setInstalling(newer.worker);
    regCtrl.triggerUpdateFound();
    newer.setState("installed");
    await flushMicrotasks();

    expect(usePwaUpdateStore.getState().hasUpdate).toBe(true);
    expect(usePwaUpdateStore.getState().waitingWorker).toBe(newer.worker);
  });

  it("controllerchange externo exibe banner sem recarregar abruptamente", async () => {
    const active = createMockServiceWorker("activated");
    const regCtrl = createMockRegistration();
    const containerCtrl = installMockServiceWorker(regCtrl.registration, active.worker);

    cleanupListeners = initPwaUpdateListeners();
    await flushMicrotasks();

    containerCtrl.triggerControllerChange();
    await flushMicrotasks();

    const state = usePwaUpdateStore.getState();
    expect(state.hasUpdate).toBe(true);
    expect(state.controllerChangedExternally).toBe(true);
    expect(reloadSpy).not.toHaveBeenCalled();
  });

  it("applyUpdate envia SKIP_WAITING e recarrega uma vez no controllerchange", async () => {
    const active = createMockServiceWorker("activated");
    const waiting = createMockServiceWorker("installed");
    const regCtrl = createMockRegistration();
    regCtrl.setWaiting(waiting.worker);
    const containerCtrl = installMockServiceWorker(regCtrl.registration, active.worker);

    cleanupListeners = initPwaUpdateListeners();
    await flushMicrotasks();

    await usePwaUpdateStore.getState().applyUpdate();

    expect(waiting.postMessage).toHaveBeenCalledWith({ type: "SKIP_WAITING" });
    expect(usePwaUpdateStore.getState().isApplying).toBe(true);
    expect(reloadSpy).not.toHaveBeenCalled();

    containerCtrl.triggerControllerChange();
    containerCtrl.triggerControllerChange();
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("applyUpdate usa fallback de timeout ou recarrega imediatamente se controller já mudou", async () => {
    const active = createMockServiceWorker("activated");
    const waiting = createMockServiceWorker("installed");
    const regCtrl = createMockRegistration();
    regCtrl.setWaiting(waiting.worker);
    installMockServiceWorker(regCtrl.registration, active.worker);

    cleanupListeners = initPwaUpdateListeners();
    await flushMicrotasks();

    await usePwaUpdateStore.getState().applyUpdate();
    vi.advanceTimersByTime(3100);
    expect(reloadSpy).toHaveBeenCalledTimes(1);

    reloadSpy.mockClear();
    usePwaUpdateStore.getState().reset();
    regCtrl.setWaiting(null);
    usePwaUpdateStore.getState().markControllerChanged();

    await usePwaUpdateStore.getState().applyUpdate();
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("checkForUpdate trata modo offline, versão atual e nova versão", async () => {
    const active = createMockServiceWorker("activated");
    const regCtrl = createMockRegistration();
    installMockServiceWorker(regCtrl.registration, active.worker);

    online = false;
    const offlineOk = await usePwaUpdateStore.getState().checkForUpdate();
    expect(offlineOk).toBe(false);
    expect(regCtrl.updateSpy).not.toHaveBeenCalled();
    expect(usePwaUpdateStore.getState().feedbackMessage).toMatch(/conexão/i);

    online = true;
    const upToDate = await usePwaUpdateStore.getState().checkForUpdate();
    expect(upToDate).toBe(false);
    expect(regCtrl.updateSpy).toHaveBeenCalledTimes(1);
    expect(usePwaUpdateStore.getState().feedbackMessage).toBe("Você já está na versão mais recente.");
    expect(usePwaUpdateStore.getState().lastCheckedAt).not.toBeNull();

    const waiting = createMockServiceWorker("installed");
    regCtrl.updateSpy.mockImplementationOnce(async () => {
      regCtrl.setWaiting(waiting.worker);
    });
    usePwaUpdateStore.getState().dismiss();

    const foundNew = await usePwaUpdateStore.getState().checkForUpdate();
    expect(foundNew).toBe(true);
    expect(usePwaUpdateStore.getState().hasUpdate).toBe(true);
    expect(usePwaUpdateStore.getState().dismissed).toBe(false);
    expect(usePwaUpdateStore.getState().waitingWorker).toBe(waiting.worker);
  });

  it("visibilitychange e online disparam update com throttle de 60s", async () => {
    const active = createMockServiceWorker("activated");
    const regCtrl = createMockRegistration();
    installMockServiceWorker(regCtrl.registration, active.worker);

    cleanupListeners = initPwaUpdateListeners();
    await flushMicrotasks();

    // Checagem inicial na montagem
    expect(regCtrl.updateSpy).toHaveBeenCalledTimes(1);

    // Dentro dos 60s não deve repetir
    vi.advanceTimersByTime(30_000);
    visibility = "visible";
    document.dispatchEvent(new Event("visibilitychange"));
    window.dispatchEvent(new Event("online"));
    await flushMicrotasks();
    expect(regCtrl.updateSpy).toHaveBeenCalledTimes(1);

    // Após 60s dispara normalmente
    vi.advanceTimersByTime(31_000);
    document.dispatchEvent(new Event("visibilitychange"));
    await flushMicrotasks();
    expect(regCtrl.updateSpy).toHaveBeenCalledTimes(2);
  });
});
