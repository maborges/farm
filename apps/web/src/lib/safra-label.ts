export interface SafraLabelSource {
  cultura?: string | null;
  ano_safra: string;
}

export function getSafraLabel(safra?: SafraLabelSource | null): string {
  if (!safra) return "Safra";
  const cultura = safra.cultura?.trim();
  return cultura ? `${cultura} — Safra ${safra.ano_safra}` : `Safra ${safra.ano_safra}`;
}
