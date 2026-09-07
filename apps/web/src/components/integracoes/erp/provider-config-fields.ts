import type {
  ErpConsoleConfig,
  ProviderFieldDefinition,
  ProviderFieldSelectOption,
  ProviderSchemaResponse,
} from "./types";

const RUNTIME_ONLY_FIELD_KEYS = new Set(["ultimo_teste", "teste_status", "ultimo_sync"]);
const UNSUPPORTED_EDITABLE_FIELD_KEYS = new Set(["legacy_auth_model"]);
const SYNC_INTERVAL_FIELD_KEY = "sync_interval";
const DEFAULT_SYNC_INTERVAL_SECONDS = 900;

function toArray<T>(value: T[] | null | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

function toHumanSyncIntervalMinutes(value: unknown): number {
  const numericValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numericValue)) {
    return Math.round(DEFAULT_SYNC_INTERVAL_SECONDS / 60);
  }
  return Math.max(0, Math.round(numericValue / 60));
}

function toComparableString(value: unknown): string {
  return String(value).trim().toLowerCase();
}

function normalizeSelectFieldValue(
  field: ProviderFieldDefinition,
  rawValue: unknown,
): unknown {
  const options = toArray(field.options);
  if (options.length === 0 || rawValue === undefined || rawValue === null || rawValue === "") {
    return rawValue;
  }

  const exactMatch = options.find((option) => String(option.value) === String(rawValue));
  if (exactMatch) {
    return exactMatch.value;
  }

  if (typeof rawValue === "string") {
    const caseInsensitiveMatch = options.find(
      (option) => toComparableString(option.value) === toComparableString(rawValue),
    );
    if (caseInsensitiveMatch) {
      return caseInsensitiveMatch.value;
    }
  }

  return rawValue;
}

export function isRuntimeOnlyProviderField(field: ProviderFieldDefinition): boolean {
  return RUNTIME_ONLY_FIELD_KEYS.has(field.key);
}

export function isEditableProviderField(field: ProviderFieldDefinition): boolean {
  if (isRuntimeOnlyProviderField(field)) {
    return false;
  }
  if (UNSUPPORTED_EDITABLE_FIELD_KEYS.has(field.key)) {
    return false;
  }
  return true;
}

export function getEditableProviderFields(schema: ProviderSchemaResponse | null): {
  connectionFields: ProviderFieldDefinition[];
  credentialFields: ProviderFieldDefinition[];
  allFields: ProviderFieldDefinition[];
} {
  const connectionFields = toArray(schema?.connection_schema?.fields).filter(isEditableProviderField);
  const credentialFields = toArray(schema?.credential_schema?.fields).filter(isEditableProviderField);

  return {
    connectionFields,
    credentialFields,
    allFields: [...connectionFields, ...credentialFields],
  };
}

export function getDisplayValueForProviderField(
  field: ProviderFieldDefinition,
  rawValue: unknown,
): string | number | boolean {
  if (field.key === SYNC_INTERVAL_FIELD_KEY) {
    return toHumanSyncIntervalMinutes(rawValue);
  }
  if (field.type === "select") {
    return normalizeSelectFieldValue(field, rawValue) as string | number | boolean;
  }
  if (rawValue === undefined || rawValue === null) {
    return field.type === "boolean" ? false : "";
  }
  if (field.type === "boolean") {
    return Boolean(rawValue);
  }
  return rawValue as string | number;
}

export function buildInitialProviderFormData(params: {
  schema: ProviderSchemaResponse | null;
  config: ErpConsoleConfig | null;
}): Record<string, unknown> {
  const { schema, config } = params;
  const { allFields } = getEditableProviderFields(schema);
  const initialForm: Record<string, unknown> = {};
  const configRecord = config;

  for (const field of allFields) {
    const configValue = configRecord ? configRecord[field.key] : undefined;
    if (configValue !== undefined) {
      initialForm[field.key] = getDisplayValueForProviderField(field, configValue);
      continue;
    }
    if (field.default !== undefined && field.default !== null) {
      initialForm[field.key] = getDisplayValueForProviderField(field, field.default);
      continue;
    }
    initialForm[field.key] = field.type === "boolean" ? false : "";
  }

  return initialForm;
}

export function normalizeProviderPayloadValue(
  field: ProviderFieldDefinition,
  value: unknown,
): unknown {
  if (field.key === SYNC_INTERVAL_FIELD_KEY) {
    const minutes = Number(value);
    if (!Number.isFinite(minutes)) {
      return value;
    }
    return Math.max(0, Math.round(minutes * 60));
  }
  return value;
}

export function normalizeProviderDisplayValue(
  field: ProviderFieldDefinition,
  value: unknown,
): unknown {
  return getDisplayValueForProviderField(field, value);
}

export function getProviderFieldSelectOptions(
  field: ProviderFieldDefinition,
  currentValue: unknown,
): ProviderFieldSelectOption[] {
  const options = [...toArray(field.options)];
  if (currentValue === undefined || currentValue === null || currentValue === "") {
    return options;
  }

  const currentValueString = String(currentValue);
  const hasCurrentValue = options.some((option) => String(option.value) === currentValueString);
  if (!hasCurrentValue) {
    options.push({
      value: currentValueString,
      label: currentValueString,
    });
  }

  return options;
}
