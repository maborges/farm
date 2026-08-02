/**
 * Utilitários de formatação de valores para o PWA Campo.
 * Todos os formatadores usam locale pt-BR por padrão.
 */

const PT_BR = "pt-BR";

/**
 * Formata um número inteiro ou decimal no locale pt-BR.
 * Ex: 1000 → "1.000"  |  1234.56 → "1.234,56"
 */
export function formatNumber(value: number, fractionDigits?: number): string {
  return new Intl.NumberFormat(PT_BR, {
    minimumFractionDigits: fractionDigits ?? 0,
    maximumFractionDigits: fractionDigits ?? 2,
  }).format(value);
}

/**
 * Formata um inteiro sem casas decimais.
 * Ex: 1500 → "1.500"
 */
export function formatInt(value: number): string {
  return new Intl.NumberFormat(PT_BR, {
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Formata um valor de peso em kg no locale pt-BR.
 * Ex: 485.3 → "485,3 kg"
 */
export function formatKg(value: number): string {
  return `${new Intl.NumberFormat(PT_BR, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(value)} kg`;
}

/**
 * Formata uma área em hectares.
 * Ex: 12.75 → "12,75 ha"
 */
export function formatHa(value: number): string {
  return `${new Intl.NumberFormat(PT_BR, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)} ha`;
}

/**
 * Formata uma porcentagem inteira.
 * Ex: 73 → "73 %"
 */
export function formatPct(value: number): string {
  return `${Math.round(value)} %`;
}

/**
 * Formata um valor monetário em BRL.
 * Ex: 1500.50 → "R$ 1.500,50"
 */
export function formatBRL(value: number): string {
  return new Intl.NumberFormat(PT_BR, {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

/**
 * Formata uma data no locale pt-BR.
 * Ex: "2026-07-26" → "26 de jul. de 2026" (com opções padrão)
 */
export function formatDate(
  value: string | Date,
  options: Intl.DateTimeFormatOptions = { day: "2-digit", month: "short" }
): string {
  const date =
    typeof value === "string"
      ? new Date(`${value}T00:00:00`)
      : value;
  return date.toLocaleDateString(PT_BR, options);
}

/**
 * Traduz o código de status/fase da safra para uma descrição amigável.
 * Ex: "PREPARO_SOLO" → "Preparo de solo"
 */
export function formatSafraStatus(status?: string | null): string {
  if (!status) return "";
  const map: Record<string, string> = {
    PLANEJADA: "Planejada",
    PLANEJAMENTO: "Planejamento",
    PREPARO_SOLO: "Preparo de solo",
    PLANTIO: "Plantio",
    DESENVOLVIMENTO: "Em desenvolvimento",
    EM_ANDAMENTO: "Em andamento",
    COLHEITA: "Colheita",
    POS_COLHEITA: "Pós-colheita",
    ENCERRADA: "Encerrada",
    CANCELADA: "Cancelada",
    ATIVA: "Ativa",
  };
  return map[status.toUpperCase()] || status.charAt(0).toUpperCase() + status.slice(1).toLowerCase().replace(/_/g, " ");
}

/**
 * Corrige a formatação de números em descrições (como área e custo) para pt-BR.
 * Ex: "Área: 123.45 ha\nCusto: R$ 1234.5" → "Área: 123,45 ha\nCusto: R$ 1.234,50"
 */
export function formatDescricao(text?: string | null): string {
  if (!text) return "";
  return text
    .replace(/Área:\s*([\d.]+)\s*ha/gi, (_, num) => {
      const val = Number(num);
      return !isNaN(val) ? `Área: ${formatHa(val)}` : `Área: ${num} ha`;
    })
    .replace(/Custo:\s*R\$\s*([\d.]+)/gi, (_, num) => {
      const val = Number(num);
      return !isNaN(val) ? `Custo: ${formatBRL(val)}` : `Custo: R$ ${num}`;
    });
}
