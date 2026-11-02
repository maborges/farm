import { describe, expect, it } from "vitest";
import {
  getContractedCampoModuleGroups,
  isCampoRouteActive,
  resolveCampoRouteMeta,
} from "@/components/campo/nav-items";

describe("nav-items (Módulo Campo)", () => {
  describe("isCampoRouteActive", () => {
    it("identifica rota exata ou sub-rota", () => {
      expect(isCampoRouteActive("/home", "/home")).toBe(true);
      expect(isCampoRouteActive("/tarefas", "/home")).toBe(false);
      expect(isCampoRouteActive("/campo/tarefa/123", "/tarefas")).toBe(true);
      expect(isCampoRouteActive("/campo/aplicacao", "/agricultura")).toBe(true);
      expect(isCampoRouteActive("/campo/pesagem", "/pecuaria")).toBe(true);
    });
  });

  describe("getContractedCampoModuleGroups", () => {
    it("retorna apenas o módulo contratado além da operação base", () => {
      const onlyAgro = getContractedCampoModuleGroups(["agricola"]);
      expect(onlyAgro.map((g) => g.id)).toEqual(["operacao-campo", "modulo-agricola"]);

      const onlyPecuaria = getContractedCampoModuleGroups(["pecuaria"]);
      expect(onlyPecuaria.map((g) => g.id)).toEqual(["operacao-campo", "modulo-pecuaria"]);
    });

    it("retorna ambos os módulos quando ambos estão contratados ou não restritos", () => {
      const both = getContractedCampoModuleGroups(["agricola", "pecuaria"]);
      expect(both.map((g) => g.id)).toEqual([
        "operacao-campo",
        "modulo-agricola",
        "modulo-pecuaria",
      ]);
    });
  });

  describe("resolveCampoRouteMeta", () => {
    it("marca /home como rota raiz sem botão voltar", () => {
      const meta = resolveCampoRouteMeta("/home");
      expect(meta.isRoot).toBe(true);
      expect(meta.title).toBe("Início Operacional");
    });

    it("resolve metadados contextuais para sub-rotas do campo", () => {
      const agroMeta = resolveCampoRouteMeta("/agricultura");
      expect(agroMeta.isRoot).toBe(false);
      expect(agroMeta.title).toBe("Agricultura");
      expect(agroMeta.backHref).toBe("/home");

      const pesagemMeta = resolveCampoRouteMeta("/campo/pesagem");
      expect(pesagemMeta.isRoot).toBe(false);
      expect(pesagemMeta.title).toBe("Pesagem de Rebanho");
      expect(pesagemMeta.backHref).toBe("/pecuaria");
    });
  });
});

