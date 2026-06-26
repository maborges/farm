import type { LocalTask } from "./db";
import { resolvePecuariaTaskKind } from "./pecuaria-tasks";

export type TaskDomain = "AGRICULTURA" | "PECUARIA";

const AGRICULTURA_TASK_TYPES = new Set([
  "APLICACAO_DEFENSIVO",
  "APLICACAO_FERTILIZANTE",
  "COLHEITA_REGISTRO",
  "PREPARO_SOLO",
  "PLANTIO_REGISTRO",
  "IRRIGACAO_EVENTO",
  "MONITORAMENTO_PRAGA",
  "AMOSTRAGEM_SOLO",
  "CHECKLIST_CAMPO",
  "ABASTECIMENTO_MAQUINA",
  "MANUTENCAO_OCORRENCIA",
]);

export function resolveTaskDomain(task: Pick<LocalTask, "module" | "type"> | { module?: string; type?: string }): TaskDomain {
  if (task.module === "pecuaria") {
    return "PECUARIA";
  }

  if (task.module === "agricola") {
    return "AGRICULTURA";
  }

  const type = (task.type ?? "").toUpperCase();
  if (
    resolvePecuariaTaskKind(type) ||
    type === "PESAGEM_ANIMAL" ||
    type === "VACINACAO_LOTE" ||
    type === "COBERTURA" ||
    type === "DIAGNOSTICO_PRENHEZ" ||
    type === "DESMAME" ||
    type === "PARTO" ||
    type === "PARTO_REGISTRO"
  ) {
    return "PECUARIA";
  }

  if (AGRICULTURA_TASK_TYPES.has(type)) {
    return "AGRICULTURA";
  }

  return "AGRICULTURA";
}

export function formatTaskDomainLabel(domain: TaskDomain): string {
  return domain === "PECUARIA" ? "Pecuária" : "Agricultura";
}
