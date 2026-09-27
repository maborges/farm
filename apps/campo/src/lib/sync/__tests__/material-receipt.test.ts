import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { db, type CachedRequisicao, type LocalSession } from "@/lib/db";
import { enfileirarDestinacaoRequisicao, enfileirarRecebimentoRequisicao } from "@/lib/requisicoes-api";
import { pushSync } from "@/lib/sync/push";
import { useSessionStore } from "@/lib/stores/session-store";

function session(): LocalSession {
  return {
    id: 1,
    user_id: "user-a",
    tenant_id: "tenant-a",
    device_id: "device-a",
    device_token: "device-token-a",
    pin_hash: "hash",
    user_name: "Operador A",
    last_sync_at: null,
    modules: ["agricola"],
    fazenda_ids: ["up-a"],
  };
}

function projection(): CachedRequisicao {
  return {
    id: "req-a",
    tenant_id: "tenant-a",
    numero: "REQ-01E",
    unidade_produtiva_id: "up-a",
    operacao_agricola_id: "op-a",
    responsavel_pessoa_id: "person-a",
    responsavel_autorizado: true,
    version: 5,
    status: "ENTREGUE",
    status_efetivo: "DIVERGENTE",
    status_conciliacao: "EM_POSSE",
    data_solicitacao: "2026-09-25T00:00:00Z",
    updated_at: "2026-09-25T00:00:00Z",
    itens: [
      {
        id: "item-a",
        requisicao_id: "req-a",
        tenant_id: "tenant-a",
        produto_id: "product-a",
        produto_nome: "Produto A",
        natureza_item: "CONSUMIVEL",
        unidade: "KG",
        quantidade_aprovada: 100,
        quantidade_entregue: 100,
        quantidade_recebida: 92,
        quantidade_recusada: 0,
        quantidade_pendente_conferencia: 8,
        quantidade_em_posse: 92,
        quantidade_consumida: 0,
        quantidade_devolvida: 0,
        status_conferencia: "DIVERGENTE",
        updated_at: "2026-09-25T00:00:00Z",
        entregas: [
          {
            id: "delivery-a",
            quantidade_entregue: 100,
            quantidade_recebida: 92,
            quantidade_recusada: 0,
            quantidade_pendente_conferencia: 8,
            quantidade_em_posse: 92,
            lote_id: "lot-a",
            deposito_id: "depot-a",
            unidade: "KG",
            entregue_em: "2026-09-25T00:00:00Z",
          },
        ],
      },
    ],
  };
}

describe("recebimento de material Campo — fila offline", () => {
  beforeEach(async () => {
    await db.delete();
    await db.open();
    useSessionStore.setState({ session: session(), isAuthenticated: true });
    Object.defineProperty(navigator, "onLine", { configurable: true, value: false });
    await db.requisicoes.put(projection());
    await db.requisicao_itens.put(projection().itens[0]);
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    await db.delete();
  });

  it("preserva client_operation_id durante perda de resposta e retry", async () => {
    const clientOperationId = await enfileirarRecebimentoRequisicao({
      requisicao_id: "req-a",
      item_id: "item-a",
      entrega_evento_id: "delivery-a",
      quantidade_recebida: 92,
      resultado: "DIVERGENTE",
      base_version: 4,
      motivo: "8 kg não conferidos",
    });

    const queued = await db.sync_queue.toArray();
    expect(queued).toHaveLength(1);
    expect(queued[0].entity_type).toBe("material_receipt");
    expect(queued[0].payload.client_operation_id).toBe(clientOperationId);
    expect((await db.requisicao_operacoes.get(clientOperationId))?.status).toBe("PENDING");

    vi.stubGlobal("navigator", { onLine: true });
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("resposta perdida"))
      .mockResolvedValue({
        ok: true,
        json: async () => ({
          evento_id: "receipt-event-a",
          projection: projection(),
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    await expect(pushSync()).rejects.toThrow("resposta perdida");
    expect((await db.sync_queue.toArray())[0].status).toBe("PENDING");
    expect((await db.requisicao_operacoes.get(clientOperationId))?.status).toBe("PENDING");

    await pushSync();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string).client_operation_id).toBe(clientOperationId);
    expect((await db.sync_queue.toArray())[0].status).toBe("DONE");
    expect((await db.requisicao_operacoes.get(clientOperationId))?.status).toBe("ACK");
    expect((await db.requisicao_operacoes.where("tenant_id").equals("tenant-a").count())).toBe(1);
  });

  it("registra conflito e aplica a projeção canônica devolvida pelo backend", async () => {
    const clientOperationId = await enfileirarRecebimentoRequisicao({
      requisicao_id: "req-a",
      item_id: "item-a",
      entrega_evento_id: "delivery-a",
      quantidade_recebida: 92,
      resultado: "DIVERGENTE",
      base_version: 4,
    });
    Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({
        detail: { message: "Versão obsoleta", projection: projection() },
      }),
    }));

    await pushSync();
    expect((await db.sync_queue.toArray())[0].status).toBe("DONE");
    expect((await db.requisicao_operacoes.get(clientOperationId))?.status).toBe("CONFLICT");
    expect((await db.requisicoes.get("req-a"))?.status_efetivo).toBe("DIVERGENTE");
  });

  it("enfileira consumo offline, preserva a chave e não usa rota de baixa física", async () => {
    const clientOperationId = await enfileirarDestinacaoRequisicao({
      requisicao_id: "req-a",
      item_id: "item-a",
      entrega_evento_id: "delivery-a",
      tipo_evento: "CONSUMO",
      quantidade: 20,
      base_version: 5,
      operacao_execucao_id: "execution-a",
    });
    const local = await db.requisicoes.get("req-a");
    expect(local?.itens[0].quantidade_consumida).toBe(20);
    expect((await db.sync_queue.toArray())[0].entity_type).toBe("material_disposition");
    expect((await db.sync_queue.toArray())[0].payload.client_operation_id).toBe(clientOperationId);

    Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ evento_id: "consume-event-a", projection: projection() }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await pushSync();
    expect(fetchMock.mock.calls[0][0]).toContain("/destinar");
    expect(fetchMock.mock.calls[0][0]).not.toContain("/receber");
    expect((await db.requisicao_operacoes.get(clientOperationId))?.status).toBe("ACK");
  });
});
