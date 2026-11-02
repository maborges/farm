import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { parseDecimalBR } from "@farm/utils"

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value)
}

export function parseLocaleNumber(value: string | number | null | undefined, fallback = 0) {
  const parsed = parseDecimalBR(value)
  return Number.isFinite(parsed) ? parsed : fallback
}
