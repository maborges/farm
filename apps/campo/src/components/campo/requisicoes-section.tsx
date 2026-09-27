"use client";

import { useEffect, useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { AlertTriangle, ChevronDown, PackageCheck, RotateCcw, Sprout } from "lucide-react";
import { CampoButton, CampoPill, CampoSurface } from "@/components/campo/ui";
import { BottomSheet } from "@/components/bottom-sheet";
import { PinPad } from "@/components/campo/pin-pad";
import { db } from "@/lib/db";
import { runSync } from "@/lib/sync/worker";
import { useSessionStore } from "@/lib/stores/session-store";
import {
  enfileirarRecebimentoRequisicao,
  enfileirarDestinacaoRequisicao,
  listarRequisicoesDaOperacao,
  type Requisicao,
} from "@/lib/requisicoes-api";

const STATUS_LABEL: Record<string, string> = {
  PENDENTE_CONFERENCIA: "Pendente de conferência",
  DIVERGENTE: "Divergência informada",
  RECEBIDA: "Recebimento confirmado",
  RECUSADO: "Entrega recusada",
};

function statusToneClass(status: string): string {
  if (status === "RECEBIDA") {
    return "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200";
  }
  if (status === "DIVERGENTE" || status === "RECUSADO") {
    return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200";
  }
  return "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200";
}

export function RequisicoesSection({ operacaoAgricolaId }: { operacaoAgricolaId: string }) {
  const [requisicoes, setRequisicoes] = useState<Requisicao[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function reload() {
    try {
      setLoadError(null);
      const data = await listarRequisicoesDaOperacao(operacaoAgricolaId);
      setRequisicoes(data);
      setExpandedId((prev) => prev ?? data[0]?.id ?? null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Erro ao carregar requisições");
    }
  }

  useEffect(() => {
    void reload();
  }, [operacaoAgricolaId]);

  if (loadError) {
    return (
      <CampoSurface className="flex items-center gap-2 p-4 text-sm text-destructive">
        <AlertTriangle className="size-4 shrink-0" />
        {loadError}
      </CampoSurface>
    );
  }

  if (!requisicoes || requisicoes.length === 0) return null;

  return (
    <CampoSurface className="flex flex-col gap-3 p-4">
      <p className="text-[11px] uppercase tracking-[0.18em] text-primary">Materiais aguardando conferência</p>
      <div className="flex flex-col gap-2">
        {requisicoes.map((requisicao) => (
          <RequisicaoItem
            key={requisicao.id}
            requisicao={requisicao}
            expanded={expandedId === requisicao.id}
            onToggle={() => setExpandedId((prev) => (prev === requisicao.id ? null : requisicao.id))}
            onChanged={reload}
          />
        ))}
      </div>
    </CampoSurface>
  );
}

function RequisicaoItem({
  requisicao,
  expanded,
  onToggle,
  onChanged,
}: {
  requisicao: Requisicao;
  expanded: boolean;
  onToggle: () => void;
  onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [openDestinacao, setOpenDestinacao] = useState(false);
  const pendingOperations = useLiveQuery(
    () => db.requisicao_operacoes.where("requisicao_id").equals(requisicao.id).toArray(),
    [requisicao.id],
    [],
  );
  const hasPending = pendingOperations?.some((operation) => ["PENDING", "IN_FLIGHT"].includes(operation.status)) ?? false;
  const hasPendingConference = requisicao.itens.some((item) => item.quantidade_pendente_conferencia > 0);
  const hasPossession = requisicao.itens.some((item) => item.quantidade_em_posse > 0);

  return (
    <div className="rounded-sm border border-border">
      <button type="button" onClick={onToggle} className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            {requisicao.numero ? `Requisição ${requisicao.numero}` : "Requisição"}
          </p>
          <CampoPill className={`mt-1 ${statusToneClass(requisicao.status_efetivo)}`}>
            {STATUS_LABEL[requisicao.status_efetivo] ?? requisicao.status_efetivo}
          </CampoPill>
        </div>
        <ChevronDown className={`size-5 shrink-0 text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`} />
      </button>

      {expanded && (
        <div className="flex flex-col gap-3 border-t border-border px-3 py-3">
          {requisicao.itens.map((item) => (
            <div key={item.id} className="rounded-sm border border-border/70 p-2.5 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate font-medium text-foreground">{item.produto_nome ?? "Produto"}</span>
                <CampoPill className="border-border bg-muted text-[10px] text-muted-foreground">
                  {item.natureza_item ?? "LEGADO"}
                </CampoPill>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Entregue {item.quantidade_entregue} {item.unidade} · Recebido {item.quantidade_recebida} {item.unidade} · Em posse {item.quantidade_em_posse} {item.unidade}
              </p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Consumido {item.quantidade_consumida ?? 0} · Devolvido {item.quantidade_devolvida ?? 0} · Perda {item.quantidade_perdida ?? 0} · Dano {item.quantidade_danificada ?? 0} · Extravio {item.quantidade_extraviada ?? 0}
              </p>
              {item.entregas.map((entrega) => (
                <p key={entrega.id} className="mt-1 text-xs text-muted-foreground">
                  Lote {entrega.lote_id ?? "não informado"}: {entrega.quantidade_pendente_conferencia} {entrega.unidade} pendentes
                </p>
              ))}
            </div>
          ))}
          {hasPending && (
            <CampoPill className="border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              Pendente de sincronização
            </CampoPill>
          )}
          {hasPendingConference && (
            <CampoButton size="sm" onClick={() => setOpen(true)}>
              <PackageCheck className="size-4 shrink-0" /> Conferir recebimento
            </CampoButton>
          )}
          {requisicao.status_conciliacao && requisicao.status_conciliacao !== "CONCILIADA" && (
            <CampoPill className="border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">
              Conciliação: {requisicao.status_conciliacao}
            </CampoPill>
          )}
          {hasPossession && (
            <CampoButton size="sm" variant="secondary" onClick={() => setOpenDestinacao(true)}>
              <RotateCcw className="size-4 shrink-0" /> Registrar consumo/devolução
            </CampoButton>
          )}
        </div>
      )}

      {open && (
        <RecebimentoSheet
          requisicao={requisicao}
          onClose={() => setOpen(false)}
          onConfirmed={() => {
            setOpen(false);
            onChanged();
          }}
        />
      )}
      {openDestinacao && (
        <DestinacaoSheet
          requisicao={requisicao}
          onClose={() => setOpenDestinacao(false)}
          onConfirmed={() => {
            setOpenDestinacao(false);
            onChanged();
          }}
        />
      )}
    </div>
  );
}

function RecebimentoSheet({
  requisicao,
  onClose,
  onConfirmed,
}: {
  requisicao: Requisicao;
  onClose: () => void;
  onConfirmed: () => void;
}) {
  const loginWithPIN = useSessionStore((state) => state.loginWithPIN);
  const pendingDeliveries = requisicao.itens.flatMap((item) =>
    item.entregas
      .filter((entrega) => entrega.quantidade_pendente_conferencia > 0)
      .map((entrega) => ({ item, entrega }))
  );
  const [quantidades, setQuantidades] = useState<Record<string, string>>(
    () => Object.fromEntries(pendingDeliveries.map(({ entrega }) => [entrega.id, String(entrega.quantidade_pendente_conferencia)]))
  );
  const [motivo, setMotivo] = useState("");
  const [recusando, setRecusando] = useState(false);
  const [step, setStep] = useState<"CONFERENCIA" | "PIN">("CONFERENCIA");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasQuantity = recusando || pendingDeliveries.some(({ entrega }) => Number(quantidades[entrega.id] ?? 0) > 0);

  async function handleSubmitPin(pin: string) {
    setLoading(true);
    setError(null);
    try {
      if (!(await loginWithPIN(pin))) throw new Error("PIN inválido.");
      if (recusando && !motivo.trim()) throw new Error("Informe o motivo da recusa.");

      let version = requisicao.version;
      const commands = recusando
        ? [pendingDeliveries[0]]
        : pendingDeliveries.filter(({ entrega }) => Number(quantidades[entrega.id] ?? 0) > 0);
      for (const entry of commands) {
        const quantidade = recusando ? 0 : Number(quantidades[entry.entrega.id] ?? 0);
        const resultado = recusando
          ? "RECUSADO" as const
          : quantidade >= entry.entrega.quantidade_pendente_conferencia
            ? "RECEBIDO_INTEGRAL" as const
            : "DIVERGENTE" as const;
        await enfileirarRecebimentoRequisicao({
          requisicao_id: requisicao.id,
          item_id: entry.item.id,
          entrega_evento_id: entry.entrega.id,
          quantidade_recebida: quantidade,
          resultado,
          base_version: version,
          motivo: motivo.trim() || undefined,
        });
        version += 1;
      }
      if (navigator.onLine) void runSync();
      onConfirmed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível registrar a conferência.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <BottomSheet
      open
      onOpenChange={(open) => !open && onClose()}
      title="Conferir recebimento"
      description={step === "CONFERENCIA" ? "A entrega já saiu do estoque. Informe o que efetivamente recebeu." : "Confirme sua identidade local para enfileirar a operação."}
    >
      <div className="flex flex-col gap-4 px-5 pb-6">
        {step === "CONFERENCIA" ? (
          <>
            <div className="flex flex-col gap-3">
              {pendingDeliveries.map(({ item, entrega }) => (
                <div key={entrega.id} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-foreground">{item.produto_nome ?? "Produto"}</span>
                    <span className="text-xs text-muted-foreground">Lote {entrega.lote_id ?? "—"}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      inputMode="decimal"
                      step="any"
                      min={0}
                      max={entrega.quantidade_pendente_conferencia}
                      value={quantidades[entrega.id] ?? ""}
                      disabled={recusando}
                      onChange={(event) => setQuantidades((current) => ({ ...current, [entrega.id]: event.target.value }))}
                      className="w-full rounded-sm border border-border bg-card px-4 py-3 text-sm outline-none focus:border-ring focus:bg-muted disabled:opacity-50"
                    />
                    <span className="shrink-0 text-xs text-muted-foreground">{entrega.unidade}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">Pendente: {entrega.quantidade_pendente_conferencia} {entrega.unidade}</p>
                </div>
              ))}
            </div>
            <textarea
              value={motivo}
              onChange={(event) => setMotivo(event.target.value)}
              placeholder="Motivo da divergência/recusa (obrigatório nesses casos)"
              rows={3}
              className="min-h-[88px] w-full rounded-sm border border-border bg-card px-4 py-3 text-sm outline-none focus:border-ring focus:bg-muted"
            />
            <div className="flex gap-2">
              <CampoButton size="sm" variant={recusando ? "secondary" : "primary"} onClick={() => setRecusando(false)}>Receber</CampoButton>
              <CampoButton size="sm" variant={recusando ? "danger" : "secondary"} onClick={() => setRecusando(true)}>Recusar entrega</CampoButton>
            </div>
            <CampoButton size="lg" onClick={() => setStep("PIN")} disabled={!hasQuantity}>Continuar</CampoButton>
            {!hasQuantity && <p className="text-center text-xs text-muted-foreground">Informe uma quantidade ou selecione recusa.</p>}
          </>
        ) : (
          <PinPad loading={loading} error={error} onSubmit={handleSubmitPin} />
        )}
        {step === "CONFERENCIA" && error && <p className="text-center text-sm text-destructive">{error}</p>}
      </div>
    </BottomSheet>
  );
}

function DestinacaoSheet({
  requisicao,
  onClose,
  onConfirmed,
}: {
  requisicao: Requisicao;
  onClose: () => void;
  onConfirmed: () => void;
}) {
  const loginWithPIN = useSessionStore((state) => state.loginWithPIN);
  const entries = requisicao.itens.flatMap((item) =>
    item.entregas
      .filter((entrega) => (entrega.quantidade_em_posse ?? 0) > 0)
      .map((entrega) => ({ item, entrega }))
  );
  const [selected, setSelected] = useState(entries[0]?.entrega.id ?? "");
  const entry = entries.find((candidate) => candidate.entrega.id === selected) ?? entries[0];
  const [tipo, setTipo] = useState<"CONSUMO" | "DEVOLUCAO" | "PERDA" | "DANO" | "EXTRAVIO">(
    entry?.item.natureza_item === "RETORNAVEL" ? "DEVOLUCAO" : "CONSUMO"
  );
  const [quantidade, setQuantidade] = useState(String(entry?.entrega.quantidade_em_posse ?? 0));
  const [motivo, setMotivo] = useState("");
  const [step, setStep] = useState<"FORM" | "PIN">("FORM");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isReturnable = entry?.item.natureza_item === "RETORNAVEL";
  const executionId = requisicao.execucoes?.find((execution) => execution.status !== "CANCELADA")?.id ?? null;
  const options = isReturnable
    ? (["DEVOLUCAO", "DANO", "EXTRAVIO"] as const)
    : (["CONSUMO", "DEVOLUCAO", "PERDA"] as const);

  async function submit(pin: string) {
    setLoading(true);
    setError(null);
    try {
      if (!(await loginWithPIN(pin))) throw new Error("PIN inválido.");
      if (!entry) throw new Error("Nenhum item em posse para destinar.");
      if (["PERDA", "DANO", "EXTRAVIO"].includes(tipo) && !motivo.trim()) {
        throw new Error("Informe o motivo.");
      }
      if (tipo === "CONSUMO" && !executionId) {
        throw new Error("A execução operacional da tarefa não está disponível.");
      }
      await enfileirarDestinacaoRequisicao({
        requisicao_id: requisicao.id,
        item_id: entry.item.id,
        entrega_evento_id: entry.entrega.id,
        tipo_evento: tipo,
        quantidade: Number(quantidade),
        base_version: requisicao.version,
        operacao_execucao_id: tipo === "CONSUMO" ? executionId : null,
        deposito_id: entry.entrega.deposito_id,
        lote_id: entry.entrega.lote_id,
        motivo: motivo.trim() || undefined,
      });
      if (navigator.onLine) void runSync();
      onConfirmed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível registrar a destinação.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <BottomSheet
      open
      onOpenChange={(open) => !open && onClose()}
      title="Destinar material em posse"
      description={step === "FORM" ? "Consumo não baixa estoque novamente. Devolução gera entrada física." : "Confirme sua identidade local para enfileirar a operação."}
    >
      <div className="flex flex-col gap-4 px-5 pb-6">
        {step === "FORM" ? (
          <>
            <select value={selected} onChange={(event) => setSelected(event.target.value)} className="rounded-sm border border-border bg-card px-3 py-3 text-sm">
              {entries.map(({ item, entrega }) => <option key={entrega.id} value={entrega.id}>{item.produto_nome ?? "Produto"} · {entrega.quantidade_em_posse} {entrega.unidade}</option>)}
            </select>
            <div className="flex flex-wrap gap-2">
              {options.map((option) => (
                <CampoButton key={option} size="sm" variant={tipo === option ? "primary" : "secondary"} onClick={() => setTipo(option)}>
                  {option === "CONSUMO" ? <Sprout className="size-4" /> : <RotateCcw className="size-4" />} {option}
                </CampoButton>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <input type="number" inputMode="decimal" min={0} max={entry?.entrega.quantidade_em_posse ?? 0} step="any" value={quantidade} onChange={(event) => setQuantidade(event.target.value)} className="w-full rounded-sm border border-border bg-card px-4 py-3 text-sm" />
              <span className="text-xs text-muted-foreground">{entry?.entrega.unidade}</span>
            </div>
            <textarea value={motivo} onChange={(event) => setMotivo(event.target.value)} placeholder="Motivo (obrigatório para perda, dano ou extravio)" rows={3} className="min-h-[88px] w-full rounded-sm border border-border bg-card px-4 py-3 text-sm" />
            <CampoButton size="lg" onClick={() => setStep("PIN")} disabled={!entry || Number(quantidade) <= 0}>Continuar</CampoButton>
          </>
        ) : <PinPad loading={loading} error={error} onSubmit={submit} />}
        {step === "FORM" && error && <p className="text-center text-sm text-destructive">{error}</p>}
      </div>
    </BottomSheet>
  );
}
