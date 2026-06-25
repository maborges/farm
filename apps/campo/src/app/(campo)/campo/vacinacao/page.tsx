"use client";

import { useEffect, useRef, useState } from "react";
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
  const vacinaNomeInputRef = useRef<HTMLInputElement | null>(null);

  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(() => db.lotes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);
  const vacinas = useLiveQuery(
    () => db.insumos.filter((i) => i.tipo === "VETERINARIO" || i.tipo === "VACINA" || i.nome.toLowerCase().includes("vacin")).toArray(),
    []
  );

  const stepIndex = ["lote", "vacina", "confirmar"].indexOf(step);
  const loteAtual = lotes?.find((l) => l.id === loteId);

  useEffect(() => {
    if (step !== "vacina" || (vacinas ?? []).length > 0) return;
    const frame = requestAnimationFrame(() => {
      vacinaNomeInputRef.current?.focus();
    });
    return () => cancelAnimationFrame(frame);
  }, [step, vacinas]);

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
      <CampoSuccessScreen
        icon="✅"
        title="Vacinação registrada"
        description="Salvo localmente e pronto para sincronizar quando houver conexão."
        primaryLabel="Nova vacinação"
        onPrimary={() => { setDone(false); setStep("lote"); setLoteId(""); setVacinaId(""); setQuantidade(""); }}
        onSecondary={() => router.replace("/home")}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader title="Vacinação" icon="💉" gpsStatus={gps.status} step={stepIndex + 1} totalSteps={3} domain="PECUARIA" />

      {step === "lote" && (
        <div className="flex flex-1 flex-col gap-4">
          <FieldSelect
            label="Lote de Animais"
            options={(lotes ?? []).map((l) => ({
              id: l.id,
              label: l.identificacao,
              sublabel: `${l.especie} · ${l.quantidade_cabecas} cabeças`,
            }))}
            value={loteId}
            onChange={setLoteId}
            placeholder={fazendaId ? "Selecione o lote" : "Selecione a unidade produtiva na barra superior"}
          />
          <CampoStepNav onBack={() => router.back()} onNext={() => setStep("vacina")} nextLabel="Próximo →" nextDisabled={!loteId} />
        </div>
      )}

      {step === "vacina" && (
        <div className="flex flex-1 flex-col gap-4">
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
            <CampoSurface className="flex flex-col gap-2 p-3.5">
              <label className="text-sm font-semibold text-foreground">Nome da Vacina</label>
              <input
                ref={vacinaNomeInputRef}
                placeholder="Ex: Febre Aftosa, Brucelose..."
                value={vacinaNome}
                onChange={(e) => setVacinaNome(e.target.value)}
                className="rounded-sm border border-border bg-card px-3.5 py-3 text-base outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
                enterKeyHint="done"
              />
            </CampoSurface>
          )}

          <NumPad value={quantidade} onChange={setQuantidade} suffix="mL/animal" label="Dose por animal (mL)" />

          <CampoStepNav onBack={() => setStep("lote")} onNext={() => setStep("confirmar")} nextLabel="Próximo →" nextDisabled={!vacinaNome && !vacinaId} />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          <CampoSurface className="grid gap-2.5 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Lote" value={loteAtual?.identificacao ?? "—"} />
            <SummaryRow label="Animais" value={String(loteAtual?.quantidade_cabecas ?? "—")} />
            <SummaryRow label="Vacina" value={vacinaNome || (vacinas?.find((v) => v.id === vacinaId)?.nome ?? "—")} />
            {quantidade && <SummaryRow label="Dose" value={`${quantidade} mL/animal`} />}
          </CampoSurface>

          <CampoSurface className="p-3.5">
            <textarea
              placeholder="Observação (ex: lote do pasto 3, vermifugação junto)"
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={3}
              className="min-h-[88px] w-full resize-none rounded-sm border border-border bg-card px-3.5 py-2.5 text-sm outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
            />
          </CampoSurface>

          <CameraCapture fotos={cam.fotos} inputRef={cam.inputRef} canAddMore={cam.canAddMore} onOpen={cam.openCamera} onFileChange={cam.handleFileChange} onRemove={cam.removePhoto} />

          <CampoButton onClick={handleSalvar} disabled={saving} className="mt-auto w-full" size="md" variant="primary">
            {saving ? "Salvando..." : "✅ Salvar Vacinação"}
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
