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
      <CampoSuccessScreen
        icon="✅"
        title="Pesagem registrada"
        description="Salvo localmente e pronto para sincronizar quando houver conexão."
        primaryLabel="Nova pesagem"
        onPrimary={() => { setDone(false); setStep("lote"); setLoteId(""); setPesoMedio(""); setQtdAnimais(""); }}
        onSecondary={() => router.replace("/home")}
      />
    );
  }

  const loteAtual = lotes?.find((l) => l.id === loteId);

  return (
    <CampoShell className="gap-5">
      <TaskHeader title="Pesagem" icon="⚖️" gpsStatus={gps.status} step={stepIndex + 1} totalSteps={3} />

      {step === "lote" && (
        <div className="flex flex-1 flex-col gap-5">
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
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {(["AMOSTRA", "LOTE_BALANCA", "INDIVIDUAL"] as TipoPesagem[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTipo(t)}
                  className={`rounded-2xl py-4 text-xs font-semibold transition-all active:scale-[0.98] ${
                    tipo === t
                      ? "bg-emerald-400/18 text-emerald-100 ring-1 ring-emerald-300/25"
                      : "border border-white/10 bg-white/[0.04] text-white/70 hover:bg-white/[0.07]"
                  }`}
                >
                  {t === "AMOSTRA" ? "Amostra" : t === "LOTE_BALANCA" ? "Balança" : "Individual"}
                </button>
              ))}
            </div>
          </div>
          <CampoStepNav onBack={() => router.back()} onNext={() => setStep("peso")} nextLabel="Próximo →" nextDisabled={!loteId} />
        </div>
      )}

      {step === "peso" && (
        <div className="flex flex-1 flex-col gap-5">
          <NumPad value={pesoMedio} onChange={setPesoMedio} suffix="kg" label="Peso médio (kg/animal)" />
          <CampoSurface className="flex flex-col gap-2 p-4">
            <label className="text-sm font-semibold text-white/85">
              Nº de animais pesados (padrão: {loteAtual?.quantidade_cabecas ?? "—"})
            </label>
            <input
              type="number"
              inputMode="numeric"
              placeholder={String(loteAtual?.quantidade_cabecas ?? "")}
              value={qtdAnimais}
              onChange={(e) => setQtdAnimais(e.target.value)}
              className="rounded-[22px] border border-white/10 bg-white/[0.04] px-4 py-3 text-base outline-none transition-colors focus:border-emerald-400/50 focus:bg-white/[0.06] placeholder:text-white/30"
            />
          </CampoSurface>
          <CampoStepNav onBack={() => setStep("lote")} onNext={() => setStep("confirmar")} nextLabel="Próximo →" nextDisabled={!pesoMedio || pesoMedio === "0"} />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-5">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          <CampoSurface className="grid gap-3 p-4 text-sm md:grid-cols-2">
            <SummaryRow label="Lote" value={loteAtual?.identificacao ?? "—"} />
            <SummaryRow label="Tipo" value={tipo} />
            <SummaryRow label="Peso médio" value={`${pesoMedio} kg`} />
            <SummaryRow label="Animais" value={qtdAnimais || String(loteAtual?.quantidade_cabecas ?? "—")} />
            <SummaryRow label="Peso total est." value={`${((parseFloat(pesoMedio) || 0) * (parseInt(qtdAnimais) || loteAtual?.quantidade_cabecas || 1)).toFixed(0)} kg`} />
          </CampoSurface>

          <CampoSurface className="p-4">
            <textarea
              placeholder="Observação (opcional)"
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={2}
              className="min-h-[96px] w-full resize-none rounded-[22px] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm outline-none transition-colors focus:border-emerald-400/50 focus:bg-white/[0.06] placeholder:text-white/30"
            />
          </CampoSurface>

          <CameraCapture fotos={cam.fotos} inputRef={cam.inputRef} canAddMore={cam.canAddMore} onOpen={cam.openCamera} onFileChange={cam.handleFileChange} onRemove={cam.removePhoto} />

          <CampoButton onClick={handleSalvar} disabled={saving} className="mt-auto w-full" size="lg" variant="primary">
            {saving ? "Salvando..." : "✅ Salvar Pesagem"}
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
