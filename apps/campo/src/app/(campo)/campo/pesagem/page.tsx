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

type Step = "lote" | "peso" | "confirmar";
type TipoPesagem = "AMOSTRA" | "LOTE_BALANCA" | "INDIVIDUAL";

export default function PesagemPage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();

  const [step, setStep] = useState<Step>("lote");
  const [loteId, setLoteId] = useState("");
  const [tipo, setTipo] = useState<TipoPesagem>("AMOSTRA");
  const [pesoMedio, setPesoMedio] = useState("");
  const [qtdAnimais, setQtdAnimais] = useState("");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(() => db.lotes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);

  const stepIndex = ["lote", "peso", "confirmar"].indexOf(step);

  const handleSalvar = async () => {
    setSaving(true);
    try {
      await createTask({
        type: "PESAGEM_ANIMAL",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId || undefined,
        dados: {
          tipo_pesagem: tipo,
          peso_medio_kg: parseFloat(pesoMedio) || 0,
          quantidade_animais: parseInt(qtdAnimais) || 0,
          peso_total_estimado: (parseFloat(pesoMedio) || 0) * (parseInt(qtdAnimais) || 1),
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
        onNew={() => { setDone(false); setStep("lote"); setLoteId(""); setPesoMedio(""); setQtdAnimais(""); }}
        onHome={() => router.replace("/home")}
      />
    );
  }

  const loteAtual = lotes?.find((l) => l.id === loteId);

  return (
    <div className="flex flex-col gap-5 p-4 pb-10 min-h-dvh">
      <TaskHeader title="Pesagem" icon="⚖️" gpsStatus={gps.status} step={stepIndex + 1} totalSteps={3} />

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
          {/* Tipo de pesagem */}
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-neutral-400">Tipo</label>
            <div className="grid grid-cols-3 gap-2">
              {(["AMOSTRA", "LOTE_BALANCA", "INDIVIDUAL"] as TipoPesagem[]).map((t) => (
                <button key={t} type="button" onClick={() => setTipo(t)}
                  className={`rounded-xl py-4 text-xs font-semibold transition-colors ${tipo === t ? "bg-green-600" : "bg-neutral-800"}`}>
                  {t === "AMOSTRA" ? "Amostra" : t === "LOTE_BALANCA" ? "Balança" : "Individual"}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-3 mt-auto">
            <button onClick={() => router.back()} className="flex-1 bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar</button>
            <button onClick={() => setStep("peso")} disabled={!loteId}
              className="flex-[2] bg-green-600 disabled:opacity-40 rounded-2xl py-4 font-semibold">Próximo →</button>
          </div>
        </div>
      )}

      {step === "peso" && (
        <div className="flex flex-col gap-5 flex-1">
          <NumPad value={pesoMedio} onChange={setPesoMedio} suffix="kg" label="Peso médio (kg/animal)" />
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-neutral-400">
              Nº de animais pesados (padrão: {loteAtual?.quantidade_cabecas ?? "—"})
            </label>
            <input
              type="number"
              inputMode="numeric"
              placeholder={String(loteAtual?.quantidade_cabecas ?? "")}
              value={qtdAnimais}
              onChange={(e) => setQtdAnimais(e.target.value)}
              className="bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-base outline-none focus:border-green-500"
            />
          </div>
          <div className="flex gap-3 mt-auto">
            <button onClick={() => setStep("lote")} className="flex-1 bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar</button>
            <button onClick={() => setStep("confirmar")} disabled={!pesoMedio || pesoMedio === "0"}
              className="flex-[2] bg-green-600 disabled:opacity-40 rounded-2xl py-4 font-semibold">Próximo →</button>
          </div>
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-col gap-5 flex-1">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          <div className="bg-neutral-800 rounded-2xl p-4 flex flex-col gap-2 text-sm">
            <SummaryRow label="Lote" value={loteAtual?.identificacao ?? "—"} />
            <SummaryRow label="Tipo" value={tipo} />
            <SummaryRow label="Peso médio" value={`${pesoMedio} kg`} />
            <SummaryRow label="Animais" value={qtdAnimais || String(loteAtual?.quantidade_cabecas ?? "—")} />
            <SummaryRow label="Peso total est." value={`${((parseFloat(pesoMedio) || 0) * (parseInt(qtdAnimais) || loteAtual?.quantidade_cabecas || 1)).toFixed(0)} kg`} />
          </div>

          <textarea
            placeholder="Observação (opcional)"
            value={obs}
            onChange={(e) => setObs(e.target.value)}
            rows={2}
            className="bg-neutral-800 border border-neutral-700 rounded-2xl px-4 py-3 text-sm resize-none outline-none focus:border-green-500 placeholder:text-neutral-600"
          />

          <CameraCapture fotos={cam.fotos} inputRef={cam.inputRef} canAddMore={cam.canAddMore} onOpen={cam.openCamera} onFileChange={cam.handleFileChange} onRemove={cam.removePhoto} />

          <button onClick={handleSalvar} disabled={saving}
            className="mt-auto bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded-2xl py-5 text-base font-bold">
            {saving ? "Salvando..." : "✅ Salvar Pesagem"}
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
        <h2 className="text-xl font-bold">Pesagem Registrada!</h2>
        <p className="text-sm text-neutral-400 mt-1">Salvo localmente. Será sincronizado quando online.</p>
      </div>
      <div className="flex flex-col gap-3 w-full max-w-sm">
        <button onClick={onNew} className="bg-green-600 rounded-2xl py-4 font-semibold">Nova Pesagem</button>
        <button onClick={onHome} className="bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar ao Início</button>
      </div>
    </div>
  );
}
