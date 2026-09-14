import { apiFetchServer } from "@/lib/api-server";
import { cookies } from "next/headers";
import { PiquetesClient, type AreaRuralOption, type PiqueteArea } from "./PiquetesClient";

export default async function PiquetesPage() {
  const cookieStore = await cookies();
  const activeFazendaId = cookieStore.get("unidade_produtiva_id")?.value;

  let initialData: PiqueteArea[] = [];
  let initialAreas: AreaRuralOption[] = [];
  if (activeFazendaId) {
    try {
      initialData = await apiFetchServer<PiqueteArea[]>(
        `/cadastros/areas-rurais?tipo=PIQUETE&unidade_produtiva_id=${activeFazendaId}`
      );
    } catch {
      // Silencia erro se a API não retornar nada
    }

    try {
      initialAreas = await apiFetchServer<AreaRuralOption[]>(
        `/cadastros/areas-rurais?unidade_produtiva_id=${activeFazendaId}`
      );
    } catch {
      // Silencia erro se a API não retornar nada
    }
  }

  return (
    <PiquetesClient
      initialData={initialData}
      initialAreas={initialAreas}
      initialActiveFazendaId={activeFazendaId}
    />
  );
}
