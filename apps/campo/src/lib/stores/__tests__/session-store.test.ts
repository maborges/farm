import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { db, type LocalSession } from "@/lib/db";
import { useSessionStore, consumeSessionClearNotice, getLocalPendingSummary } from "@/lib/stores/session-store";

function buildSession(overrides: Partial<LocalSession> = {}): LocalSession {
  return {
    id: 1,
    user_id: "user-a",
    tenant_id: "tenant-a",
    device_id: "device-1",
    device_token: "token-a",
    pin_hash: "hash",
    user_name: "Operador A",
    last_sync_at: null,
    modules: ["agricola"],
    fazenda_ids: ["fazenda-1"],
    active_fazenda_id: "fazenda-1",
    ...overrides,
  };
}

async function seedCacheTables(): Promise<void> {
  await db.fazendas.add({ id: "fazenda-1", nome: "Fazenda Teste" });
  await db.talhoes.add({ id: "talhao-1", nome: "Talhão 1", fazenda_id: "fazenda-1", tipo: "LAVOURA" });
  await db.insumos.add({ id: "insumo-1", nome: "Ureia", tipo: "FERTILIZANTE" });
  await db.safras.add({ id: "safra-1", ano_safra: "2025/26", status: "ATIVA" });
  await db.requisicoes.add({
    id: "req-1",
    tenant_id: "tenant-a",
    unidade_produtiva_id: "fazenda-1",
    operacao_agricola_id: "operacao-1",
    responsavel_autorizado: true,
    version: 1,
    status: "ENTREGUE",
    status_efetivo: "PENDENTE_CONFERENCIA",
    data_solicitacao: new Date().toISOString(),
    itens: [],
    updated_at: new Date().toISOString(),
  });
}

async function seedPendingWork(): Promise<void> {
  await db.sync_queue.add({
    id: "queue-1",
    operation: "CREATE",
    entity_type: "task",
    entity_id: "task-1",
    payload: {},
    created_at: new Date().toISOString(),
    attempts: 0,
    status: "PENDING",
  });

  await db.tasks.add({
    id: "task-1",
    type: "APLICACAO_DEFENSIVO",
    module: "agricola",
    fazenda_id: "fazenda-1",
    status: "PENDENTE",
    origem: "MANUAL",
    status_execucao: "PENDENTE",
    prioridade: "NORMAL",
    dados: {},
    fotos: [],
    localizacao_status: "INDISPONIVEL",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    synced: false,
  });

  await db.caderno_events.add({
    local_id: "evento-1",
    tenant_id: "tenant-a",
    descricao: "Pulverização talhão 1",
    safra_id: "safra-1",
    tipo_evento: "PULVERIZACAO",
    origem_evento: "PWA_OFFLINE",
    origem_tecnica: "SYNC_PWA",
    status_evento: "PENDENTE_SINCRONIZACAO",
    client_created_at: new Date().toISOString(),
    client_updated_at: new Date().toISOString(),
    device_id: "device-1",
    payload_operacional: {},
    evidencias: [],
    sync_status: "PENDING",
    sync_attempts: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });

  await db.caderno_drafts.add({
    id: "draft-1",
    user_id: "user-a",
    step: "registro",
    tipo_evento: "PULVERIZACAO",
    descricao: "",
    observacao: "",
    fotos: [],
    updated_at: new Date().toISOString(),
  });

  await db.requisicao_operacoes.add({
    id: "receipt-1",
    tenant_id: "tenant-a",
    usuario_id: "user-a",
    device_id: "device-1",
    requisicao_id: "req-1",
    item_id: "item-1",
    entrega_evento_id: "delivery-1",
    quantidade_recebida: 1,
    resultado: "RECEBIDO_INTEGRAL",
    base_version: 1,
    created_at_device: new Date().toISOString(),
    status: "PENDING",
  });
}

async function allCacheTablesEmpty(): Promise<boolean> {
  const counts = await Promise.all([
    db.tasks.count(),
    db.sync_queue.count(),
    db.caderno_events.count(),
    db.caderno_server_events.count(),
    db.caderno_drafts.count(),
    db.fazendas.count(),
    db.talhoes.count(),
    db.lotes.count(),
    db.animais.count(),
    db.insumos.count(),
    db.safras.count(),
    db.colaboradores.count(),
    db.recomendacoes_climaticas.count(),
    db.recomendacoes_operacionais.count(),
    db.pessoas_operacionais.count(),
    db.requisicoes.count(),
    db.requisicao_itens.count(),
    db.requisicao_operacoes.count(),
  ]);
  return counts.every((count) => count === 0);
}

