"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";
import { useGps } from "@/hooks/useGps";
import { useCamera } from "@/hooks/useCamera";
import { createTask } from "@/lib/task-factory";
import { useSessionStore } from "@/lib/stores/session-store";
import { TaskHeader } from "@/components/campo/task-header";
import { FieldSelect } from "@/components/campo/field-select";
import { NumPad } from "@/components/campo/num-pad";
import { CameraCapture } from "@/components/campo/camera-capture";
import { GpsWarning } from "@/components/campo/gps-warning";

type Step = "lote" | "vacina" | "confirmar";

export default function VacinacaoPage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();

  const [step, setStep] = useState<Step>("lote");
  const [loteId, setLoteId] = useState("");
  const [vacinaId, setVacinaId] = useState("");
  const [vacinaNome, setVacinaNome] = useState("");
  const [quantidade, setQuantidade] = useState("");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(() => db.lotes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);
  const vacinas = useLiveQuery(
    () => db.insumos.filter((i) => i.tipo === "VETERINARIO" || i.tipo === "VACINA" || i.nome.toLowerCase().includes("vacin")).toArray(),
    []
  );

  const stepIndex = ["lote", "vacina", "confirmar"].indexOf(step);
  const loteAtual = lotes?.find((l) => l.id === loteId);

  const handleSalvar = async () => {
    setSaving(true);
    try {
      await createTask({
        type: "VACINACAO_LOTE",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId || undefined,
        dados: {
          vacina_id: vacinaId || null,
          vacina_nome: vacinaNome,
          dose_ml: parseFloat(quantidade) || 0,
          quantidade_animais: loteAtual?.quantidade_cabecas ?? 0,
          obs,
        },
        fotos: cam.fotos,
        localizacao_status: gps.status,
        latitude: gps.latitude ?? undefined,
        longitude: gps.longitude ?? undefined,
      });
      setDone(true);
    } finally {
      setSaving(false);
    }
  };

  if (done) {
    return (
      <SuccessScreen
        onNew={() => { setDone(false); setStep("lote"); setLoteId(""); setVacinaId(""); setQuantidade(""); }}
        onHome={() => router.replace("/home")}
      />
    );
  }

  return (
    <div className="flex flex-col gap-5 p-4 pb-10 min-h-dvh">
      <TaskHeader title="Vacinação" icon="💉" gpsStatus={gps.status} step={stepIndex + 1} totalSteps={3} />

      {step === "lote" && (
        <div className="flex flex-col gap-5 flex-1">
          <FieldSelect
            label="Lote de Animais"
            options={(lotes ?? []).map((l) => ({
              id: l.id,
              label: l.identificacao,
              sublabel: `${l.especie} · ${l.quantidade_cabecas} cabeças`,
            }))}
            value={loteId}
            onChange={setLoteId}
            placeholder="Selecione o lote"
          />
          <div className="flex gap-3 mt-auto">
            <button onClick={() => router.back()} className="flex-1 bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar</button>
            <button onClick={() => setStep("vacina")} disabled={!loteId}
              className="flex-[2] bg-green-600 disabled:opacity-40 rounded-2xl py-4 font-semibold">Próximo →</button>
          </div>
        </div>
      )}

      {step === "vacina" && (
        <div className="flex flex-col gap-5 flex-1">
          {(vacinas ?? []).length > 0 ? (
            <FieldSelect
              label="Vacina"
              options={(vacinas ?? []).map((v) => ({ id: v.id, label: v.nome, sublabel: v.unidade_medida ?? undefined }))}
              value={vacinaId}
              onChange={(id) => {
                setVacinaId(id);
                const v = vacinas?.find((v) => v.id === id);
                if (v) setVacinaNome(v.nome);
              }}
              placeholder="Selecione a vacina"
            />
          ) : (
            /* Fallback: digitar nome da vacina */
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-neutral-400">Nome da Vacina</label>
              <input
                placeholder="Ex: Febre Aftosa, Brucelose..."
                value={vacinaNome}
                onChange={(e) => setVacinaNome(e.target.value)}
                className="bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-4 text-base outline-none focus:border-green-500"
              />
            </div>
          )}

          <NumPad value={quantidade} onChange={setQuantidade} suffix="mL/animal" label="Dose por animal (mL)" />

          <div className="flex gap-3 mt-auto">
            <button onClick={() => setStep("lote")} className="flex-1 bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar</button>
            <button onClick={() => setStep("confirmar")} disabled={!vacinaNome && !vacinaId}
              className="flex-[2] bg-green-600 disabled:opacity-40 rounded-2xl py-4 font-semibold">Próximo →</button>
          </div>
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-col gap-5 flex-1">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          <div className="bg-neutral-800 rounded-2xl p-4 flex flex-col gap-2 text-sm">
            <SummaryRow label="Lote" value={loteAtual?.identificacao ?? "—"} />
            <SummaryRow label="Animais" value={String(loteAtual?.quantidade_cabecas ?? "—")} />
            <SummaryRow label="Vacina" value={vacinaNome || (vacinas?.find((v) => v.id === vacinaId)?.nome ?? "—")} />
            {quantidade && <SummaryRow label="Dose" value={`${quantidade} mL/animal`} />}
          </div>

          <textarea
            placeholder="Observação (ex: lote do pasto 3, vermifugação junto)"
            value={obs}
            onChange={(e) => setObs(e.target.value)}
            rows={3}
            className="bg-neutral-800 border border-neutral-700 rounded-2xl px-4 py-3 text-sm resize-none outline-none focus:border-green-500 placeholder:text-neutral-600"
          />

          <CameraCapture fotos={cam.fotos} inputRef={cam.inputRef} canAddMore={cam.canAddMore} onOpen={cam.openCamera} onFileChange={cam.handleFileChange} onRemove={cam.removePhoto} />

          <button onClick={handleSalvar} disabled={saving}
            className="mt-auto bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded-2xl py-5 text-base font-bold">
            {saving ? "Salvando..." : "✅ Salvar Vacinação"}
          </button>
        </div>
      )}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-neutral-500">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}

function SuccessScreen({ onNew, onHome }: { onNew: () => void; onHome: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 min-h-dvh p-6">
      <div className="text-6xl">✅</div>
      <div className="text-center">
        <h2 className="text-xl font-bold">Vacinação Registrada!</h2>
        <p className="text-sm text-neutral-400 mt-1">Salvo localmente. Será sincronizado quando online.</p>
      </div>
      <div className="flex flex-col gap-3 w-full max-w-sm">
        <button onClick={onNew} className="bg-green-600 rounded-2xl py-4 font-semibold">Nova Vacinação</button>
        <button onClick={onHome} className="bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar ao Início</button>
      </div>
    </div>
  );
}
