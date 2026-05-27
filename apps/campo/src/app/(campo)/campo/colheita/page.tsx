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
import { CampoButton, CampoShell, CampoSurface } from "@/components/campo/ui";
import { CampoStepNav, CampoSuccessScreen } from "@/components/campo/flow";

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
      <CampoSuccessScreen
        icon="✅"
        title="Colheita registrada"
        description="Salvo localmente e pronto para sincronizar quando houver conexão."
        primaryLabel="Nova colheita"
        onPrimary={() => { setDone(false); setStep("local"); setTalhaoId(""); setQuantidade(""); }}
        onSecondary={() => router.replace("/home")}
      />
    );
  }

  return (
    <CampoShell className="gap-5">
      <TaskHeader title="Colheita" icon="🌾" gpsStatus={gps.status} step={stepIndex + 1} totalSteps={3} />

      {step === "local" && (
        <div className="flex flex-1 flex-col gap-5">
          <FieldSelect
            label="Talhão"
            options={(talhoes ?? []).map((t) => ({ id: t.id, label: t.nome, sublabel: t.area_ha ? `${t.area_ha} ha` : undefined }))}
            value={talhaoId}
            onChange={setTalhaoId}
            placeholder="Selecione o talhão"
          />
          <CampoStepNav onBack={() => router.back()} onNext={() => setStep("quantidade")} nextLabel="Próximo →" nextDisabled={!talhaoId} />
        </div>
      )}

      {step === "quantidade" && (
        <div className="flex flex-1 flex-col gap-5">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {UNIDADES.map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => setUnidade(u)}
                className={`flex-1 rounded-2xl py-3 text-sm font-semibold transition-all active:scale-[0.98] ${
                  unidade === u
                    ? "bg-emerald-400/18 text-emerald-100 ring-1 ring-emerald-300/25"
                    : "border border-white/10 bg-white/[0.04] text-white/70 hover:bg-white/[0.07]"
                }`}
              >
                {u}
              </button>
            ))}
          </div>
          <NumPad value={quantidade} onChange={setQuantidade} suffix={unidade} label="Quantidade colhida" />

          {/* Umidade opcional */}
          <CampoSurface className="flex flex-col gap-2 p-4">
            <label className="text-sm font-semibold text-white/85">Umidade % (opcional)</label>
            <input
              type="number"
              inputMode="decimal"
              placeholder="ex: 14"
              value={umidade}
              onChange={(e) => setUmidade(e.target.value)}
              className="rounded-[22px] border border-white/10 bg-white/[0.04] px-4 py-3 text-base outline-none transition-colors focus:border-emerald-400/50 focus:bg-white/[0.06] placeholder:text-white/30"
            />
          </CampoSurface>

          <CampoStepNav onBack={() => setStep("local")} onNext={() => setStep("confirmar")} nextLabel="Próximo →" nextDisabled={!quantidade || quantidade === "0"} />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-5">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          <CampoSurface className="grid gap-3 p-4 text-sm md:grid-cols-2">
            <SummaryRow label="Talhão" value={talhoes?.find((t) => t.id === talhaoId)?.nome ?? "—"} />
            <SummaryRow label="Quantidade" value={`${quantidade} ${unidade}`} />
            {umidade && <SummaryRow label="Umidade" value={`${umidade}%`} />}
          </CampoSurface>

          <CampoSurface className="p-4">
            <textarea
              placeholder="Observação (opcional)"
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={3}
              className="min-h-[104px] w-full resize-none rounded-[22px] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm outline-none transition-colors focus:border-emerald-400/50 focus:bg-white/[0.06] placeholder:text-white/30"
            />
          </CampoSurface>

          <CameraCapture fotos={cam.fotos} inputRef={cam.inputRef} canAddMore={cam.canAddMore} onOpen={cam.openCamera} onFileChange={cam.handleFileChange} onRemove={cam.removePhoto} />

          <CampoButton onClick={handleSalvar} disabled={saving} className="mt-auto w-full" size="lg" variant="primary">
            {saving ? "Salvando..." : "✅ Salvar Colheita"}
          </CampoButton>
        </div>
      )}
    </CampoShell>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-white/8 py-2 last:border-0">
      <span className="text-white/45">{label}</span>
      <span className="text-right font-semibold text-white/85">{value}</span>
    </div>
  );
}
