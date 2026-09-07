import { expect, test } from "@playwright/test";

import { buildLinkedImoveisViewModel } from "./imoveis-vinculados-view-model";

test.describe("buildLinkedImoveisViewModel", () => {
  test("suporta múltiplos imóveis sem principal sem escolher arbitrariamente", () => {
    const model = buildLinkedImoveisViewModel(undefined, {
      propriedade: { id: "prop-1", nome: "UP Aurora", ativo: true },
      areas_operacionais: [],
      exploracoes_rurais: [],
      imoveis_rurais: [],
      vinculos: [
        {
          id: "v1",
          tenant_id: "t1",
          tipo_vinculo: "ARRENDAMENTO",
          ativo: true,
          data_inicio: "2026-01-01",
          vinculo_principal: false,
          origem_documental: "Contrato",
          status_documental: "VALIDO",
          imovel_rural: {
            id: "im-1",
            tenant_id: "t1",
            nome: "Imóvel A",
            municipio: "Sorriso",
            uf: "MT",
            area_total_ha: 100,
            documentos_resumo: [],
            matriculas_resumo: [],
          },
        },
        {
          id: "v2",
          tenant_id: "t1",
          tipo_vinculo: "POSSE",
          ativo: true,
          data_inicio: "2026-01-02",
          vinculo_principal: false,
          origem_documental: "Termo",
          status_documental: "PENDENTE",
          imovel_rural: {
            id: "im-2",
            tenant_id: "t1",
            nome: "Imóvel B",
            municipio: "Lucas do Rio Verde",
            uf: "MT",
            area_total_ha: 80,
            documentos_resumo: [],
            matriculas_resumo: [],
          },
        },
      ],
    });

    expect(model.items.map((item) => item.id)).toEqual(["im-1", "im-2"]);
    expect(model.hasPrincipal).toBeFalsy();
    expect(model.hasAmbiguity).toBeTruthy();
  });

  test("prioriza visão territorial sobre overlay legado", () => {
    const model = buildLinkedImoveisViewModel(
      {
        unidade_produtiva_id: "up-legacy-1",
        exploracoes_rurais: [],
        propriedades: [],
        imovel_principal: {
          id: "legacy-1",
          nome: "Legado",
          nirf: "NIRF-LEG",
          car_numero: "CAR-LEG",
          numero_matricula: "MAT-LEG",
          area_total_ha: "50",
        },
        imoveis_secundarios: [],
        associacoes: [],
        fonte_da_leitura: "legacy",
        estado_de_convergencia: "LEGACY",
        avisos: [],
      },
      {
        propriedade: { id: "prop-1", nome: "UP Aurora", ativo: true },
        areas_operacionais: [],
        exploracoes_rurais: [],
        imoveis_rurais: [],
        vinculos: [
          {
            id: "v1",
            tenant_id: "t1",
            tipo_vinculo: "PROPRIEDADE",
            ativo: true,
            data_inicio: "2026-01-01",
            vinculo_principal: true,
            origem_documental: "Matrícula",
            status_documental: "VALIDO",
            imovel_rural: {
              id: "canon-1",
              tenant_id: "t1",
              nome: "Canônico",
              municipio: "Sorriso",
              uf: "MT",
              area_total_ha: 120,
              documentos_resumo: [],
              matriculas_resumo: [],
            },
          },
        ],
      },
    );

    expect(model.items).toHaveLength(1);
    expect(model.items[0]?.id).toBe("canon-1");
    expect(model.items[0]?.principal).toBeTruthy();
    expect(model.hasAmbiguity).toBeFalsy();
  });

  test("retorna zero imóveis quando não há vínculos", () => {
    const model = buildLinkedImoveisViewModel(null, null);
    expect(model.items).toEqual([]);
    expect(model.hasPrincipal).toBeFalsy();
    expect(model.hasAmbiguity).toBeFalsy();
  });
});
