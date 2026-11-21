"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { ArrowRight, Check, CheckCircle2, Pill } from "lucide-react";

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

type Step = "lote" | "produto" | "confirmar";

export default function MedicacaoPage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();

  const [step, setStep] = useState<Step>("lote");
  const [loteId, setLoteId] = useState("");
  const [aplicarIndividual, setAplicarIndividual] = useState(false);
  const [animalId, setAnimalId] = useState("");
  const [produtoId, setProdutoId] = useState("");
  const [dose, setDose] = useState("5");
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
  const todosInsumos = useLiveQuery(() => db.insumos.toArray(), []);

  const medicamentosFiltrados = (todosInsumos ?? []).filter((item) => {
    const tipo = (item.tipo ?? "").toUpperCase();
    const nome = item.nome.toLowerCase();
    return (
      tipo === "MEDICAMENTO" ||
      tipo === "VETERINARIO" ||
      tipo === "VACINA" ||
      nome.includes("verm") ||
      nome.includes("antib") ||
      nome.includes("ivermec")
    );
  });
  const opcoesProdutos =
    medicamentosFiltrados.length > 0 ? medicamentosFiltrados : todosInsumos ?? [];

  const loteAtual = lotes?.find((l) => l.id === loteId);
  const animaisAtivos = (animaisNoLote ?? []).filter((a) => {
    const status = (a.status ?? "ATIVO").toUpperCase();
    return status === "ATIVO" || status === "";
  });
  const modoIndividual = aplicarIndividual && animaisAtivos.length > 0;
  const animalSelecionado = animaisAtivos.find((a) => a.id === animalId);
  const produtoSelecionado = opcoesProdutos.find((p) => p.id === produtoId);
  const qtdCabecas = modoIndividual
    ? 1
    : animaisAtivos.length > 0
      ? animaisAtivos.length
      : loteAtual?.quantidade_cabecas ?? 0;

  const stepIndex = ["lote", "produto", "confirmar"].indexOf(step);

  const handleSalvar = async () => {
    setSaving(true);
    try {
      await createTask({
        type: "MEDICACAO_ANIMAL",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId || undefined,
        dados: {
          lote_id: loteId || undefined,
          animal_id: modoIndividual ? animalId : undefined,
          produto_id: produtoSelecionado?.id ?? null,
          produto_nome: produtoSelecionado?.nome ?? null,
          dose: parseFloat(dose) || 0,
          unidade_medida: produtoSelecionado?.unidade_medida ?? "ML",
          quantidade_animais: qtdCabecas,
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
        title="Medicação registrada"
        description="Salvo localmente e pronto para sincronizar quando houver conexão."
        primaryLabel="Nova medicação"
        onPrimary={() => {
          setDone(false);
          setStep("lote");
          setLoteId("");
          setAnimalId("");
          setProdutoId("");
          setDose("5");
          setObs("");
        }}
        onSecondary={() => router.replace("/pecuaria")}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader
        title="Medicação / Tratamento"
        icon={Pill}
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
              sublabel: `${l.especie} · ${l.quantidade_cabecas} cab.`,
            }))}
            value={loteId}
            onChange={(val) => {
              setLoteId(val);
              setAnimalId("");
              setAplicarIndividual(false);
            }}
            placeholder={fazendaId ? "Selecione o lote" : "Selecione a fazenda no topo"}
          />

          {loteAtual && animaisAtivos.length > 0 && (
            <CampoSurface className="space-y-2 p-3.5 text-sm">
              <p className="font-semibold text-foreground">Abrangência da aplicação</p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setAplicarIndividual(false)}
                  className={`rounded-sm border px-3 py-2 text-xs font-semibold ${
                    !aplicarIndividual
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-card text-muted-foreground"
                  }`}
                >
                  Lote inteiro ({animaisAtivos.length} cab.)
                </button>
                <button
                  type="button"
                  onClick={() => setAplicarIndividual(true)}
                  className={`rounded-sm border px-3 py-2 text-xs font-semibold ${
                    aplicarIndividual
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-card text-muted-foreground"
                  }`}
                >
                  Animal específico
                </button>
              </div>
            </CampoSurface>
          )}

          {loteAtual && modoIndividual && (
            <AnimalPicker
              label="Animal medicado"
              animals={animaisAtivos}
              lotes={lotes ?? []}
              value={animalId}
              onChange={setAnimalId}
              mode="GERAL"
              loteId={loteId}
            />
          )}

          <CampoStepNav
            onBack={() => router.back()}
            onNext={() => setStep("produto")}
            nextLabel={
              <>
                Próximo <ArrowRight className="ml-1 inline size-4" />
              </>
            }
            nextDisabled={!loteAtual || (modoIndividual && !animalSelecionado)}
          />
        </div>
      )}

      {step === "produto" && (
        <div className="flex flex-1 flex-col gap-4">
          {opcoesProdutos.length > 0 ? (
            <FieldSelect
              label="Medicamento / Vermífugo"
              options={opcoesProdutos.map((p) => ({
                id: p.id,
                label: p.nome,
                sublabel: p.unidade_medida ?? undefined,
              }))}
              value={produtoId}
              onChange={setProdutoId}
              placeholder="Selecione o medicamento"
            />
          ) : (
            <CampoSurface className="p-3.5 text-sm">
              <p className="font-semibold text-foreground">Sem produtos veterinários em cache</p>
              <p className="mt-1 text-muted-foreground">
                Você pode registrar a dose e descrever o medicamento utilizado nas observações da próxima etapa.
              </p>
            </CampoSurface>
          )}

          <NumPad
            value={dose}
            onChange={setDose}
            suffix={produtoSelecionado?.unidade_medida ?? "mL/animal"}
            label="Dose aplicada por animal"
          />

          <CampoStepNav
            onBack={() => setStep("lote")}
            onNext={() => setStep("confirmar")}
            nextLabel={
              <>
                Próximo <ArrowRight className="ml-1 inline size-4" />
              </>
            }
            nextDisabled={opcoesProdutos.length > 0 && !produtoSelecionado}
          />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />

          <CampoSurface className="grid gap-2 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Lote" value={loteAtual?.identificacao ?? "—"} />
            <SummaryRow
              label="Alvo"
              value={
                modoIndividual
                  ? animalSelecionado?.numero_brinco ?? animalSelecionado?.nome ?? "—"
                  : `${qtdCabecas} cabeças`
              }
            />
            <SummaryRow label="Produto" value={produtoSelecionado?.nome ?? "Informado em obs."} />
            <SummaryRow
              label="Dose"
              value={`${dose || "0"} ${produtoSelecionado?.unidade_medida ?? "mL"}`}
            />
          </CampoSurface>

          <CampoSurface className="p-3.5">
            <textarea
              placeholder="Diagnóstico, carência, via de aplicação..."
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
            onBack={() => setStep("produto")}
            onNext={() => void handleSalvar()}
            nextLabel={
              saving ? (
                "Salvando..."
              ) : (
                <>
                  <Check className="mr-1 inline size-4" /> Salvar Medicação
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
