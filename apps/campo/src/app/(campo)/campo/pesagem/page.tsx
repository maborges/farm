"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { db, type CachedAnimal } from "@/lib/db";
import { useGps } from "@/hooks/useGps";
import { useCamera } from "@/hooks/useCamera";
import { createTask } from "@/lib/task-factory";
import { useSessionStore } from "@/lib/stores/session-store";
import { TaskHeader } from "@/components/campo/task-header";
import { FieldSelect } from "@/components/campo/field-select";
import { NumPad } from "@/components/campo/num-pad";
import { CameraCapture } from "@/components/campo/camera-capture";
import { GpsWarning } from "@/components/campo/gps-warning";
import { Scale, Check, CheckCircle2, ArrowRight } from "lucide-react";
import { CampoButton, CampoShell, CampoSurface } from "@/components/campo/ui";
import { CampoStepNav, CampoSuccessScreen } from "@/components/campo/flow";

type Step = "lote" | "peso" | "confirmar";

export default function PesagemPage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();

  const [step, setStep] = useState<Step>("lote");
  const [loteId, setLoteId] = useState("");
  const [pesoMedio, setPesoMedio] = useState("");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(() => db.lotes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);
  const animaisNoLote = useLiveQuery(
    async (): Promise<CachedAnimal[]> => (loteId ? db.animais.where("lote_id").equals(loteId).toArray() : []),
    [loteId]
  );

  const stepIndex = ["lote", "peso", "confirmar"].indexOf(step);
  const animaisAtivos = (animaisNoLote ?? []).filter((animal) => {
    const status = (animal.status ?? "ATIVO").toUpperCase();
    return status === "ATIVO" || status === "";
  });
  const quantidadeAnimais = animaisAtivos.length;

  const handleSalvar = async () => {
    setSaving(true);
    try {
      await createTask({
        type: "PESAGEM",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId || undefined,
        dados: {
          tipo_pesagem: "LOTE_BALANCA",
          peso_medio_kg: parseFloat(pesoMedio) || 0,
          quantidade_animais: quantidadeAnimais,
          peso_total_estimado: (parseFloat(pesoMedio) || 0) * quantidadeAnimais,
          observacoes: obs,
          animais: animaisAtivos.map((animal) => ({
            animal_id: animal.id,
            numero_brinco: animal.numero_brinco ?? "",
            peso_kg: parseFloat(pesoMedio) || 0,
            observacao: obs.trim() || null,
          })),
          animais_ids: animaisAtivos.map((animal) => animal.id),
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
        title="Pesagem registrada"
        description="Salvo localmente e pronto para sincronizar quando houver conexão."
        primaryLabel="Nova pesagem"
        onPrimary={() => { setDone(false); setStep("lote"); setLoteId(""); setPesoMedio(""); }}
        onSecondary={() => router.replace("/home")}
      />
    );
  }

  const loteAtual = lotes?.find((l) => l.id === loteId);

  return (
    <CampoShell className="gap-4">
      <TaskHeader title="Pesagem" icon={Scale} gpsStatus={gps.status} step={stepIndex + 1} totalSteps={3} domain="PECUARIA" />

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
          <CampoSurface className="flex flex-col gap-2 p-3.5 text-sm">
            <p className="font-semibold text-foreground">Modo suportado no registro manual</p>
            <p className="text-muted-foreground">
              Esta tela aplica a pesagem coletiva para todos os animais ativos do lote sincronizado.
            </p>
            <p className="text-muted-foreground">
              Animais disponíveis no cache: <span className="font-semibold text-foreground">{quantidadeAnimais}</span>
            </p>
          </CampoSurface>
          <CampoStepNav onBack={() => router.back()} onNext={() => setStep("peso")} nextLabel={<>Próximo <ArrowRight className="size-4 ml-1 inline" /></>} nextDisabled={!loteId || quantidadeAnimais === 0} />
        </div>
      )}

      {step === "peso" && (
        <div className="flex flex-1 flex-col gap-4">
          <NumPad value={pesoMedio} onChange={setPesoMedio} suffix="kg" label="Peso médio (kg/animal)" />
          <CampoSurface className="flex flex-col gap-2 p-3.5">
            <label className="text-sm font-semibold text-foreground">Animais ativos que receberão a pesagem</label>
            <p className="text-2xl font-semibold text-foreground">{quantidadeAnimais}</p>
            <p className="text-xs text-muted-foreground">
              O mesmo peso será aplicado a todos os animais ativos deste lote.
            </p>
          </CampoSurface>
          <CampoStepNav onBack={() => setStep("lote")} onNext={() => setStep("confirmar")} nextLabel={<>Próximo <ArrowRight className="size-4 ml-1 inline" /></>} nextDisabled={!pesoMedio || pesoMedio === "0"} />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          <CampoSurface className="grid gap-2.5 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Lote" value={loteAtual?.identificacao ?? "—"} />
            <SummaryRow label="Tipo" value="LOTE_BALANCA" />
            <SummaryRow label="Peso médio" value={`${pesoMedio} kg`} />
            <SummaryRow label="Animais" value={String(quantidadeAnimais)} />
            <SummaryRow label="Peso total est." value={`${((parseFloat(pesoMedio) || 0) * quantidadeAnimais).toFixed(0)} kg`} />
          </CampoSurface>

          <CampoSurface className="p-3.5">
            <textarea
              placeholder="Observação (opcional)"
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={2}
              className="min-h-[84px] w-full resize-none rounded-sm border border-border bg-card px-3.5 py-2.5 text-sm outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
            />
          </CampoSurface>

          <CameraCapture fotos={cam.fotos} inputRef={cam.inputRef} canAddMore={cam.canAddMore} onOpen={cam.openCamera} onFileChange={cam.handleFileChange} onRemove={cam.removePhoto} />

          <CampoButton onClick={handleSalvar} disabled={saving} className="mt-auto w-full" size="md" variant="primary">
            {saving ? "Salvando..." : <><Check className="size-4 shrink-0" /> Salvar Pesagem</>}
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
