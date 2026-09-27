import { db, type CachedRequisicao, type CachedItemRequisicao, type ResultadoRecebimentoCampo } from "./db";
import { useSessionStore } from "./stores/session-store";
import { enqueueSync } from "./sync/push";

const API_BASE = "/api/v1";

export interface ItemRequisicao {
  id: string;
  produto_id: string;
  produto_nome: string | null;
  unidade: string;
  unidade_medida: string | null;
  deposito_id: string | null;
  lote_id: string | null;
  quantidade_solicitada: number;
  quantidade_aprovada: number | null;
  quantidade_entregue: number | null;
  quantidade_devolvida: number | null;
  observacoes: string | null;
  natureza_item?: "CONSUMIVEL" | "RETORNAVEL" | null;
  quantidade_recebida: number;
  quantidade_recusada: number;
  quantidade_pendente_conferencia: number;
  quantidade_em_posse: number;
  quantidade_consumida?: number;
  quantidade_perdida?: number;
  quantidade_danificada?: number;
  quantidade_extraviada?: number;
  status_conferencia: string;
  status_conciliacao?: string;
  entregas: EntregaRequisicao[];
}

export interface EntregaRequisicao {
  id: string;
  quantidade_entregue: number;
  quantidade_recebida: number;
  quantidade_recusada: number;
  quantidade_pendente_conferencia: number;
  quantidade_consumida?: number;
  quantidade_devolvida?: number;
  quantidade_perdida?: number;
  quantidade_danificada?: number;
  quantidade_extraviada?: number;
  quantidade_em_posse?: number;
  status_conciliacao?: string;
  lote_id?: string | null;
  deposito_id?: string | null;
  unidade: string;
  entregue_em: string;
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
  status_efetivo: string;
  status_conciliacao?: string;
  version: number;
  operacao_agricola_id?: string | null;
  responsavel_pessoa_id?: string | null;
  execucoes?: Array<{ id: string; status: string; data_execucao: string }>;
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
  if (navigator.onLine) {
    const res = await fetch(`${API_BASE}/campo/requisicoes?${params}`, {
      headers: authHeaders(),
      cache: "no-store",
    });
    if (!res.ok) throw new RequisicaoApiError(res.status, await parseErrorMessage(res));
    const data = (await res.json()) as Requisicao[];
    await cacheRequisicoes(data);
    return data;
  }

  const cached = await db.requisicoes
    .where("operacao_agricola_id")
    .equals(operacaoAgricolaId)
    .toArray();
  if (cached.length === 0) {
    throw new Error("Sem conexão e sem requisições previamente sincronizadas para esta operação.");
  }
  return cached.map(toRequisicao);
}

function toRequisicao(value: CachedRequisicao): Requisicao {
  return {
    id: value.id,
    numero: value.numero ?? null,
    unidade_produtiva_id: value.unidade_produtiva_id,
    solicitante_id: "",
    solicitante_nome: null,
    status: value.status,
    status_efetivo: value.status_efetivo,
    version: value.version,
    data_solicitacao: value.data_solicitacao,
    data_necessidade: null,
    origem_tipo: "ORDEM_SERVICO",
    origem_id: value.operacao_agricola_id ?? null,
    observacoes: null,
    operacao_agricola_id: value.operacao_agricola_id ?? null,
    responsavel_pessoa_id: value.responsavel_pessoa_id ?? null,
    itens: value.itens.map((item) => ({
      ...item,
      produto_nome: item.produto_nome ?? null,
      unidade: item.unidade,
      unidade_medida: item.unidade,
      deposito_id: item.entregas[0]?.deposito_id ?? null,
      lote_id: item.entregas[0]?.lote_id ?? null,
      quantidade_solicitada: item.quantidade_aprovada,
      quantidade_devolvida: item.quantidade_devolvida ?? 0,
      observacoes: null,
    })),
  };
}

async function cacheRequisicoes(requisicoes: Requisicao[]): Promise<void> {
  const now = new Date().toISOString();
  await db.transaction("rw", [db.requisicoes, db.requisicao_itens], async () => {
    for (const requisicao of requisicoes) {
      const cachedItems = requisicao.itens.map((item) => toCachedItem(item, requisicao.id, now));
      const cached: CachedRequisicao = {
        id: requisicao.id,
        tenant_id: useSessionStore.getState().session?.tenant_id ?? "",
        numero: requisicao.numero,
        unidade_produtiva_id: requisicao.unidade_produtiva_id,
        operacao_agricola_id: requisicao.operacao_agricola_id ?? null,
        responsavel_pessoa_id: requisicao.responsavel_pessoa_id ?? null,
        responsavel_autorizado: true,
        version: requisicao.version,
        status: requisicao.status,
        status_efetivo: requisicao.status_efetivo,
        data_solicitacao: requisicao.data_solicitacao,
        itens: cachedItems,
        updated_at: now,
      };
      await db.requisicoes.put(cached);
      await db.requisicao_itens.bulkPut(cachedItems);
    }
  });
}