describe("session-store — guardrails de isolamento", () => {
  beforeEach(async () => {
    await db.delete();
    await db.open();
    sessionStorage.clear();
    useSessionStore.setState({ session: null, isAuthenticated: false });
  });

  afterEach(async () => {
    await db.delete();
    sessionStorage.clear();
  });

  it("Teste 1 — mudança de tenant limpa todas as tabelas de cache/fila", async () => {
    await db.session.put(buildSession());
    await seedCacheTables();
    await seedPendingWork();

    await useSessionStore.getState().saveSession(
      buildSession({ tenant_id: "tenant-b", user_id: "user-b", device_id: "device-2", device_token: "token-b" })
    );

    expect(await allCacheTablesEmpty()).toBe(true);

    const session = await db.session.get(1);
    expect(session?.tenant_id).toBe("tenant-b");

    const notice = consumeSessionClearNotice();
    expect(notice).not.toBeNull();
    expect(notice?.reason).toBe("TENANT_CHANGED");
    expect(notice?.summary.total).toBeGreaterThan(0);
  });

  it("Teste 2 — salvar a mesma sessão (tenant/user/device iguais) não limpa o cache", async () => {
    const session = buildSession();
    await db.session.put(session);
    await seedCacheTables();

    await useSessionStore.getState().saveSession({ ...session, last_sync_at: "2026-07-20T00:00:00.000Z" });

    expect(await db.fazendas.count()).toBe(1);
    expect(await db.talhoes.count()).toBe(1);
    expect(consumeSessionClearNotice()).toBeNull();
  });

  it("Teste 3 — clearSession() detecta pendências, limpa tabelas e remove a sessão", async () => {
    await db.session.put(buildSession());
    await seedCacheTables();
    await seedPendingWork();

    await useSessionStore.getState().clearSession("DEVICE_REVOKED");

    expect(await allCacheTablesEmpty()).toBe(true);
    expect(await db.session.get(1)).toBeUndefined();

    const state = useSessionStore.getState();
    expect(state.session).toBeNull();
    expect(state.isAuthenticated).toBe(false);

    const notice = consumeSessionClearNotice();
    expect(notice).not.toBeNull();
    expect(notice?.reason).toBe("DEVICE_REVOKED");
    expect(notice?.summary.syncQueue).toBe(1);
    expect(notice?.summary.tasks).toBe(1);
    expect(notice?.summary.cadernoEvents).toBe(1);
    expect(notice?.summary.cadernoDrafts).toBe(1);
    expect(notice?.summary.requisicaoOperacoes).toBe(1);
  });

  it("Teste 4 — itens já concluídos/sincronizados não geram aviso de pendência", async () => {
    await db.session.put(buildSession());

    await db.sync_queue.add({
      id: "queue-done",
      operation: "CREATE",
      entity_type: "task",
      entity_id: "task-done",
      payload: {},
      created_at: new Date().toISOString(),
      attempts: 0,
      status: "DONE",
    });

    await db.tasks.add({
      id: "task-done",
      type: "APLICACAO_DEFENSIVO",
      module: "agricola",
      fazenda_id: "fazenda-1",
      status: "CONCLUIDA",
      origem: "MANUAL",
      status_execucao: "CONCLUIDA",
      prioridade: "NORMAL",
      dados: {},
      fotos: [],
      localizacao_status: "INDISPONIVEL",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      synced: true,
    });

    await db.caderno_events.add({
      local_id: "evento-done",
      tenant_id: "tenant-a",
      descricao: "Evento sincronizado",
      safra_id: "safra-1",
      tipo_evento: "PULVERIZACAO",
      origem_evento: "PWA_OFFLINE",
      origem_tecnica: "SYNC_PWA",
      status_evento: "SINCRONIZADO",
      client_created_at: new Date().toISOString(),
      client_updated_at: new Date().toISOString(),
      device_id: "device-1",
      payload_operacional: {},
      evidencias: [],
      sync_status: "SYNCED",
      sync_attempts: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    const summary = await getLocalPendingSummary();
    expect(summary.total).toBe(0);
    expect(summary.syncQueue).toBe(0);
    expect(summary.tasks).toBe(0);
    expect(summary.cadernoEvents).toBe(0);
    expect(summary.cadernoDrafts).toBe(0);

    await useSessionStore.getState().clearSession("MANUAL_LOGOUT");
    expect(consumeSessionClearNotice()).toBeNull();
  });

  it("Teste 5 — falha no Cache Storage não bloqueia a limpeza de sessão", async () => {
    await db.session.put(buildSession());
    await seedCacheTables();

    const originalCaches = (globalThis as { caches?: unknown }).caches;
    (globalThis as { caches?: unknown }).caches = {
      delete: vi.fn().mockRejectedValue(new Error("Cache Storage indisponível")),
    };

    try {
      await useSessionStore.getState().clearSession("SESSION_INVALID");
    } finally {
      (globalThis as { caches?: unknown }).caches = originalCaches;
    }

    expect(await allCacheTablesEmpty()).toBe(true);
    expect(await db.session.get(1)).toBeUndefined();
    expect(useSessionStore.getState().isAuthenticated).toBe(false);
  });

  it("Teste 6 — nova sessão (outro tenant) não herda a fila de sincronização anterior", async () => {
    await db.session.put(buildSession());
    await seedPendingWork();

    expect(await db.sync_queue.count()).toBe(1);

    await useSessionStore.getState().saveSession(
      buildSession({ tenant_id: "tenant-b", user_id: "user-b", device_id: "device-2", device_token: "token-b" })
    );

    const remaining = await db.sync_queue.where("status").equals("PENDING").toArray();
    expect(remaining).toHaveLength(0);
    expect(await db.sync_queue.count()).toBe(0);
  });
});
