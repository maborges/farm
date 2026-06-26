"use client";

import { useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { HeartPulse, Check, CheckCircle2 } from "lucide-react";

import { db } from "@/lib/db";
import { createTask } from "@/lib/task-factory";
import { useSessionStore } from "@/lib/stores/session-store";
import { TaskHeader } from "@/components/campo/task-header";
import { AnimalPicker } from "@/components/campo/animal-picker";
import { CampoButton, CampoShell, CampoSurface } from "@/components/campo/ui";
import { CampoSuccessScreen } from "@/components/campo/flow";

export default function DiagnosticoPrenhezPage() {
  const { session } = useSessionStore();
  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(() => db.lotes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);
  const animais = useLiveQuery(() => db.animais.where("unidade_produtiva_id").equals(fazendaId).toArray(), [fazendaId]);
  const [loteId, setLoteId] = useState("");
  const [matrizId, setMatrizId] = useState("");
  const [resultado, setResultado] = useState("PRENHE");
  const [previsaoParto, setPrevisaoParto] = useState("");
  const [dataEvento, setDataEvento] = useState(new Date().toISOString().slice(0, 10));
  const [observacoes, setObservacoes] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const handleSalvar = async () => {
    if (!fazendaId || !loteId || !matrizId) return;
    setSaving(true);
    try {
      await createTask({
        type: "DIAGNOSTICO_PRENHEZ",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId,
        dados: {
          lote_id: loteId,
          animal_id: matrizId,
          resultado,
          previsao_parto: previsaoParto || null,
          data_evento: `${dataEvento}T00:00:00Z`,
          observacoes,
        },
        localizacao_status: "INDISPONIVEL",
      });
      setDone(true);
    } finally {
      setSaving(false);
    }
  };

  if (done) {
    return (
      <CampoSuccessScreen
        icon={CheckCircle2}
        title="Diagnóstico registrado"
        description="Salvo localmente e pronto para sincronizar."
        primaryLabel="Novo diagnóstico"
        onPrimary={() => {
          setDone(false);
          setMatrizId("");
          setPrevisaoParto("");
          setObservacoes("");
        }}
        onSecondary={() => window.history.back()}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader title="Diagnóstico de prenhez" icon={HeartPulse} gpsStatus="INDISPONIVEL" step={1} totalSteps={1} domain="PECUARIA" />
      <CampoSurface className="flex flex-col gap-4 p-4">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Lote</span>
          <select value={loteId} onChange={(e) => setLoteId(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none">
            <option value="">Selecione o lote</option>
            {(lotes ?? []).map((l) => <option key={l.id} value={l.id}>{l.identificacao}</option>)}
          </select>
        </label>
        <AnimalPicker
          label="Matriz"
          animals={animais ?? []}
          lotes={lotes ?? []}
          value={matrizId}
          onChange={setMatrizId}
          mode="DIAGNOSTICO"
          loteId={loteId}
          placeholder="Buscar matriz coberta por brinco, nome ou lote"
          emptyMessage="Nenhuma matriz elegível encontrada."
        />
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Resultado</span>
          <select value={resultado} onChange={(e) => setResultado(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none">
            <option value="PRENHE">Prenhe</option>
            <option value="VAZIA">Vazia</option>
            <option value="INCONCLUSIVO">Inconclusivo</option>
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Previsão de parto</span>
          <input type="date" value={previsaoParto} onChange={(e) => setPrevisaoParto(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Data</span>
          <input type="date" value={dataEvento} onChange={(e) => setDataEvento(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Observações</span>
          <textarea value={observacoes} onChange={(e) => setObservacoes(e.target.value)} rows={3} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" />
        </label>
        <CampoButton onClick={handleSalvar} disabled={saving || !loteId || !matrizId} className="w-full" variant="primary">
          {saving ? "Salvando..." : <><Check className="mr-2 size-4" />Salvar diagnóstico</>}
        </CampoButton>
      </CampoSurface>
    </CampoShell>
  );
}
