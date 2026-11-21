"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { ArrowRight, Baby, Check, CheckCircle2 } from "lucide-react";

import { CameraCapture } from "@/components/campo/camera-capture";
import { FieldSelect } from "@/components/campo/field-select";
import { CampoStepNav, CampoSuccessScreen } from "@/components/campo/flow";
import { GpsWarning } from "@/components/campo/gps-warning";
import { NumPad } from "@/components/campo/num-pad";
import { TaskHeader } from "@/components/campo/task-header";
import { CampoShell, CampoSurface } from "@/components/campo/ui";
import { useCamera } from "@/hooks/useCamera";
import { useGps } from "@/hooks/useGps";
import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { createTask } from "@/lib/task-factory";

type Step = "lote" | "quantidade" | "confirmar";

export default function NascimentoColetivoPage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();

  const [step, setStep] = useState<Step>("lote");
  const [loteId, setLoteId] = useState("");
  const [quantidade, setQuantidade] = useState("1");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(
    () => db.lotes.where("fazenda_id").equals(fazendaId).toArray(),
    [fazendaId]
  );

  const lotesColetivos = (lotes ?? []).filter((l) => l.modo_gestao !== "INDIVIDUAL");
  const loteAtual = lotesColetivos.find((l) => l.id === loteId);
  const qtdInt = Math.floor(Number(quantidade) || 0);
  const qtdValida =
    Number.isFinite(Number(quantidade)) &&
    Number.isInteger(Number(quantidade)) &&
    qtdInt >= 1;
  const stepIndex = ["lote", "quantidade", "confirmar"].indexOf(step);

  const handleSalvar = async () => {
    setSaving(true);
    try {
      await createTask({
        type: "NASCIMENTO_LOTE",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId || undefined,
        dados: {
          lote_id: loteId || undefined,
          quantidade_cabecas: qtdInt,
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
        title="Nascimento registrado"
        description="Saldo local atualizado na fila de sincronização."
        primaryLabel="Novo nascimento"
        onPrimary={() => {
          setDone(false);
          setStep("lote");
          setLoteId("");
          setQuantidade("1");
          setObs("");
        }}
        onSecondary={() => router.replace("/pecuaria")}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader
        title="Nascimento Coletivo"
        icon={Baby}
        gpsStatus={gps.status}
        step={stepIndex + 1}
        totalSteps={3}
        domain="PECUARIA"
      />

      {step === "lote" && (
        <div className="flex flex-1 flex-col gap-4">
          {lotesColetivos.length > 0 ? (
            <FieldSelect
              label="Lote Coletivo (POR LOTE)"
              options={lotesColetivos.map((l) => ({
                id: l.id,
                label: l.identificacao,
                sublabel: `${l.especie} · ${l.quantidade_cabecas} cab. atuais`,
              }))}
              value={loteId}
              onChange={setLoteId}
              placeholder="Selecione o lote"
            />
          ) : (
            <CampoSurface className="space-y-1.5 p-4 text-sm">
              <p className="font-semibold text-foreground">Nenhum lote coletivo disponível</p>
              <p className="text-muted-foreground">
                Para matrizes em controle individual (brinco), use o atalho Parto na seção Reprodução.
              </p>
            </CampoSurface>
          )}

          <CampoStepNav
            onBack={() => router.back()}
            onNext={() => setStep("quantidade")}
            nextLabel={
              <>
                Próximo <ArrowRight className="ml-1 inline size-4" />
              </>
            }
            nextDisabled={!loteAtual}
          />
        </div>
      )}

      {step === "quantidade" && (
        <div className="flex flex-1 flex-col gap-4">
          <NumPad
            value={quantidade}
            onChange={setQuantidade}
            suffix="bezerros"
            label="Quantidade de nascimentos no lote"
          />
          <CampoSurface className="p-3.5 text-sm">
            <p className="text-muted-foreground">
              Novo saldo previsto após sincronização:{" "}
              <span className="font-semibold text-foreground">
                {(loteAtual?.quantidade_cabecas ?? 0) + (qtdValida ? qtdInt : 0)} cabeças
              </span>
            </p>
          </CampoSurface>
          <CampoStepNav
            onBack={() => setStep("lote")}
            onNext={() => setStep("confirmar")}
            nextLabel={
              <>
                Próximo <ArrowRight className="ml-1 inline size-4" />
              </>
            }
            nextDisabled={!qtdValida}
          />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />

          <CampoSurface className="grid gap-2 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Lote" value={loteAtual?.identificacao ?? "—"} />
            <SummaryRow label="Nascimentos" value={`+${qtdInt} cab.`} />
            <SummaryRow
              label="Saldo Projetado"
              value={`${(loteAtual?.quantidade_cabecas ?? 0) + qtdInt} cab.`}
            />
          </CampoSurface>

          <CampoSurface className="p-3.5">
            <textarea
              placeholder="Observações do nascimento (sexo predominante, vigor, pasto...)"
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
            onBack={() => setStep("quantidade")}
            onNext={() => void handleSalvar()}
            nextLabel={
              saving ? (
                "Salvando..."
              ) : (
                <>
                  <Check className="mr-1 inline size-4" /> Salvar Nascimento
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
