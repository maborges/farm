import { test, expect } from "@playwright/test";

import { resolveProviderConsoleEndpoints } from "./provider-console-endpoints";

test.describe("resolveProviderConsoleEndpoints", () => {
  test("usa getConfig no GET e saveConfig no POST quando são distintos", () => {
    const endpoints = resolveProviderConsoleEndpoints("erp_exemplo", {
      getConfig: "/integracoes/erp-exemplo/config-read",
      saveConfig: "/integracoes/erp-exemplo/config-write",
      removeConfig: "/integracoes/erp-exemplo/config-delete",
      testConnection: "/integracoes/erp-exemplo/test",
      getLogs: "/integracoes/erp-exemplo/logs",
      sync: (tipo) => `/integracoes/erp-exemplo/sync/${tipo}`,
    });

    expect(endpoints.getConfig).toBe("/integracoes/erp-exemplo/config-read");
    expect(endpoints.saveConfig).toBe("/integracoes/erp-exemplo/config-write");
    expect(endpoints.removeConfig).toBe("/integracoes/erp-exemplo/config-delete");
    expect(endpoints.testConnection).toBe("/integracoes/erp-exemplo/test");
    expect(endpoints.sync("pessoas")).toBe("/integracoes/erp-exemplo/sync/pessoas");
  });

  test("faz fallback seguro para saveConfig quando apenas getConfig é informado", () => {
    const endpoints = resolveProviderConsoleEndpoints("sankhya", {
      getConfig: "/integracoes/sankhya/config",
    });

    expect(endpoints.getConfig).toBe("/integracoes/sankhya/config");
    expect(endpoints.saveConfig).toBe("/integracoes/sankhya/config");
    expect(endpoints.removeConfig).toBe("/integracoes/sankhya/config");
  });
});
