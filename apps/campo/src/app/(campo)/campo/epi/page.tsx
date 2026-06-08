"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";
import { useGps } from "@/hooks/useGps";
import { createOfflineCadernoEvent, buildEvidenceFromImage } from "@/lib/caderno-offline";
import { useSessionStore } from "@/lib/stores/session-store";
import { TaskHeader } from "@/components/campo/task-header";
import { FieldSelect } from "@/components/campo/field-select";
import { NumPad } from "@/components/campo/num-pad";
import { SignaturePad } from "@/components/campo/signature-pad";
import { GpsWarning } from "@/components/campo/gps-warning";
import { CampoButton, CampoShell, CampoSurface } from "@/components/campo/ui";
import { CampoStepNav, CampoSuccessScreen } from "@/components/campo/flow";

type Step = "colaborador" | "equipamento" | "quantidade" | "assinatura" | "confirmar";

export default function EntregaEpiPage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const gps = useGps(true);

  const [step, setStep] = useState<Step>("colaborador");
  const [colaboradorId, setColaboradorId] = useState("");
  const [insumoId, setInsumoId] = useState("");
  const [quantidade, setQuantidade] = useState("1");
  const [assinaturaBase64, setAssinaturaBase64] = useState("");
  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";

  // Query collaborators and filter EPI insumos
  const colaboradores = useLiveQuery(() => db.colaboradores.toArray(), []);
  const insumosEpi = useLiveQuery(() => db.insumos.filter(i => i.tipo === "EPI").toArray(), []);
  const safras = useLiveQuery(() => db.safras.toArray(), []);

  const selectedColaborador = colaboradores?.find(c => c.id === colaboradorId);
  const selectedInsumo = insumosEpi?.find(i => i.id === insumoId);
  const activeSafra = safras?.find(s => s.status === "ATIVA") ?? safras?.[0];

  const stepsList: Step[] = ["colaborador", "equipamento", "quantidade", "assinatura", "confirmar"];
  const stepIndex = stepsList.indexOf(step);

  const handleSalvar = async () => {
    if (!selectedColaborador || !selectedInsumo || !activeSafra) return;
    setSaving(true);
    try {
      // Build the signature evidence if available
      const evidencias = assinaturaBase64
        ? [
            buildEvidenceFromImage({
              localUri: assinaturaBase64,
              index: 0,
              gpsLatitude: gps.latitude,
              gpsLongitude: gps.longitude,
            }),
          ]
        : [];

      // Create local offline event
      await createOfflineCadernoEvent({
        tipo_evento: "EPI_ENTREGA",
        safra_id: activeSafra.id,
        safra_nome: activeSafra.ano_safra,
        unidade_produtiva_id: fazendaId || null,
        descricao: `Entrega de EPI: ${selectedInsumo.nome} para ${selectedColaborador.nome}`,
        payload_operacional: {
          trabalhador_id: selectedColaborador.id,
          nome_trabalhador: selectedColaborador.nome,
          epi_tipo: selectedInsumo.nome,
          quantidade: parseInt(quantidade, 10) || 1,
          data_entrega: new Date().toISOString().slice(0, 10),
          validade: null,
          obs,
        },
        evidencias,
      });

      setDone(true);
    } catch (err) {
      console.error("Erro ao registrar entrega de EPI offline", err);
    } finally {
      setSaving(false);
    }
  };

  if (done) {
    return (
      <CampoSuccessScreen
        icon="🦺"
        title="Entrega de EPI Registrada"
        description="Salvo localmente com assinatura. Será sincronizado automaticamente ao restabelecer a conexão."
        primaryLabel="Nova Entrega"
        onPrimary={() => {
          setDone(false);
          setStep("colaborador");
          setColaboradorId("");
          setInsumoId("");
          setQuantidade("1");
          setAssinaturaBase64("");
          setObs("");
        }}
        onSecondary={() => router.replace("/home")}
      />
    );
  }

  return (
    <CampoShell className="gap-4">
      <TaskHeader title="Entrega de EPI" icon="🦺" gpsStatus={gps.status} step={stepIndex + 1} totalSteps={5} />

      {step === "colaborador" && (
        <div className="flex flex-1 flex-col gap-4">
          <FieldSelect
            label="Colaborador / Trabalhador"
            options={(colaboradores ?? []).map((c) => ({
              id: c.id,
              label: c.nome,
              sublabel: c.cargo || undefined,
            }))}
            value={colaboradorId}
            onChange={setColaboradorId}
            placeholder="Selecione o trabalhador"
          />
          <CampoStepNav
            onBack={() => router.back()}
            onNext={() => setStep("equipamento")}
            nextLabel="Próximo →"
            nextDisabled={!colaboradorId}
          />
        </div>
      )}

      {step === "equipamento" && (
        <div className="flex flex-1 flex-col gap-4">
          <FieldSelect
            label="EPI / Equipamento"
            options={(insumosEpi ?? []).map((i) => ({
              id: i.id,
              label: i.nome,
              sublabel: i.unidade_medida || undefined,
            }))}
            value={insumoId}
            onChange={setInsumoId}
            placeholder="Selecione o EPI"
          />
          <CampoStepNav
            onBack={() => setStep("colaborador")}
            onNext={() => setStep("quantidade")}
            nextLabel="Próximo →"
            nextDisabled={!insumoId}
          />
        </div>
      )}

      {step === "quantidade" && (
        <div className="flex flex-1 flex-col gap-4">
          <NumPad
            value={quantidade}
            onChange={setQuantidade}
            suffix="un"
            label="Quantidade Entregue"
          />
          <CampoStepNav
            onBack={() => setStep("equipamento")}
            onNext={() => setStep("assinatura")}
            nextLabel="Próximo →"
            nextDisabled={!quantidade || parseFloat(quantidade) <= 0}
          />
        </div>
      )}

      {step === "assinatura" && (
        <div className="flex flex-1 flex-col gap-4">
          <SignaturePad
            onSave={setAssinaturaBase64}
            placeholder="Assinatura manuscrita do colaborador"
          />
          <CampoStepNav
            onBack={() => setStep("quantidade")}
            onNext={() => setStep("confirmar")}
            nextLabel="Próximo →"
            nextDisabled={!assinaturaBase64}
          />
        </div>
      )}

      {step === "confirmar" && (
        <div className="flex flex-1 flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />
          
          <CampoSurface className="grid gap-2.5 p-3.5 text-sm md:grid-cols-2">
            <SummaryRow label="Colaborador" value={selectedColaborador?.nome ?? "—"} />
            <SummaryRow label="EPI" value={selectedInsumo?.nome ?? "—"} />
            <SummaryRow label="Quantidade" value={`${quantidade} un`} />
            <SummaryRow label="Assinatura" value={assinaturaBase64 ? "Capturada ✓" : "Pendente"} />
          </CampoSurface>

          <CampoSurface className="p-3.5">
            <textarea
              placeholder="Observações adicionais (opcional)"
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={3}
              className="min-h-[88px] w-full resize-none rounded-sm border border-border bg-card px-3.5 py-2.5 text-sm outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
            />
          </CampoSurface>

          {assinaturaBase64 && (
            <CampoSurface className="flex flex-col items-center justify-center p-3.5">
              <p className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Visualização da Assinatura</p>
              <img
                src={assinaturaBase64}
                alt="Assinatura do trabalhador"
                className="max-h-24 object-contain rounded-sm border border-border bg-white"
              />
            </CampoSurface>
          )}

          <CampoButton
            onClick={handleSalvar}
            disabled={saving || !activeSafra}
            className="mt-auto w-full"
            size="md"
            variant="primary"
          >
            {saving ? "Registrando..." : "✅ Confirmar e Salvar Entrega"}
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
