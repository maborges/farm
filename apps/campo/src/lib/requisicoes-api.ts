import { useSessionStore } from "./stores/session-store";

const API_BASE = "/api/v1";

export interface ItemRequisicao {
  id: string;
  produto_id: string;
  produto_nome: string | null;
  unidade_medida: string | null;
  deposito_id: string | null;
  lote_id: string | null;
  quantidade_solicitada: number;
  quantidade_aprovada: number | null;
  quantidade_entregue: number | null;
  quantidade_devolvida: number | null;
  observacoes: string | null;
}

export interface Requisicao {
  id: string;
  numero: string | null;
  unidade_produtiva_id: string;
  solicitante_id: string;
  solicitante_nome: string | null;
  status: string;
  data_solicitacao: string;
  data_necessidade: string | null;
  origem_tipo: string;
  origem_id: string | null;
  observacoes: string | null;
  itens: ItemRequisicao[];
}

class RequisicaoApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(): HeadersInit {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.device_token}`,
  };
}

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body?.detail ?? `Erro ${res.status}`;
  } catch {
    return `Erro ${res.status}`;
  }
}

export async function listarRequisicoesDaOperacao(operacaoAgricolaId: string): Promise<Requisicao[]> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");

  const params = new URLSearchParams({
    device_id: session.device_id,
    operacao_agricola_id: operacaoAgricolaId,
  });
  const res = await fetch(`${API_BASE}/campo/requisicoes?${params}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new RequisicaoApiError(res.status, await parseErrorMessage(res));
  return res.json();
}

export async function confirmarRetiradaRequisicao(
  requisicaoId: string,
  pin: string,
  itens: Array<{ item_id: string; quantidade_conferida: number }>
): Promise<Requisicao> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");

  const res = await fetch(`${API_BASE}/campo/requisicoes/${requisicaoId}/confirmar-retirada`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ device_id: session.device_id, pin, itens }),
  });
  if (!res.ok) throw new RequisicaoApiError(res.status, await parseErrorMessage(res));
  return res.json();
}

export async function confirmarDevolucaoRequisicao(
  requisicaoId: string,
  pin: string,
  itens: Array<{ item_id: string; quantidade_devolvida: number }>
): Promise<Requisicao> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");

  const res = await fetch(`${API_BASE}/campo/requisicoes/${requisicaoId}/confirmar-devolucao`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ device_id: session.device_id, pin, itens }),
  });
  if (!res.ok) throw new RequisicaoApiError(res.status, await parseErrorMessage(res));
  return res.json();
}
