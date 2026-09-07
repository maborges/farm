import { apiFetchServer } from "@/lib/api-server";
import { AvaliacoesClient } from "./AvaliacoesClient";
import type { ImovelRural } from "../ImoveisClient";

export default async function AvaliacoesPage() {
  let initialImoveis: ImovelRural[] = [];

  try {
    initialImoveis = await apiFetchServer<ImovelRural[]>("imoveis/?situacao=all");
  } catch (error) {
    // Ignora falhas de pré-carregamento e deixa o client buscar quando necessário.
  }

  return <AvaliacoesClient initialImoveis={initialImoveis} />;
}
