import { apiFetchServer } from "@/lib/api-server";
import { FrotaClient } from "./FrotaClient";
import { FrotaDashboard } from "./_components/types";

export default async function FrotaPage(props: {
  searchParams: Promise<{ [key: string]: string | undefined }>;
}) {
  const searchParams = await props.searchParams;
  const serverFazendaId = searchParams?.unidade_produtiva_id || "";

  let initialData: FrotaDashboard | null = null;
  try {
    const queryParam = serverFazendaId ? `?unidade_produtiva_id=${serverFazendaId}` : "";
    initialData = await apiFetchServer<FrotaDashboard>(`/frota/dashboard${queryParam}`);
  } catch (error) {
    // Evita crashes no servidor caso o endpoint retorne 402/erro. O FrotaClient fará o fetch client-side.
    console.error("Failed to prefetch frota dashboard on server:", error);
  }

  return (
    <FrotaClient
      initialData={initialData}
      serverFazendaId={serverFazendaId}
    />
  );
}
