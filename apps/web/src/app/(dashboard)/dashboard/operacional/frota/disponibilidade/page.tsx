import { apiFetchServer } from "@/lib/api-server";
import { DisponibilidadeClient } from "./DisponibilidadeClient";
import { DisponibilidadeResponse } from "./types";

export default async function FrotaDisponibilidadePage(props: {
  searchParams: Promise<{ unidade_produtiva_id?: string }>;
}) {
  const searchParams = await props.searchParams;
  const serverFazendaId = searchParams?.unidade_produtiva_id || "";

  let initialData: DisponibilidadeResponse | null = null;
  try {
    const queryParam = serverFazendaId ? `?unidade_produtiva_id=${serverFazendaId}` : "";
    initialData = await apiFetchServer<DisponibilidadeResponse>(`/frota/disponibilidade${queryParam}`);
  } catch (error) {
    console.error("Failed to prefetch Disponibilidade data on server:", error);
  }

  return (
    <DisponibilidadeClient
      initialData={initialData}
      serverFazendaId={serverFazendaId}
    />
  );
}
