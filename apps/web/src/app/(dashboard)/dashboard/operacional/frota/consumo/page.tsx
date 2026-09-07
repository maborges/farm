import { apiFetchServer } from "@/lib/api-server";
import { ConsumoClient } from "./ConsumoClient";
import { ConsumoResponse } from "./types";

export default async function FrotaConsumoPage(props: {
  searchParams: Promise<{ unidade_produtiva_id?: string }>;
}) {
  const searchParams = await props.searchParams;
  const serverFazendaId = searchParams?.unidade_produtiva_id || "";

  let initialData: ConsumoResponse | null = null;
  try {
    const queryParam = serverFazendaId ? `?unidade_produtiva_id=${serverFazendaId}` : "";
    initialData = await apiFetchServer<ConsumoResponse>(`/frota/consumo${queryParam}`);
  } catch (error) {
    console.error("Failed to prefetch Consumo data on server:", error);
  }

  return (
    <ConsumoClient
      initialData={initialData}
      serverFazendaId={serverFazendaId}
    />
  );
}
