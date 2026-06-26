"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import type { LocalTask } from "@/lib/db";
import {
  buildPecuariaPesagemDados,
  buildPecuariaVacinacaoDados,
  formatPecuariaTaskType,
  parsePecuariaPesagemRows,
  parseTaskObservacoes,
  resolvePecuariaTaskKind,
  type PecaTaskAnimaisPesagemRow,
} from "@/lib/pecuaria-tasks";
import { executarTarefa, salvarDadosTarefa } from "@/lib/task-factory";

import { CampoButton, CampoPill, CampoSectionTitle, CampoSurface } from "./ui";

interface PecuariaTaskExecutionProps {
  task: LocalTask;
  canInteract: boolean;
}

function formatValue(value: unknown): string {
  if (value === null || typeof value === "undefined" || value === "") return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "—";
  if (typeof value === "boolean") return value ? "Sim" : "Não";
  return String(value);
}

export function PecuariaTaskExecution({ task, canInteract }: PecuariaTaskExecutionProps) {
  const router = useRouter();
  const kind = resolvePecuariaTaskKind(task.type);
  const [saving, setSaving] = useState(false);
  const [observacoes, setObservacoes] = useState("");
  const [rows, setRows] = useState<PecaTaskAnimaisPesagemRow[]>([]);
  const initializedTaskIdRef = useRef<string | null>(null);
  const lastSavedSnapshotRef = useRef<string>("");

  const taskDados = useMemo(() => task.dados ?? {}, [task.dados]);
  const totalAnimais = useMemo(() => {
    if (kind === "PESAGEM") return rows.length;
    const animaisIds = Array.isArray(taskDados.animais_ids)
      ? taskDados.animais_ids.filter((item): item is string => typeof item === "string")
      : [];
    if (animaisIds.length > 0) return animaisIds.length;
    if (Array.isArray(taskDados.animais)) return taskDados.animais.length;
    return 0;
  }, [kind, rows.length, taskDados.animais, taskDados.animais_ids]);

  useEffect(() => {
    if (!kind) return;
    if (initializedTaskIdRef.current === task.id) return;

    initializedTaskIdRef.current = task.id;
    const initialObservacoes = parseTaskObservacoes(taskDados);
    setObservacoes(initialObservacoes);
    if (kind === "PESAGEM") {
      setRows(parsePecuariaPesagemRows(taskDados));
    } else {
      setRows([]);
    }
    lastSavedSnapshotRef.current = JSON.stringify({
      observacoes: initialObservacoes,
      rows: kind === "PESAGEM" ? parsePecuariaPesagemRows(taskDados) : [],
    });
  }, [kind, task.id, taskDados]);

  useEffect(() => {
    if (!kind) return;
    if (task.status_execucao !== "EM_EXECUCAO") return;

    const snapshot = JSON.stringify({
      observacoes,
      rows,
    });

    if (snapshot === lastSavedSnapshotRef.current) return;

    const timeout = setTimeout(() => {
      const dados =
        kind === "PESAGEM"
          ? buildPecuariaPesagemDados(task, rows, observacoes)
          : buildPecuariaVacinacaoDados(task, observacoes);

      void salvarDadosTarefa(task.id, dados).then(() => {
        lastSavedSnapshotRef.current = snapshot;
      }).catch(() => {
        // Persistência local falhou; a próxima alteração tentará novamente.
      });
    }, 250);

    return () => clearTimeout(timeout);
  }, [kind, observacoes, rows, task.id, task.status_execucao]);

  if (!kind) {
    return null;
  }

  const loteId = formatValue(taskDados.lote_id ?? task.lote_id);
  const areaId = formatValue(taskDados.area_id);
  const dataEvento = formatValue(taskDados.data_evento ?? task.data_programada);
  const produto = formatValue(taskDados.produto_nome ?? taskDados.produto_id);
  const dose = formatValue(taskDados.dose);
  const unidadeMedida = formatValue(taskDados.unidade_medida);
  const viaAplicacao = formatValue(taskDados.via_aplicacao);

  async function handleStart() {
    if (!canInteract || saving) return;
    setSaving(true);
    try {
      const dados =
        kind === "PESAGEM"
          ? buildPecuariaPesagemDados(task, rows, observacoes)
          : buildPecuariaVacinacaoDados(task, observacoes);
      await executarTarefa(task.id, {
        status_execucao: "EM_EXECUCAO",
        dados,
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleComplete() {
    if (!canInteract || saving) return;
    if (kind === "PESAGEM") {
      const invalida = rows.some((row) => {
        const peso = Number(row.peso_kg);
        return !Number.isFinite(peso) || peso <= 0;
      });
      if (invalida) {
        alert("Preencha um peso válido maior que zero para todos os animais.");
        return;
      }
    }

    setSaving(true);
    try {
      const dados =
        kind === "PESAGEM"
          ? buildPecuariaPesagemDados(task, rows, observacoes)
          : buildPecuariaVacinacaoDados(task, observacoes);
      await executarTarefa(task.id, {
        status_execucao: "CONCLUIDA",
        dados,
        obs: observacoes.trim() || undefined,
      });
      router.replace("/home");
    } catch (error) {
      alert(error instanceof Error ? error.message : "Erro ao concluir tarefa");
    } finally {
      setSaving(false);
    }
  }

  if (task.status_execucao === "CANCELADA") {
    return (
      <CampoSurface className="flex flex-col gap-3 p-4">
        <CampoPill className="border-border bg-muted text-muted-foreground">Tarefa cancelada</CampoPill>
        <p className="text-sm text-muted-foreground">Esta tarefa foi cancelada e não pode mais ser executada.</p>
      </CampoSurface>
    );
  }

  if (task.status_execucao === "CONCLUIDA") {
    return (
      <CampoSurface className="flex flex-col gap-3 p-4">
        <CampoPill className="border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200">
          Tarefa concluída
        </CampoPill>
        <p className="text-sm text-muted-foreground">
          Esta tarefa já foi concluída e segue para sincronização quando houver conexão.
        </p>
      </CampoSurface>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <CampoSurface className="flex flex-col gap-2.5 p-4 text-sm">
        <CampoSectionTitle
          eyebrow="Pecuária"
          title={formatPecuariaTaskType(task.type)}
          description={
            kind === "PESAGEM"
              ? "Informe o peso individual de cada animal."
              : kind === "VACINACAO"
                ? "Confirme a aplicação da vacina para o lote."
                : "Confirme o evento reprodutivo para sincronização."
          }
          action={
            <CampoPill
              className={
                kind === "PESAGEM"
                  ? "border-sky-200 bg-sky-50 text-sky-800"
                  : kind === "VACINACAO"
                    ? "border-rose-200 bg-rose-50 text-rose-700"
                    : "border-emerald-200 bg-emerald-50 text-emerald-700"
              }
            >
              {kind}
            </CampoPill>
          }
        />
        <div className="mt-2 grid gap-1.5 md:grid-cols-2">
          <SummaryRow label="Lote" value={loteId} />
          <SummaryRow label="Área / piquete" value={areaId} />
          <SummaryRow label="Data" value={formatValue(dataEvento)} />
          <SummaryRow label="Animais" value={String(totalAnimais)} />
          {kind === "VACINACAO" && (
            <>
              <SummaryRow label="Produto" value={produto} />
              <SummaryRow label="Dose" value={dose} />
              <SummaryRow label="Unidade" value={unidadeMedida} />
              <SummaryRow label="Via" value={viaAplicacao} />
            </>
          )}
          {kind === "REPRODUCAO" && (
            <>
              <SummaryRow label="Animal / matriz" value={formatValue(taskDados.animal_id ?? taskDados.mae_id ?? taskDados.matriz_id)} />
              <SummaryRow label="Reprodutor" value={formatValue(taskDados.reprodutor_id ?? taskDados.touro_id)} />
              <SummaryRow label="Resultado" value={formatValue(taskDados.resultado ?? taskDados.status)} />
              <SummaryRow label="Previsão parto" value={formatValue(taskDados.previsao_parto)} />
              <SummaryRow label="Cria" value={formatValue(taskDados.cria_numero_brinco ?? taskDados.numero_brinco)} />
              <SummaryRow label="Peso cria" value={formatValue(taskDados.peso_nascimento_kg ?? taskDados.peso_desmama_kg)} />
            </>
          )}
        </div>
      </CampoSurface>

      {!canInteract && (
        <CampoSurface className="p-4">
          <p className="text-sm text-muted-foreground">Esta tarefa está atribuída a outro operador ou não pode ser editada neste dispositivo.</p>
        </CampoSurface>
      )}

      {canInteract && task.status_execucao === "PENDENTE" && (
        <CampoSurface className="flex flex-col gap-3 p-4">
          <p className="text-sm text-muted-foreground">
            A tarefa está pronta para execução offline. Inicie para liberar o formulário.
          </p>
          <CampoButton onClick={handleStart} disabled={saving} className="w-full" size="lg" variant="primary">
            {saving ? "Iniciando..." : `Iniciar ${formatPecuariaTaskType(task.type)}`}
          </CampoButton>
        </CampoSurface>
      )}

      {canInteract && task.status_execucao === "EM_EXECUCAO" && kind === "PESAGEM" && (
        <>
          <CampoSurface className="flex items-center justify-between gap-3 p-4 text-sm">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-primary">Progresso</p>
              <p className="mt-1 font-medium text-foreground">
                {rows.filter((row) => Number(row.peso_kg) > 0).length} de {rows.length} pesos preenchidos
              </p>
            </div>
            <CampoPill className="border-border bg-muted text-muted-foreground">
              Peso individual
            </CampoPill>
          </CampoSurface>

          <div className="flex flex-col gap-3">
            {rows.map((row, index) => (
              <CampoSurface key={row.animal_id} className="flex flex-col gap-3 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.16em] text-primary">Animal {index + 1}</p>
                    <p className="text-lg font-semibold text-foreground">{row.numero_brinco || row.animal_id.slice(0, 8)}</p>
                    <p className="text-xs text-muted-foreground">{row.animal_id}</p>
                  </div>
                  <CampoPill className={Number(row.peso_kg) > 0 ? "border-green-200 bg-green-50 text-green-800" : "border-amber-200 bg-amber-50 text-amber-800"}>
                    {Number(row.peso_kg) > 0 ? "Preenchido" : "Pendente"}
                  </CampoPill>
                </div>

                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Peso (kg)</span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min="0"
                    step="0.01"
                    value={row.peso_kg}
                    onChange={(event) => {
                      const value = event.target.value;
                      setRows((current) =>
                        current.map((item) => (item.animal_id === row.animal_id ? { ...item, peso_kg: value } : item))
                      );
                    }}
                    className="w-full rounded-sm border border-border bg-card px-3.5 py-3 text-base outline-none transition-colors focus:border-ring focus:bg-muted"
                    placeholder="0,00"
                  />
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Observação</span>
                  <input
                    type="text"
                    value={row.observacao}
                    onChange={(event) => {
                      const value = event.target.value;
                      setRows((current) =>
                        current.map((item) => (item.animal_id === row.animal_id ? { ...item, observacao: value } : item))
                      );
                    }}
                    className="w-full rounded-sm border border-border bg-card px-3.5 py-3 text-sm outline-none transition-colors focus:border-ring focus:bg-muted"
                    placeholder="Opcional"
                  />
                </label>
              </CampoSurface>
            ))}
          </div>

          <CampoSurface className="p-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Observações da execução</span>
              <textarea
                value={observacoes}
                onChange={(event) => setObservacoes(event.target.value)}
                rows={3}
                className="min-h-[92px] w-full resize-none rounded-sm border border-border bg-card px-3.5 py-3 text-sm outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
                placeholder="Opcional"
              />
            </label>
          </CampoSurface>

          <CampoButton
            onClick={handleComplete}
            disabled={
              saving ||
              rows.length === 0 ||
              rows.some((row) => {
                const peso = Number(row.peso_kg);
                return !Number.isFinite(peso) || peso <= 0;
              })
            }
            className="w-full"
            size="lg"
            variant="primary"
          >
            {saving ? "Concluindo..." : "Concluir pesagem"}
          </CampoButton>
        </>
      )}

      {canInteract && task.status_execucao === "EM_EXECUCAO" && kind === "VACINACAO" && (
        <>
          <CampoSurface className="flex flex-col gap-2.5 p-4 text-sm">
            <SummaryRow label="Produto" value={formatValue(taskDados.produto_nome ?? taskDados.produto_id)} />
            <SummaryRow label="Dose" value={formatValue(taskDados.dose)} />
            <SummaryRow label="Unidade" value={formatValue(taskDados.unidade_medida)} />
            <SummaryRow label="Via de aplicação" value={formatValue(taskDados.via_aplicacao)} />
            <SummaryRow label="Total de animais" value={String(totalAnimais)} />
          </CampoSurface>

          <CampoSurface className="p-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Observações da execução</span>
              <textarea
                value={observacoes}
                onChange={(event) => setObservacoes(event.target.value)}
                rows={3}
                className="min-h-[92px] w-full resize-none rounded-sm border border-border bg-card px-3.5 py-3 text-sm outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
                placeholder="Opcional"
              />
            </label>
          </CampoSurface>

          <CampoSurface className="p-4 text-sm text-muted-foreground">
            Todos os animais do lote serão considerados aplicados ao concluir esta tarefa.
          </CampoSurface>

          <CampoButton onClick={handleComplete} disabled={saving || totalAnimais === 0} className="w-full" size="lg" variant="primary">
            {saving ? "Concluindo..." : "Concluir vacinação"}
          </CampoButton>
        </>
      )}

      {canInteract && task.status_execucao === "EM_EXECUCAO" && kind === "REPRODUCAO" && (
        <CampoSurface className="flex flex-col gap-2 p-4 text-sm">
          <p className="text-xs uppercase tracking-[0.18em] text-primary">Reprodução</p>
          <p className="text-muted-foreground">
            Esta tarefa já foi materializada no momento da criação. Revise os dados e conclua para sincronizar.
          </p>
        </CampoSurface>
      )}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border py-2 last:border-0">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="text-right font-medium text-foreground">{value}</span>
    </div>
  );
}
