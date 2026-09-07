import { test, expect } from "@playwright/test";

import {
  buildInitialProviderFormData,
  getEditableProviderFields,
  getProviderFieldSelectOptions,
  isEditableProviderField,
  normalizeProviderPayloadValue,
} from "./provider-config-fields";
import type { ErpConsoleConfig, ProviderSchemaResponse } from "./types";

const schema: ProviderSchemaResponse = {
  provider: { id: 1, slug: "sankhya", nome: "Sankhya", provider_type: "ERP", ativa: true },
  schema_version: 1,
  connection_schema: {
    schema_version: 1,
    required: ["sankhya_environment", "sankhya_api_base_url", "sync_interval"],
    optional: ["auth_model", "ws_url"],
    fields: [
      {
        key: "sankhya_environment",
        label: "Ambiente Sankhya",
        type: "select",
        required: true,
        secret: false,
        order: 5,
        default: "producao",
        options: [
          { value: "producao", label: "Produção" },
          { value: "homologacao", label: "Homologação" },
          { value: "sandbox", label: "Sandbox" },
        ],
      },
      { key: "sankhya_api_base_url", label: "URL base", type: "url", required: true, secret: false, order: 10 },
      {
        key: "auth_model",
        label: "Modelo de Autenticação",
        type: "select",
        required: false,
        secret: false,
        order: 15,
        default: "gateway_oauth_client_credentials",
        options: [
          { value: "gateway_oauth_client_credentials", label: "OAuth" },
          { value: "gateway_legacy_login", label: "Legacy login" },
          { value: "legacy_ws_basic_auth", label: "Legacy WS Basic Auth (compatibilidade)" },
        ],
      },
      { key: "ws_url", label: "WS URL", type: "url", required: false, secret: false, order: 17 },
      { key: "sync_interval", label: "Intervalo", type: "integer", required: true, secret: false, order: 20, default: 900 },
    ],
  },
  credential_schema: {
    schema_version: 1,
    required: [],
    optional: ["sankhya_token", "password"],
    fields: [
      { key: "sankhya_client_id", label: "Client ID", type: "string", required: false, secret: false, order: 10 },
      { key: "sankhya_token", label: "Token legado", type: "secret", required: false, secret: true, order: 20 },
      { key: "password", label: "Senha", type: "secret", required: false, secret: true, order: 30 },
    ],
  },
};

const config: ErpConsoleConfig = {
  id: 10,
  tenant_id: "tenant-1",
  ativo: true,
  sankhya_environment: "producao",
  sync_interval: 900,
  password_configured: false,
  sankhya_api_base_url: "https://api.sankhya.example",
  sankhya_client_id: "client-123",
  auth_model: "legacy_ws_basic_auth",
};

test.describe("provider-config-fields", () => {
  test("filtra runtime fields e legacy_auth_model da área editável", () => {
    expect(isEditableProviderField(schema.connection_schema!.fields[0])).toBe(true);
    const editable = getEditableProviderFields(schema);
    expect(editable.connectionFields.map((field) => field.key)).toEqual([
      "sankhya_environment",
      "sankhya_api_base_url",
      "auth_model",
      "ws_url",
      "sync_interval",
    ]);
    expect(editable.credentialFields.map((field) => field.key)).toEqual([
      "sankhya_client_id",
      "sankhya_token",
      "password",
    ]);
  });

  test("converte sync_interval persistido em segundos para minutos no form", () => {
    const formData = buildInitialProviderFormData({ schema, config });

    expect(formData.sankhya_environment).toBe("producao");
    expect(formData.sync_interval).toBe(15);
    expect(formData.sankhya_api_base_url).toBe("https://api.sankhya.example");
    expect(formData.sankhya_client_id).toBe("client-123");
    expect(formData.auth_model).toBe("legacy_ws_basic_auth");
  });

  test("preserva sync_interval zero no reload sem multiplicação repetida", () => {
    const formData = buildInitialProviderFormData({
      schema,
      config: {
        ...config,
        sync_interval: 0,
      },
    });

    expect(formData.sync_interval).toBe(0);
  });

  test("normaliza sync_interval de minutos para segundos no payload", () => {
    const field = schema.connection_schema!.fields.find((item) => item.key === "sync_interval")!;
    expect(normalizeProviderPayloadValue(field, 15)).toBe(900);
    expect(normalizeProviderPayloadValue(field, "20")).toBe(1200);
  });

  test("reusa opção do select quando o valor vem em casing diferente", () => {
    const field = schema.connection_schema!.fields[0];
    const options = getProviderFieldSelectOptions(field, "producao");

    expect(options.map((option) => option.value)).toContain("producao");
    expect(buildInitialProviderFormData({ schema, config }).sankhya_environment).toBe("producao");
  });

  test("adiciona fallback visível quando o valor do select não existe no schema", () => {
    const field = schema.connection_schema!.fields[2];
    const options = getProviderFieldSelectOptions(field, "legacy_ws_basic_auth");

    expect(options.some((option) => option.value === "legacy_ws_basic_auth")).toBe(true);
  });
});
