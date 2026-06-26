"use client";

import { useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { Baby, Check, CheckCircle2 } from "lucide-react";

import { db } from "@/lib/db";
import { createTask } from "@/lib/task-factory";
import { useSessionStore } from "@/lib/stores/session-store";
import { TaskHeader } from "@/components/campo/task-header";
import { AnimalPicker } from "@/components/campo/animal-picker";
import { CampoButton, CampoShell, CampoSurface } from "@/components/campo/ui";
import { CampoSuccessScreen } from "@/components/campo/flow";

export default function PartoPage() {
  const { session } = useSessionStore();
  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(() => db.lotes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);
  const animais = useLiveQuery(() => db.animais.where("unidade_produtiva_id").equals(fazendaId).toArray(), [fazendaId]);
  const [loteId, setLoteId] = useState("");
  const [maeId, setMaeId] = useState("");
  const [reprodutorId, setReprodutorId] = useState("");
  const [sexoCria, setSexoCria] = useState("MACHO");
  const [pesoCria, setPesoCria] = useState("");
  const [brincoCria, setBrincoCria] = useState("");
  const [dataEvento, setDataEvento] = useState(new Date().toISOString().slice(0, 10));
  const [observacoes, setObservacoes] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const handleSalvar = async () => {
    if (!fazendaId || !loteId || !maeId) return;
    setSaving(true);
    try {
      await createTask({
        type: "PARTO_REGISTRO",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId,
        dados: {
          lote_id: loteId,
          mae_id: maeId,
          reprodutor_id: reprodutorId || null,
          sexo_cria: sexoCria,
          peso_nascimento_kg: Number(pesoCria) || null,
          cria_numero_brinco: brincoCria || null,
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
        title="Parto registrado"
        description="A cria será materializada na sincronização."
        primaryLabel="Novo parto"
        onPrimary={() => {
          setDone(false);
          setMaeId("");
          setReprodutorId("");
          setPesoCria("");
          setBrincoCria("");
        }}
        onSecondary={() => window.history.back()}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader title="Parto" icon={Baby} gpsStatus="INDISPONIVEL" step={1} totalSteps={1} domain="PECUARIA" />
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
          value={maeId}
          onChange={setMaeId}
          mode="PARTO"
          loteId={loteId}
          placeholder="Buscar matriz prenhe por brinco, nome ou lote"
          emptyMessage="Nenhuma matriz prenhe encontrada."
        />
        <AnimalPicker
          label="Reprodutor / pai"
          animals={animais ?? []}
          lotes={lotes ?? []}
          value={reprodutorId}
          onChange={setReprodutorId}
          mode="GERAL"
          placeholder="Buscar pai por identificação, nome ou lote"
          emptyMessage="Nenhum reprodutor encontrado."
        />
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Sexo da cria</span>
          <select value={sexoCria} onChange={(e) => setSexoCria(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none">
            <option value="MACHO">Macho</option>
            <option value="FEMEA">Fêmea</option>
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Peso ao nascer (kg)</span>
          <input type="number" min={0} step={0.1} value={pesoCria} onChange={(e) => setPesoCria(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Brinco da cria</span>
          <input value={brincoCria} onChange={(e) => setBrincoCria(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" placeholder="Opcional" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Data</span>
          <input type="date" value={dataEvento} onChange={(e) => setDataEvento(e.target.value)} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-muted-foreground">Observações</span>
          <textarea value={observacoes} onChange={(e) => setObservacoes(e.target.value)} rows={3} className="rounded-sm border border-border bg-card px-3 py-2.5 text-sm outline-none" />
        </label>
        <CampoButton onClick={handleSalvar} disabled={saving || !loteId || !maeId} className="w-full" variant="primary">
          {saving ? "Salvando..." : <><Check className="mr-2 size-4" />Salvar parto</>}
        </CampoButton>
      </CampoSurface>
    </CampoShell>
  );
}
