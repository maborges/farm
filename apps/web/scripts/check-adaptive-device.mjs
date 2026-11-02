import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const deviceDetectionPath = resolve("src/lib/device/device-detection.ts");
const deviceContextPath = resolve("src/lib/device/use-device-context.tsx");
const topbarPath = resolve("src/components/layout/topbar.tsx");
const bottomNavPath = resolve("src/components/layout/mobile-bottom-nav.tsx");
const shellPath = resolve("src/components/layout/adaptive-dashboard-shell.tsx");
const globalsCssPath = resolve("src/app/globals.css");

const [
  deviceDetectionSource,
  deviceContextSource,
  topbarSource,
  bottomNavSource,
  shellSource,
  globalsCssSource,
] = await Promise.all([
  readFile(deviceDetectionPath, "utf8"),
  readFile(deviceContextPath, "utf8"),
  readFile(topbarPath, "utf8"),
  readFile(bottomNavPath, "utf8"),
  readFile(shellPath, "utf8"),
  readFile(globalsCssPath, "utf8"),
]);

const checks = [
  [
    "device-detection exporta detectDeviceCategory, detectExecutionMode, detectPlatformOS e getAdaptiveLayoutProfile",
    () =>
      deviceDetectionSource.includes("export function detectDeviceCategory") &&
      deviceDetectionSource.includes("export function detectExecutionMode") &&
      deviceDetectionSource.includes("export function detectPlatformOS") &&
      deviceDetectionSource.includes("export function getAdaptiveLayoutProfile"),
  ],
  [
    "use-device-context exporta DeviceContextProvider e useDeviceContext",
    () =>
      deviceContextSource.includes("export function DeviceContextProvider") &&
      deviceContextSource.includes("export function useDeviceContext"),
  ],
  [
    "Topbar expõe data-device, data-testid='web-app-header' e badge adaptativo de ambiente",
    () =>
      topbarSource.includes('data-testid="web-app-header"') &&
      topbarSource.includes("data-device={deviceCategory}") &&
      topbarSource.includes('data-testid="header-device-badge"'),
  ],
  [
    "MobileBottomNav implementa dock inferior nativo (mobile-bottom-dock) com safe-area-pb",
    () =>
      bottomNavSource.includes('data-testid="mobile-bottom-dock"') &&
      bottomNavSource.includes("safe-area-pb"),
  ],
  [
    "AdaptiveDashboardShell recolhe automaticamente a sidebar em modo Navigation Rail para tablets",
    () =>
      shellSource.includes('deviceCategory === "tablet"') &&
      shellSource.includes("setOpen(false)") &&
      shellSource.includes("<MobileBottomNav />"),
  ],
  [
    "globals.css unifica os tokens Verde Esmeralda Agro (#006B3D) e utilitários safe-area",
    () =>
      globalsCssSource.includes("--primary: 154 100% 21%;") &&
      globalsCssSource.includes("--background: 140 12% 97%;") &&
      globalsCssSource.includes("--background: 155 30% 6%;") &&
      globalsCssSource.includes(".safe-area-pt") &&
      globalsCssSource.includes(".safe-area-pb"),
  ],
];

for (const [description, check] of checks) {
  assert.equal(check(), true, `Falha no guardrail adaptativo: ${description}`);
}

console.log(`Adaptive UI/UX guardrails passed (${checks.length} checks).`);

