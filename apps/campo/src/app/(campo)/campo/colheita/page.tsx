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

type Step = "local" | "quantidade" | "confirmar";

const UNIDADES = ["sc", "kg", "t", "cx"];

export default function ColheitaPage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();

  const [step, setStep] = useState<Step>("local");
  const [talhaoId, setTalhaoId] = useState("");
  const [quantidade, setQuantidade] = useState("");
  const [unidade, setUnidade] = useState("sc");
  const [umidade, setUmidade] = useState("");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.fazenda_ids?.[0] ?? "";
  const talhoes = useLiveQuery(() => db.talhoes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);

  const stepIndex = ["local", "quantidade", "confirmar"].indexOf(step);

  const handleSalvar = async () => {
    setSaving(true);
    try {
      await createTask({
        type: "COLHEITA_REGISTRO",
        module: "agricola",
        fazenda_id: fazendaId,
        talhao_id: talhaoId || undefined,
        dados: {
          quantidade: parseFloat(quantidade) || 0,
          unidade,
          umidade_perc: parseFloat(umidade) || null,
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
        onNew={() => { setDone(false); setStep("local"); setTalhaoId(""); setQuantidade(""); }}
        onHome={() => router.replace("/home")}
      />
    );
  }

  return (
    <div className="flex flex-col gap-5 p-4 pb-10 min-h-dvh">
      <TaskHeader title="Colheita" icon="🌾" gpsStatus={gps.status} step={stepIndex + 1} totalSteps={3} />

      {step === "local" && (
        <div className="flex flex-col gap-5 flex-1">
          <FieldSelect
            label="Talhão"
            options={(talhoes ?? []).map((t) => ({ id: t.id, label: t.nome, sublabel: t.area_ha ? `${t.area_ha} ha` : undefined }))}
            value={talhaoId}
            onChange={setTalhaoId}
            placeholder="Selecione o talhão"
          />
          <div className="flex gap-3 mt-auto">
            <button onClick={() => router.back()} className="flex-1 bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar</button>
            <button onClick={() => setStep("quantidade")} disabled={!talhaoId}
              className="flex-[2] bg-green-600 disabled:opacity-40 rounded-2xl py-4 font-semibold">Próximo →</button>
          </div>
        </div>
      )}

      {step === "quantidade" && (
        <div className="flex flex-col gap-5 flex-1">
          <div className="flex gap-2">
            {UNIDADES.map((u) => (
              <button key={u} type="button" onClick={() => setUnidade(u)}
                className={`flex-1 py-3 rounded-xl text-sm font-semibold transition-colors ${unidade === u ? "bg-green-600" : "bg-neutral-800"}`}>
                {u}
              </button>
            ))}
          </div>
          <NumPad value={quantidade} onChange={setQuantidade} suffix={unidade} label="Quantidade colhida" />

          {/* Umidade opcional */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-neutral-400">Umidade % (opcional)</label>
            <input
              type="number"
              inputMode="decimal"
              placeholder="ex: 14"
              value={umidade}
              onChange={(e) => setUmidade(e.target.value)}
              className="bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-base outline-none focus:border-green-500"
            />
          </div>

          <div className="flex gap-3 mt-auto">
            <button onClick={() => setStep("local")} className="flex-1 bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar</button>
            <button onClick={() => setStep("confirmar")} disabled={!quantidade || quantidade === "0"}
              className="flex-[2] bg-green-600 disabled:opacity-40 rounded-2xl py-4 font-semibold">Próximo →</button>
          </div>
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-col gap-5 flex-1">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          <div className="bg-neutral-800 rounded-2xl p-4 flex flex-col gap-2 text-sm">
            <SummaryRow label="Talhão" value={talhoes?.find((t) => t.id === talhaoId)?.nome ?? "—"} />
            <SummaryRow label="Quantidade" value={`${quantidade} ${unidade}`} />
            {umidade && <SummaryRow label="Umidade" value={`${umidade}%`} />}
          </div>

          <textarea
            placeholder="Observação (opcional)"
            value={obs}
            onChange={(e) => setObs(e.target.value)}
            rows={3}
            className="bg-neutral-800 border border-neutral-700 rounded-2xl px-4 py-3 text-sm resize-none outline-none focus:border-green-500 placeholder:text-neutral-600"
          />

          <CameraCapture fotos={cam.fotos} inputRef={cam.inputRef} canAddMore={cam.canAddMore} onOpen={cam.openCamera} onFileChange={cam.handleFileChange} onRemove={cam.removePhoto} />

          <button onClick={handleSalvar} disabled={saving}
            className="mt-auto bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded-2xl py-5 text-base font-bold transition-colors">
            {saving ? "Salvando..." : "✅ Salvar Colheita"}
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
        <h2 className="text-xl font-bold">Colheita Registrada!</h2>
        <p className="text-sm text-neutral-400 mt-1">Salvo localmente. Será sincronizado quando online.</p>
      </div>
      <div className="flex flex-col gap-3 w-full max-w-sm">
        <button onClick={onNew} className="bg-green-600 rounded-2xl py-4 font-semibold">Nova Colheita</button>
        <button onClick={onHome} className="bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar ao Início</button>
      </div>
    </div>
  );
}