function toCachedItem(item: ItemRequisicao, requisicaoId: string, now: string): CachedItemRequisicao {
  return {
    id: item.id,
    requisicao_id: requisicaoId,
    tenant_id: useSessionStore.getState().session?.tenant_id ?? "",
    produto_id: item.produto_id,
    produto_nome: item.produto_nome,
    natureza_item: item.natureza_item ?? null,
    unidade: item.unidade,
    quantidade_aprovada: item.quantidade_aprovada ?? 0,
    quantidade_entregue: item.quantidade_entregue ?? 0,
    quantidade_recebida: item.quantidade_recebida,
    quantidade_recusada: item.quantidade_recusada,
    quantidade_pendente_conferencia: item.quantidade_pendente_conferencia,
    quantidade_em_posse: item.quantidade_em_posse,
    quantidade_consumida: item.quantidade_consumida,
    quantidade_devolvida: item.quantidade_devolvida ?? undefined,
    quantidade_perdida: item.quantidade_perdida ?? undefined,
    quantidade_danificada: item.quantidade_danificada ?? undefined,
    quantidade_extraviada: item.quantidade_extraviada ?? undefined,
    status_conferencia: item.status_conferencia,
    status_conciliacao: item.status_conciliacao,
    entregas: item.entregas,
    updated_at: now,
  };
}

export async function enfileirarRecebimentoRequisicao(input: {
  requisicao_id: string;
  item_id: string;
  entrega_evento_id: string;
  quantidade_recebida: number;
  resultado: ResultadoRecebimentoCampo;
  base_version: number;
  motivo?: string;
}): Promise<string> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");
  const clientOperationId = crypto.randomUUID();
  const payload = {
    item_id: input.item_id,
    entrega_evento_id: input.entrega_evento_id,
    quantidade_recebida: input.quantidade_recebida,
    resultado: input.resultado,
    base_version: input.base_version,
    client_operation_id: clientOperationId,
    dispositivo_id: session.device_id,
    ocorrido_em_dispositivo: new Date().toISOString(),
    motivo: input.motivo ?? null,
    tenant_id: session.tenant_id,
    usuario_id: session.user_id,
    device_id: session.device_id,
  };
  await db.requisicao_operacoes.put({
    id: clientOperationId,
    tenant_id: session.tenant_id,
    usuario_id: session.user_id,
    device_id: session.device_id,
    requisicao_id: input.requisicao_id,
    item_id: input.item_id,
    entrega_evento_id: input.entrega_evento_id,
    quantidade_recebida: input.quantidade_recebida,
    resultado: input.resultado,
    motivo: input.motivo ?? null,
    base_version: input.base_version,
    created_at_device: String(payload.ocorrido_em_dispositivo),
    status: "PENDING",
    server_event_id: null,
    error: null,
  });
  await enqueueSync("CREATE", "material_receipt", clientOperationId, payload);
  await aplicarRecebimentoLocal(input);
  return clientOperationId;
}

export async function enfileirarDestinacaoRequisicao(input: {
  requisicao_id: string;
  item_id: string;
  entrega_evento_id: string;
  tipo_evento: "CONSUMO" | "DEVOLUCAO" | "PERDA" | "DANO" | "EXTRAVIO";
  quantidade: number;
  base_version: number;
  operacao_execucao_id?: string | null;
  deposito_id?: string | null;
  lote_id?: string | null;
  motivo?: string;
}): Promise<string> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");
  const clientOperationId = crypto.randomUUID();
  const createdAt = new Date().toISOString();
  const payload = {
    item_id: input.item_id,
    entrega_evento_id: input.entrega_evento_id,
    tipo_evento: input.tipo_evento,
    quantidade: input.quantidade,
    base_version: input.base_version,
    client_operation_id: clientOperationId,
    operacao_execucao_id: input.operacao_execucao_id ?? null,
    deposito_id: input.deposito_id ?? null,
    lote_id: input.lote_id ?? null,
    dispositivo_id: session.device_id,
    ocorrido_em_dispositivo: createdAt,
    motivo: input.motivo ?? null,
    tenant_id: session.tenant_id,
    usuario_id: session.user_id,
    device_id: session.device_id,
  };
  await db.requisicao_operacoes.put({
    id: clientOperationId,
    tenant_id: session.tenant_id,
    usuario_id: session.user_id,
    device_id: session.device_id,
    requisicao_id: input.requisicao_id,
    item_id: input.item_id,
    entrega_evento_id: input.entrega_evento_id,
    quantidade_recebida: 0,
    resultado: "RECEBIDO_INTEGRAL",
    tipo_evento: input.tipo_evento,
    operacao_execucao_id: input.operacao_execucao_id ?? null,
    deposito_id: input.deposito_id ?? null,
    lote_id: input.lote_id ?? null,
    motivo: input.motivo ?? null,
    base_version: input.base_version,
    created_at_device: createdAt,
    status: "PENDING",
    server_event_id: null,
    error: null,
  });
  await enqueueSync("CREATE", "material_disposition", clientOperationId, payload);
  await aplicarDestinacaoLocal(input);
  return clientOperationId;
}

