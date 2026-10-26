/** Centraliza o acesso à API. Por padrão, o navegador usa a mesma origem. */
export function agroApiOrigin(): string {
  return (process.env.NEXT_PUBLIC_AGRO_API_ORIGIN ?? "").replace(/\/$/, "");
}

export function agroApiUrl(path: `/api/${string}`): string {
  return `${agroApiOrigin()}${path}`;
}
