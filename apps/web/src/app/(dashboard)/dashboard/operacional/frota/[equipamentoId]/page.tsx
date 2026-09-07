import { apiFetchServer } from "@/lib/api-server";
import { EquipamentoDetalheClient } from "./EquipamentoDetalheClient";
import { FrotaDetalheResponse } from "../_components/types";

export default async function FrotaEquipamentoDetalhePage(props: {
  params: Promise<{ equipamentoId: string }>;
  searchParams: Promise<{ [key: string]: string | undefined }>;
}) {
  const params = await props.params;
  const searchParams = await props.searchParams;

  const { equipamentoId } = params;
  const serverFazendaId = searchParams?.unidade_produtiva_id || "";

  let initialData: FrotaDetalheResponse | null = null;
  try {
    // No servidor, usamos o período padrão de 90 dias
    const queryParam = `?periodo_dias=90${serverFazendaId ? `&unidade_produtiva_id=${serverFazendaId}` : ""}`;
    initialData = await apiFetchServer<FrotaDetalheResponse>(
      `/frota/dashboard/equipamentos/${equipamentoId}${queryParam}`
    );
  } catch (error) {
    // Evita crashes no servidor caso o endpoint retorne 402 ou 404. O cliente lidará com o fetch.
    console.error("Failed to prefetch frota equipment details on server:", error);
  }

  return (
    <EquipamentoDetalheClient
      initialData={initialData}
      equipamentoId={equipamentoId}
      serverFazendaId={serverFazendaId}
    />
  );
}
