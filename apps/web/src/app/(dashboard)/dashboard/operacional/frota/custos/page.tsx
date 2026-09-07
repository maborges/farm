import { apiFetchServer } from "@/lib/api-server";
import { CustosClient } from "./CustosClient";
import { CustoResponse } from "./types";

export default async function FrotaCustosPage(props: {
  searchParams: Promise<{ unidade_produtiva_id?: string }>;
}) {
  const searchParams = await props.searchParams;
  const serverFazendaId = searchParams?.unidade_produtiva_id || "";

  let initialData: CustoResponse | null = null;
  try {
    const params = new URLSearchParams();
    if (serverFazendaId) {
      params.append("unidade_produtiva_id", serverFazendaId);
    }
    params.append("periodo_dias", "90");
    initialData = await apiFetchServer<CustoResponse>(`/frota/custos?${params.toString()}`);
  } catch (error) {
    console.error("Failed to prefetch Custos data on server:", error);
  }

  return (
    <CustosClient
      initialData={initialData}
      serverFazendaId={serverFazendaId}
    />
  );
}
