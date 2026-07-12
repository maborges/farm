import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db, generatePessoaOperacionalId } from "@/lib/db";
import { pullSync } from "@/lib/sync/pull";
import { useSessionStore } from "@/lib/stores/session-store";

// Mock do fetch global
global.fetch = async () => ({} as Response);

describe("Sync Pull - Fase 2C", () => {
  const MOCK_DEVICE_TOKEN = "mocked-device-token";
  const UP_1 = "uuid-up-1";
  const UP_2 = "uuid-up-2";
  const PESSOA_1 = "uuid-pessoa-1";
  
  beforeEach(async () => {
    useSessionStore.setState({
      session: {
        id: 1,
        user_id: "user-1",
        tenant_id: "tenant-1",
        device_id: "device-1",
        device_token: MOCK_DEVICE_TOKEN,
        pin_hash: "hash",
        user_name: "Test User",
        last_sync_at: null,
        modules: ["agricola"],
        fazenda_ids: [UP_1, UP_2]
      }
    });

    // Reset BD
    await db.delete();
    await db.open();
  });

  afterEach(async () => {
    await db.delete();
  });

  it("1. converte payload backend em registro Dexie (preserva múltiplos papéis e mesma pessoa em duas UPs)", async () => {
    const payload = {
      sync_at: new Date().toISOString(),
      pessoas_operacionais: [
        {
          pessoa_id: PESSOA_1,
          nome_exibicao: "João",
          unidade_produtiva_id: UP_1,
          papeis: ["OPERADOR", "GERENTE", "OPERADOR"] // Teste de deduplicação
        },
        {
          pessoa_id: PESSOA_1,
          nome_exibicao: "João",
          unidade_produtiva_id: UP_2,
          papeis: ["MECANICO"] // Mesma pessoa, outra UP
        }
      ]
    };

    global.fetch = async () => ({
      ok: true,
      json: async () => payload
    } as Response);

    await pullSync();

    const pessoas = await db.pessoas_operacionais.toArray();
    expect(pessoas).toHaveLength(2);

    const jpUp1 = pessoas.find(p => p.unidade_produtiva_id === UP_1);
    expect(jpUp1).toBeDefined();
    expect(jpUp1?.id).toBe(generatePessoaOperacionalId(UP_1, PESSOA_1));
    expect(jpUp1?.papeis).toEqual(["OPERADOR", "GERENTE"]); // Deduplicou

    const jpUp2 = pessoas.find(p => p.unidade_produtiva_id === UP_2);
    expect(jpUp2).toBeDefined();
    expect(jpUp2?.id).toBe(generatePessoaOperacionalId(UP_2, PESSOA_1));
    expect(jpUp2?.papeis).toEqual(["MECANICO"]);
  });

  it("15. resposta vazia limpa a store quando o bloco está presente", async () => {
    // Insere dado pré-existente
    await db.pessoas_operacionais.put({
      id: generatePessoaOperacionalId(UP_1, PESSOA_1),
      pessoa_id: PESSOA_1,
      nome_exibicao: "Old Joao",
      unidade_produtiva_id: UP_1,
      papeis: ["OLD"]
    });

    let pessoas = await db.pessoas_operacionais.toArray();
    expect(pessoas).toHaveLength(1);

    const payload = {
      sync_at: new Date().toISOString(),
      pessoas_operacionais: [] // Bloco presente, mas vazio
    };

    global.fetch = async () => ({
      ok: true,
      json: async () => payload
    } as Response);

    await pullSync();

    pessoas = await db.pessoas_operacionais.toArray();
    expect(pessoas).toHaveLength(0); // Limpou corretamente
  });

  it("16. bloco ausente não quebra nem apaga indevidamente", async () => {
    await db.pessoas_operacionais.put({
      id: generatePessoaOperacionalId(UP_1, PESSOA_1),
      pessoa_id: PESSOA_1,
      nome_exibicao: "Old Joao",
      unidade_produtiva_id: UP_1,
      papeis: ["OLD"]
    });

    const payload = {
      sync_at: new Date().toISOString(),
      // pessoas_operacionais ausente (e.g. backend antigo)
    };

    global.fetch = async () => ({
      ok: true,
      json: async () => payload
    } as Response);

    await pullSync();

    const pessoas = await db.pessoas_operacionais.toArray();
    expect(pessoas).toHaveLength(1); // Não apagou
  });
});
