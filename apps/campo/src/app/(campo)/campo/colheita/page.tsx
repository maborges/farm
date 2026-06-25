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
import { Wheat, Check, CheckCircle2, ArrowRight } from "lucide-react";
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

  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
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
        icon={CheckCircle2}
        title="Colheita Registrada"
        description="Salvo localmente e pronto para sincronizar quando houver conexão."
        primaryLabel="Nova colheita"
        onPrimary={() => { setDone(false); setStep("local"); setTalhaoId(""); setQuantidade(""); }}
        onSecondary={() => router.replace("/home")}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader title="Colheita" icon={Wheat} gpsStatus={gps.status} step={stepIndex + 1} totalSteps={3} domain="AGRICULTURA" />

      {step === "local" && (
        <div className="flex flex-1 flex-col gap-4">
          <FieldSelect
            label="Talhão"
            options={(talhoes ?? []).map((t) => ({ id: t.id, label: t.nome, sublabel: t.area_ha ? `${t.area_ha} ha` : undefined }))}
            value={talhaoId}
            onChange={setTalhaoId}
            placeholder={fazendaId ? "Selecione o talhão" : "Selecione a unidade produtiva na barra superior"}
          />
          <CampoStepNav onBack={() => router.back()} onNext={() => setStep("quantidade")} nextLabel={<>Próximo <ArrowRight className="size-4 ml-1 inline" /></>} nextDisabled={!talhaoId} />
        </div>
      )}

      {step === "quantidade" && (
        <div className="flex flex-1 flex-col gap-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {UNIDADES.map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => setUnidade(u)}
                className={`flex-1 rounded-sm py-2.5 text-sm font-semibold transition-all active:scale-[0.98] ${
                  unidade === u
                    ? "border border-green-200 bg-green-50 text-green-800 ring-1 ring-green-200 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200 dark:ring-green-900/50"
                    : "border border-border bg-card text-muted-foreground hover:bg-muted"
                }`}
              >
                {u}
              </button>
            ))}
          </div>
          <NumPad value={quantidade} onChange={setQuantidade} suffix={unidade} label="Quantidade colhida" />

          {/* Umidade opcional */}
          <CampoSurface className="flex flex-col gap-2 p-3.5">
            <label className="text-sm font-semibold text-foreground">Umidade % (opcional)</label>
            <input
              type="number"
              inputMode="decimal"
              placeholder="ex: 14"
              value={umidade}
              onChange={(e) => setUmidade(e.target.value)}
              className="rounded-sm border border-border bg-card px-3.5 py-2.5 text-base outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
              enterKeyHint="done"
            />
          </CampoSurface>

          <CampoStepNav onBack={() => setStep("local")} onNext={() => setStep("confirmar")} nextLabel={<>Próximo <ArrowRight className="size-4 ml-1 inline" /></>} nextDisabled={!quantidade || quantidade === "0"} />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          <CampoSurface className="grid gap-2.5 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Talhão" value={talhoes?.find((t) => t.id === talhaoId)?.nome ?? "—"} />
            <SummaryRow label="Quantidade" value={`${quantidade} ${unidade}`} />
            {umidade && <SummaryRow label="Umidade" value={`${umidade}%`} />}
          </CampoSurface>

          <CampoSurface className="p-3.5">
            <textarea
              placeholder="Observação (opcional)"
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={3}
              className="min-h-[88px] w-full resize-none rounded-sm border border-border bg-card px-3.5 py-2.5 text-sm outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
            />
          </CampoSurface>

          <CameraCapture fotos={cam.fotos} inputRef={cam.inputRef} canAddMore={cam.canAddMore} onOpen={cam.openCamera} onFileChange={cam.handleFileChange} onRemove={cam.removePhoto} />

          <CampoButton onClick={handleSalvar} disabled={saving} className="mt-auto w-full" size="md" variant="primary">
            {saving ? "Salvando..." : <><Check className="size-4 shrink-0" /> Salvar Colheita</>}
          </CampoButton>
        </div>
      )}
    </CampoShell>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border py-1.5 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-semibold text-foreground">{value}</span>
    </div>
  );
}
