import { test, expect } from "@playwright/test";
import { buildProviderConfigPayload } from "./provider-config-payload";
import type { ProviderSchemaResponse } from "./types";

test.describe("buildProviderConfigPayload", () => {
  const mockSchema: ProviderSchemaResponse = {
    provider: { id: 1, slug: "fictitious", nome: "Fictitious", provider_type: "ERP", ativa: true },
    schema_version: 1,
    connection_schema: {
      schema_version: 1,
      required: ["api_url"],
      optional: ["auth_model", "ws_url", "interval", "ultimo_sync"],
      fields: [
        { key: "api_url", type: "url", required: true, secret: false, label: "API", order: 1 },
        { key: "auth_model", type: "select", required: false, secret: false, label: "Auth Model", order: 2 },
        { key: "ws_url", type: "url", required: false, secret: false, label: "WS URL", order: 3 },
        { key: "sync_interval", type: "integer", required: false, secret: false, label: "Interval", order: 4 },
        { key: "is_active", type: "boolean", required: false, secret: false, label: "Is Active", order: 5 },
        { key: "ultimo_sync", type: "string", required: false, secret: false, label: "Último sync", order: 6 },
      ]
    },
    credential_schema: {
      schema_version: 1,
      required: ["client_id"],
      optional: ["client_secret", "token", "legacy_auth_model"],
      fields: [
        { key: "client_id", type: "string", required: true, secret: false, label: "Client ID", order: 1 },
        { key: "client_secret", type: "secret", required: false, secret: true, label: "Secret", order: 2 },
        { key: "token", type: "secret", required: false, secret: true, label: "Token", order: 3 },
        { key: "legacy_auth_model", type: "boolean", required: false, secret: false, label: "Legacy auth", order: 4 },
      ]
    }
  };

  test("1. envia campo de connection schema", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { api_url: "https://api.example.com" }
    });
    expect(payload).toEqual({ api_url: "https://api.example.com" });
  });

  test("2. envia campo de credential schema", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { client_id: "my-id" }
    });
    expect(payload).toEqual({ client_id: "my-id" });
  });

  test("3. envia auth_model", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { auth_model: "gateway_legacy_login" }
    });
    expect(payload).toEqual({ auth_model: "gateway_legacy_login" });
  });

  test("4. envia ws_url", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { ws_url: "https://ws.example.com" }
    });
    expect(payload).toEqual({ ws_url: "https://ws.example.com" });
  });

  test("6. envia campo de provider fictício sem prefixo Sankhya", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { api_url: "https://api", auth_model: "test", client_id: "id" }
    });
    expect(payload).toEqual({ api_url: "https://api", auth_model: "test", client_id: "id" });
  });

  test("7. ignora campo extra do formData", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { api_url: "https://api", injected_field: "lixo", "sankhya_algo": 1 }
    });
    expect(payload).toEqual({ api_url: "https://api" });
  });

  test("8. preserva número", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { sync_interval: 60 }
    });
    expect(payload).toEqual({ sync_interval: 3600 });
  });

  test("9. converte minutos para segundos (e preserva 0)", () => {
    const payload1 = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { sync_interval: "120" }
    });
    expect(payload1).toEqual({ sync_interval: 7200 });

    const payload2 = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { sync_interval: "0" }
    });
    expect(payload2).toEqual({ sync_interval: 0 });

    const payload3 = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { sync_interval: "invalid" }
    });
    expect(payload3).toEqual({});
  });

  test("10. preserva boolean", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { is_active: true }
    });
    expect(payload).toEqual({ is_active: true });
  });

  test("11. select envia valor técnico", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { auth_model: "gateway_oauth_client_credentials" }
    });
    expect(payload).toEqual({ auth_model: "gateway_oauth_client_credentials" });
  });

  test("13. secret novo é enviado", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { client_secret: "new_real_secret123!" }
    });
    expect(payload).toEqual({ client_secret: "new_real_secret123!" });
  });

  test("14. secret mascarado não é reenviado", () => {
    const payload1 = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { client_secret: "••••••••" }
    });
    expect(payload1).toEqual({});

    const payload2 = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { token: "********" }
    });
    expect(payload2).toEqual({});
  });

  test("14b. secret mascarado via valor inicial não é reenviado", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { client_secret: "enc::gAAA1234" },
      initialValues: { client_secret: "enc::gAAA1234" }
    });
    expect(payload).toEqual({});
  });

  test("19. schema vazio", () => {
    const payload = buildProviderConfigPayload({
      schema: null,
      formData: { client_secret: "123" }
    });
    expect(payload).toEqual({});
  });
  
  test("20. formData parcial", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { api_url: "url" }
    });
    expect(payload).toEqual({ api_url: "url" });
  });

  test("22. função não conhece sankhya_", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { sankhya_environment: "PROD" }
    });
    expect(payload).toEqual({});
  });

  test("23. ignora runtime fields não editáveis", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { ultimo_sync: "2026-07-14T10:00:00Z" }
    });
    expect(payload).toEqual({});
  });

  test("24. ignora legacy_auth_model sem persistência real", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { legacy_auth_model: true }
    });
    expect(payload).toEqual({});
  });

  test("25. não multiplica sync_interval repetidamente após reload do form", () => {
    const payload = buildProviderConfigPayload({
      schema: mockSchema,
      formData: { sync_interval: 15 },
      initialValues: { sync_interval: 900 },
    });
    expect(payload).toEqual({ sync_interval: 900 });
  });

});
