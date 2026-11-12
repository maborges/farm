import { apiFetchServer } from "@/lib/api-server";
import { SolicitacoesClient } from "./SolicitacoesClient";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Solicitações de Compra | AGRO",
  description: "Gestão de solicitações de suprimentos e reposição de estoque.",
};

export default async function SolicitacoesPage() {
  // Busca inicial no servidor
  let initialData = [];
  try {
    initialData = await apiFetchServer("/compras/solicitacoes");
  } catch (error) {
    console.error("Erro ao buscar solicitações iniciais:", error);
  }

  return <SolicitacoesClient initialData={initialData} />;
}
