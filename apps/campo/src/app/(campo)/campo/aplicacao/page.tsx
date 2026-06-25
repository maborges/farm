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

  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";

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
    return (
      <CampoSuccessScreen
        icon="✅"
        title="Aplicação registrada"
        description="Salvo localmente e pronto para sincronizar quando houver conexão."
        primaryLabel="Nova aplicação"
        onPrimary={() => { setDone(false); setStep("local"); setTalhaoId(""); setInsumoId(""); setQuantidade(""); }}
        onSecondary={() => router.replace("/home")}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader title="Aplicação" icon="🌿" gpsStatus={gps.status} step={stepIndex + 1} totalSteps={4} domain="AGRICULTURA" />

      {step === "local" && (
        <div className="flex flex-1 flex-col gap-4">
          <FieldSelect
            label="Talhão"
            options={(talhoes ?? []).map((t) => ({ id: t.id, label: t.nome, sublabel: t.area_ha ? `${t.area_ha} ha` : undefined }))}
            value={talhaoId}
            onChange={setTalhaoId}
            placeholder={fazendaId ? "Selecione o talhão" : "Selecione a unidade produtiva na barra superior"}
          />
          <CampoStepNav onBack={() => router.back()} onNext={() => setStep("produto")} nextLabel="Próximo →" nextDisabled={!talhaoId} />
        </div>
      )}

      {step === "produto" && (
        <div className="flex flex-1 flex-col gap-4">
          <FieldSelect
            label="Produto / Insumo"
            options={(insumos ?? []).map((i) => ({ id: i.id, label: i.nome, sublabel: i.tipo }))}
            value={insumoId}
            onChange={setInsumoId}
            placeholder="Selecione o produto"
          />
          <CampoStepNav onBack={() => setStep("local")} onNext={() => setStep("quantidade")} nextLabel="Próximo →" nextDisabled={!insumoId} />
        </div>
      )}

      {step === "quantidade" && (
        <div className="flex flex-1 flex-col gap-4">
          {/* Unidade rápida */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {["L/ha", "kg/ha", "mL/ha", "g/ha"].map((u) => (
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
          <NumPad value={quantidade} onChange={setQuantidade} suffix={unidade} label="Quantidade" />
          <CampoStepNav onBack={() => setStep("produto")} onNext={() => setStep("confirmar")} nextLabel="Próximo →" nextDisabled={!quantidade || quantidade === "0"} />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          {/* Resumo */}
          <CampoSurface className="grid gap-2.5 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Talhão" value={talhoes?.find((t) => t.id === talhaoId)?.nome ?? "—"} />
            <SummaryRow label="Produto" value={insumos?.find((i) => i.id === insumoId)?.nome ?? "—"} />
            <SummaryRow label="Quantidade" value={`${quantidade} ${unidade}`} />
          </CampoSurface>

          {/* Observação opcional */}
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

          <CampoButton
            onClick={handleSalvar}
            disabled={saving}
            className="mt-auto w-full"
            size="md"
            variant="primary"
          >
            {saving ? "Salvando..." : "✅ Salvar Aplicação"}
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
