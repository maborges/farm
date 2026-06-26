import type { LocalTask } from "./db";

export const PECUARIA_TASK_KIND = {
  PESAGEM: "PESAGEM",
  VACINACAO: "VACINACAO",
  REPRODUCAO: "REPRODUCAO",
} as const;

const PECUARIA_TASK_ALIASES = new Set([
  "PESAGEM",
  "PESAGEM_ANIMAL",
  "VACINACAO",
  "VACINACAO_LOTE",
  "COBERTURA",
  "INSEMINACAO",
  "DIAGNOSTICO_PRENHEZ",
  "PARTO",
  "PARTO_REGISTRO",
  "DESMAME",
]);

export type PecuariaTaskKind = (typeof PECUARIA_TASK_KIND)[keyof typeof PECUARIA_TASK_KIND];

export interface PecaTaskAnimaisPesagemRow {
  animal_id: string;
  numero_brinco: string;
  peso_kg: string;
  observacao: string;
}

export function isPecuariaTaskType(type: string): boolean {
  return PECUARIA_TASK_ALIASES.has(type);
}

export function resolvePecuariaTaskKind(type: string): PecuariaTaskKind | null {
  if (type === PECUARIA_TASK_KIND.PESAGEM || type === "PESAGEM_ANIMAL") {
    return PECUARIA_TASK_KIND.PESAGEM;
  }
  if (type === PECUARIA_TASK_KIND.VACINACAO || type === "VACINACAO_LOTE") {
    return PECUARIA_TASK_KIND.VACINACAO;
  }
  if (PECUARIA_TASK_ALIASES.has(type) && type !== "PESAGEM" && type !== "PESAGEM_ANIMAL" && type !== "VACINACAO" && type !== "VACINACAO_LOTE") {
    return PECUARIA_TASK_KIND.REPRODUCAO;
  }
  return null;
}

export function formatPecuariaTaskType(type: string): string {
  const kind = resolvePecuariaTaskKind(type);
  if (kind === PECUARIA_TASK_KIND.PESAGEM) return "Pesagem";
  if (kind === PECUARIA_TASK_KIND.VACINACAO) return "Vacinação";
  if (kind === PECUARIA_TASK_KIND.REPRODUCAO) {
    if (type === "COBERTURA") return "Cobertura";
    if (type === "INSEMINACAO") return "Inseminação";
    if (type === "DIAGNOSTICO_PRENHEZ") return "Diagnóstico de prenhez";
    if (type === "PARTO_REGISTRO" || type === "PARTO") return "Parto";
    if (type === "DESMAME") return "Desmama";
    return "Reprodução";
  }
  return type;
}

export function parseTaskObservacoes(dados: Record<string, unknown>): string {
  const value = dados.observacoes ?? dados.obs_execucao ?? dados.obs;
  return typeof value === "string" ? value : "";
}

export function parsePecuariaPesagemRows(dados: Record<string, unknown>): PecaTaskAnimaisPesagemRow[] {
  const animais = Array.isArray(dados.animais) ? dados.animais : [];
  if (animais.length > 0) {
    return animais
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        const row = item as Record<string, unknown>;
        const animalId = row.animal_id;
        if (typeof animalId !== "string" || !animalId) return null;
        return {
          animal_id: animalId,
          numero_brinco: typeof row.numero_brinco === "string" ? row.numero_brinco : "",
          peso_kg: typeof row.peso_kg === "number" && Number.isFinite(row.peso_kg) ? String(row.peso_kg) : "",
          observacao: typeof row.observacao === "string" ? row.observacao : "",
        };
      })
      .filter((row): row is PecaTaskAnimaisPesagemRow => row !== null);
  }

  const animaisIds = Array.isArray(dados.animais_ids) ? dados.animais_ids : [];
  return animaisIds
    .map((item) => (typeof item === "string" ? item : null))
    .filter((item): item is string => Boolean(item))
    .map((animalId) => ({
      animal_id: animalId,
      numero_brinco: "",
      peso_kg: "",
      observacao: "",
    }));
}

export function buildPecuariaPesagemDados(
  task: LocalTask,
  rows: PecaTaskAnimaisPesagemRow[],
  observacoes: string
): Record<string, unknown> {
  const base = task.dados ?? {};
  const animais = rows.map((row) => ({
    animal_id: row.animal_id,
    numero_brinco: row.numero_brinco || null,
    peso_kg: row.peso_kg ? Number(row.peso_kg) : null,
    observacao: row.observacao.trim() || null,
  }));

  return {
    ...base,
    lote_id: typeof base.lote_id === "string" ? base.lote_id : task.lote_id ?? null,
    area_id: typeof base.area_id === "string" ? base.area_id : null,
    data_evento:
      typeof base.data_evento === "string"
        ? base.data_evento
        : task.data_programada
          ? `${task.data_programada}T00:00:00Z`
          : null,
    tipo: "PESAGEM",
    observacoes: observacoes.trim(),
    animais,
    animais_ids: animais.map((animal) => animal.animal_id),
  };
}

export function buildPecuariaVacinacaoDados(task: LocalTask, observacoes: string): Record<string, unknown> {
  const base = task.dados ?? {};
  const animaisIds = Array.isArray(base.animais_ids)
    ? base.animais_ids.filter((item): item is string => typeof item === "string" && item.length > 0)
    : [];

  return {
    ...base,
    lote_id: typeof base.lote_id === "string" ? base.lote_id : task.lote_id ?? null,
    area_id: typeof base.area_id === "string" ? base.area_id : null,
    data_evento:
      typeof base.data_evento === "string"
        ? base.data_evento
        : task.data_programada
          ? `${task.data_programada}T00:00:00Z`
          : null,
    tipo: "VACINACAO",
    observacoes: observacoes.trim(),
    animais_ids: animaisIds,
  };
}
