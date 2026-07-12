import { useLiveQuery } from "dexie-react-hooks";
import { db, type PessoaOperacional } from "@/lib/db";

export function usePessoasOperacionais(unidadeProdutivaId?: string): PessoaOperacional[] | undefined {
  return useLiveQuery(async () => {
    if (!unidadeProdutivaId) return [];
    const pessoas = await db.pessoas_operacionais
      .where("unidade_produtiva_id")
      .equals(unidadeProdutivaId)
      .toArray();

    // Ordenar alfabeticamente
    return pessoas.sort((a, b) => a.nome_exibicao.localeCompare(b.nome_exibicao));
  }, [unidadeProdutivaId]);
}
