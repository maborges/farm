import { cookies } from "next/headers";

import { apiFetchServer } from "@/lib/api-server";

import { FluxoCaixaClient, type FluxoCaixaResponse } from "./FluxoCaixaClient";

function getDefaultHorizon(): { dataInicio: string; dataFim: string } {
  const hoje = new Date();
  const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
  const fim = new Date(hoje.getFullYear(), hoje.getMonth() + 6, 0);
  const toIso = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return {
    dataInicio: toIso(inicio),
    dataFim: toIso(fim),
  };
}

export default async function FluxoCaixaPage() {
  const cookieStore = await cookies();
  const activeFazendaId = cookieStore.get("unidade_produtiva_id")?.value;
  const { dataInicio, dataFim } = getDefaultHorizon();

  const qs = new URLSearchParams({
    data_inicio: dataInicio,
    data_fim: dataFim,
    saldo_inicial: "0",
    taxa_credito_planejado_aa: "8.5",
    taxa_credito_reativo_aa: "24",
  });
  if (activeFazendaId) qs.set("unidade_produtiva_id", activeFazendaId);

  let initialFluxo: FluxoCaixaResponse | null = null;
  try {
    initialFluxo = await apiFetchServer<FluxoCaixaResponse>(`/relatorios/fluxo-caixa?${qs.toString()}`);
  } catch {
    // Fallback para carregamento via client query com sessão ativa.
  }

  return (
    <FluxoCaixaClient
      initialFluxo={initialFluxo}
      initialInicio={dataInicio}
      initialFim={dataFim}
      initialActiveFazendaId={activeFazendaId}
    />
  );
}
