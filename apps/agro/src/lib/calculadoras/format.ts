/**
 * Utilitários de Formatação e Parsing de Valores Numéricos pt-BR
 * para Calculadoras do DeepFarms Agro.
 *
 * Tratamento explícito de entradas brasileiras, ambíguas e limites numéricos.
 */

export const MENSAGEM_NAO_CALCULAVEL = "Não calculável com os valores informados.";

/**
 * Converte string informada pelo usuário em número real, com validações estritas de segurança.
 *
 * Regras de Parsing:
 * 1. Padrão pt-BR com vírgula decimal: "1250,50", "1,25", "1,234" -> decimais reais.
 * 2. Padrão pt-BR com separador de milhar e vírgula: "1.250,50", "1.000.000,00" -> decimais reais.
 * 3. Múltiplos pontos sem vírgula: "1.250.000" -> separadores de milhar (1250000).
 * 4. Ponto único sem vírgula com 1 ou 2 dígitos decimais: "1250.50", "1.5", "0.75" -> decimais reais.
 * 5. Ponto único com exatamente 3 dígitos sem vírgula ("1.234"):
 *    Adota a convenção oficial brasileira (pt-BR / ABNT), interpretando o ponto como separador
 *    de milhar (1234 unidades). Para decimais de 3 dígitos, exige-se a vírgula ("1,234").
 * 6. Valores inválidos, não numéricos, vazios, NaN, Infinity ou excedendo MAX_SAFE_INTEGER retornam null.
 */
export function parseNumeroPtBr(input: string | number | undefined | null): number | null {
  if (input === undefined || input === null) {
    return null;
  }

  if (typeof input === "number") {
    if (!Number.isFinite(input) || Number.isNaN(input)) {
      return null;
    }
    if (Math.abs(input) > Number.MAX_SAFE_INTEGER) {
      return null;
    }
    return input;
  }

  const trimmed = input.trim();
  if (!trimmed || trimmed === "-") {
    return null;
  }

  // Rejeita strings com caracteres que não sejam dígitos, separadores permitidos ou sinal negativo
  if (/[^\d.,-]/.test(trimmed)) {
    return null;
  }

  // Apenas um sinal negativo e apenas no primeiro caractere
  if (trimmed.indexOf("-") > 0 || (trimmed.match(/-/g) ?? []).length > 1) {
    return null;
  }

  // Previne overflow de strings excessivamente longas (> 18 caracteres de dígitos)
  const contagemDigitos = trimmed.replace(/\D/g, "").length;
  if (contagemDigitos > 16) {
    return null;
  }

  // Rejeita múltiplos separadores de vírgula (ex: "1,2,3")
  const partesVirgula = trimmed.split(",");
  if (partesVirgula.length > 2) {
    return null;
  }

  // Caso 1: Contém vírgula e ponto (ex: "1.250,50" ou "1.000.000,50")
  if (trimmed.includes(",") && trimmed.includes(".")) {
    const ultimoPonto = trimmed.lastIndexOf(".");
    const ultimaVirgula = trimmed.lastIndexOf(",");

    // Em pt-BR, o ponto de milhar precede a vírgula decimal
    if (ultimoPonto < ultimaVirgula) {
      const semPontos = trimmed.replace(/\./g, "");
      const comPontoDecimal = semPontos.replace(",", ".");
      const parsed = Number.parseFloat(comPontoDecimal);
      return Number.isFinite(parsed) && Math.abs(parsed) <= Number.MAX_SAFE_INTEGER ? parsed : null;
    }

    // Se o usuário digitou padrão internacional com vírgula de milhar (ex: "1,250.50")
    if (ultimaVirgula < ultimoPonto) {
      const semVirgulas = trimmed.replace(/,/g, "");
      const parsed = Number.parseFloat(semVirgulas);
      return Number.isFinite(parsed) && Math.abs(parsed) <= Number.MAX_SAFE_INTEGER ? parsed : null;
    }

    return null;
  }

  // Caso 2: Contém apenas vírgula (ex: "1250,50", "1,25", "1,234")
  if (trimmed.includes(",")) {
    const comPonto = trimmed.replace(",", ".");
    const parsed = Number.parseFloat(comPonto);
    return Number.isFinite(parsed) && Math.abs(parsed) <= Number.MAX_SAFE_INTEGER ? parsed : null;
  }

  // Caso 3: Contém apenas pontos
  if (trimmed.includes(".")) {
    const partesPonto = trimmed.split(".");

    // Se houver mais de um ponto (ex: "1.250.000"), são obrigatoriamente separadores de milhar
    if (partesPonto.length > 2) {
      const parsed = Number.parseFloat(trimmed.replace(/\./g, ""));
      return Number.isFinite(parsed) && Math.abs(parsed) <= Number.MAX_SAFE_INTEGER ? parsed : null;
    }

    // Ponto único (ex: "1250.50", "1.25", "1.5", "1.234")
    const [, parteDecimal] = partesPonto;

    // Se tiver exatamente 3 dígitos após o ponto (ex: "1.234" ou "10.500"):
    // Adota a convenção brasileira: ponto seguido de 3 dígitos é separador de milhar
    if (parteDecimal && parteDecimal.length === 3) {
      const parsed = Number.parseFloat(trimmed.replace(/\./g, ""));
      return Number.isFinite(parsed) && Math.abs(parsed) <= Number.MAX_SAFE_INTEGER ? parsed : null;
    }

    // Caso contrário (ex: "1250.50" com 2 dígitos, "1.5" com 1 dígito, ou 4 dígitos):
    // Grupos de milhar nunca têm 1, 2 ou 4 dígitos, logo é inequivocamente decimal
    const parsed = Number.parseFloat(trimmed);
    return Number.isFinite(parsed) && Math.abs(parsed) <= Number.MAX_SAFE_INTEGER ? parsed : null;
  }

  // Caso 4: Inteiro sem separadores (ex: "1250", "100")
  const parsed = Number.parseFloat(trimmed);
  return Number.isFinite(parsed) && Math.abs(parsed) <= Number.MAX_SAFE_INTEGER ? parsed : null;
}