async function aplicarDestinacaoLocal(input: {
  requisicao_id: string;
  item_id: string;
  entrega_evento_id: string;
  tipo_evento: "CONSUMO" | "DEVOLUCAO" | "PERDA" | "DANO" | "EXTRAVIO";
  quantidade: number;
}): Promise<void> {
  const requisicao = await db.requisicoes.get(input.requisicao_id);
  if (!requisicao) return;
  const item = requisicao.itens.find((candidate) => candidate.id === input.item_id);
  const entrega = item?.entregas.find((candidate) => candidate.id === input.entrega_evento_id);
  if (!item || !entrega) return;
  const field = {
    CONSUMO: "quantidade_consumida",
    DEVOLUCAO: "quantidade_devolvida",
    PERDA: "quantidade_perdida",
    DANO: "quantidade_danificada",
    EXTRAVIO: "quantidade_extraviada",
  }[input.tipo_evento] as "quantidade_consumida" | "quantidade_devolvida" | "quantidade_perdida" | "quantidade_danificada" | "quantidade_extraviada";
  item[field] = (item[field] ?? 0) + input.quantidade;
  entrega[field] = (entrega[field] ?? 0) + input.quantidade;
  item.quantidade_em_posse = Math.max(0, item.quantidade_em_posse - input.quantidade);
  entrega.quantidade_em_posse = Math.max(0, (entrega.quantidade_em_posse ?? 0) - input.quantidade);
  item.status_conciliacao = item.quantidade_em_posse > 0 ? "EM_POSSE" : "CONCILIADO";
  entrega.status_conciliacao = entrega.quantidade_em_posse > 0 ? "EM_POSSE" : "CONCILIADO";
  requisicao.status_conciliacao = requisicao.itens.every((candidate) =>
    candidate.status_conciliacao === "CONCILIADO"
  ) ? "CONCILIADA" : "EM_POSSE";
  requisicao.version += 1;
  await db.requisicoes.put({ ...requisicao, updated_at: new Date().toISOString() });
  await db.requisicao_itens.put({ ...item, updated_at: new Date().toISOString() });
}

async function aplicarRecebimentoLocal(input: {
  requisicao_id: string;
  item_id: string;
  entrega_evento_id: string;
  quantidade_recebida: number;
  resultado: ResultadoRecebimentoCampo;
}): Promise<void> {
  const requisicao = await db.requisicoes.get(input.requisicao_id);
  if (!requisicao) return;
  const item = requisicao.itens.find((candidate) => candidate.id === input.item_id);
  const entrega = item?.entregas.find((candidate) => candidate.id === input.entrega_evento_id);
  if (!item || !entrega) return;
  const quantidade = input.resultado === "RECUSADO"
    ? entrega.quantidade_pendente_conferencia
    : input.quantidade_recebida;
  entrega.quantidade_recebida += input.quantidade_recebida;
  entrega.quantidade_recusada += input.resultado === "RECUSADO" ? quantidade : 0;
  entrega.quantidade_pendente_conferencia = Math.max(
    0,
    entrega.quantidade_pendente_conferencia - quantidade,
  );
  item.quantidade_recebida += input.quantidade_recebida;
  item.quantidade_recusada += input.resultado === "RECUSADO" ? quantidade : 0;
  item.quantidade_pendente_conferencia = Math.max(
    0,
    item.quantidade_pendente_conferencia - quantidade,
  );
  item.quantidade_em_posse += input.quantidade_recebida;
  item.status_conferencia = item.quantidade_pendente_conferencia > 0
    ? (item.quantidade_recebida > 0 ? "DIVERGENTE" : "PENDENTE_CONFERENCIA")
    : input.resultado === "RECUSADO" ? "RECUSADO" : "RECEBIDO_INTEGRAL";
  requisicao.version += 1;
  const hasDivergence = requisicao.itens.some((candidate) =>
    candidate.status_conferencia === "DIVERGENTE" || candidate.status_conferencia === "RECUSADO"
  );
  requisicao.status_efetivo = hasDivergence
    ? "DIVERGENTE"
    : requisicao.itens.every((candidate) => candidate.quantidade_pendente_conferencia <= 0)
      ? "RECEBIDA"
      : "PENDENTE_CONFERENCIA";
  await db.requisicoes.put({ ...requisicao, updated_at: new Date().toISOString() });
  await db.requisicao_itens.put({
    ...item,
    updated_at: new Date().toISOString(),
  });
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
