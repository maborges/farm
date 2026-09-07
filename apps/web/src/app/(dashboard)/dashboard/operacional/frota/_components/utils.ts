import { FrotaEquipamento, TipoRisco } from "./types";

export const RISCO_LABELS: Record<TipoRisco, string> = {
  SEM_ABASTECIMENTO_RECENTE: "Sem abastecimento",
  OS_ABERTA_ANTIGA: "OS antiga",
  MANUTENCAO_VENCIDA: "Manutenção vencida",
  DOCUMENTO_VENCIDO: "Documento vencido",
  CUSTO_ACIMA_MEDIA: "Custo acima da média",
};

export const MANUTENCAO_LABELS: Record<FrotaEquipamento["manutencao_status"], string> = {
  OK: "Em dia",
  PROXIMA: "Próxima",
  VENCIDA: "Vencida",
  SEM_PLANO: "Sem plano",
};

export function formatCurrency(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value ?? 0);
}

export function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }

  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatDateOrDash(value: string | null | undefined) {
  if (!value) {
    return "—";
  }
  return new Date(value).toLocaleDateString("pt-BR");
}

export function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}

export function getMaintenanceBadgeClass(status: FrotaEquipamento["manutencao_status"]) {
  switch (status) {
    case "VENCIDA":
      return "border-red-200 text-red-700";
    case "PROXIMA":
      return "border-amber-200 text-amber-700";
    case "OK":
      return "border-emerald-200 text-emerald-700";
    default:
      return "border-slate-200 text-slate-600";
  }
}

export function getRiskClass(value: "BAIXO" | "MEDIO" | "ALTO" | "CRITICO") {
  switch (value) {
    case "BAIXO":
      return "border-emerald-200 text-emerald-700";
    case "MEDIO":
      return "border-amber-200 text-amber-700";
    case "ALTO":
      return "border-orange-200 text-orange-700";
    case "CRITICO":
      return "border-red-200 text-red-700";
  }
}

export function formatRiskLabel(value: "BAIXO" | "MEDIO" | "ALTO" | "CRITICO") {
  switch (value) {
    case "BAIXO":
      return "Baixo";
    case "MEDIO":
      return "Médio";
    case "ALTO":
      return "Alto";
    case "CRITICO":
      return "Crítico";
  }
}