/**
 * Detecta se a entrada possui ambiguidade numérica (ex: "1.234" sem vírgula)
 * para emitir aviso preventivo na interface e evitar erros financeiros.
 */
export function detectarEntradaAmbiguaPtBr(input: string | null | undefined): string | null {
  if (!input) return null;
  const trimmed = input.trim();

  // Ponto único seguido de exatamente 3 dígitos sem vírgula (ex: "1.234", "10.500")
  if (/^-?\d{1,3}\.\d{3}$/.test(trimmed)) {
    const valorMilhar = trimmed.replace(".", "");
    return `Notação pt-BR: '${trimmed}' foi interpretado como ${valorMilhar} unidades (separador de milhar). Para valor fracionário com decimais, utilize vírgula: '${trimmed.replace(".", ",")}'.`;
  }

  return null;
}

/**
 * Formata um número com padrão pt-BR de milhar e decimais.
 */
export function formatarNumero(valor: number | null | undefined, casasDecimais = 2): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) {
    return "—";
  }

  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: casasDecimais,
  }).format(valor);
}

/**
 * Formata um valor numérico ou apresenta mensagem padronizada quando não calculável.
 */
export function formatarNumeroOuNaoCalculavel(
  valor: number | null | undefined,
  casasDecimais = 2,
  sufixo = ""
): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) {
    return MENSAGEM_NAO_CALCULAVEL;
  }

  const formatado = formatarNumero(valor, casasDecimais);
  return sufixo ? `${formatado} ${sufixo}` : formatado;
}

/**
 * Formata um valor monetário em Reais (R$).
 */
export function formatarMoeda(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) {
    return "—";
  }

  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(valor);
}

/**
 * Formata valor monetário ou apresenta mensagem padronizada quando não calculável.
 */
export function formatarMoedaOuNaoCalculavel(
  valor: number | null | undefined,
  sufixoUnitario = ""
): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) {
    return MENSAGEM_NAO_CALCULAVEL;
  }

  const formatado = formatarMoeda(valor);
  return sufixoUnitario ? `${formatado} ${sufixoUnitario}` : formatado;
}

/**
 * Formata percentual com símbolo %.
 */
export function formatarPercentual(valor: number | null | undefined, casasDecimais = 1): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) {
    return "—";
  }

  const formatado = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: casasDecimais,
    maximumFractionDigits: casasDecimais,
  }).format(valor);

  return `${formatado}%`;
}

/**
 * Formata percentual ou apresenta mensagem padronizada quando não calculável.
 */
export function formatarPercentualOuNaoCalculavel(
  valor: number | null | undefined,
  casasDecimais = 1
): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) {
    return MENSAGEM_NAO_CALCULAVEL;
  }

  return formatarPercentual(valor, casasDecimais);
}
