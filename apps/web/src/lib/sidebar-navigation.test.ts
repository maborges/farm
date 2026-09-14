import { test, expect } from "@playwright/test";
import {
  resolveMostSpecificMatch,
  getActiveSectionFromPath,
  getActiveBackofficeSectionFromPath,
  isItemActive,
  resolveToggle,
  getSidebarModuleFromPath,
  type ToggleState,
} from "./sidebar-navigation";

// ─── resolveMostSpecificMatch ────────────────────────────────────────────────

test.describe("resolveMostSpecificMatch", () => {
  test("selects the most specific candidate by segment count", () => {
    const candidates = [
      { href: "/agricola", key: "safras" },
      { href: "/agricola/operacoes", key: "execucao" },
      { href: "/agricola/safras", key: "safras-painel" },
    ];
    const result = resolveMostSpecificMatch(
      "/agricola/operacoes",
      new URLSearchParams(),
      candidates
    );
    expect(result).toBe("execucao");
  });

  test("/agricola does NOT capture /agricola/operacoes", () => {
    const candidates = [
      { href: "/agricola", key: "painel" },
      { href: "/agricola/operacoes", key: "execucao" },
    ];
    const result = resolveMostSpecificMatch(
      "/agricola/operacoes",
      new URLSearchParams(),
      candidates
    );
    expect(result).toBe("execucao");
  });

  test("falls back to base route when no specific match", () => {
    const candidates = [
      { href: "/agricola", key: "painel" },
      { href: "/agricola/operacoes", key: "execucao" },
    ];
    const result = resolveMostSpecificMatch(
      "/agricola",
      new URLSearchParams(),
      candidates
    );
    expect(result).toBe("painel");
  });

  test("handles query string candidates correctly", () => {
    const candidates = [
      { href: "/agricola/safras?redirect=planejamento-operacional", key: "planejamento" },
      { href: "/agricola/safras?redirect=orcamento", key: "orcamento" },
      { href: "/agricola/safras", key: "safras" },
    ];

    const planResult = resolveMostSpecificMatch(
      "/agricola/safras",
      new URLSearchParams("redirect=planejamento-operacional"),
      candidates
    );
    expect(planResult).toBe("planejamento");

    const orcResult = resolveMostSpecificMatch(
      "/agricola/safras",
      new URLSearchParams("redirect=orcamento"),
      candidates
    );
    expect(orcResult).toBe("orcamento");
  });

  test("query candidate without matching params is skipped", () => {
    const candidates = [
      { href: "/agricola/safras?redirect=orcamento", key: "orcamento" },
      { href: "/agricola/safras", key: "safras" },
    ];
    const result = resolveMostSpecificMatch(
      "/agricola/safras",
      new URLSearchParams("redirect=planejamento-operacional"),
      candidates
    );
    expect(result).toBe("safras");
  });

  test("returns null when no candidate matches", () => {
    const candidates = [
      { href: "/financeiro", key: "fin" },
    ];
    const result = resolveMostSpecificMatch(
      "/agricola/operacoes",
      new URLSearchParams(),
      candidates
    );
    expect(result).toBeNull();
  });

  test("does not match partial segment names", () => {
    const candidates = [
      { href: "/agricola", key: "ag" },
    ];
    const result = resolveMostSpecificMatch(
      "/agricola-xyz",
      new URLSearchParams(),
      candidates
    );
    expect(result).toBeNull();
  });

  test("handles dynamic route subroutes", () => {
    const candidates = [
      { href: "/agricola/safras", key: "safras" },
      { href: "/agricola/operacoes", key: "execucao" },
    ];
    const result = resolveMostSpecificMatch(
      "/agricola/safras/abc123-uuid/tarefas",
      new URLSearchParams(),
      candidates
    );
    expect(result).toBe("safras");
  });
});

// ─── getActiveSectionFromPath ────────────────────────────────────────────────

