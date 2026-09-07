import { apiFetchServer } from "@/lib/api-server";
import { SegurancaClient } from "./SegurancaClient";

type Colaborador = {
  id: string;
  nome: string;
};

export default async function SegurancaPage() {
  let initialColaboradores: Colaborador[] = [];

  try {
    initialColaboradores = await apiFetchServer<Colaborador[]>("/rh/colaboradores?ativo=true");
  } catch (error) {
    // Pré-carga opcional; o client continua funcionando com listas vazias.
  }

  return <SegurancaClient initialColaboradores={initialColaboradores} />;
}
