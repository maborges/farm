import { describe, expect, it } from "vitest";
import {
  detectDeviceCategory,
  detectExecutionMode,
  detectPlatformOS,
  getAdaptiveLayoutProfile,
} from "@/lib/device/device-detection";

describe("Detecção Adaptativa de Dispositivo e Ambiente (PWA Agro)", () => {
  describe("detectDeviceCategory", () => {
    it("identifica celulares (mobile) em viewports menores que 768px", () => {
      expect(
        detectDeviceCategory({
          width: 375,
          height: 667,
          isTouch: true,
          userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
          maxTouchPoints: 5,
        })
      ).toBe("mobile");

      expect(
        detectDeviceCategory({
          width: 412,
          height: 915,
          isTouch: true,
          userAgent: "Mozilla/5.0 (Linux; Android 14; Pixel 8) Mobile",
          maxTouchPoints: 5,
        })
      ).toBe("mobile");
    });

    it("identifica tablets em viewports intermediárias (768px a 1023px)", () => {
      expect(
        detectDeviceCategory({
          width: 768,
          height: 1024,
          isTouch: true,
          userAgent: "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X)",
          maxTouchPoints: 5,
        })
      ).toBe("tablet");

      expect(
        detectDeviceCategory({
          width: 820,
          height: 1180,
          isTouch: false,
          userAgent: "Mozilla/5.0 (X11; Linux x86_64)",
          maxTouchPoints: 0,
        })
      ).toBe("tablet");
    });

    it("identifica iPadOS com User-Agent desktop (MacIntel + maxTouchPoints > 1) como tablet mesmo em 1024px-1180px", () => {
      expect(
        detectDeviceCategory({
          width: 1024,
          height: 1366,
          isTouch: true,
          userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
          platform: "MacIntel",
          maxTouchPoints: 5,
        })
      ).toBe("tablet");
    });

    it("identifica desktop em viewports >= 1024px sem assinatura de tablet", () => {
      expect(
        detectDeviceCategory({
          width: 1280,
          height: 800,
          isTouch: false,
          userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
          maxTouchPoints: 0,
        })
      ).toBe("desktop");

      expect(
        detectDeviceCategory({
          width: 1920,
          height: 1080,
          isTouch: false,
          userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
          maxTouchPoints: 0,
        })
      ).toBe("desktop");
    });

    it("trata valores inválidos ou zero com fallback seguro para mobile ou desktop", () => {
      expect(
        detectDeviceCategory({
          width: 0,
          height: 0,
          isTouch: false,
          userAgent: "",
          maxTouchPoints: 0,
        })
      ).toBe("desktop");

      expect(
        detectDeviceCategory({
          width: -100,
          height: 500,
          isTouch: true,
          userAgent: "iPhone",
          maxTouchPoints: 5,
        })
      ).toBe("mobile");
    });
  });

  describe("detectExecutionMode", () => {
    it("retorna standalone quando display-mode standalone está ativo", () => {
      expect(detectExecutionMode(true, false)).toBe("standalone");
    });

    it("retorna standalone quando navigator.standalone do iOS está ativo", () => {
      expect(detectExecutionMode(false, true)).toBe("standalone");
    });

    it("retorna browser quando executado em aba comum do navegador", () => {
      expect(detectExecutionMode(false, false)).toBe("browser");
    });
  });

  describe("detectPlatformOS", () => {
    it("identifica iOS e iPadOS corretamente", () => {
      expect(detectPlatformOS("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)", "iPhone", 5)).toBe("ios");
      expect(detectPlatformOS("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)", "MacIntel", 5)).toBe("ios");
    });

    it("identifica Android corretamente", () => {
      expect(detectPlatformOS("Mozilla/5.0 (Linux; Android 14; SM-S918B)", "Linux armv8l", 5)).toBe("android");
    });

    it("retorna other para sistemas desktop tradicionais", () => {
      expect(detectPlatformOS("Mozilla/5.0 (X11; Linux x86_64)", "Linux x86_64", 0)).toBe("other");
    });
  });

  describe("getAdaptiveLayoutProfile", () => {
    it("configura perfil mobile com bottom-dock, bottom-sheet e inputs otimizados para toque", () => {
      const profile = getAdaptiveLayoutProfile({
        deviceCategory: "mobile",
        executionMode: "standalone",
        platformOS: "ios",
        isTouch: true,
        isPortrait: true,
      });

      expect(profile.navigationPattern).toBe("bottom-dock");
      expect(profile.sheetPresentation).toBe("bottom-sheet");
      expect(profile.compactHeader).toBe(true);
      expect(profile.touchOptimizedInputs).toBe(true);
      expect(profile.showSidebar).toBe(false);
    });

    it("configura perfil tablet com navigation-rail retrátil e inputs otimizados para toque", () => {
      const profile = getAdaptiveLayoutProfile({
        deviceCategory: "tablet",
        executionMode: "browser",
        platformOS: "android",
        isTouch: true,
        isPortrait: false,
      });

      expect(profile.navigationPattern).toBe("navigation-rail");
      expect(profile.sheetPresentation).toBe("centered-dialog");
      expect(profile.compactHeader).toBe(false);
      expect(profile.touchOptimizedInputs).toBe(true);
      expect(profile.showSidebar).toBe(true);
    });

    it("configura perfil desktop com sidebar-and-topbar retrátil", () => {
      const profile = getAdaptiveLayoutProfile({
        deviceCategory: "desktop",
        executionMode: "browser",
        platformOS: "other",
        isTouch: false,
        isPortrait: false,
      });

      expect(profile.navigationPattern).toBe("sidebar-and-topbar");
      expect(profile.sheetPresentation).toBe("centered-dialog");
      expect(profile.compactHeader).toBe(false);
      expect(profile.touchOptimizedInputs).toBe(false);
      expect(profile.showSidebar).toBe(true);
    });
  });
});

