export const DEFAULT_LOCALE = "pt-BR";

/**
 * Parseia números no padrão brasileiro.
 * Aceita "1.234,56", "1234,56" e também payloads técnicos com ponto decimal.
 */
export function parseDecimalBR(value: string | number | null | undefined): number {
  if (typeof value === "number") {
    return value;
  }

  if (value == null) {
    return Number.NaN;
  }

  const normalized = value
    .trim()
    .replace(/\s/g, "")
    .replace(/[^\d,.-]/g, "");

  if (!normalized) {
    return Number.NaN;
  }

  const lastComma = normalized.lastIndexOf(",");
  const lastDot = normalized.lastIndexOf(".");

  if (lastComma === -1 && lastDot !== -1) {
    const dotParts = normalized.split(".");
    const isBrazilianThousands =
      dotParts.length > 2 || dotParts[dotParts.length - 1]?.length === 3;

    return Number.parseFloat(isBrazilianThousands ? dotParts.join("") : normalized);
  }

  const decimalSeparator = lastComma > lastDot ? "," : ".";
  const thousandsSeparator = decimalSeparator === "," ? "." : ",";

  const parsed = normalized
    .replace(new RegExp(`\\${thousandsSeparator}`, "g"), "")
    .replace(decimalSeparator, ".");

  return Number.parseFloat(parsed);
}

export function formatNumberBR(value: number, decimals = 2): string {
  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}
