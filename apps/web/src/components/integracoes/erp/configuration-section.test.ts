import { expect, test } from "@playwright/test";

import {
  resolveErpConfigurationSectionViewState,
} from "./configuration-section";
import type {
  ConsoleResourceState,
  ErpConsoleConfig,
  ProviderFieldDefinition,
  ProviderSchemaResponse,
} from "./types";

const field: ProviderFieldDefinition = {
  key: "sankhya_api_base_url",
  label: "URL base",
  type: "url",
  required: true,
  secret: false,
  order: 10,
};

const schemaStateSuccess: ConsoleResourceState<ProviderSchemaResponse> = {
  status: "success",
  data: {
    provider: { id: 1, slug: "sankhya", nome: "Sankhya", provider_type: "ERP", ativa: true },
    schema_version: 1,
    connection_schema: {
      schema_version: 1,
      required: ["sankhya_api_base_url"],
      optional: [],
      fields: [field],
    },
    credential_schema: { schema_version: 1, required: [], optional: [], fields: [] },
  },
  message: null,
};

const configNotFoundState: ConsoleResourceState<ErpConsoleConfig> = {
  status: "not_found",
  data: null,
  message: null,
};

test.describe("resolveErpConfigurationSectionViewState", () => {
  test("mostra loading explícito enquanto schema carrega", () => {
    const state = resolveErpConfigurationSectionViewState({
      schemaState: {
        status: "loading",
        data: null,
        message: null,
      },
      configState: configNotFoundState,
      connectionFields: [],
      credentialFields: [],
      hasEditableFields: false,
      saveAllowed: true,
    });

    expect(state.schemaMessage).toBe("loading");
    expect(state.message).toContain("Carregando campos de configuração");
    expect(state.showForm).toBe(false);
    expect(state.showActions).toBe(false);
  });

  test("mostra estado inicial quando config retorna 404 e schema carregou", () => {
    const state = resolveErpConfigurationSectionViewState({
      schemaState: schemaStateSuccess,
      configState: configNotFoundState,
      connectionFields: [field],
      credentialFields: [],
      hasEditableFields: true,
      saveAllowed: true,
    });

    expect(state.schemaMessage).toBe("config_not_found");
    expect(state.message).toContain("ainda não possui configuração salva");
    expect(state.showForm).toBe(true);
    expect(state.showActions).toBe(true);
  });

  test("mostra erro explícito quando schema falha e não habilita ações inválidas", () => {
    const state = resolveErpConfigurationSectionViewState({
      schemaState: {
        status: "error",
        data: null,
        message: "Erro ao carregar schema",
      },
      configState: configNotFoundState,
      connectionFields: [],
      credentialFields: [],
      hasEditableFields: false,
      saveAllowed: true,
    });

    expect(state.schemaMessage).toBe("error");
    expect(state.message).toBe("Não foi possível carregar os campos de configuração deste ERP.");
    expect(state.showForm).toBe(false);
    expect(state.showActions).toBe(false);
  });

  test("mostra mensagem de schema vazio sem exibir formulário vazio", () => {
    const state = resolveErpConfigurationSectionViewState({
      schemaState: {
        status: "empty",
        data: null,
        message: "Este provider não disponibilizou campos de configuração.",
      },
      configState: configNotFoundState,
      connectionFields: [],
      credentialFields: [],
      hasEditableFields: false,
      saveAllowed: true,
    });

    expect(state.schemaMessage).toBe("empty");
    expect(state.message).toBe("Este provider não disponibilizou campos de configuração.");
    expect(state.showForm).toBe(false);
    expect(state.showActions).toBe(false);
    expect(state.hasFields).toBe(false);
  });

  test("schema 403 mostra mensagem específica sem liberar ações", () => {
    const state = resolveErpConfigurationSectionViewState({
      schemaState: {
        status: "forbidden",
        data: null,
        message: "Sem permissão no schema",
      },
      configState: configNotFoundState,
      connectionFields: [],
      credentialFields: [],
      hasEditableFields: false,
      saveAllowed: true,
    });

    expect(state.schemaMessage).toBe("forbidden");
    expect(state.message).toContain("não possui permissão");
    expect(state.showForm).toBe(false);
    expect(state.showActions).toBe(false);
  });

  test("config 403 não é tratada como primeira configuração", () => {
    const state = resolveErpConfigurationSectionViewState({
      schemaState: schemaStateSuccess,
      configState: {
        status: "forbidden",
        data: null,
        message: "Sem permissão",
      },
      connectionFields: [field],
      credentialFields: [],
      hasEditableFields: true,
      saveAllowed: true,
    });

    expect(state.schemaMessage).toBe("config_forbidden");
    expect(state.message).toContain("não possui permissão");
    expect(state.showForm).toBe(true);
  });

  test("config 500 mantém formulário visível e expõe retry explícito", () => {
    const state = resolveErpConfigurationSectionViewState({
      schemaState: schemaStateSuccess,
      configState: {
        status: "error",
        data: {
          id: 10,
          tenant_id: "tenant-1",
          ativo: true,
          sync_interval: 900,
          password_configured: false,
        },
        message: "Falha temporária ao consultar a configuração.",
      },
      connectionFields: [field],
      credentialFields: [],
      hasEditableFields: true,
      saveAllowed: true,
    });

    expect(state.schemaMessage).toBe("config_error");
    expect(state.message).toBe("Falha temporária ao consultar a configuração.");
    expect(state.showForm).toBe(true);
    expect(state.showActions).toBe(true);
  });
});