test.describe("getActiveSectionFromPath", () => {
  test("Frota: /dashboard/operacional/manutencoes keeps O1-FROTA active", () => {
    expect(getSidebarModuleFromPath("/dashboard/operacional/manutencoes")).toBe("O1-FROTA");
    expect(getActiveSectionFromPath("O1-FROTA", "/dashboard/operacional/manutencoes", new URLSearchParams())).toBe("O1-manutencao");
  });

  test("Agricultura: /agricola/operacoes activates A1-execucao, NOT A1-visao-geral", () => {
    const result = getActiveSectionFromPath(
      "A1",
      "/agricola/operacoes",
      new URLSearchParams()
    );
    expect(result).toBe("A1-execucao");
  });

  test("Agricultura: /agricola activates A1-visao-geral", () => {
    const result = getActiveSectionFromPath(
      "A1",
      "/agricola",
      new URLSearchParams()
    );
    expect(result).toBe("A1-visao-geral");
  });

  test("Agricultura: /agricola/safras activates A1-visao-geral", () => {
    const result = getActiveSectionFromPath(
      "A1",
      "/agricola/safras",
      new URLSearchParams()
    );
    expect(result).toBe("A1-visao-geral");
  });

  test("Agricultura: query string planejamento activates A1-planejamento", () => {
    const result = getActiveSectionFromPath(
      "A1",
      "/agricola/safras",
      new URLSearchParams("redirect=planejamento-operacional")
    );
    expect(result).toBe("A1-planejamento");
  });

  test("Agricultura: query string orcamento activates A1-planejamento", () => {
    const result = getActiveSectionFromPath(
      "A1",
      "/agricola/safras",
      new URLSearchParams("redirect=orcamento")
    );
    expect(result).toBe("A1-planejamento");
  });

  test("Agricultura: /agricola/caderno activates A1-execucao", () => {
    const result = getActiveSectionFromPath(
      "A1",
      "/agricola/caderno",
      new URLSearchParams()
    );
    expect(result).toBe("A1-execucao");
  });

  test("Agricultura: /agricola/romaneios activates A1-colheita", () => {
    const result = getActiveSectionFromPath(
      "A1",
      "/agricola/romaneios",
      new URLSearchParams()
    );
    expect(result).toBe("A1-colheita");
  });

  test("Agricultura: /dashboard/agricola/rentabilidade activates A1-resultados", () => {
    const result = getActiveSectionFromPath(
      "A1",
      "/dashboard/agricola/rentabilidade",
      new URLSearchParams()
    );
    expect(result).toBe("A1-resultados");
  });

  test("Financeiro: /dashboard/financeiro/despesas activates F1-despesas", () => {
    const result = getActiveSectionFromPath(
      "F1",
      "/dashboard/financeiro/despesas",
      new URLSearchParams()
    );
    expect(result).toBe("F1-despesas");
  });

  test("Financeiro: /dashboard/financeiro activates F1-dashboard", () => {
    const result = getActiveSectionFromPath(
      "F1",
      "/dashboard/financeiro",
      new URLSearchParams()
    );
    expect(result).toBe("F1-dashboard");
  });

  test("Financeiro: /dashboard/financeiro/hedge/contratos activates F1-hedge", () => {
    const result = getActiveSectionFromPath(
      "F1",
      "/dashboard/financeiro/hedge/contratos",
      new URLSearchParams()
    );
    expect(result).toBe("F1-hedge");
  });

  test("Pecuária: /dashboard/pecuaria/animais activates P1-rebanho", () => {
    const result = getActiveSectionFromPath(
      "P1",
      "/dashboard/pecuaria/animais",
      new URLSearchParams()
    );
    expect(result).toBe("P1-rebanho");
  });

  test("Suprimentos: /suprimentos/compras activates O1-compras", () => {
    const result = getActiveSectionFromPath(
      "O1",
      "/suprimentos/compras",
      new URLSearchParams()
    );
    expect(result).toBe("O1-compras");
  });

  test("Suprimentos: /suprimentos/saldos activates O1-estoque", () => {
    const result = getActiveSectionFromPath(
      "O1",
      "/suprimentos/saldos",
      new URLSearchParams()
    );
    expect(result).toBe("O1-estoque");
  });

  test("Ambiental: /dashboard/ambiental/car/lista activates AM1-car", () => {
    const result = getActiveSectionFromPath(
      "AM1",
      "/dashboard/ambiental/car/lista",
      new URLSearchParams()
    );
    expect(result).toBe("AM1-car");
  });

  test("IA: /dashboard/ia/performance activates IA-performance", () => {
    const result = getActiveSectionFromPath(
      "IA1",
      "/dashboard/ia/performance",
      new URLSearchParams()
    );
    expect(result).toBe("IA-performance");
  });

  test("returns empty for unknown module", () => {
    const result = getActiveSectionFromPath(
      "NONEXISTENT",
      "/something",
      new URLSearchParams()
    );
    expect(result).toBe("");
  });

  test("dynamic route: /agricola/safras/<uuid>/tarefas activates A1-visao-geral", () => {
    const result = getActiveSectionFromPath(
      "A1",
      "/agricola/safras/550e8400-e29b-41d4-a716-446655440000/tarefas",
      new URLSearchParams()
    );
    expect(result).toBe("A1-visao-geral");
  });
});

