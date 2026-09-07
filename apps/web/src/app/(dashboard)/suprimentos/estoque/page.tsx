import { EstoqueClient } from "./EstoqueClient";
import { apiFetchServer } from "@/lib/api-server";

export default async function EstoquePage(props: { searchParams: Promise<{ [key: string]: string | undefined }> }) {
  // In Next.js >= 15 searchParams is a Promise. We'll await it or just support plain depending on Next.js version.
  // Actually, in AgroSaaS we've been using sync searchParams for now (Next 14).
  const searchParams = await props.searchParams;
  const unidade_produtiva_id = searchParams.unidade_produtiva_id || "";
  
  const fazendaParam = unidade_produtiva_id ? `?unidade_produtiva_id=${unidade_produtiva_id}` : "";
  const fazendaParamComE = unidade_produtiva_id ? `&unidade_produtiva_id=${unidade_produtiva_id}` : "";

  const [
    saldosResult,
    alertasResult,
    produtosResult,
    depositosResult,
    reservasResult,
    movimentacoesResult,
  ] = await Promise.allSettled([
    apiFetchServer(`/estoque/saldos${fazendaParam}`),
    apiFetchServer(`/estoque/alertas${fazendaParam}`),
    apiFetchServer("/cadastros/produtos?ativo=true"),
    apiFetchServer(`/estoque/depositos${fazendaParam}`),
    apiFetchServer("/estoque/reservas?status="), // Reservas don't have fazendaParam in the client? Wait, the client used `activeFazendaId` in queryKey but didn't pass it to the URL `/estoque/reservas?status=`. We will preserve the exact URL.
    apiFetchServer(`/estoque/movimentacoes?limit=200${fazendaParamComE}`),
  ]);

  const initialData = {
    saldos: saldosResult.status === "fulfilled" ? saldosResult.value : [],
    alertas: alertasResult.status === "fulfilled" ? alertasResult.value : [],
    produtos: produtosResult.status === "fulfilled" ? produtosResult.value : [],
    depositos: depositosResult.status === "fulfilled" ? depositosResult.value : [],
    reservas: reservasResult.status === "fulfilled" ? reservasResult.value : [],
    movimentacoes: movimentacoesResult.status === "fulfilled" ? movimentacoesResult.value : [],
  };

  return <EstoqueClient initialData={initialData} />;
}
