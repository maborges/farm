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

type Step = "local" | "produto" | "quantidade" | "confirmar";

export default function AplicacaoPage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();

  const [step, setStep] = useState<Step>("local");
  const [talhaoId, setTalhaoId] = useState("");
  const [insumoId, setInsumoId] = useState("");
  const [quantidade, setQuantidade] = useState("");
  const [unidade, setUnidade] = useState("L/ha");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.fazenda_ids?.[0] ?? "";

  const talhoes = useLiveQuery(() => db.talhoes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);
  const insumos = useLiveQuery(() => db.insumos.toArray(), []);

  const stepIndex = ["local", "produto", "quantidade", "confirmar"].indexOf(step);

  const handleSalvar = async () => {
    setSaving(true);
    try {
      await createTask({
        type: "APLICACAO_DEFENSIVO",
        module: "agricola",
        fazenda_id: fazendaId,
        talhao_id: talhaoId || undefined,
        dados: {
          insumo_id: insumoId,
          quantidade: parseFloat(quantidade) || 0,
          unidade,
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
    return <SuccessScreen onNew={() => { setDone(false); setStep("local"); setTalhaoId(""); setInsumoId(""); setQuantidade(""); }} onHome={() => router.replace("/home")} />;
  }

  return (
    <div className="flex flex-col gap-5 p-4 pb-10 min-h-dvh">
      <TaskHeader title="Aplicação" icon="🌿" gpsStatus={gps.status} step={stepIndex + 1} totalSteps={4} />

      {step === "local" && (
        <div className="flex flex-col gap-5 flex-1">
          <FieldSelect
            label="Talhão"
            options={(talhoes ?? []).map((t) => ({ id: t.id, label: t.nome, sublabel: t.area_ha ? `${t.area_ha} ha` : undefined }))}
            value={talhaoId}
            onChange={setTalhaoId}
            placeholder="Selecione o talhão"
          />
          <NavButtons onBack={() => router.back()} onNext={() => setStep("produto")} nextLabel="Próximo →" nextDisabled={!talhaoId} />
        </div>
      )}

      {step === "produto" && (
        <div className="flex flex-col gap-5 flex-1">
          <FieldSelect
            label="Produto / Insumo"
            options={(insumos ?? []).map((i) => ({ id: i.id, label: i.nome, sublabel: i.tipo }))}
            value={insumoId}
            onChange={setInsumoId}
            placeholder="Selecione o produto"
          />
          <NavButtons onBack={() => setStep("local")} onNext={() => setStep("quantidade")} nextLabel="Próximo →" nextDisabled={!insumoId} />
        </div>
      )}

      {step === "quantidade" && (
        <div className="flex flex-col gap-5 flex-1">
          {/* Unidade rápida */}
          <div className="flex gap-2">
            {["L/ha", "kg/ha", "mL/ha", "g/ha"].map((u) => (
              <button key={u} type="button" onClick={() => setUnidade(u)}
                className={`flex-1 py-3 rounded-xl text-sm font-semibold transition-colors ${unidade === u ? "bg-green-600" : "bg-neutral-800"}`}>
                {u}
              </button>
            ))}
          </div>
          <NumPad value={quantidade} onChange={setQuantidade} suffix={unidade} label="Quantidade" />
          <NavButtons onBack={() => setStep("produto")} onNext={() => setStep("confirmar")} nextLabel="Próximo →" nextDisabled={!quantidade || quantidade === "0"} />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-col gap-5 flex-1">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          {/* Resumo */}
          <div className="bg-neutral-800 rounded-2xl p-4 flex flex-col gap-2 text-sm">
            <SummaryRow label="Talhão" value={talhoes?.find((t) => t.id === talhaoId)?.nome ?? "—"} />
            <SummaryRow label="Produto" value={insumos?.find((i) => i.id === insumoId)?.nome ?? "—"} />
            <SummaryRow label="Quantidade" value={`${quantidade} ${unidade}`} />
          </div>

          {/* Observação opcional */}
          <textarea
            placeholder="Observação (opcional)"
            value={obs}
            onChange={(e) => setObs(e.target.value)}
            rows={3}
            className="bg-neutral-800 border border-neutral-700 rounded-2xl px-4 py-3 text-sm resize-none outline-none focus:border-green-500 placeholder:text-neutral-600"
          />

          <CameraCapture fotos={cam.fotos} inputRef={cam.inputRef} canAddMore={cam.canAddMore} onOpen={cam.openCamera} onFileChange={cam.handleFileChange} onRemove={cam.removePhoto} />

          <button
            onClick={handleSalvar}
            disabled={saving}
            className="mt-auto bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded-2xl py-5 text-base font-bold transition-colors"
          >
            {saving ? "Salvando..." : "✅ Salvar Aplicação"}
          </button>
        </div>
      )}
    </div>
  );
}

function NavButtons({ onBack, onNext, nextLabel, nextDisabled }: { onBack: () => void; onNext: () => void; nextLabel: string; nextDisabled?: boolean }) {
  return (
    <div className="flex gap-3 mt-auto">
      <button type="button" onClick={onBack} className="flex-1 bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar</button>
      <button type="button" onClick={onNext} disabled={nextDisabled}
        className="flex-[2] bg-green-600 hover:bg-green-500 disabled:opacity-40 rounded-2xl py-4 font-semibold transition-colors">
        {nextLabel}
      </button>
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
        <h2 className="text-xl font-bold">Aplicação Registrada!</h2>
        <p className="text-sm text-neutral-400 mt-1">Salvo localmente. Será sincronizado quando online.</p>
      </div>
      <div className="flex flex-col gap-3 w-full max-w-sm">
        <button onClick={onNew} className="bg-green-600 rounded-2xl py-4 font-semibold">Nova Aplicação</button>
        <button onClick={onHome} className="bg-neutral-800 rounded-2xl py-4 font-semibold">← Voltar ao Início</button>
      </div>
    </div>
  );
}