test.describe("isItemActive", () => {
  test("does not activate a parent route when exact is requested", () => {
    expect(isItemActive("/dashboard/operacional/frota", "/dashboard/operacional/frota/consumo", new URLSearchParams(), true)).toBe(false);
  });
});

// ─── getActiveBackofficeSectionFromPath ──────────────────────────────────────

test.describe("getActiveBackofficeSectionFromPath", () => {
  test("resolves backoffice dashboard section", () => {
    const result = getActiveBackofficeSectionFromPath(
      "/dashboard/backoffice/dashboard"
    );
    expect(result).toBe("backoffice-visao");
  });

  test("resolves backoffice comercial section", () => {
    const result = getActiveBackofficeSectionFromPath(
      "/dashboard/backoffice/assinantes"
    );
    expect(result).toBe("backoffice-comercial");
  });

  test("returns null for non-backoffice path", () => {
    const result = getActiveBackofficeSectionFromPath("/agricola");
    expect(result).toBeNull();
  });
});

// ─── isItemActive ────────────────────────────────────────────────────────────

test.describe("isItemActive", () => {
  test("exact match", () => {
    expect(
      isItemActive("/agricola/operacoes", "/agricola/operacoes", new URLSearchParams())
    ).toBe(true);
  });

  test("does not match different path", () => {
    expect(
      isItemActive("/agricola/operacoes", "/agricola/safras", new URLSearchParams())
    ).toBe(false);
  });

  test("dynamic route child matches parent", () => {
    expect(
      isItemActive(
        "/agricola/safras",
        "/agricola/safras/abc-uuid-123/tarefas",
        new URLSearchParams()
      )
    ).toBe(true);
  });

  test("does not match partial segment", () => {
    expect(
      isItemActive("/agricola", "/agricola-xyz", new URLSearchParams())
    ).toBe(false);
  });

  test("query string match: planejamento", () => {
    expect(
      isItemActive(
        "/agricola/safras?redirect=planejamento-operacional",
        "/agricola/safras",
        new URLSearchParams("redirect=planejamento-operacional")
      )
    ).toBe(true);
  });

  test("query string mismatch: expects planejamento, gets orcamento", () => {
    expect(
      isItemActive(
        "/agricola/safras?redirect=planejamento-operacional",
        "/agricola/safras",
        new URLSearchParams("redirect=orcamento")
      )
    ).toBe(false);
  });

  test("query string match: orcamento", () => {
    expect(
      isItemActive(
        "/agricola/safras?redirect=orcamento",
        "/agricola/safras",
        new URLSearchParams("redirect=orcamento")
      )
    ).toBe(true);
  });

  test("item without query matches pathname even with query in URL", () => {
    expect(
      isItemActive(
        "/agricola/safras",
        "/agricola/safras",
        new URLSearchParams("redirect=orcamento")
      )
    ).toBe(true);
  });

  test("root path does not match everything", () => {
    expect(
      isItemActive("/", "/agricola/safras", new URLSearchParams())
    ).toBe(false);
  });
});

