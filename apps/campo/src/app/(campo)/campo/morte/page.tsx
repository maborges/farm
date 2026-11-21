"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { ArrowRight, Check, CheckCircle2, Skull } from "lucide-react";

import { AnimalPicker } from "@/components/campo/animal-picker";
import { CameraCapture } from "@/components/campo/camera-capture";
import { FieldSelect } from "@/components/campo/field-select";
import { CampoStepNav, CampoSuccessScreen } from "@/components/campo/flow";
import { GpsWarning } from "@/components/campo/gps-warning";
import { NumPad } from "@/components/campo/num-pad";
import { TaskHeader } from "@/components/campo/task-header";
import { CampoShell, CampoSurface } from "@/components/campo/ui";
import { useCamera } from "@/hooks/useCamera";
import { useGps } from "@/hooks/useGps";
import { db, type CachedAnimal } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { createTask } from "@/lib/task-factory";

type Step = "lote" | "detalhes" | "confirmar";

const CAUSAS_MORTE = [
  "Doença",
  "Acidente",
  "Raio / Clima",
  "Parto",
  "Predador",
  "Desconhecida",
] as const;

export default function MorteRegistroPage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();

  const [step, setStep] = useState<Step>("lote");
  const [loteId, setLoteId] = useState("");
  const [animalId, setAnimalId] = useState("");
  const [causa, setCausa] = useState<string>("Doença");
  const [qtdCabecas, setQtdCabecas] = useState("1");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(
    () => db.lotes.where("fazenda_id").equals(fazendaId).toArray(),
    [fazendaId]
  );
  const animaisNoLote = useLiveQuery(
    async (): Promise<CachedAnimal[]> =>
      loteId ? db.animais.where("lote_id").equals(loteId).toArray() : [],
    [loteId]
  );

  const loteAtual = lotes?.find((l) => l.id === loteId);
  const animaisAtivos = (animaisNoLote ?? []).filter((animal) => {
    const status = (animal.status ?? "ATIVO").toUpperCase();
    return status === "ATIVO" || status === "";
  });
  const modoIndividual =
    Boolean(loteAtual) &&
    (loteAtual?.modo_gestao === "INDIVIDUAL" || animaisAtivos.length > 0);
  const animalSelecionado = animaisAtivos.find((a) => a.id === animalId);

  const qtdInt = Math.floor(Number(qtdCabecas) || 0);
  const saldoDisponivel = loteAtual?.quantidade_cabecas ?? 0;
  const qtdValida = modoIndividual
    ? Boolean(animalSelecionado)
    : Number.isFinite(Number(qtdCabecas)) &&
      Number.isInteger(Number(qtdCabecas)) &&
      qtdInt >= 1 &&
      qtdInt <= saldoDisponivel;

  const stepIndex = ["lote", "detalhes", "confirmar"].indexOf(step);

  const handleSalvar = async () => {
    setSaving(true);
    try {
      await createTask({
        type: "MORTE_REGISTRO",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId || undefined,
        dados: {
          lote_id: loteId || undefined,
          animal_id: modoIndividual ? animalId : undefined,
          quantidade_cabecas: modoIndividual ? 1 : qtdInt,
          causa_morte: causa,
          observacoes: obs.trim() || undefined,
          data_evento: new Date().toISOString().slice(0, 10),
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
        title="Ocorrência de morte salva"
        description="Salvo localmente com evidência e pronto para sincronizar."
        primaryLabel="Registrar outra ocorrência"
        onPrimary={() => {
          setDone(false);
          setStep("lote");
          setLoteId("");
          setAnimalId("");
          setQtdCabecas("1");
          setObs("");
        }}
        onSecondary={() => router.replace("/pecuaria")}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader
        title="Registro de Morte"
        icon={Skull}
        gpsStatus={gps.status}
        step={stepIndex + 1}
        totalSteps={3}
        domain="PECUARIA"
      />

      {step === "lote" && (
        <div className="flex flex-1 flex-col gap-4">
          <FieldSelect
            label="Lote"
            options={(lotes ?? []).map((l) => ({
              id: l.id,
              label: l.identificacao,
              sublabel: `${l.especie} · ${l.quantidade_cabecas} cab. · ${
                l.modo_gestao === "INDIVIDUAL" ? "Individual" : "Por Lote"
              }`,
            }))}
            value={loteId}
            onChange={(val) => {
              setLoteId(val);
              setAnimalId("");
              setQtdCabecas("1");
            }}
            placeholder={fazendaId ? "Selecione o lote" : "Selecione a fazenda no topo"}
          />

          {loteAtual && modoIndividual && (
            <AnimalPicker
              label="Selecione o animal (Brinco)"
              animals={animaisAtivos}
              lotes={lotes ?? []}
              value={animalId}
              onChange={setAnimalId}
              mode="GERAL"
              loteId={loteId}
            />
          )}

          {loteAtual && !modoIndividual && (
            <CampoSurface className="p-3.5 text-sm">
              <p className="font-semibold text-foreground">Lote Coletivo (POR LOTE)</p>
              <p className="mt-1 text-muted-foreground">
                Saldo disponível para baixa:{" "}
                <span className="font-semibold text-foreground">{saldoDisponivel} cabeças</span>
              </p>
            </CampoSurface>
          )}

          <CampoStepNav
            onBack={() => router.back()}
            onNext={() => setStep("detalhes")}
            nextLabel={
              <>
                Próximo <ArrowRight className="ml-1 inline size-4" />
              </>
            }
            nextDisabled={
              !loteAtual ||
              (modoIndividual ? !animalSelecionado : saldoDisponivel <= 0)
            }
          />
        </div>
      )}

      {step === "detalhes" && (
        <div className="flex flex-1 flex-col gap-4">
          <CampoSurface className="space-y-2.5 p-3.5">
            <p className="text-sm font-semibold text-foreground">Causa provável</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {CAUSAS_MORTE.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setCausa(item)}
                  className={`rounded-sm border px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                    causa === item
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-card text-foreground hover:bg-muted"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
          </CampoSurface>

          {!modoIndividual && (
            <NumPad
              value={qtdCabecas}
              onChange={setQtdCabecas}
              suffix="cabeças"
              label={`Quantidade de óbitos (máx. ${saldoDisponivel})`}
            />
          )}

          <CampoStepNav
            onBack={() => setStep("lote")}
            onNext={() => setStep("confirmar")}
            nextLabel={
              <>
                Próximo <ArrowRight className="ml-1 inline size-4" />
              </>
            }
            nextDisabled={!causa || !qtdValida}
          />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />

          <CampoSurface className="grid gap-2 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Lote" value={loteAtual?.identificacao ?? "—"} />
            <SummaryRow
              label={modoIndividual ? "Animal" : "Quantidade"}
              value={
                modoIndividual
                  ? animalSelecionado?.numero_brinco ?? animalSelecionado?.nome ?? "—"
                  : `${qtdInt} cabeças`
              }
            />
            <SummaryRow label="Causa" value={causa} />
          </CampoSurface>

          <CampoSurface className="p-3.5">
            <textarea
              placeholder="Detalhes da ocorrência, laudo de campo ou pasto..."
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={3}
              className="min-h-[84px] w-full resize-none rounded-sm border border-border bg-card px-3.5 py-2.5 text-sm outline-none focus:border-ring placeholder:text-muted-foreground/50"
            />
          </CampoSurface>

          <CameraCapture
            fotos={cam.fotos}
            inputRef={cam.inputRef}
            canAddMore={cam.canAddMore}
            onOpen={cam.openCamera}
            onFileChange={cam.handleFileChange}
            onRemove={cam.removePhoto}
          />

          <CampoStepNav
            onBack={() => setStep("detalhes")}
            onNext={() => void handleSalvar()}
            nextLabel={
              saving ? (
                "Salvando..."
              ) : (
                <>
                  <Check className="mr-1 inline size-4" /> Salvar Morte
                </>
              )
            }
            nextDisabled={saving}
          />
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
