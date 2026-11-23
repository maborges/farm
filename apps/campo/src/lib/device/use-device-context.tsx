"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  detectDeviceCategory,
  detectExecutionMode,
  detectPlatformOS,
  getAdaptiveLayoutProfile,
  type AdaptiveLayoutProfile,
  type DeviceCategory,
} from "./device-detection";

interface NavigatorWithStandalone extends Navigator {
  standalone?: boolean;
}

export interface DeviceContextValue {
  layoutProfile: AdaptiveLayoutProfile;
  isHydrated: boolean;
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

const DEFAULT_PROFILE: AdaptiveLayoutProfile = getAdaptiveLayoutProfile({
  deviceCategory: "mobile",
  executionMode: "browser",
  platformOS: "other",
});

const DeviceContext = createContext<DeviceContextValue>({
  layoutProfile: DEFAULT_PROFILE,
  isHydrated: false,
  isSidebarCollapsed: false,
  toggleSidebar: () => undefined,
  setSidebarCollapsed: () => undefined,
});

/**
 * Lê os sinais reais do navegador para construir o perfil adaptativo em runtime.
 *
 * Args:
 *   win (Window): Instância global de Window do cliente.
 *
 * Return:
 *   AdaptiveLayoutProfile: Perfil calculado a partir da viewport, pointer e display-mode.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function readBrowserAdaptiveProfile(win: Window): AdaptiveLayoutProfile {
  const nav = win.navigator as NavigatorWithStandalone;
  const userAgent = nav.userAgent ?? "";
  const hasCoarsePointer = win.matchMedia("(pointer: coarse)").matches;
  const isDisplayModeStandalone =
    win.matchMedia("(display-mode: standalone)").matches ||
    win.matchMedia("(display-mode: fullscreen)").matches ||
    win.matchMedia("(display-mode: minimal-ui)").matches;

  const deviceCategory = detectDeviceCategory({
    viewportWidth: win.innerWidth,
    hasCoarsePointer,
    userAgent,
  });
  const executionMode = detectExecutionMode({
    isDisplayModeStandalone,
    isNavigatorStandalone: Boolean(nav.standalone),
  });
  const platformOS = detectPlatformOS(userAgent);

  return getAdaptiveLayoutProfile({ deviceCategory, executionMode, platformOS });
}

/**
 * Provedor de contexto que monitora onde o PWA Campo está sendo executado e adapta a UI/UX.
 *
 * Args:
 *   props ({ children: ReactNode }): Elementos filhos da árvore React.
 *
 * Return:
 *   JSX.Element: Provider configurado com detecção reativa de viewport e modo PWA.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function DeviceContextProvider({ children }: { children: ReactNode }) {
  const [layoutProfile, setLayoutProfile] = useState<AdaptiveLayoutProfile>(DEFAULT_PROFILE);
  const [isHydrated, setIsHydrated] = useState<boolean>(false);
  const [isSidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const lastCategoryRef = useRef<DeviceCategory | null>(null);

  useEffect(() => {
    const updateProfile = () => {
      const nextProfile = readBrowserAdaptiveProfile(window);
      setLayoutProfile(nextProfile);
      setIsHydrated(true);

      if (nextProfile.deviceCategory !== lastCategoryRef.current) {
        lastCategoryRef.current = nextProfile.deviceCategory;
        if (nextProfile.deviceCategory === "tablet") {
          setSidebarCollapsed(true);
        } else if (nextProfile.deviceCategory === "desktop") {
          setSidebarCollapsed(false);
        }
      }
    };

    updateProfile();

    const standaloneQuery = window.matchMedia("(display-mode: standalone)");
    window.addEventListener("resize", updateProfile, { passive: true });
    standaloneQuery.addEventListener("change", updateProfile);

    return () => {
      window.removeEventListener("resize", updateProfile);
      standaloneQuery.removeEventListener("change", updateProfile);
    };
  }, []);

  const value = useMemo<DeviceContextValue>(
    () => ({
      layoutProfile,
      isHydrated,
      isSidebarCollapsed,
      toggleSidebar: () => setSidebarCollapsed((prev) => !prev),
      setSidebarCollapsed,
    }),
    [layoutProfile, isHydrated, isSidebarCollapsed]
  );

  return <DeviceContext.Provider value={value}>{children}</DeviceContext.Provider>;
}

/**
 * Hook para consumir o perfil de dispositivo e estado da sidebar adaptativa no módulo Campo.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   DeviceContextValue: Perfil de layout adaptativo e controles de navegação.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function useDeviceContext(): DeviceContextValue {
  return useContext(DeviceContext);
}

