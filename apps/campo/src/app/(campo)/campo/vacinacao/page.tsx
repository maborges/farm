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
import { Syringe, Check, CheckCircle2, ArrowRight } from "lucide-react";
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
  const [quantidade, setQuantidade] = useState("");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";
  const lotes = useLiveQuery(() => db.lotes.where("fazenda_id").equals(fazendaId).toArray(), [fazendaId]);
  const animaisNoLote = useLiveQuery(
    async (): Promise<CachedAnimal[]> => (loteId ? db.animais.where("lote_id").equals(loteId).toArray() : []),
    [loteId]
  );
  const vacinas = useLiveQuery(
    () => db.insumos.filter((i) => i.tipo === "VETERINARIO" || i.tipo === "VACINA" || i.nome.toLowerCase().includes("vacin")).toArray(),
    []
  );

  const stepIndex = ["lote", "vacina", "confirmar"].indexOf(step);
  const loteAtual = lotes?.find((l) => l.id === loteId);
  const vacinaAtual = (vacinas ?? []).find((vacina) => vacina.id === vacinaId);
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
    try {
      await createTask({
        type: "VACINACAO",
        module: "pecuaria",
        fazenda_id: fazendaId,
        lote_id: loteId || undefined,
        dados: {
          lote_id: loteId || undefined,
          area_id: loteAtual?.area_id ?? null,
          modo_gestao: isPorLote ? "POR_LOTE" : "INDIVIDUAL",
          vacina_id: vacinaAtual?.id ?? null,
          produto_id: vacinaAtual?.id ?? null,
          produto_nome: vacinaAtual?.nome ?? null,
          dose_ml: parseFloat(quantidade) || 0,
          dose: parseFloat(quantidade) || 0,
          unidade_medida: vacinaAtual?.unidade_medida ?? "ML",
          quantidade_animais: quantidadeAnimais,
          animais_ids: isPorLote ? [] : animaisAtivos.map((animal) => animal.id),
          observacoes: obs,
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
      <TaskHeader title="Vacinação" icon={Syringe} gpsStatus={gps.status} step={stepIndex + 1} totalSteps={3} domain="PECUARIA" />

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
              <p className="font-semibold text-foreground">Cabeças consideradas no lote</p>
              {loteAtual && (
                <span className="rounded-sm border border-border bg-muted px-2 py-0.5 text-[11px] font-semibold">
                  {isPorLote ? "POR LOTE" : "INDIVIDUAL"}
                </span>
              )}
            </div>
            <p className="text-2xl font-semibold text-foreground">{quantidadeAnimais}</p>
            <p className="text-muted-foreground">
              {isPorLote
                ? "Baixa proporcional de estoque será calculada pelo saldo de cabeças do lote."
                : "Aplica a vacinação para todos os animais individuais ativos do lote."}
            </p>
          </CampoSurface>
          <CampoStepNav onBack={() => router.back()} onNext={() => setStep("vacina")} nextLabel={<>Próximo <ArrowRight className="size-4 ml-1 inline" /></>} nextDisabled={!loteId || quantidadeAnimais === 0} />
        </div>
      )}

      {step === "vacina" && (
        <div className="flex flex-1 flex-col gap-4">
          {(vacinas ?? []).length > 0 ? (
            <FieldSelect
              label="Vacina"
              options={(vacinas ?? []).map((v) => ({ id: v.id, label: v.nome, sublabel: v.unidade_medida ?? undefined }))}
              value={vacinaId}
              onChange={setVacinaId}
              placeholder="Selecione a vacina"
            />
          ) : (
            <CampoSurface className="flex flex-col gap-2 p-3.5 text-sm">
              <p className="font-semibold text-foreground">Nenhuma vacina sincronizada</p>
              <p className="text-muted-foreground">
                Sincronize os insumos do dispositivo antes de registrar vacinação manual, para garantir estoque e custo.
              </p>
            </CampoSurface>
          )}

          <NumPad value={quantidade} onChange={setQuantidade} suffix="mL/animal" label="Dose por animal (mL)" />

          <CampoStepNav onBack={() => setStep("lote")} onNext={() => setStep("confirmar")} nextLabel={<>Próximo <ArrowRight className="size-4 ml-1 inline" /></>} nextDisabled={!vacinaAtual || !quantidade || quantidade === "0" || quantidadeAnimais === 0} />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          <CampoSurface className="grid gap-2.5 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Lote" value={loteAtual?.identificacao ?? "—"} />
            <SummaryRow label="Modo" value={isPorLote ? "Por Lote (Coletivo)" : "Individual"} />
            <SummaryRow label="Cabeças" value={String(quantidadeAnimais)} />
            <SummaryRow label="Vacina" value={vacinaAtual?.nome ?? "—"} />
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
            {saving ? "Salvando..." : <><Check className="size-4 shrink-0" /> Salvar Vacinação</>}
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
