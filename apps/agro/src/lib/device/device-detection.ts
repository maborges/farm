/**
 * Módulo de detecção determinística de dispositivo, modo de execução PWA e perfil adaptativo.
 */

export type DeviceCategory = "mobile" | "tablet" | "desktop";
export type ExecutionMode = "standalone" | "browser";
export type PlatformOS = "ios" | "android" | "other";
export type NavigationPattern = "bottom-dock" | "navigation-rail" | "sidebar-and-topbar";
export type SheetPresentation = "bottom-sheet" | "centered-dialog";

export interface ViewportEnvironmentInput {
  width: number;
  height: number;
  isTouch: boolean;
  userAgent?: string;
  platform?: string;
  maxTouchPoints?: number;
}

export interface DeviceExecutionContext {
  deviceCategory: DeviceCategory;
  executionMode: ExecutionMode;
  platformOS: PlatformOS;
  isTouch: boolean;
  isPortrait: boolean;
}

export interface AdaptiveLayoutProfile {
  navigationPattern: NavigationPattern;
  sheetPresentation: SheetPresentation;
  compactHeader: boolean;
  touchOptimizedInputs: boolean;
  showSidebar: boolean;
}

/**
 * Verifica se o agente de usuário e plataforma correspondem a um tablet iPadOS ou Android.
 *
 * Args:
 *   input: Dados do ambiente de viewport e navegador.
 *
 * Return:
 *   Verdadeiro se o dispositivo apresentar assinatura de tablet.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function isTabletSignature(input: ViewportEnvironmentInput): boolean {
  const ua = input.userAgent ?? "";
  const touchPoints = input.maxTouchPoints ?? 0;
  const isIpadOs = input.platform === "MacIntel" && touchPoints > 1;
  const isIpadUa = /ipad/i.test(ua);
  const isAndroidTablet = /android/i.test(ua) && !/mobile/i.test(ua);
  return isIpadOs || isIpadUa || isAndroidTablet;
}

/**
 * Classifica a categoria do dispositivo onde o módulo PWA Agro está sendo executado.
 *
 * Args:
 *   input: Dimensões de viewport e sinais de hardware/navegador.
 *
 * Return:
 *   Categoria adaptativa ("mobile", "tablet" ou "desktop").
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function detectDeviceCategory(input: ViewportEnvironmentInput): DeviceCategory {
  const validWidth = Number.isFinite(input.width) && input.width > 0 ? input.width : 0;
  if (validWidth === 0) {
    return /iphone|ipod|android.*mobile/i.test(input.userAgent ?? "") ? "mobile" : "desktop";
  }
  if (validWidth < 768) {
    return "mobile";
  }
  if (validWidth < 1024 || (validWidth <= 1366 && isTabletSignature(input))) {
    return "tablet";
  }
  return "desktop";
}

/**
 * Identifica se a aplicação está rodando instalada em modo PWA standalone ou no navegador.
 *
 * Args:
 *   isStandaloneMedia: Resultado da media query (display-mode: standalone).
 *   navigatorStandalone: Propriedade standalone específica do Safari iOS.
 *
 * Return:
 *   Modo de execução ("standalone" ou "browser").
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function detectExecutionMode(
  isStandaloneMedia: boolean,
  navigatorStandalone: boolean = false
): ExecutionMode {
  return isStandaloneMedia || navigatorStandalone ? "standalone" : "browser";
}

/**
 * Detecta o sistema operacional principal para ajustes ergonômicos nativos.
 *
 * Args:
 *   userAgent: String de User-Agent do navegador.
 *   platform: Plataforma informada pelo navegador.
 *   maxTouchPoints: Número máximo de pontos de toque simultâneos.
 *
 * Return:
 *   Identificador do sistema ("ios", "android" ou "other").
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function detectPlatformOS(
  userAgent: string,
  platform: string = "",
  maxTouchPoints: number = 0
): PlatformOS {
  if (/iphone|ipad|ipod/i.test(userAgent) || (platform === "MacIntel" && maxTouchPoints > 1)) {
    return "ios";
  }
  if (/android/i.test(userAgent)) {
    return "android";
  }
  return "other";
}

/**
 * Deriva o perfil de UI/UX adaptativa a partir do contexto de execução detectado.
 *
 * Args:
 *   context: Contexto consolidado do dispositivo e modo de execução.
 *
 * Return:
 *   Perfil de layout adaptativo com padrões de navegação, modais e densidade.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function getAdaptiveLayoutProfile(
  context: DeviceExecutionContext
): AdaptiveLayoutProfile {
  if (context.deviceCategory === "mobile") {
    return {
      navigationPattern: "bottom-dock",
      sheetPresentation: "bottom-sheet",
      compactHeader: true,
      touchOptimizedInputs: true,
      showSidebar: false,
    };
  }
  if (context.deviceCategory === "tablet") {
    return {
      navigationPattern: "navigation-rail",
      sheetPresentation: "centered-dialog",
      compactHeader: false,
      touchOptimizedInputs: true,
      showSidebar: true,
    };
  }
  return {
    navigationPattern: "sidebar-and-topbar",
    sheetPresentation: "centered-dialog",
    compactHeader: false,
    touchOptimizedInputs: false,
    showSidebar: true,
  };
}

