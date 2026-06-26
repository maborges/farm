"use client";

import { useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { Scissors, Check, CheckCircle2 } from "lucide-react";

import { db } from "@/lib/db";
import { createTask } from "@/lib/task-factory";
import { useSessionStore } from "@/lib/stores/session-store";
import { TaskHeader } from "@/components/campo/task-header";
import { AnimalPicker } from "@/components/campo/animal-picker";
import { CampoButton, CampoShell, CampoSurface } from "@/components/campo/ui";
import { CampoSuccessScreen } from "@/components/campo/flow";

export default function DesmamaPage() {
  const { session } = useSessionStore();
  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(() => db.lotes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);
  const animais = useLiveQuery(() => db.animais.where("unidade_produtiva_id").equals(fazendaId).toArray(), [fazendaId]);
  const [animalId, setAnimalId] = useState("");
  const [loteDestinoId, setLoteDestinoId] = useState("");
  const [pesoDesmama, setPesoDesmama] = useState("");
  const [dataEvento, setDataEvento] = useState(new Date().toISOString().slice(0, 10));
  const [observacoes, setObservacoes] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const handleSalvar = async () => {
    if (!fazendaId || !animalId) return;
    setSaving(true);
    try {
      await createTask({
        type: "DESMAME",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteDestinoId || undefined,
        dados: {
          animal_id: animalId,
          lote_destino_id: loteDestinoId || null,
          peso_desmama_kg: Number(pesoDesmama) || null,
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
        title="Desmama registrada"
        description="Salva localmente e pronta para sincronizar."
        primaryLabel="Nova desmama"
        onPrimary={() => {
          setDone(false);
          setAnimalId("");
          setLoteDestinoId("");
          setPesoDesmama("");
          setObservacoes("");
        }}
        onSecondary={() => window.history.back()}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader title="Desmama" icon={Scissors} gpsStatus="INDISPONIVEL" step={1} totalSteps={1} domain="PECUARIA" />
      <CampoSurface className="flex flex-col gap-4 p-4">
        <AnimalPicker
          label="Animal / cria"
          animals={animais ?? []}
          lotes={lotes ?? []}
          value={animalId}
          onChange={setAnimalId}
          mode="DESMAMA"
          placeholder="Buscar cria por brinco, nome ou lote"
          emptyMessage="Nenhuma cria elegível encontrada."
        />
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Lote destino</span>
          <select value={loteDestinoId} onChange={(e) => setLoteDestinoId(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none">
            <option value="">Selecione o lote</option>
            {(lotes ?? []).map((l) => <option key={l.id} value={l.id}>{l.identificacao}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Peso à desmama (kg)</span>
          <input type="number" min={0} step={0.1} value={pesoDesmama} onChange={(e) => setPesoDesmama(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Data</span>
          <input type="date" value={dataEvento} onChange={(e) => setDataEvento(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Observações</span>
          <textarea value={observacoes} onChange={(e) => setObservacoes(e.target.value)} rows={3} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" />
        </label>
        <CampoButton onClick={handleSalvar} disabled={saving || !animalId} className="w-full" variant="primary">
          {saving ? "Salvando..." : <><Check className="mr-2 size-4" />Salvar desmama</>}
        </CampoButton>
      </CampoSurface>
    </CampoShell>
  );
}
