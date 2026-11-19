import { apiFetchServer } from "@/lib/api-server";

import { ViabilidadeClient, type TemplateProjetoAgro } from "./ViabilidadeClient";

export default async function ViabilidadePage() {
  let initialTemplates: TemplateProjetoAgro[] = [];

  try {
    initialTemplates = await apiFetchServer<TemplateProjetoAgro[]>("/financeiro/viabilidade/templates");
  } catch {
    // Fallback para carregamento via client query com sessão ativa.
  }

  return <ViabilidadeClient initialTemplates={initialTemplates} />;
}
