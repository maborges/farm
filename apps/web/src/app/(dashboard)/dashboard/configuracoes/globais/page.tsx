import { apiFetchServer } from "@/lib/api-server";
import { GlobaisClient } from "./GlobaisClient";

export const dynamic = "force-dynamic";

interface ConfigGeral {
  ano_agricola: { mes_inicio: number; mes_fim: number };
  unidade_area: string;
  moeda: string;
  fuso_horario: string;
  idioma: string;
}

interface SequencialConfig {
  entidade: string;
  label: string;
  prefixo: string;
  digitos: number;
  escopo: "ANO" | "GLOBAL";
  personalizado: boolean;
  ultimo_numero: number;
}

export const metadata = {
  title: "Configurações Globais",
};

export default async function ConfiguracoesGlobaisPage() {
  const [configGeralRes, sequenciaisRes] = await Promise.allSettled([
    apiFetchServer<ConfigGeral>("config/geral"),
    apiFetchServer<SequencialConfig[]>("config/sequenciais"),
  ]);

  if (configGeralRes.status === "rejected") {
    console.error("Failed to prefetch config/geral on server:", configGeralRes.reason);
  }
  if (sequenciaisRes.status === "rejected") {
    console.error("Failed to prefetch config/sequenciais on server:", sequenciaisRes.reason);
  }

  return (
    <GlobaisClient
      initialConfigGeral={configGeralRes.status === "fulfilled" ? configGeralRes.value : null}
      initialSequenciais={sequenciaisRes.status === "fulfilled" ? sequenciaisRes.value : null}
    />
  );
}
