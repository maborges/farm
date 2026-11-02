export type DeviceCategory = "mobile" | "tablet" | "desktop";
export type ExecutionMode = "standalone" | "browser";
export type PlatformOS = "ios" | "android" | "other";

export type NavigationMode = "bottom-nav" | "rail-and-bottom" | "sidebar";
export type SheetPresentation = "bottom-sheet" | "centered-dialog";
export type TouchDensity = "touch-comfortable" | "compact";

export interface DeviceSignalsInput {
  viewportWidth: number;
  hasCoarsePointer: boolean;
  userAgent: string;
}

export interface ExecutionModeInput {
  isDisplayModeStandalone: boolean;
  isNavigatorStandalone: boolean;
}

export interface AdaptiveProfileInput {
  deviceCategory: DeviceCategory;
  executionMode: ExecutionMode;
  platformOS: PlatformOS;
}

export interface AdaptiveLayoutProfile {
  deviceCategory: DeviceCategory;
  executionMode: ExecutionMode;
  platformOS: PlatformOS;
  navigationMode: NavigationMode;
  sheetPresentation: SheetPresentation;
  density: TouchDensity;
  isNativeLikeShell: boolean;
  showInstallBanner: boolean;
}

const MOBILE_MAX_WIDTH = 767;
const TABLET_MAX_WIDTH = 1023;

/**
 * Verifica se o User-Agent corresponde a um tablet conhecido (iPad ou Android Tablet).
 *
 * Args:
 *   userAgent (string): String de identificação do navegador.
 *   hasCoarsePointer (boolean): Indica se o dispositivo primário é touch.
 *
 * Return:
 *   boolean: Verdadeiro se for identificado como tablet por UA ou ponteiro touch em tela média/grande.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function isTabletUserAgent(userAgent: string, hasCoarsePointer: boolean): boolean {
  const normalized = userAgent.toLowerCase();
  const isIpad = normalized.includes("ipad") || (normalized.includes("macintosh") && hasCoarsePointer);
  const isAndroidTablet = normalized.includes("android") && !normalized.includes("mobile");
  return isIpad || isAndroidTablet;
}

/**
 * Classifica a categoria física/ergonômica do dispositivo onde o módulo Campo está executando.
 *
 * Args:
 *   signals (DeviceSignalsInput): Largura da viewport, tipo de ponteiro e User-Agent.
 *
 * Return:
 *   DeviceCategory: Categoria detectada ('mobile', 'tablet' ou 'desktop').
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function detectDeviceCategory(signals: DeviceSignalsInput): DeviceCategory {
  const safeWidth = Number.isFinite(signals.viewportWidth) ? Math.max(0, signals.viewportWidth) : 0;

  if (safeWidth <= MOBILE_MAX_WIDTH) {
    return "mobile";
  }

  if (safeWidth <= TABLET_MAX_WIDTH) {
    return "tablet";
  }

  if (signals.hasCoarsePointer || isTabletUserAgent(signals.userAgent, signals.hasCoarsePointer)) {
    return "tablet";
  }

  return "desktop";
}

/**
 * Detecta se o aplicativo está executando instalado como PWA standalone ou em aba de navegador.
 *
 * Args:
 *   input (ExecutionModeInput): Flags de media query display-mode e navigator.standalone.
 *
 * Return:
 *   ExecutionMode: 'standalone' quando instalado na tela inicial ou 'browser' no navegador.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function detectExecutionMode(input: ExecutionModeInput): ExecutionMode {
  if (input.isDisplayModeStandalone || input.isNavigatorStandalone) {
    return "standalone";
  }
  return "browser";
}

/**
 * Identifica o sistema operacional principal a partir do User-Agent.
 *
 * Args:
 *   userAgent (string): String User-Agent do navegador.
 *
 * Return:
 *   PlatformOS: 'ios', 'android' ou 'other'.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function detectPlatformOS(userAgent: string): PlatformOS {
  const normalized = userAgent.toLowerCase();
  if (/iphone|ipad|ipod/.test(normalized)) {
    return "ios";
  }
  if (normalized.includes("android")) {
    return "android";
  }
  return "other";
}

/**
 * Constrói o perfil de UI/UX adaptativa de acordo com o ambiente de execução detectado.
 *
 * Args:
 *   input (AdaptiveProfileInput): Categoria de dispositivo, modo de execução e SO.
 *
 * Return:
 *   AdaptiveLayoutProfile: Diretrizes de navegação, modais, densidade e shell nativo.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function getAdaptiveLayoutProfile(input: AdaptiveProfileInput): AdaptiveLayoutProfile {
  const isMobile = input.deviceCategory === "mobile";
  const isTablet = input.deviceCategory === "tablet";
  const isTouchDevice = isMobile || isTablet;

  return {
    deviceCategory: input.deviceCategory,
    executionMode: input.executionMode,
    platformOS: input.platformOS,
    navigationMode: isMobile ? "bottom-nav" : isTablet ? "rail-and-bottom" : "sidebar",
    sheetPresentation: isMobile ? "bottom-sheet" : "centered-dialog",
    density: isTouchDevice ? "touch-comfortable" : "compact",
    isNativeLikeShell: isTouchDevice || input.executionMode === "standalone",
    showInstallBanner: isTouchDevice && input.executionMode === "browser",
  };
}

