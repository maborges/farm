import { describe, expect, it } from "vitest";
import {
  detectDeviceCategory,
  detectExecutionMode,
  detectPlatformOS,
  getAdaptiveLayoutProfile,
} from "@/lib/device/device-detection";

describe("device-detection (Módulo Campo)", () => {
  describe("detectDeviceCategory", () => {
    it("identifica mobile quando largura é menor que 768px", () => {
      const category = detectDeviceCategory({
        viewportWidth: 390,
        hasCoarsePointer: true,
        userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
      });
      expect(category).toBe("mobile");
    });

    it("identifica tablet quando largura está entre 768px e 1023px", () => {
      const category = detectDeviceCategory({
        viewportWidth: 820,
        hasCoarsePointer: true,
        userAgent: "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X)",
      });
      expect(category).toBe("tablet");
    });

    it("identifica tablet em iPadOS ou Android Tablet mesmo em landscape >= 1024px com ponteiro coarse", () => {
      const category = detectDeviceCategory({
        viewportWidth: 1180,
        hasCoarsePointer: true,
        userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Mobile/15E148",
      });
      expect(category).toBe("tablet");
    });

    it("identifica desktop quando largura >= 1024px com ponteiro fino", () => {
      const category = detectDeviceCategory({
        viewportWidth: 1440,
        hasCoarsePointer: false,
        userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
      });
      expect(category).toBe("desktop");
    });

    it("trata edge cases de largura zero ou negativa como mobile seguro", () => {
      const category = detectDeviceCategory({
        viewportWidth: 0,
        hasCoarsePointer: false,
        userAgent: "",
      });
      expect(category).toBe("mobile");
    });
  });

  describe("detectExecutionMode", () => {
    it("retorna standalone quando display-mode standalone está ativo", () => {
      const mode = detectExecutionMode({
        isDisplayModeStandalone: true,
        isNavigatorStandalone: false,
      });
      expect(mode).toBe("standalone");
    });

    it("retorna standalone quando navigator.standalone (iOS Safari PWA) é true", () => {
      const mode = detectExecutionMode({
        isDisplayModeStandalone: false,
        isNavigatorStandalone: true,
      });
      expect(mode).toBe("standalone");
    });

    it("retorna browser quando executado em aba comum do navegador", () => {
      const mode = detectExecutionMode({
        isDisplayModeStandalone: false,
        isNavigatorStandalone: false,
      });
      expect(mode).toBe("browser");
    });
  });

  describe("detectPlatformOS", () => {
    it("identifica iOS para iPhone e iPad", () => {
      expect(
        detectPlatformOS("Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)")
      ).toBe("ios");
    });

    it("identifica Android", () => {
      expect(
        detectPlatformOS("Mozilla/5.0 (Linux; Android 14; Pixel 8)")
      ).toBe("android");
    });

    it("identifica other para Linux/Windows/macOS desktop", () => {
      expect(
        detectPlatformOS("Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0")
      ).toBe("other");
    });
  });

  describe("getAdaptiveLayoutProfile", () => {
    it("gera perfil nativo mobile com bottom-nav e bottom-sheet quando em celular", () => {
      const profile = getAdaptiveLayoutProfile({
        deviceCategory: "mobile",
        executionMode: "standalone",
        platformOS: "android",
      });

      expect(profile.navigationMode).toBe("bottom-nav");
      expect(profile.sheetPresentation).toBe("bottom-sheet");
      expect(profile.density).toBe("touch-comfortable");
      expect(profile.isNativeLikeShell).toBe(true);
      expect(profile.showInstallBanner).toBe(false);
    });

    it("habilita banner de instalação quando em mobile ou tablet no modo browser", () => {
      const profile = getAdaptiveLayoutProfile({
        deviceCategory: "mobile",
        executionMode: "browser",
        platformOS: "ios",
      });

      expect(profile.navigationMode).toBe("bottom-nav");
      expect(profile.showInstallBanner).toBe(true);
    });

    it("gera perfil híbrido para tablet com rail lateral e modais centralizados", () => {
      const profile = getAdaptiveLayoutProfile({
        deviceCategory: "tablet",
        executionMode: "standalone",
        platformOS: "ios",
      });

      expect(profile.navigationMode).toBe("rail-and-bottom");
      expect(profile.sheetPresentation).toBe("centered-dialog");
      expect(profile.density).toBe("touch-comfortable");
    });

    it("gera perfil desktop com sidebar retrátil e densidade compacta", () => {
      const profile = getAdaptiveLayoutProfile({
        deviceCategory: "desktop",
        executionMode: "browser",
        platformOS: "other",
      });

      expect(profile.navigationMode).toBe("sidebar");
      expect(profile.sheetPresentation).toBe("centered-dialog");
      expect(profile.density).toBe("compact");
      expect(profile.showInstallBanner).toBe(false);
    });
  });
});

