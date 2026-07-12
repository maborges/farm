import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db, generatePessoaOperacionalId } from "@/lib/db";

describe("Database Upgrade - Fase 2C", () => {
  beforeEach(async () => {
    await db.delete();
    await db.open();
  });

  afterEach(async () => {
    await db.delete();
  });

  it("cria a nova store pessoas_operacionais corretamente", async () => {
    expect(db.pessoas_operacionais).toBeDefined();

    const id = generatePessoaOperacionalId("up-1", "pessoa-1");
    await db.pessoas_operacionais.add({
      id,
      pessoa_id: "pessoa-1",
      nome_exibicao: "Teste",
      unidade_produtiva_id: "up-1",
      papeis: ["PAPEL_TESTE"]
    });

    const pessoas = await db.pessoas_operacionais.toArray();
    expect(pessoas).toHaveLength(1);
    expect(pessoas[0].id).toBe(id);
  });

  it("consulta por Unidade e não retorna Pessoas de outra Unidade", async () => {
    const p1 = {
      id: generatePessoaOperacionalId("up-1", "pessoa-1"),
      pessoa_id: "pessoa-1",
      nome_exibicao: "Pessoa 1",
      unidade_produtiva_id: "up-1",
      papeis: ["PAPEL"]
    };
    const p2 = {
      id: generatePessoaOperacionalId("up-2", "pessoa-2"),
      pessoa_id: "pessoa-2",
      nome_exibicao: "Pessoa 2",
      unidade_produtiva_id: "up-2",
      papeis: ["PAPEL"]
    };
    await db.pessoas_operacionais.bulkAdd([p1, p2]);

    const result = await db.pessoas_operacionais.where("unidade_produtiva_id").equals("up-1").toArray();
    expect(result).toHaveLength(1);
    expect(result[0].pessoa_id).toBe("pessoa-1");
  });

  it("upgrade preserva a store legada colaboradores", () => {
    expect(db.colaboradores).toBeDefined();
  });
});
