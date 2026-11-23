"use client";

import * as React from "react";
import {
  detectDeviceCategory,
  detectExecutionMode,
  detectPlatformOS,
  getAdaptiveLayoutProfile,
  type AdaptiveLayoutProfile,
  type DeviceCategory,
  type DeviceExecutionContext,
} from "./device-detection";

export interface AdaptiveDeviceState extends DeviceExecutionContext {
  layoutProfile: AdaptiveLayoutProfile;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  isHydrated: boolean;
}

const DEFAULT_CONTEXT: DeviceExecutionContext = {
  deviceCategory: "mobile",
  executionMode: "browser",
  platformOS: "other",
  isTouch: true,
  isPortrait: true,
};

const DEFAULT_STATE: AdaptiveDeviceState = {
  ...DEFAULT_CONTEXT,
  layoutProfile: getAdaptiveLayoutProfile(DEFAULT_CONTEXT),
  sidebarCollapsed: false,
  toggleSidebar: () => {},
  isHydrated: false,
};

const DeviceContext = React.createContext<AdaptiveDeviceState>(DEFAULT_STATE);

const SIDEBAR_STORAGE_KEY = "deepfarms_agro_sidebar_collapsed_v1";

/**
 * Lê o estado instantâneo do ambiente de execução no navegador.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   Objeto DeviceExecutionContext populado com dados reais da janela.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function readBrowserDeviceContext(): DeviceExecutionContext {
  if (typeof window === "undefined") {
    return DEFAULT_CONTEXT;
  }

  const width = window.innerWidth;
  const height = window.innerHeight;
  const nav = window.navigator as Navigator & { standalone?: boolean };
  const userAgent = nav.userAgent ?? "";
  const platform = nav.platform ?? "";
  const maxTouchPoints = nav.maxTouchPoints ?? 0;
  const isTouch =
    maxTouchPoints > 0 ||
    window.matchMedia?.("(pointer: coarse)").matches ||
    "ontouchstart" in window;
  const isStandaloneMedia = window.matchMedia?.("(display-mode: standalone)").matches ?? false;

  const deviceCategory = detectDeviceCategory({
    width,
    height,
    isTouch,
    userAgent,
    platform,
    maxTouchPoints,
  });

  return {
    deviceCategory,
    executionMode: detectExecutionMode(isStandaloneMedia, Boolean(nav.standalone)),
    platformOS: detectPlatformOS(userAgent, platform, maxTouchPoints),
    isTouch,
    isPortrait: height >= width,
  };
}

/**
 * Lê a preferência salva da sidebar para modo desktop no navegador.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   Verdadeiro se a sidebar desktop deve iniciar retraída.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function readDesktopSidebarPreference(): boolean {
  try {
    return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function DeviceContextProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const [context, setContext] = React.useState<DeviceExecutionContext>(DEFAULT_CONTEXT);
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState<boolean>(false);
  const [isHydrated, setIsHydrated] = React.useState<boolean>(false);
  const contextRef = React.useRef<DeviceExecutionContext>(DEFAULT_CONTEXT);
  const lastCategoryRef = React.useRef<DeviceCategory | null>(null);

  React.useEffect(() => {
    const applyDeviceState = (nextContext: DeviceExecutionContext) => {
      const prevCategory = lastCategoryRef.current;
      contextRef.current = nextContext;
      setContext(nextContext);

      if (nextContext.deviceCategory !== prevCategory) {
        lastCategoryRef.current = nextContext.deviceCategory;
        if (nextContext.deviceCategory === "tablet") {
          setSidebarCollapsed(true);
        } else if (nextContext.deviceCategory === "desktop") {
          setSidebarCollapsed(readDesktopSidebarPreference());
        }
      }
    };

    applyDeviceState(readBrowserDeviceContext());
    setIsHydrated(true);

    const handleUpdate = () => {
      applyDeviceState(readBrowserDeviceContext());
    };

    const standaloneMedia = window.matchMedia?.("(display-mode: standalone)");
    window.addEventListener("resize", handleUpdate, { passive: true });
    window.addEventListener("orientationchange", handleUpdate, { passive: true });
    window.addEventListener("appinstalled", handleUpdate);
    standaloneMedia?.addEventListener("change", handleUpdate);

    return () => {
      window.removeEventListener("resize", handleUpdate);
      window.removeEventListener("orientationchange", handleUpdate);
      window.removeEventListener("appinstalled", handleUpdate);
      standaloneMedia?.removeEventListener("change", handleUpdate);
    };
  }, []);

  const toggleSidebar = React.useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      if (contextRef.current.deviceCategory === "desktop") {
        try {
          window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
        } catch {
          // Ignora erro de quota ou privacidade no localStorage
        }
      }
      return next;
    });
  }, []);

  const value = React.useMemo<AdaptiveDeviceState>(() => {
    const layoutProfile = getAdaptiveLayoutProfile(context);
    return {
      ...context,
      layoutProfile,
      sidebarCollapsed,
      toggleSidebar,
      isHydrated,
    };
  }, [context, sidebarCollapsed, toggleSidebar, isHydrated]);

  return <DeviceContext.Provider value={value}>{children}</DeviceContext.Provider>;
}

/**
 * Hook para consumir o estado adaptativo do dispositivo em qualquer Client Component.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   Estado consolidado do dispositivo e perfil de layout adaptativo.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function useDeviceContext(): AdaptiveDeviceState {
  return React.useContext(DeviceContext);
}

