"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { useRouter, useSearchParams } from "next/navigation";
import {
  db,
  type CachedFazenda,
  type CachedSafra,
  type CachedTalhao,
  type CadernoDraft,
  type CampoEventoOffline,
  type CampoEventoOficial,
  type CadernoEvidenciaOffline,
  type CadernoEventoTipo,
  type LocalTask,
} from "@/lib/db";
import {
  buildEvidenceFromImage,
  createOfflineCadernoEvent,
  mapTaskTypeToCadernoTipo,
  PWA_CADERNO_EVENT_TYPES,
  retryOfflineCadernoEvent,
  retryEvidenciaUpload,
} from "@/lib/caderno-offline";
import { useGps } from "@/hooks/useGps";
import { useCamera } from "@/hooks/useCamera";
import { useSessionStore } from "@/lib/stores/session-store";
import { formatSafraStatus, formatDescricao } from "@/lib/format";
import {
  CampoButton,
  CampoPill,
  CampoSectionTitle,
  CampoShell,
  CampoSurface,
} from "@/components/campo/ui";
import { CampoStepNav } from "@/components/campo/flow";
import { FieldSelect } from "@/components/campo/field-select";
import { CameraCapture } from "@/components/campo/camera-capture";
import { GpsWarning } from "@/components/campo/gps-warning";
import { PessoaSelect } from "@/components/campo/PessoaSelect";
import { ArrowLeft, ArrowRight } from "lucide-react";

const EVENT_LABELS: Record<CadernoEventoTipo, string> = {
  MONITORAMENTO: "Monitoramento",
  OCORRENCIA: "Ocorrência",
  INSPECAO: "Inspeção",
  OBSERVACAO: "Observação",
  APLICACAO: "Aplicação",
  PULVERIZACAO: "Pulverização",
  IRRIGACAO: "Irrigação",
  PLANTIO: "Plantio",
  COLHEITA: "Colheita",
  MANUTENCAO: "Manutenção",
  ABASTECIMENTO: "Abastecimento",
  EXECUCAO_OPERACIONAL: "Execução operacional",
  VISITA_TECNICA: "Visita técnica",
  EPI_ENTREGA: "Entrega de EPI",
  CLIMA: "Clima",
  SOLO: "Solo",
};

const SYNC_LABELS: Record<string, { label: string; cls: string }> = {
  PENDING: {
    label: "Pendente",
    cls: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200",
  },
  SYNCING: {
    label: "Sincronizando",
    cls: "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200",
  },
  SYNCED: {
    label: "Sincronizado",
    cls: "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200",
  },
  ERROR: {
    label: "Erro",
    cls: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200",
  },
  CONFLICT: {
    label: "Conflito",
    cls: "border-orange-200 bg-orange-50 text-orange-800 dark:border-orange-900/60 dark:bg-orange-950/30 dark:text-orange-200",
  },
};

const EVIDENCE_LABELS: Record<string, { label: string; cls: string }> = {
  LOCAL: {
    label: "Local",
    cls: "border-border bg-muted text-muted-foreground",
  },
  PENDENTE_UPLOAD: {
    label: "Pendente upload",
    cls: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200",
  },
  ENVIANDO: {
    label: "Enviando...",
    cls: "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200",
  },
  ENVIADA: {
    label: "Enviada",
    cls: "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200",
  },
  ERRO_UPLOAD: {
    label: "Erro upload",
    cls: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200",
  },
};

type WizardStep = "contexto" | "registro" | "evidencias";
type DraftStatus = "idle" | "saving" | "saved";

const STEP_ORDER: WizardStep[] = ["contexto", "registro", "evidencias"];
const DRAFT_SAVE_DELAY_MS = 500;

const STEP_CONTENT: Record<
  WizardStep,
  { eyebrow: string; title: string; description: string }
> = {
  contexto: {
    eyebrow: "Passo 1",
    title: "Defina onde o operador está trabalhando",
    description:
      "Selecione a unidade produtiva, a safra e o talhão antes de registrar a atividade.",
  },
  registro: {
    eyebrow: "Passo 2",
    title: "Descreva o que aconteceu em campo",
    description:
      "Escolha o tipo do evento e adicione o mínimo necessário para que o gestor entenda o registro.",
  },
  evidencias: {
    eyebrow: "Passo 3",
    title: "Revise o contexto e anexe evidências",
    description:
      "Valide GPS, fotos e resumo final antes de salvar o registro offline.",
  },
};

