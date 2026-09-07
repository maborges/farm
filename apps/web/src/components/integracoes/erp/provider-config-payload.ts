import type { ProviderSchemaResponse } from "./types";
import {
  getEditableProviderFields,
  normalizeProviderPayloadValue,
} from "./provider-config-fields";

export interface BuildProviderConfigPayloadOptions {
  schema: ProviderSchemaResponse | null;
  formData: Record<string, unknown>;
  initialValues?: Record<string, unknown>;
}

export function buildProviderConfigPayload({
  schema,
  formData,
  initialValues = {},
}: BuildProviderConfigPayloadOptions): Record<string, unknown> {
  if (!schema) {
    return {};
  }

  const payload: Record<string, unknown> = {};
  const { allFields: fields } = getEditableProviderFields(schema);

  for (const field of fields) {
    const key = field.key;
    const value = formData[key];

    // Tratar campos vazios ou omitidos (em conformidade com o comportamento anterior)
    if (value === undefined || value === null || value === "") {
      continue;
    }

    // Tratar campos sensíveis/segredos
    if (field.type === "secret" || field.secret) {
      if (typeof value === "string") {
        if (value.includes("•") || value.includes("*")) {
          // Rejeita máscara genérica
          continue;
        }
      }
      if (initialValues[key] !== undefined && initialValues[key] === value) {
        // Valor não foi alterado desde o load, não reenvia
        continue;
      }
    }

    // Tratar tipos específicos e normalizar
    if (field.type === "integer") {
      const normalizedValue = normalizeProviderPayloadValue(field, value);
      const num = Number(normalizedValue);
      if (!Number.isNaN(num)) {
        payload[key] = num;
      }
    } else if (field.type === "boolean") {
      payload[key] = Boolean(normalizeProviderPayloadValue(field, value));
    } else if (field.type === "string" || field.type === "url" || field.type === "select") {
      const normalizedValue = normalizeProviderPayloadValue(field, value);
      payload[key] =
        typeof normalizedValue === "string"
          ? normalizedValue.trim()
          : String(normalizedValue).trim();
    } else {
      payload[key] = normalizeProviderPayloadValue(field, value);
    }
  }

  return payload;
}
