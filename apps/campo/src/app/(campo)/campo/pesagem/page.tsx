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
  const loteAtual = lotes?.find((l) => l.id === loteId);
  const animaisAtivos = (animaisNoLote ?? []).filter((animal) => {
    const status = (animal.status ?? "ATIVO").toUpperCase();
    return status === "ATIVO" || status === "";
  });
  const isPorLote =
    Boolean(loteAtual) && loteAtual?.modo_gestao !== "INDIVIDUAL" && animaisAtivos.length === 0;
  const quantidadeAnimais = isPorLote
    ? (loteAtual?.quantidade_cabecas ?? 0)
    : animaisAtivos.length;

  const handleSalvar = async () => {
    setSaving(true);
    const pesoMedioValor = parseFloat(pesoMedio) || 0;
    try {
      await createTask({
        type: "PESAGEM",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId || undefined,
        dados: {
          lote_id: loteId || undefined,
          modo_gestao: isPorLote ? "POR_LOTE" : "INDIVIDUAL",
          tipo_pesagem: "LOTE_BALANCA",
          peso_medio_kg: pesoMedioValor,
          quantidade_animais: quantidadeAnimais,
          peso_total_kg: Number((pesoMedioValor * quantidadeAnimais).toFixed(2)),
          peso_total_estimado: pesoMedioValor * quantidadeAnimais,
          observacoes: obs,
          animais: isPorLote
            ? []
            : animaisAtivos.map((animal) => ({
                animal_id: animal.id,
                numero_brinco: animal.numero_brinco ?? "",
                peso_kg: pesoMedioValor,
                observacao: obs.trim() || null,
              })),
          animais_ids: isPorLote ? [] : animaisAtivos.map((animal) => animal.id),
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
              sublabel: `${l.especie} · ${l.quantidade_cabecas} cabeças · ${l.modo_gestao === "INDIVIDUAL" ? "Individual" : "Por Lote"}`,
            }))}
            value={loteId}
            onChange={setLoteId}
            placeholder={fazendaId ? "Selecione o lote" : "Selecione a unidade produtiva na barra superior"}
          />
          <CampoSurface className="flex flex-col gap-2 p-3.5 text-sm">
            <div className="flex items-center justify-between gap-2">
              <p className="font-semibold text-foreground">
                {isPorLote ? "Pesagem Coletiva (Por Lote)" : "Pesagem Individual em Lote"}
              </p>
              {loteAtual && (
                <span className="rounded-sm border border-border bg-muted px-2 py-0.5 text-[11px] font-semibold">
                  {isPorLote ? "POR LOTE" : "INDIVIDUAL"}
                </span>
              )}
            </div>
            <p className="text-muted-foreground">
              {isPorLote
                ? "Atualiza o peso médio e registra a pesagem coletiva sem exigir brincos."
                : "Aplica o peso médio para todos os animais individuais ativos do lote."}
            </p>
            <p className="text-muted-foreground">
              Cabeças consideradas no lote:{" "}
              <span className="font-semibold text-foreground">{quantidadeAnimais}</span>
            </p>
          </CampoSurface>
          <CampoStepNav onBack={() => router.back()} onNext={() => setStep("peso")} nextLabel={<>Próximo <ArrowRight className="size-4 ml-1 inline" /></>} nextDisabled={!loteId || quantidadeAnimais === 0} />
        </div>
      )}

      {step === "peso" && (
        <div className="flex flex-1 flex-col gap-4">
          <NumPad value={pesoMedio} onChange={setPesoMedio} suffix="kg" label="Peso médio (kg/animal)" />
          <CampoSurface className="flex flex-col gap-2 p-3.5">
            <label className="text-sm font-semibold text-foreground">Cabeças consideradas na pesagem</label>
            <p className="text-2xl font-semibold text-foreground">{quantidadeAnimais}</p>
            <p className="text-xs text-muted-foreground">
              Peso total estimado:{" "}
              <span className="font-semibold text-foreground">
                {((parseFloat(pesoMedio) || 0) * quantidadeAnimais).toFixed(1)} kg
              </span>
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
            <SummaryRow label="Modo" value={isPorLote ? "Por Lote (Coletivo)" : "Individual"} />
            <SummaryRow label="Peso médio" value={`${pesoMedio} kg`} />
            <SummaryRow label="Cabeças" value={String(quantidadeAnimais)} />
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