export default function CadernoPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session, setActiveFazenda } = useSessionStore();
  const gps = useGps(true);
  const cam = useCamera();
  const {
    fotos,
    inputRef,
    canAddMore,
    openCamera,
    handleFileChange,
    removePhoto,
    clearPhotos,
    restorePhotos,
  } = cam;
  const draftSaveRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const descricaoInputRef = useRef<HTMLInputElement | null>(null);

  const [step, setStep] = useState<WizardStep>("contexto");
  const [saving, setSaving] = useState(false);
  const [draftLoaded, setDraftLoaded] = useState(false);
  const [draftRestored, setDraftRestored] = useState(false);
  const [draftStatus, setDraftStatus] = useState<DraftStatus>("idle");
  const [fazendaId, setFazendaId] = useState("");
  const [descricao, setDescricao] = useState("");
  const [observacao, setObservacao] = useState("");
  const [safraId, setSafraId] = useState("");
  const [talhaoId, setTalhaoId] = useState("");
  const [tipoEvento, setTipoEvento] = useState<CadernoEventoTipo>("MONITORAMENTO");
  const [executadoPorPessoaId, setExecutadoPorPessoaId] = useState<string | null>(null);

  const taskId = searchParams.get("task_id");
  const querySafraId = searchParams.get("safra_id");
  const queryTalhaoId = searchParams.get("talhao_id");
  const queryTipo = searchParams.get("tipo_evento") as CadernoEventoTipo | null;
  const draftId = taskId ? `caderno:${taskId}` : "caderno:default";
  const activeFazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0] ?? "";

  const fazendas = useLiveQuery(async (): Promise<CachedFazenda[]> => {
    const allowedIds = session?.fazenda_ids ?? [];
    if (allowedIds.length === 0) return [];

    const rows = await db.fazendas.bulkGet(allowedIds);
    return rows
      .filter((row): row is CachedFazenda => Boolean(row))
      .sort((a, b) => a.nome.localeCompare(b.nome));
  }, [session?.fazenda_ids?.join("|")]);

  const safras = useLiveQuery(async (): Promise<CachedSafra[]> => {
    const items = await db.safras.toArray();
    return items.sort((a, b) => b.ano_safra.localeCompare(a.ano_safra));
  }, []);

  const talhoes = useLiveQuery(async (): Promise<CachedTalhao[]> => {
    if (!fazendaId) return [];
    return db.talhoes.where("fazenda_id").equals(fazendaId).sortBy("nome");
  }, [fazendaId]);

  const cadernoEventos = useLiveQuery(async (): Promise<CampoEventoOffline[]> => {
    return db.caderno_events.orderBy("created_at").reverse().limit(20).toArray();
  }, []);
  const cadernoEventosOficiais = useLiveQuery(async (): Promise<CampoEventoOficial[]> => {
    return db.caderno_server_events.orderBy("data_registro").reverse().limit(20).toArray();
  }, []);

  const tarefaContext = useLiveQuery(async (): Promise<LocalTask | undefined> => {
    if (!taskId) return undefined;
    return db.tasks.get(taskId);
  }, [taskId]);

  const queryTalhao = useLiveQuery(async (): Promise<CachedTalhao | undefined> => {
    if (!queryTalhaoId) return undefined;
    return db.talhoes.get(queryTalhaoId);
  }, [queryTalhaoId]);

  const fazendaAtual = useMemo(
    () => fazendas?.find((f) => f.id === fazendaId) ?? null,
    [fazendas, fazendaId]
  );
  const talhaoAtual = useMemo(
    () => talhoes?.find((t) => t.id === talhaoId) ?? null,
    [talhoes, talhaoId]
  );
  const safraAtual = useMemo(
    () => safras?.find((s) => s.id === safraId) ?? null,
    [safras, safraId]
  );

  useEffect(() => {
    if (queryTipo && PWA_CADERNO_EVENT_TYPES.includes(queryTipo as (typeof PWA_CADERNO_EVENT_TYPES)[number])) {
      setTipoEvento(queryTipo);
    }
  }, [queryTipo]);

  useEffect(() => {
    let cancelled = false;

    async function loadDraft() {
      if (!session) {
        if (!cancelled) {
          setDraftLoaded(false);
          setDraftRestored(false);
          setDraftStatus("idle");
        }
        return;
      }

      setDraftLoaded(false);

      const draft = await db.caderno_drafts.get(draftId);
      if (cancelled) return;

      if (!draft || draft.user_id !== session.user_id) {
        restorePhotos([]);
        setDraftLoaded(true);
        setDraftRestored(false);
        setDraftStatus("idle");
        return;
      }

      const restoredTipo = resolveDraftTipo(draft, queryTipo, tarefaContext);
      const restoredFazendaId =
        tarefaContext?.fazenda_id ?? queryTalhao?.fazenda_id ?? draft.fazenda_id ?? activeFazendaId ?? "";
      const restoredSafraId = querySafraId ?? draft.safra_id ?? "";
      const restoredTalhaoId = queryTalhaoId ?? tarefaContext?.talhao_id ?? draft.talhao_id ?? "";

      setStep(draft.step);
      setFazendaId(restoredFazendaId);
      setSafraId(restoredSafraId);
      setTalhaoId(restoredTalhaoId);
      setTipoEvento(restoredTipo);
      setDescricao(draft.descricao);
      setObservacao(draft.observacao);
      setExecutadoPorPessoaId(draft.executado_por_pessoa_id ?? null);
      restorePhotos(draft.fotos ?? []);
      setDraftLoaded(true);
      setDraftRestored(true);
      setDraftStatus("saved");
    }

    loadDraft();

    return () => {
      cancelled = true;
    };
  }, [activeFazendaId, draftId, querySafraId, queryTalhao?.fazenda_id, queryTalhaoId, queryTipo, restorePhotos, session, tarefaContext]);

  useEffect(() => {
    if (tarefaContext?.fazenda_id) {
      setFazendaId(tarefaContext.fazenda_id);
      return;
    }
    if (queryTalhao?.fazenda_id) {
      setFazendaId(queryTalhao.fazenda_id);
      return;
    }
    if (!tarefaContext?.fazenda_id && !queryTalhao?.fazenda_id && activeFazendaId && fazendaId !== activeFazendaId) {
      setFazendaId(activeFazendaId);
    }
  }, [activeFazendaId, fazendaId, queryTalhao?.fazenda_id, tarefaContext?.fazenda_id]);

  useEffect(() => {
    if (querySafraId) {
      setSafraId(querySafraId);
      return;
    }
    if (!safraId && safras?.length) {
      setSafraId(safras[0].id);
    }
  }, [querySafraId, safraId, safras]);

  useEffect(() => {
    if (queryTalhaoId && talhoes?.some((talhao) => talhao.id === queryTalhaoId)) {
      setTalhaoId(queryTalhaoId);
      return;
    }
    if (tarefaContext?.talhao_id && talhoes?.some((talhao) => talhao.id === tarefaContext.talhao_id)) {
      setTalhaoId(tarefaContext.talhao_id);
      return;
    }
    if (talhaoId && talhoes && !talhoes.some((talhao) => talhao.id === talhaoId)) {
      setTalhaoId("");
      return;
    }
    if (!talhaoId && talhoes?.length === 1) {
      setTalhaoId(talhoes[0].id);
    }
  }, [queryTalhaoId, talhaoId, talhoes, tarefaContext?.talhao_id]);

  useEffect(() => {
    if (tarefaContext?.type && !queryTipo) {
      setTipoEvento(mapTaskTypeToCadernoTipo(tarefaContext.type));
    }
  }, [queryTipo, tarefaContext]);

  useEffect(() => {
    if (step !== "registro") return;
    const frame = requestAnimationFrame(() => {
      descricaoInputRef.current?.focus();
    });
    return () => cancelAnimationFrame(frame);
  }, [step]);

  useEffect(() => {
    if (!session || !draftLoaded || saving) return;

    const hasDraftContent =
      step !== "contexto" ||
      !!fazendaId ||
      !!safraId ||
      !!talhaoId ||
      !!descricao.trim() ||
      !!observacao.trim() ||
      fotos.length > 0 ||
      tipoEvento !== "MONITORAMENTO";

    if (draftSaveRef.current) {
      clearTimeout(draftSaveRef.current);
    }

    if (!hasDraftContent) {
      void db.caderno_drafts.delete(draftId);
      setDraftStatus("idle");
      return;
    }

    setDraftStatus("saving");
    draftSaveRef.current = setTimeout(() => {
      const draft: CadernoDraft = {
        id: draftId,
        task_id: taskId ?? null,
        user_id: session.user_id,
        step,
        fazenda_id: fazendaId || null,
        safra_id: safraId || null,
        talhao_id: talhaoId || null,
        tipo_evento: tipoEvento,
        descricao,
        observacao,
        executado_por_pessoa_id: executadoPorPessoaId,
        fotos,
        updated_at: new Date().toISOString(),
      };

      void db.caderno_drafts.put(draft).then(() => {
        setDraftStatus("saved");
      });
    }, DRAFT_SAVE_DELAY_MS);

    return () => {
      if (draftSaveRef.current) {
        clearTimeout(draftSaveRef.current);
        draftSaveRef.current = null;
      }
    };
  }, [
    fotos,
    descricao,
    draftId,
    draftLoaded,
    fazendaId,
    observacao,
    safraId,
    saving,
    session,
    step,
    talhaoId,
    taskId,
    tipoEvento,
    executadoPorPessoaId,
  ]);

  const preparedEvidence = useMemo<CadernoEvidenciaOffline[]>(
    () =>
      fotos.map((foto, index) =>
        buildEvidenceFromImage({
          localUri: foto,
          index,
          gpsLatitude: gps.latitude,
          gpsLongitude: gps.longitude,
        })
      ),
    [fotos, gps.latitude, gps.longitude]
  );

  const contextReady = !!fazendaId && !!safraId && !!talhaoId;
  const canSubmit = contextReady && !saving;
  const recent = cadernoEventos ?? [];
  const officialRecent = cadernoEventosOficiais ?? [];
  const currentStep = STEP_CONTENT[step];
  const pendingLocalEvents = useMemo(
    () => recent.filter((entry) => entry.sync_status !== "SYNCED" && entry.sync_status !== "CONFLICT"),
    [recent]
  );
  const reviewLocalEvents = useMemo(
    () =>
      recent.filter(
        (entry) =>
          entry.sync_status === "CONFLICT" ||
          entry.review_required ||
          entry.status_evento === "REJEITADO" ||
          entry.documental_status === "ORIGEM_INVALIDADA" ||
          entry.origem_invalidada ||
          Boolean(entry.retificado_por_evento_id)
      ),
    [recent]
  );
  const reviewOfficialEvents = useMemo(
    () =>
      officialRecent.filter(
        (entry) =>
          entry.status_evento === "REJEITADO" ||
          entry.documental_status === "ORIGEM_INVALIDADA" ||
          entry.origem_invalidada ||
          entry.retificado
      ),
    [officialRecent]
  );

  const handleFazendaChange = (id: string) => {
    void setActiveFazenda(id);
    setFazendaId(id);
    setTalhaoId("");
  };

  const handleSalvar = async () => {
    if (!session || !contextReady) return;

    setSaving(true);
    try {
      await createOfflineCadernoEvent({
        tipo_evento: tipoEvento,
        safra_id: safraId,
        safra_nome: safraAtual?.ano_safra
          ? `${safraAtual.ano_safra}${safraAtual.cultura ? ` · ${safraAtual.cultura}` : ""}`
          : null,
        talhao_id: talhaoId || null,
        talhao_nome: talhaoAtual?.nome ?? null,
        unidade_produtiva_id: fazendaId || null,
        tarefa_id: taskId ?? null,
        descricao: descricao.trim() || EVENT_LABELS[tipoEvento] || tipoEvento,
        payload_operacional: {
          descricao: descricao.trim() || EVENT_LABELS[tipoEvento] || tipoEvento,
          observacao: observacao.trim() || undefined,
          task_id: taskId ?? undefined,
          tarefa_origem: tarefaContext?.type ?? undefined,
          data_registro: new Date().toISOString().slice(0, 10),
          localizacao_status: gps.status,
          latitude: gps.latitude ?? undefined,
          longitude: gps.longitude ?? undefined,
          unidade_produtiva_id: fazendaId,
        },
        evidencias: preparedEvidence,
        usuario_id: session.user_id,
        executado_por_pessoa_id: executadoPorPessoaId || null,
      });

      await db.caderno_drafts.delete(draftId);

      setDescricao("");
      setObservacao("");
      clearPhotos();
      setStep("contexto");
      setDraftStatus("idle");
      setDraftRestored(false);
    } finally {
      setSaving(false);
    }
  };

  const goNext = () => {
    if (step === "contexto") {
      if (!contextReady) return;
      setStep("registro");
      return;
    }

    if (step === "registro") {
      setStep("evidencias");
      return;
    }

    router.push("/sync");
  };

  const goBack = () => {
    if (step === "evidencias") {
      setStep("registro");
      return;
    }

    if (step === "registro") {
      setStep("contexto");
      return;
    }

    router.back();
  };

  return (
    <CampoShell className="gap-5">
      <CampoSurface className="p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <CampoPill className="border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200">
              Caderno oficial
            </CampoPill>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">
              Registros do Caderno
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              O aplicativo conduz o operador por contexto, registro e evidências antes do envio.
            </p>
          </div>
          <CampoButton variant="secondary" size="sm" onClick={() => router.back()} className="size-10 px-0 shrink-0 border-border bg-card shadow-sm flex items-center justify-center">
            <ArrowLeft className="size-5 text-muted-foreground" />
          </CampoButton>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <CampoPill className="border-border bg-muted text-muted-foreground">
            {recent.length} registros locais
          </CampoPill>
          <CampoPill
            className={
              gps.status === "DISPONIVEL"
                ? "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200"
                : "border-border bg-muted text-muted-foreground"
            }
          >
            {gps.status === "DISPONIVEL"
              ? "GPS pronto"
              : gps.status === "AGUARDANDO"
                ? "Aguardando GPS"
                : "Sem GPS"}
          </CampoPill>
          {fazendaAtual && (
            <CampoPill className="border-border bg-muted text-muted-foreground">
              {fazendaAtual.nome}
            </CampoPill>
          )}
          {taskId && (
            <CampoPill className="border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">
              Vinculado à tarefa
            </CampoPill>
          )}
          {draftRestored && (
            <CampoPill className="border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              Rascunho restaurado
            </CampoPill>
          )}
          {draftStatus === "saving" && (
            <CampoPill className="border-border bg-muted text-muted-foreground">
              Salvando rascunho...
            </CampoPill>
          )}
          {draftStatus === "saved" && (
            <CampoPill className="border-border bg-muted text-muted-foreground">
              Rascunho salvo
            </CampoPill>
          )}
        </div>
      </CampoSurface>

      <section className="flex flex-col gap-3">
        <CampoSectionTitle
          eyebrow={currentStep.eyebrow}
          title={currentStep.title}
          description={currentStep.description}
        />

        <div className="grid gap-2 sm:grid-cols-3">
          {STEP_ORDER.map((wizardStep, index) => {
            const active = wizardStep === step;
            const unlocked =
              wizardStep === "contexto" ||
              (wizardStep === "registro" && contextReady) ||
              wizardStep === "evidencias";
            return (
              <div
                key={wizardStep}
                className={`rounded-sm border px-4 py-3 text-sm transition-colors ${
                  active
                    ? "border-primary/40 bg-accent text-accent-foreground shadow-sm"
                    : unlocked
                      ? "border-border bg-card text-foreground"
                      : "border-border bg-muted/60 text-muted-foreground"
                }`}
              >
                <p className="text-[11px] uppercase tracking-[0.16em] opacity-70">
                  Etapa {index + 1}
                </p>
                <p className="mt-1 font-semibold capitalize">{wizardStep}</p>
              </div>
            );
          })}
        </div>

        {step === "contexto" && (
          <div className="grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="flex flex-col gap-3">
              <FieldSelect
                label="Unidade produtiva"
                options={(fazendas ?? []).map((fazenda) => ({
                  id: fazenda.id,
                  label: fazenda.nome,
                  sublabel: [fazenda.municipio, fazenda.uf].filter(Boolean).join(" · ") || undefined,
                }))}
                value={fazendaId}
                onChange={handleFazendaChange}
                placeholder="Escolha onde está operando"
              />

              <CampoSurface className="flex flex-col gap-2 p-4 sm:p-5">
                <label className="text-sm font-semibold text-foreground">Safra</label>
                {safras && safras.length > 0 ? (
                  <select
                    value={safraId}
                    onChange={(e) => setSafraId(e.target.value)}
                    className="rounded-sm border border-border bg-card px-4 py-4 text-base outline-none transition-colors focus:border-ring focus:bg-muted"
                  >
                    <option value="">Selecione a safra</option>
                    {safras.map((safra) => (
                      <option key={safra.id} value={safra.id}>
                        {safra.ano_safra}
                        {safra.cultura ? ` · ${safra.cultura}` : ""}
                        {safra.status ? ` · ${formatSafraStatus(safra.status)}` : ""}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="rounded-sm border border-border bg-card px-4 py-4 text-sm text-muted-foreground">
                    Nenhuma safra sincronizada ainda. Faça sync para carregar as safras ativas.
                  </p>
                )}
              </CampoSurface>

              <FieldSelect
                label="Talhão"
                options={(talhoes ?? []).map((talhao) => ({
                  id: talhao.id,
                  label: talhao.nome,
                  sublabel: talhao.area_ha ? `${talhao.area_ha} ha` : undefined,
                }))}
                value={talhaoId}
                onChange={setTalhaoId}
                placeholder={
                  fazendaId
                    ? "Selecione o talhão"
                    : "Escolha a unidade produtiva antes"
                }
              />
            </div>

            <CampoSurface className="flex flex-col gap-4 p-4 sm:p-5">
              <p className="text-[11px] uppercase tracking-[0.18em] text-primary">
                Guia do operador
              </p>
              <div className="grid gap-2 text-sm">
                <Row label="Unidade produtiva" value={fazendaAtual?.nome ?? "Selecione"} />
                <Row label="Safra" value={safraAtual ? `${safraAtual.ano_safra}${safraAtual.cultura ? ` · ${safraAtual.cultura}` : ""}${safraAtual.status ? ` · ${formatSafraStatus(safraAtual.status)}` : ""}` : "Selecione"} />
                <Row label="Talhão" value={talhaoAtual?.nome ?? "Selecione"} />
              </div>
              <p className="text-sm leading-6 text-muted-foreground">
                O registro só avança quando o contexto operacional estiver definido. Isso evita lançar
                eventos na área errada.
              </p>
              <p className="text-xs text-muted-foreground">
                O rascunho fica salvo neste dispositivo enquanto o operador estiver preenchendo.
              </p>
              {!contextReady && (
                <p className="rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                  Preencha unidade produtiva, safra e talhão para liberar a próxima etapa.
                </p>
              )}
            </CampoSurface>
          </div>
        )}

        {step === "registro" && (
          <div className="grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="flex flex-col gap-3">
              <FieldSelect
                label="Tipo de evento"
                options={PWA_CADERNO_EVENT_TYPES.map((tipo) => ({
                  id: tipo,
                  label: EVENT_LABELS[tipo],
                }))}
                value={tipoEvento}
                onChange={(id) => setTipoEvento(id as CadernoEventoTipo)}
                placeholder="Escolha o tipo"
              />

              <CampoSurface className="flex flex-col gap-2 p-4 sm:p-5">
                <label className="text-sm font-semibold text-foreground">Executor (Opcional)</label>
                <PessoaSelect
                  unidadeProdutivaId={fazendaId}
                  value={executadoPorPessoaId}
                  onChange={setExecutadoPorPessoaId}
                />
              </CampoSurface>

              <CampoSurface className="flex flex-col gap-2 p-4 sm:p-5">
                <label className="text-sm font-semibold text-foreground">Descrição</label>
                <input
                  ref={descricaoInputRef}
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  placeholder="Ex: presença de lagarta no talhão 7"
                  className="rounded-lg md:rounded-sm border border-border bg-card px-4 py-3.5 md:py-4 text-base outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
                  enterKeyHint="next"
                />
              </CampoSurface>

              <CampoSurface className="flex flex-col gap-2 p-4 sm:p-5">
                <label className="text-sm font-semibold text-foreground">Observação</label>
                <textarea
                  value={observacao}
                  onChange={(e) => setObservacao(e.target.value)}
                  placeholder="Complementos do registro, recomendação, detalhe técnico..."
                  rows={4}
                  className="min-h-[120px] w-full resize-none rounded-lg md:rounded-sm border border-border bg-card px-4 py-3 text-base md:text-sm outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
                  enterKeyHint="done"
                />
              </CampoSurface>
            </div>

            <CampoSurface className="flex flex-col gap-4 p-4 sm:p-5">
              <p className="text-[11px] uppercase tracking-[0.18em] text-primary">
                Contexto confirmado
              </p>
              <div className="grid gap-2 text-sm">
                <Row label="Unidade produtiva" value={fazendaAtual?.nome ?? "—"} />
                <Row label="Safra" value={safraAtual ? `${safraAtual.ano_safra}${safraAtual.cultura ? ` · ${safraAtual.cultura}` : ""}${safraAtual.status ? ` · ${formatSafraStatus(safraAtual.status)}` : ""}` : "—"} />
                <Row label="Talhão" value={talhaoAtual?.nome ?? "—"} />
                <Row label="Tipo" value={EVENT_LABELS[tipoEvento] ?? tipoEvento} />
              </div>
              <p className="text-sm leading-6 text-muted-foreground">
                Escreva como o operador falaria em campo. Se a descrição ficar vazia, o app usará o
                nome do tipo de evento.
              </p>
              {taskId && tarefaContext && (
                <div className="rounded-sm border border-sky-200 bg-sky-50 px-3 py-3 text-xs text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">
                  Registro vinculado à tarefa {tarefaContext.titulo ?? tarefaContext.type}.
                </div>
              )}
            </CampoSurface>
          </div>
        )}

        {step === "evidencias" && (
          <div className="grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="flex flex-col gap-3">
              <GpsWarning status={gps.status} onRetry={gps.capture} />
              <CameraCapture
                fotos={fotos}
                inputRef={inputRef}
                canAddMore={canAddMore}
                onOpen={openCamera}
                onFileChange={handleFileChange}
                onRemove={removePhoto}
              />
            </div>

            <div className="flex flex-col gap-3">
              <CampoSurface className="p-4 sm:p-5">
                <p className="text-[11px] uppercase tracking-[0.18em] text-primary">
                  Resumo final
                </p>
                <div className="mt-3 grid gap-2 text-sm">
                  <Row label="Unidade produtiva" value={fazendaAtual?.nome ?? "—"} />
                  <Row label="Safra" value={safraAtual ? `${safraAtual.ano_safra}${safraAtual.cultura ? ` · ${safraAtual.cultura}` : ""}${safraAtual.status ? ` · ${formatSafraStatus(safraAtual.status)}` : ""}` : "—"} />
                  <Row label="Talhão" value={talhaoAtual?.nome ?? "—"} />
                  <Row label="Tipo" value={EVENT_LABELS[tipoEvento] ?? tipoEvento} />
                  <Row label="Descrição" value={formatDescricao(descricao.trim()) || EVENT_LABELS[tipoEvento]} />
                  <Row label="Fotos" value={`${preparedEvidence.length}`} />
                </div>
              </CampoSurface>

              <CampoSurface className="p-4 sm:p-5">
                <p className="text-sm leading-6 text-muted-foreground">
                  Salve o registro mesmo offline. Quando a conexão voltar, o sync enviará o evento ao
                  backend oficial com o contexto já validado.
                </p>
              </CampoSurface>

              <CampoButton
                onClick={handleSalvar}
                disabled={!canSubmit}
                className="w-full"
                size="lg"
                variant="primary"
              >
                {saving ? "Salvando..." : "Salvar registro offline"}
              </CampoButton>
            </div>
          </div>
        )}
      </section>

      {taskId && tarefaContext && (
        <CampoSurface className="p-4 sm:p-5">
          <p className="text-[11px] uppercase tracking-[0.18em] text-primary">Vínculo com tarefa</p>
          <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
            <Row label="Tarefa" value={tarefaContext.titulo ?? tarefaContext.type} />
            <Row label="Talhão da tarefa" value={tarefaContext.talhao_id ?? "—"} />
          </div>
        </CampoSurface>
      )}

      <section className="flex flex-col gap-3 pb-24">
        <CampoSectionTitle
          eyebrow="Fila local"
          title="Pendentes no Dispositivo"
          description="Somente o que ainda depende deste aparelho: envio, retry ou upload local."
        />
        <div className="flex flex-col gap-3">
          {pendingLocalEvents.length === 0 ? (
            <CampoSurface className="p-5 text-sm text-muted-foreground">
              Nenhum pendente local no dispositivo.
            </CampoSurface>
          ) : (
            pendingLocalEvents.map((entry) => {
              const syncBadge = SYNC_LABELS[entry.sync_status] ?? SYNC_LABELS.PENDING;
              return (
                <CampoSurface key={entry.local_id} className="flex flex-col gap-3 p-4 sm:p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-foreground">
                        {EVENT_LABELS[entry.tipo_evento as CadernoEventoTipo] ?? entry.tipo_evento}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {new Date(entry.created_at).toLocaleString("pt-BR")}
                      </p>
                    </div>
                    <CampoPill className={syncBadge.cls}>{syncBadge.label}</CampoPill>
                  </div>

                  <div className="grid gap-2 text-sm md:grid-cols-2">
                    <Row label="Safra" value={entry.safra_nome ?? entry.safra_id.slice(0, 8)} />
                    <Row label="Talhão" value={entry.talhao_nome ?? entry.talhao_id ?? "—"} />
                    <Row label="Descrição" value={formatDescricao(entry.descricao) || "—"} />
                    <Row label="Status local" value={entry.status_evento} />
                  </div>

                  {entry.last_sync_error && (
                    <p className="rounded-sm border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
                      {entry.last_sync_error}
                    </p>
                  )}

                  {/* Aviso: evento sincronizado mas evidências ainda pendentes */}
                  {entry.sync_status === "SYNCED" && entry.evidencias.some(
                    (ev) => ev.upload_status !== "ENVIADA" && ev.upload_status !== "ENVIANDO"
                  ) && (
                    <p className="rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                      ✓ Registro enviado. Evidências aguardam conexão para upload.
                    </p>
                  )}

                  <div className="flex flex-wrap gap-2">
                    {entry.evidencias.length > 0 && (() => {
                      const enviadas = entry.evidencias.filter((ev) => ev.upload_status === "ENVIADA").length;
                      const pendentes = entry.evidencias.filter(
                        (ev) => ev.upload_status === "PENDENTE_UPLOAD" || ev.upload_status === "LOCAL" || ev.upload_status === "ENVIANDO"
                      ).length;
                      const erros = entry.evidencias.filter((ev) => ev.upload_status === "ERRO_UPLOAD").length;
                      return (
                        <>
                          {enviadas > 0 && (
                            <CampoPill className="border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200">
                              {enviadas} enviada{enviadas !== 1 ? "s" : ""}
                            </CampoPill>
                          )}
                          {pendentes > 0 && (
                            <CampoPill className="border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                              {pendentes} pendente{pendentes !== 1 ? "s" : ""}
                            </CampoPill>
                          )}
                          {erros > 0 && (
                            <CampoPill className="border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
                              {erros} com erro
                            </CampoPill>
                          )}
                        </>
                      );
                    })()}
                    {entry.tarefa_id && (
                      <CampoPill className="border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">
                        Vinculado à tarefa
                      </CampoPill>
                    )}
                  </div>

                  {entry.evidencias.length > 0 && (
                    <div className="flex flex-col gap-2">
                      {entry.evidencias.map((evidencia, index) => {
                        const badge = EVIDENCE_LABELS[evidencia.upload_status ?? "LOCAL"] ?? EVIDENCE_LABELS.LOCAL;
                        const podeRetry =
                          evidencia.upload_status === "ERRO_UPLOAD" &&
                          entry.sync_status === "SYNCED" &&
                          (evidencia.upload_attempts ?? 0) < 5;
                        return (
                          <div
                            key={`${entry.local_id}:evidencia:${evidencia.local_evidence_id ?? index}`}
                            className="flex items-center justify-between gap-2"
                          >
                            <CampoPill className={badge.cls}>
                              Evidência {index + 1} · {badge.label}
                              {evidencia.upload_attempts != null && evidencia.upload_attempts > 0 && (
                                <span className="ml-1 opacity-70">({evidencia.upload_attempts}×)</span>
                              )}
                            </CampoPill>
                            {podeRetry && (
                              <CampoButton
                                variant="secondary"
                                size="sm"
                                onClick={async () => {
                                  try {
                                    await retryEvidenciaUpload(entry.local_id, evidencia.local_evidence_id);
                                  } catch (e) {
                                    console.error(e);
                                  }
                                }}
                              >
                                Reenviar
                              </CampoButton>
                            )}
                            {evidencia.last_upload_error && evidencia.upload_status === "ERRO_UPLOAD" && (
                              <span className="text-xs text-rose-700 dark:text-rose-300 truncate max-w-[180px]" title={evidencia.last_upload_error}>
                                {evidencia.last_upload_error}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {entry.sync_status === "ERROR" && (
                    <div>
                      <CampoButton
                        variant="secondary"
                        size="sm"
                        onClick={() => retryOfflineCadernoEvent(entry.local_id)}
                      >
                        Tentar novamente
                      </CampoButton>
                    </div>
                  )}
                </CampoSurface>

              );
            })
          )}
        </div>
      </section>

      <section className="flex flex-col gap-3 pb-24">
        <CampoSectionTitle
          eyebrow="Atenção"
          title="Revisão Necessária"
          description="Registros com rejeição, retificação, invalidação documental ou divergência entre aparelho e servidor."
        />
        <div className="flex flex-col gap-3">
          {reviewLocalEvents.length === 0 && reviewOfficialEvents.length === 0 ? (
            <CampoSurface className="p-5 text-sm text-muted-foreground">
              Nenhum item exigindo revisão no momento.
            </CampoSurface>
          ) : (
            <>
              {reviewLocalEvents.map((entry) => (
                <CampoSurface key={`review-local:${entry.local_id}`} className="flex flex-col gap-3 p-4 sm:p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-foreground">
                        {EVENT_LABELS[entry.tipo_evento as CadernoEventoTipo] ?? entry.tipo_evento}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Registro local · {new Date(entry.created_at).toLocaleString("pt-BR")}
                      </p>
                    </div>
                    <CampoPill className={(SYNC_LABELS[entry.sync_status] ?? SYNC_LABELS.PENDING).cls}>
                      {(SYNC_LABELS[entry.sync_status] ?? SYNC_LABELS.PENDING).label}
                    </CampoPill>
                  </div>

                  <div className="grid gap-2 text-sm md:grid-cols-2">
                    <Row label="Status oficial conhecido" value={entry.status_evento} />
                    <Row label="Estado documental" value={entry.documental_status ?? "—"} />
                    <Row label="Descrição" value={formatDescricao(entry.descricao) || "—"} />
                    <Row label="Reconciliação" value={entry.reconciled_at ? new Date(entry.reconciled_at).toLocaleString("pt-BR") : "Pendente"} />
                  </div>

                  {renderAttentionMessage({
                    statusEvento: entry.status_evento,
                    documentalStatus: entry.documental_status ?? null,
                    origemInvalidada: entry.origem_invalidada ?? false,
                    retificado: Boolean(entry.retificado_por_evento_id),
                  })}

                  {entry.conflict_reason && (
                    <p className="rounded-sm border border-orange-200 bg-orange-50 px-3 py-2 text-xs text-orange-800 dark:border-orange-900/60 dark:bg-orange-950/30 dark:text-orange-200">
                      {entry.conflict_reason}
                    </p>
                  )}

                  {entry.oficial_justificativa && (
                    <Row label="Justificativa oficial" value={entry.oficial_justificativa} />
                  )}
                  {entry.motivo_invalidacao_origem && (
                    <Row label="Motivo da invalidação" value={entry.motivo_invalidacao_origem} />
                  )}
                </CampoSurface>
              ))}

              {reviewOfficialEvents.map((entry) => (
                <CampoSurface key={`review-oficial:${entry.server_id}`} className="flex flex-col gap-3 p-4 sm:p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-foreground">
                        {EVENT_LABELS[(entry.tipo_evento ?? entry.tipo) as CadernoEventoTipo] ?? entry.tipo_evento ?? entry.tipo}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Registro oficial · {new Date(`${entry.data_registro}T12:00:00`).toLocaleDateString("pt-BR")}
                      </p>
                    </div>
                    <CampoPill className={getDocumentalPillClass(entry.documental_status)}>
                      {entry.documental_status}
                    </CampoPill>
                  </div>

                  <div className="grid gap-2 text-sm md:grid-cols-2">
                    <Row label="Status do evento" value={entry.status_evento} />
                    <Row label="Descrição" value={formatDescricao(entry.descricao) || "—"} />
                    <Row label="Versão vigente" value={entry.versao_vigente ? "Sim" : "Não"} />
                    <Row label="Origem invalidada" value={entry.origem_invalidada ? "Sim" : "Não"} />
                  </div>

                  {renderAttentionMessage({
                    statusEvento: entry.status_evento,
                    documentalStatus: entry.documental_status,
                    origemInvalidada: entry.origem_invalidada,
                    retificado: entry.retificado,
                  })}

                  {entry.justificativa && <Row label="Justificativa oficial" value={entry.justificativa} />}
                  {entry.motivo_invalidacao_origem && (
                    <Row label="Motivo da invalidação" value={entry.motivo_invalidacao_origem} />
                  )}
                  {entry.motivo_retificacao && (
                    <Row label="Motivo da retificação" value={entry.motivo_retificacao} />
                  )}
                </CampoSurface>
              ))}
            </>
          )}
        </div>
      </section>

      <section className="flex flex-col gap-3 pb-24">
        <CampoSectionTitle
          eyebrow="Caderno Oficial"
          title="Timeline Oficial"
          description="Registros oficiais do servidor. Aprovação, rejeição, retificação e invalidação aparecem aqui."
        />
        <div className="flex flex-col gap-3">
          {officialRecent.length === 0 ? (
            <CampoSurface className="p-5 text-sm text-muted-foreground">
              Nenhum evento oficial sincronizado ainda.
            </CampoSurface>
          ) : (
            officialRecent.map((entry) => (
              <CampoSurface key={entry.server_id} className="flex flex-col gap-3 p-4 sm:p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground">
                      {EVENT_LABELS[(entry.tipo_evento ?? entry.tipo) as CadernoEventoTipo] ?? entry.tipo_evento ?? entry.tipo}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {new Date(`${entry.data_registro}T12:00:00`).toLocaleDateString("pt-BR")}
                    </p>
                  </div>
                  <CampoPill className={getDocumentalPillClass(entry.documental_status)}>
                    {entry.documental_status}
                  </CampoPill>
                </div>

                <div className="grid gap-2 text-sm md:grid-cols-2">
                  <Row label="Descrição" value={formatDescricao(entry.descricao) || "—"} />
                  <Row label="Status do evento" value={entry.status_evento} />
                  <Row label="Versão vigente" value={entry.versao_vigente ? "Sim" : "Não"} />
                  <Row label="Origem invalidada" value={entry.origem_invalidada ? "Sim" : "Não"} />
                </div>

                <div className="flex flex-wrap gap-2">
                  {entry.retificado && (
                    <CampoPill className="border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                      Retificado
                    </CampoPill>
                  )}
                  {entry.retificador && (
                    <CampoPill className="border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">
                      Retificador
                    </CampoPill>
                  )}
                  {entry.invalidado && (
                    <CampoPill className="border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
                      Origem invalidada
                    </CampoPill>
                  )}
                  {entry.local_id && entry.device_id === session?.device_id && (
                    <CampoPill className="border-border bg-muted text-muted-foreground">
                      Reconhecido neste dispositivo
                    </CampoPill>
                  )}
                  {entry.device_id && entry.device_id !== session?.device_id && (
                    <CampoPill className="border-border bg-muted text-muted-foreground">
                      Recebido de outro dispositivo
                    </CampoPill>
                  )}
                </div>

                {renderAttentionMessage({
                  statusEvento: entry.status_evento,
                  documentalStatus: entry.documental_status,
                  origemInvalidada: entry.origem_invalidada,
                  retificado: entry.retificado,
                })}

                {(entry.motivo_invalidacao_origem || entry.motivo_retificacao) && (
                  <div className="grid gap-2 text-sm">
                    {entry.motivo_invalidacao_origem && (
                      <Row label="Motivo da invalidação" value={entry.motivo_invalidacao_origem} />
                    )}
                    {entry.motivo_retificacao && (
                      <Row label="Motivo da retificação" value={entry.motivo_retificacao} />
                    )}
                    {entry.justificativa && (
                      <Row label="Justificativa oficial" value={entry.justificativa} />
                    )}
                  </div>
                )}
              </CampoSurface>
            ))
          )}
        </div>
      </section>

      <CampoStepNav
        aboveBottomNav
        onBack={goBack}
        onNext={goNext}
        nextLabel={
          step === "contexto"
            ? <><span className="hidden sm:inline">Continuar para o </span>registro <ArrowRight className="size-4 ml-1 inline" /></>
            : step === "registro"
              ? <><span className="hidden sm:inline">Revisar </span>evidências <ArrowRight className="size-4 ml-1 inline" /></>
              : <><span className="hidden sm:inline">Ver </span>sincronização <ArrowRight className="size-4 ml-1 inline" /></>
        }
        nextDisabled={step === "contexto" && !contextReady}
        backLabel={step === "contexto" ? "Voltar" : "Etapa anterior"}
      />
    </CampoShell>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 rounded-sm border border-border bg-card px-3 py-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium text-foreground">{value}</span>
    </div>
  );
}

function getDocumentalPillClass(documentalStatus: string): string {
  if (documentalStatus === "ORIGEM_INVALIDADA") {
    return "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200";
  }
  if (documentalStatus === "RETIFICADO") {
    return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200";
  }
  return "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200";
}

function renderAttentionMessage({
  statusEvento,
  documentalStatus,
  origemInvalidada,
  retificado,
}: {
  statusEvento: string;
  documentalStatus: string | null;
  origemInvalidada: boolean;
  retificado: boolean;
}) {
  if (statusEvento === "PENDENTE_APROVACAO") {
    return (
      <p className="rounded-sm border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">
        Registro enviado. Aguardando aprovação.
      </p>
    );
  }

  if (statusEvento === "REJEITADO") {
    return (
      <p className="rounded-sm border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
        Registro rejeitado. Verifique a justificativa.
      </p>
    );
  }

  if (documentalStatus === "ORIGEM_INVALIDADA" || origemInvalidada) {
    return (
      <p className="rounded-sm border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
        A origem operacional deste registro foi invalidada.
      </p>
    );
  }

  if (retificado || documentalStatus === "RETIFICADO") {
    return (
      <p className="rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
        Este registro possui versão corrigida.
      </p>
    );
  }

  return null;
}

function resolveDraftTipo(
  draft: CadernoDraft,
  queryTipo: CadernoEventoTipo | null,
  tarefaContext?: LocalTask
): CadernoEventoTipo {
  if (queryTipo && PWA_CADERNO_EVENT_TYPES.includes(queryTipo as (typeof PWA_CADERNO_EVENT_TYPES)[number])) {
    return queryTipo;
  }

  if (tarefaContext?.type) {
    return mapTaskTypeToCadernoTipo(tarefaContext.type);
  }

  return (draft.tipo_evento as CadernoEventoTipo) ?? "MONITORAMENTO";
}