// ─── resolveToggle ───────────────────────────────────────────────────────────

test.describe("resolveToggle", () => {
  test("closed always returns false", () => {
    expect(resolveToggle("closed", true)).toBe(false);
    expect(resolveToggle("closed", false)).toBe(false);
  });

  test("open always returns true", () => {
    expect(resolveToggle("open", true)).toBe(true);
    expect(resolveToggle("open", false)).toBe(true);
  });

  test("auto returns route match result", () => {
    expect(resolveToggle("auto", true)).toBe(true);
    expect(resolveToggle("auto", false)).toBe(false);
  });

  test("undefined defaults to auto", () => {
    expect(resolveToggle(undefined, true)).toBe(true);
    expect(resolveToggle(undefined, false)).toBe(false);
  });
});

// ─── getSidebarModuleFromPath ────────────────────────────────────────────────

test.describe("getSidebarModuleFromPath", () => {
  test("resolves agricultura from /agricola", () => {
    expect(getSidebarModuleFromPath("/agricola")).toBe("A1");
  });

  test("resolves agricultura from /agricola/operacoes", () => {
    expect(getSidebarModuleFromPath("/agricola/operacoes")).toBe("A1");
  });

  test("resolves financeiro", () => {
    expect(getSidebarModuleFromPath("/dashboard/financeiro")).toBe("F1");
  });

  test("resolves financeiro subroute", () => {
    expect(getSidebarModuleFromPath("/dashboard/financeiro/despesas")).toBe("F1");
  });

  test("resolves cadastros", () => {
    expect(getSidebarModuleFromPath("/cadastros/propriedades")).toBe("CADASTROS");
  });

  test("resolves imoveis before generic cadastros", () => {
    expect(getSidebarModuleFromPath("/cadastros/imoveis")).toBe("I1");
  });

  test("resolves suprimentos", () => {
    expect(getSidebarModuleFromPath("/suprimentos")).toBe("O1");
  });

  test("resolves pecuaria", () => {
    expect(getSidebarModuleFromPath("/dashboard/pecuaria/animais")).toBe("P1");
  });

  test("resolves RH seguranca before generic RH", () => {
    expect(getSidebarModuleFromPath("/dashboard/rh/seguranca")).toBe("RH2");
  });

  test("resolves generic RH", () => {
    expect(getSidebarModuleFromPath("/dashboard/rh/colaboradores")).toBe("RH");
  });

  test("resolves ambiental", () => {
    expect(getSidebarModuleFromPath("/dashboard/ambiental")).toBe("AM1");
  });

  test("resolves IA", () => {
    expect(getSidebarModuleFromPath("/dashboard/ia")).toBe("IA1");
  });

  test("resolves campo", () => {
    expect(getSidebarModuleFromPath("/dashboard/operacional/campo/dispositivos")).toBe("CAMPO");
  });

  test("returns empty for unknown path", () => {
    expect(getSidebarModuleFromPath("/dashboard")).toBe("");
  });

  test("context change: Agricultura → Financeiro", () => {
    const agModule = getSidebarModuleFromPath("/agricola/operacoes");
    const finModule = getSidebarModuleFromPath("/dashboard/financeiro");
    expect(agModule).toBe("A1");
    expect(finModule).toBe("F1");
    expect(agModule).not.toBe(finModule);
  });
});
