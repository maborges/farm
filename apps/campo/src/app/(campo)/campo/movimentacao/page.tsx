"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { ArrowRight, ArrowRightLeft, Check, CheckCircle2 } from "lucide-react";

import { AnimalPicker } from "@/components/campo/animal-picker";
import { CameraCapture } from "@/components/campo/camera-capture";
import { FieldSelect } from "@/components/campo/field-select";
import { CampoStepNav, CampoSuccessScreen } from "@/components/campo/flow";
import { GpsWarning } from "@/components/campo/gps-warning";
import { TaskHeader } from "@/components/campo/task-header";
import { CampoShell, CampoSurface } from "@/components/campo/ui";
import { useCamera } from "@/hooks/useCamera";
import { useGps } from "@/hooks/useGps";
import { db, type CachedAnimal } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { createTask } from "@/lib/task-factory";

type Step = "origem" | "destino" | "confirmar";
type ModoMovimento = "PIQUETE" | "TRANSFERIR_ANIMAL";

export default function MovimentacaoLotePage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();

  const [step, setStep] = useState<Step>("origem");
  const [loteId, setLoteId] = useState("");
  const [modo, setModo] = useState<ModoMovimento>("PIQUETE");
  const [animalId, setAnimalId] = useState("");
  const [areaDestinoId, setAreaDestinoId] = useState("");
  const [loteDestinoId, setLoteDestinoId] = useState("");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(
    () => db.lotes.where("fazenda_id").equals(fazendaId).toArray(),
    [fazendaId]
  );
  const piquetes = useLiveQuery(
    () =>
      db.talhoes
        .where("fazenda_id")
        .equals(fazendaId)
        .filter((t) => t.tipo === "PIQUETE")
        .toArray(),
    [fazendaId]
  );
  const animaisNoLote = useLiveQuery(
    async (): Promise<CachedAnimal[]> =>
      loteId ? db.animais.where("lote_id").equals(loteId).toArray() : [],
    [loteId]
  );

  const loteAtual = lotes?.find((l) => l.id === loteId);
  const animaisAtivos = (animaisNoLote ?? []).filter((a) => {
    const status = (a.status ?? "ATIVO").toUpperCase();
    return status === "ATIVO" || status === "";
  });
  const piqueteAtual = piquetes?.find((p) => p.id === loteAtual?.area_id);
  const piquetesDestino = (piquetes ?? []).filter((p) => p.id !== loteAtual?.area_id);
  const lotesDestino = (lotes ?? []).filter((l) => l.id !== loteId);
  const piqueteDestino = piquetesDestino.find((p) => p.id === areaDestinoId);
  const loteDestino = lotesDestino.find((l) => l.id === loteDestinoId);
  const animalSelecionado = animaisAtivos.find((a) => a.id === animalId);

  const stepIndex = ["origem", "destino", "confirmar"].indexOf(step);

  const handleSalvar = async () => {
    setSaving(true);
    try {
      await createTask({
        type: "MOVIMENTACAO_LOTE",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId || undefined,
        dados:
          modo === "TRANSFERIR_ANIMAL"
            ? {
                lote_id: loteId || undefined,
                animal_id: animalId,
                lote_destino_id: loteDestinoId,
                observacoes: obs.trim() || undefined,
                data_evento: new Date().toISOString().slice(0, 10),
              }
            : {
                lote_id: loteId || undefined,
                area_destino_id: areaDestinoId,
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
        title="Movimentação registrada"
        description="Salvo localmente e pronto para sincronizar quando houver sinal."
        primaryLabel="Nova movimentação"
        onPrimary={() => {
          setDone(false);
          setStep("origem");
          setLoteId("");
          setAnimalId("");
          setAreaDestinoId("");
          setLoteDestinoId("");
          setObs("");
        }}
        onSecondary={() => router.replace("/pecuaria")}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader
        title="Troca de Piquete / Lote"
        icon={ArrowRightLeft}
        gpsStatus={gps.status}
        step={stepIndex + 1}
        totalSteps={3}
        domain="PECUARIA"
      />

      {step === "origem" && (
        <div className="flex flex-1 flex-col gap-4">
          <FieldSelect
            label="Lote de Origem"
            options={(lotes ?? []).map((l) => ({
              id: l.id,
              label: l.identificacao,
              sublabel: `${l.quantidade_cabecas} cab. · ${
                l.modo_gestao === "INDIVIDUAL" ? "Individual" : "Por Lote"
              }`,
            }))}
            value={loteId}
            onChange={(val) => {
              setLoteId(val);
              setModo("PIQUETE");
              setAnimalId("");
              setAreaDestinoId("");
              setLoteDestinoId("");
            }}
            placeholder={fazendaId ? "Selecione o lote" : "Selecione a fazenda no topo"}
          />

          {loteAtual && (
            <CampoSurface className="space-y-3 p-3.5 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">Piquete atual:</span>
                <span className="font-semibold text-foreground">
                  {piqueteAtual?.nome ?? "Sem piquete vinculado"}
                </span>
              </div>

              {animaisAtivos.length > 0 && (
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setModo("PIQUETE")}
                    className={`rounded-sm border px-3 py-2 text-xs font-semibold ${
                      modo === "PIQUETE"
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-card text-muted-foreground"
                    }`}
                  >
                    Trocar Lote de Pasto
                  </button>
                  <button
                    type="button"
                    onClick={() => setModo("TRANSFERIR_ANIMAL")}
                    className={`rounded-sm border px-3 py-2 text-xs font-semibold ${
                      modo === "TRANSFERIR_ANIMAL"
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-card text-muted-foreground"
                    }`}
                  >
                    Transferir 1 Animal
                  </button>
                </div>
              )}
            </CampoSurface>
          )}

          {loteAtual && modo === "TRANSFERIR_ANIMAL" && animaisAtivos.length > 0 && (
            <AnimalPicker
              label="Animal a transferir"
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
            onNext={() => setStep("destino")}
            nextLabel={
              <>
                Próximo <ArrowRight className="ml-1 inline size-4" />
              </>
            }
            nextDisabled={!loteAtual || (modo === "TRANSFERIR_ANIMAL" && !animalSelecionado)}
          />
        </div>
      )}

      {step === "destino" && (
        <div className="flex flex-1 flex-col gap-4">
          {modo === "PIQUETE" ? (
            piquetesDestino.length > 0 ? (
              <FieldSelect
                label="Piquete Destino"
                options={piquetesDestino.map((p) => ({
                  id: p.id,
                  label: p.nome,
                  sublabel: p.area_ha ? `${p.area_ha.toFixed(1)} ha` : undefined,
                }))}
                value={areaDestinoId}
                onChange={setAreaDestinoId}
                placeholder="Selecione o pasto de destino"
              />
            ) : (
              <CampoSurface className="p-4 text-sm">
                <p className="font-semibold text-foreground">Nenhum piquete destino disponível</p>
                <p className="mt-1 text-muted-foreground">
                  Cadastre áreas do tipo PIQUETE na fazenda e sincronize o dispositivo antes de transferir o lote.
                </p>
              </CampoSurface>
            )
          ) : (
            <FieldSelect
              label="Lote Destino"
              options={lotesDestino.map((l) => ({
                id: l.id,
                label: l.identificacao,
                sublabel: `${l.quantidade_cabecas} cab.`,
              }))}
              value={loteDestinoId}
              onChange={setLoteDestinoId}
              placeholder="Selecione o lote de destino"
            />
          )}

          <CampoStepNav
            onBack={() => setStep("origem")}
            onNext={() => setStep("confirmar")}
            nextLabel={
              <>
                Próximo <ArrowRight className="ml-1 inline size-4" />
              </>
            }
            nextDisabled={modo === "PIQUETE" ? !areaDestinoId : !loteDestinoId}
          />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />

          <CampoSurface className="grid gap-2 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Lote Origem" value={loteAtual?.identificacao ?? "—"} />
            {modo === "PIQUETE" ? (
              <>
                <SummaryRow label="Piquete Atual" value={piqueteAtual?.nome ?? "Sem piquete"} />
                <SummaryRow label="Piquete Destino" value={piqueteDestino?.nome ?? "—"} />
                <SummaryRow label="Cabeças" value={String(loteAtual?.quantidade_cabecas ?? 0)} />
              </>
            ) : (
              <>
                <SummaryRow
                  label="Animal"
                  value={animalSelecionado?.numero_brinco ?? animalSelecionado?.nome ?? "—"}
                />
                <SummaryRow label="Lote Destino" value={loteDestino?.identificacao ?? "—"} />
              </>
            )}
          </CampoSurface>

          <CampoSurface className="p-3.5">
            <textarea
              placeholder="Observação da troca de pasto (ex: vedação, rotação, altura do capim)..."
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={2}
              className="min-h-[78px] w-full resize-none rounded-sm border border-border bg-card px-3.5 py-2.5 text-sm outline-none focus:border-ring placeholder:text-muted-foreground/50"
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
            onBack={() => setStep("destino")}
            onNext={() => void handleSalvar()}
            nextLabel={
              saving ? (
                "Salvando..."
              ) : (
                <>
                  <Check className="mr-1 inline size-4" /> Confirmar Movimentação
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
