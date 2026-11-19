import { expect, test } from "@playwright/test";

import { buildOperationalCadastroPayload } from "./propriedades-operational-payload";

test.describe("buildOperationalCadastroPayload", () => {
  test("monta payload somente com unidade_produtiva", () => {
    const payload = buildOperationalCadastroPayload({
      id: "up-1",
      nome: "UP Aurora",
      tipo_propriedade: "fazenda",
      cpf_cnpj: "12345678000101",
      inscricao_estadual: "IE-1",
      area_total_ha: 100,
      area_app_ha: 5,
      area_rl_ha: 10,
      cep: "78890000",
      logradouro: "Estrada Rural",
      numero: "s/n",
      complemento: "Km 12",
      bairro: "Zona Rural",
      municipio: "Sorriso",
      uf: "MT",
      ibge_municipio_codigo: "5107925",
      coordenadas_sede: "-12.34,-55.67",
      geometria: { type: "Point", coordinates: [-55.67, -12.34] },
      ativo: true,
    });

    expect(payload).toEqual({
      unidade_produtiva: {
        id: "up-1",
        nome: "UP Aurora",
        tipo_propriedade: "fazenda",
        cpf_cnpj: "12345678000101",
        inscricao_estadual: "IE-1",
        area_total_ha: 100,
        area_app_ha: 5,
        area_rl_ha: 10,
        cep: "78890000",
        logradouro: "Estrada Rural",
        numero: "s/n",
        complemento: "Km 12",
        bairro: "Zona Rural",
        municipio: "Sorriso",
        uf: "MT",
        ibge_municipio_codigo: "5107925",
        coordenadas_sede: "-12.34,-55.67",
        geometria: { type: "Point", coordinates: [-55.67, -12.34] },
        ativo: true,
      },
    });
  });

  test("não inclui bloco imovel_rural nem propriedade_imovel", () => {
    const payload = buildOperationalCadastroPayload({
      nome: "UP Sem Imóvel",
      tipo_propriedade: "sitio",
      ativo: false,
    }) as Record<string, unknown>;

    expect(payload).toHaveProperty("unidade_produtiva");
    expect(payload).not.toHaveProperty("imovel_rural");
    expect(payload).not.toHaveProperty("propriedade_imovel");
    expect(Object.keys(payload)).toEqual(["unidade_produtiva"]);
  });

  test("normaliza textos vazios e áreas não positivas", () => {
    const payload = buildOperationalCadastroPayload({
      nome: "UP Limpa",
      tipo_propriedade: "chacara",
      cpf_cnpj: "   ",
      inscricao_estadual: "",
      area_total_ha: 0,
      area_app_ha: -1,
      area_rl_ha: 0,
      coordenadas_sede: "   ",
      ativo: true,
    });

    expect(payload).toEqual({
      unidade_produtiva: {
        nome: "UP Limpa",
        tipo_propriedade: "chacara",
        cpf_cnpj: null,
        inscricao_estadual: null,
        area_total_ha: undefined,
        area_app_ha: undefined,
        area_rl_ha: undefined,
        cep: null,
        logradouro: null,
        numero: null,
        complemento: null,
        bairro: null,
        municipio: null,
        uf: null,
        ibge_municipio_codigo: null,
        coordenadas_sede: undefined,
        geometria: undefined,
        ativo: true,
      },
    });
  });

  test("preserva geometria null na edição para limpar polígono salvo", () => {
    const payload = buildOperationalCadastroPayload({
      id: "up-1",
      nome: "UP Sem Polígono",
      tipo_propriedade: "fazenda",
      geometria: null,
      ativo: true,
    });

    expect(payload.unidade_produtiva).toMatchObject({
      id: "up-1",
      nome: "UP Sem Polígono",
      geometria: null,
    });
  });
});
