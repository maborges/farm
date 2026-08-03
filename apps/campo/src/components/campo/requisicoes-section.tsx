"use client";

import { useEffect, useState } from "react";
import { ChevronDown, PackageOpen, Undo2, AlertTriangle } from "lucide-react";
import { CampoSurface, CampoButton, CampoPill } from "@/components/campo/ui";
import { BottomSheet } from "@/components/bottom-sheet";
import { PinPad } from "@/components/campo/pin-pad";
import {
  listarRequisicoesDaOperacao,
  confirmarRetiradaRequisicao,
  confirmarDevolucaoRequisicao,
  type Requisicao,
} from "@/lib/requisicoes-api";

const STATUS_LABEL: Record<string, string> = {
  PENDENTE: "Aguardando separação no almoxarifado",
  SEPARANDO: "Em separação no almoxarifado",
  APROVADA: "Aprovada — aguardando retirada",
  ENTREGUE: "Retirada confirmada",
  RECUSADA: "Recusada",
  CANCELADA: "Cancelada",
};

function statusToneClass(status: string): string {
  switch (status) {
    case "ENTREGUE":
      return "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200";
    case "APROVADA":
      return "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200";
    case "RECUSADA":
    case "CANCELADA":
      return "border-border bg-muted text-muted-foreground";
    default:
      return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200";
  }
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
    reload();
  }, [operacaoAgricolaId]);

  if (loadError) {
    return (
      <CampoSurface className="flex items-center gap-2 p-4 text-sm text-destructive">
        <AlertTriangle className="size-4 shrink-0" />
        {loadError}
      </CampoSurface>
    );
  }

  if (!requisicoes || requisicoes.length === 0) {
    return null;
  }

  return (
    <CampoSurface className="flex flex-col gap-3 p-4">
      <p className="text-[11px] uppercase tracking-[0.18em] text-primary">
        Requisições de Material
      </p>
      <div className="flex flex-col gap-2">
        {requisicoes.map((req) => (
          <RequisicaoItem
            key={req.id}
            requisicao={req}
            expanded={expandedId === req.id}
            onToggle={() => setExpandedId((prev) => (prev === req.id ? null : req.id))}
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
  const [modo, setModo] = useState<"RETIRADA" | "DEVOLUCAO" | null>(null);

  const saldoNaoDevolvidoTotal = requisicao.itens.reduce((acc, item) => {
    const entregue = item.quantidade_entregue ?? 0;
    const devolvido = item.quantidade_devolvida ?? 0;
    return acc + Math.max(entregue - devolvido, 0);
  }, 0);

  // Backend só aceita entrega/retirada em APROVADA ou SEPARANDO (ver
  // EstoqueService.entregar_requisicao) — PENDENTE é o estado inicial antes do
  // almoxarifado aprovar, mostrar o botão nesse status geraria um erro confuso
  // só depois do operador digitar o PIN inteiro.
  const podeRetirar = requisicao.status === "APROVADA" || requisicao.status === "SEPARANDO";
  const podeDevolver = requisicao.status === "ENTREGUE" && saldoNaoDevolvidoTotal > 0;

  return (
    <div className="rounded-sm border border-border">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left"
      >
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            {requisicao.numero ? `Requisição ${requisicao.numero}` : "Requisição"}
          </p>
          <CampoPill className={`mt-1 ${statusToneClass(requisicao.status)}`}>
            {STATUS_LABEL[requisicao.status] ?? requisicao.status}
          </CampoPill>
        </div>
        <ChevronDown
          className={`size-5 shrink-0 text-muted-foreground transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
        />
      </button>

      {expanded && (
        <div className="flex flex-col gap-3 border-t border-border px-3 py-3">
          <div className="flex flex-col gap-2">
            {requisicao.itens.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3 text-sm">
                <span className="min-w-0 truncate text-foreground">
                  {item.produto_nome ?? "Produto"}
                </span>
                <span className="shrink-0 text-muted-foreground">
                  {requisicao.status === "ENTREGUE"
                    ? `${item.quantidade_entregue ?? 0} ${item.unidade_medida ?? ""}`
                    : `${item.quantidade_solicitada} ${item.unidade_medida ?? ""}`}
                </span>
              </div>
            ))}
          </div>

          {podeRetirar && (
            <CampoButton size="sm" onClick={() => setModo("RETIRADA")}>
              <PackageOpen className="size-4 shrink-0" /> Confirmar Retirada
            </CampoButton>
          )}
          {podeDevolver && (
            <CampoButton size="sm" variant="secondary" onClick={() => setModo("DEVOLUCAO")}>
              <Undo2 className="size-4 shrink-0" /> Registrar Devolução
            </CampoButton>
          )}
        </div>
      )}

      {modo && (
        <ConfirmacaoSheet
          requisicao={requisicao}
          modo={modo}
          onClose={() => setModo(null)}
          onConfirmed={() => {
            setModo(null);
            onChanged();
          }}
        />
      )}
    </div>
  );
}

function ConfirmacaoSheet({
  requisicao,
  modo,
  onClose,
  onConfirmed,
}: {
  requisicao: Requisicao;
  modo: "RETIRADA" | "DEVOLUCAO";
  onClose: () => void;
  onConfirmed: () => void;
}) {
  const isDevolucao = modo === "DEVOLUCAO";

  const [quantidades, setQuantidades] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const item of requisicao.itens) {
      if (isDevolucao) {
        const saldo = Math.max((item.quantidade_entregue ?? 0) - (item.quantidade_devolvida ?? 0), 0);
        if (saldo > 0) initial[item.id] = String(saldo);
      } else {
        initial[item.id] = String(item.quantidade_solicitada);
      }
    }
    return initial;
  });
  const [step, setStep] = useState<"CONFERENCIA" | "PIN">("CONFERENCIA");
  const [loading, setLoading] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);

  const itensRelevantes = isDevolucao
    ? requisicao.itens.filter(
        (item) => Math.max((item.quantidade_entregue ?? 0) - (item.quantidade_devolvida ?? 0), 0) > 0
      )
    : requisicao.itens;

  const temQuantidadeValida = isDevolucao
    ? itensRelevantes.some((item) => Number(quantidades[item.id] ?? 0) > 0)
    : true;

  async function handleSubmitPin(pin: string) {
    setLoading(true);
    setPinError(null);
    try {
      if (isDevolucao) {
        const itens = itensRelevantes
          .map((item) => ({
            item_id: item.id,
            quantidade_devolvida: Number(quantidades[item.id] ?? 0),
          }))
          .filter((item) => item.quantidade_devolvida > 0);
        await confirmarDevolucaoRequisicao(requisicao.id, pin, itens);
      } else {
        const itens = itensRelevantes.map((item) => ({
          item_id: item.id,
          quantidade_conferida: Number(quantidades[item.id] ?? 0),
        }));
        await confirmarRetiradaRequisicao(requisicao.id, pin, itens);
      }
      onConfirmed();
    } catch (err) {
      setPinError(err instanceof Error ? err.message : "Erro ao confirmar. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <BottomSheet
      open
      onOpenChange={(open) => !open && onClose()}
      title={isDevolucao ? "Registrar devolução" : "Conferência de retirada"}
      description={
        step === "CONFERENCIA"
          ? "Confira as quantidades antes de assinar."
          : "Digite seu PIN para assinar eletronicamente."
      }
    >
      <div className="flex flex-col gap-4 px-5 pb-6">
        {step === "CONFERENCIA" ? (
          <>
            <div className="flex flex-col gap-3">
              {itensRelevantes.map((item) => {
                const referencia = isDevolucao
                  ? Math.max((item.quantidade_entregue ?? 0) - (item.quantidade_devolvida ?? 0), 0)
                  : item.quantidade_solicitada;
                const valorAtual = Number(quantidades[item.id] ?? 0);
                const divergente = !isDevolucao && valorAtual !== item.quantidade_solicitada;

                return (
                  <div key={item.id} className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-foreground">
                        {item.produto_nome ?? "Produto"}
                      </span>
                      {divergente && (
                        <CampoPill className="border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                          Divergente
                        </CampoPill>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        inputMode="decimal"
                        step="any"
                        min={0}
                        value={quantidades[item.id] ?? ""}
                        onChange={(e) =>
                          setQuantidades((prev) => ({ ...prev, [item.id]: e.target.value }))
                        }
                        className="w-full rounded-sm border border-border bg-card px-4 py-3 text-sm outline-none transition-colors focus:border-ring focus:bg-muted"
                      />
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {item.unidade_medida ?? ""}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {isDevolucao ? "Saldo entregue não devolvido" : "Solicitado"}: {referencia}{" "}
                      {item.unidade_medida ?? ""}
                    </p>
                  </div>
                );
              })}
            </div>
            <CampoButton size="lg" onClick={() => setStep("PIN")} disabled={!temQuantidadeValida}>
              Continuar
            </CampoButton>
            {!temQuantidadeValida && (
              <p className="text-center text-xs text-muted-foreground">
                Informe ao menos uma quantidade maior que zero para continuar.
              </p>
            )}
          </>
        ) : (
          <PinPad loading={loading} error={pinError} onSubmit={handleSubmitPin} />
        )}
      </div>
    </BottomSheet>
  );
}
